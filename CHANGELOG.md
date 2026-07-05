# Changelog

## [Unreleased]

### Fixed (Grafana)
- The provisioned Prometheus datasource had no explicit `uid`, so a failed re-provisioning attempt left a second, broken datasource (empty URL) behind instead of updating the original in place. Pinned `uid: prometheus` and switched the dashboard's panel-level datasource references to the explicit `{type, uid}` form so restarts are idempotent.
- The "Scrapyard Overview" dashboard never visualized the Celery/job-status metrics added by the alerting work — `celery_worker_up`, `celery_task_succeeded_total`/`failed_total`, and `scrapyard_jobs_total` were collected by Prometheus but shown nowhere. Added Celery Task Throughput, Celery Worker Status, Active Jobs, and Jobs by Status panels.

## [1.3.0] — 2026-07-05

### Added (web dashboard)
- `web/` — a React + TypeScript + Vite dashboard: job list with status filters and inline actions (run/pause/resume/delete), a job creation form with a visual selector/field builder and a live "Test selectors" dry-run preview, a job detail page (results, logs, diff between runs, JSON/CSV export), and an analytics page (job-status counts, success rate, slowest jobs chart). Client-side routing with animated page transitions (React Router + Framer Motion), light/dark theme, and an optional locally-stored API key sent as `X-API-Key`.
- `docker/Dockerfile.web` — multi-stage build (Node build → static files served by `nginx-unprivileged`, non-root like the other images) — new `web` service in `docker-compose.yml`/`docker-compose.prod.yml`. `docker/nginx.web.conf` reverse-proxies `/api/*` to the `api` service so the SPA only ever calls same-origin relative URLs — no CORS configuration needed on the API, in dev (Vite's proxy) or prod (nginx) alike.

### Fixed
- `GET /api/v1/jobs` returned a 500 on a warm cache hit. The route cached raw `ScrapingJobInDB` instances; `RedisCache.set()` falls back to `str(obj)` for anything `json.dumps` can't natively serialize, so the cached value became a list of Pydantic repr strings, and FastAPI's response validation rejected it on the next read within the 60s TTL. Found while building the dashboard's job list against a live stack — every second load of the page failed. Fixed by caching `jsonable_encoder(result)` instead.

## [1.2.0] — 2026-07-04

### Added (reliability & scale)
- **Browser pool** — `worker/engines/browser_pool.py` keeps one Chromium instance alive per worker process instead of launching a fresh browser (~1-2s) for every scrape/dry-run. Each task still gets an isolated `BrowserContext` (cookies/cache/storage), only the underlying browser process is shared; a crashed browser is transparently relaunched. Closed cleanly on `worker_process_shutdown`. Verified live: first scrape on a worker process took ~1.6s (cold start), the next three took 0.7-1.0s each, all on the same `ForkPoolWorker`.
- **Per-domain proxy rotation** — `PROXY_URLS` (comma-separated) configures a pool; `worker/utils/proxy.py` deterministically pins each domain to one proxy (hash-based), so a given site consistently exits through the same IP while load spreads across the pool. Wired into both `PlaywrightEngine` (per-context `proxy`) and the scrape/dry-run tasks.
- **Per-domain circuit breaker** — `worker/utils/circuit_breaker.py` tracks consecutive 403/429 responses per domain in Redis. After `CIRCUIT_BREAKER_FAILURE_THRESHOLD` (default 3), the domain is put into cooldown for `CIRCUIT_BREAKER_COOLDOWN_SECONDS` (default 300s): further scrape attempts are deferred via `apply_async(countdown=...)` without touching the site at all, instead of retrying immediately. Verified live against a throwaway HTTP server that always returns 403: the 4th run was deferred in 8ms with zero network calls, versus ~0.5s for each of the three blocked attempts that tripped the breaker.
- `.github/workflows/release.yml` — builds and pushes `api`/`worker`/`beat` images to `ghcr.io` on every `v*` tag.

### Added (observability: alerting & tracing)
- **Alerting** — `docker/prometheus-alerts.yml` + a new `alertmanager` service cover the three gaps called out for going to production: `ScrapyardWorkerDown` (no Celery heartbeat for 2m), `ScrapyardNoTasksProcessedRecently` (zero task successes in 5m — catches a worker that's up but not draining its queue), `ScrapyardHighApiErrorRate` (>5% API 5xx over 5m), and `ScrapyardJobsInErrorState` (any job stuck at 5+ consecutive failures). `alertmanager.yml` ships with a documented no-op receiver — alerts are visible in its UI/API immediately, wire in Slack/webhook for real notifications. Worker/task metrics come from a new `celery-exporter` service (`celery_worker_up`, `celery_task_succeeded_total`, etc.); job-status counts come from a new `scrapyard_jobs_total{status=...}` gauge on `/metrics`, refreshed from MongoDB at scrape time. Verified live end-to-end: stopped the worker, watched `celery_worker_up` drop, the rule transition to `firing`, and the alert land in Alertmanager.
- **Tracing** — OpenTelemetry spans across the API, Celery tasks, MongoDB (via PyMongo/Motor), and Redis, exported to a bundled `jaeger` service (`ENABLE_TRACING`, off by default outside docker-compose). Celery instrumentation and the tracer's background export thread are initialized via `worker_process_init`/`beat_init` rather than at import time, since a `BatchSpanProcessor`'s thread doesn't survive Celery's prefork `fork()`. Verified live: a scrape job's trace shows `run/worker.tasks.scrape_job` (1.4s) broken down into its MongoDB inserts/updates and Redis calls — exactly the "why was this run slow" view this was meant to give.

## [1.1.0] — 2026-07-04

### Added (CI)
- `.github/workflows/docker-e2e.yml` — builds the `docker-compose.yml` images and brings up the full stack (MongoDB, Redis, api, worker, beat), then runs end-to-end smoke tests (`e2e/`) against the live API over HTTP: health check, `/metrics` scrape, and a job create/read/list/delete round trip. Runs on every push/PR to `master` alongside the existing unit test workflow.

### Fixed (CI)
- `Settings` (`api/core/config.py`) rejected unknown env vars by default; `GRAFANA_PASSWORD` in `.env.example` is only consumed by `docker-compose.yml`'s interpolation, not the app, so `api`/`worker`/`beat` crashed on startup for anyone following the documented `cp .env.example .env && docker-compose up -d` setup. Caught by the new `docker-e2e` workflow.

### Fixed (pre-release hardening)
- **Critical:** the worker's headless Chromium could never actually launch in Docker. `python:3.12-slim` now tracks Debian trixie, which Playwright 1.49 doesn't recognize; `playwright install-deps chromium` failed on unresolvable trixie package names and the failure was silently swallowed by `|| true`, so the image built "successfully" without the shared libraries Chromium needs (libnss3, libatk, etc.). Every real scrape would have failed on browser launch. Fixed by pinning `docker/Dockerfile.{api,worker,beat}` to `python:3.12-slim-bookworm` and removing the `|| true`. Verified by actually launching Chromium and running a live scrape job inside the built container.
- **Critical:** `worker.tasks.sync_scheduled_jobs` (the Celery Beat task that dispatches due cron jobs every minute) never connected to MongoDB — only `api/main.py`'s FastAPI lifespan and `ScrapingTask.setup()` did. On a real worker, this hit `assert db.scraping_jobs is not None` on every single run, meaning scheduled jobs never actually got dispatched. Missed by the test suite because `worker/tests/test_scheduler.py` mocks `db` directly. Added `api.core.database.ensure_connected()` (idempotent connect-if-needed) and used it in both `scheduler.py` and `scraper.py`, replacing two independent ad-hoc connection trackers that could otherwise leak duplicate `AsyncIOMotorClient`s in the same worker process.
- `PlaywrightEngine.launch()` started a Playwright driver process via `async_playwright().start()` but never stored or stopped it in `close()` — only the browser was closed. Every scrape and dry-run leaked a driver process. Now stopped alongside the browser.
- `api/core/security.py` compared the `X-API-Key` header with `!=`, which is vulnerable to a timing attack; switched to `secrets.compare_digest`.
- `docker/Dockerfile.{api,worker,beat}` ran the app as root. Added a non-root `appuser` in all three.
- Added `.dockerignore` — the build context previously included `.git`, caches, and test files.
- `.github/workflows/tests.yml`'s coverage gate was `coverage report --fail-under=75 || echo "..."`, which meant it could never actually fail the build regardless of coverage. Removed the fallback.
- Removed the obsolete `version:` key from `docker-compose.yml` (silently ignored by Compose v2, just a warning on every command).

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