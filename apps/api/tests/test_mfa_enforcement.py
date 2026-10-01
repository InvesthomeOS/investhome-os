"""Mandatory MFA enrollment at login for privileged roles."""

from __future__ import annotations

import logging
import secrets

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.mfa_challenge import (
    GENERIC_UNAVAILABLE_MESSAGE,
    MfaChallengeStoreError,
    expire_mfa_challenge_for_tests,
    reset_mfa_challenge_store_for_tests,
)
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth
from investhome_api.services.mfa_enforcement import (
    MANDATORY_MFA_ROLE_CODES,
    OPTIONAL_MFA_ROLE_CODES,
)
from investhome_api.services.mfa_login import INVALID_MFA_MESSAGE

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"
SALES_EMAIL = "sales@example.com"
FINANCE_EMAIL = "finance@example.com"
CONSTRUCTION_EMAIL = "construction@example.com"


class _BoomChallengeStore:
    def put(self, token_digest: str, user_id: str, ttl_seconds: int, purpose: str = "login") -> None:
        raise MfaChallengeStoreError("forced backend failure")

    def get(self, token_digest: str):
        raise MfaChallengeStoreError("forced backend failure")

    def consume(self, token_digest: str):
        raise MfaChallengeStoreError("forced backend failure")

    def drop_user_index(self, user_id: str, token_digest: str) -> None:
        raise MfaChallengeStoreError("forced backend failure")

    def drop_all_for_user(self, user_id: str) -> None:
        raise MfaChallengeStoreError("forced backend failure")


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _set_cookie_names(response) -> str:
    if hasattr(response.headers, "get_list"):
        raw = response.headers.get_list("set-cookie")
    elif hasattr(response.headers, "getlist"):
        raw = response.headers.getlist("set-cookie")
    else:
        raw = [
            value.decode() if isinstance(value, bytes) else value
            for key, value in response.headers.multi_items()
            if key.lower() == "set-cookie"
        ]
    return " | ".join(raw).lower()


def _session_cookie_issued(response) -> bool:
    joined = _set_cookie_names(response)
    if "ih_session=" not in joined:
        return False
    return "max-age=0" not in joined


def _create_role_user(db: Session, email: str, role_code: str) -> User:
    role = db.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        role = Role(name=role_code, code=role_code, is_system_role=True)
        db.add(role)
        db.flush()
    user = User(
        full_name=email.split("@")[0],
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _password_enrollment(client: TestClient, email: str) -> str:
    response = _login(client, email)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("mfa_enrollment_required") is True
    token = body["mfa_enrollment_challenge_token"]
    assert token
    assert len(token) >= 16
    assert body["expires_in"] == 300
    assert "email" not in body
    assert "recovery_codes" not in body
    assert "otpauth_uri" not in body
    assert not _session_cookie_issued(response)
    assert client.get("/auth/me").status_code == 401
    return token


def _complete_required_enrollment(client: TestClient, email: str) -> tuple[str, list[str]]:
    token = _password_enrollment(client, email)
    start = client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    assert start.status_code == 200, start.text
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = client.post(
        "/auth/mfa/enroll/required/confirm",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert confirmed.status_code == 200, confirmed.text
    codes = confirmed.json()["recovery_codes"]
    return secret, codes


def test_mandatory_and_optional_role_sets() -> None:
    assert "super_admin" in MANDATORY_MFA_ROLE_CODES
    assert "executive" in MANDATORY_MFA_ROLE_CODES
    assert "finance" in MANDATORY_MFA_ROLE_CODES
    assert "operations" in MANDATORY_MFA_ROLE_CODES
    assert "investor_relations" in MANDATORY_MFA_ROLE_CODES
    assert "marketing" in MANDATORY_MFA_ROLE_CODES
    assert "sales" in OPTIONAL_MFA_ROLE_CODES
    assert "construction" in OPTIONAL_MFA_ROLE_CODES
    assert "partner" in OPTIONAL_MFA_ROLE_CODES
    assert "assistant" in OPTIONAL_MFA_ROLE_CODES
    assert "read_only" in OPTIONAL_MFA_ROLE_CODES
    assert MANDATORY_MFA_ROLE_CODES.isdisjoint(OPTIONAL_MFA_ROLE_CODES)


def test_mandatory_role_without_mfa_cannot_enter_after_password(auth_client: TestClient) -> None:
    token = _password_enrollment(auth_client, ADMIN_EMAIL)
    assert token
    assert auth_client.get("/auth/me").status_code == 401
    assert auth_client.get("/users").status_code == 401


def test_mandatory_role_is_taken_to_enrollment(auth_client: TestClient, db: Session) -> None:
    _create_role_user(db, FINANCE_EMAIL, "finance")
    body = _login(auth_client, FINANCE_EMAIL).json()
    assert body["mfa_enrollment_required"] is True
    assert body["mfa_enrollment_challenge_token"]
    start = auth_client.post(
        "/auth/mfa/enroll/required",
        json={"challenge_token": body["mfa_enrollment_challenge_token"]},
    )
    assert start.status_code == 200, start.text
    payload = start.json()
    assert payload["otpauth_uri"].startswith("otpauth://totp/")
    assert payload["pending"] is True
    assert auth_client.get("/auth/me").status_code == 401


def test_successful_enrollment_creates_session(
    auth_client: TestClient, caplog
) -> None:
    caplog.set_level(logging.DEBUG)
    token = _password_enrollment(auth_client, ADMIN_EMAIL)
    start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = auth_client.post(
        "/auth/mfa/enroll/required/confirm",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["mfa_enabled"] is True
    assert len(body["recovery_codes"]) == 10
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["user"]["mfa_enabled"] is True
    assert _session_cookie_issued(confirmed)
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL
    assert me.json()["mfa_enabled"] is True
    assert token not in caplog.text
    assert secret not in caplog.text
    for code in body["recovery_codes"]:
        assert code not in caplog.text
    assert "otpauth://" not in caplog.text


def test_mandatory_role_with_mfa_uses_existing_second_step(auth_client: TestClient) -> None:
    secret, _codes = _complete_required_enrollment(auth_client, ADMIN_EMAIL)
    assert auth_client.post("/auth/logout").status_code == 200
    login = _login(auth_client, ADMIN_EMAIL)
    assert login.status_code == 200
    body = login.json()
    assert body.get("mfa_required") is True
    assert body.get("mfa_enrollment_required") is not True
    assert not _session_cookie_issued(login)
    assert auth_client.get("/auth/me").status_code == 401
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": body["mfa_challenge_token"], "code": pyotp.TOTP(secret).now()},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["email"] == ADMIN_EMAIL
    assert auth_client.get("/auth/me").status_code == 200


def test_non_mandatory_role_login_unchanged(auth_client: TestClient, db: Session) -> None:
    response = _login(auth_client, SALES_EMAIL)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == SALES_EMAIL
    assert body.get("mfa_required") is not True
    assert body.get("mfa_enrollment_required") is not True
    assert _session_cookie_issued(response)
    assert auth_client.get("/auth/me").status_code == 200

    _create_role_user(db, CONSTRUCTION_EMAIL, "construction")
    construction = _login(auth_client, CONSTRUCTION_EMAIL)
    assert construction.status_code == 200
    assert construction.json()["email"] == CONSTRUCTION_EMAIL
    assert construction.json().get("mfa_enrollment_required") is not True
    assert _session_cookie_issued(construction)


def test_expired_enrollment_challenge_rejected(auth_client: TestClient) -> None:
    token = _password_enrollment(auth_client, ADMIN_EMAIL)
    expire_mfa_challenge_for_tests(token)
    start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    assert start.status_code == 401
    assert start.json()["detail"] == INVALID_MFA_MESSAGE
    confirm = auth_client.post(
        "/auth/mfa/enroll/required/confirm",
        json={"challenge_token": token, "code": "123456"},
    )
    assert confirm.status_code == 401
    assert auth_client.get("/auth/me").status_code == 401


def test_reused_enrollment_challenge_rejected(auth_client: TestClient) -> None:
    token = _password_enrollment(auth_client, ADMIN_EMAIL)
    start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    first = auth_client.post(
        "/auth/mfa/enroll/required/confirm",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert first.status_code == 200
    auth_client.post("/auth/logout")
    reused = auth_client.post(
        "/auth/mfa/enroll/required/confirm",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert reused.status_code == 401
    assert reused.json()["detail"] == INVALID_MFA_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_forged_enrollment_challenge_rejected(auth_client: TestClient) -> None:
    forged = auth_client.post(
        "/auth/mfa/enroll/required",
        json={"challenge_token": secrets.token_urlsafe(32)},
    )
    assert forged.status_code == 401
    assert forged.json()["detail"] == INVALID_MFA_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_login_challenge_cannot_start_enrollment(auth_client: TestClient) -> None:
    secret, _codes = _complete_required_enrollment(auth_client, ADMIN_EMAIL)
    auth_client.post("/auth/logout")
    login = _login(auth_client, ADMIN_EMAIL)
    token = login.json()["mfa_challenge_token"]
    start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    assert start.status_code == 401
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert verified.status_code == 200


def test_production_enrollment_store_failure_fails_closed(
    auth_client: TestClient, monkeypatch, caplog
) -> None:
    class _ProductionSettings:
        environment = "production"
        redis_url = "redis://localhost:6379/0"

    monkeypatch.setattr(
        "investhome_api.services.mfa_challenge.get_settings",
        lambda: _ProductionSettings(),
    )
    reset_mfa_challenge_store_for_tests(_BoomChallengeStore())
    caplog.set_level(logging.ERROR, logger="investhome.auth.mfa")
    login = _login(auth_client, ADMIN_EMAIL)
    assert login.status_code == 503
    assert login.json()["detail"] == GENERIC_UNAVAILABLE_MESSAGE
    assert not _session_cookie_issued(login)
    assert auth_client.get("/auth/me").status_code == 401
    assert "mfa_challenge_backend_failure" in caplog.text
    assert "mfa_enrollment_challenge_token" not in caplog.text


def test_required_enrollment_does_not_enable_mfa_before_confirm(
    auth_client: TestClient, db: Session
) -> None:
    token = _password_enrollment(auth_client, ADMIN_EMAIL)
    start = auth_client.post("/auth/mfa/enroll/required", json={"challenge_token": token})
    assert start.status_code == 200
    db.expire_all()
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert user is not None
    assert user.mfa_enabled is False
    assert user.mfa_method is None
    assert auth_client.get("/auth/me").status_code == 401
