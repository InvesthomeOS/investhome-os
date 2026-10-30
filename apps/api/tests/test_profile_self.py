"""Self-service profile updates."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import User

DEMO_PASSWORD = "Demo123!"
SALES_EMAIL = "sales@example.com"
ADMIN_EMAIL = "admin@example.com"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _user(db: Session, email: str) -> User:
    db.expire_all()
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def test_profile_name_language_and_timezone_update(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, SALES_EMAIL)
    admin_before = _user(db, ADMIN_EMAIL)
    admin_name = admin_before.full_name
    admin_id = admin_before.id

    me = auth_client.get("/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == SALES_EMAIL
    assert "Emin" not in me.json()["full_name"]

    renamed = auth_client.patch("/auth/me", json={"first_name": "Hasan", "last_name": "Yılmaz"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["full_name"] == "Hasan Yılmaz"
    assert renamed.json()["email"] == SALES_EMAIL

    language = auth_client.patch("/auth/me", json={"preferred_language": "en"})
    assert language.status_code == 200, language.text
    assert language.json()["preferred_language"] == "en"
    assert language.json()["full_name"] == "Hasan Yılmaz"

    timezone = auth_client.patch("/auth/me", json={"timezone": "Europe/Istanbul"})
    assert timezone.status_code == 200, timezone.text
    assert timezone.json()["timezone"] == "Europe/Istanbul"
    assert timezone.json()["preferred_language"] == "en"

    stored = _user(db, SALES_EMAIL)
    assert stored.full_name == "Hasan Yılmaz"
    assert stored.preferred_language == "en"
    assert stored.timezone == "Europe/Istanbul"
    assert _user(db, ADMIN_EMAIL).full_name == admin_name

    other = auth_client.patch(f"/users/{admin_id}", json={"full_name": "Taken Over"})
    assert other.status_code == 403, other.text
    assert _user(db, ADMIN_EMAIL).full_name == admin_name


def test_profile_rejects_role_permissions_email_and_blank_name(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, SALES_EMAIL)
    before = auth_client.get("/auth/me").json()

    for payload in (
        {"role": "super_admin"},
        {"roles": ["super_admin"]},
        {"permissions": ["*:*"]},
        {"email": "other@investhome.com"},
        {"status": "inactive"},
        {"department": "Administration"},
        {"is_demo": True},
    ):
        rejected = auth_client.patch("/auth/me", json=payload)
        assert rejected.status_code == 422, rejected.text

    invalid_zone = auth_client.patch("/auth/me", json={"timezone": "Not/AZone"})
    assert invalid_zone.status_code == 400, invalid_zone.text

    blank = auth_client.patch("/auth/me", json={"first_name": " ", "last_name": " "})
    assert blank.status_code == 400, blank.text

    after = auth_client.get("/auth/me").json()
    assert after["email"] == before["email"]
    assert after["full_name"] == before["full_name"]
    assert after["roles"] == before["roles"]
    assert after["permissions"] == before["permissions"]
    assert _user(db, SALES_EMAIL).email == SALES_EMAIL


def test_password_and_mfa_profile_routes_remain(auth_client: TestClient) -> None:
    _login(auth_client, SALES_EMAIL)
    password = auth_client.post(
        "/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "another-valid-password"},
    )
    assert password.status_code == 400, password.text
    spec = auth_client.get("/openapi.json")
    assert spec.status_code == 200, spec.text
    paths = spec.json()["paths"]
    assert "/auth/mfa/enroll" in paths
    assert "/auth/mfa/enroll/confirm" in paths
    assert "patch" in paths["/auth/me"]
