"""Rate-limit public password reset requests by IP and normalized email."""

from __future__ import annotations

from investhome_api.services.login_rate_limit import (
    LoginAttemptStore,
    _raise_lockout,
    _with_store,
    hashed_limit_key,
    normalize_login_identity,
)

GENERIC_RESET_LOCKOUT = "Too many password reset attempts. Try again later."
_KEY_PREFIX_IP = "auth:password-reset:ip:"
_KEY_PREFIX_EMAIL = "auth:password-reset:email:"


def enforce_password_reset_rate_limit(*, ip: str, email: str) -> None:
    ip_key = hashed_limit_key(_KEY_PREFIX_IP, ip)
    email_key = hashed_limit_key(_KEY_PREFIX_EMAIL, normalize_login_identity(email))

    def _check(store: LoginAttemptStore) -> int | None:
        return store.retry_after_seconds(ip_key, email_key)

    retry_after = _with_store("password_reset_check", _check)
    if retry_after is not None:
        _raise_lockout(retry_after, GENERIC_RESET_LOCKOUT)


def record_password_reset_attempt(*, ip: str, email: str) -> None:
    ip_key = hashed_limit_key(_KEY_PREFIX_IP, ip)
    email_key = hashed_limit_key(_KEY_PREFIX_EMAIL, normalize_login_identity(email))

    def _record(store: LoginAttemptStore) -> None:
        store.record_failure(ip_key, email_key)

    _with_store("password_reset_record", _record)
