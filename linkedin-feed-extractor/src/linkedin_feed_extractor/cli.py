"""CLI entry point for LinkedIn Feed Extractor.

Provides a click-based command-line interface.
"""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel

from linkedin_feed_extractor import __version__
from linkedin_feed_extractor.config import ExtractorConfig

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="linkedin-feed")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """LinkedIn Feed Extractor — Research-oriented feed data extraction."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
def status() -> None:
    """Show current configuration status and readiness."""
    config = ExtractorConfig.from_env()
    issues = config.validate()

    console.print(
        Panel(
            f"[bold cyan]LinkedIn Feed Extractor[/bold cyan] v{__version__}",
            title="Status",
            border_style="cyan",
        )
    )
    console.print(f"\n[dim]Configuration:[/dim]\n  {config}\n")

    if issues:
        console.print("[yellow]WARNING: Configuration issues:[/yellow]")
        for issue in issues:
            console.print(f"  [yellow]- {issue}[/yellow]")
    else:
        console.print("[green]OK: Configuration looks valid.[/green]")

    console.print()


@main.command()
def extract() -> None:
    """Extract feed posts from LinkedIn.

    Requires an authenticated browser session.
    Not yet implemented — coming in V0.5+.
    """
    console.print(
        Panel(
            "[yellow]Feed extraction is not yet implemented.[/yellow]\n\n"
            "This command will be available after completing:\n"
            "  • V0.2 — Domain models\n"
            "  • V0.3 — Extractor contract\n"
            "  • V0.4 — Session architecture\n"
            "  • V0.5 — Browser connectivity",
            title="Not Yet Available",
            border_style="yellow",
        )
    )
    sys.exit(1)


@main.command()
def version() -> None:
    """Display version information."""
    console.print(f"linkedin-feed-extractor {__version__}")


if __name__ == "__main__":
    main()
