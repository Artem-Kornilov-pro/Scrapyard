from typing import Optional

from motor.core import AgnosticCollection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from api.core.config import settings


class MongoDB:
    """MongoDB connection manager using Motor async driver."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    scraping_jobs: Optional[AgnosticCollection] = None
    scraped_results: Optional[AgnosticCollection] = None
    job_logs: Optional[AgnosticCollection] = None


db = MongoDB()


async def connect_to_mongo():
    """Connect to MongoDB and initialize indexes."""
    db.client = AsyncIOMotorClient(settings.mongo_uri)
    db.db = db.client[settings.db_name]

    db.scraping_jobs = db.db.scraping_jobs
    db.scraped_results = db.db.scraped_results

    # Create Time Series collection for job logs
    existing = await db.db.list_collection_names()
    if "job_logs" not in existing:
        await db.db.create_collection(
            "job_logs",
            timeseries={
                "timeField": "timestamp",
                "metaField": "job_id",
                "granularity": "seconds",
            },
        )

    db.job_logs = db.db.job_logs
    await db.job_logs.create_index("job_id")

    # Indexes for scraping_jobs
    await db.scraping_jobs.create_index("job_id", unique=True)
    await db.scraping_jobs.create_index("status")
    await db.scraping_jobs.create_index([("status", 1), ("next_run", 1)])
    await db.scraping_jobs.create_index("tags")

    # Indexes for scraped_results
    await db.scraped_results.create_index("job_id")
    await db.scraped_results.create_index(
        [("job_id", ASCENDING), ("timestamp", ASCENDING)])

        # Drop existing timestamp indexes to avoid conflicts
    try:
        indexes = await db.scraped_results.index_information()
        for name in indexes:
            if name == "timestamp_1" or name == "timestamp_ttl":
                await db.scraped_results.drop_index(name)
    except Exception:
        pass

    await db.scraped_results.create_index(
        "timestamp",
        name="timestamp_ttl",
        expireAfterSeconds=90 * 24 * 60 * 60,
    )


async def ensure_connected():
    """Connect to MongoDB if not already connected.

    Idempotent, so it's safe to call at the top of any Celery task that
    touches the database without knowing whether another task already
    connected in this worker process.
    """
    if db.client is None:
        await connect_to_mongo()


async def close_mongo_connection():
    """Close MongoDB connection."""
    if db.client:
        db.client.close()
        db.client = None
        print("MongoDB connection closed")
