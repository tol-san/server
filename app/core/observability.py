"""
Observability layer: Prometheus metrics registry, structured JSON logging,
and trace-ID middleware for distributed tracing.
"""
import logging
import time
import uuid
import re
from contextvars import ContextVar
from typing import Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Trace ID context var — propagated per-request
# ─────────────────────────────────────────────────────────────────────────────

_UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_NUMERIC_ID_PATTERN = re.compile(r"/\d+")

def _normalize_path(path: str) -> str:
    """Replace UUID and numeric path segments with placeholders for Prometheus label cardinality control."""
    path = _UUID_PATTERN.sub("{id}", path)
    path = _NUMERIC_ID_PATTERN.sub("/{id}", path)
    return path

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)


# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics Registry
# ─────────────────────────────────────────────────────────────────────────────

# ---- HTTP ----
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

# ---- Chat ----
CHAT_MESSAGES_TOTAL = Counter(
    "chat_messages_total",
    "Total chat messages created",
    ["community_id"],
)
CHAT_WS_CONNECTIONS = Gauge(
    "chat_ws_connections_active",
    "Active WebSocket chat connections",
    ["community_id"],
)
CHAT_MESSAGES_RATE_LIMITED = Counter(
    "chat_messages_rate_limited_total",
    "Chat messages rejected by rate limiter",
    ["user_id"],
)

# ---- Live Rooms ----
LIVE_SESSIONS_TOTAL = Counter(
    "live_sessions_total",
    "Total live sessions started",
    ["community_id"],
)
LIVE_VIEWERS_CURRENT = Gauge(
    "live_viewers_current",
    "Current live room viewers",
    ["session_id"],
)
LIVE_TOKENS_ISSUED = Counter(
    "live_tokens_issued_total",
    "Total LiveKit tokens issued",
    ["role"],  # host | viewer
)

# ---- Workers ----
WORKER_EVENTS_PROCESSED = Counter(
    "worker_events_processed_total",
    "Total stream events processed by workers",
    ["worker", "event_type"],
)
WORKER_EVENTS_FAILED = Counter(
    "worker_events_failed_total",
    "Total stream events that failed after retries",
    ["worker", "event_type"],
)
WORKER_EVENT_DURATION = Histogram(
    "worker_event_processing_duration_seconds",
    "Worker event processing duration",
    ["worker", "event_type"],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)
OUTBOX_EVENTS_PENDING = Gauge(
    "outbox_events_pending",
    "Outbox events waiting to be relayed",
)
DEAD_LETTER_EVENTS_TOTAL = Counter(
    "dead_letter_events_total",
    "Events moved to dead-letter queue",
    ["worker", "event_type"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Structured JSON Logging
# ─────────────────────────────────────────────────────────────────────────────

def configure_logging() -> None:
    """Configure application-wide structured logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    root = logging.getLogger()
    root.setLevel(log_level)
    
    # Suppress verbose internal transport/handshake chatter from third-party drivers
    for noisy_logger in ("redis", "redis.asyncio", "asyncio", "urllib3", "httpcore", "httpx"):
        logging.getLogger(noisy_logger).setLevel(logging.INFO)
    
    if settings.LOG_FORMAT == "json":
        try:
            from pythonjsonlogger.json import JsonFormatter

            formatter = JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                rename_fields={"asctime": "timestamp", "levelname": "level"},
            )
            if root.handlers:
                root.handlers[0].setFormatter(formatter)
        except ImportError:
            pass  # fall back to default text format


class _TraceFilter(logging.Filter):
    """Injects the current request trace_id into every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True

_TRACE_FILTER = _TraceFilter()


def get_logger(name: str) -> logging.Logger:
    """Return a logger that auto-injects trace_id into log records."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, _TraceFilter) for f in logger.filters):
        logger.addFilter(_TRACE_FILTER)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Injects trace ID, records HTTP metrics per request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Propagate or generate trace ID
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        set_trace_id(trace_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        response.headers["X-Trace-ID"] = trace_id

        # Collapse parameterised path for metric cardinality control
        path = _normalize_path(request.url.path)
        method = request.method
        status = str(response.status_code)

        if settings.ENABLE_METRICS:
            HTTP_REQUEST_DURATION.labels(
                method=method, endpoint=path, status_code=status
            ).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=path, status_code=status
            ).inc()

        return response


# ─────────────────────────────────────────────────────────────────────────────
# /metrics endpoint handler
# ─────────────────────────────────────────────────────────────────────────────

async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics in text exposition format."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
