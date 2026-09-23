"""CRM operational leads workspace tests — live table only, no demo seed."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.lead import Lead, LeadStatus


def test_crm_leads_empty_kpis_are_zero(client: TestClient) -> None:
    response = client.get("/crm/leads")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["kpis"] == {
        "total": 0,
        "active": 0,
        "yeni": 0,
        "following": 0,
        "qualified": 0,
        "converted": 0,
        "unqualified": 0,
        "unmatched": 0,
        "failed": 0,
    }


def test_crm_leads_create_edit_stage_filter_and_kanban_list_consistency(
    client: TestClient, db: Session
) -> None:
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Ayşe Lead",
            "phone": "+90 555 111 22 33",
            "email": "ayse.lead@example.com",
            "source": "website",
            "project": "1812",
            "notes": "Manual intake",
        },
    )
    assert created.status_code == 201, created.text
    lead = created.json()
    assert lead["full_name"] == "Ayşe Lead"
    assert lead["stage"] == "yeni"
    assert lead["ingest_status"] == "ok"
    assert lead["project"] == "1812"
    lead_id = lead["id"]

    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    body = listed.json()
    assert body["kpis"]["total"] == 1
    assert body["kpis"]["yeni"] == 1
    assert any(item["id"] == lead_id for item in body["items"])

    patched = client.patch(
        f"/crm/leads/{lead_id}",
        json={"notes": "Updated note", "campaign": "Spring Form"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["notes"] == "Updated note"
    assert patched.json()["campaign"] == "Spring Form"

    moved = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "following"})
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"] == "following"

    blocked = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "converted"})
    assert blocked.status_code == 400

    following = client.get("/crm/leads", params={"stage": "following"})
    assert following.status_code == 200
    assert following.json()["items"][0]["id"] == lead_id
    assert following.json()["kpis"]["following"] == 1
    assert following.json()["kpis"]["total"] == 1

    search = client.get("/crm/leads", params={"search": "Ayşe", "source": "website", "project": "1812"})
    assert search.status_code == 200
    assert len(search.json()["items"]) == 1

    db.expire_all()
    row = db.get(Lead, UUID(lead_id))
    assert row is not None
    assert row.status == LeadStatus.FOLLOW_UP
    assert row.is_demo is False


def test_crm_leads_duplicate_person_warning_and_confirm(client: TestClient, db: Session) -> None:
    person = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name="Existing CRM Person",
        status=CrmContactStatus.ACTIVE,
        primary_email="existing.person@example.com",
        primary_phone="+905551234567",
    )
    db.add(person)
    db.commit()

    conflict = client.post(
        "/crm/leads",
        json={
            "full_name": "New Duplicate",
            "email": "existing.person@example.com",
            "source": "manual",
        },
    )
    assert conflict.status_code == 409, conflict.text
    body = conflict.json()
    assert body["error"]["code"] == "existing_person"
    assert body["matches"][0]["kind"] == "person"
    assert body["matches"][0]["id"] == str(person.id)
    assert "/workspaces/crm/contacts/" in body["matches"][0]["href"]
    db.expire_all()
    assert (
        db.scalar(select(func.count()).select_from(Lead).where(Lead.email == "existing.person@example.com"))
        or 0
    ) == 0

    confirmed = client.post(
        "/crm/leads?confirm=true",
        json={
            "full_name": "New Duplicate",
            "email": "existing.person@example.com",
            "source": "manual",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    lead = confirmed.json()
    assert lead["existing_person_id"] == str(person.id)
    people_before = db.scalar(select(func.count()).select_from(CrmContact)) or 0

    converted = client.post(f"/crm/leads/{lead['id']}/convert")
    assert converted.status_code == 200, converted.text
    result = converted.json()
    assert result["reused_existing"] is True
    assert result["contact_id"] == str(person.id)
    assert result["lead"]["stage"] == "converted"
    db.expire_all()
    people_after = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    assert people_after == people_before


def test_crm_leads_convert_creates_person_not_purchase(client: TestClient, db: Session) -> None:
    agreements_before = db.scalar(select(func.count()).select_from(CrmAgreement)) or 0
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Convert Person",
            "email": "convert.person@example.com",
            "phone": "0555 222 33 44",
            "source": "google",
            "campaign": "Search Brand",
            "stage": "qualified",
        },
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]

    converted = client.post(f"/crm/leads/{lead_id}/convert")
    assert converted.status_code == 200, converted.text
    body = converted.json()
    assert body["reused_existing"] is False
    assert body["lead"]["stage"] == "converted"
    contact_id = body["contact_id"]
    db.expire_all()
    contact = db.get(CrmContact, UUID(contact_id))
    assert contact is not None
    assert contact.lead_id is not None
    assert contact.source == "google"
    assert "Search Brand" in (contact.notes or "")
    agreements_after = db.scalar(select(func.count()).select_from(CrmAgreement)) or 0
    assert agreements_after == agreements_before
    lead = db.get(Lead, UUID(lead_id))
    assert lead is not None
    assert lead.status == LeadStatus.WON
    assert lead.converted_contact_id == contact.id


def test_crm_leads_ingest_never_discards_failed_or_unmatched(client: TestClient, db: Session) -> None:
    failed = client.post(
        "/crm/leads/ingest",
        json={"provider": "meta", "payload": {"form": "empty"}},
    )
    assert failed.status_code == 201, failed.text
    assert failed.json()["ingest_status"] == "failed"
    assert failed.json()["full_name"] == "Eşleşmeyen kaynak lead"

    unmatched = client.post(
        "/crm/leads/ingest",
        json={"provider": "google", "full_name": "Ads Name Only", "campaign": "Lead Ads"},
    )
    assert unmatched.status_code == 201, unmatched.text
    assert unmatched.json()["ingest_status"] == "unmatched"

    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    kpis = listed.json()["kpis"]
    assert kpis["failed"] >= 1
    assert kpis["unmatched"] >= 1
    db.expire_all()
    stored = list(db.scalars(select(Lead).where(Lead.provider.in_(["meta", "google"]))).all())
    assert len(stored) >= 2
    assert all(row.archived_at is None for row in stored)
