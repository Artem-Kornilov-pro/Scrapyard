import pytest
from pydantic import ValidationError
from api.models.job import (
    ScrapingJobCreate,
    ScrapingJobUpdate,
    ScrapingJobInDB,
)


VALID_SELECTORS = {
    "items": "div.product",
    "fields": {
        "title": {"selector": "h3", "attr": "text", "type": "string"},
        "price": {"selector": "span", "attr": "text", "type": "string"},
    },
}


class TestScrapingJobCreate:
    """Tests for ScrapingJobCreate model."""

    def test_valid_job(self):
        """Test creating a valid scraping job."""
        job = ScrapingJobCreate(
            name="Test Job",
            url="https://example.com",
            selectors=VALID_SELECTORS,
        )
        assert job.name == "Test Job"
        assert job.url == "https://example.com"
        assert job.schedule == "0 */6 * * *"
        assert job.tags == []

    def test_missing_required_fields(self):
        """Test that required fields raise error."""
        with pytest.raises(ValidationError):
            ScrapingJobCreate()

    def test_invalid_url(self):
        """Test that invalid URL raises error."""
        with pytest.raises(ValidationError) as exc:
            ScrapingJobCreate(
                name="Test",
                url="not-a-url",
                selectors=VALID_SELECTORS,
            )
        assert "URL must start with http:// or https://" in str(exc.value)

    def test_invalid_cron(self):
        """Test that invalid cron expression raises error."""
        with pytest.raises(ValidationError) as exc:
            ScrapingJobCreate(
                name="Test",
                url="https://example.com",
                selectors=VALID_SELECTORS,
                schedule="invalid-cron",
            )
        assert "Invalid cron expression" in str(exc.value)

    def test_invalid_selectors_no_items(self):
        """Test that selectors without 'items' raises error."""
        with pytest.raises(ValidationError) as exc:
            ScrapingJobCreate(
                name="Test",
                url="https://example.com",
                selectors={"fields": {"title": {}}},
            )
        assert "must contain 'items'" in str(exc.value)

    def test_invalid_selectors_no_fields(self):
        """Test that selectors without 'fields' raises error."""
        with pytest.raises(ValidationError) as exc:
            ScrapingJobCreate(
                name="Test",
                url="https://example.com",
                selectors={"items": "div"},
            )
        assert "must contain 'fields'" in str(exc.value)

    def test_empty_fields_dict(self):
        """Test that empty fields dict raises error."""
        with pytest.raises(ValidationError) as exc:
            ScrapingJobCreate(
                name="Test",
                url="https://example.com",
                selectors={"items": "div", "fields": {}},
            )
        assert "non-empty dict" in str(exc.value)

    def test_default_values(self):
        """Test default values are set correctly."""
        job = ScrapingJobCreate(
            name="Test",
            url="https://example.com",
            selectors=VALID_SELECTORS,
        )
        assert job.method == "GET"
        assert job.tags == []
        assert job.settings == {
            "wait_until": "networkidle",
            "timeout": 30,
            "pagination": {"type": None, "max_pages": 1},
        }


class TestScrapingJobUpdate:
    """Tests for ScrapingJobUpdate model."""

    def test_empty_update(self):
        """Test creating an empty update (all fields optional)."""
        update = ScrapingJobUpdate()
        assert update.name is None
        assert update.url is None

    def test_partial_update(self):
        """Test updating only some fields."""
        update = ScrapingJobUpdate(name="New Name", tags=["tag1", "tag2"])
        assert update.name == "New Name"
        assert update.tags == ["tag1", "tag2"]
        assert update.url is None

    def test_invalid_url_on_update(self):
        """Test invalid URL on update raises error."""
        with pytest.raises(ValidationError):
            ScrapingJobUpdate(url="bad-url")

    def test_invalid_cron_on_update(self):
        """Test invalid cron on update raises error."""
        with pytest.raises(ValidationError):
            ScrapingJobUpdate(schedule="bad")


class TestScrapingJobInDB:
    """Tests for ScrapingJobInDB model."""

    def test_auto_generated_fields(self):
        """Test that job_id, timestamps are auto-generated."""
        job = ScrapingJobInDB(
            name="Test",
            url="https://example.com",
            selectors=VALID_SELECTORS,
        )
        assert job.job_id is not None
        assert len(job.job_id) == 36  # UUID format
        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.status == "active"
        assert job.consecutive_failures == 0

    def test_invalid_status(self):
        """Test invalid status raises error."""
        with pytest.raises(ValidationError):
            ScrapingJobInDB(
                name="Test",
                url="https://example.com",
                selectors=VALID_SELECTORS,
                status="invalid",
            )

    def test_valid_statuses(self):
        """Test all valid statuses work."""
        for status in ["active", "paused", "error"]:
            job = ScrapingJobInDB(
                name="Test",
                url="https://example.com",
                selectors=VALID_SELECTORS,
                status=status,
            )
            assert job.status == status