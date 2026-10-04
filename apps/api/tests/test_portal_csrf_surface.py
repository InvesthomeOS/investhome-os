"""Portal cookie is not a FastAPI auth/CSRF surface."""

from pathlib import Path
from uuid import uuid4

import investhome_api
from investhome_api.config.settings import get_settings
from investhome_api.models.lead import LeadStatus

DEMO_PASSWORD = "Demo123!"


def _login(client, email: str = "admin@example.com") -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _lead_payload() -> dict:
    return {
        "full_name": "Portal Csrf Surface",
        "email": f"portal.csrf.{uuid4().hex[:8]}@example.com",
        "status": LeadStatus.NEW.value,
    }


def test_staff_csrf_cookie_name_is_not_portal_session() -> None:
    settings = get_settings()
    assert settings.auth_cookie_name == "ih_session"
    assert settings.auth_cookie_name != "ih_portal_session"


def test_api_package_does_not_read_portal_session_cookie() -> None:
    root = Path(investhome_api.__file__).resolve().parent
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ih_portal_session" in text or "PORTAL_SESSION_COOKIE" in text:
            hits.append(str(path))
    assert hits == []


def test_portal_cookie_alone_does_not_trigger_staff_csrf(auth_client) -> None:
    auth_client.auto_csrf = False
    auth_client.cookies.set("ih_portal_session", "forged-portal-cookie")
    response = auth_client.post("/leads", json=_lead_payload())
    assert response.status_code == 401
    body = response.json()
    code = (body.get("error") or {}).get("code")
    assert code != "csrf_rejected"


def test_bearer_with_portal_cookie_skips_csrf(auth_client) -> None:
    auth_client.auto_csrf = False
    _login(auth_client)
    session = auth_client.cookies.get("ih_session")
    assert session
    auth_client.cookies.clear()
    auth_client.cookies.set("ih_portal_session", "not-a-staff-session")
    response = auth_client.post(
        "/leads",
        json=_lead_payload(),
        headers={"Authorization": f"Bearer {session}"},
    )
    assert response.status_code == 201, response.text
