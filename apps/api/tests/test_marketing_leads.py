"""Marketing lead context API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.lead import Lead
from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus


def test_list_marketing_leads(client: TestClient, db: Session) -> None:
    ctx = MarketingLeadContext(handoff_status=MarketingLeadHandoffStatus.NOT_READY)
    db.add(ctx)
    db.commit()

    response = client.get("/marketing/leads")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_handoff_blocked_without_contact(client: TestClient, db: Session) -> None:
    ctx = MarketingLeadContext(handoff_status=MarketingLeadHandoffStatus.NOT_READY)
    db.add(ctx)
    db.commit()

    readiness = client.get(f"/marketing/leads/{ctx.id}/handoff-readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is False
    assert "contact_not_identified" in readiness.json()["blockers"]

    handoff = client.post(f"/marketing/leads/{ctx.id}/handoff")
    assert handoff.status_code == 409


def test_handoff_blocked_unknown_consent(client: TestClient, db: Session) -> None:
    contact = CrmContact(display_name="Lead Handoff", primary_email=f"handoff-{uuid4().hex[:6]}@example.com", contact_type=CrmContactType.PROSPECT)
    db.add(contact)
    db.flush()
    ctx = MarketingLeadContext(
        contact_id=contact.id,
        handoff_status=MarketingLeadHandoffStatus.NOT_READY,
    )
    db.add(ctx)
    db.commit()

    readiness = client.get(f"/marketing/leads/{ctx.id}/handoff-readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is False
    assert "unknown_consent" in readiness.json()["blockers"]


def test_no_duplicate_lead_identity_on_handoff(client: TestClient, db: Session) -> None:
    email = f"existing-{uuid4().hex[:6]}@example.com"
    contact = CrmContact(display_name="Existing Lead", primary_email=email, contact_type=CrmContactType.PROSPECT)
    db.add(contact)
    db.flush()
    db.add(
        CrmCommunicationPreference(
            entity_type="contact",
            entity_id=contact.id,
            consent_email=True,
            do_not_contact=False,
        )
    )
    existing_lead = Lead(full_name="Existing Lead", email=email)
    db.add(existing_lead)
    db.flush()
    ctx = MarketingLeadContext(contact_id=contact.id, handoff_status=MarketingLeadHandoffStatus.NOT_READY)
    db.add(ctx)
    db.commit()

    handoff = client.post(f"/marketing/leads/{ctx.id}/handoff")
    assert handoff.status_code == 200
    body = handoff.json()
    assert body["linked_existing"] is True
    assert body["lead_id"] == str(existing_lead.id)
