"""Building-level unit identity and sales market allocation."""

from fastapi.testclient import TestClient

from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventoryAssetType,
    InventorySalesStatus,
    StatusCategory,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": "PRJ-MKT-201",
            "project_name": "Market Identity",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_building(client: TestClient, project_id: str, *, code: str, name: str) -> dict:
    response = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": name,
            "code": code,
            "building_type": BuildingType.APARTMENT.value,
            "total_floors": 6,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_floor(client: TestClient, building_id: str) -> dict:
    response = client.post(
        "/inventory/floors",
        json={
            "building_id": building_id,
            "floor_number": 2,
            "display_name": "Level 2",
            "level_code": "02",
            "sort_order": 2,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _unit_payload(**overrides: object) -> dict:
    payload: dict = {
        "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
        "usage_type": UsageType.RESIDENTIAL.value,
        "availability_status": AvailabilityStatus.AVAILABLE.value,
        "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
    }
    payload.update(overrides)
    return payload


def test_repeated_unit_numbers_are_unique_per_building(client: TestClient) -> None:
    project = _create_project(client)
    historic = _create_building(client, project["id"], code="HIST", name="Historic")
    addition = _create_building(client, project["id"], code="ADD", name="Addition")
    historic_floor = _create_floor(client, historic["id"])
    addition_floor = _create_floor(client, addition["id"])

    first = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=historic["id"],
            floor_id=historic_floor["id"],
            display_id="201",
            sales_market="turkey",
        ),
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=addition["id"],
            floor_id=addition_floor["id"],
            display_id="201",
            sales_market="usa",
            sales_status=InventorySalesStatus.SOLD.value,
            availability_status=AvailabilityStatus.UNAVAILABLE.value,
        ),
    )
    assert second.status_code == 201, second.text
    assert first.json()["system_code"] != second.json()["system_code"]
    assert second.json()["sales_status"] == "sold"
    assert second.json()["availability_status"] == "unavailable"
    assert second.json()["closing_status"] == "not_started"

    duplicate = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=historic["id"],
            floor_id=historic_floor["id"],
            display_id="201",
        ),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "inventory.errors.display_id_duplicate"

    unassigned = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "display_id": "P1",
            "asset_type": InventoryAssetType.PARKING_SPACE.value,
            "usage_type": UsageType.PARKING.value,
        },
    )
    assert unassigned.status_code == 201, unassigned.text
    assert unassigned.json()["sales_market"] is None

    repeated_unassigned = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "display_id": "P1",
            "asset_type": InventoryAssetType.PARKING_SPACE.value,
            "usage_type": UsageType.PARKING.value,
        },
    )
    assert repeated_unassigned.status_code == 409
    assert repeated_unassigned.json()["detail"] == "inventory.errors.display_id_duplicate"

    other_unassigned = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "display_id": "P2",
            "asset_type": InventoryAssetType.PARKING_SPACE.value,
            "usage_type": UsageType.PARKING.value,
        },
    )
    assert other_unassigned.status_code == 201, other_unassigned.text


def test_sales_market_values_and_filters(client: TestClient) -> None:
    project = _create_project(client)
    building = _create_building(client, project["id"], code="A", name="Tower")
    floor = _create_floor(client, building["id"])

    turkey = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=building["id"],
            floor_id=floor["id"],
            display_id="301",
            sales_market="turkey",
        ),
    )
    assert turkey.status_code == 201, turkey.text
    assert turkey.json()["sales_market"] == "turkey"

    usa = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=building["id"],
            floor_id=floor["id"],
            display_id="302",
            sales_market="usa",
        ),
    )
    assert usa.status_code == 201, usa.text
    assert usa.json()["sales_market"] == "usa"

    invalid = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=building["id"],
            floor_id=floor["id"],
            display_id="303",
            sales_market="europe",
        ),
    )
    assert invalid.status_code == 422

    listed = client.get(
        "/inventory/assets",
        params={"project_id": project["id"], "sales_market": "turkey"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["display_id"] == "301"

    bad_filter = client.get("/inventory/assets", params={"sales_market": "europe"})
    assert bad_filter.status_code == 422


def test_sold_status_does_not_close_the_unit(client: TestClient) -> None:
    project = _create_project(client)
    building = _create_building(client, project["id"], code="S", name="South")
    floor = _create_floor(client, building["id"])
    created = client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=building["id"],
            floor_id=floor["id"],
            display_id="401",
        ),
    )
    assert created.status_code == 201, created.text
    asset_id = created.json()["id"]

    updated = client.post(
        f"/inventory/assets/{asset_id}/status",
        json={"status_category": StatusCategory.SALES.value, "new_status": "sold"},
    )
    assert updated.status_code == 200, updated.text

    detail = client.get(f"/inventory/assets/{asset_id}")
    body = detail.json()
    assert body["sales_status"] == "sold"
    assert body["availability_status"] == "available"
    assert body["closing_status"] == "not_started"


def test_project_units_include_building_label_and_market_counts(client: TestClient) -> None:
    project = _create_project(client)
    historic = _create_building(client, project["id"], code="HIST", name="Historic")
    addition = _create_building(client, project["id"], code="ADD", name="Addition")
    historic_floor = _create_floor(client, historic["id"])
    addition_floor = _create_floor(client, addition["id"])
    client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=historic["id"],
            floor_id=historic_floor["id"],
            display_id="201",
            sales_market="turkey",
        ),
    )
    client.post(
        "/inventory/assets",
        json=_unit_payload(
            project_id=project["id"],
            building_id=addition["id"],
            floor_id=addition_floor["id"],
            display_id="201",
            sales_market="usa",
            sales_status=InventorySalesStatus.SOLD.value,
            availability_status=AvailabilityStatus.UNAVAILABLE.value,
        ),
    )

    listed = client.get(f"/projects/{project['id']}/units")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    labels = {item["unit_label"] for item in body["items"]}
    assert labels == {"Historic · 201", "Addition · 201"}
    assert {item["building_label"] for item in body["items"]} == {"Historic", "Addition"}
    summary = body["summary"]
    assert summary["total_physical_units"]["value"] == 2
    assert summary["turkey_allocation"]["value"] == 1
    assert summary["usa_allocation"]["value"] == 1
    assert summary["sold_units"]["value"] == 1
    assert summary["available_for_sale"]["value"] == 1

    turkey = client.get(f"/projects/{project['id']}/units", params={"sales_market": "turkey"})
    assert turkey.status_code == 200
    assert turkey.json()["total"] == 1
    assert turkey.json()["items"][0]["building_label"] == "Historic"
    assert turkey.json()["items"][0]["sales_market"] == "turkey"
    assert turkey.json()["summary"]["total_physical_units"]["value"] == 2

    invalid = client.get(f"/projects/{project['id']}/units", params={"sales_market": "europe"})
    assert invalid.status_code == 422
