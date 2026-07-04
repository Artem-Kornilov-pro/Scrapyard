from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from api.core.config import settings

_instrumented = False


def setup_tracing(service_name: str) -> None:
    """Configure OpenTelemetry tracing for this process.

    A no-op when `ENABLE_TRACING` is false, and idempotent otherwise
    (safe to call more than once in the same process). Instruments
    PyMongo and Redis globally here since Motor and redis-py both
    route through those libraries' own clients, so a single call
    covers both the API and worker processes; FastAPI and Celery need
    their own instrumentation call against the specific `app`/task
    registry, done in api/main.py and worker/celery_app.py.
    """
    global _instrumented
    if not settings.enable_tracing or _instrumented:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint, insecure=True
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    PymongoInstrumentor().instrument()
    RedisInstrumentor().instrument()

    _instrumented = True
