"""Google Drive incremental sync orchestrator — Changes API + full-scan fallback.

Architecture notes
------------------
Google Drive ``changes.list`` page tokens are **global per credential**, not
per folder. We therefore persist one cursor in ``google_drive_sync_cursors`` and
filter changes to ``GOOGLE_DRIVE_ROOT_FOLDER_ID`` + ``project_drive_mappings``.

Per-project sync status / locking lives on ``project_drive_mappings``. The
global cursor advances **only** after a successful incremental batch (no
transient project failures). Permanent project failures are isolated and do
not block other projects or cursor advancement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import Settings, get_settings
from investhome_api.models.project import Project
from investhome_api.models.project_drive import (
    GLOBAL_DRIVE_CURSOR_KEY,
    DriveSyncStatus,
    GoogleDriveSyncCursor,
    ProjectDriveMapping,
)
from investhome_api.services.google_drive.categories import (
    ARCHIVE_CATEGORY,
    METADATA_FILENAME,
    README_FILENAME,
    resolve_folder_category,
)
from investhome_api.services.google_drive.errors import (
    GoogleDriveApiError,
    GoogleDriveAuthError,
    GoogleDriveConfigError,
    GoogleDriveError,
    GoogleDrivePermissionError,
)
from investhome_api.services.google_drive.provider import (
    DriveChange,
    DriveFileMeta,
    GoogleDriveProviderProtocol,
)
from investhome_api.services.google_drive.retry import (
    is_permanent_drive_error,
    is_transient_drive_error,
    with_retry,
)
from investhome_api.models.creative_studio_media import MediaAssetSyncStatus
from investhome_api.services.google_drive.scanner import (
    DriveAssetScanner,
    DriveSyncSummary,
    SyncErrorItem,
    _DiscoveredFile,
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectSyncResult:
    project_id: str
    mode: str  # incremental | full
    skipped: bool = False
    skip_reason: str | None = None
    summary: DriveSyncSummary | None = None
    status: str = DriveSyncStatus.SUCCESS.value
    error: str | None = None
    transient_failure: bool = False


@dataclass
class BackgroundSyncResult:
    enabled: bool
    projects: list[ProjectSyncResult] = field(default_factory=list)
    cursor_advanced: bool = False
    changes_fetched: int = 0
    new_start_page_token_pending: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "cursor_advanced": self.cursor_advanced,
            "changes_fetched": self.changes_fetched,
            "message": self.message,
            "projects": [
                {
                    "project_id": p.project_id,
                    "mode": p.mode,
                    "skipped": p.skipped,
                    "skip_reason": p.skip_reason,
                    "status": p.status,
                    "error": p.error,
                    "summary": p.summary.to_dict() if p.summary else None,
                }
                for p in self.projects
            ],
        }


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_or_create_cursor(db: Session, *, cursor_key: str = GLOBAL_DRIVE_CURSOR_KEY) -> GoogleDriveSyncCursor:
    row = db.scalar(
        select(GoogleDriveSyncCursor).where(GoogleDriveSyncCursor.cursor_key == cursor_key)
    )
    if row is None:
        row = GoogleDriveSyncCursor(id=uuid4(), cursor_key=cursor_key, start_page_token=None)
        db.add(row)
        db.flush()
    return row


def list_enabled_mappings(db: Session) -> list[ProjectDriveMapping]:
    return list(
        db.scalars(
            select(ProjectDriveMapping).where(
                ProjectDriveMapping.archived_at.is_(None),
                ProjectDriveMapping.drive_sync_enabled.is_(True),
            )
        ).all()
    )


def mapping_needs_full_scan(mapping: ProjectDriveMapping) -> bool:
    if mapping.force_full_sync:
        return True
    if mapping.last_successful_sync_at is None:
        return True
    if mapping.mapped_folder_id_at_sync is None:
        return True
    if mapping.mapped_folder_id_at_sync != mapping.drive_folder_id:
        return True
    return False


def try_acquire_sync_lock(
    mapping: ProjectDriveMapping,
    *,
    lock_ttl: timedelta,
    now: datetime | None = None,
) -> bool:
    """Acquire per-project sync lock. Returns False if another sync holds a fresh lock."""
    clock = now or _utcnow()
    if mapping.last_sync_status == DriveSyncStatus.RUNNING.value and mapping.sync_started_at:
        started = _normalize_dt(mapping.sync_started_at)
        if started is not None and clock - started < lock_ttl:
            return False
        logger.warning(
            "drive_sync_stale_lock_recovered",
            extra={
                "project_id": str(mapping.project_id),
                "sync_started_at": mapping.sync_started_at.isoformat()
                if mapping.sync_started_at
                else None,
            },
        )
    mapping.last_sync_status = DriveSyncStatus.RUNNING.value
    mapping.sync_started_at = clock
    mapping.last_sync_error = None
    return True


def release_sync_lock_success(
    mapping: ProjectDriveMapping,
    *,
    now: datetime | None = None,
) -> None:
    clock = now or _utcnow()
    mapping.last_sync_status = DriveSyncStatus.SUCCESS.value
    mapping.last_sync_error = None
    mapping.last_drive_sync_at = clock
    mapping.last_successful_sync_at = clock
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    mapping.force_full_sync = False
    mapping.sync_started_at = None


def release_sync_lock_failure(
    mapping: ProjectDriveMapping,
    *,
    error: str,
    now: datetime | None = None,
) -> None:
    clock = now or _utcnow()
    mapping.last_sync_status = DriveSyncStatus.FAILED.value
    mapping.last_sync_error = error[:4000]
    mapping.last_drive_sync_at = clock
    mapping.sync_started_at = None


class DriveSyncOrchestrator:
    """Coordinates full + incremental Drive → Media Library sync."""

    def __init__(
        self,
        db: Session,
        provider: GoogleDriveProviderProtocol,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.provider = provider
        self.settings = settings or get_settings()
        self._lock_ttl = timedelta(minutes=max(1, self.settings.google_drive_sync_lock_ttl_minutes))
        self._max_retries = max(0, self.settings.google_drive_sync_max_retries)

    def sync_project(
        self,
        project_id: UUID,
        *,
        dry_run: bool = False,
        force_full: bool = False,
    ) -> DriveSyncSummary:
        """Manual / single-project sync (preserves Sprint 1 dry_run semantics)."""
        project = self.db.get(Project, project_id)
        if project is None or project.archived_at is not None:
            summary = DriveSyncSummary(dry_run=dry_run)
            summary.errors.append(
                SyncErrorItem(path="", code="project_not_found", message="Project not found")
            )
            return summary

        mapping = self.db.scalar(
            select(ProjectDriveMapping).where(
                ProjectDriveMapping.project_id == project_id,
                ProjectDriveMapping.archived_at.is_(None),
            )
        )
        if mapping is None:
            summary = DriveSyncSummary(dry_run=dry_run)
            summary.errors.append(
                SyncErrorItem(
                    path="",
                    code="mapping_not_found",
                    message="No active Drive mapping for this project",
                )
            )
            return summary

        if force_full and not dry_run:
            mapping.force_full_sync = True

        if dry_run:
            scanner = DriveAssetScanner(
                self.db,
                self.provider,
                project_id=project.id,
                company_id=project.company_id,
            )
            return scanner.sync(dry_run=True)

        if not try_acquire_sync_lock(mapping, lock_ttl=self._lock_ttl):
            summary = DriveSyncSummary(dry_run=False)
            summary.errors.append(
                SyncErrorItem(
                    path=mapping.drive_folder_id,
                    code="sync_locked",
                    message="Drive sync already running for this project",
                )
            )
            summary.warnings.append("sync_locked")
            return summary

        self.db.flush()
        try:
            # Ensure global start page token exists even for manual full syncs
            self._ensure_start_page_token()
            summary = self._run_full_project_scan(mapping, project)
            if summary.errors and any(
                e.code
                in {
                    "outside_root",
                    "sync_disabled",
                    "drive_auth_error",
                    "drive_permission_denied",
                    "drive_not_configured",
                }
                for e in summary.errors
            ):
                release_sync_lock_failure(
                    mapping,
                    error="; ".join(f"{e.code}: {e.message}" for e in summary.errors),
                )
            else:
                release_sync_lock_success(mapping)
            self.db.flush()
            return summary
        except Exception as exc:  # noqa: BLE001
            release_sync_lock_failure(mapping, error=str(exc))
            self.db.flush()
            raise

    def run_background_sync(self) -> BackgroundSyncResult:
        """ARQ entry: sync all enabled projects (incremental first, full when needed)."""
        if not self.settings.google_drive_sync_enabled:
            logger.info("drive_background_sync_disabled")
            return BackgroundSyncResult(enabled=False, message="GOOGLE_DRIVE_SYNC_ENABLED=false")

        result = BackgroundSyncResult(enabled=True)
        mappings = list_enabled_mappings(self.db)
        if not mappings:
            result.message = "no_enabled_mappings"
            logger.info("drive_background_sync_no_mappings")
            return result

        # Partition: full-scan projects vs incremental-eligible
        full_projects: list[ProjectDriveMapping] = []
        incremental_eligible: list[ProjectDriveMapping] = []
        for mapping in mappings:
            if mapping_needs_full_scan(mapping):
                full_projects.append(mapping)
            else:
                incremental_eligible.append(mapping)

        # Full scans first (also seeds start page token on first ever sync)
        for mapping in full_projects:
            result.projects.append(self._sync_one_project_full(mapping))

        # Incremental for the rest
        if incremental_eligible:
            inc = self._run_incremental_batch(incremental_eligible)
            result.projects.extend(inc["project_results"])
            result.changes_fetched = inc["changes_fetched"]
            result.cursor_advanced = inc["cursor_advanced"]
            result.new_start_page_token_pending = inc.get("pending_token")

        logger.info(
            "drive_background_sync_complete",
            extra={
                "project_count": len(result.projects),
                "changes_fetched": result.changes_fetched,
                "cursor_advanced": result.cursor_advanced,
                "failed": sum(1 for p in result.projects if p.status == DriveSyncStatus.FAILED.value),
                "skipped": sum(1 for p in result.projects if p.skipped),
            },
        )
        return result

    def _ensure_start_page_token(self) -> str | None:
        cursor = get_or_create_cursor(self.db)
        if cursor.start_page_token:
            return cursor.start_page_token

        def _fetch() -> str:
            return self.provider.get_start_page_token()

        try:
            token = with_retry(
                _fetch,
                max_retries=self._max_retries,
                operation="get_start_page_token",
            )
        except GoogleDriveError:
            raise
        cursor.start_page_token = token
        cursor.updated_at = _utcnow()
        self.db.flush()
        logger.info("drive_start_page_token_initialized")
        return token

    def _sync_one_project_full(self, mapping: ProjectDriveMapping) -> ProjectSyncResult:
        project_id = mapping.project_id
        if not try_acquire_sync_lock(mapping, lock_ttl=self._lock_ttl):
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="full",
                skipped=True,
                skip_reason="sync_locked",
                status=DriveSyncStatus.RUNNING.value,
            )
        self.db.flush()
        project = self.db.get(Project, project_id)
        if project is None or project.archived_at is not None:
            release_sync_lock_failure(mapping, error="project_not_found")
            self.db.flush()
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="full",
                status=DriveSyncStatus.FAILED.value,
                error="project_not_found",
            )
        try:
            self._ensure_start_page_token()
            summary = self._run_full_project_scan(mapping, project)
            permanent = any(
                e.code
                in {
                    "outside_root",
                    "sync_disabled",
                    "drive_auth_error",
                    "drive_permission_denied",
                    "drive_not_configured",
                    "mapping_not_found",
                }
                for e in summary.errors
            )
            if permanent:
                err = "; ".join(f"{e.code}: {e.message}" for e in summary.errors)
                release_sync_lock_failure(mapping, error=err)
                self.db.flush()
                return ProjectSyncResult(
                    project_id=str(project_id),
                    mode="full",
                    summary=summary,
                    status=DriveSyncStatus.FAILED.value,
                    error=err,
                    transient_failure=False,
                )
            # Soft errors during upsert still count as success for lock/cursor purposes
            release_sync_lock_success(mapping)
            self.db.flush()
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="full",
                summary=summary,
                status=DriveSyncStatus.SUCCESS.value,
            )
        except Exception as exc:  # noqa: BLE001
            transient = is_transient_drive_error(exc) and not is_permanent_drive_error(exc)
            release_sync_lock_failure(mapping, error=str(exc))
            if transient:
                # Keep force_full so next tick retries full scan; do not clear token
                mapping.force_full_sync = True
            self.db.flush()
            logger.warning(
                "drive_project_full_sync_failed",
                extra={
                    "project_id": str(project_id),
                    "error_type": type(exc).__name__,
                    "transient": transient,
                },
            )
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="full",
                status=DriveSyncStatus.FAILED.value,
                error=str(exc),
                transient_failure=transient,
            )

    def _run_full_project_scan(
        self,
        mapping: ProjectDriveMapping,
        project: Project,
    ) -> DriveSyncSummary:
        scanner = DriveAssetScanner(
            self.db,
            self.provider,
            project_id=project.id,
            company_id=project.company_id,
        )
        return scanner.sync(dry_run=False)

    def _run_incremental_batch(
        self,
        mappings: list[ProjectDriveMapping],
    ) -> dict[str, Any]:
        cursor = get_or_create_cursor(self.db)
        if not cursor.start_page_token:
            # Should not happen after full scans, but recover safely
            for mapping in mappings:
                mapping.force_full_sync = True
            self.db.flush()
            results = [self._sync_one_project_full(m) for m in mappings]
            return {
                "project_results": results,
                "changes_fetched": 0,
                "cursor_advanced": False,
                "pending_token": None,
            }

        folder_to_mapping = {m.drive_folder_id: m for m in mappings}
        project_results: list[ProjectSyncResult] = []
        changes_fetched = 0
        pending_new_token: str | None = None
        page_token = cursor.start_page_token
        all_changes: list[DriveChange] = []

        try:
            while page_token:
                page_token_capture = page_token

                def _list() -> Any:
                    return self.provider.list_changes(page_token_capture)

                page = with_retry(
                    _list,
                    max_retries=self._max_retries,
                    operation="list_changes",
                )
                all_changes.extend(page.changes)
                changes_fetched += len(page.changes)
                if page.new_start_page_token:
                    pending_new_token = page.new_start_page_token
                    break
                page_token = page.next_page_token
                if not page_token:
                    break
        except GoogleDriveApiError as exc:
            if exc.code == "drive_invalid_page_token":
                logger.warning("drive_invalid_page_token_fallback_full")
                cursor.start_page_token = None
                for mapping in mappings:
                    mapping.force_full_sync = True
                self.db.flush()
                # Re-seed token then full-scan
                try:
                    self._ensure_start_page_token()
                except GoogleDriveError as seed_exc:
                    return {
                        "project_results": [
                            ProjectSyncResult(
                                project_id=str(m.project_id),
                                mode="full",
                                status=DriveSyncStatus.FAILED.value,
                                error=str(seed_exc),
                                transient_failure=is_transient_drive_error(seed_exc),
                            )
                            for m in mappings
                        ],
                        "changes_fetched": 0,
                        "cursor_advanced": False,
                        "pending_token": None,
                    }
                results = [self._sync_one_project_full(m) for m in mappings]
                return {
                    "project_results": results,
                    "changes_fetched": 0,
                    "cursor_advanced": False,
                    "pending_token": None,
                }
            raise
        except (GoogleDriveAuthError, GoogleDrivePermissionError, GoogleDriveConfigError) as exc:
            # Permanent credential issues — fail closed without advancing token
            for mapping in mappings:
                mapping.last_sync_status = DriveSyncStatus.FAILED.value
                mapping.last_sync_error = str(exc)[:4000]
                mapping.last_drive_sync_at = _utcnow()
                project_results.append(
                    ProjectSyncResult(
                        project_id=str(mapping.project_id),
                        mode="incremental",
                        status=DriveSyncStatus.FAILED.value,
                        error=str(exc),
                        transient_failure=False,
                    )
                )
            self.db.flush()
            return {
                "project_results": project_results,
                "changes_fetched": changes_fetched,
                "cursor_advanced": False,
                "pending_token": None,
            }

        # Group relevant changes by project folder
        by_project: dict[UUID, list[DriveChange]] = {m.project_id: [] for m in mappings}
        ignored_outside = 0
        for change in all_changes:
            project_folder = self._resolve_project_folder(change, folder_to_mapping)
            if project_folder is None:
                ignored_outside += 1
                continue
            mapping = folder_to_mapping[project_folder]
            by_project[mapping.project_id].append(change)

        if ignored_outside:
            logger.info(
                "drive_changes_ignored_outside_scope",
                extra={"ignored_count": ignored_outside, "fetched": changes_fetched},
            )

        any_transient = False
        for mapping in mappings:
            changes = by_project.get(mapping.project_id, [])
            if not changes:
                project_results.append(
                    ProjectSyncResult(
                        project_id=str(mapping.project_id),
                        mode="incremental",
                        skipped=True,
                        skip_reason="no_relevant_changes",
                        status=mapping.last_sync_status or DriveSyncStatus.IDLE.value,
                    )
                )
                continue
            pr = self._apply_incremental_changes(mapping, changes)
            if pr.transient_failure:
                any_transient = True
            project_results.append(pr)

        cursor_advanced = False
        if pending_new_token and not any_transient:
            # Only advance after successful processing of the whole batch
            cursor.start_page_token = pending_new_token
            cursor.updated_at = _utcnow()
            cursor_advanced = True
            self.db.flush()
            logger.info(
                "drive_change_token_advanced",
                extra={"changes_fetched": changes_fetched},
            )
        elif any_transient:
            logger.warning(
                "drive_change_token_preserved_after_partial_failure",
                extra={"changes_fetched": changes_fetched},
            )

        return {
            "project_results": project_results,
            "changes_fetched": changes_fetched,
            "cursor_advanced": cursor_advanced,
            "pending_token": pending_new_token,
        }

    def _resolve_project_folder(
        self,
        change: DriveChange,
        folder_to_mapping: dict[str, ProjectDriveMapping],
    ) -> str | None:
        """Return mapped project folder id if change is under root + a mapping."""
        start_id: str | None = None
        parents: tuple[str, ...] = ()
        if change.file is not None:
            start_id = change.file.id
            parents = change.file.parent_ids
            # File itself might be the project folder
            if start_id in folder_to_mapping:
                if self._safe_under_root(start_id):
                    return start_id
        else:
            start_id = change.file_id

        # Walk parents from known parents, then climb via get_file
        queue: list[str] = list(parents)
        if start_id and start_id not in queue:
            # For removed files we may only have file_id — try get_file, else asset parent lookup
            queue.append(start_id)

        seen: set[str] = set()
        while queue:
            current = queue.pop(0)
            if not current or current in seen:
                continue
            seen.add(current)
            if current in folder_to_mapping:
                if self._safe_under_root(current):
                    return current
                return None
            # Stop climbing outside approved root
            root = self.provider.root_folder_id
            if current == root:
                return None
            try:
                meta = self.provider.get_file(current)
            except GoogleDriveError:
                continue
            for parent in meta.parent_ids:
                if parent not in seen:
                    queue.append(parent)
        return None

    def _safe_under_root(self, folder_id: str) -> bool:
        try:
            return self.provider.is_descendant_of_root(folder_id)
        except GoogleDriveError:
            return False

    def _apply_incremental_changes(
        self,
        mapping: ProjectDriveMapping,
        changes: list[DriveChange],
    ) -> ProjectSyncResult:
        project_id = mapping.project_id
        if not try_acquire_sync_lock(mapping, lock_ttl=self._lock_ttl):
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="incremental",
                skipped=True,
                skip_reason="sync_locked",
                status=DriveSyncStatus.RUNNING.value,
                transient_failure=True,  # preserve token until we can process
            )
        self.db.flush()

        project = self.db.get(Project, project_id)
        if project is None:
            release_sync_lock_failure(mapping, error="project_not_found")
            self.db.flush()
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="incremental",
                status=DriveSyncStatus.FAILED.value,
                error="project_not_found",
            )

        # Root validation (same as manual sync)
        try:
            if not self.provider.is_descendant_of_root(mapping.drive_folder_id):
                release_sync_lock_failure(mapping, error="outside_root")
                self.db.flush()
                return ProjectSyncResult(
                    project_id=str(project_id),
                    mode="incremental",
                    status=DriveSyncStatus.FAILED.value,
                    error="outside_root",
                )
        except GoogleDriveError as exc:
            transient = is_transient_drive_error(exc)
            release_sync_lock_failure(mapping, error=exc.message)
            self.db.flush()
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="incremental",
                status=DriveSyncStatus.FAILED.value,
                error=exc.message,
                transient_failure=transient,
            )

        scanner = DriveAssetScanner(
            self.db,
            self.provider,
            project_id=project.id,
            company_id=project.company_id,
        )
        summary = DriveSyncSummary(dry_run=False)

        try:
            # Folder / metadata.json changes → scoped re-walk of project (safe, no binary media)
            needs_folder_rewalk = any(
                (c.file is not None and c.file.is_folder)
                or (c.file is not None and c.file.name.lower() == METADATA_FILENAME.lower())
                for c in changes
            )
            if needs_folder_rewalk:
                summary = scanner.sync(dry_run=False)
            else:
                self._apply_file_changes(scanner, mapping, changes, summary)

            release_sync_lock_success(mapping)
            self.db.flush()
            logger.info(
                "drive_incremental_project_complete",
                extra={
                    "project_id": str(project_id),
                    "change_count": len(changes),
                    "assets_created": summary.created,
                    "assets_updated": summary.updated,
                    "assets_missing": summary.missing,
                },
            )
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="incremental",
                summary=summary,
                status=DriveSyncStatus.SUCCESS.value,
            )
        except Exception as exc:  # noqa: BLE001
            transient = is_transient_drive_error(exc) and not is_permanent_drive_error(exc)
            release_sync_lock_failure(mapping, error=str(exc))
            self.db.flush()
            logger.warning(
                "drive_incremental_project_failed",
                extra={
                    "project_id": str(project_id),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                    "transient": transient,
                },
            )
            return ProjectSyncResult(
                project_id=str(project_id),
                mode="incremental",
                summary=summary,
                status=DriveSyncStatus.FAILED.value,
                error=str(exc),
                transient_failure=transient,
            )

    def _apply_file_changes(
        self,
        scanner: DriveAssetScanner,
        mapping: ProjectDriveMapping,
        changes: list[DriveChange],
        summary: DriveSyncSummary,
    ) -> None:
        existing = scanner._load_existing_drive_assets()
        checksum_index = scanner._build_checksum_index(existing)

        for change in changes:
            if change.removed or (change.file is not None and change.file.trashed):
                asset = existing.get(change.file_id)
                if asset is None:
                    summary.unchanged += 1
                    continue
                if asset.sync_status == MediaAssetSyncStatus.MISSING.value:
                    summary.unchanged += 1
                    continue
                summary.missing += 1
                asset.sync_status = MediaAssetSyncStatus.MISSING.value
                if asset.archived_at is None:
                    asset.archived_at = _utcnow()
                asset.updated_at = _utcnow()
                continue

            meta = change.file
            if meta is None:
                try:
                    meta = self.provider.get_file(change.file_id)
                except GoogleDriveError as exc:
                    summary.errors.append(
                        SyncErrorItem(path=change.file_id, code=exc.code, message=exc.message)
                    )
                    continue

            if meta.is_folder:
                continue

            name_lower = meta.name.lower()
            if name_lower in {METADATA_FILENAME.lower(), README_FILENAME.lower()}:
                summary.skipped += 1
                continue

            parent_id = meta.parent_ids[0] if meta.parent_ids else mapping.drive_folder_id
            category, under_archive, folder_meta, indexable = self._resolve_context(
                mapping.drive_folder_id, parent_id
            )
            if under_archive or category == ARCHIVE_CATEGORY or not indexable:
                # Archive / non-indexable: if we already track it, mark missing/archive
                asset = existing.get(meta.id)
                if asset is not None and asset.sync_status != MediaAssetSyncStatus.MISSING.value:
                    summary.missing += 1
                    asset.sync_status = MediaAssetSyncStatus.MISSING.value
                    if asset.archived_at is None:
                        asset.archived_at = _utcnow()
                else:
                    summary.skipped += 1
                continue

            item = _DiscoveredFile(
                meta=meta,
                folder_category=category,
                parent_folder_id=parent_id,
                indexable=indexable,
                folder_meta=folder_meta,
            )
            summary.scanned += 1
            try:
                scanner._upsert_discovered(
                    item,
                    existing_by_file_id=existing,
                    checksum_index=checksum_index,
                    summary=summary,
                    dry_run=False,
                )
            except Exception as exc:  # noqa: BLE001
                summary.errors.append(
                    SyncErrorItem(path=meta.name, code="upsert_error", message=str(exc))
                )

        self.db.flush()

    def _resolve_context(
        self,
        project_folder_id: str,
        parent_folder_id: str,
    ) -> tuple[str | None, bool, dict[str, Any] | None, bool]:
        """Walk from parent up to project folder to resolve category / archive / metadata."""
        category: str | None = None
        under_archive = False
        folder_meta: dict[str, Any] | None = None
        indexable = True

        current = parent_folder_id
        seen: set[str] = set()
        chain: list[str] = []
        while current and current not in seen:
            seen.add(current)
            chain.append(current)
            if current == project_folder_id:
                break
            try:
                meta = self.provider.get_file(current)
            except GoogleDriveError:
                break
            if not meta.parent_ids:
                break
            current = meta.parent_ids[0]

        # Resolve category from folder names (closest named category wins via walk order)
        for folder_id in reversed(chain):
            if folder_id == project_folder_id:
                continue
            try:
                meta = self.provider.get_file(folder_id)
            except GoogleDriveError:
                continue
            resolved = resolve_folder_category(meta.name)
            if resolved:
                category = resolved
                if resolved == ARCHIVE_CATEGORY:
                    under_archive = True

        # Parse metadata.json in the immediate parent (best-effort)
        try:
            for child in self.provider.list_children(parent_folder_id):
                if child.is_folder:
                    continue
                if child.name.lower() == METADATA_FILENAME.lower():
                    # Reuse scanner parse via temporary instance methods
                    raw = self.provider.download_bytes(child.id, max_bytes=256_000)
                    import json

                    data = json.loads(raw.decode("utf-8"))
                    if isinstance(data, dict):
                        folder_meta = data
                        if data.get("index") is False:
                            indexable = False
                    break
        except Exception:  # noqa: BLE001 — metadata is advisory
            pass

        return category, under_archive, folder_meta, indexable


def get_drive_status(db: Session, project_id: UUID) -> dict[str, Any]:
    """Status payload for GET /projects/{id}/drive/status."""
    mapping = db.scalar(
        select(ProjectDriveMapping).where(
            ProjectDriveMapping.project_id == project_id,
            ProjectDriveMapping.archived_at.is_(None),
        )
    )
    cursor = db.scalar(
        select(GoogleDriveSyncCursor).where(
            GoogleDriveSyncCursor.cursor_key == GLOBAL_DRIVE_CURSOR_KEY
        )
    )
    settings = get_settings()
    if mapping is None:
        return {
            "project_id": str(project_id),
            "mapped": False,
            "drive_sync_enabled": False,
            "last_sync_status": DriveSyncStatus.IDLE.value,
            "last_drive_sync_at": None,
            "last_successful_sync_at": None,
            "last_sync_error": None,
            "force_full_sync": False,
            "has_change_token": bool(cursor and cursor.start_page_token),
            "background_sync_enabled": settings.google_drive_sync_enabled,
            "background_sync_interval_minutes": settings.google_drive_sync_interval_minutes,
        }
    return {
        "project_id": str(project_id),
        "mapped": True,
        "drive_folder_id": mapping.drive_folder_id,
        "drive_sync_enabled": mapping.drive_sync_enabled,
        "last_sync_status": mapping.last_sync_status,
        "last_drive_sync_at": mapping.last_drive_sync_at,
        "last_successful_sync_at": mapping.last_successful_sync_at,
        "last_sync_error": mapping.last_sync_error,
        "force_full_sync": mapping.force_full_sync,
        "sync_started_at": mapping.sync_started_at,
        "has_change_token": bool(cursor and cursor.start_page_token),
        "background_sync_enabled": settings.google_drive_sync_enabled,
        "background_sync_interval_minutes": settings.google_drive_sync_interval_minutes,
    }
