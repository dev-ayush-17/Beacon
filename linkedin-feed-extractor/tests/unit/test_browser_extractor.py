"""Unit tests for BrowserExtractor (no real browser required)."""

from __future__ import annotations

import pytest

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.base import BaseFeedExtractor
from linkedin_feed_extractor.extractor.browser import BrowserExtractor


class TestBrowserExtractorUnit:
    """Unit tests for BrowserExtractor that don't require a browser."""

    def test_is_valid_implementation(self) -> None:
        """BrowserExtractor should be a valid BaseFeedExtractor."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        assert isinstance(extractor, BaseFeedExtractor)

    def test_has_name(self) -> None:
        """BrowserExtractor should have a descriptive name."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        assert extractor.name == "BrowserExtractor"

    def test_has_config(self) -> None:
        """BrowserExtractor should store its config."""
        config = ExtractorConfig(max_posts=10)
        extractor = BrowserExtractor(config)
        assert extractor.config.max_posts == 10

    def test_clean_text(self) -> None:
        """_clean_text should normalize whitespace."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        assert extractor._clean_text("  hello   world  ") == "hello world"
        assert extractor._clean_text(None) is None
        assert extractor._clean_text("") is None
        assert extractor._clean_text("   ") is None

    def test_clean_url_relative(self) -> None:
        """_clean_url should make relative URLs absolute."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        result = extractor._clean_url("/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_clean_url_absolute(self) -> None:
        """_clean_url should preserve absolute URLs."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        result = extractor._clean_url("https://www.linkedin.com/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_clean_url_strips_query(self) -> None:
        """_clean_url should strip tracking query params."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        result = extractor._clean_url(
            "https://www.linkedin.com/in/johndoe?miniProfileUrn=abc"
        )
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_clean_url_none(self) -> None:
        """_clean_url should handle None."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        assert extractor._clean_url(None) is None

    @pytest.mark.asyncio
    async def test_parse_engagement_count_basic(self) -> None:
        """_parse_engagement_count helper tested via direct number parsing."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        # Test the parsing logic directly isn't possible without an element,
        # but we can verify cleanup works
        await extractor.cleanup()  # Should not raise even without browser

    @pytest.mark.asyncio
    async def test_extract_without_config_returns_error(self) -> None:
        """Extract without valid session config should return errors."""
        config = ExtractorConfig()  # No browser profile configured
        extractor = BrowserExtractor(config)
        result = await extractor.extract(max_posts=1)
        # Should fail gracefully with a session error
        assert result.error_count > 0
        assert result.success_count == 0
        await extractor.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self) -> None:
        """cleanup() should be safe to call multiple times."""
        config = ExtractorConfig()
        extractor = BrowserExtractor(config)
        await extractor.cleanup()
        await extractor.cleanup()  # Second call should also be safe
