"""Inventory foundation integration tests."""

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    ConstructionStatus,
    InventoryAssetType,
    InventorySalesStatus,
    StatusCategory,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


def _create_project(client: TestClient, *, code: str = "PRJ-INV-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Inventory Test Project",
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


def _create_asset(
    client: TestClient,
    *,
    project_id: str,
    building_id: str | None = None,
    floor_id: str | None = None,
    display_id: str = "301",
    asset_type: str = InventoryAssetType.RESIDENTIAL_UNIT.value,
    usage_type: str = UsageType.RESIDENTIAL.value,
) -> dict:
    payload: dict = {
        "project_id": project_id,
        "display_id": display_id,
        "asset_type": asset_type,
        "usage_type": usage_type,
        "interior_area_sqft": "980.00",
        "availability_status": AvailabilityStatus.AVAILABLE.value,
        "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
        "construction_status": ConstructionStatus.INTERIOR.value,
    }
    if building_id is not None:
        payload["building_id"] = building_id
    if floor_id is not None:
        payload["floor_id"] = floor_id
    response = client.post("/inventory/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_building_crud(client: TestClient) -> None:
    project = _create_project(client)
    building = _create_building(client, project["id"])
    building_id = building["id"]

    listed = client.get("/inventory/buildings", params={"project_id": project["id"]})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(f"/inventory/buildings/{building_id}")
    assert detail.status_code == 200
    assert detail.json()["code"] == "A"

    updated = client.patch(
        f"/inventory/buildings/{building_id}",
        json={"name": "Tower A Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Tower A Updated"

    archived = client.post(f"/inventory/buildings/{building_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    restored = client.post(f"/inventory/buildings/{building_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_floor_crud_and_duplicate_rejection(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-INV-002")
    building = _create_building(client, project["id"], code="B")
    floor = _create_floor(client, building["id"], floor_number=3)
    floor_id = floor["id"]

    duplicate = client.post(
        "/inventory/floors",
        json={
            "building_id": building["id"],
            "floor_number": 3,
            "level_code": "99",
            "sort_order": 99,
        },
    )
    assert duplicate.status_code == 409

    listed = client.get("/inventory/floors", params={"building_id": building["id"]})
    assert listed.json()["total"] == 1

    archived = client.post(f"/inventory/floors/{floor_id}/archive")
    assert archived.status_code == 200

    restored = client.post(f"/inventory/floors/{floor_id}/restore")
    assert restored.status_code == 200


def test_asset_crud_system_code_and_filters(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-TEMP-TEST")
    building = _create_building(client, project["id"], code="A")
    floor = _create_floor(client, building["id"], floor_number=3)
    asset = _create_asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        display_id="301",
    )
    asset_id = asset["id"]

    assert asset["system_code"].startswith("TEM-")
    assert "301" in asset["system_code"]
    assert asset["system_code"] == asset["system_code"].upper()

    filtered = client.get(
        "/inventory/assets",
        params={
            "project_id": project["id"],
            "availability_status": AvailabilityStatus.AVAILABLE.value,
        },
    )
    assert filtered.json()["total"] == 1

    searched = client.get("/inventory/assets", params={"search": "301"})
    assert searched.json()["total"] == 1

    updated = client.patch(
        f"/inventory/assets/{asset_id}",
        json={"description": "Corner unit with terrace"},
    )
    assert updated.status_code == 200

    archived = client.post(f"/inventory/assets/{asset_id}/archive")
    assert archived.status_code == 200

    restored = client.post(f"/inventory/assets/{asset_id}/restore")
    assert restored.status_code == 200


def test_conditional_validation_rules(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-INV-VAL")
    building = _create_building(client, project["id"], code="V")

    missing_floor = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "display_id": "NOFLOOR",
            "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
            "usage_type": UsageType.RESIDENTIAL.value,
        },
    )
    assert missing_floor.status_code == 422
    assert missing_floor.json()["detail"] == "inventory.errors.floor_required"

    land_with_building = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "display_id": "LAND-1",
            "asset_type": InventoryAssetType.LAND_PARCEL.value,
            "usage_type": UsageType.MIXED.value,
        },
    )
    assert land_with_building.status_code == 422
    assert land_with_building.json()["detail"] == "inventory.errors.land_parcel_no_structure"

    parking_ok = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "display_id": "P-1",
            "asset_type": InventoryAssetType.PARKING_SPACE.value,
            "usage_type": UsageType.PARKING.value,
        },
    )
    assert parking_ok.status_code == 201


def test_status_update_and_history(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-INV-STAT")
    building = _create_building(client, project["id"], code="S")
    floor = _create_floor(client, building["id"], floor_number=5)
    asset = _create_asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        display_id="501",
    )

    status_response = client.post(
        f"/inventory/assets/{asset['id']}/status",
        json={
            "status_category": StatusCategory.CONSTRUCTION.value,
            "new_status": ConstructionStatus.READY.value,
            "reason": "Inspection passed",
        },
    )
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["new_status"] == ConstructionStatus.READY.value
    assert body["previous_status"] == ConstructionStatus.INTERIOR.value

    history = client.get(f"/inventory/assets/{asset['id']}/status-history")
    assert history.status_code == 200
    assert len(history.json()) == 1

    unchanged = client.post(
        f"/inventory/assets/{asset['id']}/status",
        json={
            "status_category": StatusCategory.CONSTRUCTION.value,
            "new_status": ConstructionStatus.READY.value,
        },
    )
    assert unchanged.status_code == 422


def test_display_id_duplicate_rejection(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-INV-DUP")
    building = _create_building(client, project["id"], code="D")
    floor = _create_floor(client, building["id"], floor_number=1)
    _create_asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        display_id="101",
    )

    duplicate = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": "101",
            "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
            "usage_type": UsageType.RESIDENTIAL.value,
        },
    )
    assert duplicate.status_code == 409


def test_global_search_inventory_entities(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-INV-SRCH")
    building = _create_building(client, project["id"], code="SR")
    floor = _create_floor(client, building["id"], floor_number=7)
    asset = _create_asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        display_id="7SRCH",
    )

    for entity_type, query in [
        ("building", "Tower A"),
        ("floor", "Level 7"),
        ("inventory_asset", asset["system_code"]),
    ]:
        response = client.get("/search", params={"q": query, "entity_types": entity_type})
        assert response.status_code == 200
        groups = {group["entity_type"]: group for group in response.json()["groups"]}
        assert entity_type in groups
        assert groups[entity_type]["total"] >= 1


def test_inventory_permissions(auth_client: TestClient) -> None:
    from tests.test_auth import DEMO_PASSWORD, _login

    _login(auth_client, "admin@example.com")
    project_response = auth_client.post(
        "/projects",
        json={
            "project_code": "PRJ-AUTH-INV",
            "project_name": "Auth Inventory Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    _login(auth_client, "readonly@example.com")
    denied = auth_client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": "Denied Tower",
            "code": "X",
            "building_type": BuildingType.APARTMENT.value,
        },
    )
    assert denied.status_code == 403

    _login(auth_client, "sales@example.com")
    allowed = auth_client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": "Sales Tower",
            "code": "S",
            "building_type": BuildingType.APARTMENT.value,
        },
    )
    assert allowed.status_code == 201

    _login(auth_client, "readonly@example.com")
    view_ok = auth_client.get("/inventory/buildings")
    assert view_ok.status_code == 200
