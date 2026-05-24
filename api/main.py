from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.core.database import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="Scrapyard API",
    description="Web Scraper as a Service — платформа для распределенного парсинга",
    version="0.1.0",
    lifespan=lifespan,
)


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