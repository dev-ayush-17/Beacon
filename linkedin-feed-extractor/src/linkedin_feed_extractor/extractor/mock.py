"""Mock extractor for testing.

Provides a fully functional extractor that returns synthetic data
without requiring a browser or network connection. Essential for:
- Unit testing the extraction pipeline
- Development without LinkedIn access
- CI/CD environments
"""

from __future__ import annotations

from datetime import datetime

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.extractor.base import BaseFeedExtractor
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


def _create_sample_posts(count: int) -> list[FeedPost]:
    """Generate synthetic feed posts for testing."""
    posts: list[FeedPost] = []

    samples = [
        {
            "author": "Alice Engineer",
            "headline": "Senior Software Engineer at TechCorp",
            "text": "Excited to share that I just completed a major refactor of our microservices architecture. The key insight was separating the read and write paths. #engineering #microservices",
            "post_type": PostType.ORIGINAL,
            "reactions": 127,
            "comments": 23,
            "reposts": 8,
            "relative_time": "2h",
            "hashtags": ["#engineering", "#microservices"],
        },
        {
            "author": "Bob Product Manager",
            "headline": "VP Product at StartupXYZ",
            "text": "Just published my thoughts on why most product roadmaps fail. TL;DR: They optimize for features instead of outcomes. Link in comments.",
            "post_type": PostType.ARTICLE,
            "reactions": 342,
            "comments": 56,
            "reposts": 41,
            "relative_time": "5h",
            "hashtags": [],
        },
        {
            "author": "Carol Designer",
            "headline": "UX Lead | Design Systems",
            "text": "Hot take: Dark mode isn't just an aesthetic choice. It's an accessibility feature. Here's why we made it the default in our new design system.",
            "post_type": PostType.ORIGINAL,
            "reactions": 89,
            "comments": 14,
            "reposts": 3,
            "relative_time": "1d",
            "hashtags": [],
            "media_type": MediaType.IMAGE,
        },
        {
            "author": "TechNews Daily",
            "headline": "Technology News & Analysis",
            "text": "BREAKING: Major cloud provider announces new AI infrastructure tier. Expected to reduce inference costs by 40%.",
            "post_type": PostType.ORIGINAL,
            "reactions": 1024,
            "comments": 89,
            "reposts": 156,
            "relative_time": "3h",
            "is_company": True,
            "hashtags": [],
        },
        {
            "author": "Dave Researcher",
            "headline": "PhD Candidate | Machine Learning",
            "text": "Our paper got accepted! 'Efficient Attention Mechanisms for Long-Context Transformers' will be presented at the conference next month. Grateful to my co-authors and advisors.",
            "post_type": PostType.CELEBRATION,
            "reactions": 567,
            "comments": 42,
            "reposts": 12,
            "relative_time": "8h",
            "hashtags": [],
        },
    ]

    for i in range(min(count, len(samples))):
        sample = samples[i]
        media_list: list[Media] = []
        if "media_type" in sample:
            media_list.append(
                Media(
                    media_type=sample["media_type"],  # type: ignore[arg-type]
                    url=f"https://media.example.com/image_{i}.jpg",
                    alt_text=f"Sample image for post {i}",
                )
            )

        post = FeedPost(
            id=f"urn:li:activity:mock-{i + 1:04d}",
            url=f"https://linkedin.com/feed/update/urn:li:activity:mock-{i + 1:04d}",
            author=Author(
                name=str(sample["author"]),
                headline=str(sample["headline"]),
                profile_url=f"https://linkedin.com/in/mock-user-{i + 1}",
                is_company=bool(sample.get("is_company", False)),
            ),
            content=PostContent(
                text=str(sample["text"]),
                hashtags=sample["hashtags"],  # type: ignore[arg-type]
                is_truncated=False,
            ),
            media=media_list,
            engagement=Engagement(
                reaction_count=sample["reactions"],  # type: ignore[arg-type]
                comment_count=sample["comments"],  # type: ignore[arg-type]
                repost_count=sample["reposts"],  # type: ignore[arg-type]
            ),
            metadata=PostMetadata(
                post_type=sample["post_type"],  # type: ignore[arg-type]
                relative_time=str(sample["relative_time"]),
                visibility="Public",
            ),
            extracted_at=datetime.utcnow(),
        )
        posts.append(post)

    # If more posts requested than samples, cycle through
    if count > len(samples):
        for i in range(len(samples), count):
            base = posts[i % len(samples)].model_copy(deep=True)
            base.id = f"urn:li:activity:mock-{i + 1:04d}"
            base.url = f"https://linkedin.com/feed/update/urn:li:activity:mock-{i + 1:04d}"
            posts.append(base)

    return posts


class MockExtractor(BaseFeedExtractor):
    """Mock extractor that returns synthetic feed data.

    Useful for:
    - Testing the extraction pipeline end-to-end
    - Development without browser/network dependencies
    - Generating sample data for UI development
    - CI/CD testing

    Can be configured to simulate failures for error handling tests.
    """

    def __init__(
        self,
        config: ExtractorConfig,
        *,
        simulate_failure: bool = False,
        failure_message: str = "Simulated extraction failure",
        simulate_partial: bool = False,
        error_at_indices: list[int] | None = None,
    ) -> None:
        super().__init__(config)
        self._simulate_failure = simulate_failure
        self._failure_message = failure_message
        self._simulate_partial = simulate_partial
        self._error_at_indices = error_at_indices or []
        self._is_healthy = True

    @property
    def name(self) -> str:
        return "MockExtractor"

    async def extract(self, max_posts: int | None = None) -> ExtractionResult:
        """Return synthetic extraction results.

        Args:
            max_posts: Number of mock posts to generate.
        """
        started = datetime.utcnow()
        limit = max_posts or self.config.max_posts

        if self._simulate_failure:
            return ExtractionResult(
                errors=[
                    ExtractionError(
                        message=self._failure_message,
                        error_type="simulated_failure",
                    )
                ],
                total_posts_found=0,
                extraction_started_at=started,
                extraction_completed_at=datetime.utcnow(),
                source_url="https://linkedin.com/feed/ (mock)",
                extractor_name=self.name,
            )

        all_posts = _create_sample_posts(limit)
        posts: list[FeedPost] = []
        errors: list[ExtractionError] = []

        for i, post in enumerate(all_posts):
            if i in self._error_at_indices:
                errors.append(
                    ExtractionError(
                        message=f"Simulated error at post index {i}",
                        error_type="simulated_partial_failure",
                        post_index=i,
                    )
                )
            else:
                posts.append(post)

        return ExtractionResult(
            posts=posts,
            errors=errors,
            total_posts_found=limit,
            extraction_started_at=started,
            extraction_completed_at=datetime.utcnow(),
            source_url="https://linkedin.com/feed/ (mock)",
            extractor_name=self.name,
        )

    async def health_check(self) -> bool:
        """Always returns True unless configured otherwise."""
        return self._is_healthy

    async def cleanup(self) -> None:
        """No-op for mock extractor."""
        pass

    def set_healthy(self, healthy: bool) -> None:
        """Control the health check response for testing."""
        self._is_healthy = healthy
