"""Sprint 11A2 — Documents Workspace Completion tests."""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import Permission, Role, RolePermission

pytestmark = pytest.mark.usefixtures("client")


def _login(auth_client: TestClient, email: str = "admin@example.com") -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _grant(db: Session, *, resource: str, action: str, role_code: str = "super_admin") -> None:
    perm = db.query(Permission).filter_by(resource=resource, action=action).first()
    if perm is None:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        db.flush()
    role = db.query(Role).filter_by(code=role_code).first()
    assert role is not None
    existing = (
        db.query(RolePermission)
        .filter_by(role_id=role.id, permission_id=perm.id)
        .first()
    )
    if existing is None:
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()


def _ensure_workspace_perms(auth_client: TestClient) -> None:
    from investhome_api.db.session import get_db
    from investhome_api.main import app

    db: Session = next(app.dependency_overrides[get_db]())
    for action in (
        "view",
        "create",
        "update",
        "archive",
        "delete",
        "download",
        "export",
        "view_confidential",
        "view_highly_confidential",
    ):
        _grant(db, resource="documents", action=action)


def _upload(client: TestClient, filename: str, content: bytes, **form: str) -> dict:
    files = {"files": (filename, io.BytesIO(content), "text/plain")}
    response = client.post("/documents/upload", files=files, data=form)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["results"][0]["success"] is True
    return payload["results"][0]["document"]


def test_detail_includes_workspace_fields(client: TestClient) -> None:
    doc = _upload(
        client,
        "detail.txt",
        b"detail body",
        folder="legal",
        tags="audit,q3",
        description="detail description",
        notes="detail notes",
        title="Detail Doc",
    )
    detail = client.get(f"/documents/{doc['id']}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["title"] == "Detail Doc"
    assert payload["folder"] == "legal"
    assert payload["tags"] == "audit,q3"
    assert payload["description"] == "detail description"
    assert payload["notes"] == "detail notes"
    assert payload["owner_user_id"] is not None
    assert payload["version_number"] == 1
    assert "download_count" in payload
    assert "preview_count" in payload


def test_preview_increments_and_download_logs(client: TestClient) -> None:
    doc = _upload(client, "preview-count.txt", b"preview count")
    preview = client.get(f"/documents/{doc['id']}/preview")
    assert preview.status_code == 200
    after_preview = client.get(f"/documents/{doc['id']}").json()
    assert after_preview["preview_count"] >= 1

    download = client.get(f"/documents/{doc['id']}/download")
    assert download.status_code == 200
    after_download = client.get(f"/documents/{doc['id']}").json()
    assert after_download["download_count"] >= 1

    activity = client.get(f"/activity/entity/document/{doc['id']}")
    keys = {item.get("description_key") for item in activity.json().get("items", [])}
    assert "activity.document.downloaded" in keys


def test_relations_calendar_and_financial(client: TestClient) -> None:
    doc = _upload(client, "relations.txt", b"relations")
    calendar_id = str(uuid4())
    finance_id = str(uuid4())
    assert (
        client.post(
            f"/documents/{doc['id']}/links",
            json={"entity_type": "calendar_event", "entity_id": calendar_id},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/documents/{doc['id']}/links",
            json={"entity_type": "financial_record", "entity_id": finance_id},
        ).status_code
        == 201
    )
    detail = client.get(f"/documents/{doc['id']}").json()
    types = {link["entity_type"] for link in detail["links"]}
    assert "calendar_event" in types
    assert "financial_record" in types

    by_module = client.get("/documents", params={"related_module": "calendar_event"})
    assert by_module.status_code == 200
    assert any(item["id"] == doc["id"] for item in by_module.json()["items"])


def test_search_owner_description_and_filters(client: TestClient) -> None:
    doc = _upload(
        client,
        "search-owner.txt",
        b"search body",
        title="Owner Search Target",
        description="unique-desc-token-11a2",
        folder="finance",
        tags="budget",
    )
    by_desc = client.get("/documents", params={"search": "unique-desc-token-11a2"})
    assert any(item["id"] == doc["id"] for item in by_desc.json()["items"])

    by_tag = client.get("/documents", params={"tags": "budget"})
    assert any(item["id"] == doc["id"] for item in by_tag.json()["items"])

    by_folder = client.get("/documents", params={"folder": "finance"})
    assert any(item["id"] == doc["id"] for item in by_folder.json()["items"])

    by_kind = client.get("/documents", params={"file_kind": "text"})
    assert any(item["id"] == doc["id"] for item in by_kind.json()["items"])

    by_module = client.get("/documents", params={"related_module": "project"})
    assert by_module.status_code == 200

    created_from = doc["created_at"][:10]
    by_date = client.get("/documents", params={"created_from": created_from})
    assert by_date.status_code == 200
    assert any(item["id"] == doc["id"] for item in by_date.json()["items"])


def test_version_history_and_restore(client: TestClient) -> None:
    doc = _upload(client, "version-base.txt", b"version one")
    v2 = client.post(
        f"/documents/{doc['id']}/versions",
        files={"file": ("version-two.txt", io.BytesIO(b"version two"), "text/plain")},
        data={"version_notes": "second"},
    )
    assert v2.status_code == 201, v2.text
    latest = v2.json()
    assert latest["version_number"] == 2
    assert latest["is_latest_version"] is True

    versions = client.get(f"/documents/{latest['id']}/versions")
    assert versions.status_code == 200
    items = versions.json()["items"]
    assert len(items) >= 2
    previous = next(item for item in items if item["version_number"] == 1)

    restored = client.post(f"/documents/{latest['id']}/versions/{previous['id']}/restore")
    assert restored.status_code == 201, restored.text
    payload = restored.json()
    assert payload["version_number"] == 3
    assert payload["is_latest_version"] is True
    assert payload["original_file_name"] == previous["original_file_name"]

    download = client.get(f"/documents/{payload['id']}/download")
    assert download.status_code == 200
    assert download.content == b"version one"

    activity = client.get(f"/activity/entity/document/{payload['id']}")
    keys = {item.get("description_key") for item in activity.json().get("items", [])}
    assert "activity.document.version_restored" in keys


def test_moved_and_deleted_activity(client: TestClient) -> None:
    doc = _upload(client, "move-me.txt", b"move", folder="general", title="Move Me")
    moved = client.patch(f"/documents/{doc['id']}", json={"folder": "contracts"})
    assert moved.status_code == 200
    assert moved.json()["folder"] == "contracts"

    activity = client.get(f"/activity/entity/document/{doc['id']}")
    keys = {item.get("description_key") for item in activity.json().get("items", [])}
    assert "activity.document.moved" in keys

    deleted = client.delete(f"/documents/{doc['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["archived_at"] is not None
    activity2 = client.get(f"/activity/entity/document/{doc['id']}")
    keys2 = {item.get("description_key") for item in activity2.json().get("items", [])}
    assert "activity.document.deleted" in keys2


def test_storage_summary_honest_metrics(client: TestClient) -> None:
    doc = _upload(client, "storage.txt", b"x" * 2048, folder="general")
    overview = client.get("/documents/overview")
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["total"]["available"] is True
    assert payload["total"]["value"] >= 1
    assert payload["storage_used_bytes"]["available"] is True
    assert payload["storage_used_bytes"]["value"] >= 2048
    assert payload["recent_uploads"]["available"] is True
    assert isinstance(payload["largest_files"], list)
    assert any(item["id"] == doc["id"] for item in payload["largest_files"]) or payload["largest_files"]
    assert isinstance(payload["documents_by_type"], list)
    # Most viewed is unavailable until preview/download counters exist
    if not payload["most_viewed"]["available"]:
        assert payload["most_viewed"]["reason"] in {"no_view_data", "permission_restricted"}
    client.get(f"/documents/{doc['id']}/preview")
    overview2 = client.get("/documents/overview").json()
    assert overview2["most_viewed"]["available"] is True
    assert len(overview2["most_viewed_files"]) >= 1


def test_private_visibility_and_permissions(auth_client: TestClient) -> None:
    _ensure_workspace_perms(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": ("private-11a2.txt", io.BytesIO(b"secret"), "text/plain")}
    upload = auth_client.post(
        "/documents/upload",
        files=files,
        data={"visibility": "private", "title": "Private 11A2"},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["results"][0]["document"]["id"]

    _login(auth_client, "sales@example.com")
    listed = auth_client.get("/documents")
    assert listed.status_code == 200
    assert all(item["id"] != doc_id for item in listed.json()["items"])
    assert auth_client.get(f"/documents/{doc_id}").status_code == 404


def test_soft_delete_preserves_links(client: TestClient) -> None:
    doc = _upload(client, "soft-link.txt", b"soft")
    entity_id = str(uuid4())
    linked = client.post(
        f"/documents/{doc['id']}/links",
        json={"entity_type": "task", "entity_id": entity_id},
    )
    assert linked.status_code == 201
    deleted = client.delete(f"/documents/{doc['id']}")
    assert deleted.status_code == 200
    payload = deleted.json()
    assert payload["archived_at"] is not None
    assert any(link["entity_id"] == entity_id for link in payload["links"])
    # Soft-deleted docs stay out of the default list
    listed = client.get("/documents")
    assert all(item["id"] != doc["id"] for item in listed.json()["items"])
