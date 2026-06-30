"""Route-level tests for /api/v1/jobs/{job_id}/results and /export."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_mock_cursor(return_value):
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=return_value)
    return mock_cursor


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.routes.results.db") as mock_db:
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


class TestListResults:
    """Tests for GET /api/v1/jobs/{job_id}/results."""

    def test_returns_results_for_job(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find.return_value = _make_mock_cursor([
            {"run_id": "r1", "job_id": "job-1", "items_count": 2},
        ])

        response = client_obj.get("/api/v1/jobs/job-1/results")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_empty_when_no_results(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find.return_value = _make_mock_cursor([])

        response = client_obj.get("/api/v1/jobs/job-1/results")

        assert response.status_code == 200
        assert response.json() == []

    def test_excludes_object_id_from_query(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find.return_value = _make_mock_cursor([])

        client_obj.get("/api/v1/jobs/job-1/results")

        call_args = mock_db.scraped_results.find.call_args[0]
        assert call_args[1] == {"_id": 0}


class TestExportResults:
    """Tests for GET /api/v1/jobs/{job_id}/results/export."""

    def test_export_json_defaults_to_latest_run(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find_one = AsyncMock(return_value={
            "run_id": "r1",
            "items": [{"title": "A", "price": 10}],
        })

        response = client_obj.get("/api/v1/jobs/job-1/results/export")

        assert response.status_code == 200
        assert response.json() == [{"title": "A", "price": 10}]

    def test_export_specific_run_id(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find_one = AsyncMock(return_value={
            "run_id": "r2",
            "items": [{"title": "B"}],
        })

        response = client_obj.get(
            "/api/v1/jobs/job-1/results/export?run_id=r2"
        )

        assert response.status_code == 200
        mock_db.scraped_results.find_one.assert_called_once()
        call_args = mock_db.scraped_results.find_one.call_args[0]
        assert call_args[0] == {"job_id": "job-1", "run_id": "r2"}

    def test_export_csv(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find_one = AsyncMock(return_value={
            "run_id": "r1",
            "items": [
                {"title": "A", "price": 10},
                {"title": "B", "price": 20},
            ],
        })

        response = client_obj.get(
            "/api/v1/jobs/job-1/results/export?format=csv"
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        body = response.text
        assert "title,price" in body
        assert "A,10" in body
        assert "B,20" in body

    def test_export_csv_empty_items(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find_one = AsyncMock(return_value={
            "run_id": "r1", "items": [],
        })

        response = client_obj.get(
            "/api/v1/jobs/job-1/results/export?format=csv"
        )

        assert response.status_code == 200
        assert response.text == ""

    def test_no_results_returns_404(self, client):
        client_obj, mock_db = client
        mock_db.scraped_results.find_one = AsyncMock(return_value=None)

        response = client_obj.get("/api/v1/jobs/job-1/results/export")

        assert response.status_code == 404

    def test_invalid_format_returns_422(self, client):
        client_obj, _ = client
        response = client_obj.get(
            "/api/v1/jobs/job-1/results/export?format=xml"
        )
        assert response.status_code == 422


class TestDiffResultsEndpoint:
    """Tests for GET /api/v1/jobs/{job_id}/results/diff.

    AnalyticsService.get_diff uses its own `db` import, separate from
    the one routes/results.py uses directly — both must be patched.
    """

    def test_not_enough_runs_returns_404(self, client):
        client_obj, _ = client
        with patch("api.services.analytics_service.db") as mock_analytics_db:
            mock_analytics_db.scraped_results.find.return_value = _make_mock_cursor([
                {"run_id": "r1", "items": [], "timestamp": datetime.now(UTC)}
            ])
            response = client_obj.get("/api/v1/jobs/job-1/results/diff")

        assert response.status_code == 404

    def test_returns_diff_for_two_runs(self, client):
        client_obj, _ = client
        now = datetime.now(UTC)
        with patch("api.services.analytics_service.db") as mock_analytics_db:
            mock_analytics_db.scraped_results.find.return_value = _make_mock_cursor([
                {"run_id": "r2", "items": [{"title": "B"}], "timestamp": now},
                {"run_id": "r1", "items": [{"title": "A"}], "timestamp": now},
            ])
            mock_analytics_db.scraping_jobs.find_one = AsyncMock(
                return_value={"job_id": "job-1", "diff_key": None}
            )
            response = client_obj.get("/api/v1/jobs/job-1/results/diff")

        assert response.status_code == 200
        data = response.json()
        assert data["added"] == [{"title": "B"}]
        assert data["removed"] == [{"title": "A"}]
