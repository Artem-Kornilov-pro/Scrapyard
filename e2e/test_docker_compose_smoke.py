"""End-to-end smoke tests run against the live docker-compose stack.

Unlike api/tests and worker/tests, these hit a real running API container
(with a real MongoDB and Redis behind it) over HTTP instead of mocking
dependencies. They are meant to catch integration issues — bad env vars,
broken Dockerfiles, misconfigured service wiring — that unit tests can't see.

Requires the stack to already be up (see .github/workflows/docker-e2e.yml).
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


def test_health_reports_connected_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "scrapyard-api"
    assert body["database"] == "connected"


def test_metrics_endpoint_is_scrapeable(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_job_crud_round_trip(client):
    payload = {
        "name": "e2e-smoke-job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
        "tags": ["e2e"],
    }

    created = client.post("/api/v1/jobs", json=payload)
    assert created.status_code == 201, created.text
    job = created.json()
    job_id = job["job_id"]
    assert job["name"] == payload["name"]
    assert job["status"] == "active"

    fetched = client.get(f"/api/v1/jobs/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["job_id"] == job_id

    listed = client.get("/api/v1/jobs")
    assert listed.status_code == 200
    assert any(j["job_id"] == job_id for j in listed.json())

    deleted = client.delete(f"/api/v1/jobs/{job_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/jobs/{job_id}")
    assert missing.status_code == 404
