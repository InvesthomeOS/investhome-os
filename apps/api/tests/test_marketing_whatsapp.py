"""Marketing WhatsApp channel API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType


def _audience_payload(**overrides) -> dict:
    base = {"name": f"WA Audience {uuid4().hex[:6]}", "audience_type": "static", "mode": "static"}
    base.update(overrides)
    return base


def test_whatsapp_dashboard(client: TestClient) -> None:
    resp = client.get("/marketing/whatsapp/dashboard")
    assert resp.status_code == 200
    assert resp.json()["provider_status"]["connected"] is False


def test_create_whatsapp_campaign(client: TestClient) -> None:
    resp = client.post(
        "/marketing/whatsapp/campaigns",
        json={"name": f"WA Campaign {uuid4().hex[:6]}"},
    )
    assert resp.status_code == 201


def test_whatsapp_unapproved_template_blocks(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="WA Contact",
        primary_email="wa@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(CrmCommunicationPreference(entity_type="contact", entity_id=contact.id, consent_whatsapp=True))
    db.commit()

    template = client.post(
        "/marketing/whatsapp/templates",
        json={"name": f"Template {uuid4().hex[:6]}", "body_text": "Hello {{name}}"},
    ).json()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    campaign = client.post(
        "/marketing/whatsapp/campaigns",
        json={
            "name": f"WA {uuid4().hex[:6]}",
            "audience_id": audience["id"],
            "template_id": template["id"],
        },
    ).json()

    readiness = client.post(f"/marketing/whatsapp/campaigns/{campaign['id']}/readiness").json()
    assert readiness["state"] == "blocked"
    template_check = next(c for c in readiness["checks"] if c["key"] == "whatsapp_template")
    assert template_check["passed"] is False


def test_whatsapp_unknown_consent_blocks(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Unknown WA",
        primary_email="unknown-wa@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    campaign = client.post(
        "/marketing/whatsapp/campaigns",
        json={"name": f"WA {uuid4().hex[:6]}", "audience_id": audience["id"]},
    ).json()

    readiness = client.post(f"/marketing/whatsapp/campaigns/{campaign['id']}/readiness").json()
    assert readiness["state"] == "blocked"
