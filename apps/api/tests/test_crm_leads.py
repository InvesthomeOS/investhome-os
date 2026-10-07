"""CRM operational leads workspace tests — live table only, no demo seed."""

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.services.crm.crm_lead_service import LeadValidationError, parse_investment_budget_amount


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
    assert lead["investment_budget_amount"] is None
    assert lead["investment_budget_currency"] is None
    lead_id = lead["id"]
    contact_id = lead["contact_id"]
    assert contact_id
    people = client.get("/crm/contacts", params={"search": "ayse.lead@example.com"})
    assert people.status_code == 200
    assert any(item["id"] == contact_id for item in people.json()["items"])

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
    assert lead["contact_id"] == str(person.id)
    people_before = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    retry = client.post(
        "/crm/leads?confirm=true",
        json={
            "full_name": "New Duplicate",
            "email": "existing.person@example.com",
            "source": "manual",
        },
    )
    assert retry.status_code == 409, retry.text
    assert retry.json()["error"]["code"] == "existing_lead"

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
    created_body = created.json()
    lead_id = created_body["id"]
    created_contact_id = created_body["contact_id"]
    assert created_contact_id

    converted = client.post(f"/crm/leads/{lead_id}/convert")
    assert converted.status_code == 200, converted.text
    body = converted.json()
    assert body["reused_existing"] is True
    assert body["contact_id"] == created_contact_id
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


def _money(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def test_parse_investment_budget_normalizes_user_entry() -> None:
    assert parse_investment_budget_amount("500000") == Decimal("500000.00")
    assert parse_investment_budget_amount("500,000") == Decimal("500000.00")
    assert parse_investment_budget_amount("$500,000") == Decimal("500000.00")
    assert parse_investment_budget_amount("500000.50") == Decimal("500000.50")
    with pytest.raises(LeadValidationError):
        parse_investment_budget_amount(-1)
    with pytest.raises(LeadValidationError):
        parse_investment_budget_amount(12.5)


def test_manual_lead_creates_and_lists_new_contact(client: TestClient, db: Session) -> None:
    people_before = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Yeni Kişi Lead",
            "phone": "+90 555 444 33 22",
            "email": "yeni.kisi.lead@example.com",
            "source": "manual",
        },
    )
    assert created.status_code == 201, created.text
    lead = created.json()
    contact_id = lead["contact_id"]
    assert contact_id
    assert lead["contact_name"] == "Yeni Kişi Lead"
    assert lead["existing_person_id"] == contact_id
    db.expire_all()
    contact = db.get(CrmContact, UUID(contact_id))
    assert contact is not None
    assert contact.lead_id == UUID(lead["id"])
    assert contact.archived_at is None
    people_after = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    assert people_after == people_before + 1
    listed = client.get("/crm/contacts", params={"search": "yeni.kisi.lead@example.com"})
    assert listed.status_code == 200
    assert any(item["id"] == contact_id for item in listed.json()["items"])
    detail = client.get(f"/crm/contacts/{contact_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == contact_id
    retry = client.post(
        "/crm/leads",
        json={
            "full_name": "Yeni Kişi Lead",
            "email": "yeni.kisi.lead@example.com",
            "source": "manual",
        },
    )
    assert retry.status_code == 409, retry.text
    assert retry.json()["error"]["code"] == "existing_lead"
    db.expire_all()
    assert (db.scalar(select(func.count()).select_from(CrmContact)) or 0) == people_after


def test_linked_lead_exposes_canonical_contact_name_after_rename(client: TestClient, db: Session) -> None:
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Test Test Person",
            "phone": "+90 555 444 22 11",
            "email": "canonical.rename@example.com",
            "source": "manual",
        },
    )
    assert created.status_code == 201, created.text
    lead = created.json()
    contact_id = lead["contact_id"]
    assert lead["full_name"] == "Test Test Person"
    assert lead["contact_name"] == "Test Test Person"

    renamed = client.put(
        f"/crm/contacts/{contact_id}",
        json={"display_name": "Test Person", "first_name": "Test", "last_name": "Person"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["contact"]["display_name"] == "Test Person"

    refreshed = client.get(f"/crm/leads/{lead['id']}")
    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["full_name"] == "Test Test Person"
    assert body["contact_name"] == "Test Person"
    assert body["contact_id"] == contact_id


def test_manual_lead_reuses_matching_contact(client: TestClient, db: Session) -> None:
    person = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        record_kind=CrmRecordKind.PERSON,
        display_name="Mevcut Yatırımcı",
        status=CrmContactStatus.ACTIVE,
        primary_email="mevcut.yatirimci@example.com",
        primary_phone="+905559998877",
    )
    db.add(person)
    db.commit()
    people_before = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    conflict = client.post(
        "/crm/leads",
        json={
            "full_name": "Mevcut Yatırımcı",
            "email": "mevcut.yatirimci@example.com",
            "phone": "+90 555 999 88 77",
            "source": "manual",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "existing_person"
    confirmed = client.post(
        "/crm/leads?confirm=true",
        json={
            "full_name": "Mevcut Yatırımcı",
            "email": "mevcut.yatirimci@example.com",
            "phone": "+90 555 999 88 77",
            "source": "manual",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    body = confirmed.json()
    assert body["contact_id"] == str(person.id)
    db.expire_all()
    assert (db.scalar(select(func.count()).select_from(CrmContact)) or 0) == people_before
    linked = db.get(CrmContact, person.id)
    assert linked is not None
    assert linked.lead_id == UUID(body["id"])


def test_manual_lead_ambiguous_person_is_not_silently_merged(client: TestClient, db: Session) -> None:
    for name in ("Kişi Bir", "Kişi İki"):
        db.add(
            CrmContact(
                contact_type=CrmContactType.PROSPECT,
                record_kind=CrmRecordKind.PERSON,
                display_name=name,
                status=CrmContactStatus.ACTIVE,
                primary_email="paylasilan.email@example.com",
            )
        )
    db.commit()
    people_before = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    conflict = client.post(
        "/crm/leads?confirm=true",
        json={
            "full_name": "Belirsiz Kişi",
            "email": "paylasilan.email@example.com",
            "source": "manual",
        },
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "ambiguous_person"
    db.expire_all()
    assert (db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert (db.scalar(select(func.count()).select_from(CrmContact)) or 0) == people_before


def test_crm_lead_investment_budget_persists_and_survives_edit(client: TestClient, db: Session) -> None:
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Bütçeli Lead",
            "email": "butceli.lead@example.com",
            "source": "manual",
            "investment_budget_amount": "$500,000",
            "investment_budget_currency": "usd",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert _money(body["investment_budget_amount"]) == Decimal("500000.00")
    assert body["investment_budget_currency"] == "USD"
    db.expire_all()
    row = db.get(Lead, UUID(body["id"]))
    assert row is not None
    assert row.estimated_budget == Decimal("500000.00")
    assert row.estimated_budget_currency == "USD"
    refreshed = client.get(f"/crm/leads/{body['id']}")
    assert refreshed.status_code == 200
    assert _money(refreshed.json()["investment_budget_amount"]) == Decimal("500000.00")
    assert refreshed.json()["investment_budget_currency"] == "USD"
    patched = client.patch(
        f"/crm/leads/{body['id']}",
        json={"investment_budget_amount": "500,000", "investment_budget_currency": "USD"},
    )
    assert patched.status_code == 200, patched.text
    assert _money(patched.json()["investment_budget_amount"]) == Decimal("500000.00")
    listed = client.get("/crm/leads")
    match = next(item for item in listed.json()["items"] if item["id"] == body["id"])
    assert _money(match["investment_budget_amount"]) == Decimal("500000.00")
    assert match["investment_budget_currency"] == "USD"


def test_crm_lead_without_investment_budget_still_creates(client: TestClient) -> None:
    created = client.post(
        "/crm/leads",
        json={"full_name": "Bütçesiz Lead", "email": "butcesiz.lead@example.com", "source": "manual"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["investment_budget_amount"] is None
    assert body["investment_budget_currency"] is None
    assert body["contact_id"]


def test_existing_lead_without_budget_currency_remains_valid(client: TestClient, db: Session) -> None:
    lead = Lead(
        full_name="Eski Lead",
        email="eski.lead@example.com",
        status=LeadStatus.NEW,
        ingest_status="ok",
        estimated_budget=Decimal("100000.00"),
        is_demo=False,
    )
    db.add(lead)
    db.commit()
    response = client.get(f"/crm/leads/{lead.id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert _money(body["investment_budget_amount"]) == Decimal("100000.00")
    assert body["investment_budget_currency"] is None
    listed = client.get("/crm/leads")
    assert any(item["id"] == str(lead.id) for item in listed.json()["items"])


def test_crm_lead_rejects_float_investment_budget(client: TestClient) -> None:
    response = client.post(
        "/crm/leads",
        json={
            "full_name": "Float Budget",
            "email": "float.budget@example.com",
            "source": "manual",
            "investment_budget_amount": 500000.25,
        },
    )
    assert response.status_code == 422
