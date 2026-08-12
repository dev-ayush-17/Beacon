"""Tests for retry and resilience utilities."""

from __future__ import annotations

import pytest

from linkedin_feed_extractor.resilience import (
    FEED_SELECTORS,
    RetryConfig,
    RetryResult,
    SelectorFallback,
    retry_async,
)


class TestRetryConfig:
    """Tests for RetryConfig defaults."""

    def test_default_config(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 30.0

    def test_custom_config(self) -> None:
        config = RetryConfig(max_retries=5, base_delay_seconds=0.5)
        assert config.max_retries == 5
        assert config.base_delay_seconds == 0.5


class TestRetryAsync:
    """Tests for the retry_async utility."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        """Should succeed without retries."""
        async def ok() -> str:
            return "success"

        result = await retry_async(ok)
        assert result.success is True
        assert result.value == "success"
        assert result.attempts == 1
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_success_after_retries(self) -> None:
        """Should succeed after transient failures."""
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "recovered"

        config = RetryConfig(max_retries=3, base_delay_seconds=0.01)
        result = await retry_async(flaky, config)
        assert result.success is True
        assert result.value == "recovered"
        assert result.attempts == 3
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self) -> None:
        """Should fail after exhausting retries."""
        async def always_fail() -> str:
            raise RuntimeError("permanent error")

        config = RetryConfig(max_retries=2, base_delay_seconds=0.01)
        result = await retry_async(always_fail, config)
        assert result.success is False
        assert result.value is None
        assert result.attempts == 2
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self) -> None:
        """Should not retry on non-retryable exceptions."""
        async def type_error() -> str:
            raise TypeError("wrong type")

        config = RetryConfig(
            max_retries=3,
            base_delay_seconds=0.01,
            retryable_exceptions=(ValueError,),
        )
        with pytest.raises(TypeError):
            await retry_async(type_error, config)

    @pytest.mark.asyncio
    async def test_result_has_duration(self) -> None:
        """Result should track total duration."""
        async def ok() -> str:
            return "fast"

        result = await retry_async(ok)
        assert result.total_duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self) -> None:
        """Should forward args/kwargs to the function."""
        async def add(a: int, b: int) -> int:
            return a + b

        result = await retry_async(add, None, 3, b=4)
        assert result.success is True
        assert result.value == 7


class TestSelectorFallback:
    """Tests for SelectorFallback."""

    def test_has_selectors(self) -> None:
        """SelectorFallback should store its selectors."""
        sf = SelectorFallback(
            selectors=["div.primary", "div.secondary"],
            description="Test selector",
        )
        assert len(sf.selectors) == 2

    def test_has_description(self) -> None:
        """SelectorFallback should store its description."""
        sf = SelectorFallback(
            selectors=["div.primary"],
            description="Test",
        )
        assert sf.description == "Test"


class TestFeedSelectors:
    """Tests for pre-configured feed selectors."""

    def test_all_selectors_defined(self) -> None:
        """All expected selectors should be defined."""
        expected = [
            "post_container",
            "author_name",
            "author_headline",
            "author_link",
            "post_text",
            "relative_time",
            "reaction_count",
            "comment_count",
            "main_content",
            "auth_indicator",
        ]
        for key in expected:
            assert key in FEED_SELECTORS, f"Missing selector: {key}"

    def test_selectors_have_fallbacks(self) -> None:
        """Each selector should have at least 2 alternatives."""
        for key, selector in FEED_SELECTORS.items():
            assert len(selector.selectors) >= 2, (
                f"Selector '{key}' has only {len(selector.selectors)} alternative(s)"
            )

    def test_selectors_have_descriptions(self) -> None:
        """Each selector should have a description."""
        for key, selector in FEED_SELECTORS.items():
            assert selector.description, f"Selector '{key}' has no description"
