"""Password reset, MFA re-enrollment, and user lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivityLog,
    ActivitySource,
)
from investhome_api.models.lead import Lead
from investhome_api.models.password_reset import PasswordResetToken
from investhome_api.models.user_auth import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)
from investhome_api.services.auth_service import hash_password
from investhome_api.services.login_rate_limit import reset_login_rate_limiter_for_tests
from investhome_api.services.mfa_enforcement import set_mfa_enforcement_disabled_for_tests
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"
SALES_EMAIL = "sales@example.com"
READONLY_EMAIL = "readonly@example.com"
NEW_PASSWORD = "correct-horse-battery-staple-9"
GENERIC = "If an account exists for this email, a password reset link has been sent."


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _capture(monkeypatch) -> dict[str, str]:
    captured: dict[str, str] = {}

    def _send(*, user, raw_token: str) -> str:
        del user
        captured["token"] = raw_token
        return "sent"

    monkeypatch.setattr("investhome_api.services.password_reset._send_reset_email", _send)
    return captured


def _user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def test_forgot_password_is_generic_for_known_and_unknown(
    auth_client: TestClient, monkeypatch
) -> None:
    captured = _capture(monkeypatch)
    known = auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL})
    unknown = auth_client.post(
        "/auth/password/forgot",
        json={"email": "missing.person@example.com"},
    )
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json()["message"] == GENERIC
    assert unknown.json()["message"] == known.json()["message"]
    assert captured["token"] not in known.text
    assert "token" not in known.json()


def test_forgot_password_rate_limit(auth_client: TestClient, monkeypatch) -> None:
    _capture(monkeypatch)
    last = None
    for _ in range(6):
        last = auth_client.post("/auth/password/forgot", json={"email": "limit.me@example.com"})
    assert last is not None
    assert last.status_code == 429


def test_valid_reset_updates_password_and_rejects_reuse(
    auth_client: TestClient, db: Session, monkeypatch
) -> None:
    captured = _capture(monkeypatch)
    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    token = captured["token"]
    updated = auth_client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert updated.status_code == 200, updated.text
    assert token not in updated.text
    reused = auth_client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": "another-correct-horse-battery-4"},
    )
    assert reused.status_code == 400
    assert reused.json()["details"][0]["code"] == "reset_used"
    assert _login(auth_client, SALES_EMAIL, DEMO_PASSWORD).status_code == 401
    assert _login(auth_client, SALES_EMAIL, NEW_PASSWORD).status_code == 200
    sales = _user(db, SALES_EMAIL)
    assert sales.mfa_enabled is False


def test_expired_malformed_and_replaced_tokens_are_rejected(
    auth_client: TestClient, db: Session, monkeypatch
) -> None:
    captured = _capture(monkeypatch)
    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    first = captured["token"]
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.consumed_at.is_(None)))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    expired = auth_client.post(
        "/auth/password/reset",
        json={"token": first, "new_password": NEW_PASSWORD},
    )
    assert expired.status_code == 400
    assert expired.json()["detail"] == "Reset link has expired"
    assert expired.json()["details"][0]["code"] == "reset_expired"
    reset_login_rate_limiter_for_tests()

    malformed = auth_client.post(
        "/auth/password/reset",
        json={"token": "not-a-token", "new_password": NEW_PASSWORD},
    )
    assert malformed.status_code == 400
    assert malformed.json()["details"][0]["code"] == "reset_malformed"
    reset_login_rate_limiter_for_tests()

    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    older = captured["token"]
    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    latest = captured["token"]
    stale = auth_client.post(
        "/auth/password/reset",
        json={"token": older, "new_password": NEW_PASSWORD},
    )
    assert stale.status_code == 400
    fresh = auth_client.post(
        "/auth/password/reset",
        json={"token": latest, "new_password": NEW_PASSWORD},
    )
    assert fresh.status_code == 200, fresh.text


def test_password_policy_is_enforced(auth_client: TestClient, monkeypatch) -> None:
    captured = _capture(monkeypatch)
    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    rejected = auth_client.post(
        "/auth/password/reset",
        json={"token": captured["token"], "new_password": "password1234"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Password does not meet requirements"
    assert rejected.json()["details"][0]["code"] == "password_common"
    assert "password1234" not in rejected.text
    reset_login_rate_limiter_for_tests()
    short = auth_client.post(
        "/auth/password/reset",
        json={"token": captured["token"], "new_password": "too-short"},
    )
    assert short.status_code == 400
    assert short.json()["detail"] == "Password does not meet requirements"
    assert short.json()["details"][0]["code"] == "password_too_short"


def test_reset_revokes_sessions_and_keeps_mfa(
    auth_client: TestClient, db: Session, monkeypatch, caplog
) -> None:
    assert _login(auth_client, SALES_EMAIL).status_code == 200
    start = auth_client.post("/auth/mfa/enroll")
    assert start.status_code == 200, start.text
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = auth_client.post(
        "/auth/mfa/enroll/confirm",
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert confirmed.status_code == 200, confirmed.text
    captured = _capture(monkeypatch)
    caplog.set_level(logging.INFO)
    assert auth_client.post("/auth/password/forgot", json={"email": SALES_EMAIL}).status_code == 200
    token = captured["token"]
    reset = auth_client.post(
        "/auth/password/reset",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert reset.status_code == 200, reset.text
    assert auth_client.get("/auth/me").status_code == 401
    logged = " ".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("investhome")
    )
    assert token not in logged
    sales = _user(db, SALES_EMAIL)
    db.refresh(sales)
    assert sales.mfa_enabled is True
    challenge = _login(auth_client, SALES_EMAIL, NEW_PASSWORD)
    assert challenge.status_code == 200
    assert challenge.json().get("mfa_required") is True


def test_admin_can_send_reset_and_readonly_cannot(
    auth_client: TestClient, db: Session, monkeypatch
) -> None:
    captured = _capture(monkeypatch)
    sales_id = _user(db, SALES_EMAIL).id
    assert _login(auth_client, READONLY_EMAIL).status_code == 200
    denied = auth_client.post(f"/users/{sales_id}/reset-password")
    assert denied.status_code == 403
    assert _login(auth_client).status_code == 200
    sent = auth_client.post(f"/users/{sales_id}/reset-password")
    assert sent.status_code == 200, sent.text
    assert "password" not in sent.json()
    assert captured["token"] not in sent.text
    assert _login(auth_client, SALES_EMAIL, DEMO_PASSWORD).status_code == 200


def test_admin_mfa_reset_requires_fresh_enrollment(auth_client: TestClient, db: Session) -> None:
    set_mfa_enforcement_disabled_for_tests(False)
    try:
        login = _login(auth_client)
        assert login.status_code == 200
        assert login.json().get("mfa_enrollment_required") is True
        token = login.json()["mfa_enrollment_challenge_token"]
        start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
        assert start.status_code == 200, start.text
        secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
        confirmed = auth_client.post(
            "/auth/mfa/enroll/required/confirm",
            json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
        )
        assert confirmed.status_code == 200, confirmed.text
        admin_id = _user(db, ADMIN_EMAIL).id
        reset = auth_client.post(f"/users/{admin_id}/mfa/reset")
        assert reset.status_code == 200, reset.text
        again = _login(auth_client)
        assert again.json().get("mfa_required") is not True
        assert again.json().get("mfa_enrollment_required") is True
        next_token = again.json()["mfa_enrollment_challenge_token"]
        restart = auth_client.post(
            "/auth/mfa/enroll/required",
            json={"challenge_token": next_token},
        )
        assert restart.status_code == 200, restart.text
        next_secret = totp_secret_from_otpauth(restart.json()["otpauth_uri"])
        assert next_secret != secret
        done = auth_client.post(
            "/auth/mfa/enroll/required/confirm",
            json={"challenge_token": next_token, "code": pyotp.TOTP(next_secret).now()},
        )
        assert done.status_code == 200, done.text
        assert done.json()["mfa_enabled"] is True
    finally:
        set_mfa_enforcement_disabled_for_tests(True)


def _manager_user(db: Session) -> User:
    perm = db.scalar(
        select(Permission).where(Permission.resource == "users", Permission.action == "manage")
    )
    assert perm is not None
    role = Role(name="lifecycle manager", code="lifecycle_manager", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = User(
        full_name="Lifecycle Manager",
        email="lifecycle.manager@example.com",
        hashed_password=hash_password(NEW_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _spare_user(db: Session, email: str) -> User:
    role = db.scalar(select(Role).where(Role.code == "read_only"))
    assert role is not None
    user = User(
        full_name="Spare User",
        email=email,
        hashed_password=hash_password(NEW_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    return user


def test_deactivate_archive_and_list_visibility(auth_client: TestClient, db: Session) -> None:
    user = _spare_user(db, "lifecycle.spare@example.com")
    assert _login(auth_client).status_code == 200
    deactivated = auth_client.post(f"/users/{user.id}/deactivate")
    assert deactivated.status_code == 200, deactivated.text
    blocked = _login(auth_client, user.email, NEW_PASSWORD)
    assert blocked.status_code == 403
    assert _login(auth_client).status_code == 200
    activated = auth_client.post(f"/users/{user.id}/activate")
    assert activated.status_code == 200
    assert _login(auth_client, user.email, NEW_PASSWORD).status_code == 200
    assert _login(auth_client).status_code == 200
    archived = auth_client.post(f"/users/{user.id}/archive")
    assert archived.status_code == 200, archived.text
    assert _login(auth_client, user.email, NEW_PASSWORD).status_code in {401, 403}
    hidden = auth_client.get("/users")
    assert hidden.status_code == 200
    assert all(item["email"] != user.email for item in hidden.json()["items"])
    shown = auth_client.get("/users?include_archived=true")
    match = next(item for item in shown.json()["items"] if item["email"] == user.email)
    assert match["archived_at"] is not None


def test_safe_delete_blocks_and_transfer(auth_client: TestClient, db: Session) -> None:
    source = _spare_user(db, "lifecycle.source@example.com")
    target = _spare_user(db, "lifecycle.target@example.com")
    lead = Lead(full_name="Owned Lead", assigned_manager_id=source.id)
    db.add(lead)
    audit = ActivityLog(
        event_type="test.historical",
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.USER,
        entity_id=source.id,
        actor_type=ActivityActorType.USER,
        actor_user_id=source.id,
        source=ActivitySource.API,
        description_key="activity.test.historical",
    )
    db.add(audit)
    db.commit()
    assert _login(auth_client).status_code == 200
    self_delete = auth_client.delete(f"/users/{_user(db, ADMIN_EMAIL).id}")
    assert self_delete.status_code == 409
    assert self_delete.json()["reason"] == "self"
    manager = _manager_user(db)
    assert _login(auth_client, manager.email, NEW_PASSWORD).status_code == 200
    last_admin = auth_client.delete(f"/users/{_user(db, ADMIN_EMAIL).id}")
    assert last_admin.status_code == 409
    assert last_admin.json()["reason"] == "last_super_admin"
    assert _login(auth_client).status_code == 200

    blocked = auth_client.delete(f"/users/{source.id}")
    assert blocked.status_code == 409
    assert blocked.json()["cannot_delete"] is True
    assert blocked.json()["dependencies"]["leads"] >= 1

    moved = auth_client.post(
        f"/users/{source.id}/transfer-ownership",
        json={"target_user_id": str(target.id)},
    )
    assert moved.status_code == 200, moved.text
    db.refresh(lead)
    db.refresh(audit)
    assert lead.assigned_manager_id == target.id
    assert audit.actor_user_id == source.id
    assert moved.json()["deletion"]["cannot_delete"] is False

    unused = _spare_user(db, "lifecycle.unused@example.com")
    unused_id = unused.id
    source_id = source.id
    deleted = auth_client.delete(f"/users/{unused_id}")
    assert deleted.status_code == 200, deleted.text
    db.expunge_all()
    assert db.get(User, unused_id) is None
    removed = auth_client.delete(f"/users/{source_id}")
    assert removed.status_code == 200, removed.text
