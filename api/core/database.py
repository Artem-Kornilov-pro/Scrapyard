from motor.motor_asyncio import AsyncIOMotorClient
from api.core.config import settings


class MongoDB:
    """MongoDB connection manager using Motor async driver."""
    
    client: AsyncIOMotorClient = None
    db = None
    
    # Collections
    scraping_jobs = None
    scraped_results = None


db = MongoDB()


async def connect_to_mongo():
    """Connect to MongoDB and initialize indexes."""
    db.client = AsyncIOMotorClient(settings.mongo_uri)
    db.db = db.client[settings.db_name]
    
    # Assign collections
    db.scraping_jobs = db.db.scraping_jobs
    db.scraped_results = db.db.scraped_results
    
    # Create indexes for scraping_jobs
    await db.scraping_jobs.create_index("job_id", unique=True)
    await db.scraping_jobs.create_index("status")
    await db.scraping_jobs.create_index([("status", 1), ("next_run", 1)])
    await db.scraping_jobs.create_index("tags")
    
    # Create indexes for scraped_results
    await db.scraped_results.create_index("job_id")
    await db.scraped_results.create_index("timestamp")
    await db.scraped_results.create_index([("job_id", 1), ("timestamp", -1)])
    
    # Create TTL index: auto-delete results older than 90 days
    await db.scraped_results.create_index(
        "timestamp",
        expireAfterSeconds=90 * 24 * 60 * 60
    )
    
    print(f"✅ Connected to MongoDB: {settings.db_name}")


async def close_mongo_connection():
    """Close MongoDB connection."""
    if db.client:
        db.client.close()
        db.client = None  # <-- Добавили обнуление!
        print("✅ MongoDB connection closed")