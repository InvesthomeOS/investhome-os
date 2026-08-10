"""Additive hooks from Drive sync into AI Index (never modify Drive)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.ai_index.eligibility import asset_is_ai_index_candidate, is_special_filename
from investhome_api.services.ai_index.pipeline import (
    index_asset,
    index_special_drive_file,
    mark_inactive_for_asset,
    mark_inactive_for_drive_file,
)
from investhome_api.services.ai_index.queue import enqueue_asset_ai_index
from investhome_api.services.google_drive.provider import DriveFileMeta, GoogleDriveProviderProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpecialDriveFile:
    meta: DriveFileMeta
    folder_category: str | None
    parent_folder_id: str


def notify_asset_upserted(
    db: Session,
    asset: CreativeStudioMediaAsset,
    *,
    content_changed: bool,
    provider: GoogleDriveProviderProtocol | None = None,
) -> None:
    """Small post-upsert hook — index when content-relevant fields change."""
    if not content_changed:
        return
    if not asset_is_ai_index_candidate(
        filename=asset.filename,
        folder_category=asset.folder_category,
        sync_status=asset.sync_status,
    ):
        return
    try:
        settings = get_settings()
        if settings.ai_index_processing_sync:
            # Same session — asset may not be committed yet (tests / local sync mode)
            index_asset(db, asset.id, provider=provider, force=False)
        else:
            # Defer ARQ until sync transaction commits (avoids ai_index_asset_missing race)
            enqueue_asset_ai_index(asset.id, db=db)
    except Exception:  # noqa: BLE001
        logger.warning("ai_index_enqueue_failed", extra={"asset_id": str(asset.id)}, exc_info=True)


def notify_asset_missing(db: Session, asset: CreativeStudioMediaAsset) -> None:
    """Mark linked AI document inactive when Drive asset becomes MISSING."""
    try:
        mark_inactive_for_asset(db, asset.id)
        if asset.external_file_id and asset.linked_project_id:
            mark_inactive_for_drive_file(
                db,
                project_id=asset.linked_project_id,
                drive_file_id=asset.external_file_id,
            )
    except Exception:  # noqa: BLE001
        logger.warning("ai_index_mark_inactive_failed", extra={"asset_id": str(asset.id)}, exc_info=True)


def index_special_files(
    db: Session,
    *,
    project_id: UUID,
    provider: GoogleDriveProviderProtocol,
    special_files: list[SpecialDriveFile],
) -> None:
    """Index README / metadata collected during Drive walk (additive)."""
    for item in special_files:
        if not is_special_filename(item.meta.name):
            continue
        try:
            index_special_drive_file(
                db,
                project_id=project_id,
                drive_file_id=item.meta.id,
                filename=item.meta.name,
                category=item.folder_category,
                provider=provider,
                checksum=item.meta.md5_checksum,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "ai_index_special_failed",
                extra={"drive_file_id": item.meta.id, "name": item.meta.name},
                exc_info=True,
            )


def maybe_index_special_change(
    db: Session,
    *,
    project_id: UUID,
    provider: GoogleDriveProviderProtocol,
    meta: DriveFileMeta,
    category: str | None,
) -> None:
    """Incremental sync: README/metadata file changed."""
    if not is_special_filename(meta.name):
        return
    try:
        index_special_drive_file(
            db,
            project_id=project_id,
            drive_file_id=meta.id,
            filename=meta.name,
            category=category,
            provider=provider,
            checksum=meta.md5_checksum,
        )
    except Exception:  # noqa: BLE001
        logger.warning("ai_index_special_incremental_failed", exc_info=True)
