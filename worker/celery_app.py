import asyncio

from celery import Celery
from celery.signals import worker_process_shutdown

from api.core.config import settings

app = Celery(
    "scrapyard",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    beat_schedule={
        "sync-scheduled-jobs-every-minute": {
            "task": "worker.tasks.sync_scheduled_jobs",
            "schedule": 60.0,
        },
    },
)

app.autodiscover_tasks(["worker.tasks"])


@worker_process_shutdown.connect
def _close_browser_pool(**kwargs: object) -> None:
    """Close the pooled Chromium instance when a worker process exits,
    so it doesn't linger as an orphaned process.
    """
    from worker.engines.browser_pool import browser_pool

    asyncio.run(browser_pool.close())
