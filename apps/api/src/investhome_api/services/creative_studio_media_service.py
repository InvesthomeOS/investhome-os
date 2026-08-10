"""Creative Studio Media Library — upload, list, search, archive."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    CreativeStudioMediaFolder,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio_media import (
    CreativeStudioMediaAssetResponse,
    CreativeStudioMediaFolderResponse,
)
from investhome_api.services.document_validation import (
    content_stream,
    extract_extension,
    sanitize_filename,
    validate_extension,
    validate_mime_type,
)
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

MEDIA_STORAGE_PREFIX = "creative-studio-media"
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp", "gif"})


def asset_content_url(asset_id: UUID) -> str:
    """Relative API path for auth-gated binary serving (Document Center pattern)."""
    return f"/creative-studio/media/assets/{asset_id}/content"


def build_folder_response(folder: CreativeStudioMediaFolder) -> CreativeStudioMediaFolderResponse:
    return CreativeStudioMediaFolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        company_id=folder.company_id,
        created_by_user_id=folder.created_by_user_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        archived_at=folder.archived_at,
    )


def build_asset_response(asset: CreativeStudioMediaAsset) -> CreativeStudioMediaAssetResponse:
    tags = asset.tags if isinstance(asset.tags, list) else None
    return CreativeStudioMediaAssetResponse(
        id=asset.id,
        filename=asset.filename,
        content_type=asset.content_type,
        file_size=asset.file_size,
        width=asset.width,
        height=asset.height,
        storage_provider=asset.storage_provider,
        storage_key=asset.storage_key,
        thumbnail_storage_key=asset.thumbnail_storage_key,
        url=asset_content_url(asset.id),
        thumbnail_url=None,
        folder_id=asset.folder_id,
        tags=[str(t) for t in tags] if tags is not None else None,
        company_id=asset.company_id,
        linked_project_id=asset.linked_project_id,
        uploaded_by_user_id=asset.uploaded_by_user_id,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        archived_at=asset.archived_at,
        thumbnail_pending=asset.thumbnail_storage_key is None,
        source_type=asset.source_type,
        external_file_id=asset.external_file_id,
        external_modified_at=asset.external_modified_at,
        sync_status=asset.sync_status,
        folder_category=asset.folder_category,
        possible_duplicate=bool(asset.possible_duplicate),
        web_view_link=asset.web_view_link,
        external_checksum=asset.external_checksum,
    )


def get_folder_or_404(
    folder_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> CreativeStudioMediaFolder:
    folder = db.get(CreativeStudioMediaFolder, folder_id)
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media folder not found")
    if folder.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media folder not found")
    return folder


def get_asset_or_404(
    asset_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> CreativeStudioMediaAsset:
    asset = db.get(CreativeStudioMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    if asset.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    return asset


def create_folder(
    db: Session,
    *,
    name: str,
    parent_id: UUID | None,
    company_id: UUID | None,
    actor: User,
) -> CreativeStudioMediaFolder:
    if parent_id is not None:
        get_folder_or_404(parent_id, db)
    folder = CreativeStudioMediaFolder(
        name=name.strip(),
        parent_id=parent_id,
        company_id=company_id,
        created_by_user_id=actor.id,
    )
    db.add(folder)
    db.flush()
    return folder


def list_folders(
    db: Session,
    *,
    parent_id: UUID | None = None,
    include_archived: bool = False,
) -> list[CreativeStudioMediaFolderResponse]:
    query = select(CreativeStudioMediaFolder)
    if not include_archived:
        query = query.where(CreativeStudioMediaFolder.archived_at.is_(None))
    if parent_id is not None:
        query = query.where(CreativeStudioMediaFolder.parent_id == parent_id)
    rows = list(db.scalars(query.order_by(CreativeStudioMediaFolder.name.asc())).all())
    return [build_folder_response(row) for row in rows]


def _generate_media_storage_key(ext: str) -> str:
    now = datetime.now(UTC)
    unique = uuid4().hex
    return f"{MEDIA_STORAGE_PREFIX}/{now.year:04d}/{now.month:02d}/{unique}.{ext}"


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


def _parse_tags(raw: str | None) -> list[str] | None:
    if raw is None or raw.strip() == "":
        return None
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    parts = [part.strip() for part in re.split(r"[,;]", text) if part.strip()]
    return parts or None


async def _read_upload(file: UploadFile) -> tuple[bytes, str, str, str, int]:
    """Reuse Document Center validation rules for media uploads."""
    settings = get_settings()
    max_bytes = settings.document_max_upload_bytes
    original_name = sanitize_filename(file.filename or "upload")
    ext = extract_extension(original_name)
    validate_extension(ext)
    mime_type = validate_mime_type(ext, file.content_type)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="creative_studio.media.errors.file_too_large",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="creative_studio.media.errors.empty_file",
        )
    return b"".join(chunks), ext, mime_type, original_name, total


async def upload_asset(
    db: Session,
    *,
    file: UploadFile,
    actor: User,
    folder_id: UUID | None = None,
    tags_raw: str | None = None,
    company_id: UUID | None = None,
    linked_project_id: UUID | None = None,
) -> CreativeStudioMediaAsset:
    if folder_id is not None:
        get_folder_or_404(folder_id, db)

    content, ext, mime_type, original_name, file_size = await _read_upload(file)
    storage_key = _generate_media_storage_key(ext)
    storage = get_storage_provider()
    storage.save(storage_key, content_stream(content), content_length=file_size)

    width, height = _extract_image_dimensions(content, ext)
    # Thumbnail generation is intentionally stubbed for foundation sprint.
    thumbnail_storage_key = None

    asset = CreativeStudioMediaAsset(
        filename=original_name,
        content_type=mime_type,
        file_size=file_size,
        width=width,
        height=height,
        storage_provider=provider_enum().value,
        storage_key=storage_key,
        thumbnail_storage_key=thumbnail_storage_key,
        folder_id=folder_id,
        tags=_parse_tags(tags_raw),
        company_id=company_id,
        linked_project_id=linked_project_id,
        uploaded_by_user_id=actor.id,
    )
    db.add(asset)
    db.flush()
    return asset


def list_assets(
    db: Session,
    *,
    folder_id: UUID | None = None,
    tag: str | None = None,
    linked_project_id: UUID | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CreativeStudioMediaAssetResponse], int]:
    query = select(CreativeStudioMediaAsset)
    if not include_archived:
        query = query.where(CreativeStudioMediaAsset.archived_at.is_(None))
    if folder_id is not None:
        query = query.where(CreativeStudioMediaAsset.folder_id == folder_id)
    if linked_project_id is not None:
        query = query.where(CreativeStudioMediaAsset.linked_project_id == linked_project_id)
    if tag:
        query = query.where(cast(CreativeStudioMediaAsset.tags, String).ilike(f"%{tag.strip()}%"))

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(CreativeStudioMediaAsset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return [build_asset_response(row) for row in rows], total


def search_assets(
    db: Session,
    *,
    q: str,
    folder_id: UUID | None = None,
    tag: str | None = None,
    linked_project_id: UUID | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CreativeStudioMediaAssetResponse], int]:
    pattern = f"%{q.strip()}%"
    query = select(CreativeStudioMediaAsset)
    if not include_archived:
        query = query.where(CreativeStudioMediaAsset.archived_at.is_(None))
    if folder_id is not None:
        query = query.where(CreativeStudioMediaAsset.folder_id == folder_id)
    if linked_project_id is not None:
        query = query.where(CreativeStudioMediaAsset.linked_project_id == linked_project_id)

    filters: list[Any] = [
        CreativeStudioMediaAsset.filename.ilike(pattern),
        cast(CreativeStudioMediaAsset.tags, String).ilike(pattern),
        CreativeStudioMediaAsset.content_type.ilike(pattern),
    ]
    query = query.where(or_(*filters))
    if tag:
        query = query.where(cast(CreativeStudioMediaAsset.tags, String).ilike(f"%{tag.strip()}%"))

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(CreativeStudioMediaAsset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return [build_asset_response(row) for row in rows], total


def update_asset_tags(
    db: Session,
    asset: CreativeStudioMediaAsset,
    tags: list[str],
) -> CreativeStudioMediaAsset:
    cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
    asset.tags = cleaned
    asset.updated_at = datetime.now(UTC)
    db.flush()
    return asset


def archive_asset(db: Session, asset: CreativeStudioMediaAsset) -> CreativeStudioMediaAsset:
    asset.archived_at = datetime.now(UTC)
    asset.updated_at = datetime.now(UTC)
    db.flush()
    return asset
