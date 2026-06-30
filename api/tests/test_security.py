"""Tests for API key authentication."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.core.config import settings


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
         patch("api.services.job_service.db") as mock_db, \
         patch("api.services.job_service.jobs_cache") as mock_jobs_cache, \
         patch("api.services.job_service.analytics_cache") as mock_analytics_cache:
        mock_db.scraping_jobs = MagicMock()
        mock_db.scraping_jobs.find = MagicMock(return_value=_make_mock_cursor([]))
        mock_jobs_cache.delete_pattern = AsyncMock()
        mock_jobs_cache.get = AsyncMock(return_value=None)
        mock_jobs_cache.set = AsyncMock()
        mock_analytics_cache.delete_pattern = AsyncMock()

        from api.main import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(autouse=True)
def reset_api_key():
    """Ensure tests don't leak an api_key override into each other."""
    original = settings.api_key
    yield
    settings.api_key = original


class TestApiKeyDisabled:
    """When API_KEY is unset (default), auth is a no-op."""

    def test_request_without_header_succeeds(self, client):
        settings.api_key = ""
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200


class TestApiKeyEnabled:
    """When API_KEY is configured, it's required on protected routes."""

    def test_missing_header_returns_401(self, client):
        settings.api_key = "secret-key"
        response = client.get("/api/v1/jobs")
        assert response.status_code == 401

    def test_wrong_header_returns_401(self, client):
        settings.api_key = "secret-key"
        response = client.get(
            "/api/v1/jobs", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_correct_header_succeeds(self, client):
        settings.api_key = "secret-key"
        response = client.get(
            "/api/v1/jobs", headers={"X-API-Key": "secret-key"}
        )
        assert response.status_code == 200

    def test_health_check_stays_public(self, client):
        """Health check has no auth dependency — needed for orchestrators."""
        settings.api_key = "secret-key"
        response = client.get("/health")
        assert response.status_code == 200
