
# 🕸️ Scrapyard — Web Scraper as a Service

[![Tests](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml/badge.svg)](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | [Русский](README_RU.md)

Distributed web scraping platform. Schedule scraping jobs via REST API, execute them with Playwright, and analyze results with MongoDB aggregations.

---

## 🎯 Features

- 📅 **Scheduled jobs** — cron expressions for periodic data collection
- 🧩 **Generic parser** — define CSS selectors via API, no code needed
- 🌐 **Playwright** — full JavaScript/SPA support
- 📊 **Analytics** — MongoDB aggregations for per-job statistics
- 🔄 **Auto-cleanup** — TTL indexes for old results
- ⚡ **Redis caching** — analytics cached for 5min, job lists for 1min
- 🔐 **API key auth & rate limiting** — optional `X-API-Key` header, Redis-backed per-IP limits
- 🤖 **Scraping etiquette** — respects `robots.txt`, throttles concurrent requests per domain
- 📈 **Grafana + Prometheus** — request rate/latency/errors dashboard, Redis metrics, auto-provisioned
- 🛡️ **Global 500 handler** — all unhandled exceptions logged with tracebacks, safe JSON response to clients
- 🐳 **Docker** — one-command startup for all services

---

## 🛠️ Tech Stack

| Component   | Technology                  | Why |
|-------------|----------------------------|-----|
| API         | FastAPI (async)            | High performance, auto docs |
| Database    | MongoDB + Motor            | Flexible schemas, async driver |
| Queue       | Celery + Redis             | Reliable task distribution |
| Scraping    | Playwright                 | JavaScript rendering support |
| Caching     | Redis                      | Fast analytics responses |
| CI/CD       | GitHub Actions             | Tests, linting, coverage |
| Containers  | Docker, docker-compose     | Easy deployment |

---

## 🏗️ Architecture

```
                    ┌─────────────┐
                    │   Celery    │
                    │    Beat     │
                    └──────┬──────┘
                           │ schedule jobs
                           ▼
┌──────────┐     ┌─────────────────┐     ┌──────────────┐
│  Client  │────▶│   FastAPI       │────▶│    Redis     │
│          │     │   (REST API)    │     │   (Broker)   │
└──────────┘     └─────────────────┘     └──────┬───────┘
       ▲                                       │
       │                                       ▼
       │                              ┌─────────────────┐
       │                              │  Celery Worker  │
       │                              │  (Playwright)   │
       │                              └────────┬────────┘
       │                                       │
       │                                       ▼
       │                              ┌─────────────────┐
       └──────────────────────────────│    MongoDB      │
                                      │ (jobs, results, │
                                      │     logs)       │
                                      └─────────────────┘
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/Artem-Kornilov-pro/scrapyard.git
cd scrapyard
cp .env.example .env
docker-compose up -d
```

| Service | URL |
|---------|-----|
| API (Swagger UI) | `http://localhost:8000/docs` |
| Prometheus metrics | `http://localhost:8000/metrics` |
| Prometheus UI | `http://localhost:9090` |
| Grafana | `http://localhost:3000` (admin / admin) |

The "Scrapyard Overview" Grafana dashboard is auto-provisioned. It shows request rate by status code, P95 latency, error rate, and Redis stats.

---

## 🔒 Production checklist

These are off by default for a frictionless local setup, but should be configured before exposing the API publicly:

| Setting | Default | Effect |
|---------|---------|--------|
| `API_KEY` | unset (auth disabled) | When set, every `/api/v1/*` request must send a matching `X-API-Key` header |
| `RATE_LIMIT_PER_MINUTE` | `120` | Per-IP request limit on `/api/v1/*`, backed by Redis; `0` disables it |
| `RESPECT_ROBOTS_TXT` | `true` | Worker checks the target site's `robots.txt` before scraping and skips disallowed URLs |
| `DOMAIN_THROTTLE_SECONDS` | `2.0` | Minimum gap between scrape requests to the same domain, enforced across all workers via a Redis lock |
| `SCRAPER_USER_AGENT` | `ScrapyardBot/1.0 (+https://github.com/...)` | User-Agent sent by the browser and matched against `robots.txt` rules |
| `DRY_RUN_TIMEOUT_SECONDS` | `30` | How long the API waits for a worker to finish a `/dry-run` before returning 504 |

Redis-backed features (caching, rate limiting, domain throttling) fail open: if Redis is unreachable, the API and workers keep running without that protection rather than going down. `/health` is never authenticated or rate-limited, so orchestrators can always probe it.

```bash
# with API_KEY set
curl http://localhost:8000/api/v1/jobs -H "X-API-Key: <your-key>"
```

---

## 📡 API Endpoints

### Jobs

```http
POST   /api/v1/jobs              # Create a job
GET    /api/v1/jobs              # List jobs (with pagination)
GET    /api/v1/jobs/{id}         # Get job details
PUT    /api/v1/jobs/{id}         # Update job
DELETE /api/v1/jobs/{id}         # Delete job
POST   /api/v1/jobs/{id}/pause   # Pause job
POST   /api/v1/jobs/{id}/resume  # Resume job
POST   /api/v1/jobs/{id}/run     # Run a job immediately, bypassing its schedule
POST   /api/v1/jobs/dry-run      # Test selectors against a live page without saving a job
GET    /api/v1/jobs/{id}/logs    # Get job logs
```

### Results

```http
GET    /api/v1/jobs/{id}/results         # List scrape results (most recent first)
GET    /api/v1/jobs/{id}/results/export  # Export a run's items as JSON or CSV
GET    /api/v1/jobs/{id}/results/diff    # Diff two runs (defaults to the two most recent)
```

### Analytics

```http
GET    /api/v1/analytics/overview        # System overview
GET    /api/v1/analytics/jobs/{id}/stats # Per-job statistics
GET    /api/v1/analytics/slowest         # Top slowest jobs
GET    /api/v1/analytics/success-rate    # Overall success rate
GET    /api/v1/logs                      # All logs (filterable)
```

### Examples

```bash
# Test selectors before saving a job
curl -X POST http://localhost:8000/api/v1/jobs/dry-run \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/products",
    "selectors": {
      "items": "div.product-card",
      "fields": {"title": {"selector": "h3.title", "attr": "text"}}
    }
  }'

# Create a scraping job — notify_webhook fires once the job hits 5
# consecutive failures; diff_key matches items across runs for /diff
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Prices",
    "url": "https://example.com/products",
    "selectors": {
      "items": "div.product-card",
      "fields": {
        "title": {"selector": "h3.title", "attr": "text"},
        "price": {"selector": "span.price", "attr": "text", "transform": "strip_currency"}
      }
    },
    "schedule": "0 */6 * * *",
    "diff_key": "title",
    "notify_webhook": "https://hooks.example.com/scrapyard-alerts"
  }'

# Run it right now instead of waiting for the schedule
curl -X POST http://localhost:8000/api/v1/jobs/{id}/run

# See what changed since the last run
curl http://localhost:8000/api/v1/jobs/{id}/results/diff

# Export the latest run as CSV
curl http://localhost:8000/api/v1/jobs/{id}/results/export?format=csv

# Get analytics overview
curl http://localhost:8000/api/v1/analytics/overview
```

---

## 📁 Project Structure

```
scrapyard/
├── api/                    # FastAPI application
│   ├── core/               # Config, database, cache
│   ├── models/             # Pydantic models
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   └── tests/              # API tests
├── worker/                 # Celery worker
│   ├── engines/            # Playwright engine, parsers
│   ├── tasks/              # Celery tasks (scraper, scheduler)
│   └── tests/              # Worker tests
├── scripts/                # Benchmark script
├── docker/                 # Dockerfiles
├── .github/workflows/      # CI/CD
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
