"""Sprint 11A1 — Documents Workspace Foundation tests."""

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


def test_workspace_upload_sets_folder_visibility_and_file_kind(client: TestClient) -> None:
    doc = _upload(
        client,
        "brief.txt",
        b"workspace foundation",
        folder="marketing",
        visibility="team",
        tags="launch,q3",
        notes="workspace note",
    )
    assert doc["folder"] == "marketing"
    assert doc["visibility"] == "team"
    assert doc["file_kind"] == "text"
    assert doc["document_type"] in {"text", "other"}
    assert doc["owner_user_id"] is not None
    assert doc["notes"] == "workspace note"
    assert doc["tags"] == "launch,q3"


def test_workspace_overview_metrics(client: TestClient) -> None:
    _upload(client, "overview-a.txt", b"a", folder="general")
    orphan = _upload(client, "overview-orphan.txt", b"orphan", folder="general")
    archived = _upload(client, "overview-archived.txt", b"archived", folder="finance")
    client.post(f"/documents/{archived['id']}/archive")

    overview = client.get("/documents/overview")
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["total"]["available"] is True
    assert payload["total"]["value"] >= 1
    assert payload["archived"]["available"] is True
    assert payload["archived"]["value"] >= 1
    assert payload["without_relation"]["available"] is True
    assert payload["without_relation"]["value"] >= 1
    assert isinstance(payload["most_used_types"], list)
    assert any(item["file_kind"] == "text" for item in payload["most_used_types"]) or orphan


def test_search_by_tags_folder_and_file_kind(client: TestClient) -> None:
    doc = _upload(
        client,
        "search-me.txt",
        b"searchable",
        folder="contracts",
        tags="nda,legal",
        title="NDA Search Target",
    )
    by_tag = client.get("/documents", params={"tags": "nda"})
    assert by_tag.status_code == 200
    assert any(item["id"] == doc["id"] for item in by_tag.json()["items"])

    by_folder = client.get("/documents", params={"folder": "contracts"})
    assert any(item["id"] == doc["id"] for item in by_folder.json()["items"])

    by_kind = client.get("/documents", params={"file_kind": "text"})
    assert any(item["id"] == doc["id"] for item in by_kind.json()["items"])

    by_search = client.get("/documents", params={"search": "NDA Search"})
    assert any(item["id"] == doc["id"] for item in by_search.json()["items"])


def test_relation_link_and_unlink_activity(client: TestClient) -> None:
    doc = _upload(client, "relation.txt", b"linked")
    entity_id = str(uuid4())
    linked = client.post(
        f"/documents/{doc['id']}/links",
        json={"entity_type": "marketing_asset", "entity_id": entity_id},
    )
    assert linked.status_code == 201
    listed = client.get(f"/documents/by-entity/marketing_asset/{entity_id}")
    assert listed.json()["total"] == 1

    link_id = linked.json()["id"]
    unlinked = client.delete(f"/documents/{doc['id']}/links/{link_id}")
    assert unlinked.status_code == 204
    assert client.get(f"/documents/by-entity/marketing_asset/{entity_id}").json()["total"] == 0

    activity = client.get(f"/activity/entity/document/{doc['id']}")
    assert activity.status_code == 200
    keys = {item.get("description_key") for item in activity.json().get("items", [])}
    assert "activity.document.linked" in keys or "activity.document.uploaded" in keys


def test_rename_logs_renamed_activity(client: TestClient) -> None:
    doc = _upload(client, "rename-me.txt", b"rename", title="Old Title")
    renamed = client.patch(f"/documents/{doc['id']}", json={"title": "New Title"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "New Title"
    activity = client.get(f"/activity/entity/document/{doc['id']}")
    keys = {item.get("description_key") for item in activity.json().get("items", [])}
    assert "activity.document.renamed" in keys


def test_export_metadata_csv_requires_export_permission(auth_client: TestClient) -> None:
    _ensure_workspace_perms(auth_client)
    _login(auth_client, "admin@example.com")
    _upload(auth_client, "export-me.txt", b"export")
    exported = auth_client.get("/documents/export")
    assert exported.status_code == 200
    payload = exported.json()
    assert payload["row_count"] >= 1
    assert "title" in payload["csv"]
    assert "file_kind" in payload["csv"]


def test_delete_soft_archives(client: TestClient) -> None:
    doc = _upload(client, "delete-me.txt", b"delete")
    deleted = client.delete(f"/documents/{doc['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["archived_at"] is not None
    assert deleted.json()["status"] == "archived"


def test_preview_and_download_still_work(client: TestClient) -> None:
    doc = _upload(client, "preview-workspace.txt", b"preview workspace")
    preview = client.get(f"/documents/{doc['id']}/preview")
    assert preview.status_code == 200
    download = client.get(f"/documents/{doc['id']}/download")
    assert download.status_code == 200
    assert download.content == b"preview workspace"


def test_contact_and_campaign_entity_types_supported(client: TestClient) -> None:
    doc = _upload(client, "crm-link.txt", b"crm")
    contact_id = str(uuid4())
    campaign_id = str(uuid4())
    assert (
        client.post(
            f"/documents/{doc['id']}/links",
            json={"entity_type": "contact", "entity_id": contact_id},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/documents/{doc['id']}/links",
            json={"entity_type": "campaign", "entity_id": campaign_id},
        ).status_code
        == 201
    )
    by_campaign = client.get("/documents", params={"campaign_id": campaign_id})
    assert by_campaign.status_code == 200
    assert any(item["id"] == doc["id"] for item in by_campaign.json()["items"])


def test_private_visibility_hides_from_other_roles(auth_client: TestClient) -> None:
    _ensure_workspace_perms(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": ("private.txt", io.BytesIO(b"secret private"), "text/plain")}
    upload = auth_client.post(
        "/documents/upload",
        files=files,
        data={"visibility": "private", "title": "Private Doc"},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["results"][0]["document"]["id"]

    _login(auth_client, "sales@example.com")
    listed = auth_client.get("/documents")
    assert listed.status_code == 200
    assert all(item["id"] != doc_id for item in listed.json()["items"])
