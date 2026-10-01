"""WhatsApp/Meta inbound webhook signature, handshake, and replay protection."""

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

from investhome_api.config.settings import Settings, get_settings, validate_whatsapp_webhook_secrets
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.services.crm import whatsapp_webhook as wa

APP_SECRET = "unit-test-whatsapp-app-secret-32chars"
VERIFY_TOKEN = "unit-test-whatsapp-verify-token"
WEBHOOK_PATH = "/webhooks/whatsapp"


@pytest.fixture(autouse=True)
def _whatsapp_webhook_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    get_settings.cache_clear()
    wa.reset_whatsapp_idempotency_for_tests()
    yield
    wa.reset_whatsapp_idempotency_for_tests()
    get_settings.cache_clear()


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _payload(message_id: str, sender: str = "905551112233", text: str = "Merhaba") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender,
                                    "id": message_id,
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _post(
    client: TestClient,
    payload: dict,
    *,
    secret: str = APP_SECRET,
    signature: str | bool | None = True,
):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if signature is True:
        headers["X-Hub-Signature-256"] = _sign(body, secret)
    elif isinstance(signature, str):
        headers["X-Hub-Signature-256"] = signature
    return client.post(WEBHOOK_PATH, content=body, headers=headers), body


def test_valid_signature_accepted(client: TestClient, db: Session) -> None:
    message_id = f"wamid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["duplicate"] is False
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 1


def test_invalid_signature_rejected(client: TestClient, db: Session) -> None:
    message_id = f"wamid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id), signature="sha256=" + ("ab" * 32))
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 0


def test_missing_signature_rejected_in_production(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wa, "_is_production", lambda: True)
    message_id = f"wamid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id), signature=None)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_wrong_secret_rejected(client: TestClient) -> None:
    message_id = f"wamid.{uuid4().hex}"
    response, _body = _post(client, _payload(message_id), secret="wrong-whatsapp-app-secret-32charsx")
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


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


def test_duplicate_event_processed_only_once(client: TestClient, db: Session) -> None:
    message_id = f"wamid.{uuid4().hex}"
    payload = _payload(message_id, text="Once only")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 1


def test_replay_cannot_create_duplicate_crm_records(client: TestClient, db: Session) -> None:
    message_id = f"wamid.{uuid4().hex}"
    payload = _payload(message_id, text="Replay")
    _post(client, payload)
    wa.reset_whatsapp_idempotency_for_tests()
    replay, _ = _post(client, payload)
    assert replay.status_code == 200
    count = db.scalar(
        select(func.count()).select_from(CrmCommunication).where(
            CrmCommunication.external_provider_id == message_id
        )
    )
    assert int(count or 0) == 1


def test_production_missing_webhook_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)
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
    with pytest.raises(RuntimeError, match="WHATSAPP_APP_SECRET"):
        validate_whatsapp_webhook_secrets(settings)


def test_production_post_without_secret_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(wa, "_is_production", lambda: True)
    message_id = f"wamid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id))
    assert response.status_code == 503
    assert "secret" not in response.text.lower()


def test_malformed_webhook_logged_without_secrets(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    body = b"{not-json"
    with caplog.at_level(logging.WARNING):
        response = client.post(
            WEBHOOK_PATH,
            content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
        )
    assert response.status_code == 400
    joined = caplog.text
    assert "whatsapp_webhook_malformed" in joined
    assert APP_SECRET not in joined
    assert VERIFY_TOKEN not in joined


def test_internal_ingest_is_not_public_when_auth_enabled(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/crm/live-communications/ingest",
        json={"channel": "whatsapp", "sender": "905551112233", "body_text": "internal"},
    )
    assert response.status_code in {401, 403}


def test_signed_webhook_does_not_require_session(auth_client: TestClient) -> None:
    response, _ = _post(auth_client, _payload(f"wamid.{uuid4().hex}"))
    assert response.status_code == 200, response.text
    assert APP_SECRET not in response.text
    assert VERIFY_TOKEN not in response.text
