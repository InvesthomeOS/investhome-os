"""Staff JWTs without a live auth_sessions jti must not authenticate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.db import session as session_module
from investhome_api.models.security_enterprise import AuthSession
from sqlalchemy import select

DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "admin@example.com"


def _login(client: TestClient, email: str = ADMIN_EMAIL):
    return client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})


def _cookie_name() -> str:
    return get_settings().auth_cookie_name


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _encode(payload: dict) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _set_cookie(client: TestClient, token: str) -> None:
    client.cookies.delete("ih_session")
    client.cookies.set("ih_session", token)


def _session_cookie_issued(response) -> bool:
    raw = [
        value.decode() if isinstance(value, bytes) else value
        for key, value in response.headers.multi_items()
        if key.lower() == "set-cookie"
    ]
    joined = " | ".join(raw).lower()
    if "ih_session=" not in joined:
        return False
    return "max-age=0" not in joined


def _login_payload(client: TestClient) -> tuple[str, dict]:
    assert _login(client).status_code == 200
    token = client.cookies.get(_cookie_name())
    assert token
    return token, _decode(token)


def test_valid_active_jti_accepted(auth_client: TestClient) -> None:
    token, payload = _login_payload(auth_client)
    assert payload.get("jti")
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL
    leads = auth_client.get("/leads")
    assert leads.status_code != 401
    _set_cookie(auth_client, token)
    assert auth_client.get("/auth/me").status_code == 200


def test_missing_jti_rejected(auth_client: TestClient) -> None:
    _token, payload = _login_payload(auth_client)
    payload.pop("jti", None)
    _set_cookie(auth_client, _encode(payload))
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    assert not _session_cookie_issued(me)
    leads = auth_client.get("/leads")
    assert leads.status_code == 401


def test_empty_and_malformed_jti_rejected(auth_client: TestClient) -> None:
    _token, payload = _login_payload(auth_client)
    for bad in ("", "   ", "***", "a" * 80, 123):
        forged = dict(payload)
        forged["jti"] = bad
        _set_cookie(auth_client, _encode(forged))
        me = auth_client.get("/auth/me")
        assert me.status_code == 401, bad
        assert not _session_cookie_issued(me)


def test_unknown_jti_rejected(auth_client: TestClient) -> None:
    _token, payload = _login_payload(auth_client)
    payload["jti"] = uuid4().hex
    _set_cookie(auth_client, _encode(payload))
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    leads = auth_client.get("/leads")
    assert leads.status_code == 401


def test_revoked_jti_rejected(auth_client: TestClient) -> None:
    token, payload = _login_payload(auth_client)
    assert auth_client.get("/auth/me").status_code == 200
    logout = auth_client.post("/auth/logout")
    assert logout.status_code == 200
    _set_cookie(auth_client, token)
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    db = session_module.SessionLocal()
    try:
        row = db.scalar(select(AuthSession).where(AuthSession.token_jti == payload["jti"]))
        assert row is not None
        assert row.revoked_at is not None
    finally:
        db.close()


def test_refresh_cannot_revive_jti_less_token(auth_client: TestClient) -> None:
    _token, payload = _login_payload(auth_client)
    payload.pop("jti", None)
    payload["exp"] = datetime.now(UTC) + timedelta(minutes=1)
    _set_cookie(auth_client, _encode(payload))
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    assert not _session_cookie_issued(me)
    bearer = auth_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {_encode(payload)}"},
    )
    assert bearer.status_code == 401
    assert not _session_cookie_issued(bearer)
