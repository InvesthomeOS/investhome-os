"""Rate-limit public invitation preview and accept endpoints by client IP."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

from investhome_api.services.login_rate_limit import (
    LoginAttemptStore,
    hashed_limit_key,
    _raise_lockout,
    _with_store,
)

GENERIC_INVITE_LOCKOUT = "Too many invitation attempts. Try again later."
_KEY_PREFIX_INVITE_IP = "auth:invite:ip:"
_KEY_PREFIX_INVITE_TOKEN = "auth:invite:tok:"


def enforce_invite_rate_limit(*, ip: str, token: str) -> None:
    ip_key = hashed_limit_key(_KEY_PREFIX_INVITE_IP, ip)
    token_key = hashed_limit_key(_KEY_PREFIX_INVITE_TOKEN, token)

    def _check(store: LoginAttemptStore) -> int | None:
        return store.retry_after_seconds(ip_key, token_key)

    retry_after = _with_store("invite_check", _check)
    if retry_after is not None:
        _raise_lockout(retry_after, GENERIC_INVITE_LOCKOUT)


def record_invite_attempt(*, ip: str, token: str) -> None:
    ip_key = hashed_limit_key(_KEY_PREFIX_INVITE_IP, ip)
    token_key = hashed_limit_key(_KEY_PREFIX_INVITE_TOKEN, token)

    def _record(store: LoginAttemptStore) -> None:
        store.record_failure(ip_key, token_key)

    _with_store("invite_record", _record)


def reject_invite_attempt(*, ip: str, token: str) -> NoReturn:
    record_invite_attempt(ip=ip, token=token)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invitation is invalid or expired",
    )
