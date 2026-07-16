"""Sales contract readiness integration tests."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventorySalesStatus,
    ReservationRecordStatus,
    ReservationType,
    StructureStatus,
    UsageType,
)
from investhome_api.models.lead import LeadStatus
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.models.sales import OpportunityNextAction, OpportunityPartyType, OpportunityStage
from investhome_api.models.sales_proposal import ProposalStatus
from investhome_api.models.sales_readiness import (
    ReadinessCaseStatus,
    ReadinessRequirementStatus,
    ReadinessRequirementType,
    SalesReadinessCase,
    SalesReadinessRequirement,
)
from investhome_api.services.sales.readiness_service import compute_percentage
from investhome_api.services.sales.readiness_template_service import seed_default_template

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _create_lead(client: TestClient, *, name: str = "Readiness Lead") -> dict:
    response = client.post(
        "/leads",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "status": LeadStatus.QUALIFIED.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_opportunity(client: TestClient, lead: dict) -> dict:
    response = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "next_action": OpportunityNextAction.CALL.value,
            "next_action_date": (date.today() + timedelta(days=3)).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": f"PRJ-RDY-{datetime.now().strftime('%H%M%S')}",
            "project_name": "Readiness Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_asset(client: TestClient, project_id: str) -> dict:
    building = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "code": "R",
            "name": "Readiness Building",
            "building_type": BuildingType.APARTMENT.value,
            "total_floors": 5,
            "status": StructureStatus.ACTIVE.value,
        },
    ).json()
    floor = client.post(
        "/inventory/floors",
        json={
            "building_id": building["id"],
            "floor_number": 2,
            "display_name": "Level 2",
            "level_code": "02",
            "sort_order": 2,
            "status": StructureStatus.ACTIVE.value,
        },
    ).json()
    asset = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": f"RDY-{datetime.now().strftime('%H%M%S')}",
            "asset_type": "residential_unit",
            "usage_type": UsageType.RESIDENTIAL.value,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
            "currency": "USD",
            "list_price": "250000.00",
        },
    )
    assert asset.status_code == 201, asset.text
    return asset.json()


def _link_inventory(client: TestClient, opp_id: str, asset_id: str) -> None:
    response = client.post(
        f"/sales/opportunities/{opp_id}/inventory",
        json={"inventory_asset_id": asset_id},
    )
    assert response.status_code == 201, response.text


def _create_readiness_case(client: TestClient, opp_id: str, asset_id: str) -> dict:
    response = client.post(
        f"/sales/readiness/opportunities/{opp_id}/cases",
        json={"inventory_asset_id": asset_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_opportunity_with_asset(auth_client: TestClient, *, name: str = "Readiness Lead", as_admin: bool = True) -> tuple[dict, dict]:
    if as_admin:
        _login(auth_client, "admin@example.com")
    lead = _create_lead(auth_client, name=name)
    opp = _create_opportunity(auth_client, lead)
    project = _create_project(auth_client)
    asset = _create_asset(auth_client, project["id"])
    _link_inventory(auth_client, opp["id"], asset["id"])
    return opp, asset


def test_readiness_case_creation(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client)
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    assert case["case_code"].startswith("RDY-")
    assert case["opportunity_id"] == opp["id"]
    assert len(case["requirements"]) >= 10
    assert case["readiness_percentage"] >= 0


def test_one_active_case_per_opportunity_asset(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Unique Lead")
    _login(auth_client, "sales@example.com")
    _create_readiness_case(auth_client, opp["id"], asset["id"])
    dup = auth_client.post(
        f"/sales/readiness/opportunities/{opp['id']}/cases",
        json={"inventory_asset_id": asset["id"]},
    )
    assert dup.status_code == 422


def test_percentage_calculation(db: Session) -> None:
    reqs = [
        SalesReadinessRequirement(is_mandatory=True, status=ReadinessRequirementStatus.VERIFIED, title="A", requirement_type=ReadinessRequirementType.PARTY_IDENTITY, readiness_case_id=UUID("00000000-0000-0000-0000-000000000001")),
        SalesReadinessRequirement(is_mandatory=True, status=ReadinessRequirementStatus.MISSING, title="B", requirement_type=ReadinessRequirementType.DEPOSIT_RECEIVED, readiness_case_id=UUID("00000000-0000-0000-0000-000000000001")),
    ]
    assert compute_percentage(reqs) == 50


def test_verify_and_waive_permissions(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Waiver Lead")
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    req = next(r for r in case["requirements"] if r["requirement_type"] == "party_organization_documents")
    verify = auth_client.post(f"/sales/readiness/requirements/{req['id']}/verify", json={"notes": "OK"})
    assert verify.status_code == 200
    waive_legal = next(r for r in case["requirements"] if r["requirement_type"] == "legal_review")
    sales_waive = auth_client.post(
        f"/sales/readiness/requirements/{waive_legal['id']}/waive",
        json={"reason": "Should fail for sales"},
    )
    assert sales_waive.status_code == 403


def _verify_all_mandatory(auth_client: TestClient, case_id: str) -> None:
    reqs = auth_client.get(f"/sales/readiness/cases/{case_id}/requirements").json()
    for req in reqs:
        if not req["is_mandatory"]:
            continue
        if req["status"] in {"verified", "waived", "not_applicable"}:
            continue
        response = auth_client.post(
            f"/sales/readiness/requirements/{req['id']}/verify",
            json={"notes": "Test verification"},
        )
        assert response.status_code == 200, response.text


def test_handoff_workflow(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Handoff Lead")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    case_id = case["id"]
    _verify_all_mandatory(auth_client, case_id)
    recalc = auth_client.post(f"/sales/readiness/cases/{case_id}/recalculate")
    assert recalc.status_code == 200, recalc.text
    _verify_all_mandatory(auth_client, case_id)
    request = auth_client.post(f"/sales/readiness/cases/{case_id}/handoff/request", json={"notes": "Ready"})
    assert request.status_code == 200, request.text
    approve = auth_client.post(f"/sales/readiness/cases/{case_id}/handoff/approve", json={})
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == ReadinessCaseStatus.HANDED_OFF.value


def test_handoff_return(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Return Lead")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    case_id = case["id"]
    _verify_all_mandatory(auth_client, case_id)
    auth_client.post(f"/sales/readiness/cases/{case_id}/handoff/request", json={})
    returned = auth_client.post(
        f"/sales/readiness/cases/{case_id}/handoff/return",
        json={"reason": "Missing finance review"},
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == ReadinessCaseStatus.BLOCKED.value


def test_contract_signed_requires_document(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Signed Lead")
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    fail = auth_client.post(f"/sales/readiness/cases/{case['id']}/contract-signed", json={})
    assert fail.status_code == 422


def test_dashboard_kpis(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@example.com")
    seed_default_template(db)
    db.commit()
    kpis = auth_client.get("/sales/readiness/dashboard/kpis")
    assert kpis.status_code == 200
    assert "active_cases" in kpis.json()


def test_global_search_readiness(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Search Lead")
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    search = auth_client.get(f"/search?q={case['case_code'][:10]}")
    assert search.status_code == 200
    assert search.json()["total"] >= 0


def test_activity_on_case_create(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Activity Lead")
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.SALES_READINESS,
            ActivityLog.entity_id == UUID(case["id"]),
        )
    ).all()
    assert len(logs) >= 1


def test_opportunity_summary(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Summary Lead")
    _login(auth_client, "sales@example.com")
    _create_readiness_case(auth_client, opp["id"], asset["id"])
    summary = auth_client.get(f"/sales/readiness/opportunities/{opp['id']}/summary")
    assert summary.status_code == 200
    assert summary.json() is not None


def test_follow_up_from_readiness(auth_client: TestClient, db: Session) -> None:
    seed_default_template(db)
    db.commit()
    opp, asset = _setup_opportunity_with_asset(auth_client, name="Followup Lead")
    _login(auth_client, "sales@example.com")
    case = _create_readiness_case(auth_client, opp["id"], asset["id"])
    follow = auth_client.post(
        f"/sales/readiness/cases/{case['id']}/follow-ups",
        json={"follow_up_type": "deposit_follow_up", "title": "Chase deposit"},
    )
    assert follow.status_code == 201
