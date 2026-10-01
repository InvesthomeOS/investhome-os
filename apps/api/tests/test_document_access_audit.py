"""Document download/preview access audit logging."""

from __future__ import annotations

import io
import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.user_auth import Permission, Role, RolePermission

pytestmark = pytest.mark.usefixtures("client")


def _upload(client: TestClient, filename: str, content: bytes, **form: str) -> dict:
    files = {"files": (filename, io.BytesIO(content), "text/plain")}
    response = client.post("/documents/upload", files=files, data=form)
    assert response.status_code == 201
    result = response.json()["results"][0]
    assert result["success"] is True
    return result["document"]


def _access_logs(db: Session, document_id: str, description_key: str) -> list[ActivityLog]:
    return (
        db.query(ActivityLog)
        .filter(
            ActivityLog.entity_id == UUID(document_id),
            ActivityLog.description_key == description_key,
        )
        .all()
    )


def _assert_no_document_secrets(entry: ActivityLog, *forbidden: bytes | str) -> None:
    blob = json.dumps(
        {
            "metadata": entry.metadata_json,
            "description_key": entry.description_key,
            "event_type": entry.event_type,
        },
        default=str,
    )
    for item in forbidden:
        text = item.decode() if isinstance(item, bytes) else item
        assert text not in blob


def test_successful_download_creates_audit_event(client: TestClient, db: Session) -> None:
    secret = b"download-audit-payload-not-for-logs"
    doc = _upload(client, "audit-dl.txt", secret)
    response = client.get(f"/documents/{doc['id']}/download")
    assert response.status_code == 200
    assert response.content == secret

    logs = _access_logs(db, doc["id"], "activity.document.downloaded")
    assert len(logs) >= 1
    entry = logs[-1]
    meta = entry.metadata_json or {}
    assert entry.actor_user_id is not None
    assert str(entry.entity_id) == doc["id"]
    assert meta["access_type"] == "download"
    assert meta["document_id"] == doc["id"]
    assert meta["confidentiality_level"]
    assert meta["outcome"] == "allowed"
    assert meta["module"] == "documents"
    assert entry.created_at is not None
    _assert_no_document_secrets(entry, secret)


def test_successful_preview_creates_audit_event(client: TestClient, db: Session) -> None:
    secret = b"preview-audit-payload-not-for-logs"
    doc = _upload(client, "audit-pv.txt", secret)
    response = client.get(f"/documents/{doc['id']}/preview")
    assert response.status_code == 200
    assert secret in response.content

    logs = _access_logs(db, doc["id"], "activity.document.previewed")
    assert len(logs) >= 1
    entry = logs[-1]
    meta = entry.metadata_json or {}
    assert entry.actor_user_id is not None
    assert str(entry.entity_id) == doc["id"]
    assert meta["access_type"] == "preview"
    assert meta["confidentiality_level"]
    assert meta["outcome"] == "allowed"
    _assert_no_document_secrets(entry, secret)


def test_unauthorized_access_does_not_leak_document_data(auth_client: TestClient, db: Session) -> None:
    sales = db.query(Role).filter_by(code="sales").first()
    download_perm = db.query(Permission).filter_by(resource="documents", action="download").first()
    assert sales is not None
    if download_perm:
        db.query(RolePermission).filter_by(
            role_id=sales.id,
            permission_id=download_perm.id,
        ).delete()
    db.commit()

    auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    files = {"files": ("preview-only.txt", io.BytesIO(b"secret preview"), "text/plain")}
    upload = auth_client.post("/documents/upload", files=files)
    doc_id = upload.json()["results"][0]["document"]["id"]

    auth_client.post("/auth/login", json={"email": "sales@example.com", "password": "Demo123!"})
    preview = auth_client.get(f"/documents/{doc_id}/preview")
    assert preview.status_code == 403
    assert b"secret preview" not in preview.content

    denials = _access_logs(db, doc_id, "activity.document.access_denied")
    assert len(denials) >= 1
    denial = denials[-1]
    meta = denial.metadata_json or {}
    assert meta["outcome"] == "denied"
    assert meta["access_type"] == "preview"
    _assert_no_document_secrets(denial, b"secret preview", "secret preview")
