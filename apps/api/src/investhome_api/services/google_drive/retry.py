"""Retry helpers for Google Drive API calls — bounded exponential backoff + jitter."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

from investhome_api.services.google_drive.errors import (
    GoogleDriveApiError,
    GoogleDriveAuthError,
    GoogleDriveConfigError,
    GoogleDriveError,
    GoogleDriveNotFoundError,
    GoogleDrivePermissionError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Permanent failures — do not retry endlessly
_PERMANENT_CODES = frozenset(
    {
        "drive_auth_error",
        "drive_permission_denied",
        "drive_not_configured",
        "drive_not_found",
        "outside_root",
        "mapping_not_found",
        "sync_disabled",
        "invalid_mapping",
    }
)


def is_permanent_drive_error(exc: BaseException) -> bool:
    if isinstance(exc, (GoogleDriveAuthError, GoogleDrivePermissionError, GoogleDriveConfigError)):
        return True
    if isinstance(exc, GoogleDriveNotFoundError):
        return True
    if isinstance(exc, GoogleDriveError) and exc.code in _PERMANENT_CODES:
        return True
    return False


def is_transient_drive_error(exc: BaseException) -> bool:
    if is_permanent_drive_error(exc):
        return False
    if isinstance(exc, GoogleDriveApiError):
        message = (exc.message or "").lower()
        if "429" in message or "rate" in message or "quota" in message:
            return True
        if any(code in message for code in ("500", "502", "503", "504")):
            return True
        return True  # other API errors treated as transient unless permanent class
    # Network / unexpected I/O
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    return False


def with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
    max_delay_seconds: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    operation: str = "drive_api",
) -> T:
    """Execute ``fn`` with exponential backoff + jitter on transient failures."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if is_permanent_drive_error(exc) or not is_transient_drive_error(exc):
                raise
            if attempt >= max_retries:
                logger.warning(
                    "drive_retry_exhausted",
                    extra={
                        "operation": operation,
                        "attempts": attempt + 1,
                        "error_type": type(exc).__name__,
                        "code": getattr(exc, "code", None),
                    },
                )
                raise
            delay = min(max_delay_seconds, base_delay_seconds * (2**attempt))
            delay = delay * (0.5 + random.random())  # jitter 50–150%
            logger.info(
                "drive_retry_backoff",
                extra={
                    "operation": operation,
                    "attempt": attempt + 1,
                    "delay_seconds": round(delay, 3),
                    "error_type": type(exc).__name__,
                },
            )
            sleep(delay)
            attempt += 1
