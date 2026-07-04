import asyncio

from celery import Celery
from celery.signals import beat_init, worker_process_init, worker_process_shutdown
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from api.core.config import settings
from api.core.tracing import setup_tracing

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
    # Task events power celery-exporter's Prometheus metrics (task
    # counts/latency by name and state, worker up/down) -- see
    # docker-compose.yml and docker/prometheus-alerts.yml.
    worker_send_task_events=True,
    task_send_sent_event=True,
    beat_schedule={
        "sync-scheduled-jobs-every-minute": {
            "task": "worker.tasks.sync_scheduled_jobs",
            "schedule": 60.0,
        },
    },
)

app.autodiscover_tasks(["worker.tasks"])


def _init_tracing(**kwargs: object) -> None:
    """Set up tracing once this process actually exists.

    Registered against worker_process_init (fired in each forked
    prefork child) and beat_init (beat never forks) rather than run at
    import time in the parent -- BatchSpanProcessor's background
    export thread doesn't survive fork() cleanly.
    """
    setup_tracing("scrapyard-worker")
    CeleryInstrumentor().instrument()


worker_process_init.connect(_init_tracing)
beat_init.connect(_init_tracing)


@worker_process_shutdown.connect
def _close_browser_pool(**kwargs: object) -> None:
    """Close the pooled Chromium instance when a worker process exits,
    so it doesn't linger as an orphaned process.
    """
    from worker.engines.browser_pool import browser_pool

    asyncio.run(browser_pool.close())
