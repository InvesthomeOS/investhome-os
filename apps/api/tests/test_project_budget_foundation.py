"""Sprint 10A4A — Project budget foundation tests."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_project(client: TestClient, code: str = "PRJ-BUD-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Budget Foundation Project",
            "address": "1 Budget Way",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
            "construction_budget": "1000000.00",
            "total_development_cost": "1500000.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_categories_and_cost_codes_seeded(client: TestClient) -> None:
    categories = client.get("/budget-categories")
    assert categories.status_code == 200
    body = categories.json()
    assert len(body) >= 10
    assert any(item["code"] == "HARD" for item in body)

    codes = client.get("/cost-codes")
    assert codes.status_code == 200
    assert any(item["code"] == "03-000" for item in codes.json())


def test_budget_version_lifecycle_and_lock(client: TestClient) -> None:
    project = _create_project(client)
    project_id = project["id"]

    created = client.post(
        f"/projects/{project_id}/budgets",
        json={"name": "Baseline Budget", "effective_date": date.today().isoformat()},
    )
    assert created.status_code == 201, created.text
    budget = created.json()
    budget_id = budget["id"]
    assert budget["status"] == "draft"
    assert budget["version_number"] == 1

    categories = client.get("/budget-categories").json()
    hard = next(item for item in categories if item["code"] == "HARD")
    codes = client.get("/cost-codes", params={"category_id": hard["id"]}).json()
    cost_code_id = codes[0]["id"] if codes else None

    line = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/lines",
        json={
            "category_id": hard["id"],
            "cost_code_id": cost_code_id,
            "line_number": "1000",
            "name": "Structure",
            "original_budget": "250000.00",
        },
    )
    assert line.status_code == 201, line.text
    assert Decimal(line.json()["current_budget"]) == Decimal("250000.00")
    assert Decimal(line.json()["approved_revisions"]) == Decimal("0")

    submitted = client.post(f"/projects/{project_id}/budgets/{budget_id}/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"

    # Locked while in review
    locked = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/lines",
        json={
            "category_id": hard["id"],
            "line_number": "1001",
            "name": "Should fail",
            "original_budget": "1.00",
        },
    )
    assert locked.status_code == 409

    approved = client.post(f"/projects/{project_id}/budgets/{budget_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["is_current"] is True

    still_locked = client.patch(
        f"/projects/{project_id}/budgets/{budget_id}/lines/{line.json()['id']}",
        json={"original_budget": "300000.00"},
    )
    assert still_locked.status_code == 409


def test_revision_updates_current_not_original(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-REV")
    project_id = project["id"]
    budget_id = client.post(
        f"/projects/{project_id}/budgets", json={"name": "Rev Budget"}
    ).json()["id"]
    hard = next(item for item in client.get("/budget-categories").json() if item["code"] == "HARD")
    line = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/lines",
        json={
            "category_id": hard["id"],
            "line_number": "2000",
            "name": "MEP",
            "original_budget": "100000.00",
        },
    ).json()
    client.post(f"/projects/{project_id}/budgets/{budget_id}/submit")
    client.post(f"/projects/{project_id}/budgets/{budget_id}/approve")

    revision = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/revisions",
        json={
            "title": "MEP uplift",
            "lines": [{"budget_line_id": line["id"], "amount": "15000.00"}],
        },
    )
    assert revision.status_code == 201, revision.text
    revision_id = revision.json()["id"]
    client.post(f"/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/submit")
    approved = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/approve"
    )
    assert approved.status_code == 200

    lines = client.get(f"/projects/{project_id}/budgets/{budget_id}/lines").json()["items"]
    updated = next(item for item in lines if item["id"] == line["id"])
    assert Decimal(updated["original_budget"]) == Decimal("100000.00")
    assert Decimal(updated["approved_revisions"]) == Decimal("15000.00")
    assert Decimal(updated["current_budget"]) == Decimal("115000.00")


def test_clone_and_one_current(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-CLONE")
    project_id = project["id"]
    hard = next(item for item in client.get("/budget-categories").json() if item["code"] == "HARD")
    first = client.post(f"/projects/{project_id}/budgets", json={"name": "V1"}).json()
    client.post(
        f"/projects/{project_id}/budgets/{first['id']}/lines",
        json={
            "category_id": hard["id"],
            "line_number": "1",
            "name": "Line",
            "original_budget": "50000.00",
        },
    )
    client.post(f"/projects/{project_id}/budgets/{first['id']}/submit")
    client.post(f"/projects/{project_id}/budgets/{first['id']}/approve")

    clone = client.post(f"/projects/{project_id}/budgets/{first['id']}/clone")
    assert clone.status_code == 200
    assert clone.json()["status"] == "draft"
    assert clone.json()["version_number"] == 2
    clone_lines = client.get(
        f"/projects/{project_id}/budgets/{clone.json()['id']}/lines"
    ).json()["items"]
    assert len(clone_lines) == 1
    assert Decimal(clone_lines[0]["approved_revisions"]) == Decimal("0")

    client.post(f"/projects/{project_id}/budgets/{clone.json()['id']}/submit")
    client.post(f"/projects/{project_id}/budgets/{clone.json()['id']}/approve")
    versions = client.get(f"/projects/{project_id}/budgets").json()["items"]
    current = [item for item in versions if item["is_current"]]
    assert len(current) == 1
    assert current[0]["id"] == clone.json()["id"]
    superseded = next(item for item in versions if item["id"] == first["id"])
    assert superseded["status"] == "superseded"


def test_budget_summary_unavailable_actuals(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-SUM")
    summary = client.get(f"/projects/{project['id']}/budget-summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["totals"]["actual_cost"]["available"] is False
    assert body["totals"]["committed_cost"]["available"] is False
    assert "Actual cost" in (body["totals"]["actual_cost"]["reason"] or "")


def test_csv_import_transactional(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-CSV")
    project_id = project["id"]
    budget_id = client.post(
        f"/projects/{project_id}/budgets", json={"name": "Import Budget"}
    ).json()["id"]
    csv_text = (
        "category_code,cost_code,line_number,name,original_budget\n"
        "HARD,03-000,0100,Concrete,10000.00\n"
        "HARD,03-000,0100,Duplicate,20000.00\n"
    )
    preview = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/import/preview",
        files={"file": ("budget.csv", csv_text, "text/csv")},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is False
    assert preview.json()["invalid_rows"] >= 1

    good = (
        "category_code,cost_code,line_number,name,original_budget\n"
        "HARD,03-000,0100,Concrete,10000.00\n"
        "SOFT,A-100,0200,Architecture,5000.00\n"
    )
    preview_ok = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/import/preview",
        files={"file": ("budget.csv", good, "text/csv")},
    )
    assert preview_ok.status_code == 200
    assert preview_ok.json()["valid"] is True
    rows = [row["data"] for row in preview_ok.json()["rows"]]
    confirm = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/import/confirm",
        json={"rows": rows},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["imported"] == 2
    lines = client.get(f"/projects/{project_id}/budgets/{budget_id}/lines").json()
    assert lines["total"] == 2


def test_legacy_project_budget_still_works(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-LEG")
    legacy = client.post(
        "/finance/project-budgets",
        json={
            "project_id": project["id"],
            "budget_name": "Legacy Construction",
            "category": "construction",
            "original_budget": "75000.00",
            "currency": "USD",
        },
    )
    assert legacy.status_code == 201, legacy.text
    listed = client.get("/finance/project-budgets", params={"project_id": project["id"]})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    financials = client.get(f"/projects/{project['id']}/financials")
    assert financials.status_code == 200
    assert any(item["budget_name"] == "Legacy Construction" for item in financials.json()["budgets"])


def test_invalid_transition_and_version_uniqueness(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-BUD-TX")
    project_id = project["id"]
    budget = client.post(f"/projects/{project_id}/budgets", json={"name": "Draft Only"}).json()
    reject = client.post(f"/projects/{project_id}/budgets/{budget['id']}/reject")
    assert reject.status_code == 422

    hard = next(item for item in client.get("/budget-categories").json() if item["code"] == "HARD")
    client.post(
        f"/projects/{project_id}/budgets/{budget['id']}/lines",
        json={
            "category_id": hard["id"],
            "line_number": "1",
            "name": "A",
            "original_budget": "10.00",
        },
    )
    client.post(f"/projects/{project_id}/budgets/{budget['id']}/submit")
    client.post(f"/projects/{project_id}/budgets/{budget['id']}/approve")
    approve_again = client.post(f"/projects/{project_id}/budgets/{budget['id']}/approve")
    assert approve_again.status_code == 422
