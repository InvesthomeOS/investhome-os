"""CRM contact management API tests."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmContactTypeAssignment,
)
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
    body = response.json()
    assert body["id"] == contact_id
    assert "amount_and_currency_amount" in body
    assert body["amount_and_currency_amount"] is None


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


def test_bitrix_verification_filters_detail_summary_and_export(
    client: TestClient,
    db: Session,
) -> None:
    bitrix = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Verification Contact",
        primary_phone="+15550001111",
        primary_email="verification@example.com",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={
            "bitrix_import": {
                "external_ids": ["source.xls:1"],
                "source_files": ["source.xls"],
                "source_roles": ["active_customers"],
                "historical_junk": True,
                "conflicts": [{"field": "display_name", "values": ["private"]}],
            },
            "bitrix_agent": {"status": "active"},
        },
    )
    other = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Existing OS Contact",
        source="Referral",
        status=CrmContactStatus.ACTIVE,
    )
    db.add_all([bitrix, other])
    db.flush()
    db.add(
        CrmContactTypeAssignment(
            contact_id=bitrix.id,
            contact_type=CrmContactType.BROKER,
            is_primary=False,
        )
    )
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=bitrix.id,
            activity_type=CrmActivityType.COMMENT,
            activity_category=CrmActivityCategory.NOTE,
            title="Historical Bitrix comment",
            description="private historical text",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={"bitrix_historical_comment": {"import_key": "test"}},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=bitrix.id,
            project_group="reit",
            source="bitrix",
            source_external_id="source.xls:agreement-1",
        )
    )
    db.commit()

    source_list = client.get("/crm/contacts?source_group=bitrix")
    assert source_list.status_code == 200
    assert {item["id"] for item in source_list.json()["items"]} == {str(bitrix.id)}
    role_list = client.get("/crm/contacts?role_group=agent")
    assert role_list.status_code == 200
    assert str(bitrix.id) in {item["id"] for item in role_list.json()["items"]}

    detail = client.get(f"/crm/contacts/{bitrix.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["source"] == "Bitrix"
    assert body["bitrix_history"]["external_ids"] == ["source.xls:1"]
    assert body["bitrix_history"]["conflict_fields"] == ["display_name"]
    assert "values" not in body["bitrix_history"]
    assert body["crm_activities"][0]["imported_historical_comment"] is True
    assert body["crm_agreements"][0]["project_group"] == "reit"
    assert body["agent"]["is_agent"] is True

    summary = client.get("/crm/contacts/bitrix-verification-summary")
    assert summary.status_code == 200
    assert summary.json()["bitrix_contacts"] == 1
    assert summary.json()["imported_historical_comments"] == 1
    assert summary.json()["imported_agreements"] == 1

    exported = client.get("/crm/contacts/export/bitrix-verification")
    assert exported.status_code == 200
    assert "canonical_contact_id" in exported.text
    assert "Verification Contact" in exported.text
    assert "private historical text" not in exported.text


def test_current_junk_list_is_filtered_canonical_contacts(
    client: TestClient,
    db: Session,
) -> None:
    junk = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Junk Only",
        primary_phone="+15550002222",
        source="Bitrix",
        status=CrmContactStatus.ARCHIVED,
        metadata_json={
            "bitrix_import": {
                "external_ids": ["Junklar.xls:9"],
                "source_files": ["Junklar.xls"],
                "source_roles": ["junk"],
                "historical_junk": True,
                "original_asama": "Junk Lead",
            }
        },
    )
    both = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Active With Junk History",
        primary_phone="+15550003333",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={
            "bitrix_import": {
                "source_roles": ["active_customers", "junk"],
                "historical_junk": True,
                "original_asama": "Uzun Dönem Yatırımcı",
            }
        },
    )
    db.add_all([junk, both])
    db.commit()

    response = client.get("/crm/contacts?bitrix_list=current_junk")
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["display_name"] for item in items} == {"Junk Only"}
    assert items[0]["bitrix_original_stage"] == "Junk Lead"
    assert items[0]["bitrix_historical_junk"] is True
    assert items[0]["id"] == str(junk.id)
    assert "secondary_phones" in items[0]
    assert "secondary_emails" in items[0]


def test_junk_list_search_matches_secondary_phone_and_email(
    client: TestClient,
    db: Session,
) -> None:
    junk = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Junk Search Target",
        primary_phone="+15550004444",
        secondary_phones=["+15550005555"],
        primary_email="one@example.com",
        secondary_emails=["two@example.com"],
        source="Bitrix",
        status=CrmContactStatus.ARCHIVED,
        metadata_json={
            "bitrix_import": {
                "source_roles": ["junk"],
                "historical_junk": True,
                "original_asama": "Junk Lead",
            }
        },
    )
    db.add(junk)
    db.commit()

    phone = client.get("/crm/contacts?bitrix_list=current_junk&search=5550005555")
    email = client.get("/crm/contacts?bitrix_list=current_junk&search=two@example.com")
    assert phone.status_code == 200
    assert email.status_code == 200
    assert {item["display_name"] for item in phone.json()["items"]} == {"Junk Search Target"}
    assert {item["display_name"] for item in email.json()["items"]} == {"Junk Search Target"}


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


def test_contacts_category_and_junk_reason_filters(client: TestClient, db: Session) -> None:
    customer = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Normal Customer",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    agent = CrmContact(
        contact_type=CrmContactType.BROKER,
        display_name="Agent Contact",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    junk = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Junk Customer",
        source="Bitrix",
        status=CrmContactStatus.ARCHIVED,
        junk_reason="Ulaşılamadı",
        metadata_json={"bitrix_import": {"source_roles": ["junk"], "historical_junk": True}},
    )
    db.add_all([customer, agent, junk])
    db.flush()
    db.add(CrmAgreement(contact_id=customer.id, project_group="reit", source="bitrix", source_external_id="reit:1"))
    db.commit()

    agents = client.get("/crm/contacts?category=agent")
    agreements = client.get("/crm/contacts?category=agreement&include_archived=true")
    customers = client.get("/crm/contacts?category=customer")
    reasons = client.get("/crm/contacts?junk_reason=Ulaşılamadı")
    reason_list = client.get("/crm/contacts/junk-reasons")
    assert agents.status_code == 200
    assert {item["display_name"] for item in agents.json()["items"]} == {"Agent Contact"}
    assert {item["display_name"] for item in agreements.json()["items"]} == {"Normal Customer"}
    assert "Agent Contact" not in {item["display_name"] for item in customers.json()["items"]}
    assert {item["display_name"] for item in reasons.json()["items"]} == {"Junk Customer"}
    assert reason_list.status_code == 200
    assert any(item["reason"] == "Ulaşılamadı" for item in reason_list.json()["items"])


def test_contact_status_requires_junk_reason_and_keeps_history(client: TestClient, db: Session) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload(display_name="Status Target")).json()
    contact_id = created["contact"]["id"]
    missing = client.post(f"/crm/contacts/{contact_id}/status", json={"status": "archived"})
    assert missing.status_code == 422
    junked = client.post(
        f"/crm/contacts/{contact_id}/status",
        json={"status": "archived", "junk_reason": "Bütçesi Yetersiz"},
    )
    assert junked.status_code == 200
    body = junked.json()["contact"]
    assert body["status"] == "archived"
    assert body["junk_reason"] == "Bütçesi Yetersiz"
    restored = client.post(f"/crm/contacts/{contact_id}/status", json={"status": "active"})
    assert restored.status_code == 200
    restored_body = restored.json()["contact"]
    assert restored_body["status"] == "active"
    assert restored_body["junk_reason"] == "Bütçesi Yetersiz"
    timeline = client.get(f"/crm/contacts/{contact_id}/timeline")
    assert timeline.status_code == 200
    titles = [item["title"] for item in timeline.json()["items"]]
    assert any("Junk" in title for title in titles)
    assert any("Aktif" in title for title in titles)


def test_contact_timeline_includes_imported_historical_comment(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Timeline Contact",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.COMMENT,
            activity_category=CrmActivityCategory.NOTE,
            title="Imported comment",
            description="Bitrix historical body",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={"bitrix_historical_comment": {"import_key": "safe-1"}},
        )
    )
    db.commit()
    detail = client.get(f"/crm/contacts/{contact.id}")
    timeline = client.get(f"/crm/contacts/{contact.id}/timeline")
    assert detail.status_code == 200
    assert detail.json()["crm_activities"][0]["imported_historical_comment"] is True
    assert timeline.status_code == 200
    items = timeline.json()["items"]
    assert any(item["imported_historical_comment"] for item in items)
    assert any(item["summary"] == "Bitrix historical body" for item in items)


def test_update_contact_allows_blank_phone_and_logs_changes(client: TestClient) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload()).json()
    contact_id = created["contact"]["id"]
    blank = client.put(
        f"/crm/contacts/{contact_id}",
        json={"primary_phone": "", "display_name": created["contact"]["display_name"]},
    )
    assert blank.status_code == 200, blank.text
    assert blank.json()["contact"]["primary_phone"] in {None, ""}
    invalid = client.put(f"/crm/contacts/{contact_id}", json={"primary_phone": "not-a-phone"})
    assert invalid.status_code == 422
    restored = client.put(f"/crm/contacts/{contact_id}", json={"primary_phone": "+15559876543"})
    assert restored.status_code == 200
    assert restored.json()["contact"]["primary_phone"]
    timeline = client.get(f"/crm/contacts/{contact_id}/timeline")
    titles = [item["title"] for item in timeline.json()["items"]]
    assert "Kişi bilgileri güncellendi" in titles
    assert not any(item["title"] == "activity.crm_contact.updated" for item in timeline.json()["items"])


def test_contact_agreements_promote_financial_metadata(client: TestClient, db: Session) -> None:
    created = client.post("/crm/contacts", json=_create_contact_payload(display_name="Agreement Owner")).json()
    contact_id = created["contact"]["id"]
    db.add(
        CrmAgreement(
            contact_id=UUID(contact_id),
            project_group="uniloft",
            source="bitrix",
            source_external_id=f"unit:{uuid4().hex[:8]}",
            unit_number="12A",
            metadata_json={"purchase_price": "450000", "deposit": "25000", "payment_amount": "120000"},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=UUID(contact_id),
            project_group="reit",
            source="bitrix",
            source_external_id=f"reit:{uuid4().hex[:8]}",
            investment_amount="75000",
        )
    )
    db.commit()
    detail = client.get(f"/crm/contacts/{contact_id}")
    assert detail.status_code == 200
    agreements = detail.json()["crm_agreements"]
    unit = next(item for item in agreements if item["project_group"] == "uniloft")
    reit = next(item for item in agreements if item["project_group"] == "reit")
    assert unit["unit_number"] == "12A"
    assert unit["purchase_price"] == "450000"
    assert unit["deposit"] == "25000"
    assert unit["payment_amount"] == "120000"
    assert reit["investment_amount"] == "75000"
    assert reit["unit_number"] in {None, ""}
