"""Operational portfolio totals ignore demo projects unless include_demo is set."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.document import Document
from investhome_api.models.project import Project


def _create_project(
    client: TestClient,
    code: str,
    *,
    demo: bool,
    db: Session,
    portfolio_value: str,
    construction_budget: str,
    completion: str,
) -> str:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": code,
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "current_project_value": portfolio_value,
            "construction_budget": construction_budget,
            "total_development_cost": construction_budget,
            "completion_percentage": completion,
        },
    )
    assert response.status_code == 201, response.text
    project_id = response.json()["id"]
    if demo:
        row = db.get(Project, UUID(project_id))
        assert row is not None
        row.is_demo = True
        db.commit()
    return project_id


def _document(project_id: str, title: str, *, demo: bool, archived: bool = False) -> Document:
    token = uuid4().hex
    row = Document(
        title=title,
        original_file_name=f"{token}.txt",
        stored_file_name=f"{token}.txt",
        file_extension="txt",
        mime_type="text/plain",
        file_size=12,
        storage_key=f"tests/{token}",
        checksum=token[:32],
        project_id=UUID(project_id),
        is_demo=demo,
    )
    if archived:
        row.archived_at = datetime.now(UTC)
    return row


def test_portfolio_excludes_demo_projects_until_requested(client: TestClient, db: Session) -> None:
    real_id = _create_project(
        client,
        "PRJ-PORT-REAL",
        demo=False,
        db=db,
        portfolio_value="1000000.00",
        construction_budget="500000.00",
        completion="40",
    )
    demo_id = _create_project(
        client,
        "PRJ-PORT-DEMO",
        demo=True,
        db=db,
        portfolio_value="9000000.00",
        construction_budget="8000000.00",
        completion="90",
    )

    stats = client.get("/projects/stats")
    assert stats.status_code == 200
    stats_body = stats.json()
    assert stats_body["total"] == 1
    assert stats_body["active"] == 1
    assert Decimal(stats_body["current_portfolio_value"]) == Decimal("1000000.00")
    assert Decimal(stats_body["total_development_cost"]) == Decimal("500000.00")

    listed = client.get("/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == real_id

    dashboard = client.get("/projects/dashboard")
    assert dashboard.status_code == 200
    portfolio = dashboard.json()["portfolio"]
    assert portfolio["total_projects"] == 1
    assert portfolio["active_projects"] == 1
    assert Decimal(str(portfolio["portfolio_value"]["value"])) == Decimal("1000000.00")
    assert Decimal(str(portfolio["construction_budget"]["value"])) == Decimal("500000.00")
    assert Decimal(str(portfolio["average_project_completion"]["value"])) == Decimal("40")

    with_demo = client.get("/projects/stats", params={"include_demo": True})
    assert with_demo.status_code == 200
    assert with_demo.json()["total"] == 2
    assert Decimal(with_demo.json()["current_portfolio_value"]) == Decimal("10000000.00")

    demo_list = client.get("/projects", params={"include_demo": True})
    assert demo_list.status_code == 200
    assert {item["id"] for item in demo_list.json()["items"]} == {real_id, demo_id}

    direct = client.get(f"/projects/{demo_id}")
    assert direct.status_code == 200
    assert direct.json()["project_code"] == "PRJ-PORT-DEMO"


def test_project_documents_keep_real_rows_without_drive(client: TestClient, db: Session) -> None:
    project_id = _create_project(
        client,
        "PRJ-DOCS-REAL",
        demo=False,
        db=db,
        portfolio_value="1000.00",
        construction_budget="1000.00",
        completion="10",
    )
    db.add_all(
        [
            _document(project_id, "Real deed", demo=False),
            _document(project_id, "Demo passport", demo=True),
            _document(project_id, "Archived scan", demo=False, archived=True),
        ]
    )
    db.commit()

    response = client.get(f"/projects/{project_id}/documents")
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Real deed"]
