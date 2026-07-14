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
