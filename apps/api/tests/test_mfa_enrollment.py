"""TOTP MFA enrollment — authenticated users only. Login is unchanged."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import User
from investhome_api.models.user_mfa import UserMfa, UserMfaRecoveryCode
from investhome_api.services.mfa_crypto import CURRENT_PREFIX, recovery_code_matches, unseal_totp_secret
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"


def _login(client: TestClient, email: str = ADMIN_EMAIL) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _enroll(client: TestClient) -> dict:
    response = client.post("/auth/mfa/enroll")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["issuer"]
    assert body["account_label"]
    assert body["pending"] is True
    return body


def _secret_from_start(body: dict) -> str:
    return totp_secret_from_otpauth(body["otpauth_uri"])


def _assert_logs_have_no_secrets(caplog, *, secret: str | None = None, codes: list[str] | None = None) -> None:
    text = caplog.text
    if secret:
        assert secret not in text
    if codes:
        for code in codes:
            assert code not in text
    assert "otpauth://" not in text


def test_unauthenticated_enrollment_rejected(auth_client: TestClient) -> None:
    assert auth_client.post("/auth/mfa/enroll").status_code == 401
    assert auth_client.post("/auth/mfa/enroll/confirm", json={"code": "123456"}).status_code == 401


def test_start_enrollment_returns_otpauth_for_authenticated_user(
    auth_client: TestClient, caplog
) -> None:
    caplog.set_level(logging.DEBUG)
    _login(auth_client)
    body = _enroll(auth_client)
    assert body["account_label"] == ADMIN_EMAIL
    secret = _secret_from_start(body)
    assert len(secret) >= 32
    parsed = parse_qs(urlparse(body["otpauth_uri"]).query)
    assert parsed.get("issuer", [""])[0] == body["issuer"]
    _assert_logs_have_no_secrets(caplog, secret=secret)


def test_secret_stored_encrypted_not_plaintext(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client)
    body = _enroll(auth_client)
    secret = _secret_from_start(body)
    db.expire_all()
    row = db.scalar(
        select(UserMfa).join(User, UserMfa.user_id == User.id).where(User.email == ADMIN_EMAIL)
    )
    assert row is not None
    assert row.enrollment_confirmed_at is None
    assert row.totp_secret_ciphertext
    assert row.totp_secret_ciphertext.startswith(CURRENT_PREFIX)
    assert secret not in row.totp_secret_ciphertext
    assert unseal_totp_secret(row.totp_secret_ciphertext) == secret
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert user is not None
    assert user.mfa_enabled is False
    assert user.mfa_method is None


def test_valid_totp_confirms_and_enables_mfa(
    auth_client: TestClient, db: Session, caplog
) -> None:
    caplog.set_level(logging.DEBUG)
    _login(auth_client)
    start = _enroll(auth_client)
    secret = _secret_from_start(start)
    code = pyotp.TOTP(secret).now()
    confirmed = auth_client.post("/auth/mfa/enroll/confirm", json={"code": code})
    assert confirmed.status_code == 200, confirmed.text
    payload = confirmed.json()
    assert payload["mfa_enabled"] is True
    assert payload["mfa_method"] == "totp"
    codes = payload["recovery_codes"]
    assert len(codes) == 10
    assert all(isinstance(item, str) and "-" in item for item in codes)
    _assert_logs_have_no_secrets(caplog, secret=secret, codes=codes)

    db.expire_all()
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert user is not None
    assert user.mfa_enabled is True
    assert user.mfa_method == "totp"
    assert user.mfa_enforced_at is not None
    row = db.scalar(select(UserMfa).where(UserMfa.user_id == user.id))
    assert row is not None
    assert row.enrollment_confirmed_at is not None


def test_invalid_totp_rejected(auth_client: TestClient) -> None:
    _login(auth_client)
    _enroll(auth_client)
    response = auth_client.post("/auth/mfa/enroll/confirm", json={"code": "000000"})
    assert response.status_code == 400
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["mfa_enabled"] is False


def test_recovery_codes_stored_as_hashes_only(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client)
    secret = _secret_from_start(_enroll(auth_client))
    confirmed = auth_client.post(
        "/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret).now()}
    )
    plaintext = confirmed.json()["recovery_codes"]
    db.expire_all()
    hashes = list(db.scalars(select(UserMfaRecoveryCode.code_hash)))
    assert len(hashes) == 10
    for item in plaintext:
        assert any(recovery_code_matches(item, digest) for digest in hashes)
        for digest in hashes:
            assert item not in digest
            assert not digest.startswith(item)


def test_confirmed_mfa_cannot_be_silently_overwritten(auth_client: TestClient) -> None:
    _login(auth_client)
    secret = _secret_from_start(_enroll(auth_client))
    assert (
        auth_client.post(
            "/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret).now()}
        ).status_code
        == 200
    )
    restart = auth_client.post("/auth/mfa/enroll")
    assert restart.status_code == 409
    reconfirm = auth_client.post("/auth/mfa/enroll/confirm", json={"code": "123456"})
    assert reconfirm.status_code == 409


def test_pending_enrollment_can_be_restarted(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client)
    first = _enroll(auth_client)
    second = _enroll(auth_client)
    secret_one = _secret_from_start(first)
    secret_two = _secret_from_start(second)
    assert secret_one != secret_two
    stale = auth_client.post(
        "/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret_one).now()}
    )
    assert stale.status_code == 400
    ok = auth_client.post(
        "/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret_two).now()}
    )
    assert ok.status_code == 200
    db.expire_all()
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert user is not None and user.mfa_enabled is True


def test_confirm_rate_limited_after_failed_attempts(auth_client: TestClient) -> None:
    _login(auth_client)
    _enroll(auth_client)
    for _ in range(5):
        failed = auth_client.post("/auth/mfa/enroll/confirm", json={"code": "000000"})
        assert failed.status_code == 400
    blocked = auth_client.post("/auth/mfa/enroll/confirm", json={"code": "000000"})
    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after") is not None


def test_login_after_confirmed_mfa_requires_challenge_not_session(
    auth_client: TestClient,
) -> None:
    _login(auth_client)
    secret = _secret_from_start(_enroll(auth_client))
    assert (
        auth_client.post(
            "/auth/mfa/enroll/confirm", json={"code": pyotp.TOTP(secret).now()}
        ).status_code
        == 200
    )
    assert auth_client.post("/auth/logout").status_code == 200
    login = auth_client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": DEMO_PASSWORD}
    )
    assert login.status_code == 200
    body = login.json()
    assert body.get("mfa_required") is True
    assert body.get("mfa_challenge_token")
    assert "recovery_codes" not in body
    assert auth_client.get("/auth/me").status_code == 401
