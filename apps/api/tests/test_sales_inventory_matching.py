"""Sales inventory matching integration tests."""

from datetime import date, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventoryAsset,
    InventorySalesStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.lead import LeadStatus
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.models.sales import OpportunityInventory, OpportunityPartyType, SalesOpportunity
from investhome_api.models.sales_inventory_matching import (
    MatchRejectionReason,
    MatchRelationshipType,
    MatchStatus,
    SalesInventoryMatch,
    SalesInventoryPreference,
    SalesShortlist,
    SalesShortlistItem,
)
from investhome_api.services.search_service import global_search

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _create_lead(client: TestClient, *, name: str = "Match Lead") -> dict:
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


def _create_project(client: TestClient, *, code: str = "PRJ-MATCH-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Matching Test Project",
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
            "name": f"Tower {code}",
            "code": code,
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


def _create_asset(client: TestClient, project_id: str, *, display_id: str = "501") -> dict:
    building = _create_building(client, project_id, code=f"B{display_id}")
    floor = _create_floor(client, building["id"], floor_number=int(display_id) % 20 + 1)
    response = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": display_id,
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


def _create_opportunity(client: TestClient, lead_id: str) -> dict:
    response = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead_id,
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead_id,
            "expected_revenue": "400000.00",
            "currency": "USD",
            "probability": 30,
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_save_preferences_normalized(client: TestClient, db: Session) -> None:
    lead = _create_lead(client)
    project = _create_project(client)

    response = client.put(
        "/sales/inventory-preferences",
        json={
            "lead_id": lead["id"],
            "budget_min": "200000.00",
            "budget_max": "600000.00",
            "bedrooms_min": 2,
            "preferred_project_ids": [project["id"]],
            "preferred_asset_types": ["residential_unit"],
            "preferred_usage_types": ["residential"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["budget_min"] == "200000.00"
    assert project["id"] in data["preferred_project_ids"]

    pref = db.scalar(select(SalesInventoryPreference).where(SalesInventoryPreference.lead_id == UUID(lead["id"])))
    assert pref is not None


def test_manual_match_and_shortlist_crud(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Shortlist Lead")
    project = _create_project(client, code="PRJ-MATCH-002")
    asset_a = _create_asset(client, project["id"], display_id="502")
    asset_b = _create_asset(client, project["id"], display_id="503")

    match_resp = client.post(
        "/sales/inventory-matches",
        json={
            "lead_id": lead["id"],
            "inventory_asset_id": asset_a["id"],
            "relationship_type": MatchRelationshipType.MATCHED.value,
            "match_reason": "Budget fit",
        },
    )
    assert match_resp.status_code == 201
    match_id = match_resp.json()["id"]

    shortlist_resp = client.post(
        "/sales/shortlists",
        json={"lead_id": lead["id"], "title": "Top picks", "description": "Client favorites"},
    )
    assert shortlist_resp.status_code == 201
    shortlist_id = shortlist_resp.json()["id"]

    item_resp = client.post(
        f"/sales/shortlists/{shortlist_id}/items",
        json={"inventory_asset_id": asset_b["id"], "notes": "Great view", "is_favorite": True},
    )
    assert item_resp.status_code == 201

    dup_resp = client.post(f"/sales/shortlists/{shortlist_id}/items", json={"inventory_asset_id": asset_b["id"]})
    assert dup_resp.status_code == 422

    listed = client.get("/sales/shortlists", params={"lead_id": lead["id"]})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert len(listed.json()["items"][0]["items"]) == 1

    dup_list = client.post(f"/sales/shortlists/{shortlist_id}/duplicate")
    assert dup_list.status_code == 201
    assert dup_list.json()["title"].endswith("(copy)")

    assert db.scalar(select(SalesInventoryMatch).where(SalesInventoryMatch.id == UUID(match_id))) is not None
    assert db.scalar(select(SalesShortlistItem).where(SalesShortlistItem.shortlist_id == UUID(shortlist_id))) is not None


def test_favorite_reject_primary(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Primary Lead")
    opp = _create_opportunity(client, lead["id"])
    project = _create_project(client, code="PRJ-MATCH-003")
    asset_a = _create_asset(client, project["id"], display_id="504")
    asset_b = _create_asset(client, project["id"], display_id="505")

    match_a = client.post(
        "/sales/inventory-matches",
        json={
            "opportunity_id": opp["id"],
            "inventory_asset_id": asset_a["id"],
            "relationship_type": MatchRelationshipType.SHORTLISTED.value,
        },
    ).json()
    match_b = client.post(
        "/sales/inventory-matches",
        json={
            "opportunity_id": opp["id"],
            "inventory_asset_id": asset_b["id"],
            "relationship_type": MatchRelationshipType.MATCHED.value,
        },
    ).json()

    fav = client.post(f"/sales/inventory-matches/{match_a['id']}/favorite")
    assert fav.status_code == 200
    assert fav.json()["relationship_type"] == MatchRelationshipType.FAVORITE.value

    primary = client.post(f"/sales/inventory-matches/{match_a['id']}/set-primary")
    assert primary.status_code == 200
    assert primary.json()["is_primary"] is True

    other = db.get(SalesInventoryMatch, UUID(match_b["id"]))
    assert other is not None
    assert other.is_primary is False

    link = db.scalar(
        select(OpportunityInventory).where(
            OpportunityInventory.opportunity_id == UUID(opp["id"]),
            OpportunityInventory.inventory_asset_id == UUID(asset_a["id"]),
        )
    )
    assert link is not None
    assert link.is_primary is True

    reject = client.post(
        f"/sales/inventory-matches/{match_b['id']}/reject",
        json={"rejection_reason": MatchRejectionReason.BUDGET.value, "notes": "Too expensive"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == MatchStatus.REJECTED.value

    search = client.post(
        "/sales/inventory-matching/search",
        json={"opportunity_id": opp["id"], "project_id": project["id"], "exclude_rejected": True},
    )
    assert search.status_code == 200
    asset_ids = [item["asset_id"] for item in search.json()["items"]]
    assert asset_b["id"] not in asset_ids or all(
        item.get("relationship_type") != MatchRelationshipType.REJECTED.value
        for item in search.json()["items"]
        if item["asset_id"] == asset_b["id"]
    )


def test_rejected_excluded_from_default_matches(client: TestClient) -> None:
    lead = _create_lead(client, name="Reject Lead")
    project = _create_project(client, code="PRJ-MATCH-004")
    asset = _create_asset(client, project["id"], display_id="506")

    match = client.post(
        "/sales/inventory-matches",
        json={"lead_id": lead["id"], "inventory_asset_id": asset["id"]},
    ).json()
    client.post(
        f"/sales/inventory-matches/{match['id']}/reject",
        json={"rejection_reason": MatchRejectionReason.SIZE.value},
    )

    listed = client.get("/sales/inventory-matches", params={"lead_id": lead["id"], "exclude_rejected": True})
    assert listed.status_code == 200
    assert listed.json()["total"] == 0


def test_archived_inventory_rejected(client: TestClient) -> None:
    lead = _create_lead(client, name="Archived Asset Lead")
    project = _create_project(client, code="PRJ-MATCH-005")
    asset = _create_asset(client, project["id"], display_id="507")
    client.post(f"/inventory/assets/{asset['id']}/archive")

    response = client.post(
        "/sales/inventory-matches",
        json={"lead_id": lead["id"], "inventory_asset_id": asset["id"]},
    )
    assert response.status_code == 404


def test_compare_and_stale_check(client: TestClient, db: Session) -> None:
    project = _create_project(client, code="PRJ-MATCH-006")
    asset_a = _create_asset(client, project["id"], display_id="508")
    asset_b = _create_asset(client, project["id"], display_id="509")

    compare = client.post(
        "/sales/inventory-matching/compare",
        json={"asset_ids": [asset_a["id"], asset_b["id"]]},
    )
    assert compare.status_code == 200
    assert len(compare.json()["items"]) == 2

    stale = client.post(
        "/sales/inventory-matching/stale-check",
        json={
            "asset_ids": [asset_a["id"]],
            "snapshots": {
                asset_a["id"]: {
                    "availability_status": "unavailable",
                    "reservation_status": "none",
                    "list_price": "999999",
                }
            },
        },
    )
    assert stale.status_code == 200
    assert stale.json()["items"][0]["is_stale"] is True
    assert "availability_status" in stale.json()["items"][0]["stale_fields"]


def test_soft_hold_integration(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Hold Lead")
    project = _create_project(client, code="PRJ-MATCH-007")
    asset = _create_asset(client, project["id"], display_id="510")

    response = client.post(
        "/sales/inventory-matching/soft-hold",
        json={"inventory_asset_id": asset["id"], "lead_id": lead["id"], "notes": "Sales hold"},
    )
    assert response.status_code == 200
    assert response.json()["reservation_type"] == "soft_hold"

    updated_asset = db.get(InventoryAsset, UUID(asset["id"]))
    assert updated_asset is not None
    assert updated_asset.reservation_status.value == "soft_hold"


def test_activity_logged(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Activity Lead")
    project = _create_project(client, code="PRJ-MATCH-008")
    asset = _create_asset(client, project["id"], display_id="511")

    client.post(
        "/sales/inventory-matches",
        json={"lead_id": lead["id"], "inventory_asset_id": asset["id"]},
    )

    logs = list(db.scalars(select(ActivityLog).where(ActivityLog.description_key.like("activity.sales.inventory.%"))).all())
    assert any(log.description_key == "activity.sales.inventory.matched" for log in logs)


def test_global_search_shortlist(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Search Lead")
    created = client.post(
        "/sales/shortlists",
        json={"lead_id": lead["id"], "title": "Marina View Options"},
    )
    assert created.status_code == 201

    from investhome_api.models.user_auth import User, UserStatus
    from investhome_api.services.auth_service import hash_password
    from investhome_api.services.search_service import _search_sales_shortlists, SearchFilters

    user = db.scalar(select(User).limit(1))
    if user is None:
        user = User(
            email="search@test.com",
            full_name="Search User",
            status=UserStatus.ACTIVE,
            hashed_password=hash_password("Demo123!"),
        )
        db.add(user)
        db.flush()

    results = _search_sales_shortlists(db, user, "Marina View", SearchFilters(), 10)
    assert len(results) >= 1
    assert results[0].entity_type == "sales_shortlist"


def test_executive_matching_summary(client: TestClient) -> None:
    response = client.get("/sales/inventory-matching/executive-summary")
    assert response.status_code == 200
    body = response.json()
    assert "opportunities_without_match" in body
    assert "shortlisted_unavailable" in body


def test_permissions_enforced(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    denied = auth_client.post(
        "/sales/inventory-matches",
        json={"lead_id": "00000000-0000-0000-0000-000000000001", "inventory_asset_id": "00000000-0000-0000-0000-000000000002"},
    )
    assert denied.status_code == 403


def test_shortlist_reorder(client: TestClient) -> None:
    lead = _create_lead(client, name="Reorder Lead")
    project = _create_project(client, code="PRJ-MATCH-009")
    asset_a = _create_asset(client, project["id"], display_id="512")
    asset_b = _create_asset(client, project["id"], display_id="513")

    shortlist = client.post(
        "/sales/shortlists",
        json={"lead_id": lead["id"], "title": "Reorder test"},
    ).json()
    item_a = client.post(
        f"/sales/shortlists/{shortlist['id']}/items",
        json={"inventory_asset_id": asset_a["id"]},
    ).json()
    item_b = client.post(
        f"/sales/shortlists/{shortlist['id']}/items",
        json={"inventory_asset_id": asset_b["id"]},
    ).json()

    reordered = client.patch(
        f"/sales/shortlists/{shortlist['id']}/items/reorder",
        json={"item_ids": [item_b["id"], item_a["id"]]},
    )
    assert reordered.status_code == 200
    orders = [item["sort_order"] for item in reordered.json()["items"]]
    assert orders == [0, 1]
