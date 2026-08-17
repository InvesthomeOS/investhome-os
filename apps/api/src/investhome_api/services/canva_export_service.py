"""Export a PNG (or Media Library image) into a Canva design via Connect API."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.services import canva_oauth_service as canva
from investhome_api.services import creative_studio_media_service as media_svc

logger = logging.getLogger(__name__)

CANVA_ASSET_UPLOADS_URL = "https://api.canva.com/rest/v1/asset-uploads"
CANVA_DESIGNS_URL = "https://api.canva.com/rest/v1/designs"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 20 * 1024 * 1024
_POLL_ATTEMPTS = 16
_POLL_SLEEP_SECONDS = 0.4
_CANVA_EDIT_HOSTS = frozenset({"www.canva.com", "canva.com"})


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _asset_upload_metadata(name: str) -> str:
    trimmed = (name or "Social post").strip()[:50] or "Social post"
    encoded = base64.b64encode(trimmed.encode("utf-8")).decode("ascii")
    return json.dumps({"name_base64": encoded}, separators=(",", ":"))


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != PNG_MAGIC:
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width < 1 or height < 1:
        return None
    return width, height


def _clamp_design_size(width: int | None, height: int | None) -> tuple[int, int] | None:
    if width is None or height is None:
        return None
    w = max(40, min(8000, int(width)))
    h = max(40, min(8000, int(height)))
    if w * h > 25_000_000:
        scale = (25_000_000 / (w * h)) ** 0.5
        w = max(40, min(8000, int(w * scale)))
        h = max(40, min(8000, int(h * scale)))
    return w, h


def _safe_edit_url(url: Any) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("canva_export_failed")
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.netloc not in _CANVA_EDIT_HOSTS:
        raise ValueError("canva_export_failed")
    return url.strip()


def _auth_headers(access_token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    if extra:
        headers.update(extra)
    return headers


def _json_body(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise ValueError("canva_export_failed") from exc
    return payload if isinstance(payload, dict) else {}


def _canva_request(
    db: Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    token = canva.get_valid_access_token(db)
    extra = dict(headers or {})
    kwargs: dict[str, Any] = {"headers": _auth_headers(token, extra)}
    if content is not None:
        kwargs["content"] = content
    if json_body is not None:
        kwargs["json"] = json_body

    with canva.http_client() as client:
        response = getattr(client, method)(url, **kwargs)
        if response.status_code != 401:
            return response
        stored = canva.get_stored_tokens(db)
        if not stored:
            raise ValueError("canva_not_connected")
        refreshed = canva.refresh_and_store_tokens(db, stored)
        kwargs["headers"] = _auth_headers(str(refreshed["access_token"]), extra)
        return getattr(client, method)(url, **kwargs)


def _upload_png_asset(db: Session, png_bytes: bytes, *, title: str) -> str:
    response = _canva_request(
        db,
        "post",
        CANVA_ASSET_UPLOADS_URL,
        headers={
            "Content-Type": "application/octet-stream",
            "Asset-Upload-Metadata": _asset_upload_metadata(title),
        },
        content=png_bytes,
    )
    if response.status_code >= 400:
        logger.warning("Canva asset upload failed status=%s", response.status_code)
        raise ValueError("canva_upload_failed")
    job = _json_body(response).get("job")
    if not isinstance(job, dict) or not job.get("id"):
        raise ValueError("canva_upload_failed")
    return _wait_for_asset_id(db, str(job["id"]), job)


def _wait_for_asset_id(db: Session, job_id: str, initial: dict[str, Any]) -> str:
    job = initial
    for attempt in range(_POLL_ATTEMPTS):
        status = str(job.get("status") or "")
        if status == "success":
            asset = job.get("asset") if isinstance(job.get("asset"), dict) else {}
            asset_id = str(asset.get("id") or "").strip()
            if not asset_id:
                raise ValueError("canva_upload_failed")
            return asset_id
        if status == "failed":
            logger.warning("Canva asset upload job failed")
            raise ValueError("canva_upload_failed")
        if attempt:
            _sleep(_POLL_SLEEP_SECONDS)
        poll = _canva_request(db, "get", f"{CANVA_ASSET_UPLOADS_URL}/{job_id}")
        if poll.status_code >= 400:
            raise ValueError("canva_upload_failed")
        next_job = _json_body(poll).get("job")
        if not isinstance(next_job, dict):
            raise ValueError("canva_upload_failed")
        job = next_job
    raise ValueError("canva_upload_failed")


def _create_design(
    db: Session,
    *,
    asset_id: str,
    title: str,
    width: int | None,
    height: int | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "asset_id": asset_id,
        "title": (title or "Social post").strip()[:255] or "Social post",
    }
    size = _clamp_design_size(width, height)
    if size:
        body["design_type"] = {"type": "custom", "width": size[0], "height": size[1]}
    response = _canva_request(
        db,
        "post",
        CANVA_DESIGNS_URL,
        headers={"Content-Type": "application/json"},
        json_body=body,
    )
    if response.status_code >= 400:
        logger.warning("Canva create design failed status=%s", response.status_code)
        raise ValueError("canva_export_failed")
    design = _json_body(response).get("design")
    if not isinstance(design, dict):
        raise ValueError("canva_export_failed")
    urls = design.get("urls") if isinstance(design.get("urls"), dict) else {}
    return {
        "design_id": str(design.get("id") or "").strip() or None,
        "edit_url": _safe_edit_url(urls.get("edit_url")),
        "asset_id": asset_id,
    }


def read_media_asset_png(
    db: Session,
    *,
    media_asset_id: UUID,
    linked_project_id: UUID,
) -> bytes:
    asset = media_svc.get_asset_or_404(media_asset_id, db, include_archived=True)
    stream, _media_type = media_svc.open_asset_content(
        asset,
        linked_project_id=linked_project_id,
    )
    try:
        payload = stream.read()
    finally:
        closer = getattr(stream, "close", None)
        if callable(closer):
            closer()
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise ValueError("invalid_png")
    return bytes(payload)


def ensure_png_bytes(payload: bytes) -> bytes:
    if len(payload) > MAX_PNG_BYTES:
        raise ValueError("file_too_big")
    if len(payload) < 8 or payload[:8] != PNG_MAGIC:
        raise ValueError("invalid_png")
    return payload


def export_png_to_canva(
    db: Session,
    *,
    png_bytes: bytes,
    title: str,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    png = ensure_png_bytes(png_bytes)
    dims = _png_dimensions(png)
    asset_id = _upload_png_asset(db, png, title=title)
    return _create_design(
        db,
        asset_id=asset_id,
        title=title,
        width=width if width else (dims[0] if dims else None),
        height=height if height else (dims[1] if dims else None),
    )
