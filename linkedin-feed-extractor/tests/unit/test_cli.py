"""Tests for CLI entry point."""

from __future__ import annotations

from click.testing import CliRunner

from linkedin_feed_extractor.cli import main


class TestCLI:
    """Test suite for the CLI interface."""

    def test_cli_version_flag(self) -> None:
        """--version should print version and exit cleanly."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self) -> None:
        """--help should print usage information."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "LinkedIn Feed Extractor" in result.output

    def test_cli_status_command(self) -> None:
        """status command should run and show config info."""
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "LinkedIn Feed Extractor" in result.output

    def test_cli_extract_not_implemented(self) -> None:
        """extract command should exit with error (not yet implemented)."""
        runner = CliRunner()
        result = runner.invoke(main, ["extract"])
        assert result.exit_code != 0
        assert "not yet implemented" in result.output.lower()

    def test_cli_version_command(self) -> None:
        """version subcommand should print version."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
