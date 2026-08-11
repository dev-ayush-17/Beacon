"""Browser-based feed extractor using Playwright.

Uses the user's existing Chrome browser profile for authenticated
access to the LinkedIn feed. No credentials are stored or logged.

SECURITY:
- Session reuse only (no cookie extraction)
- Never logs cookies, tokens, or session data
- Diagnostic logging limited to page state (not content)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.base import BaseFeedExtractor
from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    ExtractionError,
    ExtractionResult,
    FeedPost,
    Media,
    PostContent,
    PostMetadata,
    PostType,
)
from linkedin_feed_extractor.session import SessionConfig, SessionError

logger = logging.getLogger(__name__)

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"


class BrowserExtractor(BaseFeedExtractor):
    """Playwright-based LinkedIn feed extractor.

    Launches Chrome with the user's existing profile to access
    LinkedIn through their authenticated session.
    """

    def __init__(self, config: ExtractorConfig) -> None:
        super().__init__(config)
        self._session_config = SessionConfig(config)
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright: Any = None

    @property
    def name(self) -> str:
        return "BrowserExtractor"

    async def _ensure_browser(self) -> Page:
        """Start browser and navigate to feed if not already running.

        Returns the active page instance.
        """
        if self._page and not self._page.is_closed():
            return self._page

        logger.info("Starting browser...")

        # Validate session configuration
        issues = self._session_config.validate()
        if issues:
            raise SessionError(
                "Session configuration is invalid: " + "; ".join(issues)
            )

        pw_args = self._session_config.get_playwright_args()

        self._playwright = await async_playwright().start()
        logger.info("Playwright started")

        # Launch persistent context with user's Chrome profile
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=pw_args["user_data_dir"],
            channel=pw_args.get("channel", "chrome"),
            headless=bool(pw_args.get("headless", False)),
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 900},
            timeout=self.config.page_timeout * 1000,
        )
        logger.info("Browser context created with user profile")

        # Use the first page or create a new one
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        logger.info("Browser page ready")
        return self._page

    async def _navigate_to_feed(self) -> bool:
        """Navigate to LinkedIn feed and verify authentication.

        Returns True if the feed page loaded with authentication.
        Returns False if redirected to login or blocked.
        """
        page = await self._ensure_browser()

        logger.info("Navigating to LinkedIn feed...")
        try:
            response = await page.goto(
                LINKEDIN_FEED_URL,
                wait_until="domcontentloaded",
                timeout=self.config.page_timeout * 1000,
            )
        except Exception as e:
            logger.error("Failed to navigate to feed: %s", type(e).__name__)
            return False

        if response is None:
            logger.error("No response received from LinkedIn")
            return False

        current_url = page.url
        logger.info("Page loaded, URL: %s", current_url.split("?")[0])
        logger.info("HTTP status: %s", response.status)

        # Check if we were redirected to login
        if "/login" in current_url or "/authwall" in current_url:
            logger.warning(
                "Redirected to login page — session is not authenticated. "
                "Please log into LinkedIn in Chrome and try again."
            )
            return False

        # Check for the feed page markers
        title = await page.title()
        logger.info("Page title: %s", title)

        # Wait briefly for feed content to render
        try:
            await page.wait_for_selector(
                "[role='main']",
                timeout=10000,
            )
            logger.info("Feed main content area detected")
        except Exception:
            logger.warning("Could not find main content area within timeout")

        # Check for authentication indicators
        is_authenticated = await self._check_authentication(page)
        if is_authenticated:
            logger.info("Session appears authenticated")
        else:
            logger.warning("Session may not be authenticated")

        return is_authenticated

    async def _check_authentication(self, page: Page) -> bool:
        """Check for signs that the user is authenticated.

        Looks for common authenticated-user indicators without
        reading any personal data.
        """
        indicators = [
            # Global nav bar (present when logged in)
            "header.global-nav",
            "#global-nav",
            # Profile/me icon
            "[data-control-name='identity_welcome_message']",
            'img.global-nav__me-photo',
            ".feed-identity-module",
            # Feed-specific elements
            ".scaffold-layout__main",
            "div.feed-shared-update-v2",
            ".share-box-feed-entry__trigger",
        ]

        for selector in indicators:
            try:
                element = await page.query_selector(selector)
                if element:
                    logger.info("Auth indicator found: %s", selector)
                    return True
            except Exception:
                continue

        return False

    async def health_check(self) -> bool:
        """Verify browser can start and reach LinkedIn."""
        try:
            issues = self._session_config.validate()
            if issues:
                logger.warning("Session config issues: %s", "; ".join(issues))
                return False

            page = await self._ensure_browser()
            return not page.is_closed()
        except Exception as e:
            logger.error("Health check failed: %s", type(e).__name__)
            return False

    async def extract(self, max_posts: int | None = None) -> ExtractionResult:
        """Extract feed posts from LinkedIn.

        This is the main extraction method. It:
        1. Opens the browser with authenticated session
        2. Navigates to the feed
        3. Locates individual posts
        4. Extracts data from each post
        5. Returns structured results
        """
        started = datetime.utcnow()
        limit = max_posts or self.config.max_posts
        posts: list[FeedPost] = []
        errors: list[ExtractionError] = []

        try:
            # Navigate to feed
            is_authenticated = await self._navigate_to_feed()
            if not is_authenticated:
                return ExtractionResult(
                    errors=[
                        ExtractionError(
                            message="Not authenticated — could not access feed",
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

            # Wait for feed posts to render
            logger.info("Waiting for feed posts to appear...")
            try:
                await page.wait_for_selector(
                    "div.feed-shared-update-v2",
                    timeout=15000,
                )
            except Exception:
                logger.warning("Feed posts did not appear within timeout")
                return ExtractionResult(
                    errors=[
                        ExtractionError(
                            message="Feed posts did not render within timeout",
                            error_type="timeout_error",
                        )
                    ],
                    extraction_started_at=started,
                    extraction_completed_at=datetime.utcnow(),
                    source_url=LINKEDIN_FEED_URL,
                    extractor_name=self.name,
                )

            # Scroll to load more posts if needed
            await self._scroll_to_load(page, target_count=limit)

            # Find all post containers
            post_elements = await page.query_selector_all(
                "div.feed-shared-update-v2"
            )
            total_found = len(post_elements)
            logger.info("Found %d post elements on page", total_found)

            # Extract each post
            for i, element in enumerate(post_elements[:limit]):
                try:
                    post = await self._extract_single_post(element, i)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.warning(
                        "Failed to extract post %d: %s", i, type(e).__name__
                    )
                    errors.append(
                        ExtractionError(
                            message=f"Failed to extract post: {type(e).__name__}",
                            error_type="extraction_error",
                            post_index=i,
                        )
                    )

        except SessionError as e:
            errors.append(
                ExtractionError(
                    message=str(e),
                    error_type="session_error",
                )
            )
        except Exception as e:
            errors.append(
                ExtractionError(
                    message=f"Unexpected error: {type(e).__name__}: {e}",
                    error_type="unexpected_error",
                )
            )

        return ExtractionResult(
            posts=posts,
            errors=errors,
            total_posts_found=len(posts) + len(errors),
            extraction_started_at=started,
            extraction_completed_at=datetime.utcnow(),
            source_url=LINKEDIN_FEED_URL,
            extractor_name=self.name,
        )

    async def _scroll_to_load(self, page: Page, target_count: int) -> None:
        """Scroll the page to trigger lazy loading of more posts."""
        for scroll_attempt in range(3):
            current_count = len(
                await page.query_selector_all("div.feed-shared-update-v2")
            )
            if current_count >= target_count:
                logger.info(
                    "Have %d posts (target: %d), stopping scroll",
                    current_count,
                    target_count,
                )
                return

            logger.info(
                "Scroll %d: have %d posts, scrolling for more...",
                scroll_attempt + 1,
                current_count,
            )
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            await page.wait_for_timeout(2000)

    async def _extract_single_post(
        self, element: Any, index: int
    ) -> FeedPost | None:
        """Extract data from a single post element.

        Returns a FeedPost or None if the post couldn't be parsed.
        """
        # Extract author name
        author_name = await self._safe_text(
            element,
            ".update-components-actor__name span[aria-hidden='true'],"
            ".update-components-actor__title span[aria-hidden='true']",
        )

        # Extract author headline
        author_headline = await self._safe_text(
            element,
            ".update-components-actor__description span[aria-hidden='true'],"
            ".update-components-actor__subtitle span[aria-hidden='true']",
        )

        # Extract author profile URL
        author_url = await self._safe_attr(
            element,
            "a.update-components-actor__container-link,"
            "a.update-components-actor__meta-link",
            "href",
        )

        # Extract post text
        post_text = await self._safe_text(
            element,
            ".feed-shared-update-v2__description .update-components-text span[dir='ltr'],"
            ".update-components-text .break-words span[dir='ltr'],"
            ".feed-shared-text span[dir='ltr'],"
            ".update-components-text span.break-words",
        )

        # Extract relative time
        relative_time = await self._safe_text(
            element,
            ".update-components-actor__sub-description span[aria-hidden='true'],"
            "time.update-components-actor__sub-description",
        )

        # Extract post URL from the timestamp link or overflow menu
        post_url = await self._safe_attr(
            element,
            "a.update-components-actor__sub-description-link,"
            "a[data-urn]",
            "href",
        )

        # Extract engagement counts
        reaction_count = await self._parse_engagement_count(
            element,
            ".social-details-social-counts__reactions-count,"
            "button.social-details-social-counts__count-value",
        )
        comment_count = await self._parse_engagement_count(
            element,
            "button.social-details-social-counts__comments,"
            "[data-control-name='comments_count']",
        )

        # Detect post type
        post_type = PostType.ORIGINAL
        repost_indicator = await self._safe_text(
            element, ".update-components-header__text-view"
        )
        if repost_indicator and "repost" in repost_indicator.lower():
            post_type = PostType.REPOST

        # Build the FeedPost
        if not author_name and not post_text:
            logger.info("Post %d: no author or text found, skipping", index)
            return None

        post = FeedPost(
            url=self._clean_url(post_url),
            author=Author(
                name=self._clean_text(author_name),
                headline=self._clean_text(author_headline),
                profile_url=self._clean_url(author_url),
            ),
            content=PostContent(
                text=self._clean_text(post_text),
            ),
            engagement=Engagement(
                reaction_count=reaction_count,
                comment_count=comment_count,
            ),
            metadata=PostMetadata(
                post_type=post_type,
                relative_time=self._clean_text(relative_time),
            ),
            extracted_at=datetime.utcnow(),
        )
        return post

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

    async def _safe_attr(
        self, element: Any, selector: str, attr: str
    ) -> str | None:
        """Safely extract an attribute from a child element."""
        try:
            child = await element.query_selector(selector)
            if child:
                value = await child.get_attribute(attr)
                return value.strip() if value else None
        except Exception:
            pass
        return None

    async def _parse_engagement_count(
        self, element: Any, selector: str
    ) -> int | None:
        """Parse an engagement count from text like '42', '1,234', '2K'."""
        text = await self._safe_text(element, selector)
        if not text:
            return None

        text = text.strip().lower().replace(",", "")

        # Handle abbreviated counts
        try:
            if text.endswith("k"):
                return int(float(text[:-1]) * 1000)
            elif text.endswith("m"):
                return int(float(text[:-1]) * 1000000)
            else:
                # Extract just the digits
                digits = "".join(c for c in text if c.isdigit())
                return int(digits) if digits else None
        except (ValueError, IndexError):
            return None

    def _clean_text(self, text: str | None) -> str | None:
        """Clean extracted text: normalize whitespace, strip."""
        if not text:
            return None
        # Normalize whitespace
        cleaned = " ".join(text.split())
        return cleaned if cleaned else None

    def _clean_url(self, url: str | None) -> str | None:
        """Clean a URL: ensure it's absolute, strip tracking params."""
        if not url:
            return None
        url = url.strip()
        if url.startswith("/"):
            url = f"https://www.linkedin.com{url}"
        # Strip query parameters for cleaner URLs
        if "?" in url:
            url = url.split("?")[0]
        return url

    async def cleanup(self) -> None:
        """Close browser and clean up Playwright resources."""
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

        logger.info("Browser cleanup complete")
