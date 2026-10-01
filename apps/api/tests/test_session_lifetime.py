"""Idle timeout + absolute session lifetime. Sliding refresh cannot pass the cap."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select

from investhome_api.config.settings import get_settings
from investhome_api.db import session as session_module
from investhome_api.models.security_enterprise import AuthSession
from investhome_api.services.mfa_enrollment import totp_secret_from_otpauth
from investhome_api.services.session_lifetime import AUTH_TIME_CLAIM, compute_access_expiry

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"


_SESSION_COOKIE_RE = re.compile(r"ih_session=([^;]+)", re.IGNORECASE)


def _login(client: TestClient, email: str = ADMIN_EMAIL):
    return client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})


def _set_lifetime(monkeypatch, *, idle_minutes: int, absolute_minutes: int) -> None:
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", str(idle_minutes))
    monkeypatch.setenv("SESSION_ABSOLUTE_TIMEOUT_MINUTES", str(absolute_minutes))
    get_settings.cache_clear()


def _cookie() -> str:
    settings = get_settings()
    return settings.auth_cookie_name


def _decode_cookie(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _load_session(jti: str) -> AuthSession:
    db = session_module.SessionLocal()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == jti))
        assert row is not None
        db.expunge(row)
        return row
    finally:
        db.close()


def _update_session(jti: str, **values) -> AuthSession:
    db = session_module.SessionLocal()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == jti))
        assert row is not None
        for key, value in values.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        db.expunge(row)
        return row
    finally:
        db.close()


def _set_cookie(client: TestClient, token: str) -> None:
    client.cookies.delete("ih_session")
    client.cookies.set("ih_session", token)


def _token_from_set_cookie(response) -> str | None:
    for key, value in response.headers.multi_items():
        if key.lower() != "set-cookie":
            continue
        raw = value.decode() if isinstance(value, bytes) else value
        if "max-age=0" in raw.lower():
            continue
        match = _SESSION_COOKIE_RE.search(raw)
        if match:
            return match.group(1)
    return None


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


def test_compute_access_expiry_never_exceeds_absolute(monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=480, absolute_minutes=1440)
    started = datetime.now(UTC) - timedelta(hours=20)
    now = datetime.now(UTC)
    expiry = compute_access_expiry(started_at=started, now=now)
    assert expiry is not None
    assert expiry <= started + timedelta(hours=24)
    assert expiry <= now + timedelta(hours=8)


def test_compute_access_expiry_none_after_absolute(monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=480, absolute_minutes=1440)
    started = datetime.now(UTC) - timedelta(hours=25)
    assert compute_access_expiry(started_at=started) is None


def test_active_session_works_and_records_auth_time(auth_client: TestClient) -> None:
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    assert token
    payload = _decode_cookie(token)
    assert payload.get("sub")
    assert payload.get("jti")
    assert isinstance(payload.get(AUTH_TIME_CLAIM), (int, float))
    started = datetime.fromtimestamp(float(payload[AUTH_TIME_CLAIM]), tz=UTC)
    assert abs((datetime.now(UTC) - started).total_seconds()) < 30
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL


def test_idle_timeout_expires_session(auth_client: TestClient, monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=2, absolute_minutes=1440)
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    payload = _decode_cookie(token)
    past_idle = datetime.now(UTC) - timedelta(minutes=3)
    _update_session(payload["jti"], last_seen_at=past_idle)
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    assert not _session_cookie_issued(me)


def test_sliding_refresh_works_before_absolute_limit(auth_client: TestClient) -> None:
    login = _login(auth_client)
    assert login.status_code == 200
    current = auth_client.cookies.get(_cookie())
    assert current
    payload = _decode_cookie(current)
    auth_time = payload[AUTH_TIME_CLAIM]
    near_exp = datetime.now(UTC) + timedelta(minutes=1)
    payload["exp"] = near_exp
    settings = get_settings()
    short_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    _set_cookie(auth_client, short_token)
    _update_session(payload["jti"], expires_at=near_exp)

    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    refreshed = _token_from_set_cookie(me)
    assert refreshed
    new_payload = _decode_cookie(refreshed)
    assert new_payload["jti"] == payload["jti"]
    assert new_payload[AUTH_TIME_CLAIM] == auth_time
    new_exp = datetime.fromtimestamp(float(new_payload["exp"]), tz=UTC)
    assert new_exp > near_exp
    absolute_end = datetime.fromtimestamp(float(auth_time), tz=UTC) + timedelta(hours=24)
    assert new_exp <= absolute_end + timedelta(seconds=2)


def test_absolute_lifetime_cannot_be_extended(auth_client: TestClient, monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=5, absolute_minutes=10)
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    payload = _decode_cookie(token)
    started = datetime.now(UTC) - timedelta(minutes=8)
    _update_session(
        payload["jti"],
        created_at=started,
        last_seen_at=datetime.now(UTC),
    )
    payload[AUTH_TIME_CLAIM] = int(started.timestamp())
    near_exp = datetime.now(UTC) + timedelta(minutes=1)
    payload["exp"] = near_exp
    settings = get_settings()
    _set_cookie(
        auth_client,
        jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm),
    )
    _update_session(payload["jti"], expires_at=near_exp)

    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    refreshed = _token_from_set_cookie(me)
    assert refreshed
    new_payload = _decode_cookie(refreshed)
    assert abs(int(new_payload[AUTH_TIME_CLAIM]) - int(started.timestamp())) <= 1
    new_exp = datetime.fromtimestamp(float(new_payload["exp"]), tz=UTC)
    cap = started + timedelta(minutes=10)
    assert new_exp <= cap + timedelta(seconds=2)
    # Uncapped idle refresh would be ~now+5 minutes, past the 10-minute absolute cap.
    assert new_exp < datetime.now(UTC) + timedelta(minutes=4)


def test_absolute_lifetime_rejects_session(auth_client: TestClient, monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=5, absolute_minutes=10)
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    payload = _decode_cookie(token)
    started = datetime.now(UTC) - timedelta(minutes=11)
    _update_session(
        payload["jti"],
        created_at=started,
        last_seen_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    assert not _session_cookie_issued(me)


def test_jwt_auth_time_rejects_past_absolute(auth_client: TestClient, monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=30, absolute_minutes=10)
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    payload = _decode_cookie(token)
    payload[AUTH_TIME_CLAIM] = int((datetime.now(UTC) - timedelta(minutes=11)).timestamp())
    payload["exp"] = datetime.now(UTC) + timedelta(minutes=20)
    settings = get_settings()
    _set_cookie(
        auth_client,
        jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm),
    )
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    assert not _session_cookie_issued(me)


def test_revoked_session_remains_invalid(auth_client: TestClient) -> None:
    login = _login(auth_client)
    assert login.status_code == 200
    token = auth_client.cookies.get(_cookie())
    assert token
    payload = _decode_cookie(token)
    assert auth_client.get("/auth/me").status_code == 200
    logout = auth_client.post("/auth/logout")
    assert logout.status_code == 200
    _set_cookie(auth_client, token)
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    row = _load_session(payload["jti"])
    assert row.revoked_at is not None


def test_mfa_user_must_reauthenticate_after_expiry(auth_client: TestClient, monkeypatch) -> None:
    _set_lifetime(monkeypatch, idle_minutes=30, absolute_minutes=10)
    assert _login(auth_client).status_code == 200
    start = auth_client.post("/auth/mfa/enroll")
    assert start.status_code == 200, start.text
    secret = totp_secret_from_otpauth(start.json()["otpauth_uri"])
    confirmed = auth_client.post(
        "/auth/mfa/enroll/confirm",
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert auth_client.post("/auth/logout").status_code == 200

    password = _login(auth_client)
    assert password.status_code == 200
    body = password.json()
    assert body["mfa_required"] is True
    verified = auth_client.post(
        "/auth/mfa/verify",
        json={
            "challenge_token": body["mfa_challenge_token"],
            "code": pyotp.TOTP(secret).now(),
        },
    )
    assert verified.status_code == 200, verified.text
    assert auth_client.get("/auth/me").status_code == 200

    token = auth_client.cookies.get(_cookie())
    payload = _decode_cookie(token)
    started = datetime.now(UTC) - timedelta(minutes=11)
    _update_session(
        payload["jti"],
        created_at=started,
        last_seen_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=20),
    )
    expired = auth_client.get("/auth/me")
    assert expired.status_code == 401

    again = _login(auth_client)
    assert again.status_code == 200
    again_body = again.json()
    assert again_body["mfa_required"] is True
    assert again_body.get("mfa_challenge_token")
    assert not _session_cookie_issued(again)
    assert auth_client.get("/auth/me").status_code == 401
