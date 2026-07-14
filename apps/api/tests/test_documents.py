"""Document engine API tests."""

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.document import ConfidentialityLevel, Document, DocumentType
from investhome_api.models.user_auth import Permission, RolePermission
from investhome_api.services.storage.factory import get_storage_provider

pytestmark = pytest.mark.usefixtures("client")


def _login(auth_client: TestClient, email: str = "admin@example.com") -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _grant_documents_permissions(auth_client: TestClient) -> None:
    from investhome_api.db.session import get_db
    from investhome_api.main import app

    db: Session = next(app.dependency_overrides[get_db]())
    for action in (
        "view",
        "create",
        "update",
        "archive",
        "download",
        "view_confidential",
        "view_highly_confidential",
    ):
        perm = db.query(Permission).filter_by(resource="documents", action=action).first()
        if perm is None:
            perm = Permission(resource="documents", action=action)
            db.add(perm)
            db.flush()
        role = db.query(RolePermission).join(Permission).filter(
            Permission.resource == "documents",
            Permission.action == action,
        ).first()
        if role is None:
            from investhome_api.models.user_auth import Role

            super_admin = db.query(Role).filter_by(code="super_admin").first()
            if super_admin:
                db.add(RolePermission(role_id=super_admin.id, permission_id=perm.id))
    db.commit()


def _upload(client: TestClient, filename: str, content: bytes, **form: str) -> dict:
    files = {"files": (filename, io.BytesIO(content), "text/plain")}
    response = client.post("/documents/upload", files=files, data=form)
    assert response.status_code == 201
    payload = response.json()
    assert payload["results"][0]["success"] is True
    return payload["results"][0]["document"]


def test_upload_and_list_document(client: TestClient) -> None:
    doc = _upload(client, "sample.txt", b"Hello demo document")
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["id"] == doc["id"] for item in data["items"])


def test_blocked_file_type(client: TestClient) -> None:
    files = {"files": ("malware.exe", io.BytesIO(b"bad"), "application/octet-stream")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 201
    result = response.json()["results"][0]
    assert result["success"] is False


def test_file_size_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_MAX_UPLOAD_BYTES", "100")
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    files = {"files": ("large.txt", io.BytesIO(b"x" * 200), "text/plain")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 201
    assert response.json()["results"][0]["success"] is False


def test_download_document(client: TestClient) -> None:
    doc = _upload(client, "download-me.txt", b"download content")
    response = client.get(f"/documents/{doc['id']}/download")
    assert response.status_code == 200
    assert response.content == b"download content"


def test_preview_txt_document(client: TestClient) -> None:
    doc = _upload(client, "preview.txt", b"preview content")
    response = client.get(f"/documents/{doc['id']}/preview")
    assert response.status_code == 200
    assert b"preview content" in response.content


def test_preview_unavailable_for_docx(client: TestClient) -> None:
    content = b"PK\x03\x04fake docx"
    files = {"files": ("report.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/documents/upload", files=files)
    doc_id = response.json()["results"][0]["document"]["id"]
    preview = client.get(f"/documents/{doc_id}/preview")
    assert preview.status_code == 415


def test_version_upload(client: TestClient) -> None:
    doc = _upload(client, "v1.txt", b"version one")
    files = {"file": ("v2.txt", io.BytesIO(b"version two"), "text/plain")}
    response = client.post(f"/documents/{doc['id']}/versions", files=files, data={"version_notes": "Second version"})
    assert response.status_code == 201
    new_doc = response.json()
    assert new_doc["version_number"] == 2
    history = client.get(f"/documents/{doc['id']}/versions")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 2


def test_archive_and_restore(client: TestClient) -> None:
    doc = _upload(client, "archive-me.txt", b"archive")
    archived = client.post(f"/documents/{doc['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    restored = client.post(f"/documents/{doc['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_confidential_document_hidden_without_permission(auth_client: TestClient) -> None:
    _grant_documents_permissions(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": ("secret.txt", io.BytesIO(b"top secret"), "text/plain")}
    upload = auth_client.post(
        "/documents/upload",
        files=files,
        data={"confidentiality_level": "highly_confidential"},
    )
    assert upload.status_code == 201
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/documents")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_search_includes_documents(client: TestClient) -> None:
    _upload(client, "temple-search.txt", b"The Temple investor materials demo")
    response = client.get("/search?q=Temple")
    assert response.status_code == 200
    groups = {g["entity_type"]: g for g in response.json()["groups"]}
    assert "document" in groups


def test_link_document_to_entity(client: TestClient) -> None:
    doc = _upload(client, "linked.txt", b"linked")
    entity_id = str(uuid4())
    response = client.post(
        f"/documents/{doc['id']}/links",
        json={"entity_type": "lead", "entity_id": entity_id, "relationship_type": "supporting"},
    )
    assert response.status_code == 201
    listed = client.get(f"/documents/by-entity/lead/{entity_id}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
