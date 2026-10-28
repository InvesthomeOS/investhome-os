"""Wazzup inbound WhatsApp webhook, matching, and sales notification."""

from __future__ import annotations

import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.crm import wazzup_webhook as wz
from investhome_api.services.crm.meta_inbound_notify import MemoryNotifyLock
from investhome_api.services.crm.wazzup_inbound_notify import (
    WazzupInboundEmailRetry,
    deliver_wazzup_inbound_email,
)
from investhome_api.services.notification_gateway import GatewayResult, NotificationChannel

SECRET = "unit-test-wazzup-webhook-secret-32"
API_KEY = "unit-test-wazzup-api-key-do-not-log"
PATH = "/webhooks/wazzup"


@pytest.fixture(autouse=True)
def _wazzup_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WAZZUP_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("WAZZUP_API_KEY", API_KEY)
    monkeypatch.setenv("WAZZUP_INBOUND_EMAIL_NOTIFICATIONS_ENABLED", "false")
    get_settings.cache_clear()
    wz.reset_wazzup_idempotency_for_tests()
    yield
    wz.reset_wazzup_idempotency_for_tests()
    get_settings.cache_clear()


def _message(
    message_id: str,
    *,
    chat_id: str = "905321112233",
    text: str = "Merhaba",
    chat_type: str = "whatsapp",
    is_echo: bool = False,
    status: str = "inbound",
    is_deleted: bool = False,
    message_type: str = "text",
    content_uri: str | None = None,
    name: str | None = "Ayse",
) -> dict:
    item: dict = {
        "messageId": message_id,
        "channelId": "b96a353b-1111-4cac-8413-ba99999f981",
        "chatType": chat_type,
        "chatId": chat_id,
        "dateTime": "2026-10-28T12:00:00.002Z",
        "type": message_type,
        "status": status,
        "text": text,
        "isEcho": is_echo,
        "isDeleted": is_deleted,
        "contact": {"name": name} if name else {},
    }
    if content_uri:
        item["contentUri"] = content_uri
    return item


def _payload(*messages: dict, statuses: list | None = None) -> dict:
    body: dict = {"messages": list(messages)}
    if statuses is not None:
        body["statuses"] = statuses
    return body


def _post(client: TestClient, payload: dict, *, token: str | None = SECRET):
    params = {} if token is None else {"token": token}
    return client.post(PATH, json=payload, params=params)


def _count_messages(db: Session, message_id: str | None = None) -> int:
    query = select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.source == "live_wazzup"
    )
    if message_id is not None:
        query = query.where(CrmCommunication.external_provider_id == message_id)
    return int(db.scalar(query) or 0)


def _row(db: Session, message_id: str) -> CrmCommunication:
    db.expire_all()
    row = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == message_id)
    )
    assert row is not None
    return row


def _contact(db: Session, phone: str, name: str = "Ada") -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        primary_phone=phone,
        status=CrmContactStatus.ACTIVE,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _sales_user(db: Session, email: str) -> User:
    user = User(
        full_name="Sales Person",
        email=email,
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    role = db.scalar(select(Role).where(Role.code == "sales"))
    if role is None:
        role = Role(name="sales", code="sales", is_system_role=True)
        db.add(role)
        db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def test_probe_returns_200_and_writes_nothing(client: TestClient, db: Session) -> None:
    before = _count_messages(db)
    response = _post(client, {"test": True})
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}
    assert _count_messages(db) == before
    assert SECRET not in response.text


def test_missing_and_wrong_token_rejected(client: TestClient, db: Session) -> None:
    message_id = str(uuid4())
    missing = _post(client, _payload(_message(message_id)), token=None)
    assert missing.status_code == 403
    assert missing.json()["detail"] == "Forbidden"
    wrong = _post(client, _payload(_message(message_id)), token="not-the-secret")
    assert wrong.status_code == 403
    assert _count_messages(db, message_id) == 0
    assert SECRET not in missing.text
    assert SECRET not in wrong.text


def test_missing_secret_fails_closed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WAZZUP_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()
    response = _post(client, {"test": True}, token=SECRET)
    assert response.status_code == 503
    assert response.json()["detail"] == "Webhook temporarily unavailable"
    assert SECRET not in response.text


def test_access_log_redacts_the_query_token(caplog: pytest.LogCaptureFixture) -> None:
    from investhome_api.core.logging_config import configure_logging

    configure_logging()
    access = logging.getLogger("uvicorn.access")
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        access.info(
            '%s - "%s %s HTTP/%s" %d',
            "172.30.0.2:0",
            "POST",
            f"/webhooks/wazzup?token={SECRET}",
            "1.1",
            200,
        )
    assert SECRET not in caplog.text
    assert "token=[redacted]" in caplog.text


def test_secret_is_never_logged(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    message_id = str(uuid4())
    with caplog.at_level(logging.DEBUG):
        response = _post(client, _payload(_message(message_id, text="gizli")))
    assert response.status_code == 200, response.text
    app_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if not record.name.startswith("httpx")
    )
    assert SECRET not in app_logs
    assert API_KEY not in app_logs
    assert "token=" not in app_logs
    assert SECRET not in response.text


def test_valid_inbound_creates_one_live_wazzup_row(client: TestClient, db: Session) -> None:
    message_id = str(uuid4())
    response = _post(
        client,
        _payload(
            _message(
                message_id,
                chat_id="0532 111 22 33",
                text="Merhaba",
                message_type="image",
                content_uri="https://store.wazzup24.com/example-file",
            )
        ),
    )
    assert response.status_code == 200, response.text
    row = _row(db, message_id)
    assert row.channel == "whatsapp"
    assert row.direction == "inbound"
    assert row.source == "live_wazzup"
    assert row.sender_identity == "+905321112233"
    assert row.conversation_key == "905321112233"
    assert row.body_text == "Merhaba"
    assert row.occurred_at is not None
    assert row.occurred_at.year == 2026
    meta = row.metadata_json
    assert meta["provider"] == "wazzup"
    assert meta["message_type"] == "image"
    assert meta["content_present"] is True
    assert meta["contact_name"] == "Ayse"
    assert meta["channel_id"].startswith("b96a353b-")
    assert "contentUri" not in meta
    assert "store.wazzup24.com" not in str(meta)
    assert row.match_status == "unmatched"
    assert row.contact_id is None
    assert row.activity_id is None


def test_one_contact_attaches_and_projects_timeline(client: TestClient, db: Session) -> None:
    message_id = str(uuid4())
    contact = _contact(db, "+905321112233", "Ada")
    response = _post(client, _payload(_message(message_id, chat_id="905321112233")))
    assert response.status_code == 200, response.text
    row = _row(db, message_id)
    assert row.match_status == "matched"
    assert row.contact_id == contact.id
    assert row.activity_id is not None


def test_zero_match_stays_unmatched_and_creates_no_contact_or_lead(
    client: TestClient,
    db: Session,
) -> None:
    message_id = str(uuid4())
    contacts_before = int(db.scalar(select(func.count()).select_from(CrmContact)) or 0)
    leads_before = int(db.scalar(select(func.count()).select_from(Lead)) or 0)
    response = _post(client, _payload(_message(message_id, chat_id="905559990011")))
    assert response.status_code == 200, response.text
    row = _row(db, message_id)
    assert row.match_status == "unmatched"
    assert row.contact_id is None
    contacts_after = int(db.scalar(select(func.count()).select_from(CrmContact)) or 0)
    leads_after = int(db.scalar(select(func.count()).select_from(Lead)) or 0)
    assert contacts_after == contacts_before
    assert leads_after == leads_before


def test_ambiguous_match_stays_ambiguous(client: TestClient, db: Session) -> None:
    message_id = str(uuid4())
    _contact(db, "+905321112233", "Ada")
    _contact(db, "05321112233", "Bora")
    response = _post(client, _payload(_message(message_id)))
    assert response.status_code == 200, response.text
    row = _row(db, message_id)
    assert row.match_status == "ambiguous"
    assert row.contact_id is None
    assert row.activity_id is None
    assert len(row.suggested_matches or []) == 2


def test_duplicate_message_id_creates_one_row(client: TestClient, db: Session) -> None:
    message_id = str(uuid4())
    first = _post(client, _payload(_message(message_id, text="ilk")))
    second = _post(client, _payload(_message(message_id, text="tekrar")))
    assert first.status_code == 200
    assert second.status_code == 200
    assert _count_messages(db, message_id) == 1
    assert _row(db, message_id).body_text == "ilk"


def test_echo_statuses_group_other_chats_and_deleted_are_ignored(
    client: TestClient,
    db: Session,
) -> None:
    ignored = [
        _message(str(uuid4()), is_echo=True, status="sent"),
        _message(str(uuid4()), chat_type="whatsgroup"),
        _message(str(uuid4()), chat_type="telegram"),
        _message(str(uuid4()), chat_type="instagram"),
        _message(str(uuid4()), chat_type="viber"),
        _message(str(uuid4()), is_deleted=True),
        _message(str(uuid4()), status="delivered", is_echo=False),
    ]
    response = _post(
        client,
        _payload(*ignored, statuses=[{"messageId": str(uuid4()), "status": "delivered"}]),
    )
    assert response.status_code == 200, response.text
    assert _count_messages(db) == 0


def test_sales_email_is_queued_only_after_commit(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WAZZUP_INBOUND_EMAIL_NOTIFICATIONS_ENABLED", "true")
    get_settings.cache_clear()
    order: list[str] = []
    queued: list[str] = []

    def _enqueue(communication_ids: list[str]) -> None:
        assert db.scalar(select(func.count()).select_from(CrmCommunication)) is not None
        order.append("enqueue")
        queued.extend(communication_ids)

    from sqlalchemy.orm import Session as OrmSession

    original = OrmSession.commit

    def _commit(self):
        order.append("commit")
        return original(self)

    monkeypatch.setattr(OrmSession, "commit", _commit)
    monkeypatch.setattr(
        "investhome_api.services.crm.wazzup_inbound_notify._enqueue_ids",
        _enqueue,
    )
    message_id = str(uuid4())
    response = _post(client, _payload(_message(message_id)))
    assert response.status_code == 200, response.text
    assert "commit" in order
    assert order.index("commit") < order.index("enqueue")
    row = _row(db, message_id)
    assert queued == [str(row.id)]


def test_smtp_failure_does_not_remove_the_crm_row(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sales_user(db, f"wazzup-sales-{uuid4().hex[:8]}@example.com")
    message_id = str(uuid4())
    response = _post(client, _payload(_message(message_id, text="kalici")))
    assert response.status_code == 200, response.text
    row = _row(db, message_id)

    class _Gateway:
        def dispatch(self, message, *, provider_id: str | None = None):
            del message, provider_id
            return GatewayResult(
                ok=False,
                provider_id="email_smtp",
                channel=NotificationChannel.EMAIL,
                status="failed",
                detail="SMTP send failed",
            )

    monkeypatch.setenv("WAZZUP_INBOUND_EMAIL_NOTIFICATIONS_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "investhome_api.services.crm.wazzup_inbound_notify.get_notification_gateway",
        lambda: _Gateway(),
    )
    with pytest.raises(WazzupInboundEmailRetry):
        deliver_wazzup_inbound_email(row.id, db=db, lock=MemoryNotifyLock())
    assert _count_messages(db, message_id) == 1
    assert _row(db, message_id).body_text == "kalici"


def test_notification_flag_false_does_not_queue(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"n": 0}

    def _enqueue(communication_ids: list[str]) -> None:
        del communication_ids
        called["n"] += 1

    monkeypatch.setattr(
        "investhome_api.services.crm.wazzup_inbound_notify._enqueue_ids",
        _enqueue,
    )
    response = _post(client, _payload(_message(str(uuid4()))))
    assert response.status_code == 200, response.text
    assert called["n"] == 0
