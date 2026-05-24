import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create FastAPI test client with mocked MongoDB connection."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock):
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client