import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.core.database import db

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)
JOBS_BY_STATUS = Gauge(
    "scrapyard_jobs_total",
    "Number of scraping jobs by status",
    ["status"],
)

# A job flips to "error" after JobService.run_now's caller
# (worker.tasks.scrape_job) hits 5 consecutive failures. Any job sitting
# in this state needs a human to look at it -- see the alert rule
# ScrapyardJobsInErrorState in docker/prometheus-alerts.yml.
_JOB_STATUSES = ["active", "paused", "error"]


class PrometheusMiddleware:
    """Records request count and latency for every HTTP request.

    Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so it
    sits cleanly above Starlette's ExceptionMiddleware without
    interfering with exception-handler responses.

    Uses the matched route's path template (e.g. /api/v1/jobs/{job_id})
    rather than the raw URL, so per-job/per-run IDs don't blow up the
    metric's cardinality.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            request = Request(scope)
            route = scope.get("route")
            path = route.path if route is not None else request.url.path

            REQUEST_COUNT.labels(request.method, path, status_code).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(duration)


async def _refresh_job_status_gauges() -> None:
    """Recompute the per-status job count gauges from MongoDB.

    Cheap: `status` is indexed (see api/core/database.py), and this only
    runs once per scrape, not per request.
    """
    if db.scraping_jobs is None:
        return
    for status in _JOB_STATUSES:
        count = await db.scraping_jobs.count_documents({"status": status})
        JOBS_BY_STATUS.labels(status).set(count)


async def metrics_endpoint() -> Response:
    """Prometheus scrape target."""
    await _refresh_job_status_gauges()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
