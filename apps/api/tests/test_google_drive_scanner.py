"""Google Drive Asset Scanner acceptance tests (mocked Drive API)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.models.project_drive import ProjectDriveMapping
from investhome_api.services.google_drive.errors import GoogleDriveApiError
from investhome_api.services.google_drive.provider import DriveFileMeta
from investhome_api.services.google_drive.scanner import (
    DriveAssetScanner,
    upsert_project_drive_mapping,
)

ROOT_ID = "root-folder"
PROJECT_FOLDER = "project-folder-1"


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
) -> DriveFileMeta:
    return DriveFileMeta(
        id=file_id,
        name=name,
        mime_type="application/vnd.google-apps.folder" if is_folder else mime,
        size=None if is_folder else size,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=modified or datetime(2024, 6, 1, tzinfo=UTC),
        md5_checksum=None if is_folder else md5,
        parent_ids=(parent,),
        web_view_link=f"https://drive.example/{file_id}",
        thumbnail_link=None if is_folder else f"https://thumb.example/{file_id}",
    )


class FakeDriveProvider:
    """In-memory Drive tree for scanner tests."""

    def __init__(
        self,
        *,
        root_id: str = ROOT_ID,
        children: dict[str, list[DriveFileMeta]] | None = None,
        files: dict[str, DriveFileMeta] | None = None,
        downloads: dict[str, bytes] | None = None,
        fail_list: bool = False,
        page_size_force: int | None = None,
    ) -> None:
        self._root_id = root_id
        self.children: dict[str, list[DriveFileMeta]] = children or {}
        self.files: dict[str, DriveFileMeta] = files or {}
        self.downloads: dict[str, bytes] = downloads or {}
        self.fail_list = fail_list
        self.page_size_force = page_size_force
        self.list_calls = 0
        # Ensure file map includes all children
        for items in self.children.values():
            for item in items:
                self.files.setdefault(item.id, item)
        self.files.setdefault(root_id, _meta(root_id, "InvestHome Root", parent="", is_folder=True))

    @property
    def root_folder_id(self) -> str:
        return self._root_id

    def get_file(self, file_id: str) -> DriveFileMeta:
        if file_id not in self.files:
            # Build ancestry for root validation
            if file_id == self._root_id:
                return _meta(file_id, "root", parent="", is_folder=True)
            raise GoogleDriveApiError(f"not found: {file_id}", code="drive_not_found")
        return self.files[file_id]

    def list_children(self, folder_id: str, *, page_size: int = 100) -> Iterator[DriveFileMeta]:
        self.list_calls += 1
        if self.fail_list:
            raise GoogleDriveApiError("Drive API unavailable", code="drive_api_error")
        items = list(self.children.get(folder_id, []))
        # Simulate pagination chunking when page_size_force set
        chunk = self.page_size_force or page_size
        for i in range(0, len(items), chunk):
            yield from items[i : i + chunk]

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


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


def _create_project(db: Session) -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"PRJ-DRV-{uuid4().hex[:8]}",
        project_name="Drive Sync Project",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def _map_project(db: Session, project: Project, folder_id: str = PROJECT_FOLDER) -> ProjectDriveMapping:
    mapping = ProjectDriveMapping(
        id=uuid4(),
        project_id=project.id,
        drive_folder_id=folder_id,
        drive_sync_enabled=True,
    )
    db.add(mapping)
    db.flush()
    return mapping


def _standard_tree(
    *,
    file_id: str = "file-1",
    filename: str = "hero.png",
    parent_cat: str = "02_RENDER",
    cat_folder_id: str = "folder-render",
    modified: datetime | None = None,
    md5: str | None = "checksum-1",
    extra_files: list[DriveFileMeta] | None = None,
) -> FakeDriveProvider:
    cat_folder = _meta(cat_folder_id, parent_cat, parent=PROJECT_FOLDER, is_folder=True)
    media = _meta(
        file_id,
        filename,
        parent=cat_folder_id,
        modified=modified,
        md5=md5,
    )
    children: dict[str, list[DriveFileMeta]] = {
        ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
        PROJECT_FOLDER: [cat_folder],
        cat_folder_id: [media, *(extra_files or [])],
    }
    files = {
        ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
        PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
        cat_folder_id: cat_folder,
        file_id: media,
    }
    for f in extra_files or []:
        files[f.id] = f
    return FakeDriveProvider(children=children, files=files)


@pytest.fixture
def db_session(client) -> Session:
    """Depends on client fixture so SQLite schema exists."""
    return _db()


def test_create_asset_from_drive_file(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = _standard_tree()
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()

    assert summary.created == 1
    assert summary.errors == []
    asset = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one()
    assert asset.id is not None
    assert asset.source_type == MediaAssetSourceType.GOOGLE_DRIVE.value
    assert asset.filename == "hero.png"
    assert asset.folder_category == "02_RENDER"
    assert asset.sync_status == MediaAssetSyncStatus.ACTIVE.value
    assert asset.storage_provider == "google_drive"
    assert asset.storage_key == "gdrive:file-1"
    assert asset.linked_project_id == project.id


def test_same_drive_file_id_no_duplicate(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = _standard_tree()
    DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    first = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one()
    first_id = first.id

    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 0
    assert summary.unchanged == 1
    count = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count()
    assert count == 1
    assert db_session.get(CreativeStudioMediaAsset, first_id) is not None


def test_rename_preserves_asset_id(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = _standard_tree(filename="hero.png")
    DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    asset_id = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one().id

    provider2 = _standard_tree(filename="hero-renamed.png")
    summary = DriveAssetScanner(db_session, provider2, project_id=project.id).sync()
    db_session.commit()
    assert summary.updated == 1
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None
    assert asset.filename == "hero-renamed.png"
    assert asset.external_file_id == "file-1"


def test_move_preserves_asset_id(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    DriveAssetScanner(db_session, _standard_tree(), project_id=project.id).sync()
    db_session.commit()
    asset_id = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one().id

    # Move file into 06_MEDIA
    media_folder = _meta("folder-media", "06_MEDIA", parent=PROJECT_FOLDER, is_folder=True)
    moved = _meta("file-1", "hero.png", parent="folder-media", md5="checksum-1")
    provider = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [media_folder],
            "folder-media": [moved],
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
            "folder-media": media_folder,
            "file-1": moved,
        },
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.updated == 1
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None
    assert asset.external_parent_id == "folder-media"
    assert asset.folder_category == "06_MEDIA"


def test_modified_updates_asset(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    t0 = datetime(2024, 6, 1, tzinfo=UTC)
    DriveAssetScanner(db_session, _standard_tree(modified=t0), project_id=project.id).sync()
    db_session.commit()
    asset_id = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one().id

    t1 = t0 + timedelta(days=3)
    summary = DriveAssetScanner(
        db_session, _standard_tree(modified=t1, md5="checksum-2"), project_id=project.id
    ).sync()
    db_session.commit()
    assert summary.updated == 1
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None
    assert _normalize_dt(asset.external_modified_at) == _normalize_dt(t1)
    assert asset.external_checksum == "checksum-2"
    assert asset.sync_status == MediaAssetSyncStatus.CHANGED.value


def test_missing_marked_not_deleted(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    DriveAssetScanner(db_session, _standard_tree(), project_id=project.id).sync()
    db_session.commit()
    asset_id = db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").one().id

    # Empty project folder — file gone from Drive
    empty = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [],
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
        },
    )
    summary = DriveAssetScanner(db_session, empty, project_id=project.id).sync()
    db_session.commit()
    assert summary.missing == 1
    asset = db_session.get(CreativeStudioMediaAsset, asset_id)
    assert asset is not None  # never hard-deleted
    assert asset.sync_status == MediaAssetSyncStatus.MISSING.value
    assert asset.archived_at is not None


def test_index_false_skips_files(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    meta_file = _meta("meta-1", "metadata.json", parent="folder-render", mime="application/json", md5=None)
    media = _meta("file-1", "hero.png", parent="folder-render")
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
        downloads={"meta-1": b'{"index": false, "custom": "ok"}'},
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 0
    assert summary.skipped >= 1
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count() == 0


def test_archive_folder_no_active_asset(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    archive = _meta("folder-archive", "10_ARCHIVE", parent=PROJECT_FOLDER, is_folder=True)
    old = _meta("file-old", "old.png", parent="folder-archive")
    provider = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [archive],
            "folder-archive": [old],
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
            "folder-archive": archive,
            "file-old": old,
        },
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 0
    assert summary.skipped >= 1
    assert (
        db_session.query(CreativeStudioMediaAsset)
        .filter_by(external_file_id="file-old", sync_status=MediaAssetSyncStatus.ACTIVE.value)
        .count()
        == 0
    )


def test_malformed_metadata_does_not_abort(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    meta_file = _meta("meta-bad", "metadata.json", parent="folder-render", mime="application/json", md5=None)
    media = _meta("file-1", "hero.png", parent="folder-render")
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
            "meta-bad": meta_file,
            "file-1": media,
        },
        downloads={"meta-bad": b"NOT JSON {{"},
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 1
    assert any("Malformed metadata.json" in w for w in summary.warnings)
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count() == 1


def test_dry_run_no_db_writes(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = _standard_tree()
    before = db_session.query(CreativeStudioMediaAsset).count()
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync(dry_run=True)
    db_session.flush()
    assert summary.dry_run is True
    assert summary.created == 1
    assert db_session.query(CreativeStudioMediaAsset).count() == before


def test_cannot_scan_outside_root(db_session: Session) -> None:
    project = _create_project(db_session)
    outside = "outside-folder"
    mapping = ProjectDriveMapping(
        id=uuid4(),
        project_id=project.id,
        drive_folder_id=outside,
        drive_sync_enabled=True,
    )
    db_session.add(mapping)
    db_session.flush()

    provider = FakeDriveProvider(
        children={outside: [_meta("f1", "x.png", parent=outside)]},
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            outside: _meta(outside, "Outside", parent="other-root", is_folder=True),
            "f1": _meta("f1", "x.png", parent=outside),
            "other-root": _meta("other-root", "Other", parent="", is_folder=True),
        },
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    assert summary.created == 0
    assert any(e.code == "outside_root" for e in summary.errors)
    assert db_session.query(CreativeStudioMediaAsset).count() == 0


def test_pagination_lists_all_pages(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    cat = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    files = [_meta(f"file-{i}", f"img-{i}.png", parent="folder-render", md5=f"c{i}") for i in range(5)]
    provider = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [cat],
            "folder-render": files,
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
            "folder-render": cat,
            **{f.id: f for f in files},
        },
        page_size_force=2,
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 5
    assert db_session.query(CreativeStudioMediaAsset).filter_by(linked_project_id=project.id).count() == 5


def test_api_failure_safe(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    provider = FakeDriveProvider(
        children={},
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
        },
        fail_list=True,
    )
    # Seed one upload asset — must remain untouched on Drive failure
    upload = CreativeStudioMediaAsset(
        id=uuid4(),
        filename="local.png",
        content_type="image/png",
        file_size=10,
        storage_provider="local",
        storage_key="creative-studio-media/local.png",
        linked_project_id=project.id,
    )
    db_session.add(upload)
    db_session.flush()

    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    assert summary.created == 0
    assert any(e.code == "drive_api_error" for e in summary.errors)
    still = db_session.get(CreativeStudioMediaAsset, upload.id)
    assert still is not None
    assert still.filename == "local.png"
    assert still.source_type is None


def test_upsert_mapping_rejects_outside_root(db_session: Session) -> None:
    project = _create_project(db_session)
    provider = FakeDriveProvider(
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            "outside": _meta("outside", "X", parent="elsewhere", is_folder=True),
            "elsewhere": _meta("elsewhere", "E", parent="", is_folder=True),
        }
    )
    with pytest.raises(ValueError, match="descendant"):
        upsert_project_drive_mapping(
            db_session,
            project_id=project.id,
            drive_folder_id="outside",
            provider=provider,
        )


def test_checksum_possible_duplicate_no_merge(db_session: Session) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    DriveAssetScanner(db_session, _standard_tree(file_id="file-a", md5="same-hash"), project_id=project.id).sync()
    db_session.commit()

    # Second file same checksum, different id
    cat = _meta("folder-render", "02_RENDER", parent=PROJECT_FOLDER, is_folder=True)
    a = _meta("file-a", "hero.png", parent="folder-render", md5="same-hash")
    b = _meta("file-b", "hero-copy.png", parent="folder-render", md5="same-hash")
    provider = FakeDriveProvider(
        children={
            ROOT_ID: [_meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True)],
            PROJECT_FOLDER: [cat],
            "folder-render": [a, b],
        },
        files={
            ROOT_ID: _meta(ROOT_ID, "Root", parent="", is_folder=True),
            PROJECT_FOLDER: _meta(PROJECT_FOLDER, "My Project", parent=ROOT_ID, is_folder=True),
            "folder-render": cat,
            "file-a": a,
            "file-b": b,
        },
    )
    summary = DriveAssetScanner(db_session, provider, project_id=project.id).sync()
    db_session.commit()
    assert summary.created == 1
    assert len(summary.possible_duplicates) >= 1
    assert db_session.query(CreativeStudioMediaAsset).filter_by(linked_project_id=project.id).count() == 2


def test_sync_endpoint_dry_run(client, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _create_project(db_session)
    _map_project(db_session, project)
    db_session.commit()
    provider = _standard_tree()

    monkeypatch.setattr(
        "investhome_api.api.routes.project_drive.get_google_drive_provider",
        lambda: provider,
    )
    response = client.post(f"/projects/{project.id}/drive/sync?dry_run=true")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is True
    assert body["created"] == 1
    assert db_session.query(CreativeStudioMediaAsset).filter_by(external_file_id="file-1").count() == 0
