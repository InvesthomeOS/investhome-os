"""Export a PNG (or Media Library image) into a Canva design via Connect API.

Editable path: Canva Design Import (PPTX) — POST /rest/v1/imports with
`design:content:write`. Fallback: existing PNG asset upload + create design.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.services import canva_layered_pptx as layered
from investhome_api.services import canva_oauth_service as canva
from investhome_api.services import creative_studio_media_service as media_svc

logger = logging.getLogger(__name__)

CANVA_ASSET_UPLOADS_URL = "https://api.canva.com/rest/v1/asset-uploads"
CANVA_DESIGNS_URL = "https://api.canva.com/rest/v1/designs"
CANVA_IMPORTS_URL = "https://api.canva.com/rest/v1/imports"
CANVA_EXPORTS_URL = "https://api.canva.com/rest/v1/exports"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 20 * 1024 * 1024
_POLL_ATTEMPTS = 16
_POLL_SLEEP_SECONDS = 0.4
_EXPORT_POLL_ATTEMPTS = 40
_EXPORT_POLL_SLEEP_SECONDS = 0.5
_MAX_EXPORT_DIM = 25_000
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


def _safe_canva_file_url(url: Any) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("canva_render_failed")
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").split(":")[0].lower()
    if parsed.scheme != "https":
        raise ValueError("canva_render_failed")
    if host != "canva.com" and not host.endswith(".canva.com"):
        raise ValueError("canva_render_failed")
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


def _import_metadata(name: str) -> str:
    trimmed = (name or "Social post").strip()[:50] or "Social post"
    encoded = base64.b64encode(trimmed.encode("utf-8")).decode("ascii")
    return json.dumps(
        {"title_base64": encoded, "mime_type": layered.PPTX_MIME},
        separators=(",", ":"),
    )


def _wait_for_imported_design(db: Session, job_id: str, initial: dict[str, Any]) -> dict[str, Any]:
    job = initial
    for attempt in range(_POLL_ATTEMPTS):
        status = str(job.get("status") or "")
        if status == "success":
            result = job.get("result") if isinstance(job.get("result"), dict) else {}
            designs = result.get("designs") if isinstance(result.get("designs"), list) else []
            design = designs[0] if designs and isinstance(designs[0], dict) else {}
            urls = design.get("urls") if isinstance(design.get("urls"), dict) else {}
            design_id = str(design.get("id") or "").strip() or None
            return {
                "design_id": design_id,
                "edit_url": _safe_edit_url(urls.get("edit_url")),
                "transfer_mode": "editable",
            }
        if status == "failed":
            logger.warning("Canva design import job failed")
            raise ValueError("canva_import_failed")
        if attempt:
            _sleep(_POLL_SLEEP_SECONDS)
        poll = _canva_request(db, "get", f"{CANVA_IMPORTS_URL}/{job_id}")
        if poll.status_code >= 400:
            raise ValueError("canva_import_failed")
        next_job = _json_body(poll).get("job")
        if not isinstance(next_job, dict):
            raise ValueError("canva_import_failed")
        job = next_job
    raise ValueError("canva_import_failed")


def _export_png_format(*, width: int | None, height: int | None) -> dict[str, Any]:
    fmt: dict[str, Any] = {"type": "png", "export_quality": "regular"}
    if width:
        fmt["width"] = max(40, min(_MAX_EXPORT_DIM, int(width)))
    if height:
        fmt["height"] = max(40, min(_MAX_EXPORT_DIM, int(height)))
    return fmt


def _wait_for_export_urls(db: Session, job_id: str, initial: dict[str, Any]) -> list[str]:
    job = initial
    for attempt in range(_EXPORT_POLL_ATTEMPTS):
        status = str(job.get("status") or "")
        if status == "success":
            raw_urls = job.get("urls") if isinstance(job.get("urls"), list) else []
            urls = [str(item).strip() for item in raw_urls if isinstance(item, str) and str(item).strip()]
            if not urls:
                raise ValueError("canva_render_failed")
            return urls
        if status == "failed":
            logger.warning("Canva design export job failed")
            raise ValueError("canva_render_failed")
        if attempt:
            _sleep(_EXPORT_POLL_SLEEP_SECONDS)
        poll = _canva_request(db, "get", f"{CANVA_EXPORTS_URL}/{job_id}")
        if poll.status_code >= 400:
            raise ValueError("canva_render_failed")
        next_job = _json_body(poll).get("job")
        if not isinstance(next_job, dict):
            raise ValueError("canva_render_failed")
        job = next_job
    raise ValueError("canva_render_failed")


def _download_export_png(url: str) -> bytes:
    safe = _safe_canva_file_url(url)
    with canva.http_client() as client:
        response = client.get(safe, follow_redirects=True)
    if response.status_code >= 400:
        logger.warning("Canva export download failed status=%s", response.status_code)
        raise ValueError("canva_render_failed")
    payload = response.content
    if not isinstance(payload, (bytes, bytearray)):
        raise ValueError("canva_render_failed")
    return ensure_png_bytes(bytes(payload))


def export_design_png(
    db: Session,
    *,
    design_id: str,
    width: int | None = None,
    height: int | None = None,
) -> bytes:
    """Create a Canva export job for ``design_id``, poll it, and return PNG bytes."""
    trimmed = (design_id or "").strip()
    if not trimmed:
        raise ValueError("canva_render_failed")
    response = _canva_request(
        db,
        "post",
        CANVA_EXPORTS_URL,
        headers={"Content-Type": "application/json"},
        json_body={
            "design_id": trimmed,
            "format": _export_png_format(width=width, height=height),
        },
    )
    if response.status_code >= 400:
        logger.warning("Canva create export job failed status=%s", response.status_code)
        raise ValueError("canva_render_failed")
    job = _json_body(response).get("job")
    if not isinstance(job, dict) or not job.get("id"):
        raise ValueError("canva_render_failed")
    urls = _wait_for_export_urls(db, str(job["id"]), job)
    return _download_export_png(urls[0])


def attach_rendered_preview(
    db: Session,
    result: dict[str, Any],
    *,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Best-effort: export the Canva design to PNG for in-OS preview. Never drops edit_url."""
    design_id = str(result.get("design_id") or "").strip()
    if not design_id:
        result["preview_png_base64"] = None
        return result
    try:
        png = export_design_png(db, design_id=design_id, width=width, height=height)
        result["preview_png_base64"] = base64.b64encode(png).decode("ascii")
    except Exception:
        logger.warning("Canva PNG render failed; returning edit_url without preview", exc_info=True)
        result["preview_png_base64"] = None
    return result


def import_pptx_to_canva(db: Session, *, pptx_bytes: bytes, title: str) -> dict[str, Any]:
    if not pptx_bytes or pptx_bytes[:2] != b"PK":
        raise ValueError("canva_import_failed")
    response = _canva_request(
        db,
        "post",
        CANVA_IMPORTS_URL,
        headers={
            "Content-Type": "application/octet-stream",
            "Import-Metadata": _import_metadata(title),
        },
        content=pptx_bytes,
    )
    if response.status_code >= 400:
        logger.warning("Canva design import failed status=%s", response.status_code)
        raise ValueError("canva_import_failed")
    job = _json_body(response).get("job")
    if not isinstance(job, dict) or not job.get("id"):
        raise ValueError("canva_import_failed")
    return _wait_for_imported_design(db, str(job["id"]), job)


def export_layers_to_canva(
    db: Session,
    *,
    layers: dict[str, Any],
    images: dict[str, bytes],
    title: str,
) -> dict[str, Any]:
    pptx = layered.build_pptx_from_layers(layers, images)
    if not pptx:
        raise ValueError("canva_import_failed")
    return import_pptx_to_canva(db, pptx_bytes=pptx, title=title)


def export_to_canva(
    db: Session,
    *,
    png_bytes: bytes,
    title: str,
    width: int | None = None,
    height: int | None = None,
    layers: dict[str, Any] | None = None,
    layer_images: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    """Prefer Design Import of layered PPTX; keep PNG create-from-asset as fallback.

    After create/import, also export a PNG so Social Media Builder can show the
    result in-OS without opening Canva.
    """
    if layers:
        try:
            imported = export_layers_to_canva(
                db,
                layers=layers,
                images=layer_images or {},
                title=title,
            )
            return attach_rendered_preview(db, imported, width=width, height=height)
        except Exception:
            logger.warning("Canva editable import failed; falling back to PNG", exc_info=True)
    result = export_png_to_canva(
        db,
        png_bytes=png_bytes,
        title=title,
        width=width,
        height=height,
    )
    result["transfer_mode"] = "png"
    return attach_rendered_preview(db, result, width=width, height=height)
