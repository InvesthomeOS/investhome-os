"""MFA login verification: TOTP or one-time recovery codes. No enrollment changes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pyotp
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.user_auth import User
from investhome_api.models.user_mfa import UserMfa, UserMfaRecoveryCode
from investhome_api.services.mfa_crypto import recovery_code_matches, unseal_totp_secret

TOTP_VALID_WINDOW = 1
INVALID_MFA_MESSAGE = "Invalid or expired verification code"


def user_requires_mfa_challenge(user: User) -> bool:
    return bool(user.mfa_enabled)


def _load_user_mfa(db: Session, user_id: UUID) -> UserMfa | None:
    return db.scalar(
        select(UserMfa)
        .options(selectinload(UserMfa.recovery_codes))
        .where(UserMfa.user_id == user_id)
    )


def _normalize_totp(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isdigit())


def _normalize_recovery(code: str) -> str:
    return "".join(ch for ch in (code or "").strip().upper() if ch.isalnum() or ch == "-")


def _totp_matches(secret: str | None, code: str) -> bool:
    normalized = _normalize_totp(code)
    if not secret or len(normalized) != 6:
        return False
    return bool(pyotp.TOTP(secret).verify(normalized, valid_window=TOTP_VALID_WINDOW))


def find_unused_recovery_code(row: UserMfa | None, code: str) -> UserMfaRecoveryCode | None:
    if row is None:
        return None
    normalized = _normalize_recovery(code)
    compact = normalized.replace("-", "")
    candidates: list[str] = []
    if normalized:
        candidates.append(normalized)
    if len(compact) == 10:
        hyphenated = f"{compact[:5]}-{compact[5:]}"
        if hyphenated not in candidates:
            candidates.append(hyphenated)
    if not candidates:
        return None
    for item in row.recovery_codes:
        if item.used_at is not None:
            continue
        if any(recovery_code_matches(candidate, item.code_hash) for candidate in candidates):
            return item
    return None


def verify_login_mfa_code(db: Session, user: User, code: str) -> UserMfaRecoveryCode | bool:
    """Return True for TOTP, a recovery-code row to mark used, or False if invalid."""
    row = _load_user_mfa(db, user.id)
    secret = unseal_totp_secret(row.totp_secret_ciphertext) if row else None
    if _totp_matches(secret, code):
        return True
    matched = find_unused_recovery_code(row, code)
    if matched is not None:
        return matched
    return False


def mark_recovery_code_used(code_row: UserMfaRecoveryCode) -> None:
    code_row.used_at = datetime.now(UTC)
