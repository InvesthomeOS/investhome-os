"""MFA login challenge — password then TOTP/recovery. Enrollment unchanged."""

from __future__ import annotations

import logging
import secrets

import pyotp
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.user_mfa import UserMfaRecoveryCode
from investhome_api.services.mfa_challenge import (
    GENERIC_UNAVAILABLE_MESSAGE,
    MfaChallengeStoreError,
    expire_mfa_challenge_for_tests,
    reset_mfa_challenge_store_for_tests,
)
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth
from investhome_api.services.mfa_login import INVALID_MFA_MESSAGE

DEMO_PASSWORD = "Demo123!"
WRONG_PASSWORD = "WrongPass1"
ADMIN_EMAIL = "admin@example.com"


class _BoomChallengeStore:
    def put(self, token_digest: str, user_id: str, ttl_seconds: int, purpose: str = "login") -> None:
        raise MfaChallengeStoreError("forced backend failure")

    def get(self, token_digest: str):
        raise MfaChallengeStoreError("forced backend failure")

    def consume(self, token_digest: str):
        raise MfaChallengeStoreError("forced backend failure")

    def drop_user_index(self, user_id: str, token_digest: str) -> None:
        raise MfaChallengeStoreError("forced backend failure")


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _enable_mfa(client: TestClient, email: str = ADMIN_EMAIL) -> tuple[str, list[str]]:
    assert _login(client, email).status_code == 200
    start = client.post("/auth/mfa/enroll")
    assert start.status_code == 200, start.text
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = client.post("/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret).now()})
    assert confirmed.status_code == 200, confirmed.text
    codes = confirmed.json()["recovery_codes"]
    assert client.post("/auth/logout").status_code == 200
    return secret, codes


def _password_step(client: TestClient, email: str = ADMIN_EMAIL) -> str:
    response = _login(client, email)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mfa_required"] is True
    token = body["mfa_challenge_token"]
    assert token
    assert body["expires_in"] == 300
    return token


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


def test_non_mfa_user_login_remains_normal(auth_client: TestClient) -> None:
    response = _login(auth_client, "sales@example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "sales@example.com"
    assert body.get("mfa_required") is not True
    assert "mfa_challenge_token" not in body
    assert _session_cookie_issued(response)
    assert auth_client.get("/auth/me").status_code == 200


def test_mfa_password_step_does_not_issue_session(auth_client: TestClient) -> None:
    _enable_mfa(auth_client)
    response = _login(auth_client)
    assert response.status_code == 200
    body = response.json()
    assert body["mfa_required"] is True
    assert body["mfa_method"] == "totp"
    assert "email" not in body
    assert not _session_cookie_issued(response)
    assert auth_client.get("/auth/me").status_code == 401


def test_mfa_password_failure_stays_generic(auth_client: TestClient) -> None:
    _enable_mfa(auth_client)
    missing = _login(auth_client, "missing-mfa@example.com", WRONG_PASSWORD)
    known = _login(auth_client, ADMIN_EMAIL, WRONG_PASSWORD)
    assert missing.status_code == known.status_code == 401
    assert missing.json()["detail"] == known.json()["detail"] == "Invalid email or password"
    assert "mfa_required" not in missing.json()
    assert "mfa_required" not in known.json()
    assert auth_client.get("/auth/me").status_code == 401


def test_valid_totp_completes_login(auth_client: TestClient, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)
    code = pyotp.TOTP(secret).now()
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": code},
    )
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["mfa_enabled"] is True
    assert _session_cookie_issued(verified)
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL
    assert token not in caplog.text
    assert secret not in caplog.text
    assert "otpauth://" not in caplog.text


def test_invalid_totp_rejected(auth_client: TestClient) -> None:
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)
    failed = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": "000000"},
    )
    assert failed.status_code == 401
    assert failed.json()["detail"] == INVALID_MFA_MESSAGE
    assert not _session_cookie_issued(failed)
    assert auth_client.get("/auth/me").status_code == 401
    ok = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert ok.status_code == 200


def test_expired_challenge_rejected(auth_client: TestClient) -> None:
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)
    expire_mfa_challenge_for_tests(token)
    expired = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert expired.status_code == 401
    assert expired.json()["detail"] == INVALID_MFA_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_reused_challenge_rejected(auth_client: TestClient) -> None:
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)
    code = pyotp.TOTP(secret).now()
    first = auth_client.post(
        "/auth/mfa/verify", json={"challenge_token": token, "code": code}
    )
    assert first.status_code == 200
    auth_client.post("/auth/logout")
    reused = auth_client.post(
        "/auth/mfa/verify", json={"challenge_token": token, "code": code}
    )
    assert reused.status_code == 401
    assert reused.json()["detail"] == INVALID_MFA_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_recovery_code_works_once(auth_client: TestClient, db: Session, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    _secret, codes = _enable_mfa(auth_client)
    first_code = codes[0]
    token = _password_step(auth_client)
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": first_code},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["email"] == ADMIN_EMAIL
    assert first_code not in caplog.text
    db.expire_all()
    used = db.scalars(select(UserMfaRecoveryCode).where(UserMfaRecoveryCode.used_at.isnot(None))).all()
    assert len(used) == 1

    auth_client.post("/auth/logout")
    token_again = _password_step(auth_client)
    reused = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token_again, "code": first_code},
    )
    assert reused.status_code == 401
    assert auth_client.get("/auth/me").status_code == 401

    next_token = token_again
    if reused.status_code != 200:
        next_ok = auth_client.post(
            "/auth/mfa/verify",
            json={"challenge_token": next_token, "code": codes[1]},
        )
        assert next_ok.status_code == 200


def test_mfa_verify_rate_limit(auth_client: TestClient) -> None:
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)
    for _ in range(5):
        failed = auth_client.post(
            "/auth/mfa/verify",
            json={"challenge_token": token, "code": "000000"},
        )
        assert failed.status_code == 401
    blocked = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after") is not None
    assert auth_client.get("/auth/me").status_code == 401


def test_forged_challenge_rejected(auth_client: TestClient) -> None:
    _enable_mfa(auth_client)
    forged = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": secrets.token_urlsafe(32), "code": "123456"},
    )
    assert forged.status_code == 401
    assert forged.json()["detail"] == INVALID_MFA_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_production_challenge_store_failure_fails_closed_on_login(
    auth_client: TestClient, monkeypatch, caplog
) -> None:
    _enable_mfa(auth_client)

    class _ProductionSettings:
        environment = "production"
        redis_url = "redis://localhost:6379/0"

    monkeypatch.setattr(
        "investhome_api.services.mfa_challenge.get_settings",
        lambda: _ProductionSettings(),
    )
    reset_mfa_challenge_store_for_tests(_BoomChallengeStore())
    caplog.set_level(logging.ERROR, logger="investhome.auth.mfa")
    login = _login(auth_client)
    assert login.status_code == 503
    assert login.json()["detail"] == GENERIC_UNAVAILABLE_MESSAGE
    assert not _session_cookie_issued(login)
    assert auth_client.get("/auth/me").status_code == 401
    assert "mfa_challenge_backend_failure" in caplog.text


def test_production_challenge_store_failure_fails_closed_on_verify(
    auth_client: TestClient, monkeypatch
) -> None:
    secret, _codes = _enable_mfa(auth_client)
    token = _password_step(auth_client)

    class _ProductionSettings:
        environment = "production"
        redis_url = "redis://localhost:6379/0"

    monkeypatch.setattr(
        "investhome_api.services.mfa_challenge.get_settings",
        lambda: _ProductionSettings(),
    )
    reset_mfa_challenge_store_for_tests(_BoomChallengeStore())
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert verified.status_code == 503
    assert verified.json()["detail"] == GENERIC_UNAVAILABLE_MESSAGE
    assert auth_client.get("/auth/me").status_code == 401


def test_create_challenge_production_unit_fail_closed(monkeypatch) -> None:
    from investhome_api.services.mfa_challenge import create_mfa_challenge

    class _ProductionSettings:
        environment = "production"
        redis_url = "redis://localhost:6379/0"

    monkeypatch.setattr(
        "investhome_api.services.mfa_challenge.get_settings",
        lambda: _ProductionSettings(),
    )
    reset_mfa_challenge_store_for_tests(_BoomChallengeStore())
    with pytest.raises(HTTPException) as excinfo:
        create_mfa_challenge(user_id="00000000-0000-0000-0000-000000000001")
    assert excinfo.value.status_code == 503
    assert excinfo.value.detail == GENERIC_UNAVAILABLE_MESSAGE
