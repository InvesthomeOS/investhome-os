"""Sprint 2 — Google Drive incremental sync + background worker acceptance tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from investhome_api.config.settings import Settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.models.project_drive import (
    GLOBAL_DRIVE_CURSOR_KEY,
    DriveSyncStatus,
    GoogleDriveSyncCursor,
    ProjectDriveMapping,
)
from investhome_api.services.google_drive.errors import (
    GoogleDriveApiError,
    GoogleDriveAuthError,
    GoogleDrivePermissionError,
)
from investhome_api.services.google_drive.provider import (
    DriveChange,
    DriveChangesPage,
    DriveFileMeta,
)
from investhome_api.services.google_drive.retry import is_permanent_drive_error, with_retry
from investhome_api.services.google_drive.sync_service import (
    DriveSyncOrchestrator,
    get_drive_status,
    get_or_create_cursor,
    mapping_needs_full_scan,
    try_acquire_sync_lock,
)

ROOT_ID = "root-folder"
PROJECT_FOLDER = "project-folder-1"
PROJECT_FOLDER_B = "project-folder-2"


def _meta(
    file_id: str,
    name: str,
    *,
    mime: str = "image/png",
    parent: str = PROJECT_FOLDER,
    size: int = 100,
    modified: datetime | None = None,
    md5: str | None = "abc123",
    is_folder: bool = False,
    trashed: bool = False,
) -> DriveFileMeta:
    return DriveFileMeta(
        id=file_id,
        name=name,
        mime_type="application/vnd.google-apps.folder" if is_folder else mime,
        size=None if is_folder else size,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=modified or datetime(2024, 6, 1, tzinfo=UTC),
        md5_checksum=None if is_folder else md5,
        parent_ids=(parent,) if parent else (),
        web_view_link=f"https://drive.example/{file_id}",
        thumbnail_link=None if is_folder else f"https://thumb.example/{file_id}",
        trashed=trashed,
    )


class FakeDriveProvider:
    """In-memory Drive + Changes API for Sprint 2 tests."""

    def __init__(
        self,
        *,
        root_id: str = ROOT_ID,
        children: dict[str, list[DriveFileMeta]] | None = None,
        files: dict[str, DriveFileMeta] | None = None,
        downloads: dict[str, bytes] | None = None,
        start_page_token: str = "token-1",
        change_pages: list[DriveChangesPage] | None = None,
        fail_changes_with: Exception | None = None,
        list_changes_calls: int | None = None,
    ) -> None:
        self._root_id = root_id
        self.children: dict[str, list[DriveFileMeta]] = children or {}
        self.files: dict[str, DriveFileMeta] = files or {}
        self.downloads: dict[str, bytes] = downloads or {}
        self._start_page_token = start_page_token
        self._change_pages = list(change_pages or [])
        self._change_page_idx = 0
        self.fail_changes_with = fail_changes_with
        self.list_changes_call_count = 0
        self.get_start_page_token_calls = 0
        for items in self.children.values():
            for item in items:
                self.files.setdefault(item.id, item)
        self.files.setdefault(root_id, _meta(root_id, "InvestHome Root", parent="", is_folder=True))

    @property
    def root_folder_id(self) -> str:
        return self._root_id

    def get_file(self, file_id: str) -> DriveFileMeta:
        if file_id not in self.files:
            raise GoogleDriveApiError(f"not found: {file_id}", code="drive_not_found")
        return self.files[file_id]

    def list_children(self, folder_id: str, *, page_size: int = 100) -> Iterator[DriveFileMeta]:
        yield from self.children.get(folder_id, [])

    def is_descendant_of_root(self, folder_id: str) -> bool:
        if folder_id == self._root_id:
            return True
        current = folder_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            if current == self._root_id:
                return True
            meta = self.files.get(current)
            if meta is None or not meta.parent_ids:
                return False
            current = meta.parent_ids[0]
        return False

    def download_bytes(self, file_id: str, *, max_bytes: int | None = None) -> bytes:
        if file_id not in self.downloads:
            raise GoogleDriveApiError("download missing", code="drive_not_found")
        data = self.downloads[file_id]
        if max_bytes is not None and len(data) > max_bytes:
            raise GoogleDriveApiError("too large", code="drive_download_too_large")
        return data

    def get_start_page_token(self) -> str:
        self.get_start_page_token_calls += 1
        return self._start_page_token

    def list_changes(self, page_token: str, *, page_size: int = 100) -> DriveChangesPage:
        self.list_changes_call_count += 1
        if self.fail_changes_with is not None:
            raise self.fail_changes_with
        if self._change_page_idx >= len(self._change_pages):
            return DriveChangesPage(changes=(), next_page_token=None, new_start_page_token=page_token)
        page = self._change_pages[self._change_page_idx]
        self._change_page_idx += 1
        return page


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


def _create_project(db: Session, name: str = "Drive Sync Project") -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"PRJ-DRV-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def _map_project(
    db: Session,
    project: Project,
    folder_id: str = PROJECT_FOLDER,
    *,
    enabled: bool = True,
) -> ProjectDriveMapping:
    mapping = ProjectDriveMapping(
        id=uuid4(),
        project_id=project.id,
        drive_folder_id=folder_id,
        drive_sync_enabled=enabled,
        force_full_sync=True,
    )
    db.add(mapping)
    db.flush()
    return mapping


def _standard_tree(
    *,
    file_id: str = "file-1",
    filename: str = "hero.png",
    md5: str | None = "checksum-1",
    project_folder: str = PROJECT_FOLDER,
) -> dict[str, Any]:
    cat = _meta("folder-render", "02_RENDER", parent=project_folder, is_folder=True)
    media = _meta(file_id, filename, parent="folder-render", md5=md5)
    children = {
        ROOT_ID: [_meta(project_folder, "My Project", parent=ROOT_ID, is_folder=True)],
        project_folder: [cat],
        "folder-render": [media],
    }
    files = {
        ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
        project_folder: _meta(project_folder, "My Project", parent=ROOT_ID, is_folder=True),
        "folder-render": cat,
        file_id: media,
    }
    return {"children": children, "files": files}


def _settings(**overrides: Any) -> Settings:
    data = {
        "google_drive_sync_enabled": True,
        "google_drive_sync_interval_minutes": 5,
        "google_drive_sync_lock_ttl_minutes": 15,
        "google_drive_sync_max_retries": 2,
        "google_drive_root_folder_id": ROOT_ID,
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


@pytest.fixture
def db_session(client) -> Session:
    return _db()


# --- 21 acceptance cases ---


def test_01_initial_start_page_token_persisted(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    tree = _standard_tree()
    provider = FakeDriveProvider(**tree, start_page_token="start-abc")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()

    cursor = get_or_create_cursor(db_session)
    assert cursor.start_page_token == "start-abc"
    assert provider.get_start_page_token_calls >= 1


def test_02_incremental_fetches_changes_since_token(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    tree = _standard_tree()
    provider = FakeDriveProvider(**tree, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    assert mapping.last_sync_status == DriveSyncStatus.SUCCESS.value

    new_file = _meta("file-2", "new.png", parent="folder-render", md5="c2")
    provider.files[new_file.id] = new_file
    provider.children.setdefault("folder-render", []).append(new_file)
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="file-2", removed=False, file=new_file),),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0

    result = orch.run_background_sync()
    db_session.commit()
    assert result.changes_fetched == 1
    assert result.cursor_advanced is True
    assert get_or_create_cursor(db_session).start_page_token == "tok-2"
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-2").count() == 1


def test_03_token_advances_only_after_success(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    tree = _standard_tree()
    provider = FakeDriveProvider(**tree, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    assert get_or_create_cursor(db_session).start_page_token == "tok-1"

    # Transient failure while applying changes — token must stay
    bad = _meta("file-x", "x.png", parent="folder-render")
    provider.files[bad.id] = bad
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="file-x", removed=False, file=bad),),
            next_page_token=None,
            new_start_page_token="tok-should-not-apply",
        )
    ]
    provider._change_page_idx = 0

    original_upsert = orch._apply_file_changes

    def boom(*args: Any, **kwargs: Any) -> None:
        raise GoogleDriveApiError("503 upstream", code="drive_server_error")

    orch._apply_file_changes = boom  # type: ignore[method-assign]
    result = orch.run_background_sync()
    db_session.commit()
    assert result.cursor_advanced is False
    assert get_or_create_cursor(db_session).start_page_token == "tok-1"
    orch._apply_file_changes = original_upsert  # type: ignore[method-assign]


def test_04_invalid_token_falls_back_to_full_scan(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    tree = _standard_tree()
    provider = FakeDriveProvider(
        **tree,
        start_page_token="fresh-token",
        fail_changes_with=GoogleDriveApiError("gone", code="drive_invalid_page_token"),
    )
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()

    # Mark incremental-eligible then expire token
    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    cursor = get_or_create_cursor(db_session)
    cursor.start_page_token = "expired"
    db_session.flush()

    # After invalid token, provider stop failing so full scan works
    provider.fail_changes_with = GoogleDriveApiError("gone", code="drive_invalid_page_token")
    # First list_changes raises; fallback clears token and reseeds via get_start_page_token
    # Then full scan uses list_children — no list_changes needed
    result = orch.run_background_sync()
    db_session.commit()
    assert any(p.mode == "full" for p in result.projects)
    assert get_or_create_cursor(db_session).start_page_token == "fresh-token"


def test_05_partial_failure_preserves_token(db_session: Session) -> None:
    """Never lose changes: failed project keeps prior cursor."""
    p1 = _create_project(db_session, "P1")
    p2 = _create_project(db_session, "P2")
    m1 = _map_project(db_session, p1, PROJECT_FOLDER)
    m2 = _map_project(db_session, p2, PROJECT_FOLDER_B)

    cat1 = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    cat2 = _meta("folder-render-b", "02_RENDER", parent=PROJECT_FOLDER_B, is_folder=True)
    f1 = _meta("file-1", "a.png", parent="folder-render", md5="a")
    f2 = _meta("file-2", "b.png", parent="folder-render-b", md5="b")
    children = {
        ROOT_ID: [
            _meta(PROJECT_FOLDER, "P1", parent=ROOT_ID, is_folder=True),
            _meta(PROJECT_FOLDER_B, "P2", parent=ROOT_ID, is_folder=True),
        ],
        PROJECT_FOLDER: [cat1],
        PROJECT_FOLDER_B: [cat2],
        "folder-render": [f1],
        "folder-render-b": [f2],
    }
    files = {
        ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
        PROJECT_FOLDER: _meta(PROJECT_FOLDER, "P1", parent=ROOT_ID, is_folder=True),
        PROJECT_FOLDER_B: _meta(PROJECT_FOLDER_B, "P2", parent=ROOT_ID, is_folder=True),
        "folder-render": cat1,
        "folder-render-b": cat2,
        "file-1": f1,
        "file-2": f2,
    }
    provider = FakeDriveProvider(children=children, files=files, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(p1.id, force_full=True)
    orch.sync_project(p2.id, force_full=True)
    db_session.commit()

    for m in (m1, m2):
        m.force_full_sync = False
        m.last_successful_sync_at = datetime.now(UTC)
        m.mapped_folder_id_at_sync = m.drive_folder_id
    get_or_create_cursor(db_session).start_page_token = "tok-1"
    db_session.flush()

    new1 = _meta("file-new-1", "n1.png", parent="folder-render", md5="n1")
    new2 = _meta("file-new-2", "n2.png", parent="folder-render-b", md5="n2")
    provider.files[new1.id] = new1
    provider.files[new2.id] = new2
    provider._change_pages = [
        DriveChangesPage(
            changes=(
                DriveChange(file_id=new1.id, removed=False, file=new1),
                DriveChange(file_id=new2.id, removed=False, file=new2),
            ),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0

    from investhome_api.services.google_drive.sync_service import ProjectSyncResult

    original = DriveSyncOrchestrator._apply_incremental_changes

    def flaky(
        self: DriveSyncOrchestrator,
        mapping: ProjectDriveMapping,
        changes: list,
    ) -> ProjectSyncResult:
        if mapping.project_id == p2.id:
            # Simulate transient failure after lock would have been taken
            mapping.last_sync_status = DriveSyncStatus.FAILED.value
            mapping.last_sync_error = "simulated_transient"
            mapping.sync_started_at = None
            self.db.flush()
            return ProjectSyncResult(
                project_id=str(mapping.project_id),
                mode="incremental",
                status=DriveSyncStatus.FAILED.value,
                error="simulated_transient",
                transient_failure=True,
            )
        return original(self, mapping, changes)

    DriveSyncOrchestrator._apply_incremental_changes = flaky  # type: ignore[method-assign]
    try:
        result = orch.run_background_sync()
        db_session.commit()
    finally:
        DriveSyncOrchestrator._apply_incremental_changes = original  # type: ignore[method-assign]

    assert result.cursor_advanced is False
    assert get_or_create_cursor(db_session).start_page_token == "tok-1"
    by_id = {p.project_id: p for p in result.projects}
    assert by_id[str(p2.id)].transient_failure is True
    assert by_id[str(p2.id)].status == DriveSyncStatus.FAILED.value
    # P1 still processed successfully despite P2 failure
    assert by_id[str(p1.id)].status == DriveSyncStatus.SUCCESS.value, (
        f"p1={by_id.get(str(p1.id))} p2={by_id.get(str(p2.id))}"
    )
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-new-1").count() == 1
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-new-2").count() == 0


def test_06_ignores_changes_outside_root(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    tree = _standard_tree()
    provider = FakeDriveProvider(**tree, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    db_session.flush()

    outside = _meta("outside-file", "x.png", parent="other-root")
    provider.files["other-root"] = _meta("other-root", "Other", parent="", is_folder=True)
    provider.files[outside.id] = outside
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id=outside.id, removed=False, file=outside),),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0
    result = orch.run_background_sync()
    db_session.commit()
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="outside-file").count() == 0
    assert result.cursor_advanced is True


def test_07_only_mapped_project_folders_processed(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    tree = _standard_tree()
    # Unmapped sibling under root
    unmapped = _meta("unmapped-folder", "Unmapped", parent=ROOT_ID, is_folder=True)
    unc = _meta("unmapped-file", "u.png", parent="unmapped-folder", md5="u")
    tree["children"][ROOT_ID].append(unmapped)
    tree["children"]["unmapped-folder"] = [unc]
    tree["files"]["unmapped-folder"] = unmapped
    tree["files"]["unmapped-file"] = unc

    provider = FakeDriveProvider(**tree, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    db_session.flush()

    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id=unc.id, removed=False, file=unc),),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0
    orch.run_background_sync()
    db_session.commit()
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="unmapped-file").count() == 0


def test_08_identity_via_drive_folder_id_mapping(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project, PROJECT_FOLDER)
    assert mapping.drive_folder_id == PROJECT_FOLDER
    status = get_drive_status(db_session, project.id)
    assert status["mapped"] is True
    assert status["drive_folder_id"] == PROJECT_FOLDER


def test_09_persisted_sync_state_fields(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    provider = FakeDriveProvider(**_standard_tree(), start_page_token="tok")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    db_session.refresh(mapping)
    assert mapping.last_drive_sync_at is not None
    assert mapping.last_successful_sync_at is not None
    assert mapping.last_sync_status == DriveSyncStatus.SUCCESS.value
    assert mapping.last_sync_error is None
    assert mapping.mapped_folder_id_at_sync == PROJECT_FOLDER
    assert mapping.force_full_sync is False


def test_10_background_skips_when_globally_disabled(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = FakeDriveProvider(**_standard_tree())
    orch = DriveSyncOrchestrator(
        db_session, provider, settings=_settings(google_drive_sync_enabled=False)
    )
    result = orch.run_background_sync()
    assert result.enabled is False
    assert result.projects == []


def test_11_only_sync_enabled_projects(db_session: Session) -> None:
    enabled = _create_project(db_session, "Enabled")
    disabled = _create_project(db_session, "Disabled")
    _map_project(db_session, enabled, PROJECT_FOLDER, enabled=True)
    _map_project(db_session, disabled, PROJECT_FOLDER_B, enabled=False)

    cat = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    media = _meta("file-1", "hero.png", parent="folder-render")
    children = {
        ROOT_ID: [
            _meta(PROJECT_FOLDER, "E", parent=ROOT_ID, is_folder=True),
            _meta(PROJECT_FOLDER_B, "D", parent=ROOT_ID, is_folder=True),
        ],
        PROJECT_FOLDER: [cat],
        "folder-render": [media],
        PROJECT_FOLDER_B: [],
    }
    files = {
        ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
        PROJECT_FOLDER: _meta(PROJECT_FOLDER, "E", parent=ROOT_ID, is_folder=True),
        PROJECT_FOLDER_B: _meta(PROJECT_FOLDER_B, "D", parent=ROOT_ID, is_folder=True),
        "folder-render": cat,
        "file-1": media,
    }
    provider = FakeDriveProvider(children=children, files=files, start_page_token="t")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    result = orch.run_background_sync()
    db_session.commit()
    assert len(result.projects) == 1
    assert result.projects[0].project_id == str(enabled.id)


def test_12_full_scan_fallback_conditions(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    assert mapping_needs_full_scan(mapping) is True  # first sync / force_full

    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = PROJECT_FOLDER
    assert mapping_needs_full_scan(mapping) is False

    mapping.drive_folder_id = "new-folder"
    assert mapping_needs_full_scan(mapping) is True  # mapping changed

    mapping.drive_folder_id = PROJECT_FOLDER
    mapping.mapped_folder_id_at_sync = None
    assert mapping_needs_full_scan(mapping) is True


def test_13_manual_sync_dry_run_and_force_full(client, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    db_session.commit()
    provider = FakeDriveProvider(**_standard_tree(), start_page_token="tok")

    monkeypatch.setattr(
        "investhome_api.api.routes.project_drive.get_google_drive_provider",
        lambda: provider,
    )
    dry = client.post(f"/projects/{project.id}/drive/sync?dry_run=true")
    assert dry.status_code == 200
    assert dry.json()["dry_run"] is True
    assert db_session.query(CreativeStudioMediaAsset).count() == 0

    full = client.post(f"/projects/{project.id}/drive/sync?force_full=true")
    assert full.status_code == 200, full.text
    assert full.json()["created"] == 1
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count() == 1


def test_14_per_project_lock_skips_when_running(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    mapping.last_sync_status = DriveSyncStatus.RUNNING.value
    mapping.sync_started_at = datetime.now(UTC)
    db_session.flush()

    provider = FakeDriveProvider(**_standard_tree(), start_page_token="tok")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    summary = orch.sync_project(project.id, force_full=True)
    assert any(e.code == "sync_locked" for e in summary.errors)


def test_15_stale_lock_recovered(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    mapping.last_sync_status = DriveSyncStatus.RUNNING.value
    mapping.sync_started_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.flush()

    ok = try_acquire_sync_lock(mapping, lock_ttl=timedelta(minutes=15))
    assert ok is True
    assert mapping.last_sync_status == DriveSyncStatus.RUNNING.value


def test_16_retry_backoff_on_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise GoogleDriveApiError("429 rate", code="drive_rate_limited")
        return "ok"

    sleeps: list[float] = []
    result = with_retry(flaky, max_retries=3, base_delay_seconds=0.01, sleep=sleeps.append)
    assert result == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_17_no_endless_retry_on_auth_error() -> None:
    assert is_permanent_drive_error(GoogleDriveAuthError("bad"))
    assert is_permanent_drive_error(GoogleDrivePermissionError("denied"))

    with pytest.raises(GoogleDriveAuthError):
        with_retry(lambda: (_ for _ in ()).throw(GoogleDriveAuthError("bad")), max_retries=5)


def test_18_one_project_fail_does_not_stop_others(db_session: Session) -> None:
    p1 = _create_project(db_session, "OK")
    p2 = _create_project(db_session, "FAIL")
    _map_project(db_session, p1, PROJECT_FOLDER)
    m2 = _map_project(db_session, p2, PROJECT_FOLDER_B)

    cat1 = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    f1 = _meta("file-1", "a.png", parent="folder-render")
    children = {
        ROOT_ID: [
            _meta(PROJECT_FOLDER, "OK", parent=ROOT_ID, is_folder=True),
            _meta(PROJECT_FOLDER_B, "FAIL", parent=ROOT_ID, is_folder=True),
        ],
        PROJECT_FOLDER: [cat1],
        "folder-render": [f1],
        PROJECT_FOLDER_B: [],
    }
    files = {
        ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
        PROJECT_FOLDER: _meta(PROJECT_FOLDER, "OK", parent=ROOT_ID, is_folder=True),
        PROJECT_FOLDER_B: _meta(PROJECT_FOLDER_B, "FAIL", parent="not-under-root", is_folder=True),
        "not-under-root": _meta("not-under-root", "X", parent="", is_folder=True),
        "folder-render": cat1,
        "file-1": f1,
    }
    # Make p2 outside root so full sync fails permanently without stopping p1
    provider = FakeDriveProvider(children=children, files=files, start_page_token="t")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    result = orch.run_background_sync()
    db_session.commit()
    statuses = {p.project_id: p.status for p in result.projects}
    assert statuses[str(p1.id)] == DriveSyncStatus.SUCCESS.value
    assert statuses[str(p2.id)] == DriveSyncStatus.FAILED.value
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count() == 1
    db_session.refresh(m2)
    assert m2.last_sync_status == DriveSyncStatus.FAILED.value


def test_19_change_types_rename_move_trash_restore(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    tree = _standard_tree(file_id="file-1", filename="hero.png")
    provider = FakeDriveProvider(**tree, start_page_token="tok-1")
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()
    asset_id = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one().id

    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    db_session.flush()

    # Rename + move
    media_folder = _meta("folder-media", "06_MEDIA", parent=PROJECT_FOLDER, is_folder=True)
    moved = _meta("file-1", "hero-renamed.png", parent="folder-media", md5="checksum-1")
    provider.files["folder-media"] = media_folder
    provider.files["file-1"] = moved
    provider.children[PROJECT_FOLDER] = [media_folder]
    provider.children["folder-media"] = [moved]
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="file-1", removed=False, file=moved),),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0
    orch.run_background_sync()
    db_session.commit()
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None
    assert asset.filename == "hero-renamed.png"
    assert asset.folder_category == "06_MEDIA"
    assert asset.external_parent_id == "folder-media"

    # Trash
    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    trashed = _meta("file-1", "hero-renamed.png", parent="folder-media", trashed=True)
    provider.files["file-1"] = trashed
    get_or_create_cursor(db_session).start_page_token = "tok-2"
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="file-1", removed=True, file=trashed),),
            next_page_token=None,
            new_start_page_token="tok-3",
        )
    ]
    provider._change_page_idx = 0
    orch.run_background_sync()
    db_session.commit()
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None  # never hard-delete
    assert asset.sync_status == MediaAssetSyncStatus.MISSING.value
    assert asset.archived_at is not None

    # Restore
    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    restored = _meta("file-1", "hero-renamed.png", parent="folder-media", md5="checksum-1")
    provider.files["file-1"] = restored
    get_or_create_cursor(db_session).start_page_token = "tok-3"
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="file-1", removed=False, file=restored),),
            next_page_token=None,
            new_start_page_token="tok-4",
        )
    ]
    provider._change_page_idx = 0
    orch.run_background_sync()
    db_session.commit()
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None
    assert asset.sync_status == MediaAssetSyncStatus.ACTIVE.value
    assert asset.archived_at is None


def test_20_status_api(client, db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    db_session.add(
        GoogleDriveSyncCursor(
            id=uuid4(), cursor_key=GLOBAL_DRIVE_CURSOR_KEY, start_page_token="tok"
        )
    )
    db_session.commit()
    response = client.get(f"/projects/{project.id}/drive/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mapped"] is True
    assert body["has_change_token"] is True
    assert body["last_sync_status"] == DriveSyncStatus.IDLE.value
    assert "background_sync_enabled" in body


def test_21_metadata_reeval_and_duplicate_warning_no_merge(db_session: Session) -> None:
    project = _create_project(db_session)
    mapping = _map_project(db_session, project)
    meta_file = _meta("meta-1", "metadata.json", parent="folder-render", mime="application/json", md5=None)
    media = _meta("file-1", "hero.png", parent="folder-render", md5="same")
    cat = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    provider = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [cat],
            "folder-render": [meta_file, media],
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
            "folder-render": cat,
            "meta-1": meta_file,
            "file-1": media,
        },
        downloads={"meta-1": b'{"index": true}'},
        start_page_token="tok-1",
    )
    orch = DriveSyncOrchestrator(db_session, provider, settings=_settings())
    orch.sync_project(project.id, force_full=True)
    db_session.commit()

    mapping.force_full_sync = False
    mapping.last_successful_sync_at = datetime.now(UTC)
    mapping.mapped_folder_id_at_sync = mapping.drive_folder_id
    get_or_create_cursor(db_session).start_page_token = "tok-1"

    # metadata.json change triggers folder rewalk; add duplicate checksum file
    dup = _meta("file-2", "copy.png", parent="folder-render", md5="same")
    provider.files[dup.id] = dup
    provider.children["folder-render"] = [meta_file, media, dup]
    provider._change_pages = [
        DriveChangesPage(
            changes=(DriveChange(file_id="meta-1", removed=False, file=meta_file),),
            next_page_token=None,
            new_start_page_token="tok-2",
        )
    ]
    provider._change_page_idx = 0
    result = orch.run_background_sync()
    db_session.commit()
    assert db_session.query(CreativeStudioMediaAsset).filter_by(linked_project_id=project.id).count() == 2
    # possible duplicates reported on full rewalk summary
    proj = next(p for p in result.projects if p.project_id == str(project.id))
    assert proj.summary is not None
    assert len(proj.summary.possible_duplicates) >= 1
