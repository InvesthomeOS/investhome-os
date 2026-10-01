"""TOTP MFA enrollment for authenticated users. Does not change login."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.user_auth import User
from investhome_api.models.user_mfa import UserMfa, UserMfaRecoveryCode
from investhome_api.services.mfa_crypto import hash_recovery_code, seal_totp_secret, unseal_totp_secret

logger = get_logger("investhome.auth.mfa")

PENDING_ENROLLMENT_TTL = timedelta(minutes=15)
RECOVERY_CODE_COUNT = 10
TOTP_VALID_WINDOW = 1
ALREADY_ENABLED_MESSAGE = "MFA is already enabled"
INVALID_CODE_MESSAGE = "Invalid or expired verification code"


def _issuer() -> str:
    return (get_settings().mfa_totp_issuer or "InvestHomeOS").strip() or "InvestHomeOS"


def _account_label(user: User) -> str:
    return user.email.strip().lower()


def _load_user_mfa(db: Session, user_id) -> UserMfa | None:
    return db.scalar(
        select(UserMfa)
        .options(selectinload(UserMfa.recovery_codes))
        .where(UserMfa.user_id == user_id)
    )


def _is_confirmed(row: UserMfa | None, user: User) -> bool:
    if user.mfa_enabled and user.mfa_method == "totp":
        return True
    if row is not None and row.enrollment_confirmed_at is not None:
        return True
    return False


def _is_pending_fresh(row: UserMfa | None) -> bool:
    if row is None or not row.totp_secret_ciphertext or row.enrollment_confirmed_at is not None:
        return False
    if row.enrollment_started_at is None:
        return False
    started = row.enrollment_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return datetime.now(UTC) - started <= PENDING_ENROLLMENT_TTL


def _generate_recovery_codes() -> list[str]:
    codes: list[str] = []
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def start_enrollment(db: Session, user: User) -> dict[str, str | bool]:
    existing = _load_user_mfa(db, user.id)
    if _is_confirmed(existing, user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_ENABLED_MESSAGE)

    secret = pyotp.random_base32(length=32)
    ciphertext = seal_totp_secret(secret)
    now = datetime.now(UTC)
    if existing is None:
        existing = UserMfa(user_id=user.id)
        db.add(existing)
    else:
        existing.recovery_codes.clear()
    existing.totp_secret_ciphertext = ciphertext
    existing.method = "totp"
    existing.enrollment_started_at = now
    existing.enrollment_confirmed_at = None
    db.flush()
    logger.info("mfa_enrollment_started user_id=%s", user.id)
    issuer = _issuer()
    account = _account_label(user)
    uri = pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)
    return {
        "otpauth_uri": uri,
        "issuer": issuer,
        "account_label": account,
        "pending": True,
    }


def confirm_enrollment(db: Session, user: User, code: str) -> dict:
    existing = _load_user_mfa(db, user.id)
    if _is_confirmed(existing, user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_ENABLED_MESSAGE)
    if not _is_pending_fresh(existing) or existing is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE_MESSAGE)

    secret = unseal_totp_secret(existing.totp_secret_ciphertext)
    if not secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE_MESSAGE)

    normalized = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(normalized) != 6 or not pyotp.TOTP(secret).verify(normalized, valid_window=TOTP_VALID_WINDOW):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE_MESSAGE)

    now = datetime.now(UTC)
    existing.enrollment_confirmed_at = now
    existing.method = "totp"
    user.mfa_enabled = True
    user.mfa_method = "totp"
    user.mfa_enforced_at = now
    user.updated_at = now
    existing.recovery_codes.clear()
    plaintext_codes = _generate_recovery_codes()
    for item in plaintext_codes:
        existing.recovery_codes.append(UserMfaRecoveryCode(code_hash=hash_recovery_code(item)))
    db.flush()
    logger.info("mfa_enrollment_confirmed user_id=%s", user.id)
    return {
        "mfa_enabled": True,
        "mfa_method": "totp",
        "recovery_codes": plaintext_codes,
    }


def totp_secret_from_otpauth(uri: str) -> str:
    query = parse_qs(urlparse(uri).query)
    values = query.get("secret") or []
    if not values:
        raise ValueError("otpauth_missing_secret")
    return values[0]
