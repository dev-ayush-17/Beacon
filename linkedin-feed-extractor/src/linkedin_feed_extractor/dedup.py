"""Post deduplication and ID generation.

When extracting from the LinkedIn feed, the same post may appear
multiple times (e.g., across multiple scroll loads, or in
subsequent extraction runs). This module provides tools to:

1. Generate stable IDs for posts that don't have LinkedIn URNs
2. Deduplicate posts within a single extraction
3. Deduplicate across multiple extraction runs (merge results)
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from linkedin_feed_extractor.models import ExtractionResult, FeedPost


def generate_post_id(post: FeedPost) -> str:
    """Generate a stable, deterministic ID for a post.

    If the post already has a LinkedIn URN ID, returns it as-is.
    Otherwise, generates a hash-based ID from the post's content.

    The hash is based on:
    - Author name
    - Post text (first 200 chars)
    - Relative time

    This is NOT collision-proof but is sufficient for dedup within
    a single feed extraction session.
    """
    if post.id and post.id.startswith("urn:li:"):
        return post.id

    # Build a fingerprint from stable fields
    parts = [
        post.author.name or "",
        (post.content.text or "")[:200],
        post.metadata.relative_time or "",
    ]
    fingerprint = "|".join(parts)
    hash_digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"gen:{hash_digest}"


def deduplicate_posts(posts: list[FeedPost]) -> list[FeedPost]:
    """Remove duplicate posts, keeping the first occurrence.

    Uses post IDs for deduplication. Posts without IDs get
    generated IDs first.

    Returns a new list with duplicates removed.
    """
    seen: set[str] = set()
    unique: list[FeedPost] = []

    for post in posts:
        # Ensure each post has an ID
        if not post.id:
            post.id = generate_post_id(post)

        if post.id not in seen:
            seen.add(post.id)
            unique.append(post)

    return unique


def merge_results(
    *results: ExtractionResult,
) -> ExtractionResult:
    """Merge multiple extraction results, deduplicating posts.

    Useful for combining results from multiple extraction runs
    or scroll sessions.

    Returns a new ExtractionResult with:
    - All unique posts (first occurrence wins)
    - All errors combined
    - Metadata from the earliest start and latest end
    """
    all_posts: list[FeedPost] = []
    all_errors = []
    earliest_start = datetime.max
    latest_end = datetime.min

    for result in results:
        all_posts.extend(result.posts)
        all_errors.extend(result.errors)

        if result.extraction_started_at < earliest_start:
            earliest_start = result.extraction_started_at

        if (
            result.extraction_completed_at
            and result.extraction_completed_at > latest_end
        ):
            latest_end = result.extraction_completed_at

    unique_posts = deduplicate_posts(all_posts)

    duration = None
    completed = None
    if latest_end > datetime.min:
        completed = latest_end
        if earliest_start < datetime.max:
            duration = (latest_end - earliest_start).total_seconds()

    return ExtractionResult(
        posts=unique_posts,
        errors=all_errors,
        total_posts_found=len(unique_posts),
        extraction_started_at=earliest_start if earliest_start < datetime.max else datetime.utcnow(),
        extraction_completed_at=completed,
        extraction_duration_seconds=duration,
        extractor_name="merged",
    )
