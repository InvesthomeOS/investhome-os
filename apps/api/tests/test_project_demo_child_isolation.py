"""Real projects hide demo child rows. Demo projects still show them."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.document import Document
from investhome_api.models.finance import (
    AccountType,
    BudgetCategory,
    CommitmentType,
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    ProjectBudget,
    TransactionType,
)
from investhome_api.models.inventory import (
    AvailabilityStatus,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    UsageType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project


def _create_project(client: TestClient, code: str, *, demo: bool, db: Session) -> str:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": code,
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "construction_budget": "1000.00",
            "total_development_cost": "1000.00",
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


def _asset(
    project_id: str,
    display_id: str,
    *,
    demo: bool,
    available: bool = False,
    sold: bool = False,
) -> InventoryAsset:
    return InventoryAsset(
        project_id=UUID(project_id),
        display_id=display_id,
        system_code=f"SYS-{uuid4()}",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        availability_status=(
            AvailabilityStatus.AVAILABLE if available else AvailabilityStatus.UNAVAILABLE
        ),
        sales_status=InventorySalesStatus.SOLD if sold else InventorySalesStatus.NOT_FOR_SALE,
        is_demo=demo,
    )


def _document(project_id: str, title: str, *, demo: bool) -> Document:
    token = uuid4().hex
    return Document(
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


def test_real_project_hides_demo_children(client: TestClient, db: Session) -> None:
    project_id = _create_project(client, "PRJ-ISO-REAL", demo=False, db=db)
    db.add_all(
        [
            _asset(project_id, "REAL-1", demo=False, available=True),
            _asset(project_id, "DEMO-1", demo=True, sold=True),
        ]
    )
    investor = Investor(full_name="Operational Investor")
    db.add(investor)
    db.flush()
    db.add_all(
        [
            FundingCommitment(
                project_id=UUID(project_id),
                investor_id=investor.id,
                commitment_type=CommitmentType.EQUITY,
                committed_amount=Decimal("1000.00"),
                funded_amount=Decimal("1000.00"),
                is_demo=False,
            ),
            FundingCommitment(
                project_id=UUID(project_id),
                investor_id=investor.id,
                commitment_type=CommitmentType.EQUITY,
                committed_amount=Decimal("9000.00"),
                funded_amount=Decimal("9000.00"),
                is_demo=True,
            ),
            ProjectBudget(
                project_id=UUID(project_id),
                budget_name="Real construction",
                category=BudgetCategory.CONSTRUCTION,
                original_budget=Decimal("100.00"),
                paid_amount=Decimal("100.00"),
                is_demo=False,
            ),
            ProjectBudget(
                project_id=UUID(project_id),
                budget_name="Demo construction",
                category=BudgetCategory.CONSTRUCTION,
                original_budget=Decimal("500.00"),
                paid_amount=Decimal("500.00"),
                is_demo=True,
            ),
        ]
    )
    db.commit()

    units = client.get(f"/projects/{project_id}/units")
    assert units.status_code == 200, units.text
    unit_body = units.json()
    assert unit_body["total"] == 1
    assert [item["unit"] for item in unit_body["items"]] == ["REAL-1"]
    assert unit_body["summary"]["total_units"]["value"] == 1
    assert unit_body["summary"]["sold"]["value"] == 0
    assert unit_body["summary"]["available"]["value"] == 1

    sales = client.get(f"/projects/{project_id}/sales")
    assert sales.status_code == 200, sales.text
    assert sales.json()["summary"]["sold_units"]["value"] == 0
    assert sales.json()["summary"]["available_units"]["value"] == 1

    leasing = client.get(f"/projects/{project_id}/leasing")
    assert leasing.status_code == 200, leasing.text
    assert [item["unit"] for item in leasing.json()["items"]] == ["REAL-1"]

    investors = client.get(f"/projects/{project_id}/investors")
    assert investors.status_code == 200, investors.text
    investor_body = investors.json()
    assert investor_body["total"] == 1
    assert Decimal(str(investor_body["items"][0]["committed_amount"])) == Decimal("1000.00")

    financials = client.get(f"/projects/{project_id}/financials")
    assert financials.status_code == 200, financials.text
    finance_body = financials.json()
    assert [row["budget_name"] for row in finance_body["budgets"]] == ["Real construction"]
    assert len(finance_body["capital"]) == 1
    assert Decimal(str(finance_body["summary"]["budget_paid"]["value"])) == Decimal("100.00")

    executive = client.get(f"/projects/{project_id}/executive-finance")
    assert executive.status_code == 200, executive.text
    executive_body = executive.json()
    assert Decimal(str(executive_body["committed_funding"]["value"])) == Decimal("1000.00")
    assert Decimal(str(executive_body["actual_cost"]["value"])) == Decimal("100.00")

    cash = client.get(f"/projects/{project_id}/cash-flow-summary")
    assert cash.status_code == 200, cash.text

    detail = client.get(f"/projects/{project_id}/detail")
    assert detail.status_code == 200, detail.text
    assert detail.json()["units_count"] == 1

    overview = client.get(f"/projects/{project_id}/overview")
    assert overview.status_code == 200, overview.text
    assert overview.json()["sales_leasing_snapshot"]["sold_units"]["value"] == 0
    budget_used = overview.json()["financial_snapshot"]["budget_used"]["value"]
    assert Decimal(str(budget_used)) == Decimal("100.00")

    dashboard = client.get("/projects/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    dash = dashboard.json()
    assert dash["sales"]["sold_units"]["value"] == 0
    assert dash["sales"]["available_units"]["value"] == 1
    assert Decimal(str(dash["financials"]["budget_spent"]["value"])) == Decimal("100.00")


def test_demo_project_keeps_demo_children(client: TestClient, db: Session) -> None:
    project_id = _create_project(client, "PRJ-ISO-DEMO", demo=True, db=db)
    db.add(_asset(project_id, "DEMO-ONLY", demo=True, sold=True))
    db.add(
        ProjectBudget(
            project_id=UUID(project_id),
            budget_name="Demo budget",
            category=BudgetCategory.CONSTRUCTION,
            original_budget=Decimal("250.00"),
            paid_amount=Decimal("250.00"),
            is_demo=True,
        )
    )
    db.commit()

    units = client.get(f"/projects/{project_id}/units")
    assert units.status_code == 200, units.text
    assert units.json()["total"] == 1
    assert units.json()["items"][0]["unit"] == "DEMO-ONLY"
    assert units.json()["summary"]["sold"]["value"] == 1

    financials = client.get(f"/projects/{project_id}/financials")
    assert financials.status_code == 200, financials.text
    assert [row["budget_name"] for row in financials.json()["budgets"]] == ["Demo budget"]
    assert Decimal(str(financials.json()["summary"]["budget_paid"]["value"])) == Decimal("250.00")


def test_real_project_documents_exclude_demo_document(client: TestClient, db: Session) -> None:
    project_id = _create_project(client, "PRJ-ISO-DOCS", demo=False, db=db)
    db.add_all([_document(project_id, f"Real {index}", demo=False) for index in range(1, 7)])
    db.add(_document(project_id, "Demo document", demo=True))
    db.commit()

    response = client.get(f"/projects/{project_id}/documents")
    assert response.status_code == 200, response.text
    body = response.json()
    titles = {item["title"] for item in body["items"]}
    assert body["total"] == 6
    assert "Demo document" not in titles
    assert titles == {f"Real {index}" for index in range(1, 7)}

    detail = client.get(f"/projects/{project_id}/detail")
    assert detail.status_code == 200, detail.text
    assert detail.json()["documents_count"] == 6


def test_real_project_finance_transactions_exclude_demo(client: TestClient, db: Session) -> None:
    project_id = _create_project(client, "PRJ-ISO-TXN", demo=False, db=db)
    account = FinancialAccount(account_name="Operating", account_type=AccountType.OPERATING)
    db.add(account)
    db.flush()
    db.add_all(
        [
            FinanceTransaction(
                transaction_date=date(2026, 1, 1),
                transaction_type=TransactionType.INCOME,
                amount=Decimal("40.00"),
                account_id=account.id,
                project_id=UUID(project_id),
                description="Real receipt",
                is_demo=False,
            ),
            FinanceTransaction(
                transaction_date=date(2026, 1, 2),
                transaction_type=TransactionType.INCOME,
                amount=Decimal("80.00"),
                account_id=account.id,
                project_id=UUID(project_id),
                description="Demo receipt",
                is_demo=True,
            ),
        ]
    )
    db.commit()

    response = client.get("/finance/transactions", params={"project_id": project_id})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert [item["description"] for item in body["items"]] == ["Real receipt"]
