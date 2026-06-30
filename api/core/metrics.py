import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


async def metrics_endpoint() -> Response:
    """Prometheus scrape target."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
