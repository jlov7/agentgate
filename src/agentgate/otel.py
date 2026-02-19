"""OpenTelemetry-compatible tracing helpers with safe fallback behavior."""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from agentgate.logging import get_logger

logger = get_logger(__name__)


try:  # pragma: no cover - exercised only when optional deps are installed
    from opentelemetry import trace as _otel_trace  # type: ignore[import-not-found]
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
    from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
except Exception:  # pragma: no cover - expected in minimal dependency installs
    _otel_trace = None
    OTLPSpanExporter = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None


@dataclass
class _FallbackSpan:
    trace_id: str
    span_id: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


_fallback_stack: ContextVar[tuple[_FallbackSpan, ...]] = ContextVar(
    "agentgate_fallback_trace_stack",
    default=(),
)
_configured = False
_tracer: Any = None


def tracing_enabled() -> bool:
    value = os.getenv("AGENTGATE_OTEL_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _service_name() -> str:
    return os.getenv("AGENTGATE_OTEL_SERVICE_NAME", "agentgate").strip() or "agentgate"


def _exporter_mode() -> str:
    return os.getenv("AGENTGATE_OTEL_EXPORTER", "none").strip().lower() or "none"


def configure_tracing() -> bool:
    """Configure OTEL tracing if enabled and SDK dependencies are installed."""
    global _configured, _tracer

    if _configured:
        return tracing_enabled()

    _configured = True
    if not tracing_enabled():
        return False

    if _otel_trace is None or TracerProvider is None:
        logger.warning(
            "otel_sdk_unavailable_using_fallback_traceparent",
            service_name=_service_name(),
        )
        return True

    provider = TracerProvider(  # pragma: no cover - optional dependency path
        resource=Resource.create({"service.name": _service_name()})
    )
    mode = _exporter_mode()
    if mode == "console" and ConsoleSpanExporter is not None:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif mode == "otlp" and OTLPSpanExporter is not None:
        endpoint = os.getenv("AGENTGATE_OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        exporter = OTLPSpanExporter(endpoint=endpoint or None)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    _otel_trace.set_tracer_provider(provider)
    _tracer = _otel_trace.get_tracer("agentgate")
    logger.info("otel_tracing_configured", service_name=_service_name(), exporter_mode=mode)
    return True


def _coerce_attribute(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def set_span_attribute(span: Any, key: str, value: Any) -> None:
    if span is None:
        return
    setter = getattr(span, "set_attribute", None)
    if callable(setter):
        setter(key, _coerce_attribute(value))


@contextmanager
def _fallback_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[_FallbackSpan]:
    stack = _fallback_stack.get()
    parent = stack[-1] if stack else None
    trace_id = parent.trace_id if parent else secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    span = _FallbackSpan(trace_id=trace_id, span_id=span_id, name=name)
    for key, value in (attributes or {}).items():
        span.set_attribute(key, value)
    token = _fallback_stack.set((*stack, span))
    try:
        yield span
    finally:
        _fallback_stack.reset(token)


@contextmanager
def start_span(name: str, *, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Start a tracing span if OTEL is enabled, otherwise no-op."""
    if not tracing_enabled():
        yield None
        return

    # pragma: no cover - optional dependency path
    if _otel_trace is not None and _tracer is not None:
        with _tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                set_span_attribute(span, key, value)
            yield span
        return

    with _fallback_span(name, attributes=attributes) as span:
        yield span


def current_traceparent() -> str | None:
    """Return the current traceparent header value when a span is active."""
    if not tracing_enabled():
        return None

    # pragma: no cover - optional dependency path
    if _otel_trace is not None and _tracer is not None:
        current = _otel_trace.get_current_span()
        context = current.get_span_context()
        if context.is_valid:
            return f"00-{context.trace_id:032x}-{context.span_id:016x}-01"

    stack = _fallback_stack.get()
    if not stack:
        return None
    span = stack[-1]
    return f"00-{span.trace_id}-{span.span_id}-01"
