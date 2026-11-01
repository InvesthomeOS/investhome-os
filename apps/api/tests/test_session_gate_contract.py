"""API ih_session contract shared with the Next.js middleware gate."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.services.auth_service import decode_access_token
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth

DEMO_PASSWORD = "Demo123!"
SALES_EMAIL = "sales@example.com"
ADMIN_EMAIL = "admin@example.com"
_JTI_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _set_cookie_headers(response) -> str:
    headers = response.headers
    raw = [
        value.decode() if isinstance(value, bytes) else value
        for key, value in headers.multi_items()
        if key.lower() == "set-cookie"
    ]
    return " | ".join(raw)


def test_login_session_claims_match_the_middleware_contract(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": SALES_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    token = auth_client.cookies.get("ih_session")
    assert isinstance(token, str) and token
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert isinstance(payload["sub"], str)
    assert isinstance(payload["exp"], int)
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["auth_time"], int)
    assert _JTI_RE.fullmatch(payload["jti"])
    assert "iss" not in payload
    assert "aud" not in payload
    assert decode_access_token(token) is not None
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == SALES_EMAIL


def test_bad_signature_and_expired_token_are_rejected(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": SALES_EMAIL, "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = auth_client.cookies.get("ih_session")
    assert isinstance(token, str)
    flipped = token[:-1] + ("a" if token[-1] != "a" else "b")
    auth_client.cookies.delete("ih_session")
    auth_client.cookies.set("ih_session", flipped)
    assert auth_client.get("/auth/me").status_code == 401
    assert decode_access_token(flipped) is None

    settings = get_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000099",
            "exp": now - timedelta(hours=1),
            "iat": now - timedelta(hours=2),
            "jti": "expired-test-jti",
            "auth_time": int(now.timestamp()) - 7200,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    auth_client.cookies.delete("ih_session")
    auth_client.cookies.set("ih_session", expired)
    assert auth_client.get("/auth/me").status_code == 401
    assert decode_access_token(expired) is None


def test_production_cookie_clear_uses_the_same_domain(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_COOKIE_DOMAIN", "os.investhome.com")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    get_settings.cache_clear()
    try:
        login = auth_client.post(
            "/auth/login",
            json={"email": SALES_EMAIL, "password": DEMO_PASSWORD},
        )
        assert login.status_code == 200
        issued = _set_cookie_headers(login).lower()
        assert "domain=os.investhome.com" in issued
        assert "path=/" in issued
        assert "httponly" in issued
        assert "secure" in issued
        assert "samesite=lax" in issued
        logout = auth_client.post("/auth/logout")
        assert logout.status_code == 200
        cleared = _set_cookie_headers(logout).lower()
        assert "domain=os.investhome.com" in cleared
        assert "path=/" in cleared
        assert "max-age=0" in cleared
        assert "httponly" in cleared
    finally:
        monkeypatch.delenv("AUTH_COOKIE_DOMAIN", raising=False)
        monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
        monkeypatch.delenv("AUTH_COOKIE_SAMESITE", raising=False)
        get_settings.cache_clear()


def test_wrong_password_and_failed_mfa_do_not_authenticate(auth_client: TestClient) -> None:
    wrong = auth_client.post(
        "/auth/login",
        json={"email": SALES_EMAIL, "password": "WrongPass1"},
    )
    assert wrong.status_code == 401
    assert auth_client.get("/auth/me").status_code == 401

    assert (
        auth_client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": DEMO_PASSWORD},
        ).status_code
        == 200
    )
    start = auth_client.post("/auth/mfa/enroll")
    assert start.status_code == 200, start.text
    totp_secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = auth_client.post(
        "/auth/mfa/enroll/confirm",
        json={"code": pyotp.TOTP(totp_secret).now()},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert auth_client.post("/auth/logout").status_code == 200

    challenged = auth_client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": DEMO_PASSWORD},
    )
    assert challenged.status_code == 200
    challenge = challenged.json()["mfa_challenge_token"]
    failed = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": challenge, "code": "000000"},
    )
    assert failed.status_code == 401
    assert auth_client.get("/auth/me").status_code == 401
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={"challenge_token": challenge, "code": pyotp.TOTP(totp_secret).now()},
    )
    assert verified.status_code == 200, verified.text
    assert auth_client.get("/auth/me").status_code == 200
    assert auth_client.cookies.get("ih_session")


def test_revoked_database_session_rejects_a_still_signed_token(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": SALES_EMAIL, "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = auth_client.cookies.get("ih_session")
    assert isinstance(token, str) and token
    assert decode_access_token(token) is not None
    assert auth_client.post("/auth/logout").status_code == 200
    auth_client.cookies.set("ih_session", token)
    assert auth_client.get("/auth/me").status_code == 401
