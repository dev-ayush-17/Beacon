"""Tests for the normalization layer."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    FeedPost,
    PostContent,
    PostMetadata,
    PostType,
)
from linkedin_feed_extractor.normalizer import FeedNormalizer


@pytest.fixture
def normalizer() -> FeedNormalizer:
    """Create a FeedNormalizer instance."""
    return FeedNormalizer()


class TestNormalizeText:
    """Tests for text normalization."""

    def test_none_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text(None) is None

    def test_empty_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("") is None

    def test_whitespace_only_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("   \t\n  ") is None

    def test_strips_leading_trailing(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("  hello  ") == "hello"

    def test_collapses_whitespace(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("hello   world") == "hello world"

    def test_collapses_newlines(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("hello\n\nworld") == "hello world"

    def test_removes_zero_width_chars(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("hello\u200bworld") == "helloworld"

    def test_normal_text_unchanged(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_text("Hello, World!") == "Hello, World!"


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_none_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_url(None) is None

    def test_empty_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_url("") is None

    def test_relative_url_made_absolute(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.normalize_url("/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_absolute_url_unchanged(self, normalizer: FeedNormalizer) -> None:
        url = "https://www.linkedin.com/in/johndoe"
        assert normalizer.normalize_url(url) == url

    def test_strips_query_params(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.normalize_url(
            "https://www.linkedin.com/in/johndoe?miniProfileUrn=abc&trk=xyz"
        )
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_strips_fragment(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.normalize_url(
            "https://www.linkedin.com/feed/#section"
        )
        assert result == "https://www.linkedin.com/feed"

    def test_strips_trailing_slash(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.normalize_url(
            "https://www.linkedin.com/in/johndoe/"
        )
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_strips_whitespace(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.normalize_url("  /in/johndoe  ")
        assert result == "https://www.linkedin.com/in/johndoe"


class TestNormalizeEngagementCount:
    """Tests for engagement count parsing."""

    def test_none_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count(None) is None

    def test_empty_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("") is None

    def test_plain_number(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("42") == 42

    def test_with_comma(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("1,234") == 1234

    def test_abbreviated_k(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("2K") == 2000

    def test_abbreviated_k_decimal(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("1.5K") == 1500

    def test_abbreviated_m(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("2M") == 2000000

    def test_with_text_comments(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("23 comments") == 23

    def test_with_text_reposts(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("8 reposts") == 8

    def test_with_text_reactions(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("100 reactions") == 100

    def test_zero(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("0") == 0

    def test_whitespace_handling(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.normalize_engagement_count("  42  ") == 42


class TestParseRelativeTime:
    """Tests for relative time parsing."""

    def test_none_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.parse_relative_time(None) is None

    def test_empty_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.parse_relative_time("") is None

    def test_just_now(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("Just now")
        assert result is not None
        assert abs((datetime.utcnow() - result).total_seconds()) < 5

    def test_hours(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("2h")
        assert result is not None
        expected = datetime.utcnow() - timedelta(hours=2)
        assert abs((expected - result).total_seconds()) < 5

    def test_days(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("1d")
        assert result is not None
        expected = datetime.utcnow() - timedelta(days=1)
        assert abs((expected - result).total_seconds()) < 5

    def test_weeks(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("3w")
        assert result is not None
        expected = datetime.utcnow() - timedelta(weeks=3)
        assert abs((expected - result).total_seconds()) < 5

    def test_months(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("2mo")
        assert result is not None
        # 2 months ~ 60 days; allow 60 seconds tolerance for test execution
        delta = abs((datetime.utcnow() - result).total_seconds())
        expected_seconds = 60 * 24 * 3600  # 60 days in seconds
        assert abs(delta - expected_seconds) < 60

    def test_years(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("1yr")
        assert result is not None
        # 1 year ~ 365 days; allow 60 seconds tolerance
        delta = abs((datetime.utcnow() - result).total_seconds())
        expected_seconds = 365 * 24 * 3600
        assert abs(delta - expected_seconds) < 60

    def test_minutes(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("30m")
        assert result is not None
        expected = datetime.utcnow() - timedelta(minutes=30)
        assert abs((expected - result).total_seconds()) < 5

    def test_invalid_returns_none(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.parse_relative_time("yesterday") is None

    def test_seconds(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.parse_relative_time("45s")
        assert result is not None
        expected = datetime.utcnow() - timedelta(seconds=45)
        assert abs((expected - result).total_seconds()) < 5


class TestExtractHashtags:
    """Tests for hashtag extraction."""

    def test_none_returns_empty(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.extract_hashtags(None) == []

    def test_no_hashtags(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.extract_hashtags("Just a normal post") == []

    def test_single_hashtag(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.extract_hashtags("Check this out #python")
        assert result == ["#python"]

    def test_multiple_hashtags(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.extract_hashtags("Love #python and #rust")
        assert "#python" in result
        assert "#rust" in result


class TestExtractMentions:
    """Tests for mention extraction."""

    def test_none_returns_empty(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.extract_mentions(None) == []

    def test_no_mentions(self, normalizer: FeedNormalizer) -> None:
        assert normalizer.extract_mentions("Just a normal post") == []

    def test_single_mention(self, normalizer: FeedNormalizer) -> None:
        result = normalizer.extract_mentions("Thanks @johndoe!")
        assert result == ["@johndoe"]


class TestNormalizePost:
    """Tests for full post normalization."""

    def test_normalize_cleans_text(self, normalizer: FeedNormalizer) -> None:
        """Post text should be cleaned."""
        post = FeedPost(
            content=PostContent(text="  Hello   World  \n\n #python  "),
        )
        result = normalizer.normalize_post(post)
        assert result.content.text == "Hello World #python"

    def test_normalize_extracts_hashtags(self, normalizer: FeedNormalizer) -> None:
        """Hashtags should be extracted from text."""
        post = FeedPost(
            content=PostContent(text="Love #python and #opensource"),
        )
        result = normalizer.normalize_post(post)
        assert "#python" in result.content.hashtags
        assert "#opensource" in result.content.hashtags

    def test_normalize_preserves_existing_hashtags(
        self, normalizer: FeedNormalizer
    ) -> None:
        """Existing hashtags should be preserved over extraction."""
        post = FeedPost(
            content=PostContent(
                text="Love #python",
                hashtags=["#existing"],
            ),
        )
        result = normalizer.normalize_post(post)
        assert result.content.hashtags == ["#existing"]

    def test_normalize_cleans_urls(self, normalizer: FeedNormalizer) -> None:
        """URLs should be normalized."""
        post = FeedPost(
            url="/feed/update/123?trk=abc",
            author=Author(profile_url="/in/johndoe?miniProfile=xyz"),
        )
        result = normalizer.normalize_post(post)
        assert result.url == "https://www.linkedin.com/feed/update/123"
        assert result.author.profile_url == "https://www.linkedin.com/in/johndoe"

    def test_normalize_parses_relative_time(
        self, normalizer: FeedNormalizer
    ) -> None:
        """Relative time should be parsed into timestamp."""
        post = FeedPost(
            metadata=PostMetadata(relative_time="2h"),
        )
        result = normalizer.normalize_post(post)
        assert result.metadata.timestamp is not None
        expected = datetime.utcnow() - timedelta(hours=2)
        assert abs((expected - result.metadata.timestamp).total_seconds()) < 5

    def test_normalize_preserves_existing_timestamp(
        self, normalizer: FeedNormalizer
    ) -> None:
        """Existing timestamp should not be overwritten."""
        existing = datetime(2026, 1, 1, 12, 0, 0)
        post = FeedPost(
            metadata=PostMetadata(
                relative_time="2h",
                timestamp=existing,
            ),
        )
        result = normalizer.normalize_post(post)
        assert result.metadata.timestamp == existing

    def test_normalize_preserves_metadata(self, normalizer: FeedNormalizer) -> None:
        """Post metadata should be preserved through normalization."""
        post = FeedPost(
            id="test-123",
            author=Author(name="Test User", is_company=True),
            metadata=PostMetadata(
                post_type=PostType.ARTICLE,
                is_sponsored=True,
                visibility="Public",
            ),
        )
        result = normalizer.normalize_post(post)
        assert result.id == "test-123"
        assert result.author.name == "Test User"
        assert result.author.is_company is True
        assert result.metadata.post_type == PostType.ARTICLE
        assert result.metadata.is_sponsored is True

    def test_normalize_posts_list(self, normalizer: FeedNormalizer) -> None:
        """normalize_posts should handle a list."""
        posts = [
            FeedPost(content=PostContent(text="  Post 1  ")),
            FeedPost(content=PostContent(text="  Post 2  ")),
        ]
        results = normalizer.normalize_posts(posts)
        assert len(results) == 2
        assert results[0].content.text == "Post 1"
        assert results[1].content.text == "Post 2"
