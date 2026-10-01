"""Short-lived one-time MFA login challenges.

Redis is the production store. Challenge payloads contain only user_id and
created_at — never passwords, TOTP secrets, or recovery codes. The plaintext
challenge token is returned to the client once and stored only as a SHA-256
digest. Production Redis failures fail closed (503).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.services.mfa_enforcement import PURPOSE_ENROLLMENT, PURPOSE_LOGIN

logger = get_logger("investhome.auth.mfa")

CHALLENGE_TTL_SECONDS = 5 * 60
_KEY_PREFIX = "auth:mfa:challenge:"
_USER_INDEX_PREFIX = "auth:mfa:challenge:user:"
GENERIC_UNAVAILABLE_MESSAGE = "Login temporarily unavailable. Try again later."
_VALID_PURPOSES = {PURPOSE_LOGIN, PURPOSE_ENROLLMENT}


class MfaChallengeStoreError(Exception):
    """Raised when the challenge backend cannot apply the policy."""


@dataclass(frozen=True)
class MfaChallenge:
    user_id: str
    created_at: float
    purpose: str = PURPOSE_LOGIN


class MfaChallengeStore(Protocol):
    def put(
        self, token_digest: str, user_id: str, ttl_seconds: int, purpose: str = PURPOSE_LOGIN
    ) -> None: ...

    def get(self, token_digest: str) -> MfaChallenge | None: ...

    def consume(self, token_digest: str) -> MfaChallenge | None: ...

    def drop_user_index(self, user_id: str, token_digest: str) -> None: ...

    def drop_all_for_user(self, user_id: str) -> None: ...


class InMemoryMfaChallengeStore:
    """Process-local challenges for tests and non-production Redis fallback."""

    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[MfaChallenge, float]] = {}
        self._user_index: dict[str, str] = {}
        self._now = now or time.time

    def _prune_locked(self, token_digest: str) -> MfaChallenge | None:
        entry = self._entries.get(token_digest)
        if entry is None:
            return None
        challenge, expires_at = entry
        if expires_at <= self._now():
            self._entries.pop(token_digest, None)
            indexed = self._user_index.get(challenge.user_id)
            if indexed == token_digest:
                self._user_index.pop(challenge.user_id, None)
            return None
        return challenge

    def put(
        self, token_digest: str, user_id: str, ttl_seconds: int, purpose: str = PURPOSE_LOGIN
    ) -> None:
        now = self._now()
        with self._lock:
            previous = self._user_index.get(user_id)
            if previous:
                self._entries.pop(previous, None)
            self._entries[token_digest] = (
                MfaChallenge(user_id=user_id, created_at=now, purpose=purpose),
                now + ttl_seconds,
            )
            self._user_index[user_id] = token_digest

    def get(self, token_digest: str) -> MfaChallenge | None:
        with self._lock:
            return self._prune_locked(token_digest)

    def consume(self, token_digest: str) -> MfaChallenge | None:
        with self._lock:
            challenge = self._prune_locked(token_digest)
            if challenge is None:
                return None
            self._entries.pop(token_digest, None)
            if self._user_index.get(challenge.user_id) == token_digest:
                self._user_index.pop(challenge.user_id, None)
            return challenge

    def drop_user_index(self, user_id: str, token_digest: str) -> None:
        with self._lock:
            if self._user_index.get(user_id) == token_digest:
                self._user_index.pop(user_id, None)

    def drop_all_for_user(self, user_id: str) -> None:
        with self._lock:
            previous = self._user_index.pop(user_id, None)
            if previous:
                self._entries.pop(previous, None)

    def expire_for_tests(self, token_digest: str) -> None:
        with self._lock:
            entry = self._entries.get(token_digest)
            if entry is None:
                return
            challenge, _expires_at = entry
            self._entries[token_digest] = (challenge, 0.0)


class RedisMfaChallengeStore:
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

    def put(
        self, token_digest: str, user_id: str, ttl_seconds: int, purpose: str = PURPOSE_LOGIN
    ) -> None:
        try:
            client = self._redis()
            user_key = f"{_USER_INDEX_PREFIX}{user_id}"
            previous = client.get(user_key)
            if previous:
                client.delete(f"{_KEY_PREFIX}{previous}")
            payload = json.dumps(
                {
                    "user_id": user_id,
                    "created_at": time.time(),
                    "purpose": purpose if purpose in _VALID_PURPOSES else PURPOSE_LOGIN,
                }
            )
            client.setex(f"{_KEY_PREFIX}{token_digest}", ttl_seconds, payload)
            client.setex(user_key, ttl_seconds, token_digest)
        except Exception as exc:
            raise MfaChallengeStoreError("redis challenge put failed") from exc

    def get(self, token_digest: str) -> MfaChallenge | None:
        try:
            client = self._redis()
            raw = client.get(f"{_KEY_PREFIX}{token_digest}")
            return _parse_payload(raw)
        except MfaChallengeStoreError:
            raise
        except Exception as exc:
            raise MfaChallengeStoreError("redis challenge get failed") from exc

    def consume(self, token_digest: str) -> MfaChallenge | None:
        try:
            client = self._redis()
            key = f"{_KEY_PREFIX}{token_digest}"
            getter = getattr(client, "getdel", None)
            raw = getter(key) if callable(getter) else None
            if raw is None and getter is None:
                raw = client.get(key)
                if raw is not None:
                    client.delete(key)
            challenge = _parse_payload(raw)
            if challenge is not None:
                indexed = client.get(f"{_USER_INDEX_PREFIX}{challenge.user_id}")
                if indexed == token_digest:
                    client.delete(f"{_USER_INDEX_PREFIX}{challenge.user_id}")
            return challenge
        except Exception as exc:
            raise MfaChallengeStoreError("redis challenge consume failed") from exc

    def drop_user_index(self, user_id: str, token_digest: str) -> None:
        try:
            client = self._redis()
            user_key = f"{_USER_INDEX_PREFIX}{user_id}"
            indexed = client.get(user_key)
            if indexed == token_digest:
                client.delete(user_key)
        except Exception as exc:
            raise MfaChallengeStoreError("redis challenge index drop failed") from exc

    def drop_all_for_user(self, user_id: str) -> None:
        try:
            client = self._redis()
            user_key = f"{_USER_INDEX_PREFIX}{user_id}"
            previous = client.get(user_key)
            if previous:
                client.delete(f"{_KEY_PREFIX}{previous}")
            client.delete(user_key)
        except Exception as exc:
            raise MfaChallengeStoreError("redis challenge user drop failed") from exc


def _parse_payload(raw: object) -> MfaChallenge | None:
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            return None
        user_id = data.get("user_id")
        created_at = data.get("created_at")
        purpose = str(data.get("purpose") or PURPOSE_LOGIN)
        if purpose not in _VALID_PURPOSES:
            purpose = PURPOSE_LOGIN
        if not user_id:
            return None
        return MfaChallenge(
            user_id=str(user_id),
            created_at=float(created_at or 0),
            purpose=purpose,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


_store: MfaChallengeStore | None = None
_memory_fallback = InMemoryMfaChallengeStore()


def reset_mfa_challenge_store_for_tests(store: MfaChallengeStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryMfaChallengeStore()
    _store = store if store is not None else _memory_fallback


def get_mfa_challenge_store() -> MfaChallengeStore:
    global _store
    if _store is None:
        _store = RedisMfaChallengeStore()
    return _store


def hash_challenge_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _raise_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=GENERIC_UNAVAILABLE_MESSAGE,
    )


def _with_store(op_name: str, callback):
    store = get_mfa_challenge_store()
    try:
        return callback(store)
    except MfaChallengeStoreError:
        logger.exception("mfa_challenge_backend_failure op=%s", op_name)
        settings = get_settings()
        if settings.environment.lower() == "production":
            _raise_unavailable()
        logger.error(
            "mfa_challenge_using_memory_fallback op=%s environment=%s",
            op_name,
            settings.environment,
        )
        return callback(_memory_fallback)


def create_mfa_challenge(*, user_id: str, purpose: str = PURPOSE_LOGIN) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    digest = hash_challenge_token(token)
    kind = purpose if purpose in _VALID_PURPOSES else PURPOSE_LOGIN

    def _put(store: MfaChallengeStore) -> None:
        store.put(digest, user_id, CHALLENGE_TTL_SECONDS, kind)

    _with_store("put", _put)
    if kind == PURPOSE_ENROLLMENT:
        logger.info("mfa_enrollment_challenge_issued user_id=%s", user_id)
    else:
        logger.info("mfa_login_challenge_issued user_id=%s", user_id)
    return token, CHALLENGE_TTL_SECONDS


def peek_mfa_challenge(token: str) -> MfaChallenge | None:
    digest = hash_challenge_token(token)

    def _get(store: MfaChallengeStore) -> MfaChallenge | None:
        return store.get(digest)

    return _with_store("get", _get)


def consume_mfa_challenge(token: str) -> MfaChallenge | None:
    digest = hash_challenge_token(token)

    def _consume(store: MfaChallengeStore) -> MfaChallenge | None:
        return store.consume(digest)

    challenge = _with_store("consume", _consume)
    if challenge is not None:
        if challenge.purpose == PURPOSE_ENROLLMENT:
            logger.info("mfa_enrollment_challenge_consumed user_id=%s", challenge.user_id)
        else:
            logger.info("mfa_login_challenge_consumed user_id=%s", challenge.user_id)
    return challenge


def expire_mfa_challenge_for_tests(token: str) -> None:
    digest = hash_challenge_token(token)
    store = get_mfa_challenge_store()
    expire = getattr(store, "expire_for_tests", None)
    if callable(expire):
        expire(digest)
        return
    store.consume(digest)


def invalidate_mfa_challenges_for_user(user_id: str) -> None:
    """Best-effort drop of pending login challenges. Never logs the token."""
    try:
        get_mfa_challenge_store().drop_all_for_user(user_id)
    except Exception:
        logger.warning("mfa_challenge_invalidate_failed user_id=%s", user_id)
