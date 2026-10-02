"""Login brute-force protection: IP + identity counters in Redis.

Failed attempts are tracked independently per client IP and per normalized
email. Either dimension hitting the limit blocks further /auth/login attempts.
Successful login clears only the account (identity) counter.

Redis is the production store. Backend failures are logged and never fail open
silently: production rejects login (503); non-production falls back to a
process-local store that still enforces the same limits.
"""

from __future__ import annotations

import hashlib
import ipaddress
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Protocol

from fastapi import HTTPException, Request, status

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger

logger = get_logger("investhome.auth.rate_limit")

MAX_FAILED_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60
GENERIC_LOCKOUT_MESSAGE = "Too many login attempts. Try again later."
GENERIC_MFA_CONFIRM_LOCKOUT = "Too many verification attempts. Try again later."
GENERIC_UNAVAILABLE_MESSAGE = "Login temporarily unavailable. Try again later."

_KEY_PREFIX_IP = "auth:login:fail:ip:"
_KEY_PREFIX_ID = "auth:login:fail:id:"
_KEY_PREFIX_MFA_CONFIRM_IP = "auth:mfa:confirm:ip:"
_KEY_PREFIX_MFA_CONFIRM_USER = "auth:mfa:confirm:user:"
_KEY_PREFIX_MFA_VERIFY_IP = "auth:mfa:verify:ip:"
_KEY_PREFIX_MFA_VERIFY_ID = "auth:mfa:verify:id:"


class LoginRateLimitStoreError(Exception):
    """Raised when the rate-limit backend cannot apply the policy."""


class LoginAttemptStore(Protocol):
    def retry_after_seconds(self, ip_key: str, identity_key: str) -> int | None: ...

    def record_failure(self, ip_key: str, identity_key: str) -> None: ...

    def clear_identity(self, identity_key: str) -> None: ...


@dataclass
class _MemoryEntry:
    count: int
    expires_at: float


class InMemoryLoginAttemptStore:
    """Process-local counters for tests and non-production Redis fallback."""

    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, _MemoryEntry] = {}
        self._now = now or time.time

    def _prune_locked(self, key: str) -> _MemoryEntry | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._now():
            self._entries.pop(key, None)
            return None
        return entry

    def retry_after_seconds(self, ip_key: str, identity_key: str) -> int | None:
        now = self._now()
        retry: int | None = None
        with self._lock:
            for key in (ip_key, identity_key):
                entry = self._prune_locked(key)
                if entry is not None and entry.count >= MAX_FAILED_ATTEMPTS:
                    remaining = max(1, int(entry.expires_at - now))
                    retry = remaining if retry is None else max(retry, remaining)
        return retry

    def record_failure(self, ip_key: str, identity_key: str) -> None:
        now = self._now()
        with self._lock:
            for key in (ip_key, identity_key):
                entry = self._prune_locked(key)
                if entry is None:
                    self._entries[key] = _MemoryEntry(
                        count=1, expires_at=now + WINDOW_SECONDS
                    )
                else:
                    entry.count += 1

    def clear_identity(self, identity_key: str) -> None:
        with self._lock:
            self._entries.pop(identity_key, None)


class RedisLoginAttemptStore:
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

    def retry_after_seconds(self, ip_key: str, identity_key: str) -> int | None:
        try:
            client = self._redis()
            retry: int | None = None
            for key in (ip_key, identity_key):
                raw = client.get(key)
                if raw is None:
                    continue
                count = int(raw)
                if count < MAX_FAILED_ATTEMPTS:
                    continue
                ttl = int(client.ttl(key))
                remaining = ttl if ttl > 0 else WINDOW_SECONDS
                retry = remaining if retry is None else max(retry, remaining)
            return retry
        except LoginRateLimitStoreError:
            raise
        except Exception as exc:
            raise LoginRateLimitStoreError("redis retry-after failed") from exc

    def record_failure(self, ip_key: str, identity_key: str) -> None:
        try:
            client = self._redis()
            for key in (ip_key, identity_key):
                count = int(client.incr(key))
                if count == 1:
                    client.expire(key, WINDOW_SECONDS)
                else:
                    ttl = int(client.ttl(key))
                    if ttl < 0:
                        client.expire(key, WINDOW_SECONDS)
        except Exception as exc:
            raise LoginRateLimitStoreError("redis record-failure failed") from exc

    def clear_identity(self, identity_key: str) -> None:
        try:
            client = self._redis()
            client.delete(identity_key)
        except Exception as exc:
            raise LoginRateLimitStoreError("redis clear-identity failed") from exc


_store: LoginAttemptStore | None = None
_memory_fallback = InMemoryLoginAttemptStore()


def reset_login_rate_limiter_for_tests(store: LoginAttemptStore | None = None) -> None:
    """Replace the backend (tests). Default is a fresh in-memory store."""
    global _store, _memory_fallback
    _memory_fallback = InMemoryLoginAttemptStore()
    _store = store if store is not None else _memory_fallback


def get_login_attempt_store() -> LoginAttemptStore:
    global _store
    if _store is None:
        _store = RedisLoginAttemptStore()
    return _store


def normalize_login_identity(email: str) -> str:
    return email.strip().lower()


def _peer_host(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host.strip()[:64]
    return "unknown"


def _parse_ip(raw: str) -> IPv4Address | IPv6Address | None:
    value = raw.strip().strip("[]")
    if not value:
        return None
    if value.count(":") == 1 and "." in value:
        value = value.rsplit(":", 1)[0]
    try:
        addr: IPv4Address | IPv6Address = ipaddress.ip_address(value)
    except ValueError:
        return None
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        return mapped
    return addr


def parse_trusted_proxy_networks(entries: list[str]) -> list[IPv4Network | IPv6Network]:
    networks: list[IPv4Network | IPv6Network] = []
    for raw in entries:
        item = raw.strip()
        if not item:
            continue
        try:
            if "/" in item:
                networks.append(ipaddress.ip_network(item, strict=False))
            else:
                addr = ipaddress.ip_address(item)
                networks.append(ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}"))
        except ValueError:
            logger.warning("ignoring invalid API_TRUSTED_PROXY_IPS entry")
    return networks


def is_trusted_proxy_peer(peer: str, networks: list[IPv4Network | IPv6Network]) -> bool:
    addr = _parse_ip(peer)
    if addr is None:
        return False
    return any(addr in network for network in networks)


def _client_from_forwarded_for(
    header: str, networks: list[IPv4Network | IPv6Network]
) -> str | None:
    hops = [part.strip() for part in header.split(",") if part.strip()]
    if not hops:
        return None
    for hop in reversed(hops):
        addr = _parse_ip(hop)
        if addr is None:
            continue
        if any(addr in network for network in networks):
            continue
        return str(addr)[:64]
    fallback = _parse_ip(hops[0])
    return str(fallback)[:64] if fallback is not None else hops[0][:64]


def resolve_client_ip(request: Request) -> str:
    """Return the client IP for login rate limiting.

    Forwarded headers are ignored unless the TCP peer is in API_TRUSTED_PROXY_IPS.
    Direct clients therefore cannot spoof X-Forwarded-For or X-Real-IP.
    """
    peer = _peer_host(request)
    networks = parse_trusted_proxy_networks(get_settings().trusted_proxy_ips)
    if not networks or not is_trusted_proxy_peer(peer, networks):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        from_xff = _client_from_forwarded_for(forwarded, networks)
        if from_xff:
            return from_xff
    real_ip = _parse_ip(request.headers.get("x-real-ip") or "")
    if real_ip is not None:
        return str(real_ip)[:64]
    return peer


def hashed_limit_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"


def _hashed_key(prefix: str, value: str) -> str:
    return hashed_limit_key(prefix, value)


def ip_counter_key(ip: str) -> str:
    return _hashed_key(_KEY_PREFIX_IP, ip)


def identity_counter_key(identity: str) -> str:
    return _hashed_key(_KEY_PREFIX_ID, identity)


def _raise_lockout(retry_after: int, message: str = GENERIC_LOCKOUT_MESSAGE) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=message,
        headers={"Retry-After": str(retry_after)},
    )


def _raise_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=GENERIC_UNAVAILABLE_MESSAGE,
    )


def _with_store(op_name: str, callback):
    store = get_login_attempt_store()
    try:
        return callback(store)
    except LoginRateLimitStoreError:
        logger.exception("login_rate_limit_backend_failure op=%s", op_name)
        settings = get_settings()
        if settings.environment.lower() == "production":
            _raise_unavailable()
        logger.error(
            "login_rate_limit_using_memory_fallback op=%s environment=%s",
            op_name,
            settings.environment,
        )
        return callback(_memory_fallback)


def enforce_login_rate_limit(*, ip: str, identity: str) -> None:
    """Block the request if IP or identity is over the failed-attempt limit."""
    ip_key = ip_counter_key(ip)
    id_key = identity_counter_key(identity)

    def _check(store: LoginAttemptStore) -> int | None:
        return store.retry_after_seconds(ip_key, id_key)

    retry_after = _with_store("check", _check)
    if retry_after is not None:
        _raise_lockout(retry_after)


def record_failed_login_attempt(*, ip: str, identity: str) -> None:
    ip_key = ip_counter_key(ip)
    id_key = identity_counter_key(identity)

    def _record(store: LoginAttemptStore) -> None:
        store.record_failure(ip_key, id_key)

    _with_store("record", _record)
    from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

    observe_security_event(SecurityEventKind.FAILED_LOGIN, ip=ip, identity=identity)


def clear_failed_login_attempts_for_identity(identity: str) -> None:
    id_key = identity_counter_key(identity)

    def _clear(store: LoginAttemptStore) -> None:
        store.clear_identity(id_key)

    _with_store("clear", _clear)


def enforce_mfa_confirm_rate_limit(*, ip: str, user_id: str) -> None:
    ip_key = _hashed_key(_KEY_PREFIX_MFA_CONFIRM_IP, ip)
    user_key = _hashed_key(_KEY_PREFIX_MFA_CONFIRM_USER, user_id)

    def _check(store: LoginAttemptStore) -> int | None:
        return store.retry_after_seconds(ip_key, user_key)

    retry_after = _with_store("mfa_confirm_check", _check)
    if retry_after is not None:
        _raise_lockout(retry_after, GENERIC_MFA_CONFIRM_LOCKOUT)


def record_failed_mfa_confirm(*, ip: str, user_id: str) -> None:
    ip_key = _hashed_key(_KEY_PREFIX_MFA_CONFIRM_IP, ip)
    user_key = _hashed_key(_KEY_PREFIX_MFA_CONFIRM_USER, user_id)

    def _record(store: LoginAttemptStore) -> None:
        store.record_failure(ip_key, user_key)

    _with_store("mfa_confirm_record", _record)
    from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

    observe_security_event(SecurityEventKind.MFA_FAILURE, ip=ip, identity=user_id)


def clear_mfa_confirm_failures(*, user_id: str) -> None:
    user_key = _hashed_key(_KEY_PREFIX_MFA_CONFIRM_USER, user_id)

    def _clear(store: LoginAttemptStore) -> None:
        store.clear_identity(user_key)

    _with_store("mfa_confirm_clear", _clear)


def enforce_mfa_verify_rate_limit(*, ip: str, identity: str) -> None:
    ip_key = _hashed_key(_KEY_PREFIX_MFA_VERIFY_IP, ip)
    id_key = _hashed_key(_KEY_PREFIX_MFA_VERIFY_ID, identity)

    def _check(store: LoginAttemptStore) -> int | None:
        return store.retry_after_seconds(ip_key, id_key)

    retry_after = _with_store("mfa_verify_check", _check)
    if retry_after is not None:
        _raise_lockout(retry_after, GENERIC_MFA_CONFIRM_LOCKOUT)


def record_failed_mfa_verify(*, ip: str, identity: str) -> None:
    ip_key = _hashed_key(_KEY_PREFIX_MFA_VERIFY_IP, ip)
    id_key = _hashed_key(_KEY_PREFIX_MFA_VERIFY_ID, identity)

    def _record(store: LoginAttemptStore) -> None:
        store.record_failure(ip_key, id_key)

    _with_store("mfa_verify_record", _record)
    from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

    observe_security_event(SecurityEventKind.MFA_FAILURE, ip=ip, identity=identity)


def clear_mfa_verify_failures(*, identity: str) -> None:
    id_key = _hashed_key(_KEY_PREFIX_MFA_VERIFY_ID, identity)

    def _clear(store: LoginAttemptStore) -> None:
        store.clear_identity(id_key)

    _with_store("mfa_verify_clear", _clear)
