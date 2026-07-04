from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_mongo_singleton():
    """Reset the shared MongoDB singleton after every test.

    api.core.database.db is a module-level singleton. Tests that touch
    it directly instead of patching it (e.g. test_database.py, which
    exercises the real connect_to_mongo()) would otherwise leak a
    stale db.scraping_jobs mock into unrelated tests that read it --
    such as the /metrics job-status gauges, which call
    count_documents() on whatever db.scraping_jobs happens to be.
    """
    yield
    from api.core.database import db

    db.client = None
    db.db = None
    db.scraping_jobs = None
    db.scraped_results = None
    db.job_logs = None


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
