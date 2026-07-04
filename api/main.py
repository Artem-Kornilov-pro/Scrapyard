from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from api.core.cache import analytics_cache, jobs_cache, rate_limit_cache
from api.core.database import close_mongo_connection, connect_to_mongo
from api.core.errors import unhandled_exception_handler
from api.core.metrics import PrometheusMiddleware, metrics_endpoint
from api.core.tracing import setup_tracing
from api.routes import analytics, jobs, logs, results

setup_tracing("scrapyard-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await connect_to_mongo()
    await jobs_cache.connect()
    await analytics_cache.connect()
    await rate_limit_cache.connect()
    yield
    await jobs_cache.disconnect()
    await analytics_cache.disconnect()
    await rate_limit_cache.disconnect()
    await close_mongo_connection()


app = FastAPI(
    title="Scrapyard API",
    description="Web Scraper as a Service — платформа для распределенного парсинга",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(PrometheusMiddleware)
FastAPIInstrumentor.instrument_app(app)

# Routes
app.include_router(jobs.router)
app.include_router(analytics.router)
app.include_router(logs.router)
app.include_router(results.router)


@app.get("/metrics")
async def metrics():
    """Prometheus scrape target. Unauthenticated like /health — intended
    to sit behind network-level access control, not an API key."""
    return await metrics_endpoint()


@app.get("/health")
async def health_check():
    """Health check endpoint with database status."""
    from api.core.database import db

    db_status = "disconnected"
    if db.client:
        try:
            await db.client.admin.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "error"

    return {
        "status": "ok",
        "service": "scrapyard-api",
        "database": db_status,
    }
