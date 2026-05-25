from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.models.job import ScrapingJobInDB

VALID_SELECTORS = {
    "items": "div.product",
    "fields": {
        "title": {"selector": "h3", "attr": "text", "type": "string"},
    },
}


def _make_mock_cursor(return_value):
    """Helper to create a mock cursor with async to_list."""
    mock_cursor = MagicMock()
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=return_value)
    return mock_cursor


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.services.job_service.db") as mock_db:
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


class TestCreateJob:
    """Tests for POST /api/v1/jobs."""

    def test_create_valid_job(self, client):
        """Test creating a valid job."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.insert_one = AsyncMock()

        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test Job",
            "url": "https://example.com",
            "selectors": VALID_SELECTORS,
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Job"
        assert data["url"] == "https://example.com"
        assert data["status"] == "active"
        assert data["job_id"] is not None

    def test_create_job_invalid_url(self, client):
        """Test creating job with invalid URL returns 422."""
        client_obj, _ = client
        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test",
            "url": "bad-url",
            "selectors": VALID_SELECTORS,
        })
        assert response.status_code == 422

    def test_create_job_missing_selectors(self, client):
        """Test creating job without selectors returns 422."""
        client_obj, _ = client
        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test",
            "url": "https://example.com",
        })
        assert response.status_code == 422


class TestGetJob:
    """Tests for GET /api/v1/jobs/{job_id}."""

    def test_get_existing_job(self, client):
        """Test getting an existing job."""
        client_obj, mock_db = client
        mock_job = ScrapingJobInDB(
            name="Test",
            url="https://example.com",
            selectors=VALID_SELECTORS,
        )
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=mock_job.model_dump())

        response = client_obj.get(f"/api/v1/jobs/{mock_job.job_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_nonexistent_job(self, client):
        """Test getting a nonexistent job returns 404."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=None)
        response = client_obj.get("/api/v1/jobs/nonexistent")
        assert response.status_code == 404


class TestListJobs:
    """Tests for GET /api/v1/jobs."""

    def test_list_jobs_empty(self, client):
        """Test listing jobs when empty."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.find = MagicMock(return_value=_make_mock_cursor([]))

        response = client_obj.get("/api/v1/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_with_filter(self, client):
        """Test listing jobs with status filter."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.find = MagicMock(return_value=_make_mock_cursor([]))

        response = client_obj.get("/api/v1/jobs?status=active")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_invalid_status(self, client):
        """Test filtering with invalid status returns 422."""
        client_obj, _ = client
        response = client_obj.get("/api/v1/jobs?status=invalid")
        assert response.status_code == 422


class TestDeleteJob:
    """Tests for DELETE /api/v1/jobs/{job_id}."""

    def test_delete_existing_job(self, client):
        """Test deleting an existing job."""
        client_obj, mock_db = client
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_db.scraping_jobs.delete_one = AsyncMock(return_value=mock_result)

        response = client_obj.delete("/api/v1/jobs/test-id")
        assert response.status_code == 204

    def test_delete_nonexistent_job(self, client):
        """Test deleting nonexistent job returns 404."""
        client_obj, mock_db = client
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db.scraping_jobs.delete_one = AsyncMock(return_value=mock_result)

        response = client_obj.delete("/api/v1/jobs/nonexistent")
        assert response.status_code == 404


class TestPauseResume:
    """Tests for pause and resume endpoints."""

    def test_pause_job(self, client):
        """Test pausing a job."""
        client_obj, mock_db = client
        mock_job = ScrapingJobInDB(
            name="Test",
            url="https://example.com",
            selectors=VALID_SELECTORS,
            status="paused",
        )
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=mock_job.model_dump())
        mock_db.scraping_jobs.update_one = AsyncMock()

        response = client_obj.post(f"/api/v1/jobs/{mock_job.job_id}/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_resume_job(self, client):
        """Test resuming a job."""
        client_obj, mock_db = client
        mock_job = ScrapingJobInDB(
            name="Test",
            url="https://example.com",
            selectors=VALID_SELECTORS,
        )
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=mock_job.model_dump())
        mock_db.scraping_jobs.update_one = AsyncMock()

        response = client_obj.post(f"/api/v1/jobs/{mock_job.job_id}/resume")
        assert response.status_code == 200
