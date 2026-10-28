"""Single-use password reset tokens. Raw tokens are never stored or logged."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.password_reset import PasswordResetToken
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services import session_service
from investhome_api.services.auth_service import hash_password
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    NotificationChannel,
    get_notification_gateway,
)
from investhome_api.services.password_policy import PasswordPolicyError, validate_new_password

logger = get_logger("investhome.auth.password_reset")

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
RESET_TTL = timedelta(minutes=30)
GENERIC_RESET_ERROR = "Reset link is invalid or expired"
DELIVERY_SENT = "sent"
DELIVERY_FAILED = "failed"
DELIVERY_NOT_CONNECTED = "not_connected"


class PasswordResetError(ValueError):
    def __init__(self, message: str, *, reason_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code


@dataclass(frozen=True)
class IssuedPasswordReset:
    delivery_status: str


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_reset_token(token: str) -> str | None:
    value = (token or "").strip()
    if not TOKEN_PATTERN.fullmatch(value):
        return None
    return value


def frontend_base_url() -> str:
    settings = get_settings()
    public = (settings.app_public_url or "").strip().rstrip("/")
    if public:
        return public
    origins = settings.cors_origins or ["http://localhost:3000"]
    return str(origins[0]).rstrip("/")


def reset_url_for_token(token: str) -> str:
    return f"{frontend_base_url()}/reset-password?token={token}"


def invalidate_outstanding_resets(db: Session, user_id: UUID) -> int:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.consumed_at.is_(None),
        )
    ).all()
    count = 0
    for row in rows:
        row.consumed_at = now
        row.updated_at = now
        count += 1
    if count:
        db.flush()
    return count


def user_can_receive_reset(user: User | None) -> bool:
    if user is None or user.archived_at is not None:
        return False
    return user.status in {UserStatus.ACTIVE, UserStatus.INACTIVE}


def issue_password_reset(
    db: Session,
    user: User,
    *,
    requested_by_user_id: UUID | None,
) -> IssuedPasswordReset:
    """Create a token and email the link. The raw token is not returned."""
    invalidate_outstanding_resets(db, user.id)
    raw = generate_reset_token()
    now = datetime.now(UTC)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw),
            expires_at=now + RESET_TTL,
            requested_by_user_id=requested_by_user_id,
        )
    )
    db.flush()
    status = _send_reset_email(user=user, raw_token=raw)
    logger.info(
        "password_reset_issued user_id=%s delivery=%s",
        user.id,
        status,
    )
    return IssuedPasswordReset(delivery_status=status)


def _send_reset_email(*, user: User, raw_token: str) -> str:
    url = reset_url_for_token(raw_token)
    text = (
        "Investhome OS\n\n"
        "Şifrenizi sıfırlamak için aşağıdaki bağlantıyı kullanın.\n"
        "Bağlantı 30 dakika içinde geçerliliğini yitirir.\n\n"
        f"{url}\n\n"
        "Bu isteği siz yapmadıysanız bu e-postayı yok sayın.\n"
    )
    href = escape(url, quote=True)
    html = (
        "<!DOCTYPE html><html lang=\"tr\">"
        "<body style=\"font-family:Arial,sans-serif;color:#1A1A1A;\">"
        "<p style=\"font-weight:bold;\">Investhome OS</p>"
        "<p>Şifrenizi sıfırlamak için aşağıdaki düğmeyi kullanın. "
        "Bağlantı 30 dakika içinde geçerliliğini yitirir.</p>"
        f"<p><a href=\"{href}\" style=\"background:#C4A15A;color:#ffffff;padding:12px 18px;"
        "text-decoration:none;border-radius:4px;display:inline-block;\">Şifremi sıfırla</a></p>"
        "<p>Bu isteği siz yapmadıysanız bu e-postayı yok sayın.</p>"
        "</body></html>"
    )
    message = GatewayMessage(
        channel=NotificationChannel.EMAIL,
        recipient=user.email,
        subject="Investhome OS şifre sıfırlama",
        body=text,
        html_body=html,
        locale="tr",
        metadata={"purpose": "password_reset"},
    )
    try:
        result = get_notification_gateway().dispatch(message, provider_id="email_smtp")
    except Exception:
        logger.warning("password_reset_email_failed user_id=%s", user.id)
        return DELIVERY_FAILED
    if not result.ok:
        logger.warning(
            "password_reset_email_failed user_id=%s status=%s",
            user.id,
            result.status,
        )
        if result.status == "not_connected":
            return DELIVERY_NOT_CONNECTED
        return DELIVERY_FAILED
    return DELIVERY_SENT


def lookup_reset_token(db: Session, token: str) -> PasswordResetToken | None:
    normalized = normalize_reset_token(token)
    if normalized is None:
        return None
    return db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(normalized)
        )
    )


def reset_token_is_usable(row: PasswordResetToken, *, now: datetime | None = None) -> bool:
    moment = now or datetime.now(UTC)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return row.consumed_at is None and expires > moment


def consume_password_reset(db: Session, *, token: str, new_password: str) -> User:
    if normalize_reset_token(token) is None:
        raise PasswordResetError("malformed", reason_code="reset_malformed")
    row = lookup_reset_token(db, token)
    if row is None:
        raise PasswordResetError("invalid", reason_code="reset_invalid")
    if row.consumed_at is not None:
        raise PasswordResetError("used", reason_code="reset_used")
    if not reset_token_is_usable(row):
        raise PasswordResetError("expired", reason_code="reset_expired")
    user = db.get(User, row.user_id)
    if not user_can_receive_reset(user):
        raise PasswordResetError("invalid", reason_code="reset_invalid")
    assert user is not None
    try:
        validate_new_password(
            new_password,
            email=user.email,
            full_name=user.full_name,
            user_id=user.id,
        )
    except PasswordPolicyError as exc:
        raise PasswordResetError("password_policy", reason_code=exc.code) from exc
    now = datetime.now(UTC)
    user.hashed_password = hash_password(new_password)
    user.updated_at = now
    row.consumed_at = now
    row.updated_at = now
    invalidate_outstanding_resets(db, user.id)
    session_service.revoke_user_sessions(db, user.id, reason="password_reset")
    db.flush()
    logger.info("password_reset_consumed user_id=%s", user.id)
    return user
