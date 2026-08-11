"""Persistence layer for saving extraction results.

Handles saving extracted feed data to JSON files with
timestamped filenames.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from linkedin_feed_extractor.models import ExtractionResult

logger = logging.getLogger(__name__)


class ResultPersistence:
    """Saves extraction results to disk.

    Output directory is created automatically if it doesn't exist.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        """Create the output directory if it doesn't exist."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self) -> str:
        """Generate a timestamped filename."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        return f"feed_{timestamp}.json"

    def save(self, result: ExtractionResult) -> Path:
        """Save an extraction result to a JSON file.

        Returns the path to the saved file.
        """
        self._ensure_output_dir()
        filename = self._generate_filename()
        filepath = self._output_dir / filename

        # Serialize with Pydantic
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
