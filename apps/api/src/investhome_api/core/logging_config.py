"""Centralized logging configuration for API and worker processes."""

from __future__ import annotations

import logging
import sys

from investhome_api.config.settings import get_settings


def configure_logging() -> None:
    """Configure root logger with environment-aware defaults."""
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO
    if settings.environment == "production" and not settings.debug:
        level = logging.INFO

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
