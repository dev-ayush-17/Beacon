"""Persistence layer for saving extraction results.

Supports multiple output formats:
- JSON (full structured data)
- CSV (tabular summary)
- Markdown (human-readable report)

Handles saving extracted feed data with timestamped filenames.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path

from linkedin_feed_extractor.models import ExtractionResult, FeedPost

logger = logging.getLogger(__name__)


class ResultPersistence:
    """Saves extraction results to disk in multiple formats.

    Output directory is created automatically if it doesn't exist.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        """Create the output directory if it doesn't exist."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, extension: str = "json") -> str:
        """Generate a timestamped filename."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        return f"feed_{timestamp}.{extension}"

    # --- JSON ---

    def save(self, result: ExtractionResult) -> Path:
        """Save an extraction result to a JSON file.

        Returns the path to the saved file.
        """
        self._ensure_output_dir()
        filename = self._generate_filename("json")
        filepath = self._output_dir / filename

        data = result.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info("Saved extraction result to %s", filepath.name)
        logger.info(
            "  Posts: %d, Errors: %d, Success rate: %.0f%%",
            result.success_count,
            result.error_count,
            result.success_rate,
        )

        return filepath

    def save_json_string(self, result: ExtractionResult) -> str:
        """Return the extraction result as a JSON string."""
        data = result.model_dump(mode="json")
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    # --- CSV ---

    CSV_COLUMNS = [
        "id",
        "author_name",
        "author_headline",
        "author_profile_url",
        "text",
        "post_type",
        "relative_time",
        "timestamp",
        "reaction_count",
        "comment_count",
        "repost_count",
        "is_sponsored",
        "post_url",
        "extracted_at",
    ]

    @staticmethod
    def _post_to_csv_row(post: FeedPost) -> dict[str, str]:
        """Convert a FeedPost to a flat dict for CSV output."""
        return {
            "id": post.id or "",
            "author_name": post.author.name or "",
            "author_headline": post.author.headline or "",
            "author_profile_url": post.author.profile_url or "",
            "text": post.content.text or "",
            "post_type": post.metadata.post_type.value if post.metadata.post_type else "",
            "relative_time": post.metadata.relative_time or "",
            "timestamp": str(post.metadata.timestamp) if post.metadata.timestamp else "",
            "reaction_count": str(post.engagement.reaction_count) if post.engagement.reaction_count is not None else "",
            "comment_count": str(post.engagement.comment_count) if post.engagement.comment_count is not None else "",
            "repost_count": str(post.engagement.repost_count) if post.engagement.repost_count is not None else "",
            "is_sponsored": str(post.metadata.is_sponsored),
            "post_url": post.url or "",
            "extracted_at": str(post.extracted_at),
        }

    def save_csv(self, result: ExtractionResult) -> Path:
        """Save extraction result as a CSV file.

        Returns the path to the saved file.
        """
        self._ensure_output_dir()
        filename = self._generate_filename("csv")
        filepath = self._output_dir / filename

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            for post in result.posts:
                writer.writerow(self._post_to_csv_row(post))

        logger.info("Saved CSV to %s (%d rows)", filepath.name, len(result.posts))
        return filepath

    def to_csv_string(self, result: ExtractionResult) -> str:
        """Return the extraction result as a CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS)
        writer.writeheader()
        for post in result.posts:
            writer.writerow(self._post_to_csv_row(post))
        return output.getvalue()

    # --- Markdown ---

    def save_markdown(self, result: ExtractionResult) -> Path:
        """Save extraction result as a Markdown report.

        Returns the path to the saved file.
        """
        self._ensure_output_dir()
        filename = self._generate_filename("md")
        filepath = self._output_dir / filename

        md = self.to_markdown_string(result)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        logger.info("Saved Markdown report to %s", filepath.name)
        return filepath

    def to_markdown_string(self, result: ExtractionResult) -> str:
        """Return the extraction result as a Markdown string."""
        lines: list[str] = []
        lines.append("# LinkedIn Feed Extraction Report")
        lines.append("")
        lines.append(f"**Extracted at**: {result.extraction_started_at}")
        lines.append(f"**Extractor**: {result.extractor_name or 'unknown'}")
        lines.append(f"**Posts**: {result.success_count}")
        lines.append(f"**Errors**: {result.error_count}")
        lines.append(f"**Success Rate**: {result.success_rate:.0f}%")
        if result.extraction_duration_seconds:
            lines.append(f"**Duration**: {result.extraction_duration_seconds:.1f}s")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, post in enumerate(result.posts, 1):
            lines.append(f"## Post {i}")
            lines.append("")
            if post.author.name:
                lines.append(f"**Author**: {post.author.name}")
            if post.author.headline:
                lines.append(f"**Headline**: {post.author.headline}")
            if post.metadata.relative_time:
                lines.append(f"**Time**: {post.metadata.relative_time}")
            if post.metadata.post_type:
                lines.append(f"**Type**: {post.metadata.post_type.value}")
            lines.append("")
            if post.content.text:
                lines.append(f"> {post.content.text}")
                lines.append("")
            if post.engagement.reaction_count is not None:
                lines.append(
                    f"Reactions: {post.engagement.reaction_count} | "
                    f"Comments: {post.engagement.comment_count or 0} | "
                    f"Reposts: {post.engagement.repost_count or 0}"
                )
            if post.url:
                lines.append(f"[View Post]({post.url})")
            lines.append("")
            lines.append("---")
            lines.append("")

        if result.errors:
            lines.append("## Errors")
            lines.append("")
            for error in result.errors:
                lines.append(f"- **[{error.error_type}]** {error.message}")
            lines.append("")

        return "\n".join(lines)
