"""Drive Asset Scanner — recursive project folder scan into Creative Studio Media Library."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project_drive import ProjectDriveMapping
from investhome_api.services.google_drive.categories import (
    ARCHIVE_CATEGORY,
    METADATA_FILENAME,
    README_FILENAME,
    resolve_folder_category,
)
from investhome_api.services.google_drive.errors import GoogleDriveError
from investhome_api.services.google_drive.provider import (
    DriveFileMeta,
    GoogleDriveProviderProtocol,
)

logger = logging.getLogger(__name__)

STORAGE_PROVIDER_GOOGLE_DRIVE = "google_drive"


def _normalize_dt(value: datetime | None) -> datetime | None:
    """Compare datetimes robustly across SQLite (naive) and Postgres (aware)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass
class SyncErrorItem:
    path: str
    code: str
    message: str


@dataclass
class PossibleDuplicateItem:
    drive_file_id: str
    existing_asset_id: str
    checksum: str
    filename: str


@dataclass
class DriveSyncSummary:
    scanned: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    missing: int = 0
    skipped: int = 0
    possible_duplicates: list[PossibleDuplicateItem] = field(default_factory=list)
    errors: list[SyncErrorItem] = field(default_factory=list)
    dry_run: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "missing": self.missing,
            "skipped": self.skipped,
            "possible_duplicates": [
                {
                    "drive_file_id": d.drive_file_id,
                    "existing_asset_id": d.existing_asset_id,
                    "checksum": d.checksum,
                    "filename": d.filename,
                }
                for d in self.possible_duplicates
            ],
            "errors": [
                {"path": e.path, "code": e.code, "message": e.message} for e in self.errors
            ],
            "dry_run": self.dry_run,
            "warnings": list(self.warnings),
        }


@dataclass
class _DiscoveredFile:
    meta: DriveFileMeta
    folder_category: str | None
    parent_folder_id: str
    indexable: bool = True
    folder_meta: dict[str, Any] | None = None


class DriveAssetScanner:
    """Scan one mapped project Drive folder into ``creative_studio_media_assets``."""

    def __init__(
        self,
        db: Session,
        provider: GoogleDriveProviderProtocol,
        *,
        project_id: UUID,
        company_id: UUID | None = None,
    ) -> None:
        self.db = db
        self.provider = provider
        self.project_id = project_id
        self.company_id = company_id

    def sync(self, *, dry_run: bool = False) -> DriveSyncSummary:
        summary = DriveSyncSummary(dry_run=dry_run)
        mapping = self._get_active_mapping()
        if mapping is None:
            summary.errors.append(
                SyncErrorItem(
                    path="",
                    code="mapping_not_found",
                    message="No active Drive mapping for this project",
                )
            )
            return summary

        if not mapping.drive_sync_enabled:
            summary.errors.append(
                SyncErrorItem(
                    path=mapping.drive_folder_id,
                    code="sync_disabled",
                    message="Drive sync is disabled for this project mapping",
                )
            )
            return summary

        try:
            if not self.provider.is_descendant_of_root(mapping.drive_folder_id):
                summary.errors.append(
                    SyncErrorItem(
                        path=mapping.drive_folder_id,
                        code="outside_root",
                        message="Project Drive folder is outside GOOGLE_DRIVE_ROOT_FOLDER_ID",
                    )
                )
                logger.warning(
                    "drive_sync_outside_root",
                    extra={
                        "project_id": str(self.project_id),
                        "drive_folder_id": mapping.drive_folder_id,
                    },
                )
                return summary
        except GoogleDriveError as exc:
            summary.errors.append(
                SyncErrorItem(path=mapping.drive_folder_id, code=exc.code, message=exc.message)
            )
            logger.warning(
                "drive_sync_root_check_failed",
                extra={"project_id": str(self.project_id), "code": exc.code},
            )
            return summary

        discovered: list[_DiscoveredFile] = []
        try:
            self._walk_folder(
                mapping.drive_folder_id,
                folder_category=None,
                discovered=discovered,
                summary=summary,
                under_archive=False,
            )
        except GoogleDriveError as exc:
            summary.errors.append(
                SyncErrorItem(path=mapping.drive_folder_id, code=exc.code, message=exc.message)
            )
            logger.warning(
                "drive_sync_walk_failed",
                extra={"project_id": str(self.project_id), "code": exc.code},
            )
            return summary

        summary.scanned = len(discovered)
        seen_file_ids = {item.meta.id for item in discovered}

        existing_by_file_id = self._load_existing_drive_assets()
        checksum_index = self._build_checksum_index(existing_by_file_id)

        for item in discovered:
            try:
                self._upsert_discovered(
                    item,
                    existing_by_file_id=existing_by_file_id,
                    checksum_index=checksum_index,
                    summary=summary,
                    dry_run=dry_run,
                )
            except Exception as exc:  # noqa: BLE001 — keep scan resilient
                summary.errors.append(
                    SyncErrorItem(
                        path=item.meta.name,
                        code="upsert_error",
                        message=str(exc),
                    )
                )
                logger.warning(
                    "drive_sync_upsert_failed",
                    extra={
                        "project_id": str(self.project_id),
                        "drive_file_id": item.meta.id,
                        "error_type": type(exc).__name__,
                    },
                )

        # Mark missing Drive files (never hard-delete)
        for file_id, asset in existing_by_file_id.items():
            if file_id in seen_file_ids:
                continue
            if asset.sync_status == MediaAssetSyncStatus.MISSING.value:
                summary.unchanged += 1
                continue
            summary.missing += 1
            if not dry_run:
                asset.sync_status = MediaAssetSyncStatus.MISSING.value
                if asset.archived_at is None:
                    asset.archived_at = datetime.now(UTC)
                asset.updated_at = datetime.now(UTC)

        if not dry_run:
            mapping.last_drive_sync_at = datetime.now(UTC)
            self.db.flush()

        logger.info(
            "drive_sync_complete",
            extra={
                "project_id": str(self.project_id),
                "dry_run": dry_run,
                "assets_scanned": summary.scanned,
                "assets_created": summary.created,
                "assets_updated": summary.updated,
                "assets_unchanged": summary.unchanged,
                "assets_missing": summary.missing,
                "error_count": len(summary.errors),
            },
        )
        return summary

    def _get_active_mapping(self) -> ProjectDriveMapping | None:
        return self.db.scalar(
            select(ProjectDriveMapping).where(
                ProjectDriveMapping.project_id == self.project_id,
                ProjectDriveMapping.archived_at.is_(None),
            )
        )

    def _load_existing_drive_assets(self) -> dict[str, CreativeStudioMediaAsset]:
        rows = self.db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == self.project_id,
                CreativeStudioMediaAsset.source_type == MediaAssetSourceType.GOOGLE_DRIVE.value,
                CreativeStudioMediaAsset.external_file_id.is_not(None),
            )
        ).all()
        return {a.external_file_id: a for a in rows if a.external_file_id}

    def _build_checksum_index(
        self,
        existing_by_file_id: dict[str, CreativeStudioMediaAsset],
    ) -> dict[str, list[CreativeStudioMediaAsset]]:
        index: dict[str, list[CreativeStudioMediaAsset]] = {}
        for asset in existing_by_file_id.values():
            if asset.external_checksum:
                index.setdefault(asset.external_checksum, []).append(asset)
        # Also include any Drive-sourced checksums for this project already loaded
        return index

    def _walk_folder(
        self,
        folder_id: str,
        *,
        folder_category: str | None,
        discovered: list[_DiscoveredFile],
        summary: DriveSyncSummary,
        under_archive: bool,
    ) -> None:
        children = list(self.provider.list_children(folder_id))
        folder_meta: dict[str, Any] | None = None
        indexable = True

        # Parse metadata.json in this folder (if present)
        for child in children:
            if child.is_folder:
                continue
            if child.name.lower() == METADATA_FILENAME.lower():
                folder_meta, meta_warnings, indexable = self._parse_metadata(child)
                summary.warnings.extend(meta_warnings)
                break

        for child in children:
            if child.is_folder:
                category = resolve_folder_category(child.name) or folder_category
                is_archive = under_archive or category == ARCHIVE_CATEGORY
                self._walk_folder(
                    child.id,
                    folder_category=category,
                    discovered=discovered,
                    summary=summary,
                    under_archive=is_archive,
                )
                continue

            name_lower = child.name.lower()
            if name_lower == METADATA_FILENAME.lower():
                summary.skipped += 1
                continue
            if name_lower == README_FILENAME.lower():
                summary.skipped += 1
                continue
            if under_archive or folder_category == ARCHIVE_CATEGORY:
                # Sprint rule: no active Media Library assets from 10_ARCHIVE
                summary.skipped += 1
                continue
            if not indexable:
                summary.skipped += 1
                continue

            discovered.append(
                _DiscoveredFile(
                    meta=child,
                    folder_category=folder_category,
                    parent_folder_id=folder_id,
                    indexable=indexable,
                    folder_meta=folder_meta,
                )
            )

    def _parse_metadata(
        self,
        meta_file: DriveFileMeta,
    ) -> tuple[dict[str, Any] | None, list[str], bool]:
        """Return (parsed_dict_or_None, warnings, indexable). Malformed = warning, don't abort."""
        warnings: list[str] = []
        indexable = True
        try:
            raw = self.provider.download_bytes(meta_file.id, max_bytes=256_000)
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                warnings.append(f"metadata.json in parent of {meta_file.id} is not an object")
                return None, warnings, True
            if data.get("index") is False:
                indexable = False
            return data, warnings, indexable
        except GoogleDriveError as exc:
            warnings.append(f"Could not read metadata.json ({exc.code}): {exc.message}")
            return None, warnings, True
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            warnings.append(f"Malformed metadata.json: {exc}")
            return None, warnings, True

    def _upsert_discovered(
        self,
        item: _DiscoveredFile,
        *,
        existing_by_file_id: dict[str, CreativeStudioMediaAsset],
        checksum_index: dict[str, list[CreativeStudioMediaAsset]],
        summary: DriveSyncSummary,
        dry_run: bool,
    ) -> None:
        meta = item.meta
        existing = existing_by_file_id.get(meta.id)

        # Checksum possible-duplicate (different drive_file_id) — never auto-merge
        if meta.md5_checksum and not existing:
            for other in checksum_index.get(meta.md5_checksum, []):
                if other.external_file_id and other.external_file_id != meta.id:
                    summary.possible_duplicates.append(
                        PossibleDuplicateItem(
                            drive_file_id=meta.id,
                            existing_asset_id=str(other.id),
                            checksum=meta.md5_checksum,
                            filename=meta.name,
                        )
                    )
                    break

        if existing is None:
            summary.created += 1
            if dry_run:
                return
            asset = CreativeStudioMediaAsset(
                id=uuid4(),
                filename=meta.name[:255],
                content_type=meta.mime_type[:120],
                file_size=meta.size or 0,
                storage_provider=STORAGE_PROVIDER_GOOGLE_DRIVE,
                storage_key=f"gdrive:{meta.id}",
                linked_project_id=self.project_id,
                company_id=self.company_id,
                source_type=MediaAssetSourceType.GOOGLE_DRIVE.value,
                external_file_id=meta.id,
                external_parent_id=item.parent_folder_id,
                external_modified_at=meta.modified_at,
                external_checksum=meta.md5_checksum,
                sync_status=MediaAssetSyncStatus.ACTIVE.value,
                folder_category=item.folder_category,
                possible_duplicate=bool(
                    meta.md5_checksum
                    and any(
                        o.external_file_id != meta.id
                        for o in checksum_index.get(meta.md5_checksum, [])
                    )
                ),
                web_view_link=meta.web_view_link,
                external_thumbnail_link=meta.thumbnail_link,
                drive_meta_json=item.folder_meta,
            )
            self.db.add(asset)
            self.db.flush()
            existing_by_file_id[meta.id] = asset
            if meta.md5_checksum:
                checksum_index.setdefault(meta.md5_checksum, []).append(asset)
            return

        # Same drive_file_id → same Asset ID (rename/move preserve id)
        changed = False
        new_filename = meta.name[:255]
        new_content_type = meta.mime_type[:120]
        new_size = meta.size or 0

        if existing.filename != new_filename:
            changed = True
        if existing.content_type != new_content_type:
            changed = True
        if existing.file_size != new_size:
            changed = True
        if existing.external_parent_id != item.parent_folder_id:
            changed = True
        if existing.folder_category != item.folder_category:
            changed = True
        if existing.external_checksum != meta.md5_checksum:
            changed = True
        if existing.web_view_link != meta.web_view_link:
            changed = True
        if existing.external_thumbnail_link != meta.thumbnail_link:
            changed = True

        modified_changed = bool(
            meta.modified_at
            and _normalize_dt(existing.external_modified_at) != _normalize_dt(meta.modified_at)
        )
        if modified_changed:
            changed = True

        was_missing = existing.sync_status == MediaAssetSyncStatus.MISSING.value
        if was_missing:
            changed = True
        if item.folder_meta is not None and existing.drive_meta_json != item.folder_meta:
            changed = True

        if changed:
            summary.updated += 1
        else:
            summary.unchanged += 1

        if dry_run:
            return

        if existing.filename != new_filename:
            existing.filename = new_filename
        if existing.content_type != new_content_type:
            existing.content_type = new_content_type
        if existing.file_size != new_size:
            existing.file_size = new_size
        if existing.external_parent_id != item.parent_folder_id:
            existing.external_parent_id = item.parent_folder_id
        if existing.folder_category != item.folder_category:
            existing.folder_category = item.folder_category
        if existing.external_checksum != meta.md5_checksum:
            existing.external_checksum = meta.md5_checksum
        if existing.web_view_link != meta.web_view_link:
            existing.web_view_link = meta.web_view_link
        if existing.external_thumbnail_link != meta.thumbnail_link:
            existing.external_thumbnail_link = meta.thumbnail_link
        if modified_changed and meta.modified_at is not None:
            existing.external_modified_at = meta.modified_at
        if was_missing:
            existing.sync_status = MediaAssetSyncStatus.ACTIVE.value
            existing.archived_at = None
        elif modified_changed:
            existing.sync_status = MediaAssetSyncStatus.CHANGED.value
        elif existing.sync_status == MediaAssetSyncStatus.ERROR.value:
            existing.sync_status = MediaAssetSyncStatus.ACTIVE.value
        if item.folder_meta is not None and existing.drive_meta_json != item.folder_meta:
            existing.drive_meta_json = item.folder_meta
        if changed:
            existing.updated_at = datetime.now(UTC)
        elif existing.sync_status == MediaAssetSyncStatus.CHANGED.value:
            existing.sync_status = MediaAssetSyncStatus.ACTIVE.value


def upsert_project_drive_mapping(
    db: Session,
    *,
    project_id: UUID,
    drive_folder_id: str,
    drive_sync_enabled: bool = True,
    provider: GoogleDriveProviderProtocol,
) -> ProjectDriveMapping:
    """Create or update mapping after validating folder is under approved root."""
    folder_id = drive_folder_id.strip()
    if not folder_id:
        raise ValueError("drive_folder_id is required")

    if not provider.is_descendant_of_root(folder_id):
        raise ValueError(
            "drive_folder_id must be a descendant of GOOGLE_DRIVE_ROOT_FOLDER_ID"
        )

    # Reject if another active project already owns this folder
    conflict = db.scalar(
        select(ProjectDriveMapping).where(
            ProjectDriveMapping.drive_folder_id == folder_id,
            ProjectDriveMapping.archived_at.is_(None),
            ProjectDriveMapping.project_id != project_id,
        )
    )
    if conflict is not None:
        raise ValueError("drive_folder_id is already mapped to another project")

    mapping = db.scalar(
        select(ProjectDriveMapping).where(ProjectDriveMapping.project_id == project_id)
    )
    if mapping is None:
        mapping = ProjectDriveMapping(
            id=uuid4(),
            project_id=project_id,
            drive_folder_id=folder_id,
            drive_sync_enabled=drive_sync_enabled,
        )
        db.add(mapping)
    else:
        mapping.drive_folder_id = folder_id
        mapping.drive_sync_enabled = drive_sync_enabled
        mapping.archived_at = None
    db.flush()
    return mapping
