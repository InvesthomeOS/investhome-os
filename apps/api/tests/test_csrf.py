"""CSRF protection for cookie-authenticated state-changing requests."""

from uuid import uuid4

from investhome_api.models.lead import LeadStatus
from investhome_api.services.csrf import CSRF_HEADER

DEMO_PASSWORD = "Demo123!"


def _login(client, email: str = "admin@example.com") -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _lead_payload() -> dict:
    return {
        "full_name": "Csrf Lead",
        "email": f"csrf.{uuid4().hex[:8]}@example.com",
        "status": LeadStatus.NEW.value,
    }


def test_authenticated_post_without_csrf_rejected(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    response = auth_client.post("/leads", json=_lead_payload())
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "csrf_rejected"
    assert "CSRF token missing or invalid" in body["error"]["message"]


def test_authenticated_patch_without_csrf_rejected(auth_client) -> None:
    _login(auth_client)
    created = auth_client.post("/leads", json=_lead_payload())
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]
    auth_client.auto_csrf = False
    response = auth_client.patch(f"/leads/{lead_id}", json={"full_name": "No Csrf"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_rejected"


def test_authenticated_delete_without_csrf_rejected(auth_client) -> None:
    _login(auth_client)
    created = auth_client.post("/leads", json=_lead_payload())
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]
    auth_client.auto_csrf = False
    response = auth_client.delete(f"/leads/{lead_id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_rejected"


def test_valid_csrf_token_accepted(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    csrf = auth_client.get("/auth/csrf")
    assert csrf.status_code == 200
    token = csrf.json()["csrf_token"]
    assert token
    response = auth_client.post(
        "/leads",
        json=_lead_payload(),
        headers={CSRF_HEADER: token},
    )
    assert response.status_code == 201, response.text


def test_invalid_csrf_token_rejected(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    response = auth_client.post(
        "/leads",
        json=_lead_payload(),
        headers={CSRF_HEADER: "not-a-valid-csrf-token-value-at-all"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_rejected"


def test_query_string_csrf_token_is_ignored(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    token = auth_client.get("/auth/csrf").json()["csrf_token"]
    response = auth_client.post(
        f"/leads?csrf_token={token}",
        json=_lead_payload(),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_rejected"


def test_get_unauthenticated_shape_unchanged(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    response = auth_client.get("/leads")
    assert response.status_code == 200


def test_login_does_not_require_csrf(auth_client) -> None:
    auth_client.auto_csrf = False
    response = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_bearer_without_cookie_skips_csrf(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    session = auth_client.cookies.get("ih_session")
    assert session
    auth_client.cookies.clear()
    response = auth_client.post(
        "/leads",
        json=_lead_payload(),
        headers={"Authorization": f"Bearer {session}"},
    )
    assert response.status_code == 201, response.text
