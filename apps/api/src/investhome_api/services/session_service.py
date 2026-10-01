"""Auth session lifecycle: create, validate, revoke."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.security_enterprise import AuthSession
from investhome_api.models.user_auth import User

# Avoid row-lock contention when many authenticated requests touch the same session.
_TOUCH_MIN_INTERVAL = timedelta(seconds=60)


def _parse_device_label(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    ua = user_agent[:500]
    browser = "Browser"
    if "Edg/" in ua:
        browser = "Edge"
    elif "Chrome/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser = "Safari"
    os_name = "Unknown OS"
    if "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Linux" in ua:
        os_name = "Linux"
    return f"{browser} on {os_name}"


def create_session(
    db: Session,
    *,
    user: User,
    expires_at: datetime,
    request: Request | None = None,
) -> AuthSession:
    jti = uuid.uuid4().hex
    ip = None
    ua = None
    if request is not None:
        forwarded = request.headers.get("x-forwarded-for")
        ip = (forwarded.split(",")[0].strip() if forwarded else None) or (
            request.client.host if request.client else None
        )
        ua = request.headers.get("user-agent")
    now = datetime.now(UTC)
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_jti=jti,
        ip_address=ip,
        user_agent=(ua[:512] if ua else None),
        device_label=_parse_device_label(ua),
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    return session


def get_active_session(db: Session, token_jti: str) -> AuthSession | None:
    from investhome_api.services.session_lifetime import is_within_session_lifetime

    session = db.scalar(select(AuthSession).where(AuthSession.token_jti == token_jti))
    if session is None or session.revoked_at is not None:
        return None
    if not is_within_session_lifetime(session):
        return None
    return session


def touch_session(db: Session, session: AuthSession) -> None:
    """Update last_seen_at without holding locks on the request transaction.

    P11 session tracking used to UPDATE auth_sessions inside the request-scoped
    session and flush. Concurrent async auth deps then blocked the event loop
    waiting on that row lock, which hung login and other API calls.
    """
    del db  # request session must not hold the touch write
    now = datetime.now(UTC)
    last = session.last_seen_at
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if now - last < _TOUCH_MIN_INTERVAL:
            return

    with SessionLocal() as touch_db:
        touch_db.execute(
            update(AuthSession)
            .where(AuthSession.id == session.id)
            .values(last_seen_at=now)
        )
        touch_db.commit()
    session.last_seen_at = now


def extend_session_expiry(session_id: uuid.UUID, expires_at: datetime) -> None:
    """Persist a sliding JWT expiry without using the request-scoped session."""
    from investhome_api.db.session import SessionLocal as current_session_local

    with current_session_local() as refresh_db:
        refresh_db.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(expires_at=expires_at)
        )
        refresh_db.commit()


def revoke_session(
    db: Session,
    session: AuthSession,
    *,
    reason: str = "terminated",
) -> None:
    session.revoked_at = datetime.now(UTC)
    session.revoke_reason = reason
    db.flush()


def revoke_user_sessions(
    db: Session,
    user_id: uuid.UUID,
    *,
    reason: str = "force_logout",
    except_jti: str | None = None,
) -> int:
    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    count = 0
    for session in sessions:
        if except_jti and session.token_jti == except_jti:
            continue
        revoke_session(db, session, reason=reason)
        count += 1
    return count


def list_sessions(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    include_revoked: bool = False,
    limit: int = 200,
) -> list[AuthSession]:
    query = select(AuthSession).order_by(AuthSession.last_seen_at.desc()).limit(limit)
    if user_id is not None:
        query = query.where(AuthSession.user_id == user_id)
    if not include_revoked:
        query = query.where(AuthSession.revoked_at.is_(None))
    return list(db.scalars(query).all())


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key_secret() -> tuple[str, str, str]:
    """Return (full_secret, prefix, hash)."""
    raw = f"ihk_{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}"
    prefix = raw[:12]
    return raw, prefix, hash_api_key(raw)


_UA_SAFE = re.compile(r"[\x00-\x1f]")
