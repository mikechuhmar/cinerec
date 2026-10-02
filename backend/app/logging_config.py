"""Structured logging via structlog, bridged to the stdlib ``logging`` module.

Call :func:`configure_logging` once at startup. Afterwards, both ``structlog.get_logger()``
and plain ``logging.getLogger()`` calls emit the same structured records (JSON in production,
colourised key/value in dev). The active request's correlation id (set by
``asgi-correlation-id``) is injected into every record.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from asgi_correlation_id import correlation_id

from app.config import get_settings

_configured = False


def _add_request_id(_logger, _method, event_dict):
    rid = correlation_id.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, etc.) through the same formatter.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=renderer,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
