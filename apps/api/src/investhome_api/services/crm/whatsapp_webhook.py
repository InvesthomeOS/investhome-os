"""Meta WhatsApp inbound webhook: HMAC signature, handshake, replay protection.

Does not send outbound WhatsApp messages and does not expose internal ingest.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings, validate_whatsapp_webhook_secrets
from investhome_api.core.logging_config import get_logger
from investhome_api.services.crm.live_ingest import ingest_live_message

logger = get_logger("investhome.whatsapp.webhook")

SIGNATURE_HEADER = "X-Hub-Signature-256"
IDEMPOTENCY_PREFIX = "wa:webhook:idemp:"
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_WEBHOOK_BYTES = 256_000
GENERIC_FORBIDDEN = "Forbidden"
GENERIC_UNAVAILABLE = "Webhook temporarily unavailable"


class WhatsAppWebhookRejected(Exception):
    def __init__(self, status_code: int, public_detail: str) -> None:
        super().__init__(public_detail)
        self.status_code = status_code
        self.public_detail = public_detail


class WhatsAppIdempotencyStoreError(Exception):
    """Raised when the replay-protection backend cannot apply the policy."""


class WhatsAppIdempotencyStore(Protocol):
    def claim(self, key: str, ttl_seconds: int) -> bool:
        """Return True if this key was newly claimed."""


@dataclass
class _MemoryEntry:
    expires_at: float


class InMemoryWhatsAppIdempotencyStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, _MemoryEntry] = {}
        self._now = now or time.time

    def claim(self, key: str, ttl_seconds: int) -> bool:
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return False
            self._entries[key] = _MemoryEntry(expires_at=now + ttl_seconds)
            return True

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class RedisWhatsAppIdempotencyStore:
    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def _redis(self) -> object:
        if self._client is not None:
            return self._client
        from redis import Redis

        settings = get_settings()
        self._client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            decode_responses=True,
        )
        return self._client

    def claim(self, key: str, ttl_seconds: int) -> bool:
        try:
            client = self._redis()
            created = client.set(key, "1", nx=True, ex=max(1, ttl_seconds))
            return bool(created)
        except Exception as exc:
            raise WhatsAppIdempotencyStoreError("redis whatsapp idempotency failed") from exc


_store: WhatsAppIdempotencyStore | None = None
_memory_fallback = InMemoryWhatsAppIdempotencyStore()


def reset_whatsapp_idempotency_for_tests(store: WhatsAppIdempotencyStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryWhatsAppIdempotencyStore()
    _store = store if store is not None else _memory_fallback


def get_whatsapp_idempotency_store() -> WhatsAppIdempotencyStore:
    global _store
    if _store is None:
        _store = RedisWhatsAppIdempotencyStore()
    return _store


def verify_meta_signature(*, app_secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not app_secret:
        return False
    provided = signature_header.strip()
    prefix = "sha256="
    if not provided.lower().startswith(prefix):
        return False
    digest = provided[len(prefix) :].strip()
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if len(digest) != len(expected):
        return False
    return hmac.compare_digest(digest.lower(), expected.lower())


def verify_token_matches(*, configured: str, provided: str | None) -> bool:
    if not configured or not provided:
        return False
    expected = configured.strip()
    token = provided.strip()
    if not expected or not token or len(expected) != len(token):
        return False
    return hmac.compare_digest(expected, token)


def _is_production() -> bool:
    return (get_settings().environment or "").strip().lower() in {"production", "prod"}


def require_whatsapp_app_secret() -> str:
    settings = get_settings()
    if _is_production():
        validate_whatsapp_webhook_secrets(settings)
    secret = (settings.whatsapp_app_secret or "").strip()
    if not secret:
        logger.warning("whatsapp_webhook_missing_app_secret")
        raise WhatsAppWebhookRejected(503, GENERIC_UNAVAILABLE)
    return secret


def require_whatsapp_verify_token() -> str:
    settings = get_settings()
    if _is_production():
        validate_whatsapp_webhook_secrets(settings)
    token = (settings.whatsapp_verify_token or "").strip()
    if not token:
        logger.warning("whatsapp_webhook_missing_verify_token")
        raise WhatsAppWebhookRejected(503, GENERIC_UNAVAILABLE)
    return token


def extract_idempotency_keys(payload: dict[str, Any], *, raw_body: bytes) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") if isinstance(change.get("value"), dict) else {}
            for message in value.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                mid = str(message.get("id") or "").strip()
                if mid and mid not in seen:
                    seen.add(mid)
                    keys.append(f"msg:{mid}")
            for status in value.get("statuses") or []:
                if not isinstance(status, dict):
                    continue
                sid = str(status.get("id") or "").strip()
                if sid and sid not in seen:
                    seen.add(sid)
                    keys.append(f"status:{sid}")
    if not keys:
        keys.append("body:" + hashlib.sha256(raw_body).hexdigest())
    return keys


def _claim_keys(keys: list[str]) -> tuple[list[str], list[str]]:
    store = get_whatsapp_idempotency_store()
    claimed: list[str] = []
    duplicates: list[str] = []

    def _run(active: WhatsAppIdempotencyStore) -> None:
        claimed.clear()
        duplicates.clear()
        for key in keys:
            redis_key = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(key.encode('utf-8')).hexdigest()}"
            if active.claim(redis_key, IDEMPOTENCY_TTL_SECONDS):
                claimed.append(key)
            else:
                duplicates.append(key)

    try:
        _run(store)
    except WhatsAppIdempotencyStoreError:
        logger.exception("whatsapp_webhook_idempotency_backend_failure")
        if _is_production():
            raise WhatsAppWebhookRejected(503, GENERIC_UNAVAILABLE) from None
        logger.error("whatsapp_webhook_idempotency_memory_fallback")
        _run(_memory_fallback)
    return claimed, duplicates


def _message_timestamp(raw: object) -> datetime | None:
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _ingest_new_messages(db: Session, payload: dict[str, Any], claimed: set[str]) -> int:
    created = 0
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") if isinstance(change.get("value"), dict) else {}
            for message in value.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                mid = str(message.get("id") or "").strip()
                if not mid or f"msg:{mid}" not in claimed:
                    continue
                sender = str(message.get("from") or "").strip()
                text_body = ""
                text_obj = message.get("text")
                if isinstance(text_obj, dict):
                    text_body = str(text_obj.get("body") or "")
                elif message.get("type") == "text":
                    text_body = str(message.get("body") or "")
                _, was_created = ingest_live_message(
                    db,
                    {
                        "channel": "whatsapp",
                        "direction": "incoming",
                        "source": "live_whatsapp",
                        "sender": sender,
                        "body_text": text_body,
                        "external_provider_id": mid,
                        "conversation_key": sender or mid,
                        "occurred_at": _message_timestamp(message.get("timestamp")),
                    },
                    actor=None,
                )
                if was_created:
                    created += 1
    return created


def handle_verification_challenge(
    *,
    hub_mode: str | None,
    hub_verify_token: str | None,
    hub_challenge: str | None,
) -> str:
    expected = require_whatsapp_verify_token()
    if (hub_mode or "").strip() != "subscribe":
        logger.warning("whatsapp_webhook_handshake_invalid_mode")
        raise WhatsAppWebhookRejected(403, GENERIC_FORBIDDEN)
    if not verify_token_matches(configured=expected, provided=hub_verify_token):
        logger.warning("whatsapp_webhook_handshake_token_mismatch")
        raise WhatsAppWebhookRejected(403, GENERIC_FORBIDDEN)
    challenge = (hub_challenge or "").strip()
    if not challenge or len(challenge) > 128 or any(ch.isspace() for ch in challenge):
        logger.warning("whatsapp_webhook_handshake_malformed_challenge")
        raise WhatsAppWebhookRejected(400, "invalid_request")
    return challenge


def process_whatsapp_webhook(
    db: Session,
    *,
    raw_body: bytes,
    signature_header: str | None,
) -> dict[str, Any]:
    if len(raw_body) > MAX_WEBHOOK_BYTES:
        logger.warning("whatsapp_webhook_malformed reason=too_large")
        raise WhatsAppWebhookRejected(400, "invalid_request")

    app_secret = require_whatsapp_app_secret()
    if not signature_header:
        logger.warning("whatsapp_webhook_signature_failure reason=missing")
        raise WhatsAppWebhookRejected(403, GENERIC_FORBIDDEN)
    if not verify_meta_signature(
        app_secret=app_secret,
        raw_body=raw_body,
        signature_header=signature_header,
    ):
        logger.warning("whatsapp_webhook_signature_failure reason=invalid")
        raise WhatsAppWebhookRejected(403, GENERIC_FORBIDDEN)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("whatsapp_webhook_malformed reason=invalid_json")
        raise WhatsAppWebhookRejected(400, "invalid_request") from None
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        logger.warning("whatsapp_webhook_malformed reason=unexpected_object")
        raise WhatsAppWebhookRejected(400, "invalid_request")

    keys = extract_idempotency_keys(payload, raw_body=raw_body)
    claimed, duplicates = _claim_keys(keys)
    if duplicates:
        logger.info("whatsapp_webhook_replay_duplicate count=%s", len(duplicates))
    if not claimed:
        return {"ok": True, "duplicate": True, "ingested": 0}

    ingested = _ingest_new_messages(db, payload, set(claimed))
    return {"ok": True, "duplicate": False, "ingested": ingested}
