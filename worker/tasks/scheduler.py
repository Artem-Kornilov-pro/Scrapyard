from datetime import UTC, datetime

from celery import Celery
from celery.utils.log import get_task_logger
from croniter import croniter  # type: ignore[import-untyped]

from api.core.database import db
from worker.celery_app import app
from worker.tasks.scraper import scrape_job

logger = get_task_logger(__name__)


@app.task(name="worker.tasks.sync_scheduled_jobs")
def sync_scheduled_jobs_task() -> int:
    """Celery Beat task wrapper for sync_scheduled_jobs."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(sync_scheduled_jobs(app))


async def sync_scheduled_jobs(celery_app: Celery) -> int:
    """Check for jobs that need to run and dispatch them.

    Args:
        celery_app: Celery app instance.

    Returns:
        Number of jobs dispatched.
    """
    assert db.scraping_jobs is not None

    now = datetime.now(UTC)
    dispatched = 0

    cursor = db.scraping_jobs.find({
        "status": "active",
        "next_run": {"$lte": now},
    })

    async for doc in cursor:
        job_id = doc["job_id"]

        scrape_job.delay(doc)

        next_run = croniter(doc["schedule"], now).get_next(datetime)
        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"next_run": next_run, "updated_at": now}},
        )

        dispatched += 1
        logger.info("Dispatched job %s, next run at %s", job_id, next_run)

    return dispatched
