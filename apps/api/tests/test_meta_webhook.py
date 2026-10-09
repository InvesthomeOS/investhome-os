"""Meta Page / Messenger inbound webhook: handshake, signature, ingest, identity."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import Settings, get_settings, validate_meta_webhook_secrets
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.sales import SalesOpportunity
from investhome_api.services.crm import meta_webhook as meta
from investhome_api.services.crm.communication_feed import list_communication_feed
from investhome_api.services.crm.meta_webhook import FACEBOOK_PSID_KEY, INSTAGRAM_IGSID_KEY

APP_SECRET = "unit-test-meta-app-secret-32charsxxxx"
IG_APP_SECRET = "unit-test-meta-ig-app-secret-32charsxxx"
VERIFY_TOKEN = "unit-test-meta-verify-token"
PAGE_ID = "111222333444555"
IG_ACCOUNT_ID = "27943000000000001"
IG_WEBHOOK_ACCOUNT_ID = "17841411111111111"
WEBHOOK_PATH = "/webhooks/meta"


@pytest.fixture(autouse=True)
def _meta_webhook_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("META_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("META_INSTAGRAM_APP_SECRET", IG_APP_SECRET)
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("META_PAGE_ID", PAGE_ID)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", IG_ACCOUNT_ID)
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_ACCOUNT_ID", IG_WEBHOOK_ACCOUNT_ID)
    get_settings.cache_clear()
    meta.reset_meta_idempotency_for_tests()
    yield
    meta.reset_meta_idempotency_for_tests()
    get_settings.cache_clear()


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _payload(
    *,
    message_id: str,
    sender: str = "1029384756102938",
    text: str = "Merhaba",
    page_id: str = PAGE_ID,
    object_name: str = "page",
    timestamp: int = 1710000000000,
) -> dict:
    return {
        "object": object_name,
        "entry": [
            {
                "id": page_id,
                "time": timestamp,
                "messaging": [
                    {
                        "sender": {"id": sender},
                        "recipient": {"id": page_id},
                        "timestamp": timestamp,
                        "message": {"mid": message_id, "text": text},
                    }
                ],
            }
        ],
    }


def _post(
    client: TestClient,
    payload: dict,
    *,
    secret: str | None = None,
    signature: str | bool | None = True,
):
    if secret is None:
        secret = IG_APP_SECRET if str(payload.get("object") or "") == "instagram" else APP_SECRET
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if signature is True:
        headers["X-Hub-Signature-256"] = _sign(body, secret)
    elif isinstance(signature, str):
        headers["X-Hub-Signature-256"] = signature
    return client.post(WEBHOOK_PATH, content=body, headers=headers), body


def test_valid_verification_handshake_accepted(client: TestClient) -> None:
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "1234567890"},
    )
    assert response.status_code == 200
    assert response.text == "1234567890"
    assert VERIFY_TOKEN not in response.text
    assert APP_SECRET not in response.text


def test_wrong_verify_token_rejected(client: TestClient) -> None:
    response = client.get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": "not-the-token", "hub.challenge": "1234567890"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    assert "not-the-token" not in response.text
    assert VERIFY_TOKEN not in response.text


def test_invalid_signature_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id=message_id), signature="sha256=" + ("ab" * 32))
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_missing_signature_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id=message_id), signature=None)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_instagram_valid_signature_accepted(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, text="IG HMAC ok"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 1
    assert IG_APP_SECRET not in response.text
    assert APP_SECRET not in response.text


def test_instagram_invalid_signature_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(
        client,
        _ig_payload(message_id=message_id),
        signature="sha256=" + ("cd" * 32),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0
    assert IG_APP_SECRET not in response.text


def test_instagram_signed_with_facebook_secret_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id), secret=APP_SECRET)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_facebook_signed_with_instagram_secret_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id), secret=IG_APP_SECRET)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_instagram_missing_signature_rejected(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id), signature=None)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_instagram_missing_app_secret_fails_closed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("META_INSTAGRAM_APP_SECRET", raising=False)
    get_settings.cache_clear()
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id), secret=APP_SECRET)
    assert response.status_code == 503
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0
    facebook_id = f"mid.{uuid4().hex}"
    facebook_response, _ = _post(client, _payload(message_id=facebook_id))
    assert facebook_response.status_code == 200, facebook_response.text


def test_valid_messenger_text_event_accepted(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    sender = "1029384756102938"
    response, _ = _post(client, _payload(message_id=message_id, sender=sender, text="Merhaba Facebook"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["duplicate"] is False
    assert body["ingested"] == 1
    db.expire_all()
    comm = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == message_id))
    assert comm is not None
    assert comm.channel == "facebook"
    assert comm.source == "live_facebook"
    assert comm.sender_identity == sender
    assert comm.conversation_key == sender
    assert comm.body_text == "Merhaba Facebook"
    assert (comm.metadata_json or {}).get("kind") == "dm"
    assert comm.contact_id is not None


def test_wrong_page_id_ignored(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id, page_id="999888777666555"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def _ig_payload(
    *,
    message_id: str,
    sender: str = "17841400001234567",
    text: str = "Merhaba Instagram",
    account_id: str = IG_WEBHOOK_ACCOUNT_ID,
    timestamp: int = 1710000000000,
) -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": account_id,
                "time": timestamp,
                "messaging": [
                    {
                        "sender": {"id": sender},
                        "recipient": {"id": account_id},
                        "timestamp": timestamp,
                        "message": {"mid": message_id, "text": text},
                    }
                ],
            }
        ],
    }


def test_duplicate_meta_message_does_not_duplicate_communication(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    payload = _payload(message_id=message_id, text="Once only")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    db.expire_all()
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 1


def test_unknown_psid_creates_exactly_one_contact_and_lead(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    sender = "555666777888999"
    response, _ = _post(client, _payload(message_id=message_id, sender=sender))
    assert response.status_code == 200, response.text
    db.expire_all()
    contacts = list(db.scalars(select(CrmContact)).all())
    leads = list(db.scalars(select(Lead)).all())
    assert len(contacts) == 1
    assert len(leads) == 1
    contact = contacts[0]
    lead = leads[0]
    assert (contact.metadata_json or {}).get(FACEBOOK_PSID_KEY) == sender
    assert contact.source == "facebook"
    assert lead.source == "facebook"
    assert lead.provider == "facebook"
    assert contact.lead_id == lead.id
    assert list(db.scalars(select(SalesOpportunity).where(SalesOpportunity.lead_id == lead.id)).all()) == []


def test_webhook_retry_does_not_duplicate_contact_or_lead(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    sender = "444333222111000"
    payload = _payload(message_id=message_id, sender=sender, text="Retry")
    _post(client, payload)
    meta.reset_meta_idempotency_for_tests()
    replay, _ = _post(client, payload)
    assert replay.status_code == 200
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.external_provider_id == message_id
    )) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_existing_psid_reuses_contact_and_lead(client: TestClient, db: Session) -> None:
    sender = "777888999000111"
    first_id = f"mid.{uuid4().hex}"
    second_id = f"mid.{uuid4().hex}"
    first, _ = _post(client, _payload(message_id=first_id, sender=sender, text="One"))
    second, _ = _post(client, _payload(message_id=second_id, sender=sender, text="Two"))
    assert first.status_code == 200
    assert second.status_code == 200
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 2


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def test_followup_message_updates_existing_lead_activity(client: TestClient, db: Session) -> None:
    sender = "888999000111222"
    first_ts = 1_710_000_000_000
    second_ts = 1_710_003_600_000
    first_id = f"mid.{uuid4().hex}"
    second_id = f"mid.{uuid4().hex}"
    first, _ = _post(
        client,
        _payload(message_id=first_id, sender=sender, text="Ilk mesaj", timestamp=first_ts),
    )
    second, _ = _post(
        client,
        _payload(message_id=second_id, sender=sender, text="Ikinci mesaj", timestamp=second_ts),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    db.expire_all()
    leads = list(db.scalars(select(Lead)).all())
    contacts = list(db.scalars(select(CrmContact)).all())
    comms = list(db.scalars(select(CrmCommunication)).all())
    assert len(leads) == 1
    assert len(contacts) == 1
    assert len(comms) == 2
    lead = leads[0]
    expected = datetime.fromtimestamp(second_ts / 1000, tz=UTC)
    assert _as_utc(lead.updated_at) == expected
    meta = lead.metadata_json or {}
    assert meta.get("last_messenger_mid") == second_id
    assert meta.get("last_communication_id")
    assert all(str((row.metadata_json or {}).get("lead_id")) == str(lead.id) for row in comms)

    detail = client.get(f"/crm/leads/{lead.id}")
    assert detail.status_code == 200, detail.text
    activity = detail.json().get("activity") or []
    received = [item for item in activity if item["description"] == "crm.leads.facebook_messenger.received"]
    assert len(received) == 2
    previews = {str((item.get("metadata") or {}).get("preview") or "") for item in received}
    assert "Ilk mesaj" in previews
    assert "Ikinci mesaj" in previews
    latest = received[0]
    assert latest["metadata"]["mid"] == second_id
    assert _as_utc(datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))) == expected

    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    card = next(item for item in listed.json()["items"] if item["id"] == str(lead.id))
    assert _as_utc(datetime.fromisoformat(card["updated_at"].replace("Z", "+00:00"))) == expected

    pipeline = client.get("/crm/leads", params={"surface": "pipeline"})
    assert pipeline.status_code == 200
    assert all(item["id"] != str(lead.id) for item in pipeline.json()["items"])
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0

    feed = list_communication_feed(db, channel="facebook", page=1, page_size=25)
    facebook_rows = [
        item
        for item in feed.items
        if item.channel == "facebook" and item.preview and item.preview in {"Ilk mesaj", "Ikinci mesaj"}
    ]
    assert len(facebook_rows) == 2


def test_no_opportunity_created(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _payload(message_id=message_id))
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_facebook_communication_appears_in_feed_contract(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id, text="Feed check"))
    assert response.status_code == 200, response.text
    db.expire_all()
    feed = list_communication_feed(db, channel="facebook", page=1, page_size=25)
    facebook_rows = [
        item
        for item in feed.items
        if item.channel == "facebook" and item.preview and "Feed check" in item.preview
    ]
    assert len(facebook_rows) == 1
    assert feed.stats.facebook >= 1


def test_facebook_inbound_is_lead_not_pipeline(client: TestClient, db: Session) -> None:
    sender = "3210987654321098"
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id, sender=sender, text="Pipeline olmasin"))
    assert response.status_code == 200, response.text
    db.expire_all()
    leads = list(db.scalars(select(Lead)).all())
    assert len(leads) == 1
    lead_id = str(leads[0].id)
    listed = client.get("/crm/leads")
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == lead_id for item in listed.json()["items"])
    pipeline = client.get("/crm/leads", params={"surface": "pipeline"})
    assert pipeline.status_code == 200, pipeline.text
    assert all(item["id"] != lead_id for item in pipeline.json()["items"])
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_production_missing_webhook_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    monkeypatch.delenv("META_VERIFY_TOKEN", raising=False)
    monkeypatch.delenv("META_PAGE_ID", raising=False)
    settings = Settings(
        _env_file=None,
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
        COMMUNICATION_CREDENTIAL_KEY="unit-test-communication-credential-key-32b",
    )
    with pytest.raises(RuntimeError, match="META_APP_SECRET"):
        validate_meta_webhook_secrets(settings)


def test_instagram_inbound_creates_contact_and_lead(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    sender = "17841400001234567"
    response, _ = _post(client, _ig_payload(message_id=message_id, sender=sender, text="Merhaba Instagram"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["ingested"] == 1
    db.expire_all()
    contacts = list(db.scalars(select(CrmContact)).all())
    leads = list(db.scalars(select(Lead)).all())
    comms = list(db.scalars(select(CrmCommunication)).all())
    assert len(contacts) == 1
    assert len(leads) == 1
    assert len(comms) == 1
    contact = contacts[0]
    lead = leads[0]
    comm = comms[0]
    assert (contact.metadata_json or {}).get(INSTAGRAM_IGSID_KEY) == sender
    assert contact.source == "instagram"
    assert lead.source == "instagram"
    assert lead.provider == "instagram"
    assert (lead.metadata_json or {}).get("intake") == "instagram_dm"
    assert contact.lead_id == lead.id
    assert comm.channel == "instagram"
    assert comm.source == "live_instagram"
    assert comm.direction == "inbound"
    assert comm.conversation_key == sender
    assert comm.external_provider_id == message_id
    assert (comm.metadata_json or {}).get("lead_id") == str(lead.id)
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    pipeline = client.get("/crm/leads", params={"surface": "pipeline"})
    assert pipeline.status_code == 200
    assert all(item["id"] != str(lead.id) for item in pipeline.json()["items"])
    feed = list_communication_feed(db, channel="instagram", page=1, page_size=25)
    rows = [item for item in feed.items if item.channel == "instagram" and item.preview and "Merhaba Instagram" in item.preview]
    assert len(rows) == 1
    assert rows[0].can_reply is True


def test_instagram_repeat_message_updates_same_lead(client: TestClient, db: Session) -> None:
    sender = "17841400007654321"
    first_ts = 1_710_000_000_000
    second_ts = 1_710_003_600_000
    first_id = f"mid.{uuid4().hex}"
    second_id = f"mid.{uuid4().hex}"
    first, _ = _post(client, _ig_payload(message_id=first_id, sender=sender, text="Ilk IG", timestamp=first_ts))
    second, _ = _post(client, _ig_payload(message_id=second_id, sender=sender, text="Ikinci IG", timestamp=second_ts))
    assert first.status_code == 200
    assert second.status_code == 200
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 2
    lead = db.scalar(select(Lead))
    expected = datetime.fromtimestamp(second_ts / 1000, tz=UTC)
    assert _as_utc(lead.updated_at) == expected
    assert (lead.metadata_json or {}).get("last_instagram_mid") == second_id
    detail = client.get(f"/crm/leads/{lead.id}")
    received = [item for item in (detail.json().get("activity") or []) if item["description"] == "crm.leads.instagram_dm.received"]
    assert len(received) == 2
    pipeline = client.get("/crm/leads", params={"surface": "pipeline"})
    assert all(item["id"] != str(lead.id) for item in pipeline.json()["items"])
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="instagram", page=1, page_size=25)
    rows = [item for item in feed.items if item.channel == "instagram" and item.preview in {"Ilk IG", "Ikinci IG"}]
    assert len(rows) == 2


def test_instagram_duplicate_webhook_does_not_duplicate(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    payload = _ig_payload(message_id=message_id, text="Once IG")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.external_provider_id == message_id
    )) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_instagram_comments_payload_is_not_ingested(client: TestClient, db: Session) -> None:
    payload = {
        "object": "instagram",
        "entry": [{"id": IG_WEBHOOK_ACCOUNT_ID, "changes": [{"field": "comments", "value": {"text": "yorum"}}]}],
    }
    response, _ = _post(client, payload)
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_instagram_unknown_account_is_ignored_with_safe_log(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    parsed_account_id = "17841422222222222"
    sender = "17841400009876543"
    text = "SECRET_IG_MESSAGE_TEXT_SHOULD_NOT_LOG"
    message_id = f"mid.{uuid4().hex}"
    caplog.set_level("INFO", logger="investhome.meta.webhook")
    response, _ = _post(
        client,
        _ig_payload(message_id=message_id, sender=sender, text=text, account_id=parsed_account_id),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "meta_webhook_unknown_instagram_account" in joined
    assert "parsed_account_id=" not in joined
    assert "configured_account_id=" not in joined
    assert parsed_account_id not in joined
    assert IG_WEBHOOK_ACCOUNT_ID not in joined
    assert IG_ACCOUNT_ID not in joined
    assert text not in joined
    assert sender not in joined
    assert APP_SECRET not in joined
    assert IG_APP_SECRET not in joined
    assert "X-Hub-Signature-256" not in joined
    assert "sha256=" not in joined


def test_instagram_matching_account_still_ingested(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, account_id=IG_WEBHOOK_ACCOUNT_ID))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.external_provider_id == message_id
    )) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_instagram_login_account_id_is_not_used_for_inbound(
    client: TestClient, db: Session
) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, account_id=IG_ACCOUNT_ID))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_instagram_missing_webhook_account_id_skips_safely(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("META_INSTAGRAM_WEBHOOK_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", IG_WEBHOOK_ACCOUNT_ID)
    get_settings.cache_clear()
    caplog.set_level("WARNING", logger="investhome.meta.webhook")
    text = "SECRET_IG_SKIP_TEXT_SHOULD_NOT_LOG"
    sender = "17841400001234999"
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(
        client,
        _ig_payload(message_id=message_id, sender=sender, text=text, account_id=IG_WEBHOOK_ACCOUNT_ID),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 0
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "meta_webhook_missing_instagram_webhook_account_id" in joined
    assert text not in joined
    assert sender not in joined
    facebook_id = f"mid.{uuid4().hex}"
    facebook_response, _ = _post(client, _payload(message_id=facebook_id))
    assert facebook_response.status_code == 200, facebook_response.text
    assert facebook_response.json()["ingested"] == 1
