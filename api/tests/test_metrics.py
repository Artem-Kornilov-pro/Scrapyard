"""Tests for the Prometheus /metrics endpoint and instrumentation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock):
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client


class TestMetricsEndpoint:
    """Tests for GET /metrics."""

    def test_metrics_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type_is_prometheus_format(self, client):
        response = client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_request_counter(self, client):
        """After making a request, http_requests_total should appear."""
        client.get("/health")
        response = client.get("/metrics")
        assert "http_requests_total" in response.text

    def test_metrics_contains_latency_histogram(self, client):
        client.get("/health")
        response = client.get("/metrics")
        assert "http_request_duration_seconds" in response.text

    def test_metrics_not_authenticated(self, client):
        """/metrics is intentionally unauthenticated (like /health)."""
        from api.core.config import settings
        original = settings.api_key
        try:
            settings.api_key = "secret-key"
            response = client.get("/metrics")
        finally:
            settings.api_key = original
        assert response.status_code == 200

    def test_path_templating_avoids_high_cardinality(self, client):
        """Middleware must record route template, not raw path."""
        with patch("api.services.job_service.db") as mock_db:
            mock_db.scraping_jobs = MagicMock()
            mock_db.scraping_jobs.find_one = AsyncMock(return_value=None)
            client.get("/api/v1/jobs/some-uuid-123")

        response = client.get("/metrics")
        body = response.text
        # route template should appear, not the raw UUID
        assert "/api/v1/jobs/{job_id}" in body
        assert "some-uuid-123" not in body
