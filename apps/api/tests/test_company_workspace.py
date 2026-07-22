"""Company workspace API tests."""

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_company_dashboard_kpis(client: TestClient) -> None:
    response = client.get("/companies/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "total_companies" in body
    assert "active_companies" in body
    assert "branches" in body
    assert "employees" in body
    assert "departments" in body
    assert "teams" in body
    assert "pending_tasks" in body
    assert body["total_companies"] >= 0


def test_company_recent_activity(client: TestClient) -> None:
    client.get("/company/profile")
    response = client.get("/companies/recent-activity?limit=10")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


def test_company_search(client: TestClient) -> None:
    client.get("/company/profile")
    response = client.get("/companies/search?q=Invest")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "groups" in body
    assert "total" in body
    assert body["query"] == "Invest"


def test_company_dashboard_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/companies/dashboard")
    assert response.status_code == 403


def test_company_search_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/companies/search?q=test")
    assert response.status_code == 403
