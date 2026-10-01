"""Admin MFA reset. Does not change enrollment or login challenge behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.core.logging_config import get_logger
from investhome_api.models.user_auth import User
from investhome_api.models.user_mfa import UserMfa
from investhome_api.services import session_service
from investhome_api.services.mfa_challenge import invalidate_mfa_challenges_for_user

logger = get_logger("investhome.auth.mfa")


def _load_user_mfa(db: Session, user_id: UUID) -> UserMfa | None:
    return db.scalar(
        select(UserMfa)
        .options(selectinload(UserMfa.recovery_codes))
        .where(UserMfa.user_id == user_id)
    )


def reset_user_mfa(db: Session, user: User) -> int:
    """Clear MFA state and revoke every active session for `user`.

    Never logs secrets, recovery codes, passwords, or session tokens.
    """
    row = _load_user_mfa(db, user.id)
    if row is not None:
        row.recovery_codes.clear()
        row.totp_secret_ciphertext = None
        row.method = None
        row.enrollment_started_at = None
        row.enrollment_confirmed_at = None
        db.delete(row)

    user.mfa_enabled = False
    user.mfa_method = None
    user.mfa_enforced_at = None
    user.updated_at = datetime.now(UTC)

    revoked = session_service.revoke_user_sessions(db, user.id, reason="mfa_reset")
    invalidate_mfa_challenges_for_user(str(user.id))
    db.flush()
    logger.info("mfa_admin_reset user_id=%s sessions_revoked=%s", user.id, revoked)
    return revoked
