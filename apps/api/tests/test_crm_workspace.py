"""CRM workspace API tests."""

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_crm_dashboard(client: TestClient) -> None:
    response = client.get("/crm/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "recent_contacts" in body
    assert "recent_activities" in body
    assert "upcoming_tasks" in body
    assert "todays_meetings" in body
    assert "recently_updated" in body
    assert "relationship_alerts" in body
    assert "favorite_contacts" in body
    assert "pinned_companies" in body
    assert "communication_summary" in body
    assert isinstance(body["recent_contacts"], list)
    summary = body["communication_summary"]
    assert "total_contacts" in summary
    assert summary["total_contacts"] >= 0


def test_crm_contacts_list(client: TestClient) -> None:
    response = client.get("/crm/contacts?page=1&page_size=10")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert "pages" in body
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["page_size"] == 10


def test_crm_dashboard_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/crm/dashboard")
    assert response.status_code == 403


def test_crm_contacts_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/crm/contacts")
    assert response.status_code == 403
