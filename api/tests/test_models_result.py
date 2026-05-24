import pytest
from pydantic import ValidationError
from api.models.result import ScrapedResult, ResultMetadata


class TestResultMetadata:
    """Tests for ResultMetadata model."""

    def test_valid_metadata(self):
        """Test creating valid metadata."""
        meta = ResultMetadata(duration_ms=1500, pages_processed=3)
        assert meta.duration_ms == 1500
        assert meta.pages_processed == 3
        assert meta.status == "success"
        assert meta.error_message is None

    def test_negative_duration(self):
        """Test negative duration raises error."""
        with pytest.raises(ValidationError):
            ResultMetadata(duration_ms=-100)

    def test_invalid_status(self):
        """Test invalid status raises error."""
        with pytest.raises(ValidationError):
            ResultMetadata(duration_ms=100, status="invalid")


class TestScrapedResult:
    """Tests for ScrapedResult model."""

    def test_valid_result(self):
        """Test creating a valid scraping result."""
        result = ScrapedResult(
            job_id="test-job-id",
            items_count=42,
            items=[{"title": "Product 1", "price": "$10"}],
            metadata=ResultMetadata(duration_ms=1500),
        )
        assert result.job_id == "test-job-id"
        assert result.items_count == 42
        assert len(result.items) == 1
        assert result.run_id is not None
        assert result.timestamp is not None

    def test_auto_generated_run_id(self):
        """Test run_id is auto-generated."""
        result = ScrapedResult(
            job_id="test",
            items_count=0,
            items=[],
            metadata=ResultMetadata(duration_ms=100),
        )
        assert result.run_id is not None
        assert len(result.run_id) == 36

    def test_empty_items_list(self):
        """Test empty items list is allowed."""
        result = ScrapedResult(
            job_id="test",
            items_count=0,
            items=[],
            metadata=ResultMetadata(duration_ms=100),
        )
        assert result.items == []
        assert result.items_count == 0