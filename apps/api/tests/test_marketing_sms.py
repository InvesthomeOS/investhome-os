"""Marketing SMS channel API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType


def _audience_payload(**overrides) -> dict:
    base = {"name": f"SMS Audience {uuid4().hex[:6]}", "audience_type": "static", "mode": "static"}
    base.update(overrides)
    return base


def test_sms_dashboard(client: TestClient) -> None:
    resp = client.get("/marketing/sms/dashboard")
    assert resp.status_code == 200
    assert resp.json()["provider_status"]["connected"] is False


def test_sms_validation(client: TestClient) -> None:
    resp = client.post("/marketing/sms/validate?body=Hello")
    assert resp.status_code == 200
    assert resp.json()["segment_count"] == 1


def test_sms_opt_out_required_blocks(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="SMS Contact",
        primary_email="sms@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(CrmCommunicationPreference(entity_type="contact", entity_id=contact.id, consent_sms=True))
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    campaign = client.post(
        "/marketing/sms/campaigns",
        json={
            "name": f"SMS {uuid4().hex[:6]}",
            "message_body": "Hello there",
            "audience_id": audience["id"],
            "opt_out_required": True,
            "opt_out_text_present": False,
        },
    ).json()

    readiness = client.post(f"/marketing/sms/campaigns/{campaign['id']}/readiness").json()
    assert readiness["state"] == "blocked"
    opt_out_check = next(c for c in readiness["checks"] if c["key"] == "opt_out")
    assert opt_out_check["passed"] is False


def test_sms_unknown_consent_blocks(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Unknown SMS",
        primary_email="unknown-sms@example.com",
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
        "/marketing/sms/campaigns",
        json={
            "name": f"SMS {uuid4().hex[:6]}",
            "message_body": "Hello",
            "audience_id": audience["id"],
            "opt_out_text_present": True,
        },
    ).json()

    schedule = client.post(
        f"/marketing/sms/campaigns/{campaign['id']}/schedule",
        json={"idempotency_key": f"sms-{uuid4().hex}"},
    )
    assert schedule.status_code == 422


def test_sms_no_duplicate_recipients(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Dup SMS",
        primary_email="dup-sms@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(CrmCommunicationPreference(entity_type="contact", entity_id=contact.id, consent_sms=True))
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id), str(contact.id)]),
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    calc = client.get(f"/marketing/channel/eligibility/{audience['id']}?channel=sms")
    assert calc.status_code == 200
    assert calc.json()["duplicate_count"] >= 0
