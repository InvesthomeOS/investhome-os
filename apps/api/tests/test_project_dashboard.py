"""Sprint 10A2 — Projects portfolio dashboard tests."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from investhome_api.models.project import ProjectStatus


def _create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_code": "PRJ-DASH-001",
        "project_name": "Dashboard Alpha",
        "address": "100 Test Ave",
        "city": "Washington",
        "state": "DC",
        "country": "United States",
        "project_type": "residential",
        "development_type": "ground_up",
        "project_status": ProjectStatus.CONSTRUCTION.value,
        "priority": "high",
        "development_stage": "construction",
        "total_units": 20,
        "residential_units": 20,
        "commercial_units": 0,
        "construction_budget": "1000000.00",
        "total_development_cost": "1500000.00",
        "current_project_value": "1800000.00",
        "projected_revenue": "2200000.00",
        "projected_profit": "400000.00",
        "equity_raised": "500000.00",
        "completion_percentage": "40.00",
        "start_date": (date.today() - timedelta(days=60)).isoformat(),
        "target_completion_date": (date.today() + timedelta(days=90)).isoformat(),
        "description": "Dashboard test project",
    }
    payload.update(overrides)
    return payload


def test_dashboard_aggregates_portfolio(client: TestClient) -> None:
    client.post("/projects", json=_create_payload())
    client.post(
        "/projects",
        json=_create_payload(
            project_code="PRJ-DASH-002",
            project_name="Dashboard Completed",
            project_status=ProjectStatus.COMPLETED.value,
            completion_percentage="100.00",
            target_completion_date=(date.today() - timedelta(days=10)).isoformat(),
        ),
    )

    response = client.get("/projects/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio"]["total_projects"] == 2
    assert body["portfolio"]["under_construction_projects"] == 1
    assert body["portfolio"]["completed_projects"] == 1
    assert body["portfolio"]["total_units"] == 40
    assert body["meta"]["financial_access"] is True
    assert body["financials"] is not None
    assert Decimal(str(body["financials"]["expected_revenue"]["value"])) == Decimal("4400000.00")
    assert body["financials"]["roi"]["available"] is False
    assert "cash-flow" in (body["financials"]["roi"]["reason"] or "").lower()
    assert "status_distribution" in body["portfolio"]
    assert len(body["construction"]["projects"]) >= 1


def test_dashboard_preserves_stats_endpoint(client: TestClient) -> None:
    client.post("/projects", json=_create_payload())
    stats = client.get("/projects/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total"] == 1
    assert body["under_construction"] == 1
    assert "total_development_cost" in body


def test_overdue_milestone_and_alert(client: TestClient) -> None:
    client.post(
        "/projects",
        json=_create_payload(
            project_code="PRJ-DASH-LATE",
            project_name="Late Project",
            target_completion_date=(date.today() - timedelta(days=5)).isoformat(),
            assigned_project_manager=None,
            project_manager_user_id=None,
            completion_percentage=None,
        ),
    )

    milestones = client.get("/projects/upcoming-milestones", params={"days": 30})
    assert milestones.status_code == 200
    assert milestones.json()["total"] >= 1
    assert any(item["is_overdue"] for item in milestones.json()["items"])

    alerts = client.get("/projects/critical-items")
    assert alerts.status_code == 200
    sources = {item["source"] for item in alerts.json()["items"]}
    assert "schedule_overdue" in sources
    assert "missing_manager" in sources or "missing_completion" in sources


def test_dashboard_filters_status(client: TestClient) -> None:
    client.post("/projects", json=_create_payload())
    client.post(
        "/projects",
        json=_create_payload(
            project_code="PRJ-DASH-PIPE",
            project_name="Pipeline Only",
            project_status=ProjectStatus.PIPELINE.value,
        ),
    )
    filtered = client.get("/projects/dashboard", params={"status": "pipeline"})
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["portfolio"]["total_projects"] == 1
    assert body["meta"]["applied_filters"]["status"] == "pipeline"


def test_recent_activity_endpoint(client: TestClient) -> None:
    client.post("/projects", json=_create_payload(project_code="PRJ-DASH-ACT"))
    response = client.get("/projects/recent-activity")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert all("title" in item for item in response.json()["items"])


def test_unavailable_inventory_metrics_are_not_zero(client: TestClient) -> None:
    client.post("/projects", json=_create_payload(project_code="PRJ-DASH-NOINV"))
    body = client.get("/projects/dashboard").json()
    available = body["portfolio"]["available_units"]
    assert available["available"] is False
    assert available["value"] is None
    assert available["reason"]
