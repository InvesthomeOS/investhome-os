"""Company workspace documents API tests."""

import io
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.company import CompanyEntityType, CompanyStatus
from investhome_api.models.company_workspace_document import (
    CompanyDocumentShareLink,
    CompanyDocumentVersion,
    CompanyWorkspaceDocument,
    DocumentFolder,
)
from investhome_api.models.document import ConfidentialityLevel, Document
from investhome_api.services.company_document_service import (
    create_share_link,
    resolve_share_link,
    validate_folder_parent,
)


def _create_company(client: TestClient) -> str:
    response = client.post(
        "/companies",
        json={
            "company_name": "Doc Test Co",
            "legal_name": "Doc Test Co Ltd",
            "entity_type": CompanyEntityType.CORPORATION.value,
            "registration_number": "DOC-REG-001",
            "tax_id": "2020202020",
            "country": "TR",
            "city": "Istanbul",
            "status": CompanyStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client: TestClient, company_id: str, filename: str = "policy.txt", content: bytes = b"Company policy v1") -> dict:
    files = {"file": (filename, io.BytesIO(content), "text/plain")}
    data = {"company_id": company_id, "title": "Test Policy", "confidentiality_level": "internal"}
    response = client.post("/company-documents/upload", files=files, data=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_list_and_get(client: TestClient) -> None:
    company_id = _create_company(client)
    doc = _upload(client, company_id)
    assert doc["document_number"].startswith("CD-")
    assert doc["title"] == "Test Policy"

    listing = client.get(f"/company-documents?company_id={company_id}")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = client.get(f"/company-documents/{doc['id']}")
    assert detail.status_code == 200
    assert detail.json()["file_name"] == "policy.txt"


def test_version_immutability(client: TestClient) -> None:
    company_id = _create_company(client)
    doc = _upload(client, company_id, content=b"version one")
    files = {"file": ("v2.txt", io.BytesIO(b"version two"), "text/plain")}
    v2 = client.post(f"/company-documents/{doc['id']}/versions", files=files, data={"version_notes": "Updated"})
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2

    versions = client.get(f"/company-documents/{doc['id']}/versions")
    assert versions.status_code == 200
    items = versions.json()
    assert len(items) == 2
    assert items[0]["version_number"] == 1
    assert items[1]["is_current"] is True


def test_folder_circular_prevention(client: TestClient, db: Session) -> None:
    from uuid import UUID

    company_id = UUID(_create_company(client))
    parent = DocumentFolder(company_id=company_id, name="Parent", slug="parent")
    db.add(parent)
    db.flush()
    child = DocumentFolder(
        company_id=company_id,
        name="Child",
        slug="child",
        parent_folder_id=parent.id,
    )
    db.add(child)
    db.commit()
    with pytest.raises(ValueError, match="circular"):
        validate_folder_parent(db, parent.id, child.id)


def test_duplicate_detection(client: TestClient) -> None:
    company_id = _create_company(client)
    content = b"duplicate content test"
    first = _upload(client, company_id, content=content)
    files = {"file": ("dup.txt", io.BytesIO(content), "text/plain")}
    data = {"company_id": company_id, "allow_duplicate": "false"}
    second = client.post("/company-documents/upload", files=files, data=data)
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]


def test_expiring_query(client: TestClient) -> None:
    company_id = _create_company(client)
    files = {"file": ("expiring.txt", io.BytesIO(b"expires soon"), "text/plain")}
    exp = (date.today() + timedelta(days=7)).isoformat()
    data = {"company_id": company_id, "expiration_date": exp}
    client.post("/company-documents/upload", files=files, data=data)
    response = client.get(f"/company-documents/expiring?company_id={company_id}&days=30")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_secure_link_expiry(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    doc = _upload(client, company_id)
    share = client.post(
        f"/company-documents/{doc['id']}/share",
        json={"expires_in_hours": 1, "max_downloads": 1},
    )
    assert share.status_code == 201
    token = share.json()["token"]

    download = client.get(f"/company-documents/shared/{token}/download")
    assert download.status_code == 200

    link = db.query(CompanyDocumentShareLink).filter_by(token=token).one()
    link.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    expired = client.get(f"/company-documents/shared/{token}/download")
    assert expired.status_code == 403


def test_confidential_permission_filtering(auth_client: TestClient) -> None:
    def _login(email: str) -> None:
        r = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
        assert r.status_code == 200

    _login("admin@example.com")
    company_id = _create_company(auth_client)
    files = {"file": ("secret.txt", io.BytesIO(b"top secret"), "text/plain")}
    data = {"company_id": company_id, "confidentiality_level": "highly_confidential"}
    auth_client.post("/company-documents/upload", files=files, data=data)

    _login("readonly@example.com")
    listing = auth_client.get(f"/company-documents?company_id={company_id}")
    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_archive_restore_and_audit(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    doc = _upload(client, company_id)
    archived = client.post(f"/company-documents/{doc['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    restored = client.post(f"/company-documents/{doc['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None

    logs = db.query(ActivityLog).filter(ActivityLog.description_key.like("%company_document%")).all()
    assert len(logs) >= 1


def test_storage_summary(client: TestClient) -> None:
    company_id = _create_company(client)
    _upload(client, company_id)
    summary = client.get(f"/company-documents/storage-summary?company_id={company_id}")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_documents"] >= 1
    assert body["total_bytes"] > 0


def test_malware_scan_stub(client: TestClient) -> None:
    company_id = _create_company(client)
    doc = _upload(client, company_id)
    scan = client.post(f"/company-documents/{doc['id']}/malware-scan")
    assert scan.status_code == 200
    assert scan.json()["status"] == "passed"


def test_default_folders(client: TestClient) -> None:
    company_id = _create_company(client)
    folders = client.get(f"/company-documents/folders?company_id={company_id}")
    assert folders.status_code == 200
    assert folders.json()["total"] >= 7
