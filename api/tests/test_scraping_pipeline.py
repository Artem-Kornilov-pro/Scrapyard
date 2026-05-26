"""Integration tests for the full scraping pipeline."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID_JOB = {
    "name": "Integration Test",
    "url": "https://example.com",
    "selectors": {
        "items": "div.product",
        "fields": {
            "title": {"selector": "h3", "attr": "text", "type": "string"},
        },
    },
}


@pytest.fixture
def client():
    """Create test client with mocked DB and Redis."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.services.job_service.db") as mock_db, \
         patch("api.services.job_service.jobs_cache") as mock_jobs_cache, \
         patch("api.services.job_service.analytics_cache") as mock_analytics_cache:
        mock_db.scraping_jobs = MagicMock()
        mock_db.scraping_jobs.insert_one = AsyncMock()
        mock_db.scraping_jobs.find_one = AsyncMock()
        mock_db.scraping_jobs.find = MagicMock()
        mock_jobs_cache.delete_pattern = AsyncMock()
        mock_jobs_cache.get = AsyncMock(return_value=None)
        mock_jobs_cache.set = AsyncMock()
        mock_analytics_cache.delete_pattern = AsyncMock()

        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


class TestScrapingPipeline:
    """Integration tests for the full pipeline."""

    def test_create_and_get_job(self, client):
        """Test creating a job and retrieving it."""
        client_obj, mock_db = client

        # Mock find_one to return the created job
        created_job = {
            "job_id": "test-uuid",
            "name": "Integration Test",
            "url": "https://example.com",
            "status": "active",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "consecutive_failures": 0,
            "tags": [],
            "schedule": "0 */6 * * *",
            "selectors": VALID_JOB["selectors"],
            "method": "GET",
            "settings": {
                "wait_until": "networkidle",
                  "timeout": 30,
                    "pagination": {"type": None, "max_pages": 1}
                    },
            "last_run": None,
            "next_run": datetime.now(UTC),
        }
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=created_job)

        # Create
        response = client_obj.post("/api/v1/jobs", json=VALID_JOB)
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Get
        response = client_obj.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Integration Test"

    def test_create_pause_resume_delete_flow(self, client):
        """Test full lifecycle: create -> pause -> resume -> delete."""
        client_obj, mock_db = client

        job = {
            "job_id": "test-uuid",
            "name": "Integration Test",
            "url": "https://example.com",
            "status": "active",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "consecutive_failures": 0,
            "tags": [],
            "schedule": "0 */6 * * *",
            "selectors": VALID_JOB["selectors"],
            "method": "GET",
            "settings": {
                "wait_until": "networkidle",
                  "timeout": 30,
                    "pagination": {"type": None, "max_pages": 1}
                    },
            "last_run": None,
            "next_run": datetime.now(UTC),
        }
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=job)
        mock_db.scraping_jobs.update_one = AsyncMock()
        mock_db.scraping_jobs.delete_one = AsyncMock(
            return_value=MagicMock(deleted_count=1))

        # Create
        response = client_obj.post("/api/v1/jobs", json=VALID_JOB)
        assert response.status_code == 201

        # Pause
        response = client_obj.post("/api/v1/jobs/test-uuid/pause")
        assert response.status_code == 200

        # Resume
        response = client_obj.post("/api/v1/jobs/test-uuid/resume")
        assert response.status_code == 200

        # Delete
        response = client_obj.delete("/api/v1/jobs/test-uuid")
        assert response.status_code == 204

    def test_list_jobs_pagination(self, client):
        """Test job listing with pagination."""
        client_obj, mock_db = client

        mock_cursor = MagicMock()
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.scraping_jobs.find.return_value = mock_cursor

        response = client_obj.get("/api/v1/jobs?skip=0&limit=10")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_filter_by_status(self, client):
        """Test job filtering by status."""
        client_obj, mock_db = client

        mock_cursor = MagicMock()
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.scraping_jobs.find.return_value = mock_cursor

        response = client_obj.get("/api/v1/jobs?status=active")
        assert response.status_code == 200

    def test_404_on_nonexistent_job(self, client):
        """Test 404 for nonexistent job."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=None)

        response = client_obj.get("/api/v1/jobs/nonexistent")
        assert response.status_code == 404
