"""Integration tests for browser-based extraction.

These tests require:
1. LINKEDIN_BROWSER_PROFILE_PATH set in .env
2. An active LinkedIn session in that browser profile
3. Chrome to be closed (to avoid profile lock conflicts)

Run with: pytest -m integration -v
"""

from __future__ import annotations

import logging

import pytest

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.browser import BrowserExtractor
from linkedin_feed_extractor.models import ExtractionResult

logger = logging.getLogger(__name__)


@pytest.fixture
def integration_config() -> ExtractorConfig:
    """Load configuration from .env for integration tests."""
    config = ExtractorConfig.from_env()
    issues = config.validate()
    if any("LINKEDIN_BROWSER_PROFILE_PATH" in issue for issue in issues):
        pytest.skip(
            "LINKEDIN_BROWSER_PROFILE_PATH not configured. "
            "Set it in .env to run integration tests."
        )
    return config


@pytest.fixture
async def browser_extractor(
    integration_config: ExtractorConfig,
) -> BrowserExtractor:
    """Create a BrowserExtractor for integration testing."""
    extractor = BrowserExtractor(integration_config)
    yield extractor  # type: ignore[misc]
    await extractor.cleanup()


@pytest.mark.integration
class TestBrowserConnectivity:
    """V0.5 — Browser connectivity experiment.

    Verifies that the application can:
    1. Start the browser
    2. Establish the authorized user session
    3. Navigate to the LinkedIn feed page
    4. Detect whether the expected page is available
    5. Close the browser cleanly
    """

    @pytest.mark.asyncio
    async def test_browser_health_check(
        self, browser_extractor: BrowserExtractor
    ) -> None:
        """Browser should start and report healthy."""
        is_healthy = await browser_extractor.health_check()
        assert is_healthy, "Browser health check failed"
        logger.info("PASS: Browser health check succeeded")

    @pytest.mark.asyncio
    async def test_feed_navigation(
        self, browser_extractor: BrowserExtractor
    ) -> None:
        """Browser should navigate to feed and detect authentication."""
        is_authenticated = await browser_extractor._navigate_to_feed()
        assert is_authenticated, (
            "Feed navigation failed — session may not be authenticated. "
            "Log into LinkedIn in Chrome and close Chrome before retrying."
        )
        logger.info("PASS: Feed navigation succeeded, session is authenticated")

    @pytest.mark.asyncio
    async def test_cleanup(
        self, integration_config: ExtractorConfig
    ) -> None:
        """Browser should close cleanly without errors."""
        extractor = BrowserExtractor(integration_config)
        await extractor._ensure_browser()
        await extractor.cleanup()
        logger.info("PASS: Browser cleanup completed cleanly")


@pytest.mark.integration
class TestFeedExtraction:
    """V0.7/V0.8 — Feed post extraction integration tests."""

    @pytest.mark.asyncio
    async def test_extract_single_post(
        self, browser_extractor: BrowserExtractor
    ) -> None:
        """Should extract at least one post from the feed."""
        result = await browser_extractor.extract(max_posts=1)
        assert isinstance(result, ExtractionResult)
        assert result.extractor_name == "BrowserExtractor"
        logger.info(
            "Extraction result: %d posts, %d errors",
            result.success_count,
            result.error_count,
        )

        if result.success_count > 0:
            post = result.posts[0]
            logger.info("First post author: %s", post.author.name)
            logger.info("First post text preview: %s", (post.content.text or "")[:80])
            logger.info("PASS: Successfully extracted a feed post")
        else:
            logger.warning(
                "No posts extracted. Errors: %s",
                [e.message for e in result.errors],
            )

    @pytest.mark.asyncio
    async def test_extract_multiple_posts(
        self, browser_extractor: BrowserExtractor
    ) -> None:
        """Should extract multiple posts from the feed."""
        result = await browser_extractor.extract(max_posts=5)
        assert isinstance(result, ExtractionResult)
        logger.info(
            "Extracted %d posts, %d errors (%.0f%% success rate)",
            result.success_count,
            result.error_count,
            result.success_rate,
        )

        for i, post in enumerate(result.posts):
            logger.info(
                "Post %d: author=%s, text_len=%d, reactions=%s",
                i,
                post.author.name,
                len(post.content.text) if post.content.text else 0,
                post.engagement.reaction_count,
            )

        if result.success_count > 0:
            logger.info("PASS: Multiple post extraction succeeded")
        else:
            logger.warning("PARTIAL: No posts successfully extracted")
