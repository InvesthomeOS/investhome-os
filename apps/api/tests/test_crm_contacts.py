"""CRM contact management API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.schemas.crm_contacts import CrmContactCreate, CrmInvestmentProfileSchema


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _create_contact_payload(**overrides) -> dict:
    base = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Test Contact {uuid4().hex[:6]}",
        "primary_email": f"contact.{uuid4().hex[:8]}@example.com",
        "primary_phone": "+15551234567",
        "lifecycle_stage": "new",
        "priority": "normal",
    }
    base.update(overrides)
    return base


def test_create_contact(client: TestClient) -> None:
    payload = _create_contact_payload()
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["contact"]["display_name"] == payload["display_name"]
    assert body["contact"]["primary_email"] == payload["primary_email"]


def test_get_contact_detail(client: TestClient) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload()).json()
    contact_id = created["contact"]["id"]
    response = client.get(f"/crm/contacts/{contact_id}")
    assert response.status_code == 200
    assert response.json()["id"] == contact_id


def test_update_contact(client: TestClient) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload()).json()
    contact_id = created["contact"]["id"]
    response = client.put(
        f"/crm/contacts/{contact_id}",
        json={"display_name": "Updated Name", "priority": "high"},
    )
    assert response.status_code == 200
    assert response.json()["contact"]["display_name"] == "Updated Name"
    assert response.json()["contact"]["priority"] == "high"


def test_list_contacts_pagination(client: TestClient) -> None:
    for _ in range(3):
        client.post("/crm/contacts", json=_create_contact_payload())
    response = client.get("/crm/contacts?page=1&page_size=2&sort_by=created_at&sort_dir=desc")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 2
    assert body["total"] >= 3


def test_duplicate_detection(client: TestClient) -> None:
    email = f"dup.{uuid4().hex[:8]}@example.com"
    client.post("/crm/contacts", json=_create_contact_payload(primary_email=email))
    response = client.post(
        "/crm/contacts/check-duplicates",
        json={"primary_email": email},
    )
    assert response.status_code == 200
    matches = response.json()["matches"]
    assert len(matches) >= 1
    assert matches[0]["match_reason"] == "email"


def test_merge_contacts(client: TestClient) -> None:
    survivor = client.post("/crm/contacts", json=_create_contact_payload(display_name="Survivor")).json()
    merged = client.post(
        "/crm/contacts",
        json=_create_contact_payload(display_name="Merged Away", primary_email=f"merge.{uuid4().hex[:6]}@example.com"),
    ).json()
    response = client.post(
        "/crm/contacts/merge",
        json={
            "survivor_contact_id": survivor["contact"]["id"],
            "merged_contact_id": merged["contact"]["id"],
        },
    )
    assert response.status_code == 200
    merged_check = client.get(f"/crm/contacts/{merged['contact']['id']}")
    assert merged_check.json()["status"] == "archived"


def test_archive_and_restore(client: TestClient) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload()).json()
    contact_id = created["contact"]["id"]
    archive = client.post(f"/crm/contacts/{contact_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["contact"]["status"] == "archived"
    restore = client.post(f"/crm/contacts/{contact_id}/restore")
    assert restore.status_code == 200
    assert restore.json()["contact"]["status"] == "active"


def test_bulk_update(client: TestClient) -> None:
    ids = []
    for _ in range(2):
        created = client.post("/crm/contacts", json=_create_contact_payload()).json()
        ids.append(created["contact"]["id"])
    response = client.post(
        "/crm/contacts/bulk-update",
        json={"contact_ids": ids, "priority": "urgent"},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 2


def test_import_contacts(client: TestClient) -> None:
    response = client.post(
        "/crm/contacts/import",
        json={
            "mode": "create",
            "rows": [
                {
                    "display_name": f"Import {uuid4().hex[:6]}",
                    "contact_type": "buyer",
                    "primary_email": f"import.{uuid4().hex[:8]}@example.com",
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1


def test_export_contacts(client: TestClient) -> None:
    client.post("/crm/contacts", json=_create_contact_payload())
    response = client.get("/crm/contacts/export")
    assert response.status_code == 200
    assert "display_name" in response.text


def test_saved_views_crud(client: TestClient, db: Session) -> None:
    create = client.post(
        "/crm/contacts/saved-views",
        json={"name": "My Investors", "filters_json": {"contact_type": "investor"}, "is_default": True},
    )
    assert create.status_code == 201
    view_id = create.json()["id"]
    listing = client.get("/crm/contacts/saved-views")
    assert listing.status_code == 200
    assert any(item["id"] == view_id for item in listing.json())
    update = client.put(f"/crm/contacts/saved-views/{view_id}", json={"name": "Investors Updated"})
    assert update.status_code == 200
    delete = client.delete(f"/crm/contacts/saved-views/{view_id}")
    assert delete.status_code == 204


def test_field_stripping_without_financial_permission(auth_client: TestClient, db: Session) -> None:
    from investhome_api.config.permissions_config import DEFAULT_ROLE_PERMISSIONS
    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one_or_none()
    if perm_read is None:
        perm_read = Permission(resource="crm", action="read")
        db.add(perm_read)
        db.flush()
    role = Role(name="crm_limited", code=f"crm_limited_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    email = f"crm.limited.{uuid4().hex[:6]}@example.com"
    limited_user = User(
        email=email,
        full_name="CRM Limited",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(limited_user)
    db.flush()
    db.add(UserRole(user_id=limited_user.id, role_id=role.id))
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.INVESTOR,
            display_name="Financial Contact",
            investment_profile=CrmInvestmentProfileSchema(
                investment_capacity_min=100000,
                investment_capacity_max=500000,
            ),
            compliance_data={"kyc_status": "verified"},
        ),
    )
    db.commit()

    _login(auth_client, email)
    response = auth_client.get(f"/crm/contacts/{contact.id}")
    assert response.status_code == 200
    body = response.json()
    assert body.get("investment_profile") is None
    assert body.get("compliance_data") is None


def test_crm_contacts_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/crm/contacts")
    assert response.status_code == 403


def test_delete_contact(client: TestClient) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload()).json()
    contact_id = created["contact"]["id"]
    response = client.delete(f"/crm/contacts/{contact_id}")
    assert response.status_code == 204
    assert client.get(f"/crm/contacts/{contact_id}").status_code == 404
