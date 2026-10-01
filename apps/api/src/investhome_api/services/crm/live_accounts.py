"""Investhome OS user communication accounts — never expose credentials."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import (
    CrmUserCommunicationAccount,
    CrmUserCommunicationAccountHealth,
    CrmUserCommunicationAccountStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.identity import normalize_email, parse_phone
from investhome_api.services.crm_communication_activity import record_communication_audit
from investhome_api.services.crypto_seal import redact_secret_fields, rewrap_secret, seal_secret, unseal_secret
from investhome_api.services.permission_service import user_has_permission

logger = logging.getLogger(__name__)

ALLOWED_CHANNELS = {"email", "whatsapp"}
ALLOWED_PROVIDERS = {
    "email": {"gmail", "m365", "smtp", "imap", "graph"},
    "whatsapp": {"whatsapp_business", "meta", "wazzup", "twilio"},
}


def can_manage_all_accounts(user: User) -> bool:
    return user_has_permission(user, "crm", "manage_provider_connections") or user_has_permission(
        user, "crm", "manage_settings"
    )


def _normalize_identity(channel: str, identity: str) -> str:
    if channel == "email":
        normalized = normalize_email(identity)
        if not normalized:
            raise ValueError("invalid_email_identity")
        return normalized
    parsed = parse_phone(identity)
    if parsed and parsed.e164:
        return parsed.e164
    if parsed and parsed.match_key:
        return parsed.match_key
    raise ValueError("invalid_phone_identity")


def serialize_account(account: CrmUserCommunicationAccount, *, owner_name: str | None = None) -> dict:
    return {
        "id": str(account.id),
        "user_id": str(account.user_id),
        "user_name": owner_name,
        "channel_type": account.channel_type,
        "provider": account.provider,
        "identity": account.identity,
        "account_label": account.account_label,
        "status": account.status,
        "health": account.health,
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "last_error": account.last_error,
        "has_credentials": bool(account.encrypted_credentials),
        "scopes": account.scopes,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None,
    }


def list_accounts(db: Session, user: User, *, user_id: UUID | None = None) -> list[CrmUserCommunicationAccount]:
    query = select(CrmUserCommunicationAccount).where(CrmUserCommunicationAccount.archived_at.is_(None))
    if not can_manage_all_accounts(user):
        query = query.where(CrmUserCommunicationAccount.user_id == user.id)
    elif user_id:
        query = query.where(CrmUserCommunicationAccount.user_id == user_id)
    return list(db.scalars(query.order_by(CrmUserCommunicationAccount.created_at.desc())).all())


def register_account(
    db: Session,
    *,
    actor: User,
    user_id: UUID,
    channel_type: str,
    provider: str,
    identity: str,
    account_label: str | None = None,
    credentials: dict | None = None,
) -> CrmUserCommunicationAccount:
    channel = channel_type.strip().lower()
    if channel not in ALLOWED_CHANNELS:
        raise ValueError("unsupported_channel")
    provider_key = provider.strip().lower()
    if provider_key not in ALLOWED_PROVIDERS[channel]:
        raise ValueError("unsupported_provider")
    if not can_manage_all_accounts(actor) and user_id != actor.id:
        raise ValueError("forbidden")
    normalized = _normalize_identity(channel, identity)
    existing = db.scalar(
        select(CrmUserCommunicationAccount).where(
            CrmUserCommunicationAccount.channel_type == channel,
            CrmUserCommunicationAccount.identity == normalized,
            CrmUserCommunicationAccount.archived_at.is_(None),
        )
    )
    if existing:
        raise ValueError("identity_taken")
    sealed = seal_secret(credentials) if credentials else None
    account = CrmUserCommunicationAccount(
        user_id=user_id,
        channel_type=channel,
        provider=provider_key,
        identity=normalized,
        account_label=account_label or normalized,
        status=CrmUserCommunicationAccountStatus.NOT_CONNECTED.value,
        health=CrmUserCommunicationAccountHealth.UNKNOWN.value,
        encrypted_credentials=sealed,
        created_by=actor.id,
    )
    db.add(account)
    db.flush()
    record_communication_audit(
        db,
        event_type="account.registered",
        actor=actor,
        details={"account_id": str(account.id), "channel_type": channel, "provider": provider_key},
    )
    logger.info("live_comm_account_registered id=%s channel=%s user=%s", account.id, channel, user_id)
    return account


def load_account_credentials(account: CrmUserCommunicationAccount) -> dict | None:
    """Server-side only. Never serialize the result to an API response."""
    payload = unseal_secret(account.encrypted_credentials)
    if payload is None:
        return None
    upgraded = rewrap_secret(account.encrypted_credentials)
    if upgraded and upgraded != account.encrypted_credentials:
        account.encrypted_credentials = upgraded
    return payload


def upgrade_legacy_credentials(db: Session) -> int:
    """Re-wrap HMAC-XOR blobs to AES-GCM. Leaves unreadable rows untouched."""
    rows = list(
        db.scalars(
            select(CrmUserCommunicationAccount).where(
                CrmUserCommunicationAccount.encrypted_credentials.is_not(None)
            )
        ).all()
    )
    upgraded = 0
    for account in rows:
        blob = account.encrypted_credentials
        wrapped = rewrap_secret(blob)
        if wrapped is None or wrapped == blob:
            continue
        account.encrypted_credentials = wrapped
        upgraded += 1
    if upgraded:
        logger.info("live_comm_credentials_rewrapped count=%s", upgraded)
    return upgraded


def disconnect_account(db: Session, account_id: UUID, *, actor: User) -> CrmUserCommunicationAccount:
    account = db.get(CrmUserCommunicationAccount, account_id)
    if account is None or account.archived_at is not None:
        raise ValueError("not_found")
    if not can_manage_all_accounts(actor) and account.user_id != actor.id:
        raise ValueError("forbidden")
    account.status = CrmUserCommunicationAccountStatus.DISCONNECTED.value
    account.health = CrmUserCommunicationAccountHealth.UNKNOWN.value
    account.encrypted_credentials = None
    account.archived_at = datetime.now(UTC)
    record_communication_audit(
        db,
        event_type="account.disconnected",
        actor=actor,
        details={"account_id": str(account.id)},
    )
    return account
