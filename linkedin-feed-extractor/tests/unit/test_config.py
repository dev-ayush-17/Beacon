"""Tests for configuration module."""

from __future__ import annotations

import pytest

from linkedin_feed_extractor.config import ExtractorConfig


class TestExtractorConfig:
    """Test suite for ExtractorConfig."""

    def test_default_config_creation(self) -> None:
        """Default config should be created with sensible defaults."""
        config = ExtractorConfig()
        assert config.max_posts == 20
        assert config.page_timeout == 30
        assert config.log_level == "INFO"
        assert config.headless is False
        assert config.browser_profile_name == "Default"
        assert config.browser_profile_path is None

    def test_config_validates_missing_profile(self) -> None:
        """Config without a browser profile path should produce a warning."""
        config = ExtractorConfig()
        issues = config.validate()
        assert any("LINKEDIN_BROWSER_PROFILE_PATH" in i for i in issues)

    def test_config_validates_invalid_max_posts(self) -> None:
        """max_posts < 1 should be flagged."""
        config = ExtractorConfig(max_posts=0)
        issues = config.validate()
        assert any("max_posts" in i for i in issues)

    def test_config_validates_invalid_timeout(self) -> None:
        """page_timeout < 1 should be flagged."""
        config = ExtractorConfig(page_timeout=-1)
        issues = config.validate()
        assert any("page_timeout" in i for i in issues)

    def test_config_validates_invalid_log_level(self) -> None:
        """Invalid log level should be flagged."""
        config = ExtractorConfig(log_level="TRACE")
        issues = config.validate()
        assert any("log_level" in i for i in issues)

    def test_config_repr_does_not_expose_secrets(self) -> None:
        """repr should say SET/NOT SET, not reveal the actual path."""
        config = ExtractorConfig(browser_profile_path="/secret/path")
        repr_str = repr(config)
        assert "/secret/path" not in repr_str
        assert "SET" in repr_str

    def test_config_repr_not_set(self) -> None:
        """repr should indicate NOT SET when no profile path."""
        config = ExtractorConfig()
        repr_str = repr(config)
        assert "NOT SET" in repr_str

    def test_config_is_frozen(self) -> None:
        """Config should be immutable after creation."""
        config = ExtractorConfig()
        with pytest.raises(AttributeError):
            config.max_posts = 99  # type: ignore[misc]

    def test_from_env_with_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_env should work with no env vars set (using defaults)."""
        # Clear any env vars that might interfere
        for var in [
            "LINKEDIN_BROWSER_PROFILE_PATH",
            "LINKEDIN_BROWSER_PROFILE_NAME",
            "LINKEDIN_MAX_POSTS",
            "LINKEDIN_PAGE_TIMEOUT",
            "LINKEDIN_OUTPUT_DIR",
            "LOG_LEVEL",
            "LINKEDIN_HEADLESS",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = ExtractorConfig.from_env()
        assert config.max_posts == 20
        assert config.headless is False

    def test_from_env_with_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_env should read values from environment variables."""
        monkeypatch.setenv("LINKEDIN_MAX_POSTS", "50")
        monkeypatch.setenv("LINKEDIN_HEADLESS", "true")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        config = ExtractorConfig.from_env()
        assert config.max_posts == 50
        assert config.headless is True
        assert config.log_level == "DEBUG"
