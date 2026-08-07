"""Creative Studio Media Library foundation API tests."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.storage.factory import get_storage_provider


def _login(client: TestClient, email: str = "admin@example.com") -> None:
    response = client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _grant_cs_permissions(auth_client: TestClient, *, actions: list[str] | None = None) -> None:
    db: Session = next(app.dependency_overrides[get_db]())
    grant_actions = actions or ["view", "create", "update", "archive"]
    for action in grant_actions:
        perm = db.query(Permission).filter_by(resource="creative_studio", action=action).first()
        if perm is None:
            perm = Permission(resource="creative_studio", action=action)
            db.add(perm)
            db.flush()
        role = db.query(Role).filter_by(code="cs_media_editor").first()
        if role is None:
            role = Role(name="CS Media Editor", code="cs_media_editor", is_system_role=False)
            db.add(role)
            db.flush()
        existing = (
            db.query(RolePermission)
            .filter_by(role_id=role.id, permission_id=perm.id)
            .first()
        )
        if existing is None:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = db.query(User).filter_by(email="csmedia@example.com").first()
    if user is None:
        user = User(
            full_name="CS Media Editor",
            email="csmedia@example.com",
            hashed_password=hash_password("Demo123!"),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        role = db.query(Role).filter_by(code="cs_media_editor").first()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _png_bytes(width: int = 32, height: int = 24, color: tuple[int, int, int] = (20, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _upload(
    client: TestClient,
    *,
    filename: str = "hero.png",
    content: bytes | None = None,
    content_type: str = "image/png",
    tags: str | None = "hero,landing",
    folder_id: str | None = None,
) -> dict:
    payload = content if content is not None else _png_bytes()
    files = {"file": (filename, io.BytesIO(payload), content_type)}
    data: dict[str, str] = {}
    if tags is not None:
        data["tags"] = tags
    if folder_id is not None:
        data["folder_id"] = folder_id
    response = client.post("/creative-studio/media/upload", files=files, data=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_creates_asset_with_metadata(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "media-storage"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()

    asset = _upload(client, filename="banner.png", tags="banner,campaign")
    assert asset["id"]
    assert asset["filename"] == "banner.png"
    assert asset["content_type"] == "image/png"
    assert asset["file_size"] > 0
    assert asset["width"] == 32
    assert asset["height"] == 24
    assert asset["tags"] == ["banner", "campaign"]
    assert asset["archived_at"] is None
    assert asset["thumbnail_storage_key"] is None
    assert asset["thumbnail_pending"] is True
    assert asset["url"] == f"/creative-studio/media/assets/{asset['id']}/content"
    assert asset["storage_key"].startswith("creative-studio-media/")

    storage = get_storage_provider()
    assert storage.exists(asset["storage_key"])

    content = client.get(asset["url"])
    assert content.status_code == 200
    assert content.headers["content-type"].startswith("image/png")


def test_list_get_archive_and_search(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "media-storage"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()

    folder_resp = client.post("/creative-studio/media/folders", json={"name": "Campaign Art"})
    assert folder_resp.status_code == 201, folder_resp.text
    folder_id = folder_resp.json()["id"]

    asset_a = _upload(client, filename="sunset-villa.png", tags="villa,sunset", folder_id=folder_id)
    asset_b = _upload(client, filename="office-lobby.png", tags="office", folder_id=folder_id)

    listed = client.get("/creative-studio/media/assets", params={"folder_id": folder_id})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 2
    ids = {item["id"] for item in body["items"]}
    assert asset_a["id"] in ids
    assert asset_b["id"] in ids

    by_tag = client.get("/creative-studio/media/assets", params={"tag": "sunset"})
    assert by_tag.status_code == 200
    assert any(item["id"] == asset_a["id"] for item in by_tag.json()["items"])

    detail = client.get(f"/creative-studio/media/assets/{asset_a['id']}")
    assert detail.status_code == 200
    assert detail.json()["filename"] == "sunset-villa.png"

    search = client.get("/creative-studio/media/search", params={"q": "villa"})
    assert search.status_code == 200
    assert any(item["id"] == asset_a["id"] for item in search.json()["items"])

    search_tag = client.get("/creative-studio/media/search", params={"q": "office"})
    assert search_tag.status_code == 200
    assert any(item["id"] == asset_b["id"] for item in search_tag.json()["items"])

    deleted = client.delete(f"/creative-studio/media/assets/{asset_a['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["archived_at"] is not None

    listed_after = client.get("/creative-studio/media/assets", params={"folder_id": folder_id})
    assert listed_after.status_code == 200
    assert all(item["id"] != asset_a["id"] for item in listed_after.json()["items"])

    with_archived = client.get(
        "/creative-studio/media/assets",
        params={"folder_id": folder_id, "include_archived": "true"},
    )
    assert with_archived.status_code == 200
    assert any(item["id"] == asset_a["id"] for item in with_archived.json()["items"])


def test_update_tags(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "media-storage"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()

    asset = _upload(client, tags="old")
    patched = client.patch(
        f"/creative-studio/media/assets/{asset['id']}/tags",
        json={"tags": ["new", "featured"]},
    )
    assert patched.status_code == 200
    assert patched.json()["tags"] == ["new", "featured"]


def test_unauthenticated_rejected(auth_client: TestClient) -> None:
    response = auth_client.get("/creative-studio/media/assets")
    assert response.status_code == 401

    upload = auth_client.post(
        "/creative-studio/media/upload",
        files={"file": ("x.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert upload.status_code == 401


def test_permission_failures(auth_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "media-storage"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()

    _grant_cs_permissions(auth_client, actions=["view", "create"])
    _login(auth_client, "admin@example.com")
    asset = _upload(auth_client, filename=f"perm-{uuid4().hex[:6]}.png")

    _login(auth_client, "readonly@example.com")
    denied = auth_client.get("/creative-studio/media/assets")
    assert denied.status_code == 403

    _login(auth_client, "csmedia@example.com")
    allowed = auth_client.get("/creative-studio/media/assets")
    assert allowed.status_code == 200

    archive_denied = auth_client.delete(f"/creative-studio/media/assets/{asset['id']}")
    assert archive_denied.status_code == 403

    _grant_cs_permissions(auth_client, actions=["view", "create", "archive"])
    _login(auth_client, "csmedia@example.com")
    archive_ok = auth_client.delete(f"/creative-studio/media/assets/{asset['id']}")
    assert archive_ok.status_code == 200
