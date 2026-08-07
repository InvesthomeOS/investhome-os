"""AI Index pipeline: Drive Asset → Extractor → Metadata → Normalizer → Index."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.ai_index import AiDocument, AiDocumentStatus, AiDocumentType
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.services.ai_index.eligibility import (
    MAX_INDEX_DOWNLOAD_BYTES,
    asset_is_ai_index_candidate,
    is_legal_category,
    is_metadata_file,
    is_readme,
    is_special_filename,
    is_text_extension,
)
from investhome_api.services.ai_index.extraction import detect_document_type, extract_bytes
from investhome_api.services.ai_index.keywords import extract_keywords
from investhome_api.services.ai_index.normalizer import detect_language_code, normalize_language_code, normalize_text
from investhome_api.services.ai_index.summarizer import build_summary
from investhome_api.services.google_drive.provider import GoogleDriveProviderProtocol

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _content_checksum(content: bytes) -> str:
    return hashlib.md5(content, usedforsecurity=False).hexdigest()


def _get_or_create_by_asset(db: Session, asset: CreativeStudioMediaAsset) -> AiDocument:
    doc = db.scalar(select(AiDocument).where(AiDocument.asset_id == asset.id))
    if doc is not None:
        return doc
    if asset.external_file_id:
        doc = db.scalar(
            select(AiDocument).where(
                AiDocument.project_id == asset.linked_project_id,
                AiDocument.drive_file_id == asset.external_file_id,
            )
        )
        if doc is not None:
            doc.asset_id = asset.id
            return doc
    if asset.linked_project_id is None:
        raise ValueError("asset has no linked_project_id")
    doc = AiDocument(
        id=uuid4(),
        asset_id=asset.id,
        project_id=asset.linked_project_id,
        drive_file_id=asset.external_file_id,
        document_type=detect_document_type(asset.filename),
        category=asset.folder_category,
        title=asset.filename,
        index_status=AiDocumentStatus.PENDING.value,
        is_active=True,
        version=1,
    )
    db.add(doc)
    db.flush()
    return doc


def _get_or_create_special(
    db: Session,
    *,
    project_id: UUID,
    drive_file_id: str,
    filename: str,
    category: str | None,
) -> AiDocument:
    doc = db.scalar(
        select(AiDocument).where(
            AiDocument.project_id == project_id,
            AiDocument.drive_file_id == drive_file_id,
        )
    )
    if doc is not None:
        return doc
    doc = AiDocument(
        id=uuid4(),
        asset_id=None,
        project_id=project_id,
        drive_file_id=drive_file_id,
        document_type=detect_document_type(filename),
        category=category,
        title=filename,
        index_status=AiDocumentStatus.PENDING.value,
        is_active=True,
        version=1,
    )
    db.add(doc)
    db.flush()
    return doc


def _apply_ready(
    doc: AiDocument,
    *,
    text: str,
    document_type: str,
    checksum: str,
    category: str | None,
    title: str,
    structured: dict[str, Any] | None,
    metadata_extra: dict[str, Any] | None = None,
) -> None:
    normalized = normalize_text(text)
    language = normalize_language_code(detect_language_code(normalized))
    builders = _extract_builders(structured)
    meta: dict[str, Any] = {}
    if structured is not None:
        meta["structured"] = structured
    if metadata_extra:
        meta.update(metadata_extra)

    was_ready = (
        doc.index_status == AiDocumentStatus.READY.value
        and doc.checksum == checksum
        and doc.is_active
    )
    if was_ready and doc.extracted_text == normalized:
        # Unchanged — still refresh timestamps lightly? Prefer skip entirely upstream.
        return

    bumped = doc.checksum is not None and doc.checksum != checksum
    doc.document_type = document_type
    doc.category = category
    doc.language = language
    doc.title = title[:512]
    doc.extracted_text = normalized
    doc.summary = build_summary(normalized)
    doc.keywords = extract_keywords(normalized)
    doc.builders = builders
    doc.checksum = checksum
    doc.metadata_json = meta or None
    doc.is_active = True
    doc.index_status = AiDocumentStatus.READY.value
    doc.skip_reason = None
    doc.error_message = None
    doc.last_indexed_at = _utcnow()
    if bumped:
        doc.version = int(doc.version or 1) + 1
    elif not doc.version:
        doc.version = 1
    doc.updated_at = _utcnow()


def _extract_builders(structured: dict[str, Any] | None) -> list[str] | None:
    if not structured:
        return None
    raw = structured.get("builders") or structured.get("builder") or structured.get("Builder")
    if raw is None:
        return None
    if isinstance(raw, str):
        return [raw] if raw.strip() else None
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return [str(raw)]


def _mark_skipped(doc: AiDocument, reason: str, *, document_type: str | None = None) -> None:
    doc.is_active = True
    doc.index_status = AiDocumentStatus.SKIPPED.value
    doc.skip_reason = reason[:255]
    doc.error_message = None
    doc.last_indexed_at = _utcnow()
    doc.updated_at = _utcnow()
    if document_type:
        doc.document_type = document_type


def _mark_failed(doc: AiDocument, message: str) -> None:
    doc.index_status = AiDocumentStatus.FAILED.value
    doc.error_message = message[:2000]
    doc.last_indexed_at = _utcnow()
    doc.updated_at = _utcnow()


def mark_inactive_for_asset(db: Session, asset_id: UUID) -> None:
    doc = db.scalar(select(AiDocument).where(AiDocument.asset_id == asset_id))
    if doc is None:
        return
    doc.is_active = False
    doc.index_status = AiDocumentStatus.INACTIVE.value
    doc.updated_at = _utcnow()
    _maybe_reindex_vectors(db, doc)


def mark_inactive_for_drive_file(db: Session, *, project_id: UUID, drive_file_id: str) -> None:
    doc = db.scalar(
        select(AiDocument).where(
            AiDocument.project_id == project_id,
            AiDocument.drive_file_id == drive_file_id,
        )
    )
    if doc is None:
        return
    doc.is_active = False
    doc.index_status = AiDocumentStatus.INACTIVE.value
    doc.updated_at = _utcnow()
    _maybe_reindex_vectors(db, doc)


def _maybe_reindex_vectors(db: Session, doc: AiDocument) -> None:
    """Additive Sprint 6 hook — chunk/embed after AI Index updates (never touches Drive)."""
    try:
        from investhome_api.services.ai_search.reindex import reindex_after_ai_document_update

        reindex_after_ai_document_update(db, doc)
    except Exception:  # noqa: BLE001
        logger.warning(
            "ai_search_hook_failed",
            extra={"document_id": str(doc.id)},
            exc_info=True,
        )


def _ensure_vectors_if_missing(db: Session, doc: AiDocument) -> None:
    """Backfill chunks/embeddings when AI Index was ready before Sprint 6."""
    try:
        from investhome_api.models.ai_search import AiChunk

        has_chunk = db.scalar(select(AiChunk.id).where(AiChunk.document_id == doc.id).limit(1))
        if has_chunk is None:
            _maybe_reindex_vectors(db, doc)
    except Exception:  # noqa: BLE001
        logger.warning(
            "ai_search_backfill_check_failed",
            extra={"document_id": str(doc.id)},
            exc_info=True,
        )


def index_asset(
    db: Session,
    asset_id: UUID,
    *,
    provider: GoogleDriveProviderProtocol | None = None,
    force: bool = False,
) -> AiDocument | None:
    """Index one Media Library asset into the AI knowledge index (read-only vs Drive)."""
    asset = db.get(CreativeStudioMediaAsset, asset_id)
    if asset is None:
        logger.warning("ai_index_asset_missing", extra={"asset_id": str(asset_id)})
        return None

    if asset.sync_status == MediaAssetSyncStatus.MISSING.value:
        mark_inactive_for_asset(db, asset.id)
        db.flush()
        return db.scalar(select(AiDocument).where(AiDocument.asset_id == asset.id))

    if asset.linked_project_id is None:
        return None

    if not asset_is_ai_index_candidate(
        filename=asset.filename,
        folder_category=asset.folder_category,
        sync_status=asset.sync_status,
    ):
        doc = _get_or_create_by_asset(db, asset)
        _mark_skipped(
            doc,
            "not_eligible",
            document_type=AiDocumentType.UNSUPPORTED.value,
        )
        db.flush()
        _maybe_reindex_vectors(db, doc)
        return doc

    doc = _get_or_create_by_asset(db, asset)
    source_checksum = asset.external_checksum

    # Legal docs: metadata only (no binary download / full text)
    if is_legal_category(asset.folder_category) and not is_special_filename(asset.filename):
        legal_checksum = source_checksum or f"legal:{asset.id}:{asset.filename}:{asset.file_size}"
        if (
            not force
            and doc.is_active
            and doc.index_status == AiDocumentStatus.READY.value
            and doc.checksum == legal_checksum
        ):
            _ensure_vectors_if_missing(db, doc)
            return doc
        meta = {
            "filename": asset.filename,
            "content_type": asset.content_type,
            "file_size": asset.file_size,
            "folder_category": asset.folder_category,
            "drive_meta": asset.drive_meta_json,
            "web_view_link": asset.web_view_link,
        }
        title = asset.filename
        text = "\n".join(
            f"{k}: {v}" for k, v in meta.items() if v is not None and k != "drive_meta"
        )
        if asset.drive_meta_json:
            text += "\n" + "\n".join(
                f"{k}: {v}" for k, v in asset.drive_meta_json.items()
            )
        _apply_ready(
            doc,
            text=text,
            document_type=AiDocumentType.LEGAL_META.value,
            checksum=legal_checksum,
            category=asset.folder_category,
            title=title,
            structured=asset.drive_meta_json if isinstance(asset.drive_meta_json, dict) else None,
            metadata_extra={"legal_meta_only": True, "asset_meta": meta},
        )
        db.flush()
        _maybe_reindex_vectors(db, doc)
        return doc

    if not is_text_extension(asset.filename) and not is_special_filename(asset.filename):
        _mark_skipped(doc, f"unsupported_format:{asset.filename}", document_type=AiDocumentType.UNSUPPORTED.value)
        db.flush()
        _maybe_reindex_vectors(db, doc)
        return doc

    if (
        not force
        and source_checksum
        and doc.is_active
        and doc.index_status == AiDocumentStatus.READY.value
        and doc.checksum == source_checksum
    ):
        _ensure_vectors_if_missing(db, doc)
        return doc

    try:
        content = _download_asset_bytes(db, asset, provider=provider)
    except Exception as exc:  # noqa: BLE001
        _mark_failed(doc, f"download_failed: {exc}")
        db.flush()
        logger.warning(
            "ai_index_download_failed",
            extra={"asset_id": str(asset.id), "error": str(exc)[:300]},
        )
        return doc

    checksum = source_checksum or _content_checksum(content)
    if (
        not force
        and doc.is_active
        and doc.index_status == AiDocumentStatus.READY.value
        and doc.checksum == checksum
    ):
        _ensure_vectors_if_missing(db, doc)
        return doc

    extracted = extract_bytes(content, asset.filename)
    if extracted.skipped:
        _mark_skipped(doc, extracted.skip_reason or "unsupported", document_type=extracted.document_type)
        doc.checksum = checksum
        db.flush()
        _maybe_reindex_vectors(db, doc)
        return doc

    _apply_ready(
        doc,
        text=extracted.text,
        document_type=extracted.document_type,
        checksum=checksum,
        category=asset.folder_category,
        title=asset.filename,
        structured=extracted.structured,
        metadata_extra={"extraction_method": extracted.method},
    )
    db.flush()
    _maybe_reindex_vectors(db, doc)
    return doc


def index_special_drive_file(
    db: Session,
    *,
    project_id: UUID,
    drive_file_id: str,
    filename: str,
    category: str | None,
    provider: GoogleDriveProviderProtocol,
    checksum: str | None = None,
    force: bool = False,
) -> AiDocument:
    """Index README.md / metadata.json (not Media Library assets)."""
    doc = _get_or_create_special(
        db,
        project_id=project_id,
        drive_file_id=drive_file_id,
        filename=filename,
        category=category,
    )
    if (
        not force
        and checksum
        and doc.is_active
        and doc.index_status == AiDocumentStatus.READY.value
        and doc.checksum == checksum
    ):
        _ensure_vectors_if_missing(db, doc)
        return doc

    try:
        content = provider.download_bytes(drive_file_id, max_bytes=MAX_INDEX_DOWNLOAD_BYTES)
    except Exception as exc:  # noqa: BLE001
        _mark_failed(doc, f"download_failed: {exc}")
        db.flush()
        return doc

    content_checksum = checksum or _content_checksum(content)
    if (
        not force
        and doc.is_active
        and doc.index_status == AiDocumentStatus.READY.value
        and doc.checksum == content_checksum
    ):
        _ensure_vectors_if_missing(db, doc)
        return doc

    extracted = extract_bytes(content, filename)
    if extracted.skipped:
        _mark_skipped(doc, extracted.skip_reason or "unsupported", document_type=extracted.document_type)
        doc.checksum = content_checksum
        db.flush()
        _maybe_reindex_vectors(db, doc)
        return doc

    _apply_ready(
        doc,
        text=extracted.text,
        document_type=extracted.document_type,
        checksum=content_checksum,
        category=category,
        title=filename,
        structured=extracted.structured,
        metadata_extra={
            "extraction_method": extracted.method,
            "special": "readme" if is_readme(filename) else "metadata",
        },
    )
    db.flush()
    _maybe_reindex_vectors(db, doc)
    return doc


def _download_asset_bytes(
    db: Session,
    asset: CreativeStudioMediaAsset,
    *,
    provider: GoogleDriveProviderProtocol | None,
) -> bytes:
    if asset.source_type == MediaAssetSourceType.GOOGLE_DRIVE.value and asset.external_file_id:
        if provider is None:
            from investhome_api.services.google_drive.provider import get_google_drive_provider

            provider = get_google_drive_provider()
        return provider.download_bytes(asset.external_file_id, max_bytes=MAX_INDEX_DOWNLOAD_BYTES)

    # Local upload — read via storage provider
    from investhome_api.services.storage.factory import get_storage_provider

    storage = get_storage_provider()
    with storage.open(asset.storage_key) as handle:
        data = handle.read(MAX_INDEX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_INDEX_DOWNLOAD_BYTES:
        raise ValueError("file_too_large_for_ai_index")
    return data


def reindex_project(
    db: Session,
    project_id: UUID,
    *,
    provider: GoogleDriveProviderProtocol | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Reindex eligible Drive-linked assets + discover special README/metadata files."""
    from investhome_api.models.project_drive import ProjectDriveMapping
    from investhome_api.services.ai_index.eligibility import is_archive_category
    from investhome_api.services.google_drive.categories import (
        ARCHIVE_CATEGORY,
        METADATA_FILENAME,
        README_FILENAME,
        resolve_folder_category,
    )

    stats = {"assets": 0, "special": 0, "skipped": 0, "inactive": 0, "errors": 0}

    assets = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project_id,
                CreativeStudioMediaAsset.source_type == MediaAssetSourceType.GOOGLE_DRIVE.value,
            )
        ).all()
    )
    for asset in assets:
        try:
            if asset.sync_status == MediaAssetSyncStatus.MISSING.value:
                mark_inactive_for_asset(db, asset.id)
                stats["inactive"] += 1
                continue
            if not asset_is_ai_index_candidate(
                filename=asset.filename,
                folder_category=asset.folder_category,
                sync_status=asset.sync_status,
            ):
                stats["skipped"] += 1
                continue
            index_asset(db, asset.id, provider=provider, force=force)
            stats["assets"] += 1
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
            logger.warning("ai_index_reindex_asset_failed", exc_info=True)

    mapping = db.scalar(
        select(ProjectDriveMapping).where(
            ProjectDriveMapping.project_id == project_id,
            ProjectDriveMapping.archived_at.is_(None),
        )
    )
    if mapping is None or provider is None:
        db.flush()
        return stats

    # Walk Drive tree for README / metadata.json (not in Media Library)
    stack: list[tuple[str, str | None, bool]] = [(mapping.drive_folder_id, None, False)]
    while stack:
        folder_id, category, under_archive = stack.pop()
        try:
            children = list(provider.list_children(folder_id))
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
            continue
        for child in children:
            if child.is_folder:
                child_cat = resolve_folder_category(child.name) or category
                is_arch = under_archive or child_cat == ARCHIVE_CATEGORY
                stack.append((child.id, child_cat, is_arch))
                continue
            if under_archive or is_archive_category(category):
                continue
            name_lower = child.name.lower()
            if name_lower not in {README_FILENAME.lower(), METADATA_FILENAME.lower()}:
                continue
            try:
                index_special_drive_file(
                    db,
                    project_id=project_id,
                    drive_file_id=child.id,
                    filename=child.name,
                    category=category,
                    provider=provider,
                    checksum=child.md5_checksum,
                    force=force,
                )
                stats["special"] += 1
            except Exception:  # noqa: BLE001
                stats["errors"] += 1
                logger.warning("ai_index_reindex_special_failed", exc_info=True)

    db.flush()
    return stats
