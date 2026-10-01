"""Admin MFA reset — security:manage only. No self-service bypass."""

from __future__ import annotations

import logging

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.security_enterprise import AuthSession
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.models.user_mfa import UserMfa, UserMfaRecoveryCode
from investhome_api.services.auth_service import hash_password
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"
SALES_EMAIL = "sales@example.com"
REQUEST_ID = "mfa-reset-test-request-1"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _enable_mfa(client: TestClient, email: str) -> tuple[str, list[str]]:
    assert _login(client, email).status_code == 200
    start = client.post("/auth/mfa/enroll")
    assert start.status_code == 200, start.text
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = client.post("/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret).now()})
    assert confirmed.status_code == 200, confirmed.text
    codes = confirmed.json()["recovery_codes"]
    return secret, codes


def _user_id(db: Session, email: str):
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


def _create_users_manage_only(db: Session, email: str) -> None:
    perm = db.scalar(
        select(Permission).where(Permission.resource == "users", Permission.action == "manage")
    )
    if perm is None:
        perm = Permission(resource="users", action="manage")
        db.add(perm)
        db.flush()
    view = db.scalar(
        select(Permission).where(Permission.resource == "users", Permission.action == "view")
    )
    role = Role(name="user_manager", code="user_manager", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    if view is not None:
        db.add(RolePermission(role_id=role.id, permission_id=view.id))
    user = User(
        full_name="User Manager",
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()


def test_unauthenticated_reset_rejected(auth_client: TestClient, db: Session) -> None:
    target = _user_id(db, SALES_EMAIL)
    response = auth_client.post(f"/users/{target}/mfa/reset")
    assert response.status_code == 401


def test_unauthorized_user_cannot_reset_another_user(auth_client: TestClient, db: Session) -> None:
    target = _user_id(db, ADMIN_EMAIL)
    assert _login(auth_client, SALES_EMAIL).status_code == 200
    denied = auth_client.post(f"/users/{target}/mfa/reset")
    assert denied.status_code == 403


def test_users_manage_is_not_enough_to_reset_mfa(auth_client: TestClient, db: Session) -> None:
    _create_users_manage_only(db, "useradmin@example.com")
    target = _user_id(db, SALES_EMAIL)
    assert _login(auth_client, "useradmin@example.com").status_code == 200
    denied = auth_client.post(f"/users/{target}/mfa/reset")
    assert denied.status_code == 403


def test_admin_reset_clears_mfa_revokes_sessions_and_audits(
    auth_client: TestClient, db: Session, caplog
) -> None:
    caplog.set_level(logging.INFO)
    secret, recovery_codes = _enable_mfa(auth_client, SALES_EMAIL)
    sales_id = _user_id(db, SALES_EMAIL)
    db.expire_all()
    before_sessions = list(
        db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == sales_id,
                AuthSession.revoked_at.is_(None),
            )
        )
    )
    assert before_sessions

    assert _login(auth_client, ADMIN_EMAIL).status_code == 200
    reset = auth_client.post(
        f"/users/{sales_id}/mfa/reset",
        headers={"X-Request-Id": REQUEST_ID},
    )
    assert reset.status_code == 200, reset.text
    body = reset.json()
    assert body["sessions_revoked"] >= 1
    assert secret not in str(body)
    assert all(code not in str(body) for code in recovery_codes)

    db.expire_all()
    target = db.get(User, sales_id)
    assert target is not None
    assert target.mfa_enabled is False
    assert target.mfa_method is None
    assert target.mfa_enforced_at is None
    assert db.scalar(select(UserMfa).where(UserMfa.user_id == sales_id)) is None
    leftover_codes = list(db.scalars(select(UserMfaRecoveryCode)))
    assert leftover_codes == []

    active = list(
        db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == sales_id,
                AuthSession.revoked_at.is_(None),
            )
        )
    )
    assert active == []
    revoked = list(
        db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == sales_id,
                AuthSession.revoked_at.isnot(None),
            )
        )
    )
    assert revoked
    assert all(row.revoke_reason == "mfa_reset" for row in revoked)

    audit = db.scalar(
        select(ActivityLog)
        .where(ActivityLog.description_key == "activity.security.mfa_reset")
        .order_by(ActivityLog.created_at.desc())
    )
    assert audit is not None
    admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert admin is not None
    assert audit.actor_user_id == admin.id
    assert audit.entity_id == sales_id
    assert audit.created_at is not None
    assert audit.request_id == REQUEST_ID
    meta = audit.metadata_json or {}
    assert meta.get("action") == "mfa_reset"
    assert meta.get("actor_user_id") == str(admin.id)
    assert meta.get("target_user_id") == str(sales_id)
    blob = str(meta).lower() + caplog.text.lower()
    assert secret.lower() not in blob
    for code in recovery_codes:
        assert code.lower() not in blob
    assert "otpauth://" not in caplog.text


def test_reset_user_cannot_use_old_totp_or_recovery(auth_client: TestClient, db: Session) -> None:
    secret, recovery_codes = _enable_mfa(auth_client, SALES_EMAIL)
    assert auth_client.post("/auth/logout").status_code == 200
    challenge = _login(auth_client, SALES_EMAIL)
    assert challenge.status_code == 200
    assert challenge.json().get("mfa_required") is True
    token = challenge.json()["mfa_challenge_token"]

    sales_id = _user_id(db, SALES_EMAIL)
    assert _login(auth_client, ADMIN_EMAIL).status_code == 200
    assert auth_client.post(f"/users/{sales_id}/mfa/reset").status_code == 200

    stale_totp = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert stale_totp.status_code == 401

    assert auth_client.post("/auth/logout").status_code == 200
    login = _login(auth_client, SALES_EMAIL)
    assert login.status_code == 200
    assert login.json().get("mfa_required") is not True
    assert login.json()["email"] == SALES_EMAIL
    assert login.json()["mfa_enabled"] is False
    assert auth_client.get("/auth/me").status_code == 200

    reused_recovery = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": recovery_codes[0]},
    )
    assert reused_recovery.status_code == 401
    assert auth_client.get("/auth/me").status_code == 200
