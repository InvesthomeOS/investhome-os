from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


def _create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_code": "PRJ-TEST-001",
        "project_name": "Test Project",
        "address": "100 Test Ave NW",
        "city": "Washington",
        "state": "DC",
        "postal_code": "20001",
        "country": "United States",
        "project_type": ProjectType.RESIDENTIAL.value,
        "development_type": DevelopmentType.GROUND_UP.value,
        "project_status": ProjectStatus.PIPELINE.value,
        "ownership_entity": "Test Holdings LLC",
        "total_units": 24,
        "residential_units": 24,
        "commercial_units": 0,
        "gross_square_feet": 32000,
        "acquisition_price": "5000000.00",
        "total_development_cost": "15000000.00",
        "current_project_value": "16000000.00",
        "projected_sale_value": "18000000.00",
        "equity_required": "4500000.00",
        "equity_raised": "2000000.00",
        "debt_amount": "10500000.00",
        "loan_to_cost": "70.0000",
        "projected_revenue": "18000000.00",
        "projected_profit": "3000000.00",
        "projected_roi": "20.0000",
        "projected_irr": "18.5000",
        "start_date": date(2026, 1, 1).isoformat(),
        "target_completion_date": date(2028, 6, 30).isoformat(),
        "assigned_project_manager": "Sarah Chen",
        "description": "Integration test project",
        "notes": "Created in test suite",
    }
    payload.update(overrides)
    return payload


def test_projects_crud_flow(client: TestClient) -> None:
    create_response = client.post("/projects", json=_create_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    project_id = created["id"]
    assert created["project_name"] == "Test Project"
    assert created["project_status"] == ProjectStatus.PIPELINE.value
    assert created["slug"]
    assert created["priority"] == "medium"
    assert created["currency"] == "USD"

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["page"] == 1

    get_response = client.get(f"/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["project_code"] == "PRJ-TEST-001"

    # Valid transition path: pipeline -> pre_development -> construction
    update_response = client.patch(
        f"/projects/{project_id}",
        json={
            "project_status": ProjectStatus.PRE_DEVELOPMENT.value,
            "notes": "Updated in test",
            "completion_percentage": "15.00",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["project_status"] == ProjectStatus.PRE_DEVELOPMENT.value

    status_response = client.post(
        f"/projects/{project_id}/status",
        json={"status": ProjectStatus.CONSTRUCTION.value},
    )
    assert status_response.status_code == 200
    assert status_response.json()["project_status"] == ProjectStatus.CONSTRUCTION.value

    archive_response = client.delete(f"/projects/{project_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    hidden_response = client.get("/projects")
    assert hidden_response.json()["total"] == 0

    archived_list_response = client.get("/projects?include_archived=true")
    assert archived_list_response.json()["total"] == 1

    restore_response = client.post(f"/projects/{project_id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["archived_at"] is None
    assert client.get("/projects").json()["total"] == 1


def test_projects_filters_pagination_and_sorting(client: TestClient) -> None:
    client.post(
        "/projects",
        json=_create_payload(project_code="PRJ-A-001", project_name="Alpha Project"),
    )
    client.post(
        "/projects",
        json=_create_payload(
            project_code="PRJ-B-002",
            project_name="Beta Project",
            city="Arlington",
            state="VA",
            project_type=ProjectType.COMMERCIAL.value,
            development_type=DevelopmentType.RENOVATION.value,
            project_status=ProjectStatus.CONSTRUCTION.value,
            priority="high",
            development_stage="construction",
            assigned_project_manager="Marcus Webb",
        ),
    )

    filtered = client.get("/projects", params={"city": "Arlington"})
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["project_name"] == "Beta Project"

    searched = client.get("/projects", params={"search": "Alpha"})
    assert searched.json()["total"] == 1

    status_filtered = client.get(
        "/projects",
        params={"status": ProjectStatus.CONSTRUCTION.value},
    )
    assert status_filtered.json()["total"] == 1

    manager_filtered = client.get(
        "/projects",
        params={"assigned_project_manager": "Marcus"},
    )
    assert manager_filtered.json()["total"] == 1

    priority_filtered = client.get("/projects", params={"priority": "high"})
    assert priority_filtered.json()["total"] == 1

    stage_filtered = client.get("/projects", params={"development_stage": "construction"})
    assert stage_filtered.json()["total"] == 1

    state_filtered = client.get("/projects", params={"state": "VA"})
    assert state_filtered.json()["total"] == 1

    paged = client.get(
        "/projects",
        params={"page": 1, "page_size": 1, "sort_by": "project_name"},
    )
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1
    assert paged.json()["pages"] == 2


def test_project_stats(client: TestClient) -> None:
    client.post(
        "/projects",
        json=_create_payload(
            project_status=ProjectStatus.CONSTRUCTION.value,
            total_development_cost="20000000.00",
            current_project_value="22000000.00",
            equity_raised="5000000.00",
            total_units=30,
            residential_units=30,
            commercial_units=0,
        ),
    )
    client.post(
        "/projects",
        json=_create_payload(
            project_code="PRJ-STAT-002",
            project_name="Completed One",
            project_status=ProjectStatus.COMPLETED.value,
            total_development_cost="10000000.00",
            current_project_value="12000000.00",
            equity_raised="3000000.00",
            total_units=10,
            residential_units=10,
            commercial_units=0,
        ),
    )

    stats = client.get("/projects/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total"] == 2
    assert body["active"] == 1
    assert body["under_construction"] == 1
    assert body["completed"] == 1
    assert body["units_under_development"] == 30
    assert body["total_units"] == 40
    assert Decimal(body["total_development_cost"]) == Decimal("30000000.00")
    assert Decimal(body["current_portfolio_value"]) == Decimal("34000000.00")
    assert Decimal(body["equity_raised"]) == Decimal("8000000.00")


def test_get_missing_project_returns_404(client: TestClient) -> None:
    response = client.get(f"/projects/{UUID('00000000-0000-0000-0000-000000000003')}")
    assert response.status_code == 404


def test_invalid_status_transition_blocked(client: TestClient) -> None:
    created = client.post("/projects", json=_create_payload()).json()
    project_id = created["id"]

    response = client.post(
        f"/projects/{project_id}/status",
        json={"status": ProjectStatus.COMPLETED.value},
    )
    assert response.status_code == 409

    patch_response = client.patch(
        f"/projects/{project_id}",
        json={"project_status": ProjectStatus.COMPLETED.value},
    )
    assert patch_response.status_code == 409


def test_archived_project_cannot_be_edited(client: TestClient) -> None:
    created = client.post("/projects", json=_create_payload()).json()
    project_id = created["id"]
    client.delete(f"/projects/{project_id}")

    response = client.patch(
        f"/projects/{project_id}",
        json={"notes": "should fail"},
    )
    assert response.status_code == 404

    archived = client.get(f"/projects/{project_id}")
    assert archived.status_code == 404


def test_unique_project_code(client: TestClient) -> None:
    assert client.post("/projects", json=_create_payload()).status_code == 201
    duplicate = client.post("/projects", json=_create_payload())
    assert duplicate.status_code == 409


def test_project_team_assignment(client: TestClient) -> None:
    created = client.post("/projects", json=_create_payload()).json()
    project_id = created["id"]
    user_id = "00000000-0000-0000-0000-000000000001"

    add = client.post(
        f"/projects/{project_id}/team",
        json={
            "user_id": user_id,
            "role": "project_manager",
            "is_primary": True,
        },
    )
    assert add.status_code == 201
    member = add.json()
    assert member["role"] == "project_manager"
    assert member["is_primary"] is True

    team = client.get(f"/projects/{project_id}/team")
    assert team.status_code == 200
    assert team.json()["total"] == 1

    duplicate = client.post(
        f"/projects/{project_id}/team",
        json={"user_id": user_id, "role": "project_manager", "is_primary": True},
    )
    assert duplicate.status_code == 409

    remove = client.delete(f"/projects/{project_id}/team/{member['id']}")
    assert remove.status_code == 204
    assert client.get(f"/projects/{project_id}/team").json()["total"] == 0
