# Changelog

## [Unreleased]

### Added (observability + error handling)
- `GET /metrics` — Prometheus scrape target with request count/latency histogram by route template and status code; implemented as a pure ASGI middleware to avoid interference with exception handling
- `docker/prometheus.yml` — scrape config for the API and redis-exporter
- Prometheus + Grafana + redis-exporter services in `docker-compose.yml` and `docker-compose.prod.yml`; Grafana auto-provisions its datasource and a "Scrapyard Overview" dashboard via provisioning files (request rate, P95 latency, error rate, Redis memory/clients)
- Global 500 exception handler in `api/core/errors.py` — all unhandled exceptions are logged with full tracebacks; the JSON response body includes the exception message only when `DEBUG=true`, so production responses never leak internals
- `prometheus_client==0.25.0` added to `requirements.txt`

### Added (job utility endpoints)
- `POST /api/v1/jobs/dry-run` — test selectors against a live page without saving a job
- `POST /api/v1/jobs/{id}/run` — dispatch a job immediately, bypassing its cron schedule
- `GET /api/v1/jobs/{id}/results` — list a job's scrape results
- `GET /api/v1/jobs/{id}/results/export` — export a run's items as JSON or CSV
- `GET /api/v1/jobs/{id}/results/diff` — diff two runs (defaults to the two most recent); per-field diffing when a job sets `diff_key`
- Webhook notifications (`notify_webhook` on a job) fire when a job hits 5 consecutive failures and is marked `error`

### Fixed
- `parse_with_selectors` called Playwright's `ElementHandle.inner_text()`/`get_attribute()` with a selector argument they don't accept — every field extraction with `attr: "text"` (or any non-default attribute) silently failed in real scraping. Now resolves each field's sub-element via `query_selector()` first.
- `sync_scheduled_jobs` and the new `run_now` both passed a raw MongoDB document (including the non-JSON-serializable `_id` ObjectId) straight into a Celery task payload
- `GET /api/v1/logs` and `GET /api/v1/jobs/{id}/logs` returned raw MongoDB documents including `_id`, which FastAPI can't serialize

## [1.0.0] — 2026-05-26

### Initial Release

#### API
- FastAPI application with health check
- CRUD API for scraping jobs (create, read, update, delete)
- Job lifecycle management (pause, resume)
- Request validation with Pydantic models
- Pagination and filtering (status, tags)

#### Database
- MongoDB integration with Motor async driver
- Time Series collection for job logs
- TTL indexes for automatic data cleanup
- Aggregation pipelines for analytics

#### Scraping Engine
- Playwright browser engine with async context manager
- Generic CSS-selector parser with transform functions
- Multi-page scraping (URL, click, scroll pagination)
- Celery task for distributed scraping execution

#### Analytics
- Per-job daily statistics (runs, items, duration, errors)
- Top slowest jobs report
- Success rate calculation
- System overview dashboard

#### Infrastructure
- Celery Beat scheduler for periodic jobs
- Redis caching for analytics and job lists
- Docker deployment with docker-compose (5 services)
- Health checks for all services
- GitHub Actions CI/CD (Ruff, Mypy, Pytest with coverage)

#### Documentation
- Bilingual README (English, Russian)
- Architecture diagram
- API usage examples with curl
- CONTRIBUTING.md with conventional commits guide
- CHANGELOG.md

### Tech Stack
- **Python 3.12** + FastAPI
- **MongoDB 7.0** + Motor
- **Celery** + Redis
- **Playwright** (Chromium)
- **Docker** + docker-compose