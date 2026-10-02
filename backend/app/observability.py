"""Observability wiring: Prometheus metrics and optional OpenTelemetry tracing.

* Prometheus — request latency/throughput are exposed at ``/metrics`` plus a few custom
  recommendation metrics (cache hit/miss, ALS retrains).
* OpenTelemetry — opt-in (``CINEREC_TRACING_ENABLED=true``). When enabled, FastAPI and
  SQLAlchemy are auto-instrumented and spans are exported via OTLP/gRPC to
  ``CINEREC_OTLP_ENDPOINT``. It degrades gracefully if no collector is reachable.
"""

from __future__ import annotations

from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger(__name__)

CACHE_HITS = Counter("cinerec_cache_hits_total", "Recommendation cache hits", ["endpoint"])
CACHE_MISSES = Counter("cinerec_cache_misses_total", "Recommendation cache misses", ["endpoint"])
ALS_RETRAINS = Counter("cinerec_als_retrains_total", "Completed ALS retrains", ["trigger"])


def setup_metrics(app) -> None:
    settings = get_settings()
    if not settings.metrics_enabled:
        return
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    log.info("metrics_enabled", endpoint="/metrics")


def setup_tracing(app) -> None:
    settings = get_settings()
    if not settings.tracing_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from app.db import async_engine, engine

        provider = TracerProvider(resource=Resource.create({"service.name": "cinerec-api"}))
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine)
        SQLAlchemyInstrumentor().instrument(engine=async_engine.sync_engine)
        log.info("tracing_enabled", endpoint=settings.otlp_endpoint)
    except Exception as exc:  # pragma: no cover - depends on optional runtime collector
        log.warning("tracing_setup_failed", error=str(exc))
