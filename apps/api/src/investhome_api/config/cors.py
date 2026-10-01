"""Explicit CORS allowlists for browser access.

Origins come from API_CORS_ORIGINS. Wildcards and reflected origins are rejected.
"""

from __future__ import annotations

DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

CORS_ALLOWED_METHODS: tuple[str, ...] = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
)

CORS_ALLOWED_HEADERS: tuple[str, ...] = (
    "Accept",
    "Authorization",
    "Content-Type",
    "X-CSRF-Token",
    "X-Request-Id",
)

CORS_EXPOSE_HEADERS: tuple[str, ...] = ("X-Request-Id",)


def sanitize_cors_origins(origins: list[str] | tuple[str, ...] | None) -> list[str]:
    """Keep exact origins only. Drop empty, null, and any wildcard values."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in origins or ():
        origin = str(raw).strip().rstrip("/")
        if not origin:
            continue
        lowered = origin.lower()
        if lowered == "*" or "*" in origin or lowered == "null":
            continue
        if origin in seen:
            continue
        seen.add(origin)
        cleaned.append(origin)
    return cleaned
