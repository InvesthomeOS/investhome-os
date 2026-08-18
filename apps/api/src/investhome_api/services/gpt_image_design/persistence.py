"""Persist GPT Image outputs into Investhome-controlled storage immediately."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
)
from investhome_api.models.user_auth import User
from investhome_api.services.creative_studio_media_service import (
    IMAGE_EXTENSIONS,
    MEDIA_STORAGE_PREFIX,
    asset_content_url,
)
from investhome_api.services.document_validation import content_stream
from investhome_api.services.storage.factory import get_storage_provider, provider_enum


def _extract_image_dimensions(content: bytes, ext: str) -> tuple[int | None, int | None]:
    if ext not in IMAGE_EXTENSIONS:
        return None, None
    try:
        from PIL import Image

        with Image.open(BytesIO(content)) as img:
            width, height = img.size
            return int(width), int(height)
    except Exception:
        return None, None


def _ext_from_content_type(content_type: str) -> str:
    ctype = (content_type or "").lower()
    if "png" in ctype:
        return "png"
    if "webp" in ctype:
        return "webp"
    return "jpg"


def persist_gpt_image(
    db: Session,
    *,
    actor: User,
    linked_project_id: UUID | None,
    content: bytes,
    content_type: str,
    campaign_mode: str,
    session_id: str,
    provider_generation_id: str | None,
    campaign_context_id: str | None,
    brief_excerpt: str,
) -> CreativeStudioMediaAsset:
    ext = _ext_from_content_type(content_type)
    now = datetime.now(UTC)
    storage_key = f"{MEDIA_STORAGE_PREFIX}/{now.year:04d}/{now.month:02d}/{uuid4().hex}.{ext}"
    storage = get_storage_provider()
    storage.save(storage_key, content_stream(content), content_length=len(content))
    width, height = _extract_image_dimensions(content, ext)
    mime = {
        "png": "image/png",
        "webp": "image/webp",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(ext, content_type or "image/png")
    tags: list[Any] = [
        "provider:gpt-image",
        "gpt-image",
        f"mode:{campaign_mode}",
        f"session:{session_id}",
    ]
    if provider_generation_id:
        tags.append(f"generation:{provider_generation_id[:80]}")
    if campaign_context_id:
        tags.append(f"campaign:{campaign_context_id[:80]}")
    if brief_excerpt:
        tags.append(f"brief:{brief_excerpt[:80]}")
    asset = CreativeStudioMediaAsset(
        filename=f"gpt-image-{campaign_mode}-{session_id[:8]}.{ext}",
        content_type=mime,
        file_size=len(content),
        width=width,
        height=height,
        storage_provider=provider_enum().value,
        storage_key=storage_key,
        linked_project_id=linked_project_id,
        uploaded_by_user_id=actor.id,
        source_type=MediaAssetSourceType.UPLOAD.value,
        tags=tags,
    )
    db.add(asset)
    db.flush()
    return asset


def asset_url(asset_id: UUID) -> str:
    return asset_content_url(asset_id)


def sniff_image_content_type(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"
