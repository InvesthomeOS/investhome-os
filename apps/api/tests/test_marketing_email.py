"""Marketing email channel API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType


def _audience_payload(**overrides) -> dict:
    base = {"name": f"Email Audience {uuid4().hex[:6]}", "audience_type": "static", "mode": "static"}
    base.update(overrides)
    return base


def _campaign_payload(**overrides) -> dict:
    base = {"name": f"Email Campaign {uuid4().hex[:6]}", "subject": "Test Subject"}
    base.update(overrides)
    return base


def test_email_dashboard(client: TestClient) -> None:
    resp = client.get("/marketing/email/dashboard")
    assert resp.status_code == 200
    assert resp.json()["provider_status"]["connected"] is False


def test_create_email_campaign(client: TestClient) -> None:
    resp = client.post("/marketing/email/campaigns", json=_campaign_payload())
    assert resp.status_code == 201
    assert resp.json()["unsubscribe_required"] is True


def test_email_schedule_blocked_unknown_consent(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Unknown Email",
        primary_email="unknown-email@example.com",
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
        "/marketing/email/campaigns",
        json=_campaign_payload(
            audience_id=audience["id"],
            unsubscribe_link_present=True,
        ),
    ).json()

    readiness = client.post(f"/marketing/email/campaigns/{campaign['id']}/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["state"] == "blocked"

    schedule = client.post(
        f"/marketing/email/campaigns/{campaign['id']}/schedule",
        json={"idempotency_key": f"key-{uuid4().hex}"},
    )
    assert schedule.status_code == 422


def test_email_unsubscribe_required_blocks(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Granted Email",
        primary_email="granted@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    pref = CrmCommunicationPreference(
        entity_type="contact",
        entity_id=contact.id,
        consent_email=True,
        do_not_contact=False,
    )
    db.add(pref)
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    campaign = client.post(
        "/marketing/email/campaigns",
        json=_campaign_payload(
            audience_id=audience["id"],
            unsubscribe_required=True,
            unsubscribe_link_present=False,
        ),
    ).json()

    readiness = client.post(f"/marketing/email/campaigns/{campaign['id']}/readiness").json()
    assert readiness["state"] == "blocked"
    unsub_check = next(c for c in readiness["checks"] if c["key"] == "unsubscribe")
    assert unsub_check["passed"] is False


def test_email_schedule_idempotency(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Granted",
        primary_email="granted2@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(CrmCommunicationPreference(entity_type="contact", entity_id=contact.id, consent_email=True))
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    campaign = client.post(
        "/marketing/email/campaigns",
        json=_campaign_payload(
            audience_id=audience["id"],
            unsubscribe_link_present=True,
        ),
    ).json()

    key = f"email-key-{uuid4().hex}"
    first = client.post(
        f"/marketing/email/campaigns/{campaign['id']}/schedule",
        json={"idempotency_key": key},
    )
    second = client.post(
        f"/marketing/email/campaigns/{campaign['id']}/schedule",
        json={"idempotency_key": key},
    )
    assert first.status_code == 200
    assert second.json()["idempotent"] is True
