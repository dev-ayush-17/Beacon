"""Tests for domain models."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    ExtractionError,
    ExtractionResult,
    FeedPost,
    Media,
    MediaType,
    PostContent,
    PostMetadata,
    PostType,
)


class TestAuthor:
    """Test suite for Author model."""

    def test_default_author(self) -> None:
        """Author with no fields should be valid."""
        author = Author()
        assert author.name is None
        assert author.headline is None
        assert author.profile_url is None
        assert author.is_company is False

    def test_full_author(self) -> None:
        """Author with all fields populated."""
        author = Author(
            name="Jane Developer",
            headline="Software Engineer at TechCo",
            profile_url="https://linkedin.com/in/janedev",
            profile_image_url="https://media.linkedin.com/image.jpg",
            connection_degree="1st",
            is_company=False,
        )
        assert author.name == "Jane Developer"
        assert author.connection_degree == "1st"

    def test_company_author(self) -> None:
        """Author can represent a company page."""
        author = Author(name="TechCo Inc.", is_company=True)
        assert author.is_company is True

    def test_author_serialization(self) -> None:
        """Author should serialize to dict cleanly."""
        author = Author(name="Test User")
        data = author.model_dump()
        assert data["name"] == "Test User"
        assert data["is_company"] is False


class TestMedia:
    """Test suite for Media model."""

    def test_default_media(self) -> None:
        """Default media should have unknown type."""
        media = Media()
        assert media.media_type == MediaType.UNKNOWN

    def test_image_media(self) -> None:
        """Media with image type and URL."""
        media = Media(
            media_type=MediaType.IMAGE,
            url="https://media.linkedin.com/photo.jpg",
            alt_text="Team meeting photo",
        )
        assert media.media_type == MediaType.IMAGE
        assert media.alt_text == "Team meeting photo"

    def test_all_media_types_valid(self) -> None:
        """All MediaType enum values should be valid."""
        for media_type in MediaType:
            media = Media(media_type=media_type)
            assert media.media_type == media_type


class TestEngagement:
    """Test suite for Engagement model."""

    def test_default_engagement(self) -> None:
        """Default engagement should have all None counts."""
        eng = Engagement()
        assert eng.reaction_count is None
        assert eng.comment_count is None
        assert eng.repost_count is None

    def test_engagement_with_values(self) -> None:
        """Engagement with populated counts."""
        eng = Engagement(
            reaction_count=42,
            comment_count=5,
            repost_count=3,
            reaction_types={"like": 30, "celebrate": 10, "support": 2},
        )
        assert eng.reaction_count == 42
        assert eng.reaction_types is not None
        assert eng.reaction_types["like"] == 30

    def test_engagement_zero_counts(self) -> None:
        """Zero is a valid count (different from None/unknown)."""
        eng = Engagement(reaction_count=0, comment_count=0, repost_count=0)
        assert eng.reaction_count == 0
        assert eng.comment_count == 0


class TestPostContent:
    """Test suite for PostContent model."""

    def test_default_content(self) -> None:
        """Default content should be empty."""
        content = PostContent()
        assert content.text is None
        assert content.is_truncated is False
        assert content.hashtags == []
        assert content.mentions == []

    def test_content_with_text(self) -> None:
        """Content with text and metadata."""
        content = PostContent(
            text="Excited to share my new project! #python #opensource",
            hashtags=["#python", "#opensource"],
            mentions=["@johndoe"],
            is_truncated=False,
        )
        assert "Excited" in content.text  # type: ignore[operator]
        assert len(content.hashtags) == 2
        assert len(content.mentions) == 1

    def test_truncated_content(self) -> None:
        """Content marked as truncated."""
        content = PostContent(text="This is a long post that...", is_truncated=True)
        assert content.is_truncated is True


class TestPostMetadata:
    """Test suite for PostMetadata model."""

    def test_default_metadata(self) -> None:
        """Default metadata should have unknown post type."""
        meta = PostMetadata()
        assert meta.post_type == PostType.UNKNOWN
        assert meta.is_sponsored is False
        assert meta.is_suggested is False

    def test_sponsored_post(self) -> None:
        """Metadata for a sponsored/promoted post."""
        meta = PostMetadata(
            post_type=PostType.ORIGINAL,
            is_sponsored=True,
            visibility="Public",
        )
        assert meta.is_sponsored is True

    def test_suggested_post(self) -> None:
        """Metadata for a 'X liked this' suggested post."""
        meta = PostMetadata(
            is_suggested=True,
            suggestion_context="John Doe liked this",
        )
        assert meta.is_suggested is True
        assert "liked" in meta.suggestion_context  # type: ignore[operator]

    def test_metadata_with_relative_time(self) -> None:
        """Metadata with relative timestamp."""
        meta = PostMetadata(relative_time="2h")
        assert meta.relative_time == "2h"

    def test_all_post_types_valid(self) -> None:
        """All PostType enum values should be valid."""
        for post_type in PostType:
            meta = PostMetadata(post_type=post_type)
            assert meta.post_type == post_type


class TestFeedPost:
    """Test suite for FeedPost model."""

    def test_default_post(self) -> None:
        """Default post should have sensible defaults."""
        post = FeedPost()
        assert post.id is None
        assert post.url is None
        assert post.author.name is None
        assert post.content.text is None
        assert post.media == []
        assert post.engagement.reaction_count is None
        assert post.metadata.post_type == PostType.UNKNOWN
        assert isinstance(post.extracted_at, datetime)

    def test_minimal_post(self) -> None:
        """Post with minimal data (author + text only)."""
        post = FeedPost(
            author=Author(name="Jane Developer"),
            content=PostContent(text="Hello LinkedIn!"),
        )
        assert post.author.name == "Jane Developer"
        assert post.content.text == "Hello LinkedIn!"

    def test_full_post(self) -> None:
        """Post with all fields populated."""
        post = FeedPost(
            id="urn:li:activity:1234567890",
            url="https://linkedin.com/feed/update/urn:li:activity:1234567890",
            author=Author(
                name="Jane Developer",
                headline="Software Engineer",
                profile_url="https://linkedin.com/in/janedev",
            ),
            content=PostContent(
                text="Check out my new project!",
                hashtags=["#python"],
                is_truncated=False,
            ),
            media=[
                Media(
                    media_type=MediaType.IMAGE,
                    url="https://media.linkedin.com/img.jpg",
                )
            ],
            engagement=Engagement(
                reaction_count=100,
                comment_count=15,
                repost_count=5,
            ),
            metadata=PostMetadata(
                post_type=PostType.ORIGINAL,
                relative_time="2h",
                visibility="Public",
            ),
        )
        assert post.id == "urn:li:activity:1234567890"
        assert post.author.name == "Jane Developer"
        assert len(post.media) == 1
        assert post.engagement.reaction_count == 100
        assert post.metadata.post_type == PostType.ORIGINAL

    def test_post_serialization_roundtrip(self) -> None:
        """Post should serialize and deserialize cleanly."""
        original = FeedPost(
            id="test-123",
            author=Author(name="Test User"),
            content=PostContent(text="Hello!"),
            engagement=Engagement(reaction_count=42),
        )
        data = original.model_dump()
        restored = FeedPost.model_validate(data)
        assert restored.id == original.id
        assert restored.author.name == original.author.name
        assert restored.content.text == original.content.text
        assert restored.engagement.reaction_count == 42

    def test_post_json_serialization(self) -> None:
        """Post should convert to JSON and back."""
        post = FeedPost(
            id="json-test",
            author=Author(name="JSON User"),
        )
        json_str = post.model_dump_json()
        restored = FeedPost.model_validate_json(json_str)
        assert restored.id == "json-test"
        assert restored.author.name == "JSON User"

    def test_post_with_raw_data(self) -> None:
        """Post can store raw extraction data for debugging."""
        post = FeedPost(
            raw_data={"selector": "div.feed-post", "html_length": 1500}
        )
        assert post.raw_data is not None
        assert post.raw_data["html_length"] == 1500


class TestExtractionError:
    """Test suite for ExtractionError model."""

    def test_minimal_error(self) -> None:
        """Error with just a message."""
        error = ExtractionError(message="Failed to extract author")
        assert error.message == "Failed to extract author"
        assert error.error_type == "unknown"
        assert isinstance(error.timestamp, datetime)

    def test_error_with_context(self) -> None:
        """Error with full context."""
        error = ExtractionError(
            message="CSS selector not found",
            error_type="selector_error",
            post_index=3,
            partial_data={"author": "Found", "text": None},
        )
        assert error.post_index == 3
        assert error.partial_data is not None


class TestExtractionResult:
    """Test suite for ExtractionResult model."""

    def test_empty_result(self) -> None:
        """Empty result with no posts or errors."""
        result = ExtractionResult()
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.success_rate == 0.0
        assert result.is_complete_success is False

    def test_successful_result(self) -> None:
        """Result with only successful posts."""
        result = ExtractionResult(
            posts=[
                FeedPost(id="1", content=PostContent(text="Post 1")),
                FeedPost(id="2", content=PostContent(text="Post 2")),
            ],
            total_posts_found=2,
        )
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.success_rate == 100.0
        assert result.is_complete_success is True

    def test_partial_result(self) -> None:
        """Result with both successes and errors."""
        result = ExtractionResult(
            posts=[
                FeedPost(id="1", content=PostContent(text="Post 1")),
            ],
            errors=[
                ExtractionError(
                    message="Failed on post 2",
                    post_index=1,
                ),
            ],
            total_posts_found=2,
        )
        assert result.success_count == 1
        assert result.error_count == 1
        assert result.success_rate == 50.0
        assert result.is_complete_success is False

    def test_all_errors_result(self) -> None:
        """Result where all extractions failed."""
        result = ExtractionResult(
            errors=[
                ExtractionError(message="Error 1"),
                ExtractionError(message="Error 2"),
            ],
            total_posts_found=2,
        )
        assert result.success_count == 0
        assert result.error_count == 2
        assert result.success_rate == 0.0

    def test_result_with_metadata(self) -> None:
        """Result with extraction metadata."""
        started = datetime(2026, 8, 8, 12, 0, 0)
        completed = datetime(2026, 8, 8, 12, 0, 5)
        result = ExtractionResult(
            posts=[FeedPost(id="1")],
            extraction_started_at=started,
            extraction_completed_at=completed,
            extraction_duration_seconds=5.0,
            source_url="https://linkedin.com/feed/",
            extractor_name="BrowserExtractor",
        )
        assert result.extraction_duration_seconds == 5.0
        assert result.source_url == "https://linkedin.com/feed/"
        assert result.extractor_name == "BrowserExtractor"

    def test_result_serialization(self) -> None:
        """ExtractionResult should serialize cleanly."""
        result = ExtractionResult(
            posts=[FeedPost(id="1", author=Author(name="Test"))],
            errors=[ExtractionError(message="test error")],
            total_posts_found=2,
        )
        data = result.model_dump()
        restored = ExtractionResult.model_validate(data)
        assert restored.success_count == 1
        assert restored.error_count == 1
        assert restored.posts[0].author.name == "Test"
