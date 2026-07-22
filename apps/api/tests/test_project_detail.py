"""Sprint 10A3 — Project detail workspace tests."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from investhome_api.models.project import ProjectStatus


def _create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_code": "PRJ-DET-001",
        "project_name": "Detail Alpha",
        "address": "200 Detail Ave",
        "city": "Austin",
        "state": "TX",
        "country": "United States",
        "project_type": "residential",
        "development_type": "ground_up",
        "project_status": ProjectStatus.CONSTRUCTION.value,
        "priority": "high",
        "development_stage": "construction",
        "total_units": 12,
        "residential_units": 12,
        "commercial_units": 0,
        "construction_budget": "900000.00",
        "total_development_cost": "1200000.00",
        "current_project_value": "1400000.00",
        "projected_revenue": "1800000.00",
        "projected_profit": "300000.00",
        "completion_percentage": "35.00",
        "start_date": (date.today() - timedelta(days=40)).isoformat(),
        "target_completion_date": (date.today() + timedelta(days=120)).isoformat(),
        "description": "Detail workspace test project",
    }
    payload.update(overrides)
    return payload


def _create_project(client: TestClient, **overrides: object) -> dict:
    response = client.post("/projects", json=_create_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_detail_shell_and_overview(client: TestClient) -> None:
    project = _create_project(client)
    project_id = project["id"]

    shell = client.get(f"/projects/{project_id}/detail")
    assert shell.status_code == 200
    body = shell.json()
    assert body["project"]["id"] == project_id
    assert body["financial_access"] is True
    assert body["permissions"]["can_view_financial"] is True
    nav_keys = {item["key"] for item in body["navigation"] if item["visible"]}
    assert "overview" in nav_keys
    assert "financials" in nav_keys

    overview = client.get(f"/projects/{project_id}/overview")
    assert overview.status_code == 200
    ov = overview.json()
    assert ov["shell"]["project"]["project_name"] == "Detail Alpha"
    assert ov["financial_snapshot"] is not None
    assert Decimal(str(ov["financial_snapshot"]["expected_revenue"]["value"])) == Decimal(
        "1800000.00"
    )
    assert ov["snapshot"]["city"] == "Austin"
    assert "milestones" in ov
    assert "alerts" in ov


def test_financials_tab_and_unavailable_metrics(client: TestClient) -> None:
    project = _create_project(client)
    response = client.get(f"/projects/{project['id']}/financials")
    assert response.status_code == 200
    body = response.json()
    assert body["financial_access"] is True
    assert body["summary"]["roi"]["available"] is False
    assert body["summary"]["irr"]["available"] is False
    assert body["summary"]["total_development_budget"]["available"] is True
    assert Decimal(str(body["summary"]["total_development_budget"]["value"])) == Decimal(
        "1200000.00"
    )


def test_schedule_construction_units_sales_leasing(client: TestClient) -> None:
    project = _create_project(client)
    project_id = project["id"]

    schedule = client.get(f"/projects/{project_id}/schedule")
    assert schedule.status_code == 200
    sched = schedule.json()
    assert sched["is_delayed"] is False
    assert sched["key_dates"]["estimated_completion"] is not None
    assert isinstance(sched["milestones"], list)

    construction = client.get(f"/projects/{project_id}/construction")
    assert construction.status_code == 200
    assert construction.json()["status"] == ProjectStatus.CONSTRUCTION.value
    assert len(construction.json()["warnings"]) >= 1

    units = client.get(f"/projects/{project_id}/units")
    assert units.status_code == 200
    assert units.json()["summary"]["total_units"]["value"] == 0
    assert units.json()["summary"]["available"]["available"] is False

    sales = client.get(f"/projects/{project_id}/sales")
    assert sales.status_code == 200
    assert sales.json()["summary"]["linked_opportunities"]["value"] == 0

    leasing = client.get(f"/projects/{project_id}/leasing")
    assert leasing.status_code == 200
    assert "Lease contract data is not available" in leasing.json()["warnings"][0]


def test_investors_documents_activity_alerts_milestones(client: TestClient) -> None:
    project = _create_project(client)
    project_id = project["id"]

    investors = client.get(f"/projects/{project_id}/investors")
    assert investors.status_code == 200
    assert investors.json()["total"] == 0

    documents = client.get(f"/projects/{project_id}/documents")
    assert documents.status_code == 200
    assert documents.json()["total"] == 0

    activity = client.get(f"/projects/{project_id}/activity")
    assert activity.status_code == 200
    assert activity.json()["total"] >= 1

    alerts = client.get(f"/projects/{project_id}/alerts")
    assert alerts.status_code == 200
    assert isinstance(alerts.json()["items"], list)

    milestones = client.get(f"/projects/{project_id}/milestones")
    assert milestones.status_code == 200
    assert milestones.json()["total"] >= 1


def test_directory_users_requires_team_permission(client: TestClient) -> None:
    project = _create_project(client)
    response = client.get(f"/projects/{project['id']}/directory-users?search=a")
    assert response.status_code == 200
    assert "items" in response.json()


def test_not_found_detail(client: TestClient) -> None:
    missing = "00000000-0000-4000-8000-000000000099"
    response = client.get(f"/projects/{missing}/detail")
    assert response.status_code == 404


def test_archived_project_detail_accessible(client: TestClient) -> None:
    project = _create_project(client, project_code="PRJ-DET-ARCH")
    project_id = project["id"]
    archived = client.delete(f"/projects/{project_id}")
    assert archived.status_code == 200

    detail = client.get(f"/projects/{project_id}/detail")
    assert detail.status_code == 200
    assert detail.json()["project"]["archived_at"] is not None


def test_portfolio_dashboard_still_works(client: TestClient) -> None:
    _create_project(client, project_code="PRJ-DET-REG")
    response = client.get("/projects/dashboard")
    assert response.status_code == 200
    assert response.json()["portfolio"]["total_projects"] >= 1
