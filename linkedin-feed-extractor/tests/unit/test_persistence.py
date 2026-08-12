"""Tests for the persistence layer."""

from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path

import pytest

from linkedin_feed_extractor.models import (
    Author,
    Engagement,
    ExtractionError,
    ExtractionResult,
    FeedPost,
    PostContent,
    PostMetadata,
    PostType,
)
from linkedin_feed_extractor.persistence import ResultPersistence


@pytest.fixture
def temp_output_dir() -> Path:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_result() -> ExtractionResult:
    """Create a sample extraction result for testing."""
    return ExtractionResult(
        posts=[
            FeedPost(
                id="test-1",
                url="https://linkedin.com/feed/update/test-1",
                author=Author(name="Test User", headline="Engineer"),
                content=PostContent(text="Hello, World!"),
                engagement=Engagement(reaction_count=42, comment_count=5),
                metadata=PostMetadata(
                    post_type=PostType.ORIGINAL,
                    relative_time="2h",
                ),
            ),
            FeedPost(
                id="test-2",
                author=Author(name="Another User"),
                content=PostContent(text="Second post"),
            ),
        ],
        total_posts_found=2,
        extractor_name="TestExtractor",
    )


class TestJsonPersistence:
    """Test suite for JSON output."""

    def test_save_creates_file(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """save() should create a JSON file."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save(sample_result)
        assert path.exists()
        assert path.suffix == ".json"

    def test_save_creates_output_dir(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """save() should create the output directory if missing."""
        nested_dir = temp_output_dir / "sub" / "dir"
        persistence = ResultPersistence(nested_dir)
        path = persistence.save(sample_result)
        assert nested_dir.exists()
        assert path.exists()

    def test_saved_file_is_valid_json(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Saved file should be valid JSON."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save(sample_result)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "posts" in data
        assert len(data["posts"]) == 2

    def test_saved_file_has_correct_data(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Saved JSON should contain the original post data."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save(sample_result)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["posts"][0]["id"] == "test-1"
        assert data["posts"][0]["author"]["name"] == "Test User"
        assert data["posts"][1]["content"]["text"] == "Second post"

    def test_save_json_string(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """save_json_string should return valid JSON string."""
        persistence = ResultPersistence(temp_output_dir)
        json_str = persistence.save_json_string(sample_result)
        data = json.loads(json_str)
        assert data["posts"][0]["id"] == "test-1"

    def test_filename_has_timestamp(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Generated filename should start with 'feed_'."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save(sample_result)
        assert path.name.startswith("feed_")

    def test_empty_result_saves(self, temp_output_dir: Path) -> None:
        """Empty result should save without error."""
        result = ExtractionResult()
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save(result)
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["posts"] == []


class TestCsvPersistence:
    """Test suite for CSV output."""

    def test_save_csv_creates_file(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """save_csv() should create a CSV file."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save_csv(sample_result)
        assert path.exists()
        assert path.suffix == ".csv"

    def test_csv_has_header(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """CSV should have a header row."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save_csv(sample_result)
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "id" in header
        assert "author_name" in header
        assert "text" in header

    def test_csv_has_correct_rows(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """CSV should have one row per post."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save_csv(sample_result)
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["author_name"] == "Test User"
        assert rows[0]["reaction_count"] == "42"
        assert rows[1]["author_name"] == "Another User"

    def test_csv_string_output(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """to_csv_string should return valid CSV."""
        persistence = ResultPersistence(temp_output_dir)
        csv_str = persistence.to_csv_string(sample_result)
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2

    def test_empty_csv(self, temp_output_dir: Path) -> None:
        """Empty result should produce CSV with header only."""
        result = ExtractionResult()
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save_csv(result)
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        assert len(header) > 0
        assert len(rows) == 0


class TestMarkdownPersistence:
    """Test suite for Markdown output."""

    def test_save_markdown_creates_file(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """save_markdown() should create a .md file."""
        persistence = ResultPersistence(temp_output_dir)
        path = persistence.save_markdown(sample_result)
        assert path.exists()
        assert path.suffix == ".md"

    def test_markdown_has_title(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Markdown should start with a title."""
        persistence = ResultPersistence(temp_output_dir)
        md = persistence.to_markdown_string(sample_result)
        assert md.startswith("# LinkedIn Feed Extraction Report")

    def test_markdown_has_posts(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Markdown should contain post data."""
        persistence = ResultPersistence(temp_output_dir)
        md = persistence.to_markdown_string(sample_result)
        assert "Test User" in md
        assert "Hello, World!" in md
        assert "Another User" in md

    def test_markdown_has_metadata(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Markdown should include extraction metadata."""
        persistence = ResultPersistence(temp_output_dir)
        md = persistence.to_markdown_string(sample_result)
        assert "**Posts**: 2" in md
        assert "TestExtractor" in md

    def test_markdown_includes_errors(self, temp_output_dir: Path) -> None:
        """Markdown should include error section when errors exist."""
        result = ExtractionResult(
            errors=[
                ExtractionError(
                    message="Something failed",
                    error_type="test_error",
                ),
            ],
        )
        persistence = ResultPersistence(temp_output_dir)
        md = persistence.to_markdown_string(result)
        assert "## Errors" in md
        assert "Something failed" in md

    def test_markdown_engagement(
        self, temp_output_dir: Path, sample_result: ExtractionResult
    ) -> None:
        """Markdown should show engagement counts."""
        persistence = ResultPersistence(temp_output_dir)
        md = persistence.to_markdown_string(sample_result)
        assert "42" in md  # reaction count
