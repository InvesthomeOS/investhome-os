"""Public WordPress website form HMAC ingest into live CRM leads/contacts."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.sales import SalesOpportunity
from investhome_api.services.website_form_auth import (
    NONCE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    reset_website_form_replay_for_tests,
)

SECRET = "unit-test-website-form-ingest-secret-32"
PATH = "/public/website/forms/submit"


@pytest.fixture(autouse=True)
def _website_form_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WEBSITE_FORM_INGEST_SECRET", SECRET)
    get_settings.cache_clear()
    reset_website_form_replay_for_tests()
    yield
    reset_website_form_replay_for_tests()
    get_settings.cache_clear()


def _payload(**overrides) -> dict:
    body = {
        "full_name": "Ayşe Yılmaz",
        "phone": "05551234567",
        "email": f"website.{uuid4().hex[:10]}@example.com",
        "kvkk_accepted": True,
        "occupation": "Mühendis",
        "message": "1812 H Place için bilgi almak istiyorum.",
        "page_url": "https://investhome.com/iletisim",
        "page_title": "İletişim",
        "project": "1812 H Place",
        "form_type": "general_contact",
        "referrer": "https://www.google.com/",
        "utm_source": "google",
        "utm_medium": "organic",
        "utm_campaign": "brand",
        "language": "tr",
        "idempotency_key": f"wp-{uuid4().hex}",
    }
    body.update(overrides)
    return body


def _sign(raw: bytes, *, timestamp: str, nonce: str, secret: str = SECRET) -> str:
    material = f"{timestamp}.{nonce}.".encode("utf-8") + raw
    return hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


def _post(
    client: TestClient,
    payload: dict,
    *,
    secret: str = SECRET,
    timestamp: str | None = None,
    nonce: str | None = None,
    signature: str | bool | None = True,
):
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ts = timestamp if timestamp is not None else str(int(time.time()))
    nonce_value = nonce if nonce is not None else uuid4().hex
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if ts:
        headers[TIMESTAMP_HEADER] = ts
    if nonce_value:
        headers[NONCE_HEADER] = nonce_value
    if signature is True:
        headers[SIGNATURE_HEADER] = _sign(raw, timestamp=ts, nonce=nonce_value, secret=secret)
    elif isinstance(signature, str):
        headers[SIGNATURE_HEADER] = signature
    return client.post(PATH, content=raw, headers=headers), raw


def test_new_person_creates_contact_and_lead(client: TestClient, db: Session) -> None:
    payload = _payload()
    response, _raw = _post(client, payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["accepted"] is True
    assert body["duplicate"] is False
    assert body["matched_existing"] is False
    assert body["inquiry_id"]
    assert response.headers.get("x-request-id") or body.get("request_id")

    db.expire_all()
    lead = db.get(Lead, UUID(body["inquiry_id"]))
    assert lead is not None
    assert lead.status == LeadStatus.NEW
    assert lead.source == "website"
    assert lead.provider == "website"
    assert list(db.scalars(select(SalesOpportunity).where(SalesOpportunity.lead_id == lead.id)).all()) == []
    assert lead.assigned_manager_id is None
    meta = lead.metadata_json or {}
    assert meta["source_label"] == "Web Site Form"
    assert meta["kvkk_accepted"] is True
    assert "1812 H Place" in (lead.notes or "")

    pipeline = client.get("/crm/leads", params={"surface": "pipeline"})
    assert pipeline.status_code == 200, pipeline.text
    assert any(item["id"] == str(lead.id) for item in pipeline.json()["items"])

    contacts = list(db.scalars(select(CrmContact).where(CrmContact.primary_email == payload["email"])).all())
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact.display_name == "Ayşe Yılmaz"
    assert contact.job_title == "Mühendis"
    assert contact.source == "website"
    assert contact.compliance_data["kvkk_accepted"] is True
    assert contact.owner_user_id is None
    activities = list(
        db.scalars(select(ActivityLog).where(ActivityLog.entity_id == contact.id)).all()
    )
    assert any(row.entity_type == ActivityEntityType.CRM_CONTACT for row in activities)


def test_existing_email_matches_and_does_not_duplicate_contact(client: TestClient, db: Session) -> None:
    email = f"match.{uuid4().hex[:10]}@example.com"
    first, _ = _post(client, _payload(email=email, phone="05551112233", occupation="Avukat"))
    assert first.status_code == 201, first.text
    second, _ = _post(
        client,
        _payload(
            email=email,
            phone="05551112233",
            full_name="Should Not Overwrite",
            occupation=None,
            message="İkinci başvuru",
        ),
    )
    assert second.status_code == 201, second.text
    assert second.json()["matched_existing"] is True
    assert second.json()["inquiry_id"] != first.json()["inquiry_id"]

    db.expire_all()
    contacts = list(db.scalars(select(CrmContact).where(CrmContact.primary_email == email)).all())
    assert len(contacts) == 1
    assert contacts[0].display_name == "Ayşe Yılmaz"
    assert contacts[0].job_title == "Avukat"
    leads = list(db.scalars(select(Lead).where(Lead.email == email)).all())
    assert len(leads) == 2
    assert all(row.status == LeadStatus.NEW for row in leads)


def test_existing_phone_match_adds_secondary_email(client: TestClient, db: Session) -> None:
    phone = "05339876543"
    first_email = f"phone1.{uuid4().hex[:8]}@example.com"
    second_email = f"phone2.{uuid4().hex[:8]}@example.com"
    first, _ = _post(client, _payload(email=first_email, phone=phone))
    assert first.status_code == 201, first.text
    second, _ = _post(client, _payload(email=second_email, phone=phone, full_name="Ayşe Yılmaz"))
    assert second.status_code == 201, second.text
    assert second.json()["matched_existing"] is True
    db.expire_all()
    contacts = list(db.scalars(select(CrmContact)).all())
    matched = [row for row in contacts if row.primary_email == first_email]
    assert len(matched) == 1
    assert second_email in (matched[0].secondary_emails or [])
    assert matched[0].primary_email == first_email


def test_kvkk_false_rejected(client: TestClient, db: Session) -> None:
    response, _ = _post(client, _payload(kvkk_accepted=False))
    assert response.status_code == 422
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_invalid_signature_rejected(client: TestClient, db: Session) -> None:
    response, _ = _post(client, _payload(), signature="ab" * 32)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_missing_signature_rejected(client: TestClient, db: Session) -> None:
    response, _ = _post(client, _payload(), signature=None)
    assert response.status_code == 403
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_missing_secret_fails_closed(client: TestClient, monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    monkeypatch.setenv("WEBSITE_FORM_INGEST_SECRET", "")
    get_settings.cache_clear()
    response, _ = _post(client, _payload())
    assert response.status_code == 503
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_nonce_replay_rejected(client: TestClient, db: Session) -> None:
    payload = _payload()
    nonce = uuid4().hex
    timestamp = str(int(time.time()))
    first, _ = _post(client, payload, nonce=nonce, timestamp=timestamp)
    assert first.status_code == 201, first.text
    second, _ = _post(client, payload, nonce=nonce, timestamp=timestamp)
    assert second.status_code == 409
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1


def test_idempotency_replay_does_not_create_second_lead(client: TestClient, db: Session) -> None:
    payload = _payload()
    first, _ = _post(client, payload)
    assert first.status_code == 201, first.text
    second, _ = _post(client, payload)
    assert second.status_code == 201, second.text
    assert second.json()["duplicate"] is True
    assert second.json()["inquiry_id"] == first.json()["inquiry_id"]
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1


def test_stale_timestamp_rejected(client: TestClient, db: Session) -> None:
    response, _ = _post(client, _payload(), timestamp=str(int(time.time()) - 10_000))
    assert response.status_code == 403
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_invalid_email_rejected(client: TestClient) -> None:
    response, _ = _post(client, _payload(email="not-an-email"))
    assert response.status_code == 422


def test_extra_fields_rejected(client: TestClient) -> None:
    response, _ = _post(client, _payload(bitrix_id="66"))
    assert response.status_code == 422


def test_response_does_not_expose_crm_records(client: TestClient) -> None:
    response, _ = _post(client, _payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) <= {"accepted", "duplicate", "matched_existing", "inquiry_id", "request_id"}
    assert "email" not in body
    assert "phone" not in body
    assert "contact_id" not in body
    assert "matches" not in body


def test_get_not_allowed(client: TestClient) -> None:
    response = client.get(PATH)
    assert response.status_code == 405


def test_rate_limit_blocks_bursts(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_FORM_BURST_LIMIT", "2")
    get_settings.cache_clear()
    assert _post(client, _payload())[0].status_code == 201
    assert _post(client, _payload())[0].status_code == 201
    limited, _ = _post(client, _payload())
    assert limited.status_code == 429
