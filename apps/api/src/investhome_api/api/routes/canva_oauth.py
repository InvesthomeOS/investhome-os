"""Canva OAuth callback foundation - redirect only, no token exchange."""

from __future__ import annotations

import re
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from investhome_api.config.settings import get_settings

router = APIRouter(prefix="/platform/integrations/canva", tags=["platform-integrations-canva"])

# Existing Creative Studio / AI connections screen does not exist yet.
# Platform integrations catalog is the live integrations surface (includes AI).
_FRONTEND_PATH = "/dashboard/admin/platform/integrations"

_SAFE_OAUTH_ERRORS = frozenset(
    {
        "access_denied",
        "invalid_request",
        "unauthorized_client",
        "unsupported_response_type",
        "invalid_scope",
        "server_error",
        "temporarily_unavailable",
        "invalid_callback",
        "missing_state",
        "missing_code",
    }
)

_SAFE_ERROR_RE = re.compile(r"^[a-z0-9_]{1,64}$")


def _frontend_base_url() -> str:
    """Frontend origin from existing API_CORS_ORIGINS (no new secret config)."""
    settings = get_settings()
    origins = settings.cors_origins or ["http://localhost:3000"]
    return str(origins[0]).rstrip("/")


def _sanitize_error(error: str | None) -> str:
    """Opaque safe error token only - never forward error_description or secrets."""
    if not error:
        return "oauth_error"
    normalized = error.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in _SAFE_OAUTH_ERRORS:
        return normalized
    if _SAFE_ERROR_RE.fullmatch(normalized):
        return "oauth_error"
    return "oauth_error"


def _redirect(query: dict[str, str]) -> RedirectResponse:
    url = f"{_frontend_base_url()}{_FRONTEND_PATH}?{urlencode(query)}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
def canva_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),  # accepted, never forwarded
) -> RedirectResponse:
    """
    Canva OAuth redirect URI foundation.

    Success: redirects to frontend with `?canva=connected`.
    Error / invalid: redirects with `?canva_error=<opaque>`.
    Does not exchange codes or store tokens.
    """
    _ = error_description  # intentionally unused - avoid secret leakage

    if error:
        return _redirect({"canva_error": _sanitize_error(error)})

    if not code or not str(code).strip():
        return _redirect({"canva_error": "missing_code"})

    # Full OAuth state store not built this sprint - require non-empty state only.
    if not state or not str(state).strip():
        return _redirect({"canva_error": "missing_state"})

    return _redirect({"canva": "connected"})