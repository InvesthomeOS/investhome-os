"""One project, two phases: units, sales, and budgets stay on the selected phase."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.finance import CommitmentStatus, CommitmentType, FundingCommitment
from investhome_api.models.inventory import (
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    ProjectPhase,
    UsageType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.models.project_budget import (
    BudgetAudience,
    BudgetCategoryType,
    BudgetVersionStatus,
    ProjectBudgetCategory,
    ProjectBudgetLine,
    ProjectBudgetVersion,
)
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.crm.agreement_service import cancel_agreement, create_manual_agreement
from investhome_api.services.crm.unit_link import resolve_agreement_unit


def _project(db: Session, name: str) -> Project:
    row = Project(
        project_code=f"PRJ-PH-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        currency="USD",
    )
    db.add(row)
    db.flush()
    return row


def _phase(db: Session, project: Project, name: str, address: str) -> ProjectPhase:
    row = ProjectPhase(
        project_id=project.id,
        name=name,
        display_order=1 if name.endswith("2") else 0,
        active=True,
        address_line=address,
    )
    db.add(row)
    db.flush()
    return row


def _unit(
    db: Session,
    project: Project,
    phase: ProjectPhase,
    number: str,
    *,
    price: Decimal | None,
    asset_id=None,
) -> InventoryAsset:
    row = InventoryAsset(
        id=asset_id or uuid4(),
        project_id=project.id,
        phase_id=phase.id,
        display_id=number,
        system_code=f"{phase.id.hex[:8]}-{number}",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        list_price=price,
        currency="USD",
    )
    db.add(row)
    db.flush()
    return row


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


def _user(db: Session) -> User:
    row = User(
        full_name="Phase Scope",
        email=f"phase-scope-{uuid4().hex[:8]}@example.com",
        hashed_password="not-a-login",
        status=UserStatus.ACTIVE,
    )
    db.add(row)
    db.flush()
    return row


def _budget(
    db: Session,
    project: Project,
    category: ProjectBudgetCategory,
    *,
    version_number: int,
    amount: str,
    phase_id=None,
    audience: BudgetAudience = BudgetAudience.INTERNAL,
) -> None:
    version = ProjectBudgetVersion(
        project_id=project.id,
        phase_id=phase_id,
        name=f"v{version_number}",
        audience=audience,
        version_number=version_number,
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


def test_same_unit_number_can_belong_to_two_phases_and_existing_id_stays(db: Session) -> None:
    campus = _project(db, "Campus Example")
    kept_id = uuid4()
    phase_one = _phase(db, campus, "3220", "3220 16th St NW")
    phase_two = _phase(db, campus, "3224", "3224 16th St NW")
    kept = _unit(db, campus, phase_one, "101", price=Decimal("100"), asset_id=kept_id)
    other = _unit(db, campus, phase_two, "101", price=None)
    separate = _project(db, "3220 Existing")
    separate_unit = _unit(
        db,
        separate,
        _phase(db, separate, "Existing", "Minnesota Ave NE"),
        "101",
        price=Decimal("10"),
    )
    db.commit()

    assert kept.id == kept_id
    assert kept.project_id == campus.id
    assert other.project_id == campus.id
    assert other.id != kept.id
    assert separate_unit.project_id == separate.id
    assert db.get(InventoryAsset, kept_id).phase_id == phase_one.id
    assert phase_one.address_line == "3220 16th St NW"
    assert separate.project_name == "3220 Existing"


def test_one_buyer_can_purchase_two_units_and_a_second_sale_is_refused(
    client: TestClient, db: Session
) -> None:
    project = _project(db, "UniLoft")
    phase_one = _phase(db, project, "Faz 1", "3220 16th St NW")
    phase_two = _phase(db, project, "Faz 2", "3224 16th St NW")
    first = _unit(db, project, phase_one, "101", price=Decimal("100"))
    second = _unit(db, project, phase_two, "101", price=Decimal("120"))
    buyer = _person(db, "Phase Buyer")
    db.commit()

    with pytest.raises(ValueError, match="unit_phase_mismatch"):
        resolve_agreement_unit(
            db,
            project_id=project.id,
            unit_number="101",
            phase_id=phase_two.id,
            inventory_asset_id=first.id,
        )

    created, reused = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="101",
        investment_amount="100",
        agreement_date=None,
        phase_id=phase_one.id,
        inventory_asset_id=first.id,
    )
    assert reused is False
    assert created.inventory_asset_id == first.id
    assert created.phase_id == phase_one.id
    assert created.unit_number == "101"
    assert db.get(InventoryAsset, first.id).sales_status == InventorySalesStatus.UNDER_CONTRACT

    again, reused_again = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="101",
        investment_amount="100",
        agreement_date=None,
        phase_id=phase_one.id,
        inventory_asset_id=first.id,
    )
    assert reused_again is True
    assert again.id == created.id
    other_buyer = _person(db, "Other Buyer")
    with pytest.raises(ValueError, match="unit_already_committed"):
        create_manual_agreement(
            db,
            contact=other_buyer,
            project_group="uniloft",
            unit_number="101",
            investment_amount="100",
            agreement_date=None,
            phase_id=phase_one.id,
            inventory_asset_id=first.id,
        )

    other, other_reused = create_manual_agreement(
        db,
        contact=buyer,
        project_group="uniloft",
        unit_number="101",
        investment_amount="120",
        agreement_date=None,
        phase_id=phase_two.id,
        inventory_asset_id=second.id,
    )
    assert other_reused is False
    assert other.id != created.id
    assert other.phase_id == phase_two.id
    assert other.inventory_asset_id == second.id
    assert created.unit_number == "101"
    db.commit()
    phase_sales = client.get(
        f"/projects/{project.id}/financials", params={"phase_id": str(phase_one.id)}
    )
    assert phase_sales.status_code == 200, phase_sales.text
    assert Decimal(str(phase_sales.json()["summary"]["contracted_sales_value"]["value"])) == Decimal("100")
    both = client.get(f"/projects/{project.id}/financials")
    assert Decimal(str(both.json()["summary"]["contracted_sales_value"]["value"])) == Decimal("220")

    cancel_agreement(db, _user(db), created, reason="Alıcı vazgeçti")
    db.flush()
    assert created.unit_number == "101"
    assert db.get(InventoryAsset, first.id).sales_status == InventorySalesStatus.AVAILABLE_FOR_SALE
    assert db.get(InventoryAsset, second.id).sales_status == InventorySalesStatus.UNDER_CONTRACT


def test_phase_budgets_are_not_added_to_the_project_version(
    client: TestClient, db: Session
) -> None:
    project = _project(db, "Scoped Finance")
    phase_one = _phase(db, project, "3220", "3220 16th St NW")
    phase_two = _phase(db, project, "3224", "3224 16th St NW")
    category = ProjectBudgetCategory(
        code=f"cost-{uuid4().hex[:6]}",
        name="Cost",
        category_type=BudgetCategoryType.HARD_COST,
    )
    db.add(category)
    db.flush()
    _budget(db, project, category, version_number=1, amount="1000")
    _budget(db, project, category, version_number=2, amount="40", phase_id=phase_one.id)
    _budget(db, project, category, version_number=3, amount="60", phase_id=phase_two.id)
    _budget(
        db,
        project,
        category,
        version_number=4,
        amount="15",
        phase_id=phase_one.id,
        audience=BudgetAudience.CUSTOMER,
    )
    investor = Investor(full_name="Phase Investor")
    db.add(investor)
    db.flush()
    db.add(
        FundingCommitment(
            project_id=project.id,
            investor_id=investor.id,
            commitment_type=CommitmentType.EQUITY,
            committed_amount=Decimal("50"),
            contracted_profit=Decimal("10"),
            currency="USD",
            status=CommitmentStatus.COMMITTED,
        )
    )
    db.commit()

    whole = client.get(f"/projects/{project.id}/financials")
    assert whole.status_code == 200, whole.text
    summary = whole.json()["summary"]
    assert Decimal(str(summary["total_project_cost"]["value"])) == Decimal("100")
    assert Decimal(str(summary["investor_committed_capital"]["value"])) == Decimal("50")
    assert summary["realized_revenue"]["available"] is False
    assert summary["total_project_cost"]["value"] != summary["investor_committed_capital"]["value"]

    first = client.get(f"/projects/{project.id}/financials", params={"phase_id": str(phase_one.id)})
    second = client.get(f"/projects/{project.id}/financials", params={"phase_id": str(phase_two.id)})
    assert Decimal(str(first.json()["summary"]["total_project_cost"]["value"])) == Decimal("40")
    assert Decimal(str(second.json()["summary"]["total_project_cost"]["value"])) == Decimal("60")
    assert first.json()["summary"]["investor_committed_capital"]["available"] is False
    assert first.json()["summary"]["actual_cost"]["available"] is False

    customer = client.get(
        f"/projects/{project.id}/financials",
        params={"audience": "customer", "phase_id": str(phase_one.id)},
    )
    assert customer.status_code == 200, customer.text
    body = customer.json()["summary"]
    assert Decimal(str(body["published_budget"]["value"])) == Decimal("15")
    assert body["investor_contracted_profit"]["available"] is False
    assert body["investhome_estimated_profit"]["available"] is False
    assert "total_project_profit" not in body
    assert "40.00" not in customer.text
    assert "1000" not in whole.text


def test_unit_list_follows_the_phase_and_missing_price_is_unavailable(
    client: TestClient, db: Session
) -> None:
    project = _project(db, "Unit Filter")
    phase_one = _phase(db, project, "3220", "3220 16th St NW")
    phase_two = _phase(db, project, "3224", "3224 16th St NW")
    _unit(db, project, phase_one, "101", price=Decimal("100"))
    _unit(db, project, phase_two, "101", price=None)
    db.commit()

    scoped = client.get(f"/projects/{project.id}/units", params={"phase_id": str(phase_one.id)})
    assert scoped.status_code == 200, scoped.text
    body = scoped.json()
    assert [item["unit"] for item in body["items"]] == ["101"]
    assert body["items"][0]["phase_id"] == str(phase_one.id)
    assert body["summary"]["total_list_value"]["available"] is True
    missing = client.get(f"/projects/{project.id}/units", params={"phase_id": str(phase_two.id)})
    assert missing.json()["summary"]["total_list_value"]["available"] is False
    whole = client.get(f"/projects/{project.id}/units")
    assert whole.status_code == 200, whole.text
    assert whole.json()["total"] == 2
