"""Tests for CLI entry point."""

from __future__ import annotations

import json

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

    def test_cli_extract_help(self) -> None:
        """extract --help should show extraction options."""
        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--help"])
        assert result.exit_code == 0
        assert "--max-posts" in result.output
        assert "--mock" in result.output
        assert "--json-stdout" in result.output

    def test_cli_extract_mock(self) -> None:
        """extract --mock should work without browser."""
        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--mock", "-n", "3"])
        assert result.exit_code == 0
        assert "SUCCESS" in result.output or "Posts extracted" in result.output

    def test_cli_extract_mock_json_stdout(self) -> None:
        """extract --mock --json-stdout should output JSON data."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["extract", "--mock", "-n", "2", "--json-stdout"]
        )
        assert result.exit_code == 0
        # Output should contain JSON markers for posts
        assert '"posts"' in result.output
        assert '"extractor_name"' in result.output

    def test_cli_version_command(self) -> None:
        """version subcommand should print version."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
