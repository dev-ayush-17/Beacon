"""CLI entry point for LinkedIn Feed Extractor.

Provides a click-based command-line interface for the
complete feed extraction pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from linkedin_feed_extractor import __version__
from linkedin_feed_extractor.config import ExtractorConfig
from linkedin_feed_extractor.dedup import deduplicate_posts
from linkedin_feed_extractor.normalizer import FeedNormalizer
from linkedin_feed_extractor.persistence import ResultPersistence

console = Console()


def _setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


@click.group()
@click.version_option(version=__version__, prog_name="linkedin-feed")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """LinkedIn Feed Extractor -- Research-oriented feed data extraction."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _setup_logging(verbose)


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
@click.option(
    "--max-posts", "-n", default=None, type=int, help="Maximum posts to extract."
)
@click.option(
    "--output", "-o", default=None, type=str, help="Output directory for results."
)
@click.option(
    "--json-stdout", is_flag=True, help="Print JSON to stdout instead of saving file."
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "csv", "markdown", "all"], case_sensitive=False),
    default="json",
    help="Output format (default: json).",
)
@click.option(
    "--mock", is_flag=True, help="Use mock extractor (no browser needed)."
)
@click.pass_context
def extract(
    ctx: click.Context,
    max_posts: int | None,
    output: str | None,
    json_stdout: bool,
    format: str,
    mock: bool,
) -> None:
    """Extract feed posts from LinkedIn.

    Requires an authenticated browser session unless --mock is used.
    """
    verbose = ctx.obj.get("verbose", False)
    config = ExtractorConfig.from_env()

    if max_posts:
        # Override max_posts in config
        config = ExtractorConfig(
            browser_profile_path=config.browser_profile_path,
            browser_profile_name=config.browser_profile_name,
            max_posts=max_posts,
            page_timeout=config.page_timeout,
            output_dir=config.output_dir,
            log_level=config.log_level,
            headless=config.headless,
        )

    # Run the async extraction
    result = asyncio.run(_run_extraction(config, max_posts, mock))

    # Apply normalization
    normalizer = FeedNormalizer()
    result.posts = normalizer.normalize_posts(result.posts)

    # Deduplicate
    result.posts = deduplicate_posts(result.posts)

    # Output results
    if json_stdout:
        persistence = ResultPersistence(config.output_dir)
        console.print(persistence.save_json_string(result))
    else:
        output_dir = config.output_dir
        if output:
            from pathlib import Path
            output_dir = Path(output)

        persistence = ResultPersistence(output_dir)
        saved_paths: list[str] = []

        if format in ("json", "all"):
            path = persistence.save(result)
            saved_paths.append(str(path))
        if format in ("csv", "all"):
            path = persistence.save_csv(result)
            saved_paths.append(str(path))
        if format in ("markdown", "all"):
            path = persistence.save_markdown(result)
            saved_paths.append(str(path))

        console.print()
        _print_result_summary(result, saved_paths)

    # Exit with error code if no posts extracted
    if result.success_count == 0:
        sys.exit(1)


async def _run_extraction(
    config: ExtractorConfig,
    max_posts: int | None,
    use_mock: bool,
) -> "ExtractionResult":
    """Run the extraction pipeline."""
    from linkedin_feed_extractor.models import ExtractionResult

    if use_mock:
        from linkedin_feed_extractor.extractor.mock import MockExtractor
        extractor = MockExtractor(config)
    else:
        from linkedin_feed_extractor.extractor.browser import BrowserExtractor
        extractor = BrowserExtractor(config)

    try:
        console.print(
            Panel(
                f"[cyan]Starting extraction with {extractor.name}[/cyan]\n"
                f"Max posts: {max_posts or config.max_posts}",
                title="Extracting",
                border_style="cyan",
            )
        )

        result = await extractor.extract(max_posts=max_posts)
        return result
    finally:
        await extractor.cleanup()


def _print_result_summary(result: "ExtractionResult", saved_paths: list[str]) -> None:
    """Print a summary of the extraction results."""
    from pathlib import Path as _Path

    # Summary panel
    if result.success_count > 0:
        style = "green"
        status_text = "SUCCESS"
    elif result.error_count > 0:
        style = "red"
        status_text = "FAILED"
    else:
        style = "yellow"
        status_text = "NO DATA"

    saved_info = "\n".join(f"  - {p}" for p in saved_paths) if saved_paths else "N/A"
    console.print(
        Panel(
            f"[bold {style}]{status_text}[/bold {style}]\n\n"
            f"Posts extracted: {result.success_count}\n"
            f"Errors: {result.error_count}\n"
            f"Success rate: {result.success_rate:.0f}%\n"
            f"Duration: {result.extraction_duration_seconds or 'N/A'}s\n"
            f"Saved to:\n{saved_info}",
            title="Results",
            border_style=style,
        )
    )

    # Post table
    if result.posts:
        table = Table(title="Extracted Posts", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Author", style="cyan", max_width=25)
        table.add_column("Text", max_width=50)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Reactions", style="green", width=10)

        for i, post in enumerate(result.posts, 1):
            text_preview = (post.content.text or "")[:47]
            if post.content.text and len(post.content.text) > 47:
                text_preview += "..."

            table.add_row(
                str(i),
                post.author.name or "Unknown",
                text_preview,
                post.metadata.relative_time or "?",
                str(post.engagement.reaction_count or "?"),
            )

        console.print(table)

    # Error details
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  [red]- [{error.error_type}] {error.message}[/red]")


@main.command()
def version() -> None:
    """Display version information."""
    console.print(f"linkedin-feed-extractor {__version__}")


if __name__ == "__main__":
    main()
