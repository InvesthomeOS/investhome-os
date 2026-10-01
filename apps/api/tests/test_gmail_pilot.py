"""Gmail pilot: OAuth, parse/ingest mapping, sync, no token leaks."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationAttachment,
    CrmUserCommunicationAccount,
)
from investhome_api.services.crm import gmail_oauth
from investhome_api.services.crm.gmail_parse import parse_gmail_message
from investhome_api.services.crypto_seal import unseal_secret


def _gmail_message(
    *,
    gmail_id: str,
    thread_id: str,
    labels: list[str],
    sender: str,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
    rfc_id: str | None = None,
    when: datetime | None = None,
    filename: str | None = None,
) -> dict:
    occurred = when or datetime.now(UTC)
    headers = [
        {"name": "From", "value": sender},
        {"name": "To", "value": to},
        {"name": "Subject", "value": subject},
        {"name": "Message-ID", "value": rfc_id or f"<{gmail_id}@mail.gmail.com>"},
        {"name": "Date", "value": occurred.strftime("%a, %d %b %Y %H:%M:%S +0000")},
    ]
    text_b64 = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    parts = [
        {"mimeType": "text/plain", "body": {"data": text_b64}, "filename": ""},
    ]
    if html:
        html_b64 = base64.urlsafe_b64encode(html.encode("utf-8")).decode("ascii").rstrip("=")
        parts.append({"mimeType": "text/html", "body": {"data": html_b64}, "filename": ""})
    if filename:
        parts.append(
            {
                "mimeType": "application/pdf",
                "filename": filename,
                "body": {"attachmentId": f"att-{gmail_id}", "size": 12},
            }
        )
    return {
        "id": gmail_id,
        "threadId": thread_id,
        "labelIds": labels,
        "internalDate": str(int(occurred.timestamp() * 1000)),
        "snippet": text[:80],
        "payload": {"mimeType": "multipart/alternative", "headers": headers, "parts": parts},
    }


class FakeMailbox:
    def __init__(self, messages: list[dict], attachments: dict[str, bytes] | None = None):
        self._messages = {item["id"]: item for item in messages}
        self._attachments = attachments or {}
        self.history_id = "99"

    def get_profile_history_id(self) -> str:
        return self.history_id

    def list_message_ids(self, query: str):
        for item in self._messages.values():
            labels = set(item.get("labelIds") or [])
            if "in:inbox" in query and "INBOX" in labels:
                yield item["id"]
            elif "in:sent" in query and "SENT" in labels:
                yield item["id"]

    def get_message(self, message_id: str) -> dict:
        return self._messages[message_id]

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        return self._attachments.get(f"{message_id}:{attachment_id}", b"%PDF-fake")

    def list_history_message_ids(self, start_history_id: str) -> tuple[list[str], str | None]:
        return list(self._messages), self.history_id


@pytest.fixture(autouse=True)
def _gmail_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "drive-client-id")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "drive-client-secret")
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    gmail_oauth.clear_memory_states()
    monkeypatch.setattr(
        gmail_oauth,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )
    yield
    gmail_oauth.clear_memory_states()
    get_settings.cache_clear()


def test_gmail_authorize_reuses_drive_client_and_hides_secret(client: TestClient) -> None:
    response = client.post("/crm/settings/communication-accounts/gmail/authorize")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "drive-client-secret" not in response.text
    assert "client_secret" not in body
    parsed = urlparse(body["authorize_url"])
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["drive-client-id"]
    assert "gmail.readonly" in qs["scope"][0]
    assert "gmail.send" not in qs["scope"][0]
    assert qs["access_type"] == ["offline"]
    assert body["redirect_uri"].endswith("/crm/settings/communication-accounts/gmail/callback")


def test_gmail_callback_stores_encrypted_refresh_and_does_not_leak(
    client: TestClient, db, caplog, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = client.post("/crm/settings/communication-accounts/gmail/authorize")
    qs = parse_qs(urlparse(start.json()["authorize_url"]).query)
    state = qs["state"][0]
    refresh = f"refresh-{uuid4().hex}"
    access = f"access-{uuid4().hex}"

    monkeypatch.setattr(
        gmail_oauth,
        "exchange_authorization_code",
        lambda **kwargs: {
            "access_token": access,
            "refresh_token": refresh,
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
        },
    )
    monkeypatch.setattr(
        gmail_oauth,
        "fetch_google_userinfo",
        lambda token: {"email": "pilot.inbox@investhome.com.tr", "sub": "google-sub-1"},
    )
    monkeypatch.setattr("investhome_api.api.routes.crm_live_communications.enqueue_gmail_sync", lambda *a, **k: None)

    with caplog.at_level("DEBUG"):
        response = client.get(
            "/crm/settings/communication-accounts/gmail/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )
    assert response.status_code == 302
    location = response.headers["location"]
    assert "gmail=connected" in location
    assert refresh not in location
    assert access not in location
    assert refresh not in response.text
    assert access not in caplog.text
    assert "v2:aesgcm:" not in response.text

    listed = client.get("/crm/settings/communication-accounts")
    assert listed.status_code == 200
    listed_text = listed.text
    assert refresh not in listed_text
    assert access not in listed_text
    item = next(row for row in listed.json()["items"] if row["provider"] == "gmail")
    assert item["identity"] == "pilot.inbox@investhome.com.tr"
    assert item["status"] == "connected"
    assert item["has_credentials"] is True
    assert "encrypted_credentials" not in item

    row = db.get(CrmUserCommunicationAccount, UUID(item["id"]))
    db.refresh(row)
    creds = unseal_secret(row.encrypted_credentials)
    assert creds["refresh_token"] == refresh
    assert creds["access_token"] == access
    assert row.encrypted_credentials.startswith("v2:aesgcm:")


def test_parse_gmail_inbox_and_sent_and_skips_spam() -> None:
    inbox = parse_gmail_message(
        _gmail_message(
            gmail_id="in1",
            thread_id="th1",
            labels=["INBOX"],
            sender="Ada Buyer <ada@example.com>",
            to="pilot.inbox@investhome.com.tr",
            subject="Tapu sorusu",
            text="Merhaba, daire hakkında yazıyorum",
            html="<p>Merhaba, daire hakkında yazıyorum</p>",
        ),
        account_email="pilot.inbox@investhome.com.tr",
    )
    assert inbox.direction == "incoming"
    assert inbox.sender == "ada@example.com"
    assert inbox.skip is False
    assert inbox.conversation_key if False else inbox.thread_id == "th1"

    sent = parse_gmail_message(
        _gmail_message(
            gmail_id="out1",
            thread_id="th1",
            labels=["SENT"],
            sender="pilot.inbox@investhome.com.tr",
            to="ada@example.com",
            subject="Re: Tapu sorusu",
            text="Tabii, belgeleri paylaşıyorum",
        ),
        account_email="pilot.inbox@investhome.com.tr",
    )
    assert sent.direction == "outgoing"

    spam = parse_gmail_message(
        _gmail_message(
            gmail_id="sp1",
            thread_id="thx",
            labels=["SPAM"],
            sender="spam@example.com",
            to="pilot.inbox@investhome.com.tr",
            subject="Win money",
            text="nope",
        )
    )
    assert spam.skip is True


def test_gmail_sync_ingests_inbox_sent_attachments_and_dedupes(
    client: TestClient, db, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "docs"))
    get_settings.cache_clear()
    from investhome_api.services.storage.factory import get_storage_provider

    get_storage_provider.cache_clear()
    start = client.post("/crm/settings/communication-accounts/gmail/authorize")
    state = parse_qs(urlparse(start.json()["authorize_url"]).query)["state"][0]
    monkeypatch.setattr(
        gmail_oauth,
        "exchange_authorization_code",
        lambda **kwargs: {"access_token": "a", "refresh_token": "r", "expires_in": 3600},
    )
    monkeypatch.setattr(
        gmail_oauth,
        "fetch_google_userinfo",
        lambda token: {"email": "pilot.inbox@investhome.com.tr", "sub": "sub-1"},
    )
    monkeypatch.setattr("investhome_api.api.routes.crm_live_communications.enqueue_gmail_sync", lambda *a, **k: None)
    callback = client.get(
        "/crm/settings/communication-accounts/gmail/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    account_id = parse_qs(urlparse(callback.headers["location"]).query)["account_id"][0]

    contact = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Ada Buyer",
            "primary_email": "ada@example.com",
        },
    ).json()["contact"]

    when = datetime.now(UTC) - timedelta(days=2)
    inbox = _gmail_message(
        gmail_id="gm-in-1",
        thread_id="thread-ada",
        labels=["INBOX"],
        sender="ada@example.com",
        to="pilot.inbox@investhome.com.tr",
        subject="Tapu sorusu",
        text="Merhaba, daire",
        html="<p>Merhaba, daire</p>",
        when=when,
        filename="plan.pdf",
    )
    sent = _gmail_message(
        gmail_id="gm-out-1",
        thread_id="thread-ada",
        labels=["SENT"],
        sender="pilot.inbox@investhome.com.tr",
        to="ada@example.com",
        subject="Re: Tapu sorusu",
        text="Belgeler ektedir",
        when=when + timedelta(hours=1),
    )
    unmatched = _gmail_message(
        gmail_id="gm-unk-1",
        thread_id="thread-unk",
        labels=["INBOX"],
        sender="unknown.person@example.com",
        to="pilot.inbox@investhome.com.tr",
        subject="Kim bu",
        text="Eşleşmeyen",
        when=when,
    )
    fake = FakeMailbox([inbox, sent, unmatched])

    monkeypatch.setattr(
        "investhome_api.services.crm.gmail_sync.GoogleGmailMailbox",
        lambda account: fake,
    )
    sync = client.post(f"/crm/settings/communication-accounts/{account_id}/sync")
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["ok"] is True
    assert body["ingested"] >= 3

    again = client.post(f"/crm/settings/communication-accounts/{account_id}/sync")
    assert again.json()["duplicates"] >= 3

    db.expire_all()
    communications = list(db.scalars(select(CrmCommunication)).all())
    by_ext = {row.external_provider_id: row for row in communications}
    assert by_ext["gm-in-1"].contact_id == UUID(contact["id"])
    assert by_ext["gm-in-1"].activity_id is not None
    assert by_ext["gm-in-1"].conversation_key == "thread-ada"
    assert by_ext["gm-out-1"].direction == "outbound"
    assert by_ext["gm-unk-1"].match_status == "unmatched"
    assert by_ext["gm-unk-1"].activity_id is None
    assert db.scalar(
        select(CrmCommunicationAttachment).where(CrmCommunicationAttachment.file_name == "plan.pdf")
    )

    unmatched_list = client.get("/crm/live-communications/unmatched")
    assert unmatched_list.status_code == 200
    assert any(item["subject"] == "Kim bu" for item in unmatched_list.json()["items"])


def test_gmail_does_not_duplicate_bitrix_timeline(client: TestClient, db) -> None:
    contact = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Bitrix Person",
            "primary_email": "bitrix.person@example.com",
        },
    ).json()["contact"]
    when = datetime.now(UTC).replace(microsecond=0)
    activity = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=UUID(contact["id"]),
        activity_type=CrmActivityType.EMAIL,
        activity_category=CrmActivityCategory.COMMUNICATION,
        title="E-posta: Sözleşme taraması",
        description="from: bitrix.person@example.com",
        status=CrmActivityStatus.COMPLETED,
        start_date=when,
        metadata_json={"bitrix_history": {"kind": "email", "source": "bitrix", "rfc_message_id": "old-bitrix-1"}},
    )
    db.add(activity)
    db.commit()
    activity_id = activity.id

    ingested = client.post(
        "/crm/live-communications/ingest",
        json={
            "channel": "email",
            "direction": "incoming",
            "source": "live_email",
            "sender": "bitrix.person@example.com",
            "subject": "Sözleşme taraması",
            "body_text": "from: bitrix.person@example.com",
            "occurred_at": when.isoformat(),
            "external_provider_id": "gm-bitrix-dup",
            "rfc_message_id": "old-bitrix-1",
        },
    )
    assert ingested.status_code == 200, ingested.text
    body = ingested.json()
    assert body["created"] is True
    db.expire_all()
    comm = db.get(CrmCommunication, UUID(str(body["id"])))
    assert comm is not None
    assert comm.activity_id is None
    assert comm.metadata_json.get("skip_timeline") is True
    activity = db.get(CrmActivity, activity_id)
    assert activity is not None
    assert activity.metadata_json["bitrix_history"]["source"] == "bitrix"
    email_count = len(
        list(
            db.scalars(
                select(CrmActivity).where(
                    CrmActivity.entity_id == UUID(contact["id"]),
                    CrmActivity.activity_type == CrmActivityType.EMAIL,
                )
            ).all()
        )
    )
    assert email_count == 1
