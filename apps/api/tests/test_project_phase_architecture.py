"""Project → optional Phase → Unit is one record, referenced by id."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType


def _project(client: TestClient, *, code: str, name: str) -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": name,
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _building(client: TestClient, project_id: str, code: str = "MN") -> dict:
    response = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": "Main",
            "code": code,
            "building_type": BuildingType.APARTMENT.value,
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _floor(client: TestClient, building_id: str) -> dict:
    response = client.post(
        "/inventory/floors",
        json={
            "building_id": building_id,
            "floor_number": 2,
            "display_name": "Level 2",
            "level_code": "02",
            "status": StructureStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _asset(client: TestClient, **extra: object) -> dict:
    payload = {
        "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
        "usage_type": UsageType.RESIDENTIAL.value,
        "availability_status": AvailabilityStatus.AVAILABLE.value,
        "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
    }
    payload.update(extra)
    response = client.post("/inventory/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_project_with_no_phases_lists_empty(client: TestClient) -> None:
    project = _project(client, code="PRJ-NO-PHASE", name="Plain Project")
    listed = client.get(f"/inventory/projects/{project['id']}/phases")
    assert listed.status_code == 200
    assert listed.json() == []
    assert "Historic" not in listed.text
    assert "Addition" not in listed.text


def test_project_phase_create_edit_reorder_and_deactivate(client: TestClient) -> None:
    project = _project(client, code="PRJ-MANY-PHASE", name="Phased Project")
    one = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Only", "display_order": 0})
    assert one.status_code == 201, one.text
    assert one.json()["unit_count"] == 0
    removed = client.patch(
        f"/inventory/projects/{project['id']}/phases/{one.json()['id']}",
        json={"active": False},
    )
    assert removed.status_code == 200, removed.text
    assert client.get(f"/inventory/projects/{project['id']}/phases").json() == []

    created = []
    for index, name in enumerate(("Historic", "Addition", "Tower")):
        response = client.post(
            f"/inventory/projects/{project['id']}/phases",
            json={"name": name, "display_order": index, "active": True},
        )
        assert response.status_code == 201, response.text
        created.append(response.json())
    renamed = client.patch(
        f"/inventory/projects/{project['id']}/phases/{created[2]['id']}",
        json={"name": "Garden"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Garden"
    order = client.put(
        f"/inventory/projects/{project['id']}/phases/reorder",
        json={"phase_ids": [created[1]["id"], created[0]["id"], created[2]["id"]]},
    )
    assert order.status_code == 200, order.text
    assert [row["name"] for row in order.json() if row["active"]][:3] == ["Addition", "Historic", "Garden"]
    unknown = client.patch(
        f"/inventory/projects/{project['id']}/phases/{uuid4()}",
        json={"name": "Missing"},
    )
    assert unknown.status_code == 404
    other = _project(client, code="PRJ-OTHER-PHASE", name="Other")
    foreign = client.patch(
        f"/inventory/projects/{other['id']}/phases/{created[0]['id']}",
        json={"name": "Stolen"},
    )
    assert foreign.status_code == 404


def test_inventory_phase_filter_keeps_unit_identifier(client: TestClient) -> None:
    project = _project(client, code="PRJ-INV-PHASE", name="Inventory Phases")
    building = _building(client, project["id"], "B1")
    floor = _floor(client, building["id"])
    historic = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Historic"}).json()
    addition = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Addition", "display_order": 1},
    ).json()
    first = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=historic["id"],
        display_id="204",
    )
    _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=addition["id"],
        display_id="204",
    )
    assert first["display_id"] == "204"
    assert "Historic" not in first["display_id"]
    listed = client.get("/inventory/assets", params={"project_id": project["id"], "phase_id": historic["id"]})
    assert listed.status_code == 200, listed.text
    assert [item["display_id"] for item in listed.json()["items"]] == ["204"]
    assert listed.json()["items"][0]["phase_id"] == historic["id"]
    counted = client.get(f"/inventory/projects/{project['id']}/phases")
    assert next(row for row in counted.json() if row["id"] == historic["id"])["unit_count"] == 1
    mismatch = client.patch(
        f"/inventory/assets/{first['id']}",
        json={"phase_id": str(uuid4())},
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "inventory.errors.phase_project_mismatch"


def test_new_and_existing_lead_phase_links(client: TestClient) -> None:
    plain = _project(client, code="PRJ-LEAD-PLAIN", name="No Phase Homes")
    phased = _project(client, code="PRJ-LEAD-PHASE", name="The Temple")
    building = _building(client, phased["id"], "TM")
    floor = _floor(client, building["id"])
    phase = client.post(f"/inventory/projects/{phased['id']}/phases", json={"name": "Historic"}).json()
    asset = _asset(
        client,
        project_id=phased["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=phase["id"],
        display_id="204",
    )
    empty = client.get(f"/inventory/projects/{plain['id']}/phases")
    assert empty.json() == []
    bare = client.post(
        "/crm/leads",
        json={
            "full_name": "Fazsız Kişi",
            "email": "phase.none@example.com",
            "phone": "+90 555 300 00 01",
            "project_id": plain["id"],
            "project": "No Phase Homes",
        },
    )
    assert bare.status_code == 201, bare.text
    assert bare.json()["phase_id"] is None
    assert bare.json()["phase_name"] is None
    assert bare.json()["interest_label"] == "No Phase Homes"

    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Fazlı Kişi",
            "email": "phase.yes@example.com",
            "phone": "+90 555 300 00 02",
            "project_id": phased["id"],
            "phase_id": phase["id"],
            "inventory_asset_id": asset["id"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["unit_number"] == "204"
    assert body["phase_name"] == "Historic"
    assert body["interest_label"] == "The Temple · Historic · 204"
    assert "Historic 204" not in body["interest_label"]

    bad = client.post(
        "/crm/leads",
        json={
            "full_name": "Hatalı Kişi",
            "email": "phase.bad@example.com",
            "phone": "+90 555 300 00 03",
            "project_id": plain["id"],
            "phase_id": phase["id"],
            "inventory_asset_id": asset["id"],
        },
    )
    assert bad.status_code == 400
    assert bad.json()["detail"] in {
        "inventory.errors.phase_project_mismatch",
        "crm.agreements.errors.unit_project_mismatch",
    }

    edited = client.patch(
        f"/crm/leads/{bare.json()['id']}",
        json={"project_id": phased["id"], "phase_id": phase["id"], "inventory_asset_id": asset["id"]},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["phase_id"] == phase["id"]
    assert edited.json()["unit_number"] == "204"
    filtered = client.get("/crm/leads", params={"phase_id": phase["id"]})
    assert filtered.status_code == 200
    assert edited.json()["id"] in {item["id"] for item in filtered.json()["items"]}


def test_agreement_rejects_invalid_combination_and_keeps_history(client: TestClient, db: Session) -> None:
    project = _project(client, code="PRJ-AGR-PHASE", name="The Temple")
    building = _building(client, project["id"], "AG")
    floor = _floor(client, building["id"])
    historic = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Historic"}).json()
    addition = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Addition", "display_order": 1},
    ).json()
    asset = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=historic["id"],
        display_id="204",
    )
    rejected = client.post(
        "/crm/agreements",
        json={
            "first_name": "Hatalı",
            "last_name": "Anlaşma",
            "email": "bad.combo@example.com",
            "phone": "+90 555 300 10 01",
            "project_group": "the_temple",
            "unit_number": "204",
            "phase_id": addition["id"],
            "inventory_asset_id": asset["id"],
        },
    )
    assert rejected.status_code == 400
    assert "unit_phase_mismatch" in rejected.json()["detail"]

    legacy = client.post(
        "/crm/agreements",
        json={
            "first_name": "Eski",
            "last_name": "Anlaşma",
            "email": "legacy.phase@example.com",
            "phone": "+90 555 300 10 02",
            "project_group": "the_temple",
            "unit_number": "G-01",
        },
    )
    assert legacy.status_code == 201, legacy.text
    linked = client.post(
        "/crm/agreements",
        json={
            "first_name": "Canlı",
            "last_name": "Anlaşma",
            "email": "live.phase@example.com",
            "phone": "+90 555 300 10 03",
            "project_group": "the_temple",
            "unit_number": "204",
            "phase_id": historic["id"],
            "inventory_asset_id": asset["id"],
        },
    )
    assert linked.status_code == 201, linked.text
    assert linked.json()["unit_number"] == "204"

    moved = client.patch(f"/inventory/assets/{asset['id']}", json={"phase_id": addition["id"]})
    assert moved.status_code == 200, moved.text
    db.expire_all()
    legacy_row = db.get(CrmAgreement, UUID(legacy.json()["agreement_id"]))
    linked_row = db.get(CrmAgreement, UUID(linked.json()["agreement_id"]))
    assert legacy_row is not None and linked_row is not None
    assert legacy_row.unit_number == "G-01"
    assert legacy_row.phase_id is None
    assert linked_row.unit_number == "204"
    assert linked_row.phase_id == UUID(historic["id"])
    assert linked_row.inventory_asset_id == UUID(asset["id"])
    fresh_asset = db.get(InventoryAsset, UUID(asset["id"]))
    assert fresh_asset is not None
    assert fresh_asset.display_id == "204"
    assert fresh_asset.phase_id == UUID(addition["id"])


def test_temple_historic_and_addition_can_both_use_301(client: TestClient, db: Session) -> None:
    project = _project(client, code="PRJ-TEMPLE-301", name="The Temple")
    building = _building(client, project["id"], "T301")
    floor = _floor(client, building["id"])
    historic = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Historic"}).json()
    addition = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Addition", "display_order": 1},
    ).json()
    historic_unit = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=historic["id"],
        display_id="301",
    )
    addition_unit = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=addition["id"],
        display_id="301",
    )
    assert historic_unit["id"] != addition_unit["id"]
    assert historic_unit["display_id"] == "301"
    assert addition_unit["display_id"] == "301"
    duplicate = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "floor_id": floor["id"],
            "phase_id": historic["id"],
            "display_id": "301",
            "asset_type": InventoryAssetType.RESIDENTIAL_UNIT.value,
            "usage_type": UsageType.RESIDENTIAL.value,
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "inventory.errors.display_id_duplicate"

    historic_catalog = client.get(
        "/crm/agreements/project-units",
        params={"project_group": "the_temple", "phase_id": historic["id"]},
    )
    assert historic_catalog.status_code == 200, historic_catalog.text
    historic_rows = historic_catalog.json()["items"]
    assert [row["inventory_asset_id"] for row in historic_rows] == [historic_unit["id"]]
    assert historic_rows[0]["unit_number"] == "301"
    assert historic_rows[0]["phase_name"] == "Historic"
    assert addition_unit["id"] not in {row["inventory_asset_id"] for row in historic_rows}

    addition_catalog = client.get(
        "/crm/agreements/project-units",
        params={"project_group": "the_temple", "phase_id": addition["id"]},
    )
    addition_rows = addition_catalog.json()["items"]
    assert [row["inventory_asset_id"] for row in addition_rows] == [addition_unit["id"]]
    assert historic_unit["id"] not in {row["inventory_asset_id"] for row in addition_rows}

    listed = client.get("/inventory/assets", params={"project_id": project["id"], "phase_id": addition["id"]})
    assert [item["id"] for item in listed.json()["items"]] == [addition_unit["id"]]

    lead = client.post(
        "/crm/leads",
        json={
            "full_name": "Temple 301",
            "email": "temple.301@example.com",
            "phone": "+90 555 301 00 01",
            "project_id": project["id"],
            "phase_id": addition["id"],
            "inventory_asset_id": addition_unit["id"],
        },
    )
    assert lead.status_code == 201, lead.text
    assert lead.json()["phase_id"] == addition["id"]
    assert lead.json()["inventory_asset_id"] == addition_unit["id"]
    assert lead.json()["unit_number"] == "301"
    mixed = client.post(
        "/crm/leads",
        json={
            "full_name": "Temple Wrong Phase",
            "email": "temple.301.bad@example.com",
            "phone": "+90 555 301 00 02",
            "project_id": project["id"],
            "phase_id": historic["id"],
            "inventory_asset_id": addition_unit["id"],
        },
    )
    assert mixed.status_code == 400
    assert "unit_phase_mismatch" in mixed.json()["detail"]

    saved = client.post(
        "/crm/agreements",
        json={
            "first_name": "Historic",
            "last_name": "Buyer",
            "email": "temple.historic.301@example.com",
            "phone": "+90 555 301 10 01",
            "project_group": "the_temple",
            "unit_number": "301",
            "phase_id": historic["id"],
            "inventory_asset_id": historic_unit["id"],
        },
    )
    assert saved.status_code == 201, saved.text
    db.expire_all()
    row = db.get(CrmAgreement, UUID(saved.json()["agreement_id"]))
    assert row is not None
    assert row.unit_number == "301"
    assert row.phase_id == UUID(historic["id"])
    assert row.inventory_asset_id == UUID(historic_unit["id"])

    ambiguous = client.post(
        "/crm/agreements",
        json={
            "first_name": "Ambiguous",
            "last_name": "Buyer",
            "email": "temple.ambiguous.301@example.com",
            "phone": "+90 555 301 10 02",
            "project_group": "the_temple",
            "unit_number": "301",
        },
    )
    assert ambiguous.status_code == 400
    assert "phase_required" in ambiguous.json()["detail"]

    history = client.post(
        "/crm/agreements",
        json={
            "first_name": "History",
            "last_name": "Buyer",
            "email": "temple.history.301@example.com",
            "phone": "+90 555 301 10 03",
            "project_group": "the_temple",
            "unit_number": "301-302",
        },
    )
    assert history.status_code == 201, history.text
    renamed = client.patch(f"/inventory/assets/{historic_unit['id']}", json={"display_id": "301A"})
    assert renamed.status_code == 200, renamed.text
    db.expire_all()
    history_row = db.get(CrmAgreement, UUID(history.json()["agreement_id"]))
    assert history_row is not None
    assert history_row.unit_number == "301-302"
    assert history_row.phase_id is None
    assert history_row.inventory_asset_id is None
    assert row.unit_number == "301"
