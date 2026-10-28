"""Centralized logging configuration for API and worker processes."""

from __future__ import annotations

import logging
import re
import sys

from investhome_api.config.settings import get_settings

_TOKEN_QUERY = re.compile(r"([?&]token=)[^&\s\"]+")


class RedactWebhookTokenFilter(logging.Filter):
    """Drop the Wazzup webhook query token from access-log lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                _TOKEN_QUERY.sub(r"\1[redacted]", item) if isinstance(item, str) else item
                for item in record.args
            )
        message = record.msg
        if isinstance(message, str) and "token=" in message and "%" not in message:
            record.msg = _TOKEN_QUERY.sub(r"\1[redacted]", message)
        return True


def configure_logging() -> None:
    """Configure root logger with environment-aware defaults."""
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO
    if settings.environment == "production" and not settings.debug:
        level = logging.INFO

    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, RedactWebhookTokenFilter) for item in access.filters):
        access.addFilter(RedactWebhookTokenFilter())

    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
