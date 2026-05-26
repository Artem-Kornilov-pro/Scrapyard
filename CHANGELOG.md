# Changelog

## [0.1.0] — 2026-05-26

### Added
- FastAPI application with health check and CRUD API for scraping jobs
- MongoDB integration with Motor async driver and index management
- Pydantic models for job and result validation
- Celery task for Playwright-based web scraping
- Celery Beat scheduler for periodic job execution
- Generic CSS-selector parser with transform functions
- Pagination support (URL, click, scroll)
- MongoDB analytics with aggregation pipelines
- Job logging with Time Series collection
- Redis caching for analytics and job lists
- GitHub Actions CI/CD with Ruff, Mypy, and Pytest
- Docker deployment with docker-compose
- Bilingual documentation (EN/RU)