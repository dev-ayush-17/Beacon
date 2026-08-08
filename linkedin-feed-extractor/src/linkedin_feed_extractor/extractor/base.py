"""Base extractor interface.

Defines the contract that all feed extractors must implement.
This enables swapping extraction mechanisms (browser, API, mock)
without changing consuming code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.models import ExtractionResult


class BaseFeedExtractor(ABC):
    """Abstract base class for feed extractors.

    Every extractor implementation must:
    1. Accept an ExtractorConfig at construction
    2. Implement extract() to return an ExtractionResult
    3. Implement health_check() to verify readiness
    4. Implement cleanup() for resource management

    The contract ensures all extractors are interchangeable.
    """

    def __init__(self, config: ExtractorConfig) -> None:
        self.config = config

    @abstractmethod
    async def extract(self, max_posts: int | None = None) -> ExtractionResult:
        """Extract feed posts from LinkedIn.

        Args:
            max_posts: Override config.max_posts for this extraction.
                       If None, uses config default.

        Returns:
            ExtractionResult containing posts, errors, and metadata.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that the extractor is ready to extract.

        Returns:
            True if the extractor can connect and is ready.
            False if there are configuration or connectivity issues.
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources (browser instances, connections, etc.)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this extractor implementation."""
        ...
