"""Sprint 10A4C — Executive finance summary, health, cash-flow, funding gap."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_project(client: TestClient, code: str = "PRJ-EXEC-001", **extra) -> dict:
    payload = {
        "project_code": code,
        "project_name": "Executive Finance Project",
        "address": "10 Executive Way",
        "city": "Austin",
        "state": "TX",
        "country": "United States",
        "project_type": "residential",
        "development_type": "ground_up",
        "project_status": "construction",
        "currency": "USD",
        "projected_revenue": "5000000.00",
        "projected_profit": "800000.00",
        "total_development_cost": "4200000.00",
        "construction_budget": "3500000.00",
        "equity_required": "2000000.00",
        "equity_raised": "1200000.00",
        **extra,
    }
    response = client.post("/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_investor(client: TestClient, code: str = "INV-EXEC-001") -> dict:
    response = client.post(
        "/investors",
        json={
            "full_name": f"Executive Investor {code}",
            "investor_type": "individual",
            "status": "active",
            "email": f"{code.lower()}@example.com",
            "country": "United States",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_executive_finance_summary_and_funding_gap(client: TestClient) -> None:
    project = _create_project(client)
    project_id = project["id"]

    response = client.get(f"/projects/{project_id}/executive-finance")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["project_id"] == project_id
    assert body["expected_revenue"]["available"] is True
    assert Decimal(body["expected_revenue"]["value"]) == Decimal("5000000.00")
    assert body["expected_profit"]["available"] is True
    assert Decimal(body["expected_profit"]["value"]) == Decimal("800000.00")
    assert body["forecast_cost"]["available"] is True
    assert body["funding_gap"]["available"] is True
    assert Decimal(body["funding_gap"]["value"]) == Decimal("800000.00")
    assert body["profit_margin"]["available"] is True
    assert body["health"] in {"healthy", "watch", "at_risk", "critical", "unavailable"}
    assert "ai_summary" in body
    assert body["ai_summary"]["project_id"] == project_id
    assert "needs_cash" in body["ai_summary"]
    assert "missing_info" in body["ai_summary"]


def test_executive_finance_health_negative_profit(client: TestClient) -> None:
    project = _create_project(
        client,
        code="PRJ-EXEC-NEG",
        projected_revenue="1000000.00",
        projected_profit="-250000.00",
        equity_required="500000.00",
        equity_raised="500000.00",
    )
    response = client.get(f"/projects/{project['id']}/executive-finance")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["health"] == "critical"
    assert any(alert["code"] == "negative_projected_profit" for alert in body["alerts"])


def test_cash_flow_summary_30_60_90(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-EXEC-CF")
    project_id = project["id"]
    today = date.today()

    obligation = client.post(
        "/finance/payment-obligations",
        json={
            "project_id": project_id,
            "obligation_type": "vendor_payment",
            "payee": "General Contractor",
            "description": "Progress payment",
            "amount": "75000.00",
            "currency": "USD",
            "due_date": (today + timedelta(days=20)).isoformat(),
            "status": "upcoming",
            "priority": "high",
        },
    )
    assert obligation.status_code == 201, obligation.text

    investor = _create_investor(client)
    commitment = client.post(
        "/finance/funding-commitments",
        json={
            "project_id": project_id,
            "investor_id": investor["id"],
            "commitment_type": "equity",
            "committed_amount": "500000.00",
            "funded_amount": "100000.00",
            "remaining_amount": "400000.00",
            "currency": "USD",
            "commitment_date": today.isoformat(),
            "target_funding_date": (today + timedelta(days=45)).isoformat(),
            "status": "partially_funded",
        },
    )
    assert commitment.status_code == 201, commitment.text

    response = client.get(f"/projects/{project_id}/cash-flow-summary")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["horizon_30"]["days"] == 30
    assert body["horizon_60"]["days"] == 60
    assert body["horizon_90"]["days"] == 90
    assert body["horizon_30"]["outflows"]["available"] is True
    assert Decimal(body["horizon_30"]["outflows"]["value"]) >= Decimal("75000.00")
    assert body["horizon_60"]["inflows"]["available"] is True
    assert Decimal(body["horizon_60"]["inflows"]["value"]) >= Decimal("400000.00")
    assert body["horizon_30"]["net_need"]["available"] is True

    executive = client.get(f"/projects/{project_id}/executive-finance")
    assert executive.status_code == 200
    exec_body = executive.json()
    assert exec_body["need_30_days"]["available"] is True
    assert exec_body["need_60_days"]["available"] is True
    assert exec_body["need_90_days"]["available"] is True


def test_executive_finance_unavailable_without_assumptions(client: TestClient) -> None:
    project = _create_project(
        client,
        code="PRJ-EXEC-EMPTY",
        projected_revenue=None,
        projected_profit=None,
        total_development_cost=None,
        construction_budget=None,
        equity_required=None,
        equity_raised=None,
    )
    # Explicit nulls may be omitted by JSON — patch after create if needed
    patched = client.patch(
        f"/projects/{project['id']}",
        json={
            "projected_revenue": None,
            "projected_profit": None,
            "total_development_cost": None,
            "construction_budget": None,
            "equity_required": None,
            "equity_raised": None,
        },
    )
    assert patched.status_code == 200, patched.text

    response = client.get(f"/projects/{project['id']}/executive-finance")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["expected_revenue"]["available"] is False
    assert body["expected_profit"]["available"] is False
    assert body["funding_gap"]["available"] is False
    assert body["health"] in {"watch", "unavailable", "at_risk"}
    assert any(alert["code"] == "missing_assumptions" for alert in body["alerts"])


def test_existing_financials_endpoint_preserved(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-EXEC-PRESERVE")
    response = client.get(f"/projects/{project['id']}/financials")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["financial_access"] is True
    assert "summary" in body
    assert "budgets" in body
    assert "capital" in body


def test_budget_summary_still_works_with_executive_finance(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-EXEC-BUD")
    project_id = project["id"]

    created = client.post(
        f"/projects/{project_id}/budgets",
        json={"name": "Baseline", "effective_date": date.today().isoformat()},
    )
    assert created.status_code == 201, created.text
    budget_id = created.json()["id"]

    categories = client.get("/budget-categories").json()
    hard = next(item for item in categories if item["code"] == "HARD")
    line = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/lines",
        json={
            "category_id": hard["id"],
            "line_number": "1000",
            "name": "Structure",
            "original_budget": "250000.00",
        },
    )
    assert line.status_code == 201, line.text
    assert client.post(f"/projects/{project_id}/budgets/{budget_id}/submit").status_code == 200
    assert client.post(f"/projects/{project_id}/budgets/{budget_id}/approve").status_code == 200

    summary = client.get(f"/projects/{project_id}/budget-summary")
    assert summary.status_code == 200, summary.text
    totals = summary.json()["totals"]
    assert totals["current_budget"]["available"] is True
    assert Decimal(totals["current_budget"]["value"]) == Decimal("250000.00")

    executive = client.get(f"/projects/{project_id}/executive-finance")
    assert executive.status_code == 200
    assert executive.json()["forecast_cost"]["available"] is True
