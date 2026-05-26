"""Tests for error handling in the API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.services.job_service.db") as mock_db, \
         patch("api.services.job_service.jobs_cache") as mock_jobs_cache, \
         patch("api.services.job_service.analytics_cache") as mock_analytics_cache:
        mock_db.scraping_jobs = MagicMock()
        mock_db.scraping_jobs.insert_one = AsyncMock()
        mock_db.scraping_jobs.find_one = AsyncMock()
        mock_db.scraping_jobs.update_one = AsyncMock()
        mock_db.scraping_jobs.delete_one = AsyncMock()
        mock_db.scraping_jobs.find = MagicMock()
        mock_jobs_cache.delete_pattern = AsyncMock()
        mock_jobs_cache.get = AsyncMock(return_value=None)
        mock_jobs_cache.set = AsyncMock()
        mock_analytics_cache.delete_pattern = AsyncMock()

        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


class TestErrorHandling:
    """Tests for API error handling."""

    def test_invalid_json(self, client):
        """Test malformed JSON returns 422."""
        client_obj, _ = client
        response = client_obj.post(
            "/api/v1/jobs",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test missing required fields returns 422."""
        client_obj, _ = client
        response = client_obj.post("/api/v1/jobs", json={})
        assert response.status_code == 422

    def test_invalid_url_format(self, client):
        """Test invalid URL returns 422."""
        client_obj, _ = client
        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test",
            "url": "not-a-valid-url",
            "selectors": {"items": "div", "fields": {"t": {"selector": "h3"}}},
        })
        assert response.status_code == 422

    def test_invalid_cron_expression(self, client):
        """Test invalid cron returns 422."""
        client_obj, _ = client
        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test",
            "url": "https://example.com",
            "selectors": {"items": "div", "fields": {"t": {"selector": "h3"}}},
            "schedule": "invalid",
        })
        assert response.status_code == 422

    def test_invalid_status_filter(self, client):
        """Test invalid status filter returns 422."""
        client_obj, _ = client
        response = client_obj.get("/api/v1/jobs?status=unknown")
        assert response.status_code == 422

    def test_invalid_pagination_params(self, client):
        """Test negative skip returns 422."""
        client_obj, _ = client
        response = client_obj.get("/api/v1/jobs?skip=-1")
        assert response.status_code == 422

    def test_limit_too_high(self, client):
        """Test limit > 100 returns 422."""
        client_obj, _ = client
        response = client_obj.get("/api/v1/jobs?limit=200")
        assert response.status_code == 422
