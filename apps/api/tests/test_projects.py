from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from investhome_api.db.base import Base
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


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

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["page"] == 1

    get_response = client.get(f"/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["project_code"] == "PRJ-TEST-001"

    update_response = client.patch(
        f"/projects/{project_id}",
        json={"project_status": ProjectStatus.CONSTRUCTION.value, "notes": "Updated in test"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["project_status"] == ProjectStatus.CONSTRUCTION.value

    archive_response = client.delete(f"/projects/{project_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    hidden_response = client.get("/projects")
    assert hidden_response.json()["total"] == 0

    archived_list_response = client.get("/projects?include_archived=true")
    assert archived_list_response.json()["total"] == 1


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
            project_type=ProjectType.COMMERCIAL.value,
            development_type=DevelopmentType.RENOVATION.value,
            project_status=ProjectStatus.CONSTRUCTION.value,
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
    assert body["units_under_development"] == 30
    assert Decimal(body["total_development_cost"]) == Decimal("30000000.00")
    assert Decimal(body["current_portfolio_value"]) == Decimal("34000000.00")
    assert Decimal(body["equity_raised"]) == Decimal("8000000.00")


def test_get_missing_project_returns_404(client: TestClient) -> None:
    response = client.get(f"/projects/{UUID('00000000-0000-0000-0000-000000000003')}")
    assert response.status_code == 404
