"""Browser-based feed extractor using Playwright.

Supports two authentication modes:
1. Cookie injection (preferred) — provide li_at cookie value
2. Profile copy — copy Chrome session files to temp dir

SECURITY:
- Session reuse only (no credential storage)
- Never logs cookies, tokens, or session data
- Temp profile is cleaned up after extraction
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.base import BaseFeedExtractor
from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    ExtractionError,
    ExtractionResult,
    FeedPost,
    PostContent,
    PostMetadata,
    PostType,
)
from linkedin_feed_extractor.session import SessionConfig

logger = logging.getLogger(__name__)

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"


class BrowserExtractor(BaseFeedExtractor):
    """Playwright-based LinkedIn feed extractor.

    Authentication modes (checked in priority order):
    1. session_cookie in config — injects li_at cookie into fresh browser
    2. browser_profile_path in config — copies Chrome profile to temp dir
    """

    def __init__(self, config: ExtractorConfig) -> None:
        super().__init__(config)
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright: Any = None
        self._temp_dir: Path | None = None

    @property
    def name(self) -> str:
        return "BrowserExtractor"

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def _ensure_browser(self) -> Page:
        """Start browser and return the active page."""
        if self._page and not self._page.is_closed():
            return self._page

        logger.info("Starting browser...")

        self._playwright = await async_playwright().start()
        logger.info("Playwright started")

        if self.config.session_cookie:
            await self._launch_with_cookie()
        elif self.config.browser_profile_path:
            await self._launch_with_profile()
        else:
            raise RuntimeError(
                "No authentication configured. "
                "Set LINKEDIN_SESSION_COOKIE or LINKEDIN_BROWSER_PROFILE_PATH."
            )

        logger.info("Browser page ready")
        return self._page  # type: ignore[return-value]

    async def _launch_with_cookie(self) -> None:
        """Launch a fresh browser and inject the li_at session cookie."""
        logger.info("Using cookie-based authentication")

        browser = await self._playwright.chromium.launch(
            channel="chrome",
            headless=self.config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # Create a context with a realistic user agent
        self._context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
        )

        # Inject li_at session cookie
        await self._context.add_cookies([
            {
                "name": "li_at",
                "value": self.config.session_cookie,
                "domain": ".linkedin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            },
        ])
        logger.info("Session cookie injected")

        self._page = await self._context.new_page()

        # Warm up: visit linkedin.com first to establish the session
        # This avoids redirect loops when going directly to /feed/
        logger.info("Warming up session on linkedin.com...")
        try:
            await self._page.goto(
                "https://www.linkedin.com/",
                wait_until="domcontentloaded",
                timeout=self.config.page_timeout * 1000,
            )
            await self._page.wait_for_timeout(2000)
            logger.info("Warm-up complete, current URL: %s", self._page.url.split("?")[0])
        except Exception as e:
            logger.warning("Warm-up navigation issue: %s - %s", type(e).__name__, e)

    async def _launch_with_profile(self) -> None:
        """Launch browser with a copy of Chrome profile files."""
        logger.info("Using profile-based authentication")

        session_config = SessionConfig(self.config)
        issues = session_config.validate()
        if issues:
            raise RuntimeError(
                "Session configuration is invalid: " + "; ".join(issues)
            )

        pw_args = session_config.get_playwright_args()
        source_dir = Path(pw_args["user_data_dir"])
        profile_name = session_config.profile_name

        # Copy session to temp dir to avoid Chrome profile lock
        self._temp_dir = _copy_profile_to_temp(source_dir, profile_name)
        logger.info("Using temp profile directory")

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._temp_dir),
            channel="chrome",
            headless=self.config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1280, "height": 900},
            timeout=60000,
        )

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    # ------------------------------------------------------------------
    # Navigation & auth check
    # ------------------------------------------------------------------

    async def _navigate_to_feed(self) -> bool:
        """Navigate to LinkedIn feed and verify authentication."""
        page = await self._ensure_browser()

        logger.info("Navigating to LinkedIn feed...")
        try:
            response = await page.goto(
                LINKEDIN_FEED_URL,
                wait_until="domcontentloaded",
                timeout=self.config.page_timeout * 1000,
            )
        except Exception as e:
            logger.error("Failed to navigate to feed: %s - %s", type(e).__name__, e)
            return False

        if response is None:
            logger.error("No response received from LinkedIn")
            return False

        current_url = page.url
        logger.info("Page loaded, URL: %s", current_url.split("?")[0])
        logger.info("HTTP status: %s", response.status)

        # Check if we were redirected to login
        if "/login" in current_url or "/authwall" in current_url or "/uas/" in current_url:
            logger.warning(
                "Redirected to login page - session is not authenticated. "
                "The session cookie may be expired. "
                "Get a fresh li_at cookie from your browser."
            )
            return False

        # Wait for page to settle
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            logger.debug("Network idle timeout - continuing")

        # Wait for feed content
        try:
            await page.wait_for_selector(
                "[role='main'], .scaffold-layout__main, main",
                timeout=15000,
            )
            logger.info("Main content area detected")
        except Exception:
            logger.warning("Could not find main content area within timeout")

        # Check authentication
        is_authenticated = await self._check_authentication(page)
        if is_authenticated:
            logger.info("Session appears authenticated")
        else:
            logger.warning("Session may not be authenticated")
            await self._save_debug_screenshot(page, "debug_auth_check.png")

        return is_authenticated

    async def _check_authentication(self, page: Page) -> bool:
        """Check for signs that the user is authenticated."""
        # Strategy 1: DOM indicators
        indicators = [
            "header.global-nav",
            "#global-nav",
            ".scaffold-layout__main",
            ".feed-identity-module",
            ".share-box-feed-entry__trigger",
            "div.feed-shared-update-v2",
            'img.global-nav__me-photo',
            "input.search-global-typeahead__input",
            ".application-outlet",
        ]

        for selector in indicators:
            try:
                element = await page.query_selector(selector)
                if element:
                    logger.info("Auth indicator found: %s", selector)
                    return True
            except Exception:
                continue

        # Strategy 2: URL check
        url = page.url.lower()
        if "linkedin.com/feed" in url:
            logger.info("Auth indicator: URL is feed page")
            return True

        # Strategy 3: Page title
        try:
            title = await page.title()
            if title and "feed" in title.lower():
                if "sign" not in title.lower() and "log" not in title.lower():
                    logger.info("Auth indicator: title '%s'", title)
                    return True
        except Exception:
            pass

        return False

    async def _save_debug_screenshot(self, page: Page, filename: str) -> None:
        """Save a debug screenshot to the output directory."""
        try:
            screenshot_path = Path("output") / filename
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path), full_page=False)
            logger.info("Debug screenshot saved to %s", screenshot_path)
            logger.info("Current URL: %s", page.url)
        except Exception as e:
            logger.debug("Could not save debug screenshot: %s", e)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Verify browser can start and reach LinkedIn."""
        try:
            page = await self._ensure_browser()
            return not page.is_closed()
        except Exception as e:
            logger.error("Health check failed: %s", type(e).__name__)
            return False

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    async def extract(self, max_posts: int | None = None) -> ExtractionResult:
        """Extract feed posts from LinkedIn."""
        started = datetime.utcnow()
        limit = max_posts or self.config.max_posts
        posts: list[FeedPost] = []
        errors: list[ExtractionError] = []

        try:
            is_authenticated = await self._navigate_to_feed()
            if not is_authenticated:
                return ExtractionResult(
                    errors=[
                        ExtractionError(
                            message=(
                                "Not authenticated - could not access feed. "
                                "Your li_at cookie may be expired. "
                                "Get a fresh one from your browser DevTools."
                            ),
                            error_type="authentication_error",
                        )
                    ],
                    extraction_started_at=started,
                    extraction_completed_at=datetime.utcnow(),
                    source_url=LINKEDIN_FEED_URL,
                    extractor_name=self.name,
                )

            page = self._page
            assert page is not None

            # Find post containers
            logger.info("Waiting for feed posts to appear...")
            post_selector = await self._find_post_selector(page)

            if not post_selector:
                await self._save_debug_screenshot(page, "debug_no_posts.png")
                return ExtractionResult(
                    errors=[
                        ExtractionError(
                            message="Feed posts did not render. Check output/debug_no_posts.png",
                            error_type="timeout_error",
                        )
                    ],
                    extraction_started_at=started,
                    extraction_completed_at=datetime.utcnow(),
                    source_url=LINKEDIN_FEED_URL,
                    extractor_name=self.name,
                )

            # Scroll to load more posts
            await self._scroll_to_load(page, post_selector, target_count=limit)

            # Find all post elements
            post_elements = await page.query_selector_all(post_selector)
            total_found = len(post_elements)
            logger.info("Found %d post elements on page", total_found)

            # Extract each post
            for i, element in enumerate(post_elements[:limit]):
                try:
                    post = await self._extract_single_post(element, i)
                    if post:
                        posts.append(post)
                        logger.info(
                            "Post %d: author=%s, text=%d chars",
                            i, post.author.name, len(post.content.text or ""),
                        )
                except Exception as e:
                    logger.warning("Failed to extract post %d: %s", i, e)
                    errors.append(
                        ExtractionError(
                            message=f"Post extraction failed: {type(e).__name__}: {e}",
                            error_type="extraction_error",
                            post_index=i,
                        )
                    )

        except Exception as e:
            errors.append(
                ExtractionError(
                    message=f"Unexpected error: {type(e).__name__}: {e}",
                    error_type="unexpected_error",
                )
            )

        completed = datetime.utcnow()
        return ExtractionResult(
            posts=posts,
            errors=errors,
            total_posts_found=len(posts) + len(errors),
            extraction_started_at=started,
            extraction_completed_at=completed,
            extraction_duration_seconds=(completed - started).total_seconds(),
            source_url=LINKEDIN_FEED_URL,
            extractor_name=self.name,
        )

    async def _find_post_selector(self, page: Page) -> str | None:
        """Try multiple selectors to find post containers."""
        for selector in [
            "div.feed-shared-update-v2",
            "[data-urn*='activity']",
            "div.occludable-update",
            ".scaffold-finite-scroll__content > div",
        ]:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                logger.info("Found posts using selector: %s", selector)
                return selector
            except Exception:
                logger.debug("Selector '%s' did not match", selector)
                continue
        return None

    async def _scroll_to_load(
        self, page: Page, post_selector: str, target_count: int
    ) -> None:
        """Scroll the page to trigger lazy loading of more posts."""
        for scroll_attempt in range(5):
            current_count = len(await page.query_selector_all(post_selector))
            if current_count >= target_count:
                logger.info("Have %d posts (target: %d), done scrolling", current_count, target_count)
                return

            logger.info("Scroll %d: have %d posts, scrolling...", scroll_attempt + 1, current_count)
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            await page.wait_for_timeout(2000)

    # ------------------------------------------------------------------
    # Single-post extraction
    # ------------------------------------------------------------------

    async def _extract_single_post(self, element: Any, index: int) -> FeedPost | None:
        """Extract data from a single post element."""
        # Author name
        author_name = await self._try_selectors(element, [
            ".update-components-actor__name span[aria-hidden='true']",
            ".update-components-actor__title span[aria-hidden='true']",
            ".update-components-actor__name",
            "a.update-components-actor__container-link span span",
        ])

        # Author headline
        author_headline = await self._try_selectors(element, [
            ".update-components-actor__description span[aria-hidden='true']",
            ".update-components-actor__subtitle span[aria-hidden='true']",
            ".update-components-actor__description",
        ])

        # Author profile URL
        author_url = await self._safe_attr(
            element,
            "a.update-components-actor__container-link,"
            "a.update-components-actor__meta-link",
            "href",
        )

        # Post text
        post_text = await self._try_selectors(element, [
            ".update-components-text span.break-words",
            ".update-components-text span[dir='ltr']",
            ".feed-shared-update-v2__description .update-components-text",
            ".feed-shared-text span[dir='ltr']",
            ".update-components-text",
        ], min_length=5)

        # Relative time
        relative_time = await self._try_selectors(element, [
            ".update-components-actor__sub-description span[aria-hidden='true']",
            "time.update-components-actor__sub-description",
            ".update-components-actor__sub-description",
        ])

        # Post URL
        post_url = await self._safe_attr(
            element,
            "a.update-components-actor__sub-description-link,"
            "a[data-urn]",
            "href",
        )

        # Engagement
        reaction_count = await self._parse_engagement_count(
            element,
            ".social-details-social-counts__reactions-count,"
            "span.social-details-social-counts__reactions-count",
        )
        comment_count = await self._parse_engagement_count(
            element,
            "button.social-details-social-counts__comments,"
            "li.social-details-social-counts__comments button",
        )

        # Post type
        post_type = PostType.ORIGINAL
        repost_text = await self._safe_text(element, ".update-components-header__text-view")
        if repost_text and "repost" in repost_text.lower():
            post_type = PostType.REPOST

        # Sponsored
        is_sponsored = False
        promo = await self._safe_text(element, ".update-components-actor__sub-description")
        if promo and "promoted" in promo.lower():
            is_sponsored = True

        if not author_name and not post_text:
            logger.debug("Post %d: no author or text found, skipping", index)
            return None

        return FeedPost(
            url=self._clean_url(post_url),
            author=Author(
                name=self._clean_text(author_name),
                headline=self._clean_text(author_headline),
                profile_url=self._clean_url(author_url),
            ),
            content=PostContent(text=self._clean_text(post_text)),
            engagement=Engagement(
                reaction_count=reaction_count,
                comment_count=comment_count,
            ),
            metadata=PostMetadata(
                post_type=post_type,
                relative_time=self._clean_text(relative_time),
                is_sponsored=is_sponsored,
            ),
            extracted_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _try_selectors(
        self, element: Any, selectors: list[str], min_length: int = 0
    ) -> str | None:
        """Try multiple selectors, return first matching text."""
        for selector in selectors:
            text = await self._safe_text(element, selector)
            if text and len(text) > min_length:
                return text
        return None

    async def _safe_text(self, element: Any, selector: str) -> str | None:
        """Safely extract text content from a child element."""
        try:
            child = await element.query_selector(selector)
            if child:
                text = await child.inner_text()
                return text.strip() if text else None
        except Exception:
            pass
        return None

    async def _safe_attr(self, element: Any, selector: str, attr: str) -> str | None:
        """Safely extract an attribute from a child element."""
        try:
            child = await element.query_selector(selector)
            if child:
                value = await child.get_attribute(attr)
                return value.strip() if value else None
        except Exception:
            pass
        return None

    async def _parse_engagement_count(self, element: Any, selector: str) -> int | None:
        """Parse an engagement count from text like '42', '1,234', '2K'."""
        text = await self._safe_text(element, selector)
        if not text:
            return None
        text = text.strip().lower().replace(",", "")
        try:
            if text.endswith("k"):
                return int(float(text[:-1]) * 1000)
            elif text.endswith("m"):
                return int(float(text[:-1]) * 1000000)
            else:
                digits = "".join(c for c in text if c.isdigit())
                return int(digits) if digits else None
        except (ValueError, IndexError):
            return None

    def _clean_text(self, text: str | None) -> str | None:
        """Clean extracted text: normalize whitespace, strip."""
        if not text:
            return None
        cleaned = " ".join(text.split())
        return cleaned if cleaned else None

    def _clean_url(self, url: str | None) -> str | None:
        """Clean a URL: ensure it's absolute, strip tracking params."""
        if not url:
            return None
        url = url.strip()
        if url.startswith("/"):
            url = f"https://www.linkedin.com{url}"
        if "?" in url:
            url = url.split("?")[0]
        return url

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Close browser and clean up all resources."""
        logger.info("Cleaning up browser resources...")
        try:
            if self._context:
                await self._context.close()
                self._context = None
                self._page = None
                logger.info("Browser context closed")
        except Exception as e:
            logger.warning("Error closing context: %s", type(e).__name__)

        try:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
                logger.info("Playwright stopped")
        except Exception as e:
            logger.warning("Error stopping Playwright: %s", type(e).__name__)

        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                logger.info("Temp profile directory cleaned up")
            except Exception as e:
                logger.warning("Could not clean temp dir: %s", e)
            self._temp_dir = None

        logger.info("Browser cleanup complete")


# ------------------------------------------------------------------
# Profile copy helper (for profile-based auth)
# ------------------------------------------------------------------

_SESSION_FILES = [
    "Cookies", "Cookies-journal",
    "Login Data", "Login Data-journal",
    "Web Data", "Web Data-journal",
    "Preferences", "Secure Preferences", "Local State",
]

_SESSION_DIRS = ["Local Storage", "Session Storage", "IndexedDB"]


def _copy_locked_file(src: Path, dst: Path) -> None:
    """Copy a file that may be locked by another process."""
    with open(src, "rb") as f_in:
        data = f_in.read()
    with open(dst, "wb") as f_out:
        f_out.write(data)


def _copy_profile_to_temp(source_user_data_dir: Path, profile_name: str) -> Path:
    """Copy critical Chrome session files to a temp directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="linkedin_extractor_"))
    source_profile = source_user_data_dir / profile_name
    dest_profile = temp_dir / profile_name
    dest_profile.mkdir(parents=True, exist_ok=True)

    logger.info("Copying session files to temporary profile...")

    local_state = source_user_data_dir / "Local State"
    if local_state.exists():
        try:
            _copy_locked_file(local_state, temp_dir / "Local State")
        except (PermissionError, OSError) as e:
            logger.warning("Could not copy Local State: %s", e)

    for filename in _SESSION_FILES:
        src = source_profile / filename
        if src.exists():
            try:
                _copy_locked_file(src, dest_profile / filename)
                logger.debug("Copied: %s", filename)
            except (PermissionError, OSError) as e:
                logger.warning("Could not copy %s: %s", filename, e)

    for dirname in _SESSION_DIRS:
        src = source_profile / dirname
        if src.exists() and src.is_dir():
            try:
                shutil.copytree(
                    src, dest_profile / dirname,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.lock", "LOCK"),
                )
                logger.debug("Copied directory: %s", dirname)
            except (PermissionError, OSError) as e:
                logger.warning("Could not copy directory %s: %s", dirname, e)

    logger.info("Session files copied to temp profile")
    return temp_dir
