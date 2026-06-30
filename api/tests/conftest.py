from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_real_redis():
    """No test should depend on a reachable Redis, same as MongoDB is
    always mocked. Without this, every TestClient startup tries to
    connect RedisCache instances for real, which can pay a multi-second
    DNS/connect timeout per test if REDIS_URL isn't reachable locally.
    """
    with patch("api.core.cache.RedisCache.connect", new_callable=AsyncMock), \
         patch("api.core.cache.RedisCache.disconnect", new_callable=AsyncMock):
        yield


@pytest.fixture
def client():
    """Create FastAPI test client with mocked MongoDB connection."""
    with patch("api.main.connect_to_mongo", new_callable=AsyncMock), \
         patch("api.main.close_mongo_connection", new_callable=AsyncMock):
        from api.main import app
        with TestClient(app) as test_client:
            yield test_client
