"""Customer Gmail replies: real send, CRM persist, Sent-sync dedupe. No SMTP."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationAuditLog,
    CrmUserCommunicationAccount,
    CrmUserCommunicationAccountHealth,
    CrmUserCommunicationAccountStatus,
)
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmRecordKind,
)
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.crm.gmail_client import GmailApiError
from investhome_api.services.crm.gmail_sync import sync_gmail_account
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crypto_seal import seal_secret

SEND_PATH = "/crm/live-communications/email/send"
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
FULL_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", READ_SCOPE, SEND_SCOPE]
READONLY_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", READ_SCOPE]


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200, response.text


def _user(db: Session, email: str) -> User:
    row = db.scalar(select(User).where(User.email == email))
    assert row is not None
    return row


def _account(
    db: Session,
    user: User,
    identity: str,
    *,
    scopes: list[str] | None = None,
    status: str = CrmUserCommunicationAccountStatus.CONNECTED.value,
) -> CrmUserCommunicationAccount:
    granted = scopes if scopes is not None else FULL_SCOPES
    row = CrmUserCommunicationAccount(
        user_id=user.id,
        channel_type="email",
        provider="gmail",
        identity=identity,
        account_label=identity,
        status=status,
        health=CrmUserCommunicationAccountHealth.HEALTHY.value,
        scopes=granted,
        encrypted_credentials=seal_secret(
            {
                "access_token": f"access-{uuid4().hex}",
                "refresh_token": f"refresh-{uuid4().hex}",
                "expiry": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "scope": " ".join(granted),
            }
        ),
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _contact(db: Session, email: str | None, *, name: str = "Ada Buyer") -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        primary_email=email,
        status=CrmContactStatus.ACTIVE,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_inbound(
    db: Session,
    account: CrmUserCommunicationAccount,
    contact: CrmContact,
) -> CrmCommunication:
    comm, _created = ingest_live_message(
        db,
        {
            "channel": "email",
            "direction": "incoming",
            "source": "live_email",
            "account_id": str(account.id),
            "contact_id": str(contact.id),
            "subject": "Tapu sorusu",
            "body_text": "Merhaba, daire hakkında yazıyorum",
            "sender": contact.primary_email,
            "recipients": [account.identity],
            "cc": ["copy@example.com"],
            "external_provider_id": f"gm-in-{uuid4().hex[:8]}",
            "conversation_id": "thread-ada",
            "rfc_message_id": "<inbound-ada@mail.gmail.com>",
            "occurred_at": datetime.now(UTC) - timedelta(hours=2),
        },
    )
    db.commit()
    db.refresh(comm)
    return comm


class RecordingMailbox:
    calls: list[dict[str, object]] = []

    def __init__(self, account: CrmUserCommunicationAccount) -> None:
        self.account = account

    def send_message(self, *, raw: str, thread_id: str | None = None) -> dict[str, str]:
        RecordingMailbox.calls.append(
            {
                "identity": self.account.identity,
                "account_id": str(self.account.id),
                "raw": raw,
                "thread_id": thread_id,
            }
        )
        return {"id": "gm-sent-1", "threadId": thread_id or "thread-created"}


class FailingMailbox:
    def __init__(self, account: CrmUserCommunicationAccount) -> None:
        self.account = account

    def send_message(self, *, raw: str, thread_id: str | None = None) -> dict[str, str]:
        raise GmailApiError("gmail_api_error")


def _patch_mailbox(monkeypatch: pytest.MonkeyPatch, factory: type) -> None:
    RecordingMailbox.calls = []
    monkeypatch.setattr("investhome_api.services.crm.gmail_send.GoogleGmailMailbox", factory)


def _decode(raw: str):
    padded = raw + "=" * (-len(raw) % 4)
    return message_from_bytes(base64.urlsafe_b64decode(padded.encode("ascii")))


def _send(client: TestClient, payload: dict) -> object:
    return client.post(SEND_PATH, json=payload)


def test_reply_uses_own_thread_account_headers_and_one_row(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    thread_account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    inbound = _seed_inbound(db, thread_account, contact)
    _patch_mailbox(monkeypatch, RecordingMailbox)

    response = _send(
        auth_client,
        {
            "mode": "reply",
            "communication_id": str(inbound.id),
            "contact_id": str(contact.id),
            "to": ["ada@example.com"],
            "subject": "Re: Tapu sorusu",
            "body_text": "Belgeleri paylaşıyorum",
            "body_html": "<p>Belgeleri paylaşıyorum</p>",
        },
    )
    assert response.status_code == 200, response.text
    assert "access-" not in response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["direction"] == "outbound"
    assert body["provider_message_id"] == "gm-sent-1"
    assert body["contact_id"] == str(contact.id)

    call = RecordingMailbox.calls[0]
    assert call["identity"] == "sales.box@investhome.com.tr"
    assert call["account_id"] == str(thread_account.id)
    assert call["thread_id"] == "thread-ada"
    mime = _decode(str(call["raw"]))
    assert mime["In-Reply-To"] == "<inbound-ada@mail.gmail.com>"
    assert "<inbound-ada@mail.gmail.com>" in mime["References"]
    rendered = mime.as_string()
    assert "text/html" in rendered
    assert "text/plain" in rendered

    db.expire_all()
    rows = list(
        db.scalars(
            select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
        ).all()
    )
    assert len(rows) == 1
    outbound = rows[0]
    assert outbound.account_id == thread_account.id
    assert outbound.conversation_key == "thread-ada"
    assert outbound.provider_thread_id == "thread-ada"
    assert outbound.created_by == sales.id
    assert outbound.contact_id == contact.id
    assert outbound.activity_id is not None
    meta = outbound.metadata_json or {}
    assert meta["rfc_message_id"]
    assert meta["in_reply_to"] == "<inbound-ada@mail.gmail.com>"
    assert meta["reply_to_communication_id"] == str(inbound.id)
    audit = db.scalar(
        select(CrmCommunicationAuditLog).where(
            CrmCommunicationAuditLog.communication_id == outbound.id,
            CrmCommunicationAuditLog.event_type == "communication.email_sent",
        )
    )
    assert audit is not None
    assert audit.actor_user_id == sales.id


def _foreign_inbound(db: Session, sales: User) -> tuple[CrmCommunication, CrmContact]:
    owner = User(
        full_name="Mailbox Owner",
        email=f"owner-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        status=UserStatus.ACTIVE,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    thread_account = _account(db, owner, "thread.box@investhome.com.tr")
    _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    return _seed_inbound(db, thread_account, contact), contact


def test_reply_rejects_another_users_gmail_account(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    inbound, contact = _foreign_inbound(db, sales)
    before = db.scalar(select(func.count()).select_from(CrmCommunication))
    _patch_mailbox(monkeypatch, RecordingMailbox)
    context = auth_client.get(
        "/crm/live-communications/email/reply-context",
        params={"communication_id": str(inbound.id)},
    )
    assert context.status_code == 200, context.text
    assert context.json()["send_block"] == "gmail_account_not_owned"
    assert context.json()["from_mailbox"] is None
    assert "thread.box@investhome.com.tr" not in context.text
    response = _send(
        auth_client,
        {
            "mode": "reply",
            "communication_id": str(inbound.id),
            "contact_id": str(contact.id),
            "to": ["ada@example.com"],
            "subject": "Re: Tapu sorusu",
            "body_text": "Bu gönderilmemeli",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "gmail_account_not_owned"
    assert RecordingMailbox.calls == []
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(CrmCommunication)) == before
    assert (
        db.scalar(
            select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
        )
        is None
    )


def test_reply_all_rejects_another_users_gmail_account(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    inbound, contact = _foreign_inbound(db, sales)
    before = db.scalar(select(func.count()).select_from(CrmCommunication))
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "reply_all",
            "communication_id": str(inbound.id),
            "contact_id": str(contact.id),
            "to": ["ada@example.com"],
            "cc": ["copy@example.com"],
            "subject": "Re: Tapu sorusu",
            "body_text": "Bu da gönderilmemeli",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "gmail_account_not_owned"
    assert RecordingMailbox.calls == []
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(CrmCommunication)) == before
    assert (
        db.scalar(
            select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
        )
        is None
    )


def test_sent_sync_does_not_duplicate_outbound(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    inbound = _seed_inbound(db, account, contact)
    _patch_mailbox(monkeypatch, RecordingMailbox)
    sent = _send(
        auth_client,
        {
            "mode": "reply",
            "communication_id": str(inbound.id),
            "subject": "Re: Tapu sorusu",
            "body_text": "İlk kayıt",
        },
    )
    assert sent.status_code == 200, sent.text
    db.expire_all()
    outbound = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
    )
    assert outbound is not None
    rfc = (outbound.metadata_json or {})["rfc_message_id"]
    occurred = datetime.now(UTC) - timedelta(minutes=30)
    text_b64 = base64.urlsafe_b64encode(b"SYNC BODY DIFFERENT").decode("ascii").rstrip("=")
    message = {
        "id": "gm-sent-1",
        "threadId": "thread-ada",
        "labelIds": ["SENT"],
        "internalDate": str(int(occurred.timestamp() * 1000)),
        "snippet": "SYNC BODY DIFFERENT",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": account.identity},
                {"name": "To", "value": "ada@example.com"},
                {"name": "Subject", "value": "Re: Tapu sorusu"},
                {"name": "Message-ID", "value": rfc},
                {"name": "Date", "value": occurred.strftime("%a, %d %b %Y %H:%M:%S +0000")},
            ],
            "body": {"data": text_b64},
        },
    }

    class SentBox:
        def get_profile_history_id(self) -> str:
            return "77"

        def list_message_ids(self, query: str):
            if "in:sent" in query:
                yield message["id"]

        def get_message(self, message_id: str) -> dict:
            return message

        def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
            return b""

        def list_history_message_ids(self, start_history_id: str) -> tuple[list[str], str | None]:
            return [], "77"

    result = sync_gmail_account(db, account, mailbox=SentBox(), force_backfill=True)
    db.commit()
    assert result["duplicates"] >= 1
    db.expire_all()
    count = db.scalar(
        select(func.count())
        .select_from(CrmCommunication)
        .where(CrmCommunication.external_provider_id == "gm-sent-1")
    )
    assert count == 1


def test_new_email_uses_actor_mailbox(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    other = User(
        full_name="Other",
        email=f"other-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        status=UserStatus.ACTIVE,
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    _account(db, other, "other.box@investhome.com.tr")
    mine = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "new",
            "contact_id": str(contact.id),
            "subject": "Tanışma",
            "body_text": "Merhaba Ada",
        },
    )
    assert response.status_code == 200, response.text
    assert RecordingMailbox.calls[0]["identity"] == "sales.box@investhome.com.tr"
    assert RecordingMailbox.calls[0]["thread_id"] is None
    db.expire_all()
    row = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
    )
    assert row is not None
    assert row.account_id == mine.id
    assert row.contact_id == contact.id
    assert row.conversation_key == "thread-created"
    assert row.created_by == sales.id
    assert row.activity_id is not None


def test_missing_gmail_account_and_missing_send_scope(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    contact = _contact(db, "ada@example.com")
    _patch_mailbox(monkeypatch, RecordingMailbox)
    missing = _send(
        auth_client,
        {"mode": "new", "contact_id": str(contact.id), "subject": "Merhaba", "body_text": "Selam"},
    )
    assert missing.status_code == 409
    assert missing.json()["detail"] == "gmail_account_missing"
    assert RecordingMailbox.calls == []

    account = _account(db, sales, "sales.box@investhome.com.tr", scopes=READONLY_SCOPES)
    reconnect = _send(
        auth_client,
        {"mode": "new", "contact_id": str(contact.id), "subject": "Merhaba", "body_text": "Selam"},
    )
    assert reconnect.status_code == 409
    assert reconnect.json()["detail"] == "gmail_reconnect_required"
    assert RecordingMailbox.calls == []
    db.expire_all()
    db.refresh(account)
    assert account.status == CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value
    assert (
        db.scalar(
            select(func.count())
            .select_from(CrmCommunication)
            .where(CrmCommunication.channel == "email")
        )
        == 0
    )


def test_gmail_api_error_does_not_create_sent_row(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    _seed_inbound(db, account, contact)
    _patch_mailbox(monkeypatch, FailingMailbox)
    before = db.scalar(select(func.count()).select_from(CrmCommunication))
    response = _send(
        auth_client,
        {
            "mode": "reply",
            "contact_id": str(contact.id),
            "subject": "Re: Tapu sorusu",
            "body_text": "Olmamalı",
            "communication_id": str(
                db.scalar(
                    select(CrmCommunication.id).where(CrmCommunication.direction == "inbound")
                )
            ),
        },
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "gmail_send_failed"
    db.expire_all()
    after = db.scalar(select(func.count()).select_from(CrmCommunication))
    assert after == before


def test_contact_without_email_is_rejected(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, None, name="No Email")
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {"mode": "new", "contact_id": str(contact.id), "subject": "Merhaba", "body_text": "Selam"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "contact_email_missing"
    assert RecordingMailbox.calls == []


def test_readonly_cannot_send_and_inactive_cannot_authenticate(auth_client: TestClient) -> None:
    denied = auth_client.post(
        SEND_PATH,
        json={"mode": "new", "contact_id": str(uuid4()), "subject": "X", "body_text": "Y"},
    )
    assert denied.status_code == 401

    _login(auth_client, "readonly@example.com")
    forbidden = auth_client.post(
        SEND_PATH,
        json={"mode": "new", "contact_id": str(uuid4()), "subject": "X", "body_text": "Y"},
    )
    assert forbidden.status_code == 403

    inactive = auth_client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "Demo123!"},
    )
    assert inactive.status_code == 403


def test_reply_all_includes_cc_when_stored(
    auth_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    inbound = _seed_inbound(db, account, contact)
    inbound.bcc_recipients = ["hidden@example.com"]
    db.commit()
    context = auth_client.get(
        "/crm/live-communications/email/reply-context",
        params={"communication_id": str(inbound.id)},
    )
    assert context.status_code == 200, context.text
    assert context.json()["can_reply_all"] is True
    assert "copy@example.com" in context.json()["cc"]
    assert context.json()["to"] == ["ada@example.com"]
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "reply_all",
            "communication_id": str(inbound.id),
            "subject": context.json()["subject"],
            "body_text": "Herkese",
        },
    )
    assert response.status_code == 200, response.text
    mime = _decode(str(RecordingMailbox.calls[0]["raw"]))
    assert "copy@example.com" in (mime["Cc"] or "")
    assert mime["To"] == "ada@example.com"
    assert "sales.box@investhome.com.tr" not in (mime["To"] or "")
    assert "sales.box@investhome.com.tr" not in (mime["Cc"] or "")
    assert mime["Bcc"] is None
    assert "hidden@example.com" not in mime.as_string()
    db.expire_all()
    outbound = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
    )
    assert outbound is not None
    assert outbound.provider_thread_id == "thread-ada"
    assert outbound.conversation_key == "thread-ada"
    assert "hidden@example.com" not in context.json()["cc"]
    assert "bcc" not in context.json()


def test_new_email_sends_cc_bcc_and_persists_recipients(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "new",
            "contact_id": str(contact.id),
            "to": ["Ada@example.com", "ada@example.com"],
            "cc": ["ada@example.com", " Copy@Example.com ", "partner@example.com"],
            "bcc": ["copy@example.com", "hidden@example.com", "audit@example.com"],
            "subject": "Tanışma",
            "body_text": "Merhaba Ada",
        },
    )
    assert response.status_code == 200, response.text
    mime = _decode(str(RecordingMailbox.calls[0]["raw"]))
    assert mime["From"] == "sales.box@investhome.com.tr"
    assert mime["To"] == "ada@example.com"
    assert mime["Cc"] == "copy@example.com, partner@example.com"
    assert mime["Bcc"] == "hidden@example.com, audit@example.com"
    db.expire_all()
    row = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == "gm-sent-1")
    )
    assert row is not None
    assert row.account_id == account.id
    assert row.created_by == sales.id
    assert row.sender_identity == "sales.box@investhome.com.tr"
    assert row.recipient_identities == ["ada@example.com"]
    assert row.cc_recipients == ["copy@example.com", "partner@example.com"]
    assert row.bcc_recipients == ["hidden@example.com", "audit@example.com"]
    assert row.provider_thread_id == "thread-created"
    assert (row.metadata_json or {})["rfc_message_id"]


def test_invalid_email_is_rejected(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "new",
            "contact_id": str(contact.id),
            "to": ["ada@example.com"],
            "cc": ["not-an-email"],
            "subject": "Tanışma",
            "body_text": "Merhaba",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_email"
    assert RecordingMailbox.calls == []


def test_reply_does_not_include_prior_cc(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    inbound = _seed_inbound(db, account, contact)
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "reply",
            "communication_id": str(inbound.id),
            "subject": "Re: Tapu sorusu",
            "body_text": "Yalnızca Ada",
        },
    )
    assert response.status_code == 200, response.text
    mime = _decode(str(RecordingMailbox.calls[0]["raw"]))
    assert mime["To"] == "ada@example.com"
    assert mime["Cc"] is None
    assert mime["Bcc"] is None
    assert RecordingMailbox.calls[0]["thread_id"] == "thread-ada"


def test_reply_all_prefers_reply_to(
    auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(auth_client, "sales@example.com")
    sales = _user(db, "sales@example.com")
    account = _account(db, sales, "sales.box@investhome.com.tr")
    contact = _contact(db, "ada@example.com")
    inbound = _seed_inbound(db, account, contact)
    inbound.metadata_json = {**(inbound.metadata_json or {}), "reply_to": "desk@example.com"}
    db.commit()
    _patch_mailbox(monkeypatch, RecordingMailbox)
    response = _send(
        auth_client,
        {
            "mode": "reply_all",
            "communication_id": str(inbound.id),
            "subject": "Re: Tapu sorusu",
            "body_text": "Herkese",
        },
    )
    assert response.status_code == 200, response.text
    mime = _decode(str(RecordingMailbox.calls[0]["raw"]))
    assert mime["To"] == "desk@example.com"
    assert "ada@example.com" in (mime["Cc"] or "")
    assert "copy@example.com" in (mime["Cc"] or "")
    assert "sales.box@investhome.com.tr" not in (mime["To"] or "")
    assert "sales.box@investhome.com.tr" not in (mime["Cc"] or "")
