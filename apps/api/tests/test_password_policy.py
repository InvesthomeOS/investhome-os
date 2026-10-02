"""Password policy: length, weak/demo values, account identifiers. Existing hashes stay valid."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from investhome_api.models.user_auth import User
from investhome_api.services.auth_service import hash_password, verify_password
from investhome_api.services.password_policy import (
    GENERIC_PASSWORD_ERROR,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PasswordPolicyError,
    validate_new_password,
)

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"
STRONG_PASSWORD = "correct-horse-battery-staple-9"
LONG_PASSWORD = "Lw9#" + "".join(chr(65 + (i % 26)) + str(i % 10) for i in range(62))


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _read_only_role_id(client: TestClient) -> str:
    roles = client.get("/roles").json()["items"]
    return next(item["id"] for item in roles if item["code"] == "read_only")


def _created_user(response) -> dict:
    body = response.json()
    return body["user"] if "user" in body else body


def _set_invite_token(monkeypatch, token: str) -> str:
    monkeypatch.setattr(
        "investhome_api.services.user_invitation.generate_invite_token",
        lambda: token,
    )
    return token


def _invite_and_activate(
    client: TestClient,
    monkeypatch,
    *,
    email: str,
    password: str,
    full_name: str,
) -> dict:
    token = f"policy-{email.replace('@', '-').replace('.', '-')}"
    if len(token) < 16:
        token = f"{token}-invite-token"
    _set_invite_token(monkeypatch, token)
    created = client.post(
        "/users",
        json={
            "full_name": full_name,
            "email": email,
            "role_ids": [_read_only_role_id(client)],
        },
    )
    assert created.status_code == 201, created.text
    accepted = client.post(f"/auth/invite/{token}/accept", json={"password": password})
    assert accepted.status_code == 200, accepted.text
    return _created_user(created)


def test_policy_constants() -> None:
    assert MIN_PASSWORD_LENGTH == 12
    assert MAX_PASSWORD_LENGTH >= 128
    assert len(LONG_PASSWORD) == 128


def test_short_password_rejected_by_policy() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_new_password("Short1!", email="user@example.com")


def test_common_and_demo_passwords_rejected_by_policy() -> None:
    for candidate in ("password1234", "Demo123!", "Investhome2026!", "aaaaaaaaaaaa", "123456789012"):
        with pytest.raises(PasswordPolicyError):
            validate_new_password(candidate, email="user@example.com")


def test_email_based_password_rejected_by_policy() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_new_password("alex.river-ok12", email="alex.river@example.com")
    with pytest.raises(PasswordPolicyError):
        validate_new_password("prefix-admin-suffix", email="admin@example.com")


def test_strong_and_long_passwords_accepted_by_policy() -> None:
    validate_new_password(STRONG_PASSWORD, email="user@example.com")
    validate_new_password(LONG_PASSWORD, email="user@example.com")


def test_existing_user_with_legacy_password_can_still_log_in(auth_client: TestClient) -> None:
    response = _login(auth_client)
    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL
    me = auth_client.get("/auth/me")
    assert me.status_code == 200


def test_password_under_12_rejected_on_change(auth_client: TestClient) -> None:
    assert _login(auth_client).status_code == 200
    response = auth_client.post(
        "/auth/change-password",
        json={"current_password": DEMO_PASSWORD, "new_password": "Short1!xx"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC_PASSWORD_ERROR
    assert DEMO_PASSWORD not in response.text
    assert "Short1" not in response.text
    assert _login(auth_client).status_code == 200


def test_common_password_rejected_on_change(auth_client: TestClient) -> None:
    assert _login(auth_client).status_code == 200
    response = auth_client.post(
        "/auth/change-password",
        json={"current_password": DEMO_PASSWORD, "new_password": "password1234"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC_PASSWORD_ERROR


def test_email_based_password_rejected_on_accept(auth_client: TestClient, monkeypatch) -> None:
    assert _login(auth_client).status_code == 200
    email = "jordan.hale@example.com"
    token = "policy-jordan-hale-token"
    _set_invite_token(monkeypatch, token)
    created = auth_client.post(
        "/users",
        json={
            "full_name": "Jordan Hale",
            "email": email,
            "role_ids": [_read_only_role_id(auth_client)],
        },
    )
    assert created.status_code == 201, created.text
    response = auth_client.post(
        f"/auth/invite/{token}/accept",
        json={"password": "jordan.hale-ok"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC_PASSWORD_ERROR
    assert "jordan.hale" not in response.text.lower() or response.json()["detail"] == GENERIC_PASSWORD_ERROR


def test_strong_password_accepted_on_create_and_login(auth_client: TestClient, monkeypatch) -> None:
    assert _login(auth_client).status_code == 200
    email = "policy.strong@example.com"
    created_user = _invite_and_activate(
        auth_client,
        monkeypatch,
        email=email,
        password=STRONG_PASSWORD,
        full_name="Policy Strong",
    )
    assert "password" not in created_user
    assert STRONG_PASSWORD not in str(created_user)
    auth_client.post("/auth/logout")
    login = _login(auth_client, email, STRONG_PASSWORD)
    assert login.status_code == 200
    assert login.json()["email"] == email


def test_long_password_is_not_truncated(auth_client: TestClient, monkeypatch) -> None:
    assert _login(auth_client).status_code == 200
    email = "policy.long@example.com"
    _invite_and_activate(
        auth_client,
        monkeypatch,
        email=email,
        password=LONG_PASSWORD,
        full_name="Policy Long",
    )
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, LONG_PASSWORD).status_code == 200
    truncated = LONG_PASSWORD[:72]
    assert truncated != LONG_PASSWORD
    failed = _login(auth_client, email, truncated)
    assert failed.status_code == 401
    digest = hash_password(LONG_PASSWORD)
    assert verify_password(LONG_PASSWORD, digest)
    assert not verify_password(truncated, digest)


def test_password_change_enforces_policy_then_accepts_strong(auth_client: TestClient, monkeypatch) -> None:
    assert _login(auth_client).status_code == 200
    email = "policy.change@example.com"
    _invite_and_activate(
        auth_client,
        monkeypatch,
        email=email,
        password=STRONG_PASSWORD,
        full_name="Policy Change",
    )
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, STRONG_PASSWORD).status_code == 200
    rejected = auth_client.post(
        "/auth/change-password",
        json={"current_password": STRONG_PASSWORD, "new_password": "password1234"},
    )
    assert rejected.status_code == 400
    next_password = "another-correct-horse-battery-4"
    updated = auth_client.post(
        "/auth/change-password",
        json={"current_password": STRONG_PASSWORD, "new_password": next_password},
    )
    assert updated.status_code == 200
    assert next_password not in updated.text
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, STRONG_PASSWORD).status_code == 401
    assert _login(auth_client, email, next_password).status_code == 200


def test_admin_password_reset_does_not_return_secret_and_invalidates_old(
    auth_client: TestClient,
    monkeypatch,
) -> None:
    assert _login(auth_client).status_code == 200
    email = "policy.reset@example.com"
    created_user = _invite_and_activate(
        auth_client,
        monkeypatch,
        email=email,
        password=STRONG_PASSWORD,
        full_name="Policy Reset",
    )
    user_id = created_user["id"]
    assert _login(auth_client).status_code == 200
    reset = auth_client.post(f"/users/{user_id}/reset-password")
    assert reset.status_code == 200, reset.text
    body = reset.json()
    assert "password" not in body or "not returned" in body.get("message", "").lower()
    assert STRONG_PASSWORD not in reset.text
    auth_client.post("/auth/logout")
    assert _login(auth_client, email, STRONG_PASSWORD).status_code == 401


def test_invited_user_does_not_use_fixed_default_password(auth_client: TestClient) -> None:
    assert _login(auth_client).status_code == 200
    email = "policy.invite@example.com"
    created = auth_client.post(
        "/users",
        json={
            "full_name": "Policy Invite",
            "email": email,
            "role_ids": [_read_only_role_id(auth_client)],
        },
    )
    assert created.status_code == 201, created.text
    assert _created_user(created)["status"] == "invited"
    auth_client.post("/auth/logout")
    known = _login(auth_client, email, "InvitedUser1!")
    assert known.status_code in {401, 403}


def test_production_rejects_demo_staff_login(auth_client: TestClient, monkeypatch) -> None:
    from investhome_api.config.settings import get_settings
    from investhome_api.db import session as session_module
    from sqlalchemy import select

    db = session_module.SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        assert admin is not None
        admin.is_demo = True
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "investhome_api.api.routes.auth.production_blocks_demo_staff_login",
        lambda: True,
    )
    response = _login(auth_client)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    get_settings.cache_clear()


def test_seed_demo_users_skipped_in_production(monkeypatch) -> None:
    from types import SimpleNamespace

    from investhome_api.db.auth_seed import seed_demo_users

    monkeypatch.delenv("ALLOW_DEMO_SEED_IN_PRODUCTION", raising=False)
    monkeypatch.setattr(
        "investhome_api.config.settings.get_settings",
        lambda: SimpleNamespace(environment="production"),
    )
    assert seed_demo_users() == 0
