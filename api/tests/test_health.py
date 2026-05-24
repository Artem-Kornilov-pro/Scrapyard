import pytest
from fastapi.testclient import TestClient
from api.main import app


def test_health_check():
    """Test health check endpoint returns 200 and correct response."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "scrapyard-api"
    }