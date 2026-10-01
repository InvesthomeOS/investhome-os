"""Document engine API tests."""

import io
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.document import ConfidentialityLevel, Document, DocumentType
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
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
    from docx import Document as DocxDocument

    buffer = io.BytesIO()
    docx = DocxDocument()
    docx.add_paragraph("Preview is not supported for Word documents.")
    docx.save(buffer)
    content = buffer.getvalue()
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


def test_preview_requires_download_permission(auth_client: TestClient) -> None:
    from investhome_api.db.session import get_db
    from investhome_api.main import app
    from investhome_api.models.user_auth import Permission, Role, RolePermission

    db: Session = next(app.dependency_overrides[get_db]())
    sales = db.query(Role).filter_by(code="sales").first()
    download_perm = db.query(Permission).filter_by(resource="documents", action="download").first()
    assert sales is not None
    if download_perm:
        db.query(RolePermission).filter_by(
            role_id=sales.id,
            permission_id=download_perm.id,
        ).delete()
    db.commit()

    _login(auth_client, "admin@example.com")
    files = {"files": ("preview-only.txt", io.BytesIO(b"secret preview"), "text/plain")}
    upload = auth_client.post("/documents/upload", files=files)
    doc_id = upload.json()["results"][0]["document"]["id"]
    _login(auth_client, "sales@example.com")
    preview = auth_client.get(f"/documents/{doc_id}/preview")
    assert preview.status_code == 403


def test_confidential_document_hidden_from_activity(auth_client: TestClient) -> None:
    _grant_documents_permissions(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": ("secret-activity.txt", io.BytesIO(b"secret"), "text/plain")}
    upload = auth_client.post(
        "/documents/upload",
        files=files,
        data={"confidentiality_level": "highly_confidential", "title": "Secret Activity Doc"},
    )
    doc_id = upload.json()["results"][0]["document"]["id"]
    _login(auth_client, "readonly@example.com")
    activity = auth_client.get(f"/activity/entity/document/{doc_id}")
    assert activity.status_code == 200
    assert activity.json()["total"] == 0


def test_unlink_clears_entity_listing(client: TestClient) -> None:
    doc = _upload(client, "unlink-test.txt", b"linked")
    entity_id = str(uuid4())
    link_resp = client.post(
        f"/documents/{doc['id']}/links",
        json={"entity_type": "lead", "entity_id": entity_id},
    )
    link_id = link_resp.json()["id"]
    assert client.get(f"/documents/by-entity/lead/{entity_id}").json()["total"] == 1
    client.delete(f"/documents/{doc['id']}/links/{link_id}")
    assert client.get(f"/documents/by-entity/lead/{entity_id}").json()["total"] == 0


def test_confidential_level_requires_view_confidential(auth_client: TestClient) -> None:
    _grant_documents_permissions(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": ("confidential.txt", io.BytesIO(b"confidential data"), "text/plain")}
    upload = auth_client.post(
        "/documents/upload",
        files=files,
        data={"confidentiality_level": "confidential"},
    )
    assert upload.status_code == 201
    _login(auth_client, "sales@example.com")
    response = auth_client.get("/documents")
    assert response.status_code == 200
    assert response.json()["total"] == 0


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


def _ensure_permission(db: Session, resource: str, action: str) -> Permission:
    perm = db.query(Permission).filter_by(resource=resource, action=action).one_or_none()
    if perm is None:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        db.flush()
    return perm


def _documents_user_with(db: Session, extra: list[tuple[str, str]], *, label: str) -> str:
    grants = [("documents", "view"), ("documents", "update"), *extra]
    role = Role(name=label, code=f"{label}_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    for resource, action in grants:
        db.add(RolePermission(role_id=role.id, permission_id=_ensure_permission(db, resource, action).id))
    email = f"{label}.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name=label,
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return email


def _reload_document(db: Session, document_id: str) -> Document:
    db.expire_all()
    document = db.get(Document, UUID(str(document_id)))
    assert document is not None
    return document


def _admin_upload(auth_client: TestClient) -> dict:
    _grant_documents_permissions(auth_client)
    _login(auth_client, "admin@example.com")
    files = {"files": (f"meta-{uuid4().hex[:6]}.txt", io.BytesIO(b"document metadata"), "text/plain")}
    upload = auth_client.post("/documents/upload", files=files)
    assert upload.status_code == 201, upload.text
    return upload.json()["results"][0]["document"]


def test_documents_update_can_edit_ordinary_metadata(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    email = _documents_user_with(db, [], label="doc_update_only")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"title": "Ordinary Title", "description": "Ordinary notes"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Ordinary Title"
    assert response.json()["description"] == "Ordinary notes"


def test_documents_update_cannot_change_confidentiality_level(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    original = _reload_document(db, doc["id"])
    original_level = original.confidentiality_level
    email = _documents_user_with(db, [], label="doc_conf_blocked")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"confidentiality_level": "confidential"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.confidentiality_level == original_level


def test_documents_update_cannot_change_owner_user_id(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    original = _reload_document(db, doc["id"])
    original_owner = original.owner_user_id
    new_owner = db.query(User).filter_by(email="sales@example.com").one()
    email = _documents_user_with(db, [], label="doc_owner_blocked")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"owner_user_id": str(new_owner.id)},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.owner_user_id == original_owner


def test_documents_manage_can_change_confidentiality_level(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    email = _documents_user_with(db, [("documents", "manage")], label="doc_manage_conf")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"confidentiality_level": "confidential"},
    )
    assert response.status_code == 200, response.text
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.confidentiality_level == ConfidentialityLevel.CONFIDENTIAL


def test_documents_transfer_ownership_can_change_owner(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    new_owner = db.query(User).filter_by(email="sales@example.com").one()
    email = _documents_user_with(db, [("documents", "transfer_ownership")], label="doc_xfer_owner")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"owner_user_id": str(new_owner.id)},
    )
    assert response.status_code == 200, response.text
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.owner_user_id == new_owner.id


def test_super_admin_can_change_document_confidentiality_and_owner(auth_client: TestClient, db: Session) -> None:
    doc = _admin_upload(auth_client)
    new_owner = db.query(User).filter_by(email="sales@example.com").one()
    _login(auth_client, "admin@example.com")
    conf = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"confidentiality_level": "confidential"},
    )
    assert conf.status_code == 200, conf.text
    owner = auth_client.patch(
        f"/documents/{doc['id']}",
        json={"owner_user_id": str(new_owner.id)},
    )
    assert owner.status_code == 200, owner.text
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.confidentiality_level == ConfidentialityLevel.CONFIDENTIAL
    assert reloaded.owner_user_id == new_owner.id


def test_mixed_document_payload_cannot_bypass_sensitive_restriction(
    auth_client: TestClient, db: Session
) -> None:
    doc = _admin_upload(auth_client)
    original = _reload_document(db, doc["id"])
    original_title = original.title
    original_level = original.confidentiality_level
    original_owner = original.owner_user_id
    new_owner = db.query(User).filter_by(email="sales@example.com").one()
    email = _documents_user_with(db, [], label="doc_mixed")
    _login(auth_client, email)
    response = auth_client.patch(
        f"/documents/{doc['id']}",
        json={
            "title": "Smuggled Title",
            "confidentiality_level": "confidential",
            "owner_user_id": str(new_owner.id),
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    reloaded = _reload_document(db, doc["id"])
    assert reloaded.title == original_title
    assert reloaded.confidentiality_level == original_level
    assert reloaded.owner_user_id == original_owner
