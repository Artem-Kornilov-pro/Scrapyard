"""Route-level tests for POST /dry-run and POST /{job_id}/run."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

VALID_SELECTORS = {
    "items": "div.product",
    "fields": {"title": {"selector": "h3", "attr": "text"}},
}


@pytest.fixture
def client():
    """Create test client with mocked MongoDB connection."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock):
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client


class TestDryRunEndpoint:
    """Tests for POST /api/v1/jobs/dry-run."""

    def test_success(self, client):
        with patch(
            "api.routes.jobs.JobService.dry_run",
            new=AsyncMock(return_value={
                "success": True,
                "items_count": 1,
                "items": [{"title": "A"}],
                "truncated": False,
                "error": None,
            }),
        ):
            response = client.post("/api/v1/jobs/dry-run", json={
                "url": "https://example.com",
                "selectors": VALID_SELECTORS,
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["items"] == [{"title": "A"}]

    def test_timeout_returns_504(self, client):
        with patch(
            "api.routes.jobs.JobService.dry_run", new=AsyncMock(return_value=None)
        ):
            response = client.post("/api/v1/jobs/dry-run", json={
                "url": "https://example.com",
                "selectors": VALID_SELECTORS,
            })

        assert response.status_code == 504

    def test_invalid_url_returns_422(self, client):
        response = client.post("/api/v1/jobs/dry-run", json={
            "url": "not-a-url",
            "selectors": VALID_SELECTORS,
        })
        assert response.status_code == 422

    def test_invalid_selectors_returns_422(self, client):
        response = client.post("/api/v1/jobs/dry-run", json={
            "url": "https://example.com",
            "selectors": {"items": "div"},
        })
        assert response.status_code == 422


class TestRunNowEndpoint:
    """Tests for POST /api/v1/jobs/{job_id}/run."""

    def test_success_returns_202(self, client):
        with patch(
            "api.routes.jobs.JobService.run_now",
            new=AsyncMock(return_value={
                "job_id": "job-1", "task_id": "task-abc", "status": "dispatched",
            }),
        ):
            response = client.post("/api/v1/jobs/job-1/run")

        assert response.status_code == 202
        assert response.json()["status"] == "dispatched"

    def test_missing_job_returns_404(self, client):
        with patch(
            "api.routes.jobs.JobService.run_now", new=AsyncMock(return_value=None)
        ):
            response = client.post("/api/v1/jobs/missing/run")

        assert response.status_code == 404
