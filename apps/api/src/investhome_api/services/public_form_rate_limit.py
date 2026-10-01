"""Redis-backed rate limits for unauthenticated public form posts."""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger

logger = get_logger("investhome.public_form.rate_limit")

GENERIC_RATE_LIMIT_MESSAGE = "Too many submissions. Try again later."
GENERIC_UNAVAILABLE_MESSAGE = "Form temporarily unavailable. Try again later."

_BURST_PREFIX = "publicform:burst:"
_DAILY_PREFIX = "publicform:daily:"


class PublicFormRateLimitStoreError(Exception):
    """Raised when the rate-limit backend cannot apply the policy."""


class PublicFormRateStore(Protocol):
    def hit(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Record one hit. Returns (allowed, retry_after_seconds)."""


@dataclass
class _MemoryEntry:
    count: int
    expires_at: float


class InMemoryPublicFormRateStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, _MemoryEntry] = {}
        self._now = now or time.time

    def hit(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at <= now:
                self._entries[key] = _MemoryEntry(count=1, expires_at=now + window_seconds)
                return True, 0
            entry.count += 1
            remaining = max(1, int(entry.expires_at - now))
            if entry.count > limit:
                return False, remaining
            return True, 0


class RedisPublicFormRateStore:
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

    def hit(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        try:
            client = self._redis()
            count = int(client.incr(key))
            if count == 1:
                client.expire(key, window_seconds)
            ttl = int(client.ttl(key))
            if ttl < 0:
                client.expire(key, window_seconds)
                ttl = window_seconds
            if count > limit:
                return False, max(1, ttl)
            return True, 0
        except Exception as exc:
            raise PublicFormRateLimitStoreError("redis public-form hit failed") from exc


_store: PublicFormRateStore | None = None
_memory_fallback = InMemoryPublicFormRateStore()


def reset_public_form_rate_limiter_for_tests(store: PublicFormRateStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryPublicFormRateStore()
    _store = store if store is not None else _memory_fallback


def get_public_form_rate_store() -> PublicFormRateStore:
    global _store
    if _store is None:
        _store = RedisPublicFormRateStore()
    return _store


def _hashed_key(prefix: str, form_slug: str, ip: str) -> str:
    material = f"{form_slug.strip().lower()}|{ip.strip()}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"


def _raise_limited(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=GENERIC_RATE_LIMIT_MESSAGE,
        headers={"Retry-After": str(retry_after)},
    )


def _raise_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=GENERIC_UNAVAILABLE_MESSAGE,
    )


def _with_store(op_name: str, callback):
    store = get_public_form_rate_store()
    try:
        return callback(store)
    except PublicFormRateLimitStoreError:
        logger.exception("public_form_rate_limit_backend_failure op=%s", op_name)
        settings = get_settings()
        if settings.environment.lower() == "production":
            _raise_unavailable()
        logger.error("public_form_rate_limit_using_memory_fallback op=%s", op_name)
        return callback(_memory_fallback)


def enforce_public_form_rate_limit(*, ip: str, form_slug: str) -> None:
    settings = get_settings()
    burst_key = _hashed_key(_BURST_PREFIX, form_slug, ip)
    daily_key = _hashed_key(_DAILY_PREFIX, form_slug, ip)
    burst_limit = max(1, settings.public_form_burst_limit)
    daily_limit = max(1, settings.public_form_daily_limit)
    burst_window = max(1, settings.public_form_burst_window_seconds)
    daily_window = max(1, settings.public_form_daily_window_seconds)

    def _hit(store: PublicFormRateStore) -> tuple[bool, int]:
        burst_ok, burst_retry = store.hit(
            burst_key, limit=burst_limit, window_seconds=burst_window
        )
        daily_ok, daily_retry = store.hit(
            daily_key, limit=daily_limit, window_seconds=daily_window
        )
        if burst_ok and daily_ok:
            return True, 0
        return False, max(burst_retry, daily_retry, 1)

    allowed, retry_after = _with_store("hit", _hit)
    if not allowed:
        logger.warning("public_form_rate_limited")
        _raise_limited(retry_after)
