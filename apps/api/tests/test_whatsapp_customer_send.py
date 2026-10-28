"""WhatsApp Cloud API customer replies, CRM persistence, and delivery statuses."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import CrmCommunication, CrmCommunicationAuditLog
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.crm import whatsapp_webhook as wa
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm.whatsapp_cloud import WhatsAppCloudError

SEND_PATH = "/crm/live-communications/whatsapp/send"
WEBHOOK_PATH = "/webhooks/whatsapp"
TOKEN = "unit-test-whatsapp-access-token-do-not-log"
PHONE_NUMBER_ID = "109876543210123"
APP_SECRET = "unit-test-whatsapp-app-secret-32chars"
VERIFY_TOKEN = "unit-test-whatsapp-verify-token"


class RecordingClient:
    calls: list[dict[str, str]] = []

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        graph_api_version: str,
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.graph_api_version = graph_api_version

    def send_text(self, *, to: str, body: str) -> str:
        wamid = f"wamid.out.{uuid4().hex}"
        RecordingClient.calls.append(
            {
                "access_token": self.access_token,
                "phone_number_id": self.phone_number_id,
                "to": to,
                "body": body,
                "wamid": wamid,
            }
        )
        return wamid


@pytest.fixture(autouse=True)
def _whatsapp_send_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", PHONE_NUMBER_ID)
    monkeypatch.setenv("WHATSAPP_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    get_settings.cache_clear()
    wa.reset_whatsapp_idempotency_for_tests()
    RecordingClient.calls = []
    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_send.WhatsAppCloudClient",
        RecordingClient,
    )
    yield
    wa.reset_whatsapp_idempotency_for_tests()
    get_settings.cache_clear()


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200, response.text


def _user(db: Session, email: str) -> User:
    row = db.scalar(select(User).where(User.email == email))
    assert row is not None
    return row


def _contact(
    db: Session,
    *,
    phone: str | None,
    secondary: list[str] | None = None,
    name: str = "Ada",
) -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        primary_phone=phone,
        secondary_phones=secondary,
        status=CrmContactStatus.ACTIVE,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _count(db: Session, *, contact_id=None, wamid: str | None = None) -> int:
    query = select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.channel == "whatsapp"
    )
    if contact_id is not None:
        query = query.where(CrmCommunication.contact_id == contact_id)
    if wamid is not None:
        query = query.where(CrmCommunication.external_provider_id == wamid)
    return int(db.scalar(query) or 0)


def _outbound(db: Session, wamid: str) -> CrmCommunication:
    db.expire_all()
    row = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == wamid))
    assert row is not None
    return row


def _sign(body: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(client: TestClient, payload: dict):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )


def _status_payload(wamid: str, status: str, timestamp: int, errors: list | None = None) -> dict:
    item: dict = {
        "id": wamid,
        "status": status,
        "timestamp": str(timestamp),
        "recipient_id": "905551112233",
    }
    if errors:
        item["errors"] = errors
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {"messaging_product": "whatsapp", "statuses": [item]},
                    }
                ],
            }
        ],
    }


def test_reply_uses_cloud_api_and_keeps_one_thread(
    auth_client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    contact = _contact(db, phone="+90 555 111 22 33")
    inbound, _created = ingest_live_message(
        db,
        {
            "channel": "whatsapp",
            "direction": "incoming",
            "source": "live_whatsapp",
            "sender": "905551112233",
            "body_text": "Merhaba",
            "external_provider_id": f"wamid.in.{uuid4().hex}",
            "conversation_key": "905551112233",
            "contact_id": str(contact.id),
        },
        actor=None,
    )
    db.commit()
    with caplog.at_level(logging.INFO):
        response = auth_client.post(
            SEND_PATH,
            json={
                "contact_id": str(contact.id),
                "communication_id": str(inbound.id),
                "body_text": "Tapu durumunu paylaşıyorum",
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["channel"] == "whatsapp"
    assert body["direction"] == "outbound"
    assert body["provider_message_id"]
    assert TOKEN not in response.text
    assert TOKEN not in caplog.text
    assert len(RecordingClient.calls) == 1
    call = RecordingClient.calls[0]
    assert call["to"] == "905551112233"
    assert call["phone_number_id"] == PHONE_NUMBER_ID
    assert call["access_token"] == TOKEN
    assert call["body"] == "Tapu durumunu paylaşıyorum"
    assert _count(db, contact_id=contact.id) == 2
    row = _outbound(db, body["provider_message_id"])
    assert row.channel == "whatsapp"
    assert row.direction == "outbound"
    assert row.source == "live_whatsapp"
    assert row.status == "sent"
    assert row.sent_at is not None
    assert row.delivered_at is None
    assert row.opened_at is None
    assert row.created_by == sales.id
    assert row.contact_id == contact.id
    assert row.conversation_key == inbound.conversation_key
    assert row.thread_id == inbound.thread_id
    assert row.thread_id is not None
    audit = db.scalar(
        select(CrmCommunicationAuditLog).where(
            CrmCommunicationAuditLog.communication_id == row.id,
            CrmCommunicationAuditLog.event_type == "communication.whatsapp_sent",
        )
    )
    assert audit is not None
    assert audit.actor_user_id == sales.id


def test_new_contact_message_normalizes_phone_and_starts_a_thread(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="0532 111 22 33")
    response = auth_client.post(
        SEND_PATH,
        json={"contact_id": str(contact.id), "body_text": "İlk mesaj"},
    )
    assert response.status_code == 200, response.text
    assert RecordingClient.calls[-1]["to"] == "905321112233"
    assert RecordingClient.calls[-1]["phone_number_id"] == PHONE_NUMBER_ID
    row = _outbound(db, response.json()["provider_message_id"])
    assert row.conversation_key == "905321112233"
    assert row.thread_id is not None
    assert _count(db, contact_id=contact.id) == 1


def test_lead_without_thread_uses_lead_phone(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@example.com")
    lead = Lead(full_name="Lead Ada", phone="0533 444 55 66", status=LeadStatus.NEW)
    db.add(lead)
    db.commit()
    response = auth_client.post(
        SEND_PATH,
        json={"lead_id": str(lead.id), "body_text": "Lead mesajı"},
    )
    assert response.status_code == 200, response.text
    assert RecordingClient.calls[-1]["to"] == "905334445566"
    row = _outbound(db, response.json()["provider_message_id"])
    assert row.conversation_key == "905334445566"
    assert row.thread_id is not None


def test_missing_ambiguous_and_foreign_phone_are_rejected(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "sales@example.com")
    empty = _contact(db, phone=None, name="No Phone")
    missing = auth_client.post(SEND_PATH, json={"contact_id": str(empty.id), "body_text": "Hi"})
    assert missing.status_code == 400
    assert missing.json()["detail"] == "whatsapp_phone_missing"
    assert _count(db, contact_id=empty.id) == 0

    many = _contact(db, phone="+905551112233", secondary=["+1 202 555 0143"], name="Many")
    ambiguous = auth_client.post(SEND_PATH, json={"contact_id": str(many.id), "body_text": "Hi"})
    assert ambiguous.status_code == 400
    assert ambiguous.json()["detail"] == "whatsapp_phone_ambiguous"
    foreign = auth_client.post(
        SEND_PATH,
        json={"contact_id": str(many.id), "to": "+905559998877", "body_text": "Hi"},
    )
    assert foreign.status_code == 400
    assert foreign.json()["detail"] == "recipient_not_allowed"
    assert _count(db, contact_id=many.id) == 0
    assert RecordingClient.calls == []


def test_provider_rejection_does_not_create_a_row(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Rejecting:
        def __init__(
            self,
            *,
            access_token: str,
            phone_number_id: str,
            graph_api_version: str,
        ) -> None:
            _ = access_token, phone_number_id, graph_api_version

        def send_text(self, *, to: str, body: str) -> str:
            _ = to, body
            raise WhatsAppCloudError(
                http_status=400,
                provider_code="131026",
                provider_message="Message undeliverable",
                template_required=False,
            )

    monkeypatch.setattr("investhome_api.services.crm.whatsapp_send.WhatsAppCloudClient", Rejecting)
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    response = auth_client.post(SEND_PATH, json={"contact_id": str(contact.id), "body_text": "Hi"})
    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "whatsapp_send_failed"
    assert body["details"][0]["code"] == "131026"
    assert TOKEN not in response.text
    assert _count(db, contact_id=contact.id) == 0


def test_template_window_comes_from_provider_response(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Response:
        status_code = 400
        text = json.dumps({"error": {"code": 131047, "message": "Re-engagement message"}})

        def json(self):
            return {
                "error": {
                    "code": 131047,
                    "message": "Re-engagement message",
                    "error_data": {
                        "details": (
                            "More than 24 hours have passed since the customer last replied."
                        ),
                    },
                }
            }

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            _ = args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

        def post(self, url, json=None, headers=None):
            _ = url, json, headers
            return _Response()

    monkeypatch.setattr("investhome_api.services.crm.whatsapp_cloud.httpx.Client", _Client)
    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_send.WhatsAppCloudClient",
        wa_cloud_client(),
    )
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    response = auth_client.post(SEND_PATH, json={"contact_id": str(contact.id), "body_text": "Hi"})
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["detail"] == "whatsapp_template_required"
    assert body["details"][0]["code"] == "131047"
    assert TOKEN not in response.text
    assert _count(db, contact_id=contact.id) == 0


def wa_cloud_client():
    from investhome_api.services.crm.whatsapp_cloud import WhatsAppCloudClient

    return WhatsAppCloudClient


def test_access_token_is_a_header_and_is_not_logged(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    captured: list[dict] = []

    class _Response:
        status_code = 200

        def json(self):
            return {"messages": [{"id": "wamid.header.1"}]}

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            _ = args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

        def post(self, url, json=None, headers=None):
            captured.append({"url": url, "json": json, "headers": headers})
            return _Response()

    monkeypatch.setattr("investhome_api.services.crm.whatsapp_cloud.httpx.Client", _Client)
    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_send.WhatsAppCloudClient",
        wa_cloud_client(),
    )
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    with caplog.at_level(logging.DEBUG):
        response = auth_client.post(
            SEND_PATH,
            json={"contact_id": str(contact.id), "body_text": "Hi"},
        )
    assert response.status_code == 200, response.text
    assert captured[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert captured[0]["url"] == (
        f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    )
    assert TOKEN not in captured[0]["url"]
    assert captured[0]["json"]["to"] == "905551112233"
    assert TOKEN not in caplog.text
    assert response.json()["provider_message_id"] == "wamid.header.1"


def test_crm_persist_failure_returns_wamid_without_a_row(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _boom(*args, **kwargs):
        _ = args, kwargs
        raise RuntimeError("db down")

    monkeypatch.setattr("investhome_api.services.crm.whatsapp_send.ingest_live_message", _boom)
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    with caplog.at_level(logging.ERROR):
        response = auth_client.post(
            SEND_PATH,
            json={"contact_id": str(contact.id), "body_text": "Hi"},
        )
    assert response.status_code == 500
    assert response.json()["detail"] == "crm_persist_failed"
    assert RecordingClient.calls
    assert RecordingClient.calls[-1]["wamid"] in caplog.text
    assert TOKEN not in caplog.text
    assert _count(db, contact_id=contact.id) == 0


def test_idempotency_key_does_not_send_twice(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    payload = {
        "contact_id": str(contact.id),
        "body_text": "Bir kez",
        "idempotency_key": "local-key-1",
    }
    first = auth_client.post(SEND_PATH, json=payload)
    second = auth_client.post(SEND_PATH, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    assert second.json()["id"] == first.json()["id"]
    assert len(RecordingClient.calls) == 1
    assert _count(db, contact_id=contact.id) == 1


def test_delivery_statuses_are_idempotent_and_do_not_regress(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    created = auth_client.post(
        SEND_PATH,
        json={"contact_id": str(contact.id), "body_text": "Durum"},
    )
    assert created.status_code == 200, created.text
    wamid = created.json()["provider_message_id"]
    row = _outbound(db, wamid)
    row.sent_at = None
    row.status = "queued"
    meta = dict(row.metadata_json or {})
    meta["whatsapp_delivery_rank"] = 0
    meta["whatsapp_delivery_at"] = 0
    row.metadata_json = meta
    flag_modified(row, "metadata_json")
    db.commit()

    sent = _post_webhook(auth_client, _status_payload(wamid, "sent", 1_700_000_100))
    assert sent.status_code == 200, sent.text
    row = _outbound(db, wamid)
    assert row.status == "sent"
    assert row.sent_at is not None
    assert _count(db, wamid=wamid) == 1

    delivered = _post_webhook(auth_client, _status_payload(wamid, "delivered", 1_700_000_200))
    assert delivered.status_code == 200
    row = _outbound(db, wamid)
    assert row.status == "delivered"
    assert row.delivered_at is not None

    read = _post_webhook(auth_client, _status_payload(wamid, "read", 1_700_000_300))
    assert read.status_code == 200
    row = _outbound(db, wamid)
    opened_at = row.opened_at
    assert row.status == "opened"
    assert opened_at is not None
    assert _count(db, wamid=wamid) == 1

    replay = _post_webhook(auth_client, _status_payload(wamid, "read", 1_700_000_300))
    assert replay.status_code == 200
    assert replay.json()["duplicate"] is True
    row = _outbound(db, wamid)
    assert row.opened_at == opened_at
    assert row.status == "opened"

    wa.reset_whatsapp_idempotency_for_tests()
    older = _post_webhook(auth_client, _status_payload(wamid, "sent", 1_700_000_050))
    assert older.status_code == 200
    row = _outbound(db, wamid)
    assert row.status == "opened"
    assert row.opened_at == opened_at
    assert row.delivered_at is not None


def test_failed_status_updates_the_row_and_unknown_status_creates_nothing(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    created = auth_client.post(SEND_PATH, json={"contact_id": str(contact.id), "body_text": "Fail"})
    wamid = created.json()["provider_message_id"]
    before = _count(db, contact_id=contact.id)
    missing = _post_webhook(
        auth_client,
        _status_payload("wamid.missing", "delivered", 1_700_000_100),
    )
    assert missing.status_code == 200
    assert _count(db, wamid="wamid.missing") == 0
    failed = _post_webhook(
        auth_client,
        _status_payload(
            wamid,
            "failed",
            1_900_000_000,
            errors=[{"code": 131026, "title": "Message undeliverable"}],
        ),
    )
    assert failed.status_code == 200, failed.text
    row = _outbound(db, wamid)
    assert row.status == "failed"
    assert row.failed_at is not None
    assert row.failure_reason
    assert "131026" in row.failure_reason
    assert _count(db, contact_id=contact.id) == before


def test_readonly_and_inactive_cannot_send(auth_client: TestClient, db: Session) -> None:
    anonymous = auth_client.post(SEND_PATH, json={"body_text": "Hi"})
    assert anonymous.status_code in {401, 403}
    _login(auth_client, "readonly@example.com")
    forbidden = auth_client.post(SEND_PATH, json={"body_text": "Hi"})
    assert forbidden.status_code == 403
    inactive = auth_client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "Demo123!"},
    )
    assert inactive.status_code == 403
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    sales.status = UserStatus.SUSPENDED
    db.commit()
    try:
        suspended = auth_client.post(
            SEND_PATH,
            json={"contact_id": str(contact.id), "body_text": "Hi"},
        )
        assert suspended.status_code == 403
    finally:
        sales.status = UserStatus.ACTIVE
        db.commit()


def test_missing_cloud_credentials_fail_closed(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    response = auth_client.post(SEND_PATH, json={"contact_id": str(contact.id), "body_text": "Hi"})
    assert response.status_code == 503
    assert response.json()["detail"] == "whatsapp_not_configured"
    assert TOKEN not in response.text
    assert RecordingClient.calls == []
    assert _count(db, contact_id=contact.id) == 0


def _capturing_httpx(captured: list[dict]) -> type:
    class _Response:
        status_code = 200

        def json(self):
            return {"messages": [{"id": "wamid.version.1"}]}

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            _ = args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

        def post(self, url, json=None, headers=None):
            captured.append({"url": url, "json": json, "headers": headers})
            return _Response()

    return _Client


def test_configured_graph_version_is_used_in_the_request_url(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("WHATSAPP_GRAPH_API_VERSION", "v26.0")
    get_settings.cache_clear()
    captured: list[dict] = []
    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_cloud.httpx.Client",
        _capturing_httpx(captured),
    )
    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_send.WhatsAppCloudClient",
        wa_cloud_client(),
    )
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    with caplog.at_level(logging.DEBUG):
        response = auth_client.post(
            SEND_PATH,
            json={"contact_id": str(contact.id), "body_text": "Hi"},
        )
    assert response.status_code == 200, response.text
    assert captured[0]["url"] == (
        f"https://graph.facebook.com/v26.0/{PHONE_NUMBER_ID}/messages"
    )
    assert TOKEN not in captured[0]["url"]
    assert TOKEN not in response.text
    assert TOKEN not in caplog.text


def test_invalid_graph_version_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from pydantic import ValidationError

    monkeypatch.setenv("WHATSAPP_GRAPH_API_VERSION", "https://evil.example/v21.0")
    get_settings.cache_clear()
    with caplog.at_level(logging.DEBUG), pytest.raises(
        ValidationError, match="WHATSAPP_GRAPH_API_VERSION"
    ):
        get_settings()
    assert TOKEN not in caplog.text
    assert "evil.example" not in caplog.text
    get_settings.cache_clear()


def test_invalid_graph_version_does_not_call_meta(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _Settings:
        whatsapp_access_token = TOKEN
        whatsapp_phone_number_id = PHONE_NUMBER_ID
        whatsapp_graph_api_version = "v25.0/../admin"

    monkeypatch.setattr(
        "investhome_api.services.crm.whatsapp_send.get_settings",
        lambda: _Settings(),
    )
    _login(auth_client, "sales@example.com")
    contact = _contact(db, phone="+905551112233")
    with caplog.at_level(logging.DEBUG):
        response = auth_client.post(
            SEND_PATH,
            json={"contact_id": str(contact.id), "body_text": "Hi"},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "whatsapp_graph_version_invalid"
    assert "evil" not in response.text
    assert "../" not in response.text
    assert TOKEN not in response.text
    assert TOKEN not in caplog.text
    assert RecordingClient.calls == []
    assert _count(db, contact_id=contact.id) == 0
