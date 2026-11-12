"""Internal and customer proforma stay separate and are not double-counted."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    BudgetCategory,
    CommitmentStatus,
    CommitmentType,
    PaymentMethod,
    TransactionStatus,
    TransactionType,
)


def _project(client: TestClient) -> str:
    response = client.post(
        "/projects",
        json={
            "project_code": "PRJ-AUD-001",
            "project_name": "Audience Project",
            "city": "Austin",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
            "construction_budget": "333333.00",
            "projected_revenue": "888888.88",
            "total_development_cost": "444444.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _approve(client: TestClient, project_id: str, budget_id: str) -> None:
    submitted = client.post(f"/projects/{project_id}/budgets/{budget_id}/submit")
    assert submitted.status_code == 200, submitted.text
    approved = client.post(f"/projects/{project_id}/budgets/{budget_id}/approve")
    assert approved.status_code == 200, approved.text


def _line(client: TestClient, project_id: str, budget_id: str, amount: str, unit_cost: str) -> None:
    hard = next(item for item in client.get("/budget-categories").json() if item["code"] == "HARD")
    created = client.post(
        f"/projects/{project_id}/budgets/{budget_id}/lines",
        json={
            "category_id": hard["id"],
            "line_number": amount,
            "name": "Line",
            "original_budget": amount,
            "unit_cost": unit_cost,
        },
    )
    assert created.status_code == 201, created.text


def test_customer_view_hides_internal_cost_and_does_not_double_count(client: TestClient) -> None:
    project_id = _project(client)
    internal = client.post(
        f"/projects/{project_id}/budgets",
        json={"name": "Internal", "audience": "internal"},
    ).json()
    customer = client.post(
        f"/projects/{project_id}/budgets",
        json={"name": "Customer", "audience": "customer"},
    ).json()
    _line(client, project_id, internal["id"], "1000.00", "77.00")
    _line(client, project_id, customer["id"], "5000.00", "25.00")
    _approve(client, project_id, internal["id"])
    _approve(client, project_id, customer["id"])

    versions = client.get(f"/projects/{project_id}/budgets").json()["items"]
    current = [item for item in versions if item["is_current"]]
    assert {item["audience"] for item in current} == {"internal", "customer"}

    legacy = client.post(
        "/finance/project-budgets",
        json={
            "project_id": project_id,
            "budget_name": "Legacy",
            "category": BudgetCategory.CONSTRUCTION.value,
            "original_budget": "400.00",
            "revised_budget": "400.00",
            "paid_amount": "100.00",
            "currency": "USD",
        },
    )
    assert legacy.status_code == 201, legacy.text

    account = client.post(
        "/finance/accounts",
        json={
            "account_name": "Audience Account",
            "account_type": AccountType.OPERATING.value,
            "currency": "USD",
            "status": AccountStatus.ACTIVE.value,
        },
    )
    assert account.status_code == 201, account.text
    movement = client.post(
        "/finance/transactions",
        json={
            "transaction_date": date(2026, 6, 1).isoformat(),
            "transaction_type": TransactionType.EXPENSE.value,
            "amount": "999.00",
            "currency": "USD",
            "description": "Cash movement",
            "account_id": account.json()["id"],
            "project_id": project_id,
            "payment_method": PaymentMethod.WIRE.value,
            "status": TransactionStatus.COMPLETED.value,
        },
    )
    assert movement.status_code == 201, movement.text

    investor = client.post(
        "/investors",
        json={"full_name": "Audience Investor", "investor_type": "individual", "status": "active"},
    )
    assert investor.status_code == 201, investor.text
    commitment = client.post(
        "/finance/funding-commitments",
        json={
            "project_id": project_id,
            "investor_id": investor.json()["id"],
            "commitment_type": CommitmentType.EQUITY.value,
            "committed_amount": "200.00",
            "currency": "USD",
            "status": CommitmentStatus.COMMITTED.value,
        },
    )
    assert commitment.status_code == 201, commitment.text

    internal_view = client.get(f"/projects/{project_id}/financials")
    assert internal_view.status_code == 200, internal_view.text
    summary = internal_view.json()["summary"]
    assert Decimal(str(summary["total_project_cost"]["value"])) == Decimal("1000.00")
    assert Decimal(str(summary["estimated_cost"]["value"])) == Decimal("1000.00")
    assert Decimal(str(summary["actual_cost"]["value"])) == Decimal("100.00")
    assert Decimal(str(summary["remaining_budget"]["value"])) == Decimal("900.00")
    assert Decimal(str(summary["financing"]["value"])) == Decimal("200.00")
    assert Decimal(str(summary["investor_committed_capital"]["value"])) == Decimal("200.00")
    assert Decimal(str(summary["estimated_sales_revenue"]["value"])) == Decimal("888888.88")
    assert Decimal(str(summary["total_project_profit"]["value"])) == Decimal("887888.88")
    assert Decimal(str(summary["project_profitability"]["value"])) == Decimal("887888.88")
    assert summary["investor_contracted_profit"]["available"] is False
    assert summary["investor_total_return"]["available"] is False
    assert summary["investhome_estimated_profit"]["available"] is False
    assert summary["budget_paid"]["available"] is True
    assert "Legacy" in {row["budget_name"] for row in internal_view.json()["budgets"]}

    customer_view = client.get(
        f"/projects/{project_id}/financials", params={"audience": "customer"}
    )
    assert customer_view.status_code == 200, customer_view.text
    body = customer_view.json()
    assert body["audience"] == "customer"
    assert body["budgets"] == []
    assert body["capital"] == []
    published = Decimal(str(body["summary"]["published_budget"]["value"]))
    assert published == Decimal("5000.00")
    assert body["summary"]["investor_contracted_profit"]["available"] is False
    blob = customer_view.text
    for hidden in (
        "construction_budget",
        "actual_cost",
        "total_project_cost",
        "land_cost",
        "unit_cost",
        "888888.88",
        "1000.00",
        "333333",
        "999.00",
        "77.00",
    ):
        assert hidden not in blob

    hidden_version = client.get(
        f"/projects/{project_id}/budgets/{internal['id']}",
        params={"audience": "customer"},
    )
    assert hidden_version.status_code == 404
    hidden_lines = client.get(
        f"/projects/{project_id}/budgets/{internal['id']}/lines",
        params={"audience": "customer"},
    )
    assert hidden_lines.status_code == 404
    customer_lines = client.get(
        f"/projects/{project_id}/budgets/{customer['id']}/lines",
        params={"audience": "customer"},
    )
    assert customer_lines.status_code == 200
    assert customer_lines.json()["items"][0]["unit_cost"] is None
    assert customer_lines.json()["items"][0]["actual_cost"] is None

    customer_list = client.get(
        f"/projects/{project_id}/budgets", params={"audience": "customer"}
    ).json()["items"]
    assert [item["id"] for item in customer_list] == [customer["id"]]
