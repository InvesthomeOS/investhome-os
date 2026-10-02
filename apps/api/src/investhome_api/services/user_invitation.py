"""Issue, lookup, and consume user invitation tokens. Raw tokens are never stored."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.models.user_invitation import UserInvitation
from investhome_api.services.auth_service import hash_password
from investhome_api.services.invitation_email import build_invite_email
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    GatewayResult,
    NotificationChannel,
    get_notification_gateway,
)
from investhome_api.services.password_policy import PasswordPolicyError, validate_new_password

logger = get_logger("investhome.auth.invite")

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
GENERIC_INVITE_ERROR = "Invitation is invalid or expired"
DELIVERY_NOT_CONNECTED = "not_connected"
DELIVERY_NOT_SENT = "not_sent"
DELIVERY_FAILED = "failed"
DELIVERY_SENT = "sent"


class InvitationError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def unguessable_password_hash() -> str:
    """Satisfy hashed_password NOT NULL without a credential anyone can use."""
    return hash_password(secrets.token_urlsafe(48))


def invitation_ttl() -> timedelta:
    hours = max(1, int(get_settings().user_invite_ttl_hours))
    return timedelta(hours=hours)


def _frontend_base_url() -> str:
    settings = get_settings()
    public = (settings.app_public_url or "").strip().rstrip("/")
    if public:
        return public
    origins = settings.cors_origins or ["http://localhost:3000"]
    return str(origins[0]).rstrip("/")


def invite_url_for_token(token: str) -> str:
    return f"{_frontend_base_url()}/invite/{token}"


def normalize_invite_token(token: str) -> str | None:
    value = (token or "").strip()
    if not TOKEN_PATTERN.fullmatch(value):
        return None
    return value


def active_invitation_for_user(db: Session, user_id: UUID) -> UserInvitation | None:
    now = datetime.now(UTC)
    return db.scalar(
        select(UserInvitation)
        .where(
            UserInvitation.user_id == user_id,
            UserInvitation.consumed_at.is_(None),
            UserInvitation.expires_at > now,
        )
        .order_by(UserInvitation.created_at.desc())
    )


def invalidate_outstanding_invitations(db: Session, user_id: UUID) -> int:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(UserInvitation).where(
            UserInvitation.user_id == user_id,
            UserInvitation.consumed_at.is_(None),
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


def lookup_invitation_by_token(db: Session, token: str) -> UserInvitation | None:
    normalized = normalize_invite_token(token)
    if normalized is None:
        return None
    token_hash = hash_invite_token(normalized)
    invitation = db.scalar(
        select(UserInvitation).where(UserInvitation.token_hash == token_hash)
    )
    if invitation is None:
        return None
    return invitation


def invitation_is_redeemable(invitation: UserInvitation) -> bool:
    if invitation.consumed_at is not None:
        return False
    expires = invitation.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires > datetime.now(UTC)


def _delivery_status_from_result(result: GatewayResult) -> str:
    if result.ok and result.status == DELIVERY_SENT:
        return DELIVERY_SENT
    if result.status in {DELIVERY_NOT_CONNECTED, "not_connected"}:
        return DELIVERY_NOT_CONNECTED
    if result.status in {DELIVERY_FAILED, "failed"}:
        return DELIVERY_FAILED
    return DELIVERY_NOT_SENT


def dispatch_invite_email(
    *,
    recipient_email: str,
    recipient_name: str,
    token: str,
    locale: str,
) -> str:
    """Send via the notification gateway. Never logs the raw invite URL or token."""
    settings = get_settings()
    invite_url = invite_url_for_token(token)
    content = build_invite_email(
        full_name=recipient_name,
        invite_url=invite_url,
        ttl_hours=int(settings.user_invite_ttl_hours),
        locale=locale or "tr",
        from_name=settings.smtp_from_name,
    )
    gateway = get_notification_gateway()
    message = GatewayMessage(
        channel=NotificationChannel.EMAIL,
        recipient=recipient_email,
        subject=content.subject,
        body=content.text_body,
        html_body=content.html_body,
        locale=locale or "tr",
        metadata={"purpose": "user_invite"},
    )
    result = gateway.dispatch(message, provider_id="email_smtp")
    status = _delivery_status_from_result(result)
    logger.info(
        "invite_email_dispatch status=%s provider=%s",
        status,
        result.provider_id,
    )
    return status


@dataclass
class IssuedInvitation:
    invitation: UserInvitation
    delivery_status: str


def issue_invitation(
    db: Session,
    *,
    user: User,
    invited_by_user_id: UUID | None,
    invalidate_existing: bool = True,
) -> IssuedInvitation:
    if user.status != UserStatus.INVITED:
        raise InvitationError("User is not awaiting invitation")
    if invalidate_existing:
        invalidate_outstanding_invitations(db, user.id)

    token = generate_invite_token()
    now = datetime.now(UTC)
    invitation = UserInvitation(
        user_id=user.id,
        token_hash=hash_invite_token(token),
        expires_at=now + invitation_ttl(),
        invited_by_user_id=invited_by_user_id,
    )
    db.add(invitation)
    db.flush()
    delivery_status = dispatch_invite_email(
        recipient_email=user.email,
        recipient_name=user.full_name,
        token=token,
        locale=user.preferred_language,
    )
    return IssuedInvitation(
        invitation=invitation,
        delivery_status=delivery_status,
    )


def accept_invitation(
    db: Session,
    *,
    token: str,
    password: str,
) -> User:
    invitation = lookup_invitation_by_token(db, token)
    if invitation is None or not invitation_is_redeemable(invitation):
        raise InvitationError(GENERIC_INVITE_ERROR)

    user = db.get(User, invitation.user_id)
    if user is None or user.archived_at is not None or user.status != UserStatus.INVITED:
        raise InvitationError(GENERIC_INVITE_ERROR)

    try:
        validate_new_password(
            password,
            email=user.email,
            full_name=user.full_name,
            user_id=user.id,
        )
    except PasswordPolicyError as exc:
        raise InvitationError("password_policy") from exc

    now = datetime.now(UTC)
    invitation.consumed_at = now
    invitation.updated_at = now
    invalidate_outstanding_invitations(db, user.id)
    user.hashed_password = hash_password(password)
    user.status = UserStatus.ACTIVE
    user.updated_at = now
    db.flush()
    return user
