"""Investor contracted profit stays out of project cost and out of the customer view."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.finance import CommitmentStatus, CommitmentType


def _project(client: TestClient, code: str) -> str:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Investor Profit Project",
            "city": "Austin",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
            "projected_revenue": "10000.00",
            "total_development_cost": "4000.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _investor(client: TestClient, name: str) -> str:
    response = client.post(
        "/investors",
        json={"full_name": name, "investor_type": "individual", "status": "active"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _commitment(
    client: TestClient,
    project_id: str,
    investor_id: str,
    capital: str,
    *,
    profit: str | None,
    status: str = CommitmentStatus.COMMITTED.value,
) -> dict:
    payload: dict[str, object] = {
        "project_id": project_id,
        "investor_id": investor_id,
        "commitment_type": CommitmentType.EQUITY.value,
        "committed_amount": capital,
        "currency": "USD",
        "status": status,
    }
    if profit is not None:
        payload["contracted_profit"] = profit
    response = client.post("/finance/funding-commitments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _summary(client: TestClient, project_id: str, audience: str | None = None) -> dict:
    params = {"audience": audience} if audience else None
    response = client.get(f"/projects/{project_id}/financials", params=params)
    assert response.status_code == 200, response.text
    return response.json()["summary"]


def _money(summary: dict, key: str) -> Decimal:
    assert summary[key]["available"] is True, summary[key]
    return Decimal(str(summary[key]["value"]))


def test_one_investor_profit_is_not_a_second_cost(client: TestClient) -> None:
    project_id = _project(client, "PRJ-PRF-ONE")
    investor_id = _investor(client, "One Investor")
    created = _commitment(client, project_id, investor_id, "1000.00", profit="250.00")
    assert created["currency"] == "USD"
    assert Decimal(created["contracted_profit"]) == Decimal("250.00")

    summary = _summary(client, project_id)
    assert _money(summary, "total_project_cost") == Decimal("4000.00")
    assert _money(summary, "total_project_profit") == Decimal("6000.00")
    assert _money(summary, "investor_committed_capital") == Decimal("1000.00")
    assert _money(summary, "investor_contracted_profit") == Decimal("250.00")
    assert _money(summary, "investor_total_return") == Decimal("1250.00")
    assert _money(summary, "investhome_estimated_profit") == Decimal("5750.00")


def test_multiple_investors_sum_on_the_project(client: TestClient) -> None:
    project_id = _project(client, "PRJ-PRF-MANY")
    _commitment(
        client, project_id, _investor(client, "Investor A"), "1000.00", profit="200.00"
    )
    _commitment(
        client, project_id, _investor(client, "Investor B"), "3000.00", profit="400.00"
    )
    summary = _summary(client, project_id)
    assert _money(summary, "investor_committed_capital") == Decimal("4000.00")
    assert _money(summary, "investor_contracted_profit") == Decimal("600.00")
    assert _money(summary, "investor_total_return") == Decimal("4600.00")
    assert _money(summary, "investhome_estimated_profit") == Decimal("5400.00")
    assert _money(summary, "total_project_profit") == Decimal("6000.00")


def test_missing_contracted_profit_stays_unknown(client: TestClient) -> None:
    project_id = _project(client, "PRJ-PRF-MISS")
    _commitment(client, project_id, _investor(client, "Known"), "1000.00", profit="200.00")
    _commitment(client, project_id, _investor(client, "Unknown"), "500.00", profit=None)
    summary = _summary(client, project_id)
    assert _money(summary, "investor_committed_capital") == Decimal("1500.00")
    assert summary["investor_contracted_profit"]["available"] is False
    assert summary["investor_contracted_profit"]["value"] is None
    assert summary["investor_total_return"]["available"] is False
    assert summary["investhome_estimated_profit"]["available"] is False
    assert _money(summary, "total_project_profit") == Decimal("6000.00")


def test_cancelled_and_proposed_commitments_are_excluded(client: TestClient) -> None:
    project_id = _project(client, "PRJ-PRF-SKIP")
    _commitment(client, project_id, _investor(client, "Active"), "1000.00", profit="200.00")
    _commitment(
        client,
        project_id,
        _investor(client, "Cancelled"),
        "9000.00",
        profit="8000.00",
        status=CommitmentStatus.CANCELLED.value,
    )
    _commitment(
        client,
        project_id,
        _investor(client, "Draft"),
        "5000.00",
        profit="700.00",
        status=CommitmentStatus.PROPOSED.value,
    )
    summary = _summary(client, project_id)
    assert _money(summary, "investor_committed_capital") == Decimal("1000.00")
    assert _money(summary, "investor_contracted_profit") == Decimal("200.00")
    assert _money(summary, "investor_total_return") == Decimal("1200.00")
    assert _money(summary, "investhome_estimated_profit") == Decimal("5800.00")
    assert _money(summary, "total_project_cost") == Decimal("4000.00")


def test_customer_proforma_hides_internal_and_investor_profit(client: TestClient) -> None:
    project_id = _project(client, "PRJ-PRF-CUST")
    _commitment(client, project_id, _investor(client, "Customer Gate"), "1000.00", profit="250.00")
    customer = client.get(f"/projects/{project_id}/financials", params={"audience": "customer"})
    assert customer.status_code == 200, customer.text
    body = customer.json()
    assert body["summary"]["investor_contracted_profit"]["available"] is False
    assert body["summary"]["investor_contracted_profit"]["value"] is None
    assert body["summary"]["investor_total_return"]["value"] is None
    assert body["summary"]["investhome_estimated_profit"]["value"] is None
    assert "total_project_profit" not in body["summary"]
    blob = customer.text
    for hidden in ("250.00", "1250.00", "5750.00", "6000.00"):
        assert hidden not in blob


def test_investor_profit_is_hidden_without_financial_permission(
    auth_client: TestClient, db: Session
) -> None:
    del db
    login = auth_client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "Demo123!"}
    )
    assert login.status_code == 200, login.text
    project_id = _project(auth_client, "PRJ-PRF-AUTH")
    _commitment(
        auth_client,
        project_id,
        _investor(auth_client, "Restricted Investor"),
        "1000.00",
        profit="250.00",
    )

    sales = auth_client.post(
        "/auth/login", json={"email": "sales@example.com", "password": "Demo123!"}
    )
    assert sales.status_code == 200, sales.text
    denied = auth_client.get(f"/projects/{project_id}/financials")
    assert denied.status_code == 403
    investors = auth_client.get(f"/projects/{project_id}/investors")
    assert investors.status_code == 200, investors.text
    item = investors.json()["items"][0]
    assert item["contracted_profit"] is None
    assert item["committed_amount"] is None
    assert "250" not in investors.text

    admin = auth_client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "Demo123!"}
    )
    assert admin.status_code == 200, admin.text
    visible = auth_client.get(f"/projects/{project_id}/investors")
    assert Decimal(str(visible.json()["items"][0]["contracted_profit"])) == Decimal("250.00")
