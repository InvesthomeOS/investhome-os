"""Inventory assignment workflow integration tests."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog, ActivityAction
from investhome_api.models.inventory import (
    AssignmentRecordStatus,
    AssignmentRequestStatus,
    AvailabilityStatus,
    BuildingType,
    InventoryAssetAssignmentEvent,
    InventoryAssetAssignmentRequest,
    InventoryAssetType,
    InventorySalesStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.inventory.assignment_jobs import run_apply_scheduled_assignments


def _create_project(client: TestClient, *, code: str = "PRJ-ASG-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Assignment Test Project",
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


def _create_unit(client: TestClient, project_id: str, *, display_id: str = "12A") -> dict:
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


def _create_child_asset(
    client: TestClient,
    project_id: str,
    *,
    display_id: str,
    asset_type: str,
) -> dict:
    usage = (
        UsageType.PARKING.value
        if asset_type == InventoryAssetType.PARKING_SPACE.value
        else UsageType.STORAGE.value
    )
    response = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "display_id": display_id,
            "asset_type": asset_type,
            "usage_type": usage,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_asset(client: TestClient, project_id: str, *, display_id: str = "12A") -> dict:
    return _create_unit(client, project_id, display_id=display_id)


def _assignment_payload(child_id: str, parent_id: str, *, submit: bool = True) -> dict:
    return {
        "child_asset_id": child_id,
        "parent_asset_id": parent_id,
        "effective_date": date.today().isoformat(),
        "reason": "Link parking to unit",
        "assignment_price": "15000.00",
        "currency": "USD",
        "submit": submit,
    }


def test_initial_assignment_and_derivation(client: TestClient, db: Session):
    project = _create_project(client)
    unit = _create_asset(client, project["id"], display_id="12A")
    parking = _create_child_asset(
        client,
        project["id"],
        display_id="P-101",
        asset_type=InventoryAssetType.PARKING_SPACE.value,
    )

    created = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit["id"]))
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == AssignmentRequestStatus.SUBMITTED.value

    approved = client.post(f"/inventory/assignment-requests/{request_id}/approve", json={"comments": "OK"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == AssignmentRequestStatus.APPLIED.value

    current = client.get(f"/inventory/assignments/by-child/{parking['id']}/current")
    assert current.status_code == 200
    assert current.json()["parent_asset_id"] == unit["id"]
    assert current.json()["assignment_price"] == "15000.00"

    summary = client.get(f"/inventory/assignments/summary/by-asset/{parking['id']}")
    assert summary.json()["assignment_status"] == "assigned"
    assert summary.json()["assigned_to_display_id"] == "12A"

    parent_summary = client.get(f"/inventory/assignments/summary/by-asset/{unit['id']}")
    assert parent_summary.json()["parking_count"] == 1


def test_reassignment_closes_prior(client: TestClient, db: Session):
    project = _create_project(client)
    unit_a = _create_asset(client, project["id"], display_id="12A")
    unit_b = _create_asset(client, project["id"], display_id="12B")
    parking = _create_child_asset(
        client, project["id"], display_id="P-102", asset_type=InventoryAssetType.PARKING_SPACE.value
    )

    first = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit_a["id"]))
    client.post(f"/inventory/assignment-requests/{first.json()['id']}/approve", json={})

    second = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit_b["id"]))
    client.post(f"/inventory/assignment-requests/{second.json()['id']}/approve", json={})

    current = client.get(f"/inventory/assignments/by-child/{parking['id']}/current")
    assert current.json()["parent_asset_id"] == unit_b["id"]

    history = client.get(f"/inventory/assignments/by-child/{parking['id']}/history")
    assert len(history.json()) == 2
    historical = [row for row in history.json() if row["status"] == AssignmentRecordStatus.HISTORICAL.value]
    assert len(historical) == 1
    assert historical[0]["parent_asset_id"] == unit_a["id"]


def test_unassign_workflow(client: TestClient):
    project = _create_project(client)
    unit = _create_asset(client, project["id"])
    storage = _create_child_asset(
        client, project["id"], display_id="S-01", asset_type=InventoryAssetType.STORAGE_UNIT.value
    )

    initial = client.post("/inventory/assignment-requests", json=_assignment_payload(storage["id"], unit["id"]))
    client.post(f"/inventory/assignment-requests/{initial.json()['id']}/approve", json={})

    unassign = client.post(
        "/inventory/assignment-requests",
        json={
            "child_asset_id": storage["id"],
            "parent_asset_id": None,
            "request_type": "unassign",
            "effective_date": date.today().isoformat(),
            "reason": "Owner sold unit without storage",
            "submit": True,
        },
    )
    assert unassign.status_code == 201
    client.post(f"/inventory/assignment-requests/{unassign.json()['id']}/approve", json={})

    current = client.get(f"/inventory/assignments/by-child/{storage['id']}/current")
    assert current.json() is None


def test_stale_request_on_conflict(client: TestClient):
    project = _create_project(client)
    unit_a = _create_asset(client, project["id"], display_id="12A")
    unit_b = _create_asset(client, project["id"], display_id="12B")
    parking = _create_child_asset(
        client, project["id"], display_id="P-103", asset_type=InventoryAssetType.PARKING_SPACE.value
    )

    req_a = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit_a["id"]))
    req_b = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit_b["id"]))

    client.post(f"/inventory/assignment-requests/{req_a.json()['id']}/approve", json={})
    approve_b = client.post(f"/inventory/assignment-requests/{req_b.json()['id']}/approve", json={})
    assert approve_b.status_code == 409
    assert approve_b.json()["detail"] == "inventory.assignment.errors.stale_request"

    stale = client.get("/inventory/assignment-requests/stale")
    assert any(row["id"] == req_b.json()["id"] for row in stale.json())


def test_scheduled_assignment_job(client: TestClient, db: Session):
    project = _create_project(client)
    unit = _create_asset(client, project["id"])
    parking = _create_child_asset(
        client, project["id"], display_id="P-104", asset_type=InventoryAssetType.PARKING_SPACE.value
    )

    scheduled = client.post(
        "/inventory/assignment-requests",
        json={
            **_assignment_payload(parking["id"], unit["id"], submit=True),
            "effective_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    )
    approved = client.post(f"/inventory/assignment-requests/{scheduled.json()['id']}/approve", json={})
    assert approved.status_code == 200
    assert approved.json()["status"] == AssignmentRequestStatus.APPROVED.value

    before = client.get(f"/inventory/assignments/by-child/{parking['id']}/current")
    assert before.json() is None

    assignment_request = db.get(InventoryAssetAssignmentRequest, UUID(scheduled.json()["id"]))
    assignment_request.effective_date = date.today()
    db.commit()

    result = run_apply_scheduled_assignments()
    assert result["applied_count"] == 1

    after = client.get(f"/inventory/assignments/by-child/{parking['id']}/current")
    assert after.json() is not None


def test_self_assignment_rejected(client: TestClient):
    project = _create_project(client)
    parking = _create_child_asset(
        client, project["id"], display_id="P-105", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    response = client.post(
        "/inventory/assignment-requests",
        json=_assignment_payload(parking["id"], parking["id"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "inventory.assignment.errors.self_assignment"


def test_invalid_parent_type(client: TestClient):
    project = _create_project(client)
    parking_a = _create_child_asset(
        client, project["id"], display_id="P-106", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    parking_b = _create_child_asset(
        client, project["id"], display_id="P-107", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    response = client.post(
        "/inventory/assignment-requests",
        json=_assignment_payload(parking_a["id"], parking_b["id"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "inventory.assignment.errors.invalid_parent_type"


def test_assignment_events_and_activity(client: TestClient, db: Session):
    project = _create_project(client)
    unit = _create_asset(client, project["id"])
    parking = _create_child_asset(
        client, project["id"], display_id="P-108", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    req = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit["id"]))
    client.post(f"/inventory/assignment-requests/{req.json()['id']}/approve", json={})

    events = db.scalars(
        select(InventoryAssetAssignmentEvent).where(
            InventoryAssetAssignmentEvent.child_asset_id == UUID(parking["id"])
        )
    ).all()
    assert any(e.event_type == "inventory.assignment.assigned" for e in events)

    logs = db.scalars(select(ActivityLog).where(ActivityLog.action == ActivityAction.APPROVED)).all()
    assert logs


def test_parent_accessories_list(client: TestClient):
    project = _create_project(client)
    unit = _create_asset(client, project["id"])
    parking = _create_child_asset(
        client, project["id"], display_id="P-109", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    storage = _create_child_asset(
        client, project["id"], display_id="S-109", asset_type=InventoryAssetType.STORAGE_UNIT.value
    )

    for child in (parking, storage):
        req = client.post("/inventory/assignment-requests", json=_assignment_payload(child["id"], unit["id"]))
        client.post(f"/inventory/assignment-requests/{req.json()['id']}/approve", json={})

    accessories = client.get(f"/inventory/assignments/by-parent/{unit['id']}")
    assert len(accessories.json()) == 2


def test_pending_approvals_endpoint(client: TestClient):
    project = _create_project(client)
    unit = _create_asset(client, project["id"])
    parking = _create_child_asset(
        client, project["id"], display_id="P-110", asset_type=InventoryAssetType.PARKING_SPACE.value
    )
    req = client.post("/inventory/assignment-requests", json=_assignment_payload(parking["id"], unit["id"]))
    pending = client.get("/inventory/assignment-requests/pending-approvals")
    assert any(row["id"] == req.json()["id"] for row in pending.json())
