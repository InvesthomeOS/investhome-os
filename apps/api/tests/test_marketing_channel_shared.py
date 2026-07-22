"""Shared marketing channel API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType


def test_provider_statuses_honest(client: TestClient) -> None:
    resp = client.get("/marketing/channel/provider-status")
    assert resp.status_code == 200
    statuses = resp.json()
    assert len(statuses) >= 1
    for item in statuses:
        assert item["connected"] is False


def test_frequency_policy_crud(client: TestClient) -> None:
    created = client.post(
        "/marketing/channel/frequency-policies",
        json={
            "name": f"Policy {uuid4().hex[:6]}",
            "channel": "email",
            "max_messages_per_day": 2,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "timezone": "UTC",
        },
    )
    assert created.status_code == 201
    listed = client.get("/marketing/channel/frequency-policies?channel=email")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_personalization_preview(client: TestClient) -> None:
    resp = client.post(
        "/marketing/channel/personalization/preview",
        json={"config": {"body_template": "Hello {{first_name}}"}, "sample_contact": {"first_name": "Alex"}},
    )
    assert resp.status_code == 200
    assert "Alex" in resp.json()["preview"]


def test_opt_out_updates_crm(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Opt Out Test",
        primary_email="optout@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(CrmCommunicationPreference(entity_type="contact", entity_id=contact.id, consent_email=True))
    db.commit()

    resp = client.post(
        "/marketing/channel/opt-out",
        json={"contact_id": str(contact.id), "channel": "email"},
    )
    assert resp.status_code == 200
    assert resp.json()["consent"] == "denied"

    db.expire_all()
    pref = db.scalar(
        select(CrmCommunicationPreference).where(
            CrmCommunicationPreference.entity_id == contact.id,
            CrmCommunicationPreference.entity_type == "contact",
        )
    )
    assert pref is not None
    assert pref.consent_email is False


def test_suppression_blocks_eligibility(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        display_name="Suppressed",
        primary_email="suppressed@example.com",
        contact_type=CrmContactType.PROSPECT,
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmCommunicationPreference(
            entity_type="contact",
            entity_id=contact.id,
            consent_email=True,
            do_not_contact=True,
        )
    )
    db.commit()

    audience = client.post(
        "/marketing/audiences",
        json={
            "name": f"Suppressed {uuid4().hex[:6]}",
            "audience_type": "static",
            "mode": "static",
            "contact_ids": [str(contact.id)],
        },
    ).json()
    client.post(f"/marketing/audiences/{audience['id']}/refresh")

    calc = client.get(f"/marketing/channel/eligibility/{audience['id']}?channel=email")
    assert calc.status_code == 200
    assert calc.json()["eligible"] == 0
