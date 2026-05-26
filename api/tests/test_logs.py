from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock), \
         patch("api.routes.logs.db") as mock_db:
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client, mock_db


def _make_mock_cursor(return_value):
    """Helper to create a mock cursor with async to_list."""
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.skip = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=return_value)
    return mock_cursor


class TestLogsEndpoints:
    """Tests for logs API endpoints."""

    def test_get_job_logs(self, client):
        """Test getting logs for a job."""
        client_obj, mock_db = client
        mock_db.job_logs.find.return_value = _make_mock_cursor([
            {"job_id": "test", "status": "completed"},
        ])

        response = client_obj.get("/api/v1/jobs/test-id/logs")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_job_logs_empty(self, client):
        """Test getting logs for a job with no logs."""
        client_obj, mock_db = client
        mock_db.job_logs.find.return_value = _make_mock_cursor([])

        response = client_obj.get("/api/v1/jobs/test-id/logs")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_logs(self, client):
        """Test getting all logs."""
        client_obj, mock_db = client
        mock_db.job_logs.find.return_value = _make_mock_cursor([
            {"job_id": "job-1", "status": "completed"},
            {"job_id": "job-2", "status": "failed"},
        ])

        response = client_obj.get("/api/v1/logs")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_logs_by_status(self, client):
        """Test filtering logs by status."""
        client_obj, mock_db = client
        mock_db.job_logs.find.return_value = _make_mock_cursor([])

        response = client_obj.get("/api/v1/logs?status=failed")
        assert response.status_code == 200
