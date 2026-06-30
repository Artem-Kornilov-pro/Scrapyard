"""Tests for error handling in the API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.core.config import settings


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


class TestGlobalExceptionHandler:
    """Tests for the catch-all 500 handler.

    Starlette re-raises the exception after calling the handler so that
    middleware finalizers can run — TestClient catches this and re-raises
    unless `raise_server_exceptions=False` is set. The unit-test approach
    below calls the handler function directly to avoid this framework
    wrapping and test only the handler's own logic.
    """

    @pytest.fixture(autouse=True)
    def reset_debug(self):
        original = settings.debug
        yield
        settings.debug = original

    @pytest.mark.asyncio
    async def test_returns_500_json_response(self):
        from fastapi import Request

        from api.core.errors import unhandled_exception_handler

        scope = {"type": "http", "method": "GET", "path": "/api/v1/jobs/x",
                 "query_string": b"", "headers": []}
        request = Request(scope)
        response = await unhandled_exception_handler(request, RuntimeError("boom"))

        assert response.status_code == 500
        import json
        body = json.loads(response.body)
        assert body["error"] == "internal_server_error"

    @pytest.mark.asyncio
    async def test_debug_false_hides_detail(self):
        from fastapi import Request

        from api.core.errors import unhandled_exception_handler

        settings.debug = False
        scope = {"type": "http", "method": "GET", "path": "/",
                 "query_string": b"", "headers": []}
        request = Request(scope)
        response = await unhandled_exception_handler(
            request, RuntimeError("sensitive internal detail")
        )

        import json
        body = json.loads(response.body)
        assert "sensitive internal detail" not in body["detail"]
        assert body["detail"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_debug_true_includes_detail(self):
        from fastapi import Request

        from api.core.errors import unhandled_exception_handler

        settings.debug = True
        scope = {"type": "http", "method": "GET", "path": "/",
                 "query_string": b"", "headers": []}
        request = Request(scope)
        response = await unhandled_exception_handler(
            request, RuntimeError("sensitive internal detail")
        )

        import json
        body = json.loads(response.body)
        assert "sensitive internal detail" in body["detail"]

    def test_http_exceptions_still_return_their_own_status(self, client):
        """404/422 etc. must NOT be swallowed by the Exception handler."""
        client_obj, mock_db = client
        mock_db.scraping_jobs.find_one = AsyncMock(return_value=None)
        response = client_obj.get("/api/v1/jobs/nonexistent")

        assert response.status_code == 404
