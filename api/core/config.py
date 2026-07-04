from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "scrapyard"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Debug
    debug: bool = False

    # Security
    # Empty string disables auth (local dev / tests). Set in production to
    # require the X-API-Key header on every /api/v1 request.
    api_key: str = ""
    rate_limit_per_minute: int = 120

    # Scraping etiquette
    scraper_user_agent: str = (
        "ScrapyardBot/1.0 (+https://github.com/Artem-Kornilov-pro/scrapyard)"
    )
    respect_robots_txt: bool = True
    # Minimum seconds between scrape requests to the same domain, enforced
    # across all workers via a Redis lock. 0 disables throttling.
    domain_throttle_seconds: float = 2.0

    # How long the API waits for a worker to finish a dry run before
    # giving up and returning 504.
    dry_run_timeout_seconds: int = 30

    # Comma-separated proxy URLs (e.g. "http://user:pass@p1:8080,http://p2:8080").
    # Empty disables proxying -- scrapes go out directly.
    proxy_urls: str = ""

    # Consecutive 403/429 responses from a domain before the circuit
    # breaker opens and defers scrapes to that domain for a cooldown period.
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 300

    # OpenTelemetry tracing across api -> Celery -> MongoDB/Redis. Off by
    # default (e.g. for bare `uvicorn api.main:app` or tests, where
    # there's no collector to send spans to); docker-compose enables it
    # via .env.example since Jaeger is bundled there.
    enable_tracing: bool = False
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"

    @property
    def proxy_list(self) -> list[str]:
        """Parsed, whitespace-trimmed list of configured proxy URLs."""
        return [p.strip() for p in self.proxy_urls.split(",") if p.strip()]


settings = Settings()
