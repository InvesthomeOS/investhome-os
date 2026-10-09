"""Facebook / Instagram outbound send: Graph API, auth, fail-closed, CRM storage."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.sales import SalesOpportunity
from investhome_api.services.crm import meta_send, meta_webhook as meta
from investhome_api.services.crm.communication_feed import list_communication_feed
from investhome_api.services.crm.meta_send import (
    FACEBOOK_MESSAGES_URL,
    PUBLIC_INSTAGRAM_NOT_CONFIGURED,
    PUBLIC_NOT_CONFIGURED,
    PUBLIC_SEND_FAILED,
    instagram_messages_url,
)

from test_meta_webhook import (
    APP_SECRET,
    IG_APP_SECRET,
    PAGE_ID,
    VERIFY_TOKEN,
    WEBHOOK_PATH,
    _ig_payload,
    _payload,
    _sign,
)

PAGE_TOKEN = "unit-test-meta-page-access-token"
IG_TOKEN = "unit-test-meta-instagram-access-token"
IG_ACCOUNT_ID = "17841411111111111"
SEND_PATH = "/crm/live-communications/send"


@pytest.fixture(autouse=True)
def _meta_send_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("META_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("META_INSTAGRAM_APP_SECRET", IG_APP_SECRET)
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("META_PAGE_ID", PAGE_ID)
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()
    meta.reset_meta_idempotency_for_tests()
    yield
    meta.reset_meta_idempotency_for_tests()
    get_settings.cache_clear()


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200, response.text


def _inbound_facebook(client: TestClient, *, sender: str, text: str = "Gelen FB") -> str:
    message_id = f"mid.{uuid4().hex}"
    body = json.dumps(_payload(message_id=message_id, sender=sender, text=text), separators=(",", ":")).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )
    assert response.status_code == 200, response.text
    return sender


def _inbound_instagram(client: TestClient, *, sender: str, text: str = "Gelen IG") -> str:
    message_id = f"mid.{uuid4().hex}"
    body = json.dumps(_ig_payload(message_id=message_id, sender=sender, text=text), separators=(",", ":")).encode("utf-8")
    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body, IG_APP_SECRET)},
    )
    assert response.status_code == 200, response.text
    return sender


def _contact_for(db: Session, sender: str, *, instagram: bool = False) -> CrmContact:
    contacts = list(db.scalars(select(CrmContact)).all())
    key = "instagram_igsid" if instagram else "facebook_psid"
    for contact in contacts:
        meta_json = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
        if meta_json.get(key) == sender:
            return contact
    raise AssertionError("contact not found")


def test_facebook_outbound_success_stores_once(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sender = "1029384756101111"
    _inbound_facebook(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender)
    _enable_instagram_send(monkeypatch)
    calls: list[dict] = []

    def _fake_post(url: str, payload: dict, token: str):
        assert token == PAGE_TOKEN
        assert token != IG_TOKEN
        assert url == FACEBOOK_MESSAGES_URL
        assert "access_token" not in url
        assert "graph.instagram.com" not in url
        calls.append({"url": url, "payload": payload, "token": token})
        return _DummyResponse(200, {"message_id": "mid.out.fb.1", "recipient_id": sender})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    payload = {"channel": "facebook", "contact_id": str(contact.id), "conversation_key": sender, "text": "Cevap FB"}
    first = client.post(SEND_PATH, json=payload)
    second = client.post(SEND_PATH, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    body = first.json()
    assert PAGE_TOKEN not in first.text
    assert APP_SECRET not in first.text
    assert body["channel"] == "facebook"
    assert body["direction"] == "outbound"
    assert body["provider_message_id"] == "mid.out.fb.1"
    assert body["contact_id"] == str(contact.id)
    assert body["duplicate"] is False
    assert second.json()["duplicate"] is True
    db.expire_all()
    outgoing = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.channel == "facebook",
                CrmCommunication.direction == "outbound",
            )
        ).all()
    )
    assert len(outgoing) == 1
    assert outgoing[0].external_provider_id == "mid.out.fb.1"
    assert outgoing[0].contact_id == contact.id
    assert (outgoing[0].metadata_json or {}).get("lead_id")
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="facebook", page=1, page_size=25)
    previews = [item.preview for item in feed.items if item.channel == "facebook"]
    assert previews.count("Cevap FB") == 1
    assert len(calls) >= 1


def test_facebook_outbound_graph_failure_is_visible(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sender = "1029384756102222"
    _inbound_facebook(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender)

    def _fake_post(url: str, payload: dict, token: str):
        assert url == FACEBOOK_MESSAGES_URL
        return _DummyResponse(400, {"error": {"message": "fail", "code": 10}})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    before = int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0)
    response = client.post(
        SEND_PATH,
        json={"channel": "facebook", "contact_id": str(contact.id), "conversation_key": sender, "text": "Olmasin"},
    )
    assert response.status_code == 502, response.text
    assert response.json()["detail"] == PUBLIC_SEND_FAILED
    assert PAGE_TOKEN not in response.text
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == before
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_facebook_outbound_missing_token_fails_closed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = "1029384756103333"
    _inbound_facebook(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender)
    monkeypatch.delenv("META_PAGE_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    called = {"n": 0}

    def _fake_post(url: str, payload: dict, token: str):
        called["n"] += 1
        return _DummyResponse(200, {"message_id": "should-not"})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    response = client.post(
        SEND_PATH,
        json={"channel": "facebook", "contact_id": str(contact.id), "conversation_key": sender, "text": "Token yok"},
    )
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == PUBLIC_NOT_CONFIGURED
    assert called["n"] == 0
    assert PAGE_TOKEN not in response.text


def _enable_instagram_send(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", IG_ACCOUNT_ID)
    get_settings.cache_clear()


def test_instagram_outbound_success_and_failure(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sender = "17841400009999999"
    _inbound_instagram(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender, instagram=True)
    _enable_instagram_send(monkeypatch)

    def _ok(url: str, payload: dict, token: str):
        assert token == IG_TOKEN
        assert token != PAGE_TOKEN
        assert url == instagram_messages_url(IG_ACCOUNT_ID)
        assert url.startswith("https://graph.instagram.com/")
        assert FACEBOOK_MESSAGES_URL not in url
        assert "graph.facebook.com" not in url
        assert "access_token" not in url
        assert payload["recipient"]["id"] == sender
        return _DummyResponse(200, {"message_id": "mid.out.ig.1", "recipient_id": sender})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _ok)
    ok = client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "Cevap IG"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["channel"] == "instagram"
    assert ok.json()["direction"] == "outbound"
    assert ok.json()["provider_message_id"] == "mid.out.ig.1"
    assert PAGE_TOKEN not in ok.text
    assert IG_TOKEN not in ok.text
    db.expire_all()
    outgoing = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.channel == "instagram",
            CrmCommunication.direction == "outbound",
        )
    )
    assert outgoing is not None
    assert outgoing.contact_id == contact.id
    lead = db.scalar(select(Lead))
    assert lead is not None
    assert (outgoing.metadata_json or {}).get("lead_id") == str(lead.id)
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="instagram", page=1, page_size=25)
    assert sum(1 for item in feed.items if item.preview == "Cevap IG") == 1

    def _fail(url: str, payload: dict, token: str):
        assert url == instagram_messages_url(IG_ACCOUNT_ID)
        assert token == IG_TOKEN
        return _DummyResponse(500, {"error": {"message": "down"}})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fail)
    before = int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0)
    failed = client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "Hata IG"},
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == PUBLIC_SEND_FAILED
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == before


def test_facebook_outbound_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.post(
        SEND_PATH,
        json={"channel": "facebook", "contact_id": str(uuid4()), "text": "Nope"},
    )
    assert response.status_code == 401
    assert PAGE_TOKEN not in response.text


def test_facebook_outbound_readonly_forbidden(auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sender = "1029384756104444"
    _inbound_facebook(auth_client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender)
    monkeypatch.setattr(
        meta_send,
        "_post_graph_messages",
        lambda url, payload, token: _DummyResponse(200, {"message_id": "should-not"}),
    )
    _login(auth_client, "readonly@example.com")
    denied = auth_client.post(
        SEND_PATH,
        json={"channel": "facebook", "contact_id": str(contact.id), "conversation_key": sender, "text": "Yetki yok"},
    )
    assert denied.status_code == 403
    assert PAGE_TOKEN not in denied.text


def test_instagram_outbound_auth_admin_allowed(auth_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sender = "17841400008888888"
    _inbound_instagram(auth_client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender, instagram=True)
    _enable_instagram_send(monkeypatch)

    def _ok(url: str, payload: dict, token: str):
        assert token == IG_TOKEN
        assert token != PAGE_TOKEN
        assert url == instagram_messages_url(IG_ACCOUNT_ID)
        return _DummyResponse(200, {"message_id": "mid.out.ig.auth", "recipient_id": sender})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _ok)
    _login(auth_client, "admin@example.com")
    allowed = auth_client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "Admin IG"},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["provider_message_id"] == "mid.out.ig.auth"
    assert PAGE_TOKEN not in allowed.text
    assert IG_TOKEN not in allowed.text
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_instagram_outbound_never_falls_back_to_facebook_token(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = "17841400007777777"
    _inbound_instagram(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender, instagram=True)
    monkeypatch.delenv("META_INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("META_INSTAGRAM_ACCOUNT_ID", raising=False)
    get_settings.cache_clear()
    called: list[tuple[str, str]] = []

    def _fake_post(url: str, payload: dict, token: str):
        called.append((url, token))
        return _DummyResponse(200, {"message_id": "should-not"})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    response = client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "Fallback yok"},
    )
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == PUBLIC_INSTAGRAM_NOT_CONFIGURED
    assert called == []
    assert PAGE_TOKEN not in response.text


def test_instagram_outbound_missing_account_id_fails_closed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = "17841400006666666"
    _inbound_instagram(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender, instagram=True)
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    monkeypatch.delenv("META_INSTAGRAM_ACCOUNT_ID", raising=False)
    get_settings.cache_clear()
    called = {"n": 0}

    def _fake_post(url: str, payload: dict, token: str):
        called["n"] += 1
        return _DummyResponse(200, {"message_id": "should-not"})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    response = client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "Account yok"},
    )
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == PUBLIC_INSTAGRAM_NOT_CONFIGURED
    assert called["n"] == 0
    assert IG_TOKEN not in response.text


def test_instagram_outbound_missing_token_fails_closed(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = "17841400005555555"
    _inbound_instagram(client, sender=sender)
    db.expire_all()
    contact = _contact_for(db, sender, instagram=True)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", IG_ACCOUNT_ID)
    monkeypatch.delenv("META_INSTAGRAM_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    called = {"n": 0}

    def _fake_post(url: str, payload: dict, token: str):
        called["n"] += 1
        return _DummyResponse(200, {"message_id": "should-not"})

    monkeypatch.setattr(meta_send, "_post_graph_messages", _fake_post)
    response = client.post(
        SEND_PATH,
        json={"channel": "instagram", "contact_id": str(contact.id), "conversation_key": sender, "text": "IG token yok"},
    )
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == PUBLIC_INSTAGRAM_NOT_CONFIGURED
    assert called["n"] == 0
    assert PAGE_TOKEN not in response.text
