import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from api.core.database import connect_to_mongo, db
from worker.celery_app import app
from worker.engines.parsers.generic import parse_with_selectors
from worker.engines.playwright_engine import PlaywrightEngine

logger = get_task_logger(__name__)


class ScrapingTask(Task):
    """Base task with MongoDB connection handling."""

    _db_connected = False

    async def setup(self) -> None:
        """Ensure MongoDB connection on worker start."""
        if not self._db_connected:
            await connect_to_mongo()
            self._db_connected = True


@app.task(
    bind=True,
    base=ScrapingTask,
    name="worker.tasks.scrape_job",
    max_retries=3,
    default_retry_delay=60,
)
def scrape_job(self: Task, job_config: dict[str, Any]) -> dict[str, Any]:
    """Execute scraping job and save results to MongoDB."""
    return _run_scrape(self, job_config)


async def _run_scrape(
    self: Task, job_config: dict[str, Any]
) -> dict[str, Any]:
    """Async implementation of scraping logic."""
    job_id = job_config["job_id"]
    run_id = str(uuid.uuid4())
    start_time = datetime.now(UTC)

    assert db.scraping_jobs is not None
    assert db.scraped_results is not None
    assert db.job_logs is not None

    # Log start
    await db.job_logs.insert_one({
        "job_id": job_id,
        "run_id": run_id,
        "status": "started",
        "timestamp": start_time,
    })

    try:
        async with PlaywrightEngine(headless=True) as engine:
            await engine.navigate(job_config["url"])
            items = await parse_with_selectors(
                engine._page, job_config["selectors"]
            )

        duration_ms = int(
            (datetime.now(UTC) - start_time).total_seconds() * 1000
        )

        result = {
            "job_id": job_id,
            "run_id": run_id,
            "timestamp": start_time,
            "items_count": len(items),
            "items": items,
            "metadata": {
                "duration_ms": duration_ms,
                "pages_processed": 1,
                "status": "success",
                "error_message": None,
            },
        }

        await db.scraped_results.insert_one(result)
        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "last_run": start_time,
                    "consecutive_failures": 0,
                }
            },
        )

        # Log completion
        await db.job_logs.insert_one({
            "job_id": job_id,
            "run_id": run_id,
            "status": "completed",
            "timestamp": datetime.now(UTC),
            "duration_ms": duration_ms,
            "items_scraped": len(items),
        })

        logger.info(
            "Job %s completed: %d items in %dms",
            job_id,
            len(items),
            duration_ms,
        )

        return {"run_id": run_id, "items_count": len(items)}

    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, str(exc))

        # Log failure
        await db.job_logs.insert_one({
            "job_id": job_id,
            "run_id": run_id,
            "status": "failed",
            "timestamp": datetime.now(UTC),
            "error_type": type(exc).__name__,
        })

        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {"$inc": {"consecutive_failures": 1}},
        )

        job_doc = await db.scraping_jobs.find_one({"job_id": job_id})
        if job_doc and job_doc.get("consecutive_failures", 0) >= 5:
            await db.scraping_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "error"}},
            )

        raise self.retry(exc=exc)
