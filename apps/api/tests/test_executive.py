from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    FinancialAccount,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentObligation,
)
from investhome_api.models.investor import InvestorStatus, InvestorType
from investhome_api.models.lead import LeadStatus
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


def _seed_lead(client: TestClient) -> None:
    client.post(
        "/leads",
        json={
            "full_name": "Executive Lead",
            "status": LeadStatus.QUALIFIED.value,
            "estimated_budget": "500000.00",
        },
    )


def _seed_investor(client: TestClient) -> None:
    client.post(
        "/investors",
        json={
            "full_name": "Executive Investor",
            "investor_type": InvestorType.INDIVIDUAL.value,
            "status": InvestorStatus.ACTIVE.value,
            "investment_capacity": "1000000.00",
        },
    )


def _seed_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": "PRJ-EXEC-001",
            "project_name": "Executive Tower",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
            "total_units": 10,
            "total_development_cost": "5000000.00",
            "current_project_value": "4500000.00",
            "equity_required": "2000000.00",
            "equity_raised": "1000000.00",
            "target_completion_date": (date.today() - timedelta(days=5)).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def _seed_account(client: TestClient) -> dict:
    response = client.post(
        "/finance/accounts",
        json={
            "account_name": "Executive Operating",
            "account_type": AccountType.OPERATING.value,
            "currency": "USD",
            "current_balance": "100000.00",
            "available_balance": "10000.00",
            "status": AccountStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_executive_summary_and_attention(client: TestClient) -> None:
    _seed_lead(client)
    _seed_investor(client)
    project = _seed_project(client)
    _seed_account(client)

    client.post(
        "/finance/payment-obligations",
        json={
            "project_id": project["id"],
            "obligation_type": ObligationType.VENDOR_PAYMENT.value,
            "payee": "Critical Vendor",
            "amount": "50000.00",
            "currency": "USD",
            "due_date": (date.today() - timedelta(days=3)).isoformat(),
            "status": ObligationStatus.OVERDUE.value,
            "priority": ObligationPriority.CRITICAL.value,
        },
    )

    summary = client.get("/executive/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert len(body["cards"]) == 8
    assert any(card["key"] == "total_leads" and card["value"] == 1 for card in body["cards"])

    attention = client.get("/executive/attention")
    assert attention.status_code == 200
    items = attention.json()["items"]
    assert len(items) >= 2
    assert any(item["severity"] == "critical" for item in items)


def test_executive_pipeline_and_portfolio(client: TestClient) -> None:
    _seed_lead(client)
    _seed_project(client)

    pipeline = client.get("/executive/leads-pipeline")
    assert pipeline.status_code == 200
    assert pipeline.json()["stages"]

    portfolio = client.get("/executive/project-portfolio")
    assert portfolio.status_code == 200
    projects = portfolio.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["health_status"] in {"on_track", "attention", "at_risk"}


def test_executive_financial_and_deadlines(client: TestClient) -> None:
    account = _seed_account(client)
    project = _seed_project(client)

    client.post(
        "/finance/transactions",
        json={
            "transaction_date": date.today().isoformat(),
            "transaction_type": "rental_income",
            "amount": "25000.00",
            "currency": "USD",
            "description": "Executive rent",
            "account_id": account["id"],
            "project_id": project["id"],
            "status": "completed",
        },
    )

    financial = client.get("/executive/financial-overview")
    assert financial.status_code == 200
    assert financial.json()["cash_by_account"]

    deadlines = client.get("/executive/deadlines")
    assert deadlines.status_code == 200
    assert isinstance(deadlines.json()["items"], list)


def test_executive_invalid_date_range(client: TestClient) -> None:
    response = client.get(
        "/executive/summary",
        params={"date_from": "2026-07-10", "date_to": "2026-07-01"},
    )
    assert response.status_code == 422
