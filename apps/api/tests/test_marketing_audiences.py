"""Marketing audience API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType


def _audience_payload(**overrides) -> dict:
    base = {
        "name": f"Test Audience {uuid4().hex[:6]}",
        "audience_type": "static",
        "mode": "static",
    }
    base.update(overrides)
    return base


def test_create_audience(client: TestClient) -> None:
    response = client.post("/marketing/audiences", json=_audience_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["mode"] == "static"


def test_list_audiences_with_summary(client: TestClient) -> None:
    client.post("/marketing/audiences", json=_audience_payload())
    list_resp = client.get("/marketing/audiences?page=1&page_size=10")
    assert list_resp.status_code == 200
    summary_resp = client.get("/marketing/audiences/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["total"] >= 1


def test_audience_member_consent_blocking(client: TestClient, db: Session) -> None:
    contact = CrmContact(display_name="Consent Test", primary_email="consent-test@example.com", contact_type=CrmContactType.PROSPECT)
    db.add(contact)
    db.flush()
    pref = CrmCommunicationPreference(
        entity_type="contact",
        entity_id=contact.id,
        consent_email=None,
        do_not_contact=False,
    )
    db.add(pref)
    db.commit()

    created = client.post(
        "/marketing/audiences",
        json=_audience_payload(contact_ids=[str(contact.id)]),
    ).json()
    audience_id = created["id"]
    refresh = client.post(f"/marketing/audiences/{audience_id}/refresh")
    assert refresh.status_code == 200

    members = client.get(f"/marketing/audiences/{audience_id}/members").json()
    assert members["total"] >= 1
    member = members["items"][0]
    assert member["is_included"] is False
    assert member["exclusion_reason"] == "consent"


def test_audience_readiness_unknown_consent(client: TestClient, db: Session) -> None:
    contact = CrmContact(display_name="Unknown Consent", primary_email="unknown@example.com", contact_type=CrmContactType.PROSPECT)
    db.add(contact)
    db.commit()

    created = client.post(
        "/marketing/audiences",
        json=_audience_payload(
            contact_ids=[str(contact.id)],
            consent_requirements_json={"channels": ["email"]},
        ),
    ).json()
    audience_id = created["id"]
    client.post(f"/marketing/audiences/{audience_id}/refresh")
    readiness = client.get(f"/marketing/audiences/{audience_id}/readiness")
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["state"] in ("blocked", "not_calculated", "warning")


def test_duplicate_audience(client: TestClient) -> None:
    created = client.post("/marketing/audiences", json=_audience_payload()).json()
    dup = client.post(f"/marketing/audiences/{created['id']}/duplicate")
    assert dup.status_code == 200
    assert dup.json()["name"].endswith("(Copy)")


def test_audience_permissions_required(auth_client: TestClient) -> None:
    response = auth_client.get("/marketing/audiences")
    assert response.status_code == 401
