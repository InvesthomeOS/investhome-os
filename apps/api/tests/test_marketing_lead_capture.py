"""Marketing lead capture API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.lead import Lead
from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus
from investhome_api.models.marketing_landing_conversion import MarketingLeadRoutingRule


def test_lead_capture_dashboard(client: TestClient) -> None:
    response = client.get("/marketing/lead-capture/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"] == "not_connected"


def test_routing_fallback(client: TestClient, db: Session) -> None:
    fallback = MarketingLeadRoutingRule(
        name="Fallback",
        is_fallback=True,
        is_active=True,
        action_json={"assign_team": "default"},
    )
    db.add(fallback)
    db.commit()

    rules = client.get("/marketing/lead-capture/routing")
    assert rules.status_code == 200
    assert any(r["is_fallback"] for r in rules.json())


def test_create_routing_rule(client: TestClient) -> None:
    response = client.post(
        "/marketing/lead-capture/routing",
        json={"name": "UTM Rule", "priority": 10, "conditions_json": {"utm_source": "google"}},
    )
    assert response.status_code == 201


def test_handoff_readiness_blocked(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Handoff Test",
        primary_email=f"handoff-{uuid4().hex[:6]}@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    ctx = MarketingLeadContext(contact_id=contact.id, handoff_status=MarketingLeadHandoffStatus.NOT_READY)
    db.add(ctx)
    db.commit()

    handoff = client.post(f"/marketing/lead-capture/handoff/{ctx.id}")
    assert handoff.status_code == 201
    assert handoff.json()["status"] == "blocked"


def test_no_duplicate_sales_lead_on_handoff(client: TestClient, db: Session) -> None:
    email = f"sales-dup-{uuid4().hex[:6]}@example.com"
    contact = CrmContact(display_name="Sales Dup", primary_email=email, contact_type=CrmContactType.PROSPECT)
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
    existing_lead = Lead(full_name="Sales Dup", email=email)
    db.add(existing_lead)
    db.flush()
    ctx = MarketingLeadContext(contact_id=contact.id, handoff_status=MarketingLeadHandoffStatus.NOT_READY)
    db.add(ctx)
    db.commit()

    sales_handoff = client.post(f"/marketing/leads/{ctx.id}/handoff")
    assert sales_handoff.status_code == 200
    assert sales_handoff.json()["linked_existing"] is True


def test_handoff_slas(client: TestClient) -> None:
    response = client.get("/marketing/lead-capture/slas")
    assert response.status_code == 200
    assert len(response.json()) >= 1
