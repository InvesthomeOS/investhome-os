"""User invitation foundation: invite, accept, login gate, activate/deactivate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.security_enterprise import AuthSession
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.models.user_invitation import UserInvitation
from investhome_api.services.auth_service import hash_password
from investhome_api.services.user_invitation import hash_invite_token

DEMO_PASSWORD = "Demo123!"
STRONG_PASSWORD = "correct-horse-battery-staple-9"
ADMIN_EMAIL = "admin@example.com"


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _created_user(response) -> dict:
    body = response.json()
    assert "token" not in body
    assert "hashed_password" not in body
    user = body["user"]
    assert "token" not in user
    assert "hashed_password" not in user
    return user


def _read_only_role_id(client: TestClient) -> str:
    assert _login(client).status_code == 200
    roles = client.get("/roles").json()["items"]
    return next(item["id"] for item in roles if item["code"] == "read_only")


def _role_id(client: TestClient, code: str) -> str:
    assert _login(client).status_code == 200
    roles = client.get("/roles").json()["items"]
    return next(item["id"] for item in roles if item["code"] == code)


def _set_invite_token(monkeypatch, token: str) -> str:
    monkeypatch.setattr(
        "investhome_api.services.user_invitation.generate_invite_token",
        lambda: token,
    )
    return token


def _invite_user(
    client: TestClient,
    monkeypatch,
    *,
    email: str,
    role_ids: list[str],
    token: str,
    full_name: str = "Invited Person",
    department: str = "Sales",
) -> tuple[dict, str]:
    _set_invite_token(monkeypatch, token)
    assert _login(client).status_code == 200
    created = client.post(
        "/users",
        json={
            "full_name": full_name,
            "email": email,
            "department": department,
            "role_ids": role_ids,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["delivery_status"] in {"not_connected", "not_sent", "failed", "sent"}
    assert token not in created.text
    user = _created_user(created)
    assert user["status"] == "invited"
    assert user["email"] == email
    return user, token


def test_admin_invited_user_creates(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.create.{uuid4().hex[:8]}@example.com"
    user, _token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-create-{uuid4().hex}",
    )
    assert user["status"] == "invited"
    assert "password" not in user


def test_invite_token_valid(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.valid.{uuid4().hex[:8]}@example.com"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-valid-{uuid4().hex}",
    )
    preview = auth_client.get(f"/auth/invite/{token}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["email"] == email
    assert preview.json()["full_name"] == user["full_name"]
    assert token not in preview.text


def test_expired_token_rejected(auth_client: TestClient, monkeypatch, db: Session) -> None:
    email = f"invite.expired.{uuid4().hex[:8]}@example.com"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-expired-{uuid4().hex}",
    )
    invitation = db.scalar(
        select(UserInvitation).where(UserInvitation.token_hash == hash_invite_token(token))
    )
    assert invitation is not None
    invitation.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    preview = auth_client.get(f"/auth/invite/{token}")
    assert preview.status_code == 404
    accepted = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    )
    assert accepted.status_code == 404


def test_consumed_token_rejected(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.consumed.{uuid4().hex[:8]}@example.com"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-consumed-{uuid4().hex}",
    )
    first = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    )
    assert first.status_code == 200, first.text
    second = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    )
    assert second.status_code == 404
    preview = auth_client.get(f"/auth/invite/{token}")
    assert preview.status_code == 404


def test_resend_invalidates_previous_token(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.resend.{uuid4().hex[:8]}@example.com"
    first_token = f"invite-first-{uuid4().hex}"
    user, _token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=first_token,
    )
    second_token = f"invite-second-{uuid4().hex}"
    _set_invite_token(monkeypatch, second_token)
    assert _login(auth_client).status_code == 200
    resent = auth_client.post(f"/users/{user['id']}/invite/resend")
    assert resent.status_code == 200, resent.text
    assert resent.json()["delivery_status"] in {"not_connected", "not_sent", "failed", "sent"}
    assert first_token not in resent.text
    assert second_token not in resent.text
    assert auth_client.get(f"/auth/invite/{first_token}").status_code == 404
    assert auth_client.get(f"/auth/invite/{second_token}").status_code == 200


def test_accept_sets_password_and_activates(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.accept.{uuid4().hex[:8]}@example.com"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-accept-{uuid4().hex}",
    )
    accepted = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    )
    assert accepted.status_code == 200, accepted.text
    assert STRONG_PASSWORD not in accepted.text
    fetched = auth_client.get(f"/users/{user['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "active"


def test_login_before_accept_impossible(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.nologin.{uuid4().hex[:8]}@example.com"
    _user, _token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-nologin-{uuid4().hex}",
    )
    auth_client.post("/auth/logout")
    blocked = _login(auth_client, email, STRONG_PASSWORD)
    assert blocked.status_code in {401, 403}
    known_default = _login(auth_client, email, "InvitedUser1!")
    assert known_default.status_code in {401, 403}


def test_login_after_accept_works(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.login.{uuid4().hex[:8]}@example.com"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-login-{uuid4().hex}",
    )
    assert auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    ).status_code == 200
    auth_client.post("/auth/logout")
    logged_in = _login(auth_client, email, STRONG_PASSWORD)
    assert logged_in.status_code == 200, logged_in.text
    assert logged_in.json()["email"] == email
    assert logged_in.json()["status"] == "active"


def test_privileged_role_mfa_enrollment_after_accept(auth_client: TestClient, monkeypatch) -> None:
    from investhome_api.services.mfa_enforcement import set_mfa_enforcement_disabled_for_tests

    email = f"invite.mfa.{uuid4().hex[:8]}@example.com"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_role_id(auth_client, "super_admin")],
        token=f"invite-mfa-{uuid4().hex}",
        full_name="Privileged Invitee",
    )
    assert auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    ).status_code == 200
    auth_client.post("/auth/logout")
    set_mfa_enforcement_disabled_for_tests(False)
    try:
        response = _login(auth_client, email, STRONG_PASSWORD)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body.get("mfa_enrollment_required") is True
        assert body.get("mfa_enrollment_challenge_token")
        me = auth_client.get("/auth/me")
        assert me.status_code == 401
    finally:
        set_mfa_enforcement_disabled_for_tests(True)


def test_deactivate_revokes_sessions(auth_client: TestClient, monkeypatch, db: Session) -> None:
    email = f"invite.revoke.{uuid4().hex[:8]}@example.com"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-revoke-{uuid4().hex}",
    )
    assert auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    ).status_code == 200
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, STRONG_PASSWORD).status_code == 200
    user_uuid = UUID(str(user["id"]))
    active_before = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user_uuid, AuthSession.revoked_at.is_(None))
    ).all()
    assert active_before
    assert _login(auth_client).status_code == 200
    deactivated = auth_client.post(f"/users/{user['id']}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    db.expire_all()
    active_after = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user_uuid, AuthSession.revoked_at.is_(None))
    ).all()
    assert active_after == []
    auth_client.post("/auth/logout")
    blocked = _login(auth_client, email, STRONG_PASSWORD)
    assert blocked.status_code == 403

    assert _login(auth_client).status_code == 200
    activated = auth_client.post(f"/users/{user['id']}/activate")
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, STRONG_PASSWORD).status_code == 200


def test_multi_role_assignment_preserved(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.roles.{uuid4().hex[:8]}@example.com"
    role_ids = [_read_only_role_id(auth_client), _role_id(auth_client, "sales")]
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=role_ids,
        token=f"invite-roles-{uuid4().hex}",
    )
    assert {role["id"] for role in user["roles"]} == set(role_ids)
    assert auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    ).status_code == 200
    fetched = auth_client.get(f"/users/{user['id']}")
    assert {role["id"] for role in fetched.json()["roles"]} == set(role_ids)


def test_non_super_admin_cannot_assign_super_admin(auth_client: TestClient, db: Session) -> None:
    assert _login(auth_client).status_code == 200
    super_admin_id = _role_id(auth_client, "super_admin")
    perm = db.scalar(select(Permission).where(Permission.resource == "users", Permission.action == "manage"))
    assert perm is not None
    view = db.scalar(select(Permission).where(Permission.resource == "users", Permission.action == "view"))
    role = Role(name="user_manager", code=f"user_mgr_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    if view is not None:
        db.add(RolePermission(role_id=role.id, permission_id=view.id))
    manager = User(
        full_name="User Manager",
        email=f"usermgr.{uuid4().hex[:8]}@example.com",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(manager)
    db.flush()
    db.add(UserRole(user_id=manager.id, role_id=role.id))
    db.commit()

    assert _login(auth_client, manager.email).status_code == 200
    denied = auth_client.post(
        "/users",
        json={
            "full_name": "Escalated",
            "email": f"escalated.{uuid4().hex[:8]}@example.com",
            "role_ids": [super_admin_id],
        },
    )
    assert denied.status_code == 403


def test_invite_audit_events_omit_secrets(auth_client: TestClient, monkeypatch, db: Session) -> None:
    email = f"invite.audit.{uuid4().hex[:8]}@example.com"
    token = f"invite-audit-{uuid4().hex}"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=token,
    )
    assert auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    ).status_code == 200
    db.expire_all()
    logs = db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50)).all()
    keys = {log.description_key for log in logs}
    assert "activity.user.invited" in keys
    assert "activity.user.invite_accepted" in keys
    for log in logs:
        meta = log.metadata_json if hasattr(log, "metadata_json") else getattr(log, "metadata", None)
        blob = str(meta or "")
        assert token not in blob
        assert STRONG_PASSWORD not in blob


def test_invite_accept_does_not_require_csrf_while_logged_in(
    auth_client: TestClient, monkeypatch
) -> None:
    email = f"invite.csrf.{uuid4().hex[:8]}@example.com"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-csrf-{uuid4().hex}",
    )
    auth_client.auto_csrf = False
    accepted = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": STRONG_PASSWORD},
    )
    assert accepted.status_code == 200, accepted.text
