"""Base extractor interface.

Defines the contract that all feed extractors must implement.
This enables swapping extraction mechanisms (browser, API, mock)
without changing consuming code.

Full implementation comes in V0.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseFeedExtractor(ABC):
    """Abstract base class for feed extractors.

    Every extractor implementation must implement extract().
    The contract will be fully defined in V0.3.
    """

    @abstractmethod
    async def extract(self, **kwargs: Any) -> Any:
        """Extract feed data from LinkedIn.

        Returns structured extraction results.
        Exact return type will be defined in V0.2/V0.3.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that the extractor can connect and is ready."""
        ...
