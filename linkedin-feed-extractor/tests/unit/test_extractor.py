"""Tests for the extractor contract and mock implementation."""

from __future__ import annotations

import pytest

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.base import BaseFeedExtractor
from linkedin_feed_extractor.extractor.mock import MockExtractor
from linkedin_feed_extractor.models import ExtractionResult, FeedPost


@pytest.fixture
def config() -> ExtractorConfig:
    """Default test configuration."""
    return ExtractorConfig(max_posts=5)


@pytest.fixture
def mock_extractor(config: ExtractorConfig) -> MockExtractor:
    """Standard mock extractor."""
    return MockExtractor(config)


class TestExtractorContract:
    """Tests that verify the extractor contract is properly defined."""

    def test_base_extractor_is_abstract(self) -> None:
        """BaseFeedExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseFeedExtractor(ExtractorConfig())  # type: ignore[abstract]

    def test_mock_extractor_is_valid_implementation(
        self, mock_extractor: MockExtractor
    ) -> None:
        """MockExtractor is a valid BaseFeedExtractor implementation."""
        assert isinstance(mock_extractor, BaseFeedExtractor)

    def test_extractor_has_name(self, mock_extractor: MockExtractor) -> None:
        """Extractor must have a name property."""
        assert isinstance(mock_extractor.name, str)
        assert len(mock_extractor.name) > 0

    def test_extractor_has_config(self, mock_extractor: MockExtractor) -> None:
        """Extractor must store its configuration."""
        assert mock_extractor.config is not None
        assert isinstance(mock_extractor.config, ExtractorConfig)


class TestMockExtractor:
    """Tests for the MockExtractor implementation."""

    @pytest.mark.asyncio
    async def test_extract_returns_result(
        self, mock_extractor: MockExtractor
    ) -> None:
        """extract() should return an ExtractionResult."""
        result = await mock_extractor.extract()
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_extract_returns_posts(
        self, mock_extractor: MockExtractor
    ) -> None:
        """extract() should return the configured number of posts."""
        result = await mock_extractor.extract()
        assert len(result.posts) == 5
        assert result.success_count == 5

    @pytest.mark.asyncio
    async def test_extract_posts_are_valid(
        self, mock_extractor: MockExtractor
    ) -> None:
        """Extracted posts should be valid FeedPost instances."""
        result = await mock_extractor.extract()
        for post in result.posts:
            assert isinstance(post, FeedPost)
            assert post.id is not None
            assert post.author.name is not None
            assert post.content.text is not None

    @pytest.mark.asyncio
    async def test_extract_respects_max_posts_override(
        self, mock_extractor: MockExtractor
    ) -> None:
        """extract(max_posts=N) should override config."""
        result = await mock_extractor.extract(max_posts=2)
        assert len(result.posts) == 2

    @pytest.mark.asyncio
    async def test_extract_has_metadata(
        self, mock_extractor: MockExtractor
    ) -> None:
        """ExtractionResult should have metadata populated."""
        result = await mock_extractor.extract()
        assert result.extractor_name == "MockExtractor"
        assert result.source_url is not None
        assert result.extraction_started_at is not None
        assert result.extraction_completed_at is not None

    @pytest.mark.asyncio
    async def test_extract_posts_have_unique_ids(
        self, mock_extractor: MockExtractor
    ) -> None:
        """Each post should have a unique ID."""
        result = await mock_extractor.extract()
        ids = [p.id for p in result.posts]
        assert len(ids) == len(set(ids)), "Post IDs are not unique"

    @pytest.mark.asyncio
    async def test_health_check_default(
        self, mock_extractor: MockExtractor
    ) -> None:
        """Default health check should return True."""
        assert await mock_extractor.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_can_be_unhealthy(
        self, config: ExtractorConfig
    ) -> None:
        """Health check should be controllable for testing."""
        extractor = MockExtractor(config)
        extractor.set_healthy(False)
        assert await extractor.health_check() is False

    @pytest.mark.asyncio
    async def test_cleanup_is_safe(self, mock_extractor: MockExtractor) -> None:
        """cleanup() should be callable without error."""
        await mock_extractor.cleanup()  # Should not raise

    @pytest.mark.asyncio
    async def test_simulated_failure(self, config: ExtractorConfig) -> None:
        """Simulated failure should return errors, no posts."""
        extractor = MockExtractor(
            config,
            simulate_failure=True,
            failure_message="Test failure",
        )
        result = await extractor.extract()
        assert result.success_count == 0
        assert result.error_count == 1
        assert result.errors[0].message == "Test failure"

    @pytest.mark.asyncio
    async def test_simulated_partial_failure(
        self, config: ExtractorConfig
    ) -> None:
        """Partial failure should return some posts and some errors."""
        extractor = MockExtractor(
            config,
            error_at_indices=[1, 3],
        )
        result = await extractor.extract()
        assert result.success_count == 3  # 5 total - 2 errors
        assert result.error_count == 2
        assert result.errors[0].post_index == 1
        assert result.errors[1].post_index == 3

    @pytest.mark.asyncio
    async def test_extract_more_than_samples(
        self, config: ExtractorConfig
    ) -> None:
        """Requesting more posts than samples should cycle."""
        extractor = MockExtractor(ExtractorConfig(max_posts=10))
        result = await extractor.extract()
        assert len(result.posts) == 10
        # All should have unique IDs even when cycling
        ids = [p.id for p in result.posts]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_extraction_result_success_rate(
        self, config: ExtractorConfig
    ) -> None:
        """Success rate should calculate correctly."""
        extractor = MockExtractor(config, error_at_indices=[0])
        result = await extractor.extract()
        assert result.success_rate == 80.0  # 4 out of 5
