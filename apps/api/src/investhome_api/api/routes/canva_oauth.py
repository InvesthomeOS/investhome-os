"""Canva Connect OAuth 2.0 + PKCE — authorize, callback exchange, disconnect, export."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission
from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.services import canva_export_service as canva_export
from investhome_api.services import canva_oauth_service as canva

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform/integrations/canva", tags=["platform-integrations-canva"])

_FRONTEND_PATH = "/dashboard/admin/platform/integrations"
_platform_manage = require_any_permission(("platform", "manage"), ("security", "manage"))
_cs_or_platform = require_any_permission(
    ("creative_studio", "view"),
    ("platform", "manage"),
    ("security", "manage"),
)

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
        "invalid_state",
        "token_exchange_failed",
        "canva_not_configured",
        "oauth_error",
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


@router.post("/authorize")
def canva_oauth_authorize_start(
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    """
    Start Canva OAuth + PKCE. Returns authorize_url for the browser to navigate to.
    Does not expose client_secret or code_verifier.
    """
    _ = db  # ensure DB session available for future audit hooks
    try:
        authorize_url = canva.start_authorization(user_id=str(user.id) if user else None)
    except ValueError as exc:
        code = str(exc) or "canva_not_configured"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=code if code in _SAFE_OAUTH_ERRORS else "canva_not_configured",
        ) from exc
    return {
        "authorize_url": authorize_url,
        "redirect_uri": canva.CANVA_REDIRECT_URI,
    }


@router.get("/callback")
def canva_oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),  # accepted, never forwarded
) -> RedirectResponse:
    """
    Canva OAuth redirect URI.

    Success: exchange authorization code (PKCE) → store tokens → redirect `?canva=connected`.
    Error / invalid: redirect `?canva_error=<opaque>`.
    """
    _ = error_description  # intentionally unused - avoid secret leakage

    if error:
        return _redirect({"canva_error": _sanitize_error(error)})

    if not code or not str(code).strip():
        return _redirect({"canva_error": "missing_code"})

    if not state or not str(state).strip():
        return _redirect({"canva_error": "missing_state"})

    pending = canva.pop_oauth_state(str(state).strip())
    if not pending or not pending.get("code_verifier"):
        return _redirect({"canva_error": "invalid_state"})

    try:
        token_payload = canva.exchange_authorization_code(
            code=str(code).strip(),
            code_verifier=str(pending["code_verifier"]),
        )
        canva.store_tokens(db, token_payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _redirect({"canva_error": _sanitize_error(str(exc))})
    except Exception:
        db.rollback()
        logger.exception("Canva OAuth callback failed")
        return _redirect({"canva_error": "token_exchange_failed"})

    return _redirect({"canva": "connected"})


@router.post("/disconnect")
def canva_oauth_disconnect(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_manage),
) -> dict:
    """Clear stored Canva tokens and mark integration not_connected."""
    canva.disconnect_canva(db)
    db.commit()
    return {"ok": True, "status": "not_connected"}


def _raise_canva_export_error(exc: ValueError) -> None:
    code = str(exc) or "canva_export_failed"
    mapping = {
        "canva_not_connected": status.HTTP_409_CONFLICT,
        "canva_not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
        "canva_token_refresh_failed": status.HTTP_409_CONFLICT,
        "missing_png_or_asset": status.HTTP_400_BAD_REQUEST,
        "invalid_png": status.HTTP_400_BAD_REQUEST,
        "file_too_big": 413,
        "linked_project_id_required": status.HTTP_400_BAD_REQUEST,
        "invalid_asset_id": status.HTTP_400_BAD_REQUEST,
        "canva_upload_failed": status.HTTP_502_BAD_GATEWAY,
        "canva_export_failed": status.HTTP_502_BAD_GATEWAY,
    }
    raise HTTPException(
        status_code=mapping.get(code, status.HTTP_502_BAD_GATEWAY),
        detail=code if code in mapping else "canva_export_failed",
    ) from exc


@router.post("/export")
async def canva_export_design(
    db: Session = Depends(get_db),
    _user: User = Depends(_cs_or_platform),
    file: UploadFile | None = File(default=None),
    media_asset_id: str | None = Form(default=None),
    linked_project_id: str | None = Form(default=None),
    title: str | None = Form(default=None),
    width: int | None = Form(default=None),
    height: int | None = Form(default=None),
) -> dict:
    """
    Upload a PNG (current SMB design) or a project-scoped Media Library asset
    to Canva Connect, create a design, and return ``edit_url``.
    """
    if not canva.is_canva_connected(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="canva_not_connected",
        )

    png_bytes: bytes | None = None
    if file is not None and file.filename:
        png_bytes = await file.read()

    if not png_bytes and media_asset_id:
        project_raw = (linked_project_id or "").strip()
        if not project_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="linked_project_id_required",
            )
        try:
            asset_uuid = UUID(str(media_asset_id).strip())
            project_uuid = UUID(project_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_asset_id",
            ) from exc
        try:
            png_bytes = canva_export.read_media_asset_png(
                db,
                media_asset_id=asset_uuid,
                linked_project_id=project_uuid,
            )
        except HTTPException:
            raise
        except ValueError as exc:
            _raise_canva_export_error(exc)

    if not png_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_png_or_asset",
        )

    design_title = (title or (file.filename if file else None) or "Social post").strip()
    try:
        result = canva_export.export_png_to_canva(
            db,
            png_bytes=png_bytes,
            title=design_title,
            width=width,
            height=height,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_canva_export_error(exc)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Canva export failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="canva_export_failed",
        ) from None

    return {
        "edit_url": result["edit_url"],
        "design_id": result.get("design_id"),
    }
