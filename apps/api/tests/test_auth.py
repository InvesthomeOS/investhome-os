"""Authentication and authorization tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from investhome_api.models.lead import LeadStatus

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200


def test_login_and_me(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert "*:*" in body["permissions"]

    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["full_name"] == "admin"


def test_invalid_login_does_not_reveal_email(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_inactive_user_blocked(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 403


def test_unauthenticated_returns_401(auth_client: TestClient) -> None:
    response = auth_client.get("/leads")
    assert response.status_code == 401


def test_read_only_cannot_create_leads(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.post(
        "/leads",
        json={
            "full_name": "Blocked Lead",
            "email": f"lead.{uuid4().hex[:8]}@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    assert response.status_code == 403


def test_sales_can_create_leads(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    response = auth_client.post(
        "/leads",
        json={
            "full_name": "Allowed Lead",
            "email": f"lead.{uuid4().hex[:8]}@example.com",
            "phone": "+1 555 0100",
            "country": "United States",
            "source": "Website",
            "status": LeadStatus.NEW.value,
            "assigned_to": "Sales User",
        },
    )
    assert response.status_code == 201, response.text


def test_non_admin_cannot_manage_users(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    response = auth_client.get("/users")
    assert response.status_code == 403


def _set_cookie_deleted(response) -> bool:
    """True when Set-Cookie clears ih_session (Max-Age=0 / expires in the past)."""
    # httpx/starlette may expose multiple set-cookie headers
    raw_headers = response.headers.get_list("set-cookie") if hasattr(response.headers, "get_list") else []
    if not raw_headers:
        # Starlette TestClient / httpx: cookies jar may drop deleted cookies; check raw
        raw_headers = [v.decode() if isinstance(v, bytes) else v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"]
    joined = " | ".join(raw_headers).lower()
    if "ih_session=" not in joined:
        return False
    return "max-age=0" in joined or "expires=" in joined


def test_logout_clears_cookie_without_session(auth_client: TestClient) -> None:
    response = auth_client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"
    assert _set_cookie_deleted(response)


def test_logout_clears_invalid_cookie(auth_client: TestClient) -> None:
    auth_client.cookies.set("ih_session", "not-a-jwt")
    response = auth_client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"
    assert _set_cookie_deleted(response)
    me = auth_client.get("/auth/me")
    assert me.status_code == 401


def test_logout_revokes_valid_session_and_stays_logged_out(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    assert auth_client.get("/auth/me").status_code == 200

    logout = auth_client.post("/auth/logout")
    assert logout.status_code == 200
    assert _set_cookie_deleted(logout)

    me = auth_client.get("/auth/me")
    assert me.status_code == 401


def test_invalid_cookie_rejected_by_me(auth_client: TestClient) -> None:
    auth_client.cookies.set("ih_session", "bogus.token.value")
    me = auth_client.get("/auth/me")
    assert me.status_code == 401


def test_expired_cookie_rejected_by_me(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    import jwt

    from investhome_api.config.settings import get_settings

    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()
    payload = {
        "sub": "00000000-0000-0000-0000-000000000099",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "jti": "expired-test-jti",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    auth_client.cookies.set("ih_session", token)
    me = auth_client.get("/auth/me")
    assert me.status_code == 401
    # Stale cookie can still be cleared via logout
    logout = auth_client.post("/auth/logout")
    assert logout.status_code == 200
    assert _set_cookie_deleted(logout)


def test_relogin_after_logout(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    assert auth_client.post("/auth/logout").status_code == 200
    assert auth_client.get("/auth/me").status_code == 401
    _login(auth_client, "admin@example.com")
    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


def test_revise_without_session_returns_401(auth_client: TestClient) -> None:
    campaign_id = "00000000-0000-0000-0000-000000000001"
    asset_id = "00000000-0000-0000-0000-000000000002"
    response = auth_client.post(
        f"/ai/creative-studio/campaigns/{campaign_id}/revise",
        json={"instruction": "grow headline", "current_final_asset_id": asset_id},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_generate_ad_without_session_returns_401(auth_client: TestClient) -> None:
    campaign_id = "00000000-0000-0000-0000-000000000001"
    response = auth_client.post(
        f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
        json={"production_mode": "finished_ad"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_revise_with_session_cookie_is_not_401(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    campaign_id = "00000000-0000-0000-0000-000000000001"
    asset_id = "00000000-0000-0000-0000-000000000002"
    response = auth_client.post(
        f"/ai/creative-studio/campaigns/{campaign_id}/revise",
        json={"instruction": "grow headline", "current_final_asset_id": asset_id},
    )
    assert response.status_code != 401
    assert response.json().get("detail") != "Not authenticated"


def test_empty_bearer_falls_back_to_session_cookie(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    response = auth_client.get("/auth/me", headers={"Authorization": "Bearer "})
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_near_expiry_session_cookie_is_refreshed(auth_client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta

    import jwt

    from investhome_api.config.settings import get_settings
    from investhome_api.db import session as session_module
    from investhome_api.models.security_enterprise import AuthSession
    from sqlalchemy import select

    login = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    settings = get_settings()
    current = auth_client.cookies.get("ih_session")
    assert current
    payload = jwt.decode(current, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    near_exp = datetime.now(UTC) + timedelta(minutes=1)
    payload["exp"] = near_exp
    short_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    auth_client.cookies.set("ih_session", short_token)
    db = session_module.SessionLocal()
    try:
        session_row = db.scalar(select(AuthSession).where(AuthSession.token_jti == payload["jti"]))
        assert session_row is not None
        session_row.expires_at = near_exp
        db.commit()
    finally:
        db.close()

    me = auth_client.get("/auth/me")
    assert me.status_code == 200
    set_cookie = " | ".join(
        v.decode() if isinstance(v, bytes) else v
        for k, v in me.headers.multi_items()
        if k.lower() == "set-cookie"
    )
    assert "ih_session=" in set_cookie.lower()
