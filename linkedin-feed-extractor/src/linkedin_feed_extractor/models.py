"""Domain models for LinkedIn feed data.

These models represent the structured data extracted from LinkedIn feeds.
They are platform-data-oriented, not tied to HTML structure.

All fields that may not always be present use Optional types.
Models use Pydantic for validation, serialization, and type safety.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Types of media that can appear in a LinkedIn post."""

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    ARTICLE = "article"
    POLL = "poll"
    LINK = "link"
    UNKNOWN = "unknown"


class PostType(str, Enum):
    """Types of LinkedIn feed posts."""

    ORIGINAL = "original"
    REPOST = "repost"
    SHARED = "shared"
    ARTICLE = "article"
    POLL = "poll"
    CELEBRATION = "celebration"
    UNKNOWN = "unknown"


class Author(BaseModel):
    """Represents the author of a LinkedIn post.

    Fields are optional because extraction may not always
    capture every piece of author information.
    """

    name: str | None = None
    headline: str | None = None
    profile_url: str | None = None
    profile_image_url: str | None = None
    connection_degree: str | None = None  # e.g., "1st", "2nd", "3rd"
    is_company: bool = False


class Media(BaseModel):
    """Represents a media attachment in a LinkedIn post."""

    media_type: MediaType = MediaType.UNKNOWN
    url: str | None = None
    thumbnail_url: str | None = None
    alt_text: str | None = None
    title: str | None = None
    description: str | None = None


class Engagement(BaseModel):
    """Engagement metrics for a LinkedIn post.

    All counts are optional — they may not always be visible
    or extractable from the feed.
    """

    reaction_count: int | None = None
    comment_count: int | None = None
    repost_count: int | None = None
    # Detailed reactions breakdown (like, celebrate, support, etc.)
    reaction_types: dict[str, int] | None = None


class PostContent(BaseModel):
    """The textual content of a LinkedIn post."""

    text: str | None = None
    # Whether the text was truncated ("...see more")
    is_truncated: bool = False
    # Hashtags found in the post
    hashtags: list[str] = Field(default_factory=list)
    # Mentioned users/companies
    mentions: list[str] = Field(default_factory=list)


class PostMetadata(BaseModel):
    """Metadata about the post itself (not content)."""

    post_type: PostType = PostType.UNKNOWN
    # Relative time as displayed ("2h", "1d", "3w")
    relative_time: str | None = None
    # Parsed timestamp if available
    timestamp: datetime | None = None
    # Post visibility ("Public", "Connections only", etc.)
    visibility: str | None = None
    # Whether this appeared as a promoted/sponsored post
    is_sponsored: bool = False
    # Whether this appeared via "X liked this" or "X commented on this"
    is_suggested: bool = False
    suggestion_context: str | None = None  # e.g., "John Doe liked this"


class FeedPost(BaseModel):
    """A single post from the LinkedIn feed.

    This is the primary domain object representing a complete
    extracted post with all available data.
    """

    # Unique identifier (LinkedIn post URN or constructed ID)
    id: str | None = None
    # Direct URL to the post
    url: str | None = None
    # Post author
    author: Author = Field(default_factory=Author)
    # Text content
    content: PostContent = Field(default_factory=PostContent)
    # Media attachments
    media: list[Media] = Field(default_factory=list)
    # Engagement metrics
    engagement: Engagement = Field(default_factory=Engagement)
    # Post metadata
    metadata: PostMetadata = Field(default_factory=PostMetadata)
    # When this post was extracted
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    # Raw data preserved for debugging (never contains credentials)
    raw_data: dict[str, Any] | None = None


class ExtractionError(BaseModel):
    """Represents an error encountered during extraction of a single post."""

    message: str
    error_type: str = "unknown"
    # Index of the post in the feed where the error occurred
    post_index: int | None = None
    # Partial data recovered before the error
    partial_data: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExtractionResult(BaseModel):
    """The complete result of a feed extraction operation.

    Contains both successfully extracted posts and any errors
    encountered during extraction.
    """

    # Successfully extracted posts
    posts: list[FeedPost] = Field(default_factory=list)
    # Errors encountered during extraction
    errors: list[ExtractionError] = Field(default_factory=list)
    # Total posts found on the page (may differ from len(posts))
    total_posts_found: int = 0
    # Extraction metadata
    extraction_started_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_completed_at: datetime | None = None
    # Duration in seconds
    extraction_duration_seconds: float | None = None
    # Source URL
    source_url: str | None = None
    # Extractor implementation that produced this result
    extractor_name: str | None = None

    @property
    def success_count(self) -> int:
        """Number of successfully extracted posts."""
        return len(self.posts)

    @property
    def error_count(self) -> int:
        """Number of errors during extraction."""
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0.0 to 100.0)."""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100.0

    @property
    def is_complete_success(self) -> bool:
        """True if extraction completed with no errors."""
        return self.error_count == 0 and self.success_count > 0
