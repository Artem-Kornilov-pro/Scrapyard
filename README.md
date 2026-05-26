
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

API available at `http://localhost:8000/docs`

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
GET    /api/v1/jobs/{id}/logs    # Get job logs
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
# Create a scraping job
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
    "schedule": "0 */6 * * *"
  }'

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
