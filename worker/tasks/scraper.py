import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from api.core.cache import domain_throttle_cache
from api.core.config import settings
from api.core.database import db, ensure_connected
from worker.celery_app import app
from worker.engines.parsers.pagination import collect_page_items
from worker.engines.playwright_engine import PlaywrightEngine
from worker.utils.notify import send_webhook_notification
from worker.utils.robots import is_allowed
from worker.utils.throttle import acquire_domain_slot, extract_domain

logger = get_task_logger(__name__)


class ScrapingTask(Task):
    """Base task with MongoDB/Redis connection handling."""

    _db_connected = False

    async def setup(self) -> None:
        """Ensure MongoDB and Redis connections on worker start."""
        if not self._db_connected:
            await ensure_connected()
            await domain_throttle_cache.connect()
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
    return asyncio.get_event_loop().run_until_complete(
        _run_scrape(self, job_config)
    )


async def _run_scrape(
    self: Task, job_config: dict[str, Any]
) -> dict[str, Any]:
    """Async implementation of scraping logic."""
    await self.setup()

    job_id = job_config["job_id"]
    run_id = str(uuid.uuid4())
    url = job_config["url"]
    start_time = datetime.now(UTC)

    assert db.scraping_jobs is not None
    assert db.scraped_results is not None
    assert db.job_logs is not None

    if not await is_allowed(url):
        logger.info("Job %s blocked by robots.txt: %s", job_id, url)
        await db.job_logs.insert_one({
            "job_id": job_id,
            "run_id": run_id,
            "status": "skipped",
            "timestamp": datetime.now(UTC),
            "reason": "blocked_by_robots_txt",
        })
        return {"run_id": run_id, "items_count": 0, "skipped": "robots_txt"}

    domain = extract_domain(url)
    if not await acquire_domain_slot(domain):
        logger.info(
            "Job %s deferred: domain %s is within its throttle window",
            job_id,
            domain,
        )
        self.apply_async(
            args=[job_config], countdown=settings.domain_throttle_seconds
        )
        return {
            "run_id": run_id,
            "items_count": 0,
            "deferred": "domain_throttled",
        }

    # Log start
    await db.job_logs.insert_one({
        "job_id": job_id,
        "run_id": run_id,
        "status": "started",
        "timestamp": start_time,
    })

    selectors = job_config["selectors"]
    pagination_config = (job_config.get("settings") or {}).get(
        "pagination"
    ) or {}
    pagination_type = pagination_config.get("type")
    max_pages = pagination_config.get("max_pages", 1)

    try:
        async with PlaywrightEngine(
            headless=True, user_agent=settings.scraper_user_agent
        ) as engine:
            await engine.navigate(job_config["url"])
            items = await collect_page_items(
                engine._page, selectors, pagination_config
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
                "pages_processed": max_pages if pagination_type else 1,
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

        job_doc = await db.scraping_jobs.find_one(
            {"job_id": job_id}, {"_id": 0}
        )
        if job_doc and job_doc.get("consecutive_failures", 0) >= 5:
            await db.scraping_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "error"}},
            )
            webhook_url = job_doc.get("notify_webhook")
            if webhook_url:
                await send_webhook_notification(webhook_url, {
                    "event": "job.error",
                    "job_id": job_id,
                    "job_name": job_doc.get("name"),
                    "url": job_doc.get("url"),
                    "consecutive_failures": job_doc["consecutive_failures"],
                    "last_error": type(exc).__name__,
                    "timestamp": datetime.now(UTC).isoformat(),
                })

        raise self.retry(exc=exc)
