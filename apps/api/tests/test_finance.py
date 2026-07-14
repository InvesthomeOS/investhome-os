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
from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    BudgetCategory,
    CommitmentStatus,
    CommitmentType,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentMethod,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.investor import InvestorStatus, InvestorType
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


def _create_project(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_code": "PRJ-FIN-001",
        "project_name": "Finance Test Project",
        "city": "Washington",
        "project_type": ProjectType.RESIDENTIAL.value,
        "development_type": DevelopmentType.GROUND_UP.value,
        "project_status": ProjectStatus.CONSTRUCTION.value,
    }
    payload.update(overrides)
    response = client.post("/projects", json=payload)
    assert response.status_code == 201
    return response.json()


def _create_investor(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Finance Test Investor",
        "email": "finance.test@example.com",
        "country": "United States",
        "investor_type": InvestorType.INDIVIDUAL.value,
        "status": InvestorStatus.ACTIVE.value,
    }
    payload.update(overrides)
    response = client.post("/investors", json=payload)
    assert response.status_code == 201
    return response.json()


def _create_account_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "account_name": "Test Operating Account",
        "account_type": AccountType.OPERATING.value,
        "institution_name": "Test Bank",
        "ownership_entity": "Test Holdings LLC",
        "currency": "USD",
        "current_balance": "1000000.00",
        "available_balance": "950000.00",
        "account_reference": "TB-001",
        "status": AccountStatus.ACTIVE.value,
        "notes": "Test account",
    }
    payload.update(overrides)
    return payload


def _create_transaction_payload(
    account_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "transaction_date": date(2026, 6, 1).isoformat(),
        "transaction_type": TransactionType.EXPENSE.value,
        "category": "Operating",
        "amount": "5000.00",
        "currency": "USD",
        "description": "Test transaction",
        "account_id": account_id,
        "payment_method": PaymentMethod.WIRE.value,
        "status": TransactionStatus.COMPLETED.value,
        "paid_date": date(2026, 6, 1).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_finance_stats_and_summary(client: TestClient) -> None:
    account = client.post("/finance/accounts", json=_create_account_payload()).json()
    project = _create_project(client)
    client.post(
        "/finance/transactions",
        json=_create_transaction_payload(
            account["id"],
            project_id=project["id"],
            transaction_type=TransactionType.INVESTMENT_INFLOW.value,
            status=TransactionStatus.PENDING.value,
            amount="250000.00",
        ),
    )
    client.post(
        "/finance/payment-obligations",
        json={
            "obligation_type": ObligationType.VENDOR_PAYMENT.value,
            "amount": "10000.00",
            "currency": "USD",
            "status": ObligationStatus.OVERDUE.value,
            "priority": ObligationPriority.HIGH.value,
        },
    )

    stats = client.get("/finance/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert Decimal(body["total_cash"]["USD"]) == Decimal("1000000.00")
    assert Decimal(body["pending_receivables"]["USD"]) == Decimal("250000.00")
    assert Decimal(body["overdue_payments"]["USD"]) == Decimal("10000.00")

    summary = client.get("/finance/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["project_count"] == 1
    assert summary_body["active_investors"] == 0


def test_accounts_crud_and_archive(client: TestClient) -> None:
    create_response = client.post("/finance/accounts", json=_create_account_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    account_id = created["id"]
    assert created["account_name"] == "Test Operating Account"

    list_response = client.get("/finance/accounts")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = client.get(f"/finance/accounts/{account_id}")
    assert get_response.status_code == 200

    update_response = client.patch(
        f"/finance/accounts/{account_id}",
        json={"current_balance": "1100000.00", "notes": "Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["notes"] == "Updated"

    archive_response = client.delete(f"/finance/accounts/{account_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    hidden = client.get("/finance/accounts")
    assert hidden.json()["total"] == 0


def test_transactions_crud_archive_and_filters(client: TestClient) -> None:
    account = client.post("/finance/accounts", json=_create_account_payload()).json()
    project = _create_project(client, project_code="PRJ-FIN-002", project_name="Filter Project")
    investor = _create_investor(client)

    create_response = client.post(
        "/finance/transactions",
        json=_create_transaction_payload(
            account["id"],
            project_id=project["id"],
            investor_id=investor["id"],
            description="Construction draw for Filter Project",
            transaction_type=TransactionType.CONSTRUCTION_COST.value,
            amount="75000.00",
        ),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    transaction_id = created["id"]
    assert created["project_name"] == "Filter Project"
    assert created["investor_name"] == "Finance Test Investor"
    assert created["account_name"] == "Test Operating Account"

    filtered = client.get(
        "/finance/transactions",
        params={
            "project_id": project["id"],
            "investor_id": investor["id"],
            "account_id": account["id"],
            "transaction_type": TransactionType.CONSTRUCTION_COST.value,
            "status": TransactionStatus.COMPLETED.value,
            "currency": "USD",
            "search": "Construction",
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    update_response = client.patch(
        f"/finance/transactions/{transaction_id}",
        json={"amount": "80000.00"},
    )
    assert update_response.status_code == 200
    assert Decimal(update_response.json()["amount"]) == Decimal("80000.00")

    archive_response = client.delete(f"/finance/transactions/{transaction_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None


def test_transaction_fk_validation(client: TestClient) -> None:
    missing_id = str(UUID("00000000-0000-0000-0000-000000000099"))
    response = client.post(
        "/finance/transactions",
        json={
            "transaction_date": date(2026, 6, 1).isoformat(),
            "transaction_type": TransactionType.EXPENSE.value,
            "amount": "100.00",
            "currency": "USD",
            "account_id": missing_id,
        },
    )
    assert response.status_code == 404


def test_project_budgets_crud(client: TestClient) -> None:
    project = _create_project(client, project_code="PRJ-FIN-003")

    create_response = client.post(
        "/finance/project-budgets",
        json={
            "project_id": project["id"],
            "budget_name": "Construction Budget",
            "category": BudgetCategory.CONSTRUCTION.value,
            "original_budget": "5000000.00",
            "revised_budget": "5200000.00",
            "paid_amount": "2100000.00",
            "forecast_amount": "5350000.00",
            "currency": "USD",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    budget_id = created["id"]
    assert created["project_name"] == "Finance Test Project"
    assert Decimal(created["remaining"]) == Decimal("3100000.00")
    assert Decimal(created["variance"]) == Decimal("150000.00")

    filtered = client.get(
        "/finance/project-budgets",
        params={"project_id": project["id"]},
    )
    assert filtered.json()["total"] == 1

    update_response = client.patch(
        f"/finance/project-budgets/{budget_id}",
        json={"paid_amount": "2500000.00"},
    )
    assert update_response.status_code == 200
    assert Decimal(update_response.json()["remaining"]) == Decimal("2700000.00")

    delete_response = client.delete(f"/finance/project-budgets/{budget_id}")
    assert delete_response.status_code == 204


def test_funding_commitments_crud(client: TestClient) -> None:
    project = _create_project(client, project_code="PRJ-FIN-004")
    investor = _create_investor(client, full_name="Commitment Investor", email="commit@example.com")

    create_response = client.post(
        "/finance/funding-commitments",
        json={
            "project_id": project["id"],
            "investor_id": investor["id"],
            "commitment_type": CommitmentType.EQUITY.value,
            "committed_amount": "2000000.00",
            "funded_amount": "1000000.00",
            "currency": "USD",
            "status": CommitmentStatus.PARTIALLY_FUNDED.value,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    commitment_id = created["id"]
    assert created["project_name"] == "Finance Test Project"
    assert created["investor_name"] == "Commitment Investor"
    assert Decimal(created["remaining_amount"]) == Decimal("1000000.00")

    filtered = client.get(
        "/finance/funding-commitments",
        params={"project_id": project["id"], "investor_id": investor["id"]},
    )
    assert filtered.json()["total"] == 1

    update_response = client.patch(
        f"/finance/funding-commitments/{commitment_id}",
        json={"funded_amount": "1500000.00", "remaining_amount": "500000.00"},
    )
    assert update_response.status_code == 200

    delete_response = client.delete(f"/finance/funding-commitments/{commitment_id}")
    assert delete_response.status_code == 204


def test_payment_obligations_crud_archive_and_filters(client: TestClient) -> None:
    project = _create_project(client, project_code="PRJ-FIN-005")

    create_response = client.post(
        "/finance/payment-obligations",
        json={
            "project_id": project["id"],
            "obligation_type": ObligationType.VENDOR_PAYMENT.value,
            "payee": "Test Vendor",
            "description": "Materials invoice",
            "amount": "45000.00",
            "currency": "USD",
            "due_date": date(2026, 8, 15).isoformat(),
            "status": ObligationStatus.UPCOMING.value,
            "priority": ObligationPriority.CRITICAL.value,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    obligation_id = created["id"]
    assert created["project_name"] == "Finance Test Project"

    filtered = client.get(
        "/finance/payment-obligations",
        params={
            "project_id": project["id"],
            "status": ObligationStatus.UPCOMING.value,
            "priority": ObligationPriority.CRITICAL.value,
            "due_date_from": date(2026, 8, 1).isoformat(),
            "due_date_to": date(2026, 8, 31).isoformat(),
        },
    )
    assert filtered.json()["total"] == 1

    update_response = client.patch(
        f"/finance/payment-obligations/{obligation_id}",
        json={"status": ObligationStatus.PAID.value, "paid_date": date(2026, 8, 10).isoformat()},
    )
    assert update_response.status_code == 200

    archive_response = client.delete(f"/finance/payment-obligations/{obligation_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None


def test_budget_missing_project_returns_404(client: TestClient) -> None:
    missing_id = str(UUID("00000000-0000-0000-0000-000000000099"))
    response = client.post(
        "/finance/project-budgets",
        json={
            "project_id": missing_id,
            "budget_name": "Invalid Budget",
            "category": BudgetCategory.OTHER.value,
        },
    )
    assert response.status_code == 404
