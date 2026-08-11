"""Tests for the persistence layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from linkedin_feed_extractor.models import (
    Author,
    ExtractionResult,
    FeedPost,
    PostContent,
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
                author=Author(name="Test User"),
                content=PostContent(text="Hello, World!"),
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


class TestResultPersistence:
    """Test suite for ResultPersistence."""

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
