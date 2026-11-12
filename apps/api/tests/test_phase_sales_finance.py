"""Phase budget versions, verified collections, and sale commission stay separate."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.finance import (
    AccountType,
    FinanceTransaction,
    FinancialAccount,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.inventory import InventorySalesStatus, ProjectPhase
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.models.project_budget import (
    BudgetAudience,
    BudgetCategoryType,
    BudgetVersionStatus,
    ProjectBudgetCategory,
    ProjectBudgetLine,
    ProjectBudgetVersion,
)
from investhome_api.services.crm.agreement_service import create_manual_agreement
from investhome_api.services.project_budget_service import _next_version_number


def _project(db: Session, name: str) -> Project:
    row = Project(
        project_code=f"PRJ-SF-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        currency="USD",
    )
    db.add(row)
    db.flush()
    return row


def _phase(db: Session, project: Project, name: str) -> ProjectPhase:
    row = ProjectPhase(project_id=project.id, name=name, display_order=0, active=True)
    db.add(row)
    db.flush()
    return row


def _version(
    db: Session,
    project: Project,
    category: ProjectBudgetCategory,
    *,
    number: int,
    amount: str,
    phase_id=None,
    audience: BudgetAudience = BudgetAudience.INTERNAL,
) -> ProjectBudgetVersion:
    version = ProjectBudgetVersion(
        project_id=project.id,
        phase_id=phase_id,
        name=f"v{number}-{audience.value}",
        audience=audience,
        version_number=number,
        status=BudgetVersionStatus.APPROVED,
        is_current=True,
        currency="USD",
    )
    db.add(version)
    db.flush()
    db.add(
        ProjectBudgetLine(
            project_id=project.id,
            budget_version_id=version.id,
            category_id=category.id,
            line_number="1",
            name="Cost",
            current_budget=Decimal(amount),
            original_budget=Decimal(amount),
            currency="USD",
        )
    )
    db.flush()
    return version


def _person(db: Session, name: str) -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
        source="test",
    )
    db.add(row)
    db.flush()
    return row


def test_each_phase_and_audience_keeps_version_one(
    client: TestClient, db: Session
) -> None:
    project = _project(db, "Version Scope")
    first = _phase(db, project, "3220")
    second = _phase(db, project, "3224")
    category = ProjectBudgetCategory(
        code=f"sf-{uuid4().hex[:6]}",
        name="Cost",
        category_type=BudgetCategoryType.HARD_COST,
    )
    db.add(category)
    db.flush()
    kept = _version(db, project, category, number=1, amount="1000")
    kept_id = kept.id
    kept_status = kept.status
    phase_cost = _version(db, project, category, number=1, amount="40", phase_id=first.id)
    _version(db, project, category, number=1, amount="60", phase_id=second.id)
    _version(
        db,
        project,
        category,
        number=1,
        amount="15",
        phase_id=first.id,
        audience=BudgetAudience.CUSTOMER,
    )
    db.commit()

    saved = db.get(ProjectBudgetVersion, kept_id)
    assert saved is not None
    assert saved.id == kept_id
    assert saved.status == kept_status
    assert saved.version_number == 1
    assert saved.phase_id is None
    assert _next_version_number(db, project.id, BudgetAudience.INTERNAL, first.id) == 2
    assert _next_version_number(db, project.id, BudgetAudience.CUSTOMER, second.id) == 1
    duplicate = ProjectBudgetVersion(
        project_id=project.id,
        phase_id=first.id,
        name="duplicate",
        audience=BudgetAudience.INTERNAL,
        version_number=1,
        status=BudgetVersionStatus.DRAFT,
        currency="USD",
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    whole = client.get(f"/projects/{project.id}/financials")
    assert whole.status_code == 200, whole.text
    assert Decimal(str(whole.json()["summary"]["total_project_cost"]["value"])) == Decimal("100")
    customer = client.get(
        f"/projects/{project.id}/financials",
        params={"audience": "customer", "phase_id": str(first.id)},
    )
    body = customer.json()["summary"]
    assert Decimal(str(body["published_budget"]["value"])) == Decimal("15")
    assert "verified_collections" not in body
    assert "commission_amount" not in body
    assert "40.00" not in customer.text
    assert phase_cost.version_number == 1


def test_verified_cash_partial_refund_and_missing_link(
    client: TestClient, db: Session
) -> None:
    from datetime import date

    project = _project(db, "UniLoft")
    phase = _phase(db, project, "Faz 1")
    other = _phase(db, project, "Faz 2")
    from investhome_api.models.inventory import InventoryAsset, InventoryAssetType, UsageType

    def unit(phase_row: ProjectPhase, number: str) -> InventoryAsset:
        row = InventoryAsset(
            project_id=project.id,
            phase_id=phase_row.id,
            display_id=number,
            system_code=f"{phase_row.id.hex[:8]}-{number}",
            asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
            usage_type=UsageType.RESIDENTIAL,
            sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
            currency="USD",
        )
        db.add(row)
        db.flush()
        return row

    first = unit(phase, "101")
    second = unit(other, "202")
    buyer = _person(db, "Cash Buyer")
    account = FinancialAccount(account_name="Operating", account_type=AccountType.OPERATING)
    db.add(account)
    db.commit()

    sale, reused = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="101",
        investment_amount="100",
        agreement_date=date.today(),
        phase_id=phase.id,
        inventory_asset_id=first.id,
    )
    other_sale, other_reused = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="202",
        investment_amount="80",
        agreement_date=date.today(),
        phase_id=other.id,
        inventory_asset_id=second.id,
    )
    assert reused is False and other_reused is False
    assert sale.id != other_sale.id
    with pytest.raises(ValueError, match="unit_already_committed"):
        create_manual_agreement(
            db,
            contact=_person(db, "Second Buyer"),
            project_group="uniloft",
            unit_number="101",
            investment_amount="100",
            agreement_date=date.today(),
            phase_id=phase.id,
            inventory_asset_id=first.id,
        )
    db.add(
        FinanceTransaction(
            transaction_date=date.today(),
            transaction_type=TransactionType.SALE_PROCEEDS,
            amount=Decimal("40"),
            currency="USD",
            account_id=account.id,
            project_id=project.id,
            agreement_id=sale.id,
            status=TransactionStatus.COMPLETED,
        )
    )
    db.add(
        FinanceTransaction(
            transaction_date=date.today(),
            transaction_type=TransactionType.SALE_PROCEEDS,
            amount=Decimal("999"),
            currency="USD",
            account_id=account.id,
            project_id=project.id,
            agreement_id=sale.id,
            status=TransactionStatus.PENDING,
        )
    )
    db.add(
        FinanceTransaction(
            transaction_date=date.today(),
            transaction_type=TransactionType.SALE_PROCEEDS,
            amount=Decimal("500"),
            currency="USD",
            account_id=account.id,
            project_id=project.id,
            agreement_id=None,
            status=TransactionStatus.COMPLETED,
        )
    )
    db.commit()

    partial = client.get(f"/projects/{project.id}/financials", params={"phase_id": str(phase.id)})
    summary = partial.json()["summary"]
    assert Decimal(str(summary["contracted_sales_value"]["value"])) == Decimal("100")
    assert Decimal(str(summary["verified_collections"]["value"])) == Decimal("40")
    assert Decimal(str(summary["remaining_receivable"]["value"])) == Decimal("60")
    missing = client.get(
        f"/projects/{project.id}/financials", params={"phase_id": str(other.id)}
    )
    assert missing.json()["summary"]["verified_collections"]["available"] is False
    assert missing.json()["summary"]["remaining_receivable"]["available"] is False
    assert "999" not in partial.text
    assert "500" not in partial.text

    db.add(
        FinanceTransaction(
            transaction_date=date.today(),
            transaction_type=TransactionType.REFUND,
            amount=Decimal("10"),
            currency="USD",
            account_id=account.id,
            project_id=project.id,
            agreement_id=sale.id,
            status=TransactionStatus.COMPLETED,
        )
    )
    sale.metadata_json = {"discount_amount": "5"}
    db.commit()
    adjusted = client.get(
        f"/projects/{project.id}/financials", params={"phase_id": str(phase.id)}
    )
    assert Decimal(str(adjusted.json()["summary"]["verified_collections"]["value"])) == Decimal("30")
    assert Decimal(str(adjusted.json()["summary"]["remaining_receivable"]["value"])) == Decimal("65")

    from investhome_api.services.crm.agreement_service import cancel_agreement
    from investhome_api.models.user_auth import User, UserStatus

    actor = User(
        full_name="Cancel",
        email=f"cancel-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        status=UserStatus.ACTIVE,
    )
    db.add(actor)
    db.flush()
    cancel_agreement(db, actor, sale, reason="İade")
    db.commit()
    after = client.get(f"/projects/{project.id}/financials", params={"phase_id": str(phase.id)})
    assert after.json()["summary"]["contracted_sales_value"]["available"] is False
    assert after.json()["summary"]["verified_collections"]["available"] is False


def test_commission_is_not_added_to_sale_or_collection(
    client: TestClient, db: Session
) -> None:
    from datetime import date

    project = _project(db, "UniLoft")
    phase = _phase(db, project, "Faz 1")
    from investhome_api.models.inventory import InventoryAsset, InventoryAssetType, UsageType

    asset = InventoryAsset(
        project_id=project.id,
        phase_id=phase.id,
        display_id="301",
        system_code=f"com-{uuid4().hex[:6]}",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        currency="USD",
    )
    db.add(asset)
    buyer = _person(db, "Commission Buyer")
    agent = _person(db, "Agency")
    agent.contact_type = CrmContactType.BROKER
    account = FinancialAccount(account_name="Sales", account_type=AccountType.OPERATING)
    db.add(account)
    db.commit()
    sale, _reused = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="301",
        investment_amount="200",
        agreement_date=date.today(),
        phase_id=phase.id,
        inventory_asset_id=asset.id,
    )
    db.add(
        CrmAgreementParticipant(
            agreement_id=sale.id,
            contact_id=agent.id,
            role="broker",
            commission_rate=Decimal("0.0300"),
            commission_paid=Decimal("2.00"),
            commission_condition="Closing",
            is_primary=False,
        )
    )
    db.add(
        FinanceTransaction(
            transaction_date=date.today(),
            transaction_type=TransactionType.SALE_PROCEEDS,
            amount=Decimal("50"),
            currency="USD",
            account_id=account.id,
            project_id=project.id,
            agreement_id=sale.id,
            status=TransactionStatus.COMPLETED,
        )
    )
    db.commit()
    body = client.get(f"/projects/{project.id}/financials", params={"phase_id": str(phase.id)})
    summary = body.json()["summary"]
    assert Decimal(str(summary["contracted_sales_value"]["value"])) == Decimal("200")
    assert Decimal(str(summary["verified_collections"]["value"])) == Decimal("50")
    assert Decimal(str(summary["remaining_receivable"]["value"])) == Decimal("150")
    assert Decimal(str(summary["commission_amount"]["value"])) == Decimal("6.00")
    assert Decimal(str(summary["commission_paid"]["value"])) == Decimal("2.00")
    assert Decimal(str(summary["commission_remaining"]["value"])) == Decimal("4.00")
    assert summary["total_project_cost"]["value"] in (None, "0", "0.00", 0)


def test_sales_user_cannot_read_project_financials(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "Demo123!"}
    )
    assert login.status_code == 200, login.text
    created = auth_client.post(
        "/projects",
        json={
            "project_code": f"PRJ-DENY-{uuid4().hex[:6]}",
            "project_name": "Hidden Finance",
            "city": "Austin",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
        },
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]
    sales = auth_client.post(
        "/auth/login", json={"email": "sales@example.com", "password": "Demo123!"}
    )
    assert sales.status_code == 200, sales.text
    denied = auth_client.get(f"/projects/{project_id}/financials")
    assert denied.status_code == 403
