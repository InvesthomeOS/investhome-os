"""Inventory ownership workflow integration tests."""

import io
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog, ActivityAction, ActivityEntityType
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventoryAssetType,
    InventoryOwnership,
    InventoryOwnershipEvent,
    InventorySalesStatus,
    OwnershipRecordStatus,
    OwnershipTransferRequest,
    StructureStatus,
    TransferRequestStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.inventory.ownership_jobs import run_apply_scheduled_transfers
from investhome_api.services.inventory.ownership_service import sum_active_legal_percentages


def _create_project(client: TestClient, *, code: str = "PRJ-OWN-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Ownership Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_investor(client: TestClient, *, name: str = "Owner One", email: str | None = None) -> dict:
    response = client.post(
        "/investors",
        json={
            "full_name": name,
            "email": email or f"{uuid4().hex[:8]}@example.com",
            "investor_type": "individual",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_building(client: TestClient, project_id: str, *, code: str = "A") -> dict:
    response = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": "Tower A",
            "code": code,
            "building_type": BuildingType.APARTMENT.value,
            "total_floors": 10,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201
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
    assert response.status_code == 201
    return response.json()


def _create_asset(client: TestClient, project_id: str, *, display_id: str = "12A") -> dict:
    building = _create_building(client, project_id, code=f"B-{display_id}")
    floor = _create_floor(client, building["id"])
    response = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": display_id,
            "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
            "usage_type": UsageType.RESIDENTIAL.value,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload_supporting_document(client: TestClient) -> str:
    files = {"files": ("ownership-deed.txt", io.BytesIO(b"Supporting ownership document"), "text/plain")}
    response = client.post("/documents/upload", files=files, data={"title": "Ownership deed"})
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["results"][0]["success"] is True
    return payload["results"][0]["document"]["id"]


def _initial_ownership_payload(asset_id: str, party_id: str, *, submit: bool = True) -> dict:
    return {
        "inventory_asset_id": asset_id,
        "transfer_type": "initial_ownership",
        "effective_date": date.today().isoformat(),
        "reason": "Initial closing record",
        "parties": [
            {
                "party_id": party_id,
                "ownership_type": "legal_owner",
                "proposed_percentage": "100",
                "role": "incoming_owner",
            }
        ],
        "submit": submit,
    }


def test_initial_ownership_and_derivation(client: TestClient, db: Session):
    project = _create_project(client)
    asset = _create_asset(client, project["id"])
    owner = _create_investor(client)

    created = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == TransferRequestStatus.SUBMITTED.value

    approved = client.post(f"/inventory/ownership-transfers/{request_id}/approve", json={"comments": "OK"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == TransferRequestStatus.APPLIED.value

    current = client.get(f"/inventory/ownership/by-asset/{asset['id']}/current")
    assert current.status_code == 200
    assert len(current.json()) == 1
    assert current.json()[0]["ownership_percentage"] == "100.0000"
    assert current.json()[0]["status"] == OwnershipRecordStatus.ACTIVE.value

    summary = client.get(f"/inventory/ownership/summary/by-asset/{asset['id']}")
    assert summary.status_code == 200
    assert summary.json()["owner_count"] == 1
    assert summary.json()["ownership_status"] == "complete"

    active = db.scalars(
        select(InventoryOwnership).where(
            InventoryOwnership.inventory_asset_id == UUID(asset["id"])
        )
    ).all()
    assert sum_active_legal_percentages(active) == Decimal("100")


def test_partial_transfer_closes_prior_records(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-002")
    asset = _create_asset(client, project["id"], display_id="12B")
    owner1 = _create_investor(client, name="Owner Alpha")
    owner2 = _create_investor(client, name="Owner Beta")

    initial = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner1["id"]))
    initial_id = initial.json()["id"]
    client.post(f"/inventory/ownership-transfers/{initial_id}/approve", json={})

    document_id = _upload_supporting_document(client)
    partial = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "partial_transfer",
            "effective_date": date.today().isoformat(),
            "reason": "Co-buyer added",
            "supporting_document_id": document_id,
            "parties": [
                {
                    "party_id": owner1["id"],
                    "ownership_type": "legal_owner",
                    "previous_percentage": "100",
                    "proposed_percentage": "50",
                    "role": "continuing_owner",
                },
                {
                    "party_id": owner2["id"],
                    "ownership_type": "legal_owner",
                    "proposed_percentage": "50",
                    "role": "incoming_owner",
                },
            ],
            "submit": True,
        },
    )
    assert partial.status_code == 201, partial.text
    partial_id = partial.json()["id"]
    approved = client.post(f"/inventory/ownership-transfers/{partial_id}/approve", json={})
    assert approved.status_code == 200, approved.text

    current = client.get(f"/inventory/ownership/by-asset/{asset['id']}/current")
    assert len(current.json()) == 2
    history = client.get(f"/inventory/ownership/by-asset/{asset['id']}/history")
    assert len(history.json()) >= 3
    historical = [r for r in history.json() if r["status"] == OwnershipRecordStatus.HISTORICAL.value]
    assert len(historical) >= 1


def test_rejected_transfer_does_not_change_ownership(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-003")
    asset = _create_asset(client, project["id"], display_id="12C")
    owner = _create_investor(client, name="Solo Owner")
    other = _create_investor(client, name="Rejected Buyer")

    initial = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    client.post(f"/inventory/ownership-transfers/{initial.json()['id']}/approve", json={})

    document_id = _upload_supporting_document(client)
    bad = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "partial_transfer",
            "effective_date": date.today().isoformat(),
            "reason": "Should fail",
            "supporting_document_id": document_id,
            "parties": [
                {
                    "party_id": owner["id"],
                    "ownership_type": "legal_owner",
                    "previous_percentage": "100",
                    "proposed_percentage": "50",
                    "role": "continuing_owner",
                },
                {
                    "party_id": other["id"],
                    "ownership_type": "legal_owner",
                    "proposed_percentage": "50",
                    "role": "incoming_owner",
                },
            ],
            "submit": True,
        },
    )
    rejected = client.post(
        f"/inventory/ownership-transfers/{bad.json()['id']}/reject",
        json={"decision_notes": "Not approved"},
    )
    assert rejected.status_code == 200

    current = client.get(f"/inventory/ownership/by-asset/{asset['id']}/current")
    assert len(current.json()) == 1
    assert current.json()[0]["party_id"] == owner["id"]


def test_stale_request_on_competing_approval(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-004")
    asset = _create_asset(client, project["id"], display_id="12D")
    owner = _create_investor(client)
    buyer_a = _create_investor(client, name="Buyer A")
    buyer_b = _create_investor(client, name="Buyer B")

    initial = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    client.post(f"/inventory/ownership-transfers/{initial.json()['id']}/approve", json={})

    document_a = _upload_supporting_document(client)
    req_a = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "partial_transfer",
            "effective_date": date.today().isoformat(),
            "reason": "Offer A",
            "supporting_document_id": document_a,
            "parties": [
                {"party_id": owner["id"], "ownership_type": "legal_owner", "previous_percentage": "100", "proposed_percentage": "50", "role": "continuing_owner"},
                {"party_id": buyer_a["id"], "ownership_type": "legal_owner", "proposed_percentage": "50", "role": "incoming_owner"},
            ],
            "submit": True,
        },
    )
    document_b = _upload_supporting_document(client)
    req_b = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "partial_transfer",
            "effective_date": date.today().isoformat(),
            "reason": "Offer B",
            "supporting_document_id": document_b,
            "parties": [
                {"party_id": owner["id"], "ownership_type": "legal_owner", "previous_percentage": "100", "proposed_percentage": "50", "role": "continuing_owner"},
                {"party_id": buyer_b["id"], "ownership_type": "legal_owner", "proposed_percentage": "50", "role": "incoming_owner"},
            ],
            "submit": True,
        },
    )

    approve_a = client.post(f"/inventory/ownership-transfers/{req_a.json()['id']}/approve", json={})
    assert approve_a.status_code == 200

    approve_b = client.post(f"/inventory/ownership-transfers/{req_b.json()['id']}/approve", json={})
    assert approve_b.status_code == 409
    assert approve_b.json()["detail"] == "inventory.ownership.errors.stale_request"

    stale = client.get("/inventory/ownership-transfers/stale")
    assert any(item["id"] == req_b.json()["id"] for item in stale.json())


def test_future_dated_scheduled_transfer(client: TestClient, db: Session):
    project = _create_project(client, code="PRJ-OWN-005")
    asset = _create_asset(client, project["id"], display_id="12E")
    owner = _create_investor(client)
    buyer = _create_investor(client, name="Future Buyer")
    future = (date.today() + timedelta(days=7)).isoformat()

    initial = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    client.post(f"/inventory/ownership-transfers/{initial.json()['id']}/approve", json={})

    document_id = _upload_supporting_document(client)
    scheduled = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "partial_transfer",
            "effective_date": future,
            "reason": "Future co-buyer",
            "supporting_document_id": document_id,
            "parties": [
                {"party_id": owner["id"], "ownership_type": "legal_owner", "previous_percentage": "100", "proposed_percentage": "50", "role": "continuing_owner"},
                {"party_id": buyer["id"], "ownership_type": "legal_owner", "proposed_percentage": "50", "role": "incoming_owner"},
            ],
            "submit": True,
        },
    )
    approved = client.post(f"/inventory/ownership-transfers/{scheduled.json()['id']}/approve", json={})
    assert approved.status_code == 200
    assert approved.json()["status"] == TransferRequestStatus.APPROVED.value

    current_before = client.get(f"/inventory/ownership/by-asset/{asset['id']}/current")
    assert len(current_before.json()) == 1

    transfer = db.get(OwnershipTransferRequest, UUID(scheduled.json()["id"]))
    transfer.effective_date = date.today()
    db.commit()

    result = run_apply_scheduled_transfers()
    assert result["applied_count"] == 1

    current_after = client.get(f"/inventory/ownership/by-asset/{asset['id']}/current")
    assert len(current_after.json()) == 2


def test_invalid_legal_total_blocked(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-006")
    asset = _create_asset(client, project["id"], display_id="12F")
    owner = _create_investor(client)

    response = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "initial_ownership",
            "effective_date": date.today().isoformat(),
            "reason": "Bad total",
            "parties": [
                {
                    "party_id": owner["id"],
                    "ownership_type": "legal_owner",
                    "proposed_percentage": "60",
                    "role": "incoming_owner",
                }
            ],
            "submit": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "inventory.ownership.errors.legal_total_invalid"


def test_archived_party_rejected(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-007")
    asset = _create_asset(client, project["id"], display_id="12G")
    owner = _create_investor(client)
    client.delete(f"/investors/{owner['id']}")

    response = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    assert response.status_code == 404
    assert response.json()["detail"] == "inventory.ownership.errors.party_not_found"


def test_beneficial_ownership_separate(client: TestClient):
    project = _create_project(client, code="PRJ-OWN-008")
    asset = _create_asset(client, project["id"], display_id="12H")
    legal = _create_investor(client, name="Legal Owner")
    beneficial = _create_investor(client, name="Beneficial Owner")

    legal_req = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], legal["id"]))
    client.post(f"/inventory/ownership-transfers/{legal_req.json()['id']}/approve", json={})

    bene_req = client.post(
        "/inventory/ownership-transfers",
        json={
            "inventory_asset_id": asset["id"],
            "transfer_type": "owner_addition",
            "effective_date": date.today().isoformat(),
            "reason": "Beneficial interest",
            "parties": [
                {
                    "party_id": beneficial["id"],
                    "ownership_type": "beneficial_owner",
                    "proposed_percentage": "100",
                    "role": "incoming_owner",
                }
            ],
            "submit": True,
        },
    )
    client.post(f"/inventory/ownership-transfers/{bene_req.json()['id']}/approve", json={})

    detail = client.get(f"/inventory/ownership/by-asset/{asset['id']}/detail")
    assert len(detail.json()["current_legal"]) == 1
    assert len(detail.json()["current_beneficial"]) == 1


def test_activity_and_events_on_approve(client: TestClient, db: Session):
    project = _create_project(client, code="PRJ-OWN-009")
    asset = _create_asset(client, project["id"], display_id="12I")
    owner = _create_investor(client)

    req = client.post("/inventory/ownership-transfers", json=_initial_ownership_payload(asset["id"], owner["id"]))
    client.post(f"/inventory/ownership-transfers/{req.json()['id']}/approve", json={})

    events = db.scalars(select(InventoryOwnershipEvent)).all()
    assert any(e.event_type == "inventory.ownership.transferred" for e in events)

    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.INVENTORY_OWNERSHIP,
            ActivityLog.action == ActivityAction.APPROVED,
        )
    ).all()
    assert len(logs) >= 1
