"""Tests for session management."""

from __future__ import annotations

import os
import tempfile

import pytest

from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.session import SessionConfig, SessionError


@pytest.fixture
def temp_profile_dir() -> str:
    """Create a temporary directory simulating a browser profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a "Default" profile subdirectory
        os.makedirs(os.path.join(tmpdir, "Default"))
        yield tmpdir


class TestSessionConfig:
    """Test suite for SessionConfig."""

    def test_not_configured_without_path(self) -> None:
        """SessionConfig without profile path is not configured."""
        config = ExtractorConfig()
        session = SessionConfig(config)
        assert session.is_configured is False

    def test_configured_with_path(self, temp_profile_dir: str) -> None:
        """SessionConfig with profile path is configured."""
        config = ExtractorConfig(browser_profile_path=temp_profile_dir)
        session = SessionConfig(config)
        assert session.is_configured is True

    def test_validate_unconfigured(self) -> None:
        """Validation fails when no profile path is set."""
        config = ExtractorConfig()
        session = SessionConfig(config)
        issues = session.validate()
        assert len(issues) > 0
        assert "not configured" in issues[0].lower()

    def test_validate_nonexistent_path(self) -> None:
        """Validation fails when profile path doesn't exist."""
        config = ExtractorConfig(browser_profile_path="/nonexistent/path/to/profile")
        session = SessionConfig(config)
        issues = session.validate()
        assert len(issues) > 0
        assert "does not exist" in issues[0].lower()

    def test_validate_valid_profile(self, temp_profile_dir: str) -> None:
        """Validation passes with a valid profile directory."""
        config = ExtractorConfig(browser_profile_path=temp_profile_dir)
        session = SessionConfig(config)
        issues = session.validate()
        assert len(issues) == 0

    def test_validate_missing_named_profile(self, temp_profile_dir: str) -> None:
        """Validation warns when named profile subdirectory is missing."""
        config = ExtractorConfig(
            browser_profile_path=temp_profile_dir,
            browser_profile_name="Profile 2",
        )
        session = SessionConfig(config)
        issues = session.validate()
        assert len(issues) > 0
        assert "Profile 2" in issues[0]

    def test_get_playwright_args_valid(self, temp_profile_dir: str) -> None:
        """get_playwright_args returns correct args for valid config."""
        config = ExtractorConfig(
            browser_profile_path=temp_profile_dir,
            headless=True,
        )
        session = SessionConfig(config)
        args = session.get_playwright_args()
        assert args["user_data_dir"] == temp_profile_dir
        assert args["channel"] == "chrome"
        assert args["headless"] is True

    def test_get_playwright_args_invalid_raises(self) -> None:
        """get_playwright_args raises SessionError for invalid config."""
        config = ExtractorConfig()
        session = SessionConfig(config)
        with pytest.raises(SessionError):
            session.get_playwright_args()

    def test_repr_does_not_expose_paths(self, temp_profile_dir: str) -> None:
        """repr should not contain actual file paths."""
        config = ExtractorConfig(browser_profile_path=temp_profile_dir)
        session = SessionConfig(config)
        repr_str = repr(session)
        assert temp_profile_dir not in repr_str
        assert "CONFIGURED" in repr_str

    def test_profile_name_default(self) -> None:
        """Default profile name should be 'Default'."""
        config = ExtractorConfig()
        session = SessionConfig(config)
        assert session.profile_name == "Default"

    def test_profile_name_custom(self) -> None:
        """Custom profile name should be reflected."""
        config = ExtractorConfig(browser_profile_name="Profile 1")
        session = SessionConfig(config)
        assert session.profile_name == "Profile 1"
