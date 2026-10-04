"""Explicit CORS allowlists for browser access.

Origins come from API_CORS_ORIGINS. Wildcards and reflected origins are rejected.
Production must use HTTPS non-localhost origins; localhost fallback is development-only.
"""

from __future__ import annotations

from urllib.parse import urlparse

DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

_LOCAL_CORS_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})

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


def _origin_host(origin: str) -> str:
    host = (urlparse(origin).hostname or "").strip().lower()
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    return host


def is_local_cors_origin(origin: str) -> bool:
    host = _origin_host(origin)
    return host in _LOCAL_CORS_HOSTS or host.endswith(".localhost")


def is_absolute_web_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.path not in {"", "/"}:
        return False
    if parsed.query or parsed.fragment:
        return False
    return bool(parsed.hostname and parsed.netloc)


def production_cors_problems(origins: list[str] | tuple[str, ...] | None) -> list[str]:
    """Return production CORS configuration problems. Do not include origin values."""
    cleaned = [str(origin).strip() for origin in (origins or ()) if str(origin).strip()]
    problems: list[str] = []
    if not cleaned:
        problems.append("API_CORS_ORIGINS is required in production")
        return problems
    if any(not is_absolute_web_origin(origin) for origin in cleaned):
        problems.append("API_CORS_ORIGINS contains malformed origins")
    local_origins = [origin for origin in cleaned if is_local_cors_origin(origin)]
    if local_origins:
        if len(local_origins) == len(cleaned):
            problems.append("API_CORS_ORIGINS must not be localhost-only in production")
        else:
            problems.append("API_CORS_ORIGINS must not include localhost origins in production")
    http_origins = [
        origin
        for origin in cleaned
        if is_absolute_web_origin(origin) and urlparse(origin).scheme.lower() != "https"
    ]
    if http_origins:
        if len(http_origins) == len(cleaned):
            problems.append("API_CORS_ORIGINS must not be HTTP-only in production")
        else:
            problems.append("API_CORS_ORIGINS must use HTTPS in production")
    return problems
