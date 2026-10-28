"""Wazzup API v3 inbound WhatsApp webhook.

The direct API-key account does not send an Authorization header.
The webhook URI carries WAZZUP_WEBHOOK_SECRET as the token query parameter.
This module does not call the Wazzup API and does not send WhatsApp messages.
"""

from __future__ import annotations

import hmac
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.services.crm.identity import parse_phone
from investhome_api.services.crm.live_ingest import ingest_live_message

logger = get_logger("investhome.wazzup.webhook")

IDEMPOTENCY_PREFIX = "wazzup:message:"
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_WEBHOOK_BYTES = 256_000
GENERIC_FORBIDDEN = "Forbidden"
GENERIC_UNAVAILABLE = "Webhook temporarily unavailable"
_CONTENT_TYPES = frozenset({"image", "audio", "video", "document"})


class WazzupWebhookRejected(Exception):
    def __init__(self, status_code: int, public_detail: str) -> None:
        super().__init__(public_detail)
        self.status_code = status_code
        self.public_detail = public_detail


class WazzupIdempotencyStoreError(Exception):
    """Raised when replay protection cannot be applied."""


class WazzupIdempotencyStore(Protocol):
    def claim(self, key: str, ttl_seconds: int) -> bool:
        """Return True when this key was newly claimed."""


@dataclass
class _MemoryEntry:
    expires_at: float


class InMemoryWazzupIdempotencyStore:
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


class RedisWazzupIdempotencyStore:
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
            raise WazzupIdempotencyStoreError("redis wazzup idempotency failed") from exc


_store: WazzupIdempotencyStore | None = None
_memory_fallback = InMemoryWazzupIdempotencyStore()


def reset_wazzup_idempotency_for_tests(store: WazzupIdempotencyStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryWazzupIdempotencyStore()
    _store = store if store is not None else _memory_fallback


def get_wazzup_idempotency_store() -> WazzupIdempotencyStore:
    global _store
    if _store is None:
        _store = RedisWazzupIdempotencyStore()
    return _store


def token_matches(*, configured: str, provided: str | None) -> bool:
    if not configured or provided is None:
        return False
    expected = configured.strip()
    given = provided.strip()
    if not expected or not given or len(expected) != len(given):
        return False
    return hmac.compare_digest(expected, given)


def require_wazzup_webhook_secret() -> str:
    secret = (get_settings().wazzup_webhook_secret or "").strip()
    if secret:
        return secret
    logger.warning("wazzup_webhook_missing_secret")
    raise WazzupWebhookRejected(503, GENERIC_UNAVAILABLE)


def _occurred(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _contact_name(message: dict[str, Any]) -> str:
    contact = message.get("contact")
    if not isinstance(contact, dict):
        return ""
    return str(contact.get("name") or "").strip()[:200]


def _metadata(message: dict[str, Any]) -> dict[str, Any]:
    message_type = str(message.get("type") or "").strip().lower()[:40]
    content_uri = str(message.get("contentUri") or "").strip()
    meta: dict[str, Any] = {
        "provider": "wazzup",
        "message_type": message_type,
        "content_present": bool(content_uri) and message_type in _CONTENT_TYPES,
    }
    channel_id = str(message.get("channelId") or "").strip()
    if channel_id:
        meta["channel_id"] = channel_id[:80]
    name = _contact_name(message)
    if name:
        meta["contact_name"] = name
    return meta


def _inbound_message(message: dict[str, Any]) -> dict[str, Any] | None:
    if str(message.get("chatType") or "").strip() != "whatsapp":
        return None
    if message.get("isEcho") is not False:
        return None
    if str(message.get("status") or "").strip() != "inbound":
        return None
    if message.get("isDeleted") is True:
        return None
    message_id = str(message.get("messageId") or "").strip()
    chat_id = str(message.get("chatId") or "").strip()
    if not message_id or not chat_id:
        return None
    parsed = parse_phone(chat_id)
    if parsed is None:
        return None
    conversation_key = parsed.e164.lstrip("+") if parsed.e164 else parsed.digits
    if not conversation_key:
        return None
    return {
        "channel": "whatsapp",
        "direction": "incoming",
        "source": "live_wazzup",
        "sender": chat_id,
        "body_text": str(message.get("text") or ""),
        "external_provider_id": message_id,
        "conversation_key": conversation_key,
        "occurred_at": _occurred(message.get("dateTime")),
        "metadata_json": _metadata(message),
    }


def _is_probe(payload: dict[str, Any]) -> bool:
    return payload.get("test") is True and "messages" not in payload and "statuses" not in payload


def process_wazzup_webhook(
    db: Session,
    *,
    raw_body: bytes,
    token: str | None,
) -> dict[str, Any]:
    if len(raw_body) > MAX_WEBHOOK_BYTES:
        logger.warning("wazzup_webhook_malformed reason=too_large")
        raise WazzupWebhookRejected(400, "invalid_request")
    secret = require_wazzup_webhook_secret()
    if not token_matches(configured=secret, provided=token):
        logger.warning("wazzup_webhook_token_rejected")
        raise WazzupWebhookRejected(403, GENERIC_FORBIDDEN)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("wazzup_webhook_malformed reason=invalid_json")
        raise WazzupWebhookRejected(400, "invalid_request") from None
    if not isinstance(payload, dict):
        logger.warning("wazzup_webhook_malformed reason=not_object")
        raise WazzupWebhookRejected(400, "invalid_request")
    if _is_probe(payload):
        logger.info("wazzup_webhook_probe")
        return {"ok": True, "created_ids": []}

    created_ids: list[UUID] = []
    store = get_wazzup_idempotency_store()
    messages = payload.get("messages") or []
    if not isinstance(messages, list):
        logger.warning("wazzup_webhook_malformed reason=messages")
        raise WazzupWebhookRejected(400, "invalid_request")
    for item in messages:
        if not isinstance(item, dict):
            continue
        mapped = _inbound_message(item)
        if mapped is None:
            continue
        message_id = str(mapped["external_provider_id"])
        try:
            claimed = store.claim(f"{IDEMPOTENCY_PREFIX}{message_id}", IDEMPOTENCY_TTL_SECONDS)
        except WazzupIdempotencyStoreError:
            logger.warning("wazzup_webhook_idempotency_unavailable")
            raise WazzupWebhookRejected(503, GENERIC_UNAVAILABLE) from None
        if not claimed:
            logger.info("wazzup_webhook_replay message_id=%s", message_id)
            continue
        _row, was_created = ingest_live_message(db, mapped, actor=None)
        if was_created:
            created_ids.append(_row.id)
    logger.info("wazzup_webhook_accepted created=%s", len(created_ids))
    return {"ok": True, "created_ids": created_ids}
