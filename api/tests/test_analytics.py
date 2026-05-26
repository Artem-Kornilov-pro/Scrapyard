from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.services.analytics_service.db") as mock_db:
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


def _make_mock_cursor(return_value):
    """Helper to create a mock cursor with async to_list."""
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=return_value)
    return mock_cursor


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""

    def test_get_job_stats(self, client):
        """Test job stats endpoint."""
        client_obj, mock_db = client
        mock_db.scraped_results.aggregate.return_value = _make_mock_cursor([])

        response = client_obj.get("/api/v1/analytics/jobs/test-id/stats?days=7")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_slowest_jobs(self, client):
        """Test slowest jobs endpoint."""
        client_obj, mock_db = client
        mock_db.scraped_results.aggregate.return_value = _make_mock_cursor([])

        response = client_obj.get("/api/v1/analytics/slowest?limit=3")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_success_rate(self, client):
        """Test success rate endpoint."""
        client_obj, mock_db = client
        mock_db.scraped_results.aggregate.return_value = _make_mock_cursor([
            {"total": 10, "successes": 9, "failures": 1, "success_rate": 90.0}
        ])

        response = client_obj.get("/api/v1/analytics/success-rate")

        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 90.0

    def test_get_overview(self, client):
        """Test overview endpoint."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.count_documents = AsyncMock(side_effect=[10, 5, 3, 2])
        mock_db.scraped_results.count_documents = AsyncMock(return_value=100)

        response = client_obj.get("/api/v1/analytics/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 10
        assert data["active_jobs"] == 5
        assert data["total_results"] == 100
