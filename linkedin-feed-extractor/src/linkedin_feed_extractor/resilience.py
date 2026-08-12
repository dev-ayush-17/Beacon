"""Retry and resilience utilities for feed extraction.

Provides:
- Configurable retry with exponential backoff
- Timeout-aware retries
- Structured error capture for analysis
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    # Which exception types to retry on
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


@dataclass
class RetryResult:
    """Result of a retried operation."""

    success: bool
    value: Any = None
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0


async def retry_async(
    func: Callable[..., Any],
    config: RetryConfig | None = None,
    *args: Any,
    **kwargs: Any,
) -> RetryResult:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to call.
        config: Retry configuration. Uses defaults if None.
        *args: Positional args to pass to func.
        **kwargs: Keyword args to pass to func.

    Returns:
        RetryResult with success status, value, and error history.
    """
    if config is None:
        config = RetryConfig()

    errors: list[str] = []
    start = time.monotonic()

    for attempt in range(1, config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            duration = time.monotonic() - start
            return RetryResult(
                success=True,
                value=result,
                attempts=attempt,
                errors=errors,
                total_duration_seconds=duration,
            )
        except config.retryable_exceptions as e:
            error_msg = f"Attempt {attempt}/{config.max_retries}: {type(e).__name__}: {e}"
            errors.append(error_msg)
            logger.warning(error_msg)

            if attempt < config.max_retries:
                delay = min(
                    config.base_delay_seconds * (config.exponential_base ** (attempt - 1)),
                    config.max_delay_seconds,
                )
                logger.info("Retrying in %.1f seconds...", delay)
                await asyncio.sleep(delay)

    duration = time.monotonic() - start
    return RetryResult(
        success=False,
        attempts=config.max_retries,
        errors=errors,
        total_duration_seconds=duration,
    )


@dataclass
class SelectorFallback:
    """A CSS selector with fallback alternatives.

    Tries selectors in order, returning the first match.
    This handles LinkedIn's occasional DOM structure changes.
    """

    selectors: list[str]
    description: str = ""

    async def find_in(self, element: Any) -> Any | None:
        """Try each selector until one matches.

        Returns the first matching element, or None.
        """
        for selector in self.selectors:
            try:
                result = await element.query_selector(selector)
                if result:
                    return result
            except Exception:
                continue
        return None

    async def find_text_in(self, element: Any) -> str | None:
        """Try each selector and return text content of first match."""
        matched = await self.find_in(element)
        if matched:
            try:
                text = await matched.inner_text()
                return text.strip() if text else None
            except Exception:
                return None
        return None

    async def find_attr_in(self, element: Any, attr: str) -> str | None:
        """Try each selector and return an attribute of first match."""
        matched = await self.find_in(element)
        if matched:
            try:
                value = await matched.get_attribute(attr)
                return value.strip() if value else None
            except Exception:
                return None
        return None


# Pre-configured selectors with fallbacks for LinkedIn feed elements
FEED_SELECTORS = {
    "post_container": SelectorFallback(
        selectors=[
            "div.feed-shared-update-v2",
            "div[data-urn]",
            "article.feed-shared-update",
        ],
        description="Feed post container",
    ),
    "author_name": SelectorFallback(
        selectors=[
            ".update-components-actor__name span[aria-hidden='true']",
            ".update-components-actor__title span[aria-hidden='true']",
            ".feed-shared-actor__name span[aria-hidden='true']",
            ".update-components-actor__name",
        ],
        description="Author name",
    ),
    "author_headline": SelectorFallback(
        selectors=[
            ".update-components-actor__description span[aria-hidden='true']",
            ".update-components-actor__subtitle span[aria-hidden='true']",
            ".feed-shared-actor__description span[aria-hidden='true']",
        ],
        description="Author headline/subtitle",
    ),
    "author_link": SelectorFallback(
        selectors=[
            "a.update-components-actor__container-link",
            "a.update-components-actor__meta-link",
            "a.feed-shared-actor__container-link",
        ],
        description="Author profile link",
    ),
    "post_text": SelectorFallback(
        selectors=[
            ".feed-shared-update-v2__description .update-components-text span[dir='ltr']",
            ".update-components-text .break-words span[dir='ltr']",
            ".feed-shared-text span[dir='ltr']",
            ".update-components-text span.break-words",
            ".update-components-text",
        ],
        description="Post text content",
    ),
    "relative_time": SelectorFallback(
        selectors=[
            ".update-components-actor__sub-description span[aria-hidden='true']",
            "time.update-components-actor__sub-description",
            ".feed-shared-actor__sub-description span[aria-hidden='true']",
        ],
        description="Relative timestamp",
    ),
    "reaction_count": SelectorFallback(
        selectors=[
            ".social-details-social-counts__reactions-count",
            "button.social-details-social-counts__count-value",
            "span.social-details-social-counts__reactions-count",
        ],
        description="Reaction count",
    ),
    "comment_count": SelectorFallback(
        selectors=[
            "button.social-details-social-counts__comments",
            "[data-control-name='comments_count']",
            "li.social-details-social-counts__comments",
        ],
        description="Comment count",
    ),
    "main_content": SelectorFallback(
        selectors=[
            "[role='main']",
            ".scaffold-layout__main",
            "main",
        ],
        description="Main content area (authenticated indicator)",
    ),
    "auth_indicator": SelectorFallback(
        selectors=[
            "header.global-nav",
            "#global-nav",
            ".feed-identity-module",
            'img.global-nav__me-photo',
            ".scaffold-layout__main",
            ".share-box-feed-entry__trigger",
        ],
        description="Authentication indicator",
    ),
}
