"""Structured logging helpers with correlation IDs."""

from __future__ import annotations

import logging
from typing import cast

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


def configure_logging(level: str) -> None:
    """Configure structlog with JSON output."""
    level_name = level.upper()
    numeric_level = logging._nameToLevel.get(level_name, logging.INFO)

    logging.basicConfig(format="%(message)s", level=numeric_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID into the logging context."""
    bind_contextvars(correlation_id=correlation_id)


def clear_logging_context() -> None:
    """Clear bound context variables after a request completes."""
    clear_contextvars()


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a structured logger."""
    return cast(structlog.BoundLogger, structlog.get_logger(name))
