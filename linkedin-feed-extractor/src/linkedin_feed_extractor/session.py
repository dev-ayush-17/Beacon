"""Session management for authenticated LinkedIn access.

Manages browser sessions using a user's existing browser profile.
This approach avoids storing raw cookies and uses the browser's own
session management for safer, more reliable authentication.

SECURITY:
- Never logs cookies, tokens, or session data
- Never stores credentials in source code
- Uses existing browser profile (user already authenticated)
- Validates session presence without exposing session details
"""

from __future__ import annotations

import logging
from pathlib import Path

from linkedin_feed_extractor.config import ExtractorConfig

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Raised when there is a session configuration or validation error."""


class SessionConfig:
    """Validates and prepares browser session configuration.

    This class checks that the required browser profile exists
    and is accessible, without reading or logging any session data.
    """

    def __init__(self, config: ExtractorConfig) -> None:
        self._config = config
        self._validated = False

    @property
    def profile_path(self) -> Path | None:
        """Path to the browser user data directory."""
        if self._config.browser_profile_path:
            return Path(self._config.browser_profile_path)
        return None

    @property
    def profile_name(self) -> str:
        """Browser profile name (e.g., 'Default')."""
        return self._config.browser_profile_name

    @property
    def is_configured(self) -> bool:
        """Whether a browser profile path has been set."""
        return self._config.browser_profile_path is not None

    def validate(self) -> list[str]:
        """Validate session configuration.

        Returns a list of issues. Empty list means valid.
        Does NOT log or return any sensitive path details beyond existence checks.
        """
        issues: list[str] = []

        if not self.is_configured:
            issues.append(
                "Browser profile path is not configured. "
                "Set LINKEDIN_BROWSER_PROFILE_PATH in your .env file."
            )
            return issues

        profile_path = self.profile_path
        assert profile_path is not None  # is_configured guarantees this

        if not profile_path.exists():
            issues.append(
                "Browser profile path does not exist. "
                "Verify LINKEDIN_BROWSER_PROFILE_PATH points to your Chrome user data directory."
            )
            return issues

        if not profile_path.is_dir():
            issues.append(
                "Browser profile path is not a directory. "
                "It should point to the Chrome 'User Data' directory."
            )
            return issues

        # Check for the named profile subdirectory
        named_profile = profile_path / self.profile_name
        if not named_profile.exists():
            issues.append(
                f"Profile '{self.profile_name}' not found in the browser user data directory. "
                f"Check LINKEDIN_BROWSER_PROFILE_NAME."
            )

        self._validated = len(issues) == 0
        return issues

    def get_playwright_args(self) -> dict[str, str | bool]:
        """Get Playwright launch arguments for this session.

        Returns a dict of arguments suitable for playwright's
        browser.launch_persistent_context().

        Raises SessionError if not validated.
        """
        if not self._validated:
            issues = self.validate()
            if issues:
                raise SessionError(
                    "Session configuration is invalid: " + "; ".join(issues)
                )

        assert self.profile_path is not None

        return {
            "user_data_dir": str(self.profile_path),
            "channel": "chrome",
            "headless": self._config.headless,
        }

    def __repr__(self) -> str:
        """Safe repr — never exposes actual paths."""
        status = "CONFIGURED" if self.is_configured else "NOT CONFIGURED"
        validated = "VALIDATED" if self._validated else "NOT VALIDATED"
        return f"SessionConfig(status={status}, validated={validated}, profile='{self.profile_name}')"
