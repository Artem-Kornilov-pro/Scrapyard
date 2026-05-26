from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.services.analytics_service.analytics_cache") as mock_analytics, \
         patch("api.services.job_service.jobs_cache") as mock_jobs, \
         patch("api.services.job_service.analytics_cache") as mock_analytics_svc, \
         patch("api.services.job_service.db") as mock_db:
        mock_db.scraping_jobs = MagicMock()
        mock_db.scraping_jobs.insert_one = AsyncMock()
        mock_analytics_svc.delete_pattern = AsyncMock()
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_analytics, mock_jobs


class TestCache:
    """Tests for Redis caching."""

    def test_analytics_cache_hit(self, client):
        """Test that cached analytics data is returned."""
        client_obj, mock_analytics, _ = client
        mock_analytics.get = AsyncMock(return_value=[{"test": "cached"}])

        response = client_obj.get("/api/v1/analytics/overview")
        assert response.status_code == 200
        assert response.json() == [{"test": "cached"}]

    def test_jobs_cache_invalidation_on_create(self, client):
        """Test cache is invalidated when job is created."""
        client_obj, _, mock_jobs = client
        mock_jobs.delete_pattern = AsyncMock()

        response = client_obj.post("/api/v1/jobs", json={
            "name": "Test",
            "url": "https://example.com",
            "selectors": {"items": "div", "fields": {"title": {"selector": "h3"}}},
        })
        assert response.status_code == 201
        mock_jobs.delete_pattern.assert_any_call("jobs:*")
