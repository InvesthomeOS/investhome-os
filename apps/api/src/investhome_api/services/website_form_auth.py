"""HMAC authentication, timestamp skew, nonce replay, and idempotency for website forms.

WordPress validates reCAPTCHA, then POSTs the JSON body with:
  X-Investhome-Timestamp  unix seconds
  X-Investhome-Nonce      unique 16-64 char token
  X-Investhome-Signature  hex HMAC-SHA256(secret, "{timestamp}.{nonce}.{raw_body}")

The secret lives only in server env (WEBSITE_FORM_INGEST_SECRET). Never send it to browsers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger

logger = get_logger("investhome.website_form.auth")

TIMESTAMP_HEADER = "X-Investhome-Timestamp"
NONCE_HEADER = "X-Investhome-Nonce"
SIGNATURE_HEADER = "X-Investhome-Signature"

GENERIC_FORBIDDEN = "Forbidden"
GENERIC_UNAVAILABLE = "Form temporarily unavailable. Try again later."
GENERIC_DUPLICATE = "Duplicate request"

MAX_SKEW_SECONDS = 300
NONCE_TTL_SECONDS = 600
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 60 * 60
MIN_SECRET_LENGTH = 32
_NONCE_RE = re.compile(r"^[A-Za-z0-9._-]{16,64}$")
_PENDING = "__pending__"

_NONCE_PREFIX = "websiteform:nonce:"
_IDEMP_PREFIX = "websiteform:idemp:"


class WebsiteFormAuthError(Exception):
    def __init__(self, status_code: int, public_detail: str) -> None:
        super().__init__(public_detail)
        self.status_code = status_code
        self.public_detail = public_detail


class WebsiteFormStoreError(Exception):
    """Raised when Redis cannot apply nonce/idempotency policy."""


class WebsiteFormReplayStore(Protocol):
    def claim(self, key: str, ttl_seconds: int) -> bool: ...

    def get(self, key: str) -> str | None: ...

    def put(self, key: str, value: str, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...


@dataclass
class _MemoryEntry:
    value: str
    expires_at: float


class InMemoryWebsiteFormReplayStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, _MemoryEntry] = {}
        self._now = now or time.time

    def _purge_unlocked(self, now: float) -> None:
        expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired:
            self._entries.pop(key, None)

    def claim(self, key: str, ttl_seconds: int) -> bool:
        now = self._now()
        with self._lock:
            self._purge_unlocked(now)
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return False
            self._entries[key] = _MemoryEntry(value="1", expires_at=now + ttl_seconds)
            return True

    def get(self, key: str) -> str | None:
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.value

    def put(self, key: str, value: str, ttl_seconds: int) -> None:
        now = self._now()
        with self._lock:
            self._entries[key] = _MemoryEntry(value=value, expires_at=now + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)


class RedisWebsiteFormReplayStore:
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
            raise WebsiteFormStoreError("redis website-form nonce failed") from exc

    def get(self, key: str) -> str | None:
        try:
            client = self._redis()
            value = client.get(key)
            return str(value) if value is not None else None
        except Exception as exc:
            raise WebsiteFormStoreError("redis website-form idempotency get failed") from exc

    def put(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            client = self._redis()
            client.set(key, value, ex=max(1, ttl_seconds))
        except Exception as exc:
            raise WebsiteFormStoreError("redis website-form idempotency put failed") from exc

    def delete(self, key: str) -> None:
        try:
            client = self._redis()
            client.delete(key)
        except Exception as exc:
            raise WebsiteFormStoreError("redis website-form idempotency delete failed") from exc


_store: WebsiteFormReplayStore | None = None
_memory_fallback = InMemoryWebsiteFormReplayStore()


def reset_website_form_replay_for_tests(store: WebsiteFormReplayStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryWebsiteFormReplayStore()
    _store = store if store is not None else _memory_fallback


def get_website_form_replay_store() -> WebsiteFormReplayStore:
    global _store
    if _store is None:
        _store = RedisWebsiteFormReplayStore()
    return _store


def _is_production() -> bool:
    return (get_settings().environment or "").strip().lower() in {"production", "prod"}


def _with_store(op_name: str, callback):
    store = get_website_form_replay_store()
    try:
        return callback(store)
    except WebsiteFormStoreError:
        logger.exception("website_form_replay_backend_failure op=%s", op_name)
        if _is_production():
            raise WebsiteFormAuthError(503, GENERIC_UNAVAILABLE) from None
        logger.error("website_form_replay_using_memory_fallback op=%s", op_name)
        return callback(_memory_fallback)


def require_website_form_secret() -> str:
    secret = (get_settings().website_form_ingest_secret or "").strip()
    if len(secret) < MIN_SECRET_LENGTH:
        logger.warning("website_form_missing_or_short_secret")
        raise WebsiteFormAuthError(503, GENERIC_UNAVAILABLE)
    return secret


def _hashed(prefix: str, material: str) -> str:
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"


def _parse_timestamp(raw: str | None) -> int:
    if not raw or not raw.strip().isdigit():
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN)
    try:
        ts = int(raw.strip())
    except ValueError as exc:
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN) from exc
    now = int(time.time())
    if abs(now - ts) > MAX_SKEW_SECONDS:
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN)
    return ts


def _parse_nonce(raw: str | None) -> str:
    nonce = (raw or "").strip()
    if not _NONCE_RE.match(nonce):
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN)
    return nonce


def _extract_signature(header: str | None) -> str:
    provided = (header or "").strip()
    if provided.lower().startswith("sha256="):
        provided = provided[7:].strip()
    if len(provided) != 64:
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN)
    try:
        bytes.fromhex(provided)
    except ValueError as exc:
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN) from exc
    return provided.lower()


def verify_website_form_signature(
    *,
    secret: str,
    timestamp: str,
    nonce: str,
    raw_body: bytes,
    signature_header: str | None,
) -> bool:
    provided = _extract_signature(signature_header)
    material = f"{timestamp}.{nonce}.".encode("utf-8") + raw_body
    expected = hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    if len(provided) != len(expected):
        return False
    return hmac.compare_digest(provided, expected)


def authenticate_website_form_request(
    *,
    raw_body: bytes,
    timestamp_header: str | None,
    nonce_header: str | None,
    signature_header: str | None,
) -> None:
    secret = require_website_form_secret()
    timestamp = (timestamp_header or "").strip()
    _parse_timestamp(timestamp)
    nonce = _parse_nonce(nonce_header)
    if not verify_website_form_signature(
        secret=secret,
        timestamp=timestamp,
        nonce=nonce,
        raw_body=raw_body,
        signature_header=signature_header,
    ):
        logger.warning("website_form_invalid_signature")
        raise WebsiteFormAuthError(403, GENERIC_FORBIDDEN)

    nonce_key = _hashed(_NONCE_PREFIX, nonce)

    def _claim(store: WebsiteFormReplayStore) -> bool:
        return store.claim(nonce_key, NONCE_TTL_SECONDS)

    claimed = _with_store("nonce_claim", _claim)
    if not claimed:
        raise WebsiteFormAuthError(409, GENERIC_DUPLICATE)


def idempotency_lookup(idempotency_key: str) -> dict | None:
    redis_key = _hashed(_IDEMP_PREFIX, idempotency_key.strip())

    def _get(store: WebsiteFormReplayStore) -> str | None:
        return store.get(redis_key)

    raw = _with_store("idemp_get", _get)
    if not raw or raw == _PENDING:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def idempotency_claim(idempotency_key: str) -> bool:
    redis_key = _hashed(_IDEMP_PREFIX, idempotency_key.strip())

    def _claim(store: WebsiteFormReplayStore) -> bool:
        return store.claim(redis_key, 60)

    return bool(_with_store("idemp_claim", _claim))


def idempotency_store(idempotency_key: str, payload: dict) -> None:
    redis_key = _hashed(_IDEMP_PREFIX, idempotency_key.strip())
    encoded = json.dumps(payload, separators=(",", ":"), default=str)

    def _put(store: WebsiteFormReplayStore) -> None:
        store.put(redis_key, encoded, IDEMPOTENCY_TTL_SECONDS)

    _with_store("idemp_put", _put)


def idempotency_clear(idempotency_key: str) -> None:
    redis_key = _hashed(_IDEMP_PREFIX, idempotency_key.strip())

    def _delete(store: WebsiteFormReplayStore) -> None:
        store.delete(redis_key)

    _with_store("idemp_clear", _delete)
