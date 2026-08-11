"""Normalization layer for feed post data.

Separates raw extraction from clean application data.
Handles:
- Whitespace normalization
- Missing value defaults
- Timestamp parsing
- Engagement number formatting
- URL normalization
- Text formatting and cleanup

Architecture:
    LinkedIn Page -> Raw Extractor -> Raw Post -> Normalizer -> FeedPost -> Consumer
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    FeedPost,
    PostContent,
    PostMetadata,
)


class FeedNormalizer:
    """Normalizes raw feed post data into clean domain objects.

    Takes partially-extracted or messy data and produces consistent,
    clean FeedPost instances suitable for downstream processing.
    """

    @staticmethod
    def normalize_text(text: str | None) -> str | None:
        """Normalize text content.

        - Strip leading/trailing whitespace
        - Collapse multiple spaces/newlines to single space
        - Remove zero-width characters
        - Return None for empty/whitespace-only strings
        """
        if text is None:
            return None

        # Remove zero-width characters
        cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        # Collapse whitespace
        cleaned = " ".join(cleaned.split())
        # Strip
        cleaned = cleaned.strip()

        return cleaned if cleaned else None

    @staticmethod
    def normalize_url(url: str | None) -> str | None:
        """Normalize a URL.

        - Make relative URLs absolute (LinkedIn domain)
        - Strip tracking query parameters
        - Strip trailing slashes (except root)
        - Return None for empty/invalid URLs
        """
        if not url:
            return None

        url = url.strip()

        # Make relative URLs absolute
        if url.startswith("/"):
            url = f"https://www.linkedin.com{url}"

        # Strip query parameters (tracking params)
        if "?" in url:
            url = url.split("?")[0]

        # Strip fragment
        if "#" in url:
            url = url.split("#")[0]

        # Strip trailing slash (but keep root slash)
        if url.endswith("/") and url.count("/") > 3:
            url = url.rstrip("/")

        return url if url else None

    @staticmethod
    def normalize_engagement_count(text: str | None) -> int | None:
        """Parse an engagement count string into an integer.

        Handles formats:
        - Plain number: "42"
        - With comma: "1,234"
        - Abbreviated: "2K", "1.5M"
        - With text: "23 comments", "8 reposts"
        - Empty/None: returns None
        """
        if not text:
            return None

        text = text.strip().lower().replace(",", "")

        # Remove trailing text like "comments", "reposts", "reactions"
        text = re.sub(r"\s*(comments?|reposts?|reactions?|likes?)\s*$", "", text)
        text = text.strip()

        if not text:
            return None

        try:
            if text.endswith("k"):
                return int(float(text[:-1]) * 1000)
            elif text.endswith("m"):
                return int(float(text[:-1]) * 1_000_000)
            elif text.endswith("b"):
                return int(float(text[:-1]) * 1_000_000_000)
            else:
                # Extract just digits and dots
                digits = re.sub(r"[^\d]", "", text)
                return int(digits) if digits else None
        except (ValueError, IndexError):
            return None

    @staticmethod
    def parse_relative_time(relative_time: str | None) -> datetime | None:
        """Parse LinkedIn relative time strings into approximate datetimes.

        Handles formats like:
        - "2h" -> 2 hours ago
        - "1d" -> 1 day ago
        - "3w" -> 3 weeks ago
        - "2mo" -> 2 months ago
        - "1yr" -> 1 year ago
        - "Just now" -> now
        - "30m" or "30min" -> 30 minutes ago

        Returns an approximate UTC datetime, or None if unparseable.
        """
        if not relative_time:
            return None

        text = relative_time.strip().lower()
        now = datetime.utcnow()

        if text in ("just now", "now"):
            return now

        # Match patterns like "2h", "1d", "3w", "2mo", "1yr", "30m", "30min"
        # Longer alternatives must come first to avoid partial matches (e.g., "mo" before "m")
        match = re.match(r"(\d+)\s*(min|mo|yr|s|m|h|d|w)", text)
        if not match:
            return None

        value = int(match.group(1))
        unit = match.group(2)

        if unit == "s":
            return now - timedelta(seconds=value)
        elif unit in ("m", "min"):
            return now - timedelta(minutes=value)
        elif unit == "h":
            return now - timedelta(hours=value)
        elif unit == "d":
            return now - timedelta(days=value)
        elif unit == "w":
            return now - timedelta(weeks=value)
        elif unit == "mo":
            return now - timedelta(days=value * 30)  # Approximate
        elif unit == "yr":
            return now - timedelta(days=value * 365)  # Approximate

        return None

    @staticmethod
    def extract_hashtags(text: str | None) -> list[str]:
        """Extract hashtags from post text.

        Returns a list of hashtag strings including the # prefix.
        """
        if not text:
            return []
        return re.findall(r"#\w+", text)

    @staticmethod
    def extract_mentions(text: str | None) -> list[str]:
        """Extract @mentions from post text.

        Returns a list of mention strings including the @ prefix.
        """
        if not text:
            return []
        return re.findall(r"@[\w.-]+", text)

    def normalize_post(self, post: FeedPost) -> FeedPost:
        """Apply all normalizations to a FeedPost.

        Returns a new FeedPost with normalized data.
        Does not modify the original.
        """
        # Normalize text content
        normalized_text = self.normalize_text(post.content.text)

        # Extract hashtags and mentions from normalized text
        hashtags = post.content.hashtags or self.extract_hashtags(normalized_text)
        mentions = post.content.mentions or self.extract_mentions(normalized_text)

        # Parse relative time into timestamp
        timestamp = post.metadata.timestamp or self.parse_relative_time(
            post.metadata.relative_time
        )

        return FeedPost(
            id=post.id,
            url=self.normalize_url(post.url),
            author=Author(
                name=self.normalize_text(post.author.name),
                headline=self.normalize_text(post.author.headline),
                profile_url=self.normalize_url(post.author.profile_url),
                profile_image_url=self.normalize_url(post.author.profile_image_url),
                connection_degree=post.author.connection_degree,
                is_company=post.author.is_company,
            ),
            content=PostContent(
                text=normalized_text,
                is_truncated=post.content.is_truncated,
                hashtags=hashtags,
                mentions=mentions,
            ),
            media=post.media,  # Media passed through as-is
            engagement=Engagement(
                reaction_count=post.engagement.reaction_count,
                comment_count=post.engagement.comment_count,
                repost_count=post.engagement.repost_count,
                reaction_types=post.engagement.reaction_types,
            ),
            metadata=PostMetadata(
                post_type=post.metadata.post_type,
                relative_time=post.metadata.relative_time,
                timestamp=timestamp,
                visibility=post.metadata.visibility,
                is_sponsored=post.metadata.is_sponsored,
                is_suggested=post.metadata.is_suggested,
                suggestion_context=post.metadata.suggestion_context,
            ),
            extracted_at=post.extracted_at,
            raw_data=post.raw_data,
        )

    def normalize_posts(self, posts: list[FeedPost]) -> list[FeedPost]:
        """Normalize a list of posts."""
        return [self.normalize_post(post) for post in posts]
