"""Idle and absolute session lifetime policy for browser JWTs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from investhome_api.config.settings import get_settings
from investhome_api.models.security_enterprise import AuthSession

AUTH_TIME_CLAIM = "auth_time"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def idle_timeout() -> timedelta:
    settings = get_settings()
    minutes = max(1, int(settings.jwt_expire_minutes))
    return timedelta(minutes=minutes)


def absolute_timeout() -> timedelta:
    settings = get_settings()
    minutes = max(1, int(settings.session_absolute_timeout_minutes))
    return timedelta(minutes=minutes)


def session_started_at(session: AuthSession) -> datetime:
    return _aware(session.created_at)


def compute_access_expiry(
    *,
    started_at: datetime,
    now: datetime | None = None,
) -> datetime | None:
    """Return JWT/cookie expiry, or None when the session is already past both windows."""
    current = _aware(now or datetime.now(UTC))
    started = _aware(started_at)
    idle_end = current + idle_timeout()
    absolute_end = started + absolute_timeout()
    expiry = min(idle_end, absolute_end)
    if expiry <= current:
        return None
    return expiry


def is_within_session_lifetime(session: AuthSession, *, now: datetime | None = None) -> bool:
    current = _aware(now or datetime.now(UTC))
    started = session_started_at(session)
    if current >= started + absolute_timeout():
        return False
    last_seen = session.last_seen_at or session.created_at
    if current >= _aware(last_seen) + idle_timeout():
        return False
    expires = _aware(session.expires_at)
    if current >= expires:
        return False
    return True


def auth_time_timestamp(started_at: datetime) -> int:
    return int(_aware(started_at).timestamp())
