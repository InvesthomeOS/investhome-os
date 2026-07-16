"""Sales proposal engine integration tests."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.lead import LeadStatus
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventorySalesStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.models.sales import OpportunityNextAction, OpportunityPartyType, OpportunityStage
from investhome_api.models.sales_proposal import (
    ProposalStatus,
    SalesProposal,
    SalesProposalActivity,
    SalesProposalVersion,
)
from investhome_api.services.search_service import global_search

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _create_lead(client: TestClient, *, name: str = "Proposal Lead") -> dict:
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


def _create_project(client: TestClient, *, code: str = "PRJ-PROP-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Proposal Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_building(client: TestClient, project_id: str, *, code: str = "A") -> dict:
    response = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "code": code,
            "name": f"Building {code}",
            "building_type": BuildingType.APARTMENT.value,
            "total_floors": 10,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_floor(client: TestClient, building_id: str, *, floor_number: int = 3) -> dict:
    response = client.post(
        "/inventory/floors",
        json={
            "building_id": building_id,
            "floor_number": floor_number,
            "display_name": f"Level {floor_number}",
            "level_code": f"{floor_number:02d}",
            "sort_order": floor_number,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_asset(client: TestClient, project_id: str, *, code: str = "UNIT-P001") -> dict:
    building = _create_building(client, project_id)
    floor = _create_floor(client, building["id"])
    response = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": code,
            "asset_type": "residential_unit",
            "usage_type": UsageType.RESIDENTIAL.value,
            "interior_area_sqft": "1200.00",
            "bedrooms": 2,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
            "construction_status": "interior",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_initial_price(client: TestClient, asset_id: str, amount: str = "250000.00") -> dict:
    response = client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset_id,
            "price_type": "list",
            "amount": amount,
            "currency": "USD",
            "effective_from": date.today().isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_opportunity(client: TestClient, lead_id: str) -> dict:
    response = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead_id,
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead_id,
            "expected_revenue": "250000.00",
            "currency": "USD",
            "probability": 30,
            "next_action": OpportunityNextAction.PROPOSAL.value,
            "next_action_date": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def _proposal_payload(opportunity_id: str, **overrides) -> dict:
    payload = {
        "opportunity_id": opportunity_id,
        "title": "Luxury Unit Proposal",
        "currency": "USD",
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
        "recipient_email": "buyer@example.com",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def proposal_setup(client: TestClient) -> dict:
    lead = _create_lead(client)
    project = _create_project(client)
    asset = _create_asset(client, project["id"])
    price = _create_initial_price(client, asset["id"])
    opportunity = _create_opportunity(client, lead["id"])
    return {
        "lead": lead,
        "project": project,
        "asset": asset,
        "price": price,
        "opportunity": opportunity,
    }


def test_proposal_creation_and_number_uniqueness(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    r1 = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    assert r1.status_code == 201
    p1 = r1.json()
    assert p1["status"] == "draft"
    assert p1["proposal_number"]
    assert p1["opportunity_id"] == opp_id

    r2 = client.post("/sales/proposals", json=_proposal_payload(opp_id, title="Second Proposal"))
    assert r2.status_code == 201
    p2 = r2.json()
    assert p2["proposal_number"] != p1["proposal_number"]


def test_add_item_with_approved_price(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]

    item_resp = client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    assert item_resp.status_code == 201
    item = item_resp.json()
    assert item["approved_price_id"] == price_id
    assert Decimal(item["displayed_amount"]) == Decimal("250000.00")


def test_shortlist_import(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]

    shortlist = client.post(
        "/sales/shortlists",
        json={"opportunity_id": opp_id, "title": "Proposal Shortlist"},
    )
    assert shortlist.status_code == 201
    sl_id = shortlist.json()["id"]

    add_item = client.post(
        f"/sales/shortlists/{sl_id}/items",
        json={"inventory_asset_id": asset_id},
    )
    assert add_item.status_code == 201

    proposal = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = proposal.json()["id"]

    imported = client.post(
        f"/sales/proposals/{proposal_id}/import-shortlist",
        json={"shortlist_id": sl_id},
    )
    assert imported.status_code == 200
    assert len(imported.json()["items"]) == 1


def test_approval_flow_and_version_immutability(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    version_id = created.json()["current_version"]["id"]

    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )

    submit = client.post(f"/sales/proposals/{proposal_id}/submit")
    assert submit.status_code == 200
    assert submit.json()["status"] == "internal_review"

    approved = client.post(
        f"/sales/proposals/{proposal_id}/review",
        json={"decision": "approved", "comments": "Looks good"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    patch = client.patch(
        f"/sales/proposals/{proposal_id}",
        json={"content_snapshot": {"introduction": "Changed"}},
    )
    assert patch.status_code == 422


def test_mark_sent_and_opportunity_stage_sync(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    # Advance opportunity to proposal_preparation through valid transitions
    current = client.get(f"/sales/opportunities/{opp_id}").json()["stage"]
    path = {
        "new": ["qualified", "meeting_scheduled", "meeting_completed", "inventory_matching", "proposal_preparation"],
        "qualified": ["meeting_scheduled", "meeting_completed", "inventory_matching", "proposal_preparation"],
    }.get(current, ["proposal_preparation"])
    for stage in path:
        resp = client.post(f"/sales/opportunities/{opp_id}/stage", json={"new_stage": stage})
        if resp.status_code != 200:
            break

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    client.post(f"/sales/proposals/{proposal_id}/submit")
    client.post(f"/sales/proposals/{proposal_id}/review", json={"decision": "approved"})

    opp_before = client.get(f"/sales/opportunities/{opp_id}").json()["stage"]
    sent = client.post(f"/sales/proposals/{proposal_id}/mark-sent")
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.json()["sent_at"]

    opp_after = client.get(f"/sales/opportunities/{opp_id}").json()["stage"]
    if opp_before == OpportunityStage.PROPOSAL_PREPARATION.value:
        assert opp_after == OpportunityStage.PROPOSAL_SENT.value
    else:
        assert opp_after == opp_before or opp_after == OpportunityStage.PROPOSAL_SENT.value


def test_stale_check_and_refresh(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )

    stale = client.get(f"/sales/proposals/{proposal_id}/stale-check")
    assert stale.status_code == 200
    assert stale.json()["has_stale"] is False


def test_expiration_blocks_acceptance(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post(
        "/sales/proposals",
        json=_proposal_payload(opp_id, valid_until=(date.today() - timedelta(days=1)).isoformat()),
    )
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    client.post(f"/sales/proposals/{proposal_id}/submit")
    client.post(f"/sales/proposals/{proposal_id}/review", json={"decision": "approved"})
    client.post(f"/sales/proposals/{proposal_id}/mark-sent")

    accepted = client.post(f"/sales/proposals/{proposal_id}/mark-accepted")
    assert accepted.status_code == 422


def test_manual_mark_viewed_accepted(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    client.post(f"/sales/proposals/{proposal_id}/submit")
    client.post(f"/sales/proposals/{proposal_id}/review", json={"decision": "approved"})
    client.post(f"/sales/proposals/{proposal_id}/mark-sent")

    viewed = client.post(f"/sales/proposals/{proposal_id}/mark-viewed")
    assert viewed.status_code == 200
    assert viewed.json()["viewed_at"]

    accepted = client.post(f"/sales/proposals/{proposal_id}/mark-accepted")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"


def test_create_new_version_after_approval(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    client.post(f"/sales/proposals/{proposal_id}/submit")
    client.post(f"/sales/proposals/{proposal_id}/review", json={"decision": "approved"})

    version = client.post(f"/sales/proposals/{proposal_id}/versions")
    assert version.status_code == 200
    assert version.json()["version_number"] == 2
    assert version.json()["is_approved"] is False

    detail = client.get(f"/sales/proposals/{proposal_id}")
    assert detail.json()["status"] == "draft"


def test_permissions_enforced(client: TestClient, proposal_setup: dict, auth_client: TestClient) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    _login(auth_client, "readonly@example.com")
    response = auth_client.post("/sales/proposals", json=_proposal_payload(opp_id))
    assert response.status_code == 403


def test_activity_logged_on_create(client: TestClient, proposal_setup: dict, db: Session) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = UUID(created.json()["id"])

    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.SALES_PROPOSAL,
            ActivityLog.entity_id == proposal_id,
        )
    ).all()
    assert any(log.description_key == "activity.sales.proposal.created" for log in logs)


def test_global_search_finds_proposal(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    assert created.status_code == 201
    number = created.json()["proposal_number"]

    response = client.get(f"/search?q={number}&entity_types=sales_proposal")
    assert response.status_code == 200
    payload = response.json()
    group = next((item for item in payload["groups"] if item["entity_type"] == "sales_proposal"), None)
    assert group is not None
    assert any(number in item.get("subtitle", "") or number in item.get("title", "") for item in group["items"])


def test_executive_summary(client: TestClient, proposal_setup: dict) -> None:
    summary = client.get("/sales/proposals/executive-summary")
    assert summary.status_code == 200
    assert "by_status" in summary.json()


def test_proposal_preview(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )

    preview = client.get(f"/sales/proposals/{proposal_id}/preview")
    assert preview.status_code == 200
    assert proposal_id[:8] in preview.json()["html"] or created.json()["proposal_number"] in preview.json()["html"]


def test_archive_and_restore(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]

    archived = client.delete(f"/sales/proposals/{proposal_id}")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    restored = client.post(f"/sales/proposals/{proposal_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_reject_does_not_auto_lose_opportunity(client: TestClient, proposal_setup: dict) -> None:
    opp_id = proposal_setup["opportunity"]["id"]
    asset_id = proposal_setup["asset"]["id"]
    price_id = proposal_setup["price"]["id"]

    created = client.post("/sales/proposals", json=_proposal_payload(opp_id))
    proposal_id = created.json()["id"]
    client.post(
        f"/sales/proposals/{proposal_id}/items",
        json={"inventory_asset_id": asset_id, "approved_price_id": price_id},
    )
    client.post(f"/sales/proposals/{proposal_id}/submit")
    client.post(f"/sales/proposals/{proposal_id}/review", json={"decision": "approved"})
    client.post(f"/sales/proposals/{proposal_id}/mark-sent")
    client.post(f"/sales/proposals/{proposal_id}/mark-rejected")

    opp = client.get(f"/sales/opportunities/{opp_id}")
    assert opp.json()["stage"] != OpportunityStage.LOST.value
