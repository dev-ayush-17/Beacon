"""Configuration management for LinkedIn Feed Extractor.

Loads settings from environment variables and .env files.
Never stores or logs sensitive credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file() -> Path | None:
    """Locate the .env file by walking up from the current directory."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        env_path = directory / ".env"
        if env_path.is_file():
            return env_path
    return None


@dataclass(frozen=True)
class ExtractorConfig:
    """Immutable configuration for the feed extractor.

    All sensitive paths are validated but never logged.
    """

    # Browser profile path (directory containing the authenticated session)
    browser_profile_path: str | None = None

    # Browser profile name (e.g., "Default", "Profile 1")
    browser_profile_name: str = "Default"

    # Maximum posts to extract per run
    max_posts: int = 20

    # Page load timeout in seconds
    page_timeout: int = 30

    # Output directory for extracted data
    output_dir: Path = field(default_factory=lambda: Path("./output"))

    # Log level
    log_level: str = "INFO"

    # Headless browser mode
    headless: bool = False

    @classmethod
    def from_env(cls) -> ExtractorConfig:
        """Load configuration from environment variables.

        Loads .env file if present. Never logs sensitive values.
        """
        env_file = _find_env_file()
        if env_file:
            load_dotenv(env_file)

        return cls(
            browser_profile_path=os.getenv("LINKEDIN_BROWSER_PROFILE_PATH") or None,
            browser_profile_name=os.getenv("LINKEDIN_BROWSER_PROFILE_NAME", "Default"),
            max_posts=int(os.getenv("LINKEDIN_MAX_POSTS", "20")),
            page_timeout=int(os.getenv("LINKEDIN_PAGE_TIMEOUT", "30")),
            output_dir=Path(os.getenv("LINKEDIN_OUTPUT_DIR", "./output")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            headless=os.getenv("LINKEDIN_HEADLESS", "false").lower() == "true",
        )

    def validate(self) -> list[str]:
        """Validate configuration and return a list of warnings/errors.

        Does NOT log or return sensitive values.
        """
        issues: list[str] = []

        if self.browser_profile_path:
            profile_path = Path(self.browser_profile_path)
            if not profile_path.exists():
                issues.append(
                    f"Browser profile path does not exist: {profile_path}"
                )
            elif not profile_path.is_dir():
                issues.append(
                    f"Browser profile path is not a directory: {profile_path}"
                )
        else:
            issues.append(
                "LINKEDIN_BROWSER_PROFILE_PATH is not set. "
                "Browser session will not be available."
            )

        if self.max_posts < 1:
            issues.append(f"max_posts must be >= 1, got {self.max_posts}")

        if self.page_timeout < 1:
            issues.append(f"page_timeout must be >= 1, got {self.page_timeout}")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if self.log_level.upper() not in valid_levels:
            issues.append(
                f"Invalid log_level '{self.log_level}'. Must be one of: {valid_levels}"
            )

        return issues

    def __repr__(self) -> str:
        """Safe repr that never exposes sensitive paths."""
        profile_status = "SET" if self.browser_profile_path else "NOT SET"
        return (
            f"ExtractorConfig("
            f"browser_profile={profile_status}, "
            f"profile_name='{self.browser_profile_name}', "
            f"max_posts={self.max_posts}, "
            f"timeout={self.page_timeout}s, "
            f"output='{self.output_dir}', "
            f"log_level='{self.log_level}', "
            f"headless={self.headless})"
        )
