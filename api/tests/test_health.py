from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked MongoDB."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock):
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client


def test_health_check_no_db(client):
    """Test health check when database is not connected."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "scrapyard-api"
    assert data["database"] == "disconnected"


def test_health_check_with_db(client):
    """Test health check when database is connected."""
    # Создаем мок-клиент
    mock_admin = AsyncMock()
    mock_admin.command = AsyncMock(return_value={"ok": 1})

    mock_client = AsyncMock()
    mock_client.admin = mock_admin

    # Патчим правильный путь: api.core.database.db
    with patch("api.core.database.db") as mock_db:
        mock_db.client = mock_client

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"
