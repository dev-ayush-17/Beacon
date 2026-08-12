"""Tests for post deduplication and ID generation."""

from __future__ import annotations

from datetime import datetime

import pytest

from linkedin_feed_extractor.dedup import (
    deduplicate_posts,
    generate_post_id,
    merge_results,
)
from linkedin_feed_extractor.models import (
    Author,
    ExtractionError,
    ExtractionResult,
    FeedPost,
    PostContent,
    PostMetadata,
)


class TestGeneratePostId:
    """Tests for stable ID generation."""

    def test_returns_urn_if_present(self) -> None:
        """Posts with LinkedIn URNs should keep their ID."""
        post = FeedPost(id="urn:li:activity:123456")
        assert generate_post_id(post) == "urn:li:activity:123456"

    def test_generates_id_without_urn(self) -> None:
        """Posts without URNs should get a generated ID."""
        post = FeedPost(
            author=Author(name="Jane"),
            content=PostContent(text="Hello world"),
        )
        generated = generate_post_id(post)
        assert generated.startswith("gen:")
        assert len(generated) > 4

    def test_same_content_same_id(self) -> None:
        """Same content should produce the same ID."""
        post1 = FeedPost(
            author=Author(name="Jane"),
            content=PostContent(text="Hello world"),
            metadata=PostMetadata(relative_time="2h"),
        )
        post2 = FeedPost(
            author=Author(name="Jane"),
            content=PostContent(text="Hello world"),
            metadata=PostMetadata(relative_time="2h"),
        )
        assert generate_post_id(post1) == generate_post_id(post2)

    def test_different_content_different_id(self) -> None:
        """Different content should produce different IDs."""
        post1 = FeedPost(
            author=Author(name="Jane"),
            content=PostContent(text="Hello world"),
        )
        post2 = FeedPost(
            author=Author(name="Jane"),
            content=PostContent(text="Different text"),
        )
        assert generate_post_id(post1) != generate_post_id(post2)

    def test_different_authors_different_id(self) -> None:
        """Different authors should produce different IDs."""
        post1 = FeedPost(
            author=Author(name="Alice"),
            content=PostContent(text="Same text"),
        )
        post2 = FeedPost(
            author=Author(name="Bob"),
            content=PostContent(text="Same text"),
        )
        assert generate_post_id(post1) != generate_post_id(post2)

    def test_empty_post_gets_id(self) -> None:
        """Even empty posts should get a generated ID."""
        post = FeedPost()
        generated = generate_post_id(post)
        assert generated.startswith("gen:")

    def test_non_urn_id_gets_replaced(self) -> None:
        """Non-URN IDs should get a generated ID."""
        post = FeedPost(id="some-custom-id")
        generated = generate_post_id(post)
        assert generated.startswith("gen:")


class TestDeduplicatePosts:
    """Tests for post deduplication."""

    def test_no_duplicates(self) -> None:
        """Unique posts should all be kept."""
        posts = [
            FeedPost(id="urn:li:activity:1", content=PostContent(text="A")),
            FeedPost(id="urn:li:activity:2", content=PostContent(text="B")),
        ]
        result = deduplicate_posts(posts)
        assert len(result) == 2

    def test_removes_exact_duplicates(self) -> None:
        """Posts with same ID should be deduplicated."""
        posts = [
            FeedPost(id="urn:li:activity:1", content=PostContent(text="A")),
            FeedPost(id="urn:li:activity:1", content=PostContent(text="A")),
        ]
        result = deduplicate_posts(posts)
        assert len(result) == 1

    def test_keeps_first_occurrence(self) -> None:
        """First occurrence of a duplicate should be kept."""
        posts = [
            FeedPost(id="urn:li:activity:1", content=PostContent(text="First")),
            FeedPost(id="urn:li:activity:1", content=PostContent(text="Second")),
        ]
        result = deduplicate_posts(posts)
        assert result[0].content.text == "First"

    def test_assigns_ids_to_posts_without_them(self) -> None:
        """Posts without IDs should get generated IDs."""
        posts = [
            FeedPost(
                author=Author(name="Jane"),
                content=PostContent(text="Hello"),
            ),
        ]
        result = deduplicate_posts(posts)
        assert result[0].id is not None
        assert result[0].id.startswith("gen:")

    def test_content_based_dedup(self) -> None:
        """Posts with same content but no ID should be deduped."""
        posts = [
            FeedPost(
                author=Author(name="Jane"),
                content=PostContent(text="Hello"),
                metadata=PostMetadata(relative_time="2h"),
            ),
            FeedPost(
                author=Author(name="Jane"),
                content=PostContent(text="Hello"),
                metadata=PostMetadata(relative_time="2h"),
            ),
        ]
        result = deduplicate_posts(posts)
        assert len(result) == 1

    def test_empty_list(self) -> None:
        """Empty list should return empty."""
        assert deduplicate_posts([]) == []


class TestMergeResults:
    """Tests for merging extraction results."""

    def test_merge_two_results(self) -> None:
        """Merging two results should combine posts."""
        r1 = ExtractionResult(
            posts=[FeedPost(id="urn:li:activity:1", content=PostContent(text="A"))],
            extraction_started_at=datetime(2026, 1, 1, 12, 0, 0),
            extraction_completed_at=datetime(2026, 1, 1, 12, 0, 5),
        )
        r2 = ExtractionResult(
            posts=[FeedPost(id="urn:li:activity:2", content=PostContent(text="B"))],
            extraction_started_at=datetime(2026, 1, 1, 12, 1, 0),
            extraction_completed_at=datetime(2026, 1, 1, 12, 1, 5),
        )
        merged = merge_results(r1, r2)
        assert merged.success_count == 2
        assert merged.extraction_started_at == datetime(2026, 1, 1, 12, 0, 0)
        assert merged.extraction_completed_at == datetime(2026, 1, 1, 12, 1, 5)

    def test_merge_deduplicates(self) -> None:
        """Merging should remove duplicate posts."""
        r1 = ExtractionResult(
            posts=[FeedPost(id="urn:li:activity:1", content=PostContent(text="A"))],
        )
        r2 = ExtractionResult(
            posts=[FeedPost(id="urn:li:activity:1", content=PostContent(text="A"))],
        )
        merged = merge_results(r1, r2)
        assert merged.success_count == 1

    def test_merge_combines_errors(self) -> None:
        """Merging should combine all errors."""
        r1 = ExtractionResult(
            errors=[ExtractionError(message="Error 1")],
        )
        r2 = ExtractionResult(
            errors=[ExtractionError(message="Error 2")],
        )
        merged = merge_results(r1, r2)
        assert merged.error_count == 2

    def test_merge_single_result(self) -> None:
        """Merging a single result should return it as-is."""
        r1 = ExtractionResult(
            posts=[FeedPost(id="urn:li:activity:1")],
        )
        merged = merge_results(r1)
        assert merged.success_count == 1
