"""Tests for Redis-backed rate limiting."""

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
def reset_rate_limit_setting():
    original = settings.rate_limit_per_minute
    yield
    settings.rate_limit_per_minute = original


class TestRateLimit:
    """Tests for the enforce_rate_limit dependency."""

    def test_under_limit_succeeds(self, client):
        settings.rate_limit_per_minute = 5
        with patch(
            "api.core.rate_limit.rate_limit_cache.increment",
            new=AsyncMock(return_value=1),
        ):
            response = client.get("/api/v1/jobs")
        assert response.status_code == 200

    def test_exceeding_limit_returns_429(self, client):
        settings.rate_limit_per_minute = 5
        with patch(
            "api.core.rate_limit.rate_limit_cache.increment",
            new=AsyncMock(return_value=6),
        ):
            response = client.get("/api/v1/jobs")
        assert response.status_code == 429

    def test_disabled_when_limit_is_zero(self, client):
        """rate_limit_per_minute <= 0 disables the check entirely."""
        settings.rate_limit_per_minute = 0
        with patch(
            "api.core.rate_limit.rate_limit_cache.increment",
            new=AsyncMock(side_effect=AssertionError("should not be called")),
        ):
            response = client.get("/api/v1/jobs")
        assert response.status_code == 200

    def test_redis_unavailable_fails_open(self, client):
        """increment() returning 0 (Redis down) never triggers a 429."""
        settings.rate_limit_per_minute = 5
        with patch(
            "api.core.rate_limit.rate_limit_cache.increment",
            new=AsyncMock(return_value=0),
        ):
            response = client.get("/api/v1/jobs")
        assert response.status_code == 200

    def test_health_check_not_rate_limited(self, client):
        """Health check has no rate-limit dependency."""
        settings.rate_limit_per_minute = 1
        with patch(
            "api.core.rate_limit.rate_limit_cache.increment",
            new=AsyncMock(side_effect=AssertionError("should not be called")),
        ):
            response = client.get("/health")
        assert response.status_code == 200
