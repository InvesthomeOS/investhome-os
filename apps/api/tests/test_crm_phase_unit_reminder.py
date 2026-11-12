"""Phase, string unit identity, and the 10-minute task reminder default."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivityReminder
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
from investhome_api.models.notification import Notification
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.crm.agreement_service import format_linked_unit
from investhome_api.services.crm.task_reminder_jobs import run_crm_task_due_reminders

ISTANBUL = ZoneInfo("Europe/Istanbul")


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


def _building(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/inventory/buildings",
        json={
            "project_id": project_id,
            "name": "Main",
            "code": "MN",
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


def test_project_without_phases_hides_phase_catalog(client: TestClient) -> None:
    project = _project(client, code="PRJ-NOPHASE", name="The Temple")
    catalog = client.get("/crm/agreements/project-units", params={"project_group": "the_temple"})
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["phases"] == []
    assert project["project_name"] == "The Temple"


def test_phases_filter_units_without_rewriting_the_identifier(client: TestClient, db: Session) -> None:
    project = _project(client, code="PRJ-TEMPLE-PHASE", name="The Temple")
    building = _building(client, project["id"])
    floor = _floor(client, building["id"])
    historic = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Historic", "display_order": 1},
    )
    addition = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Addition", "display_order": 2},
    )
    assert historic.status_code == 201, historic.text
    assert addition.status_code == 201, addition.text
    first = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=historic.json()["id"],
        display_id="204",
    )
    second = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=addition.json()["id"],
        display_id="204",
    )
    assert first["display_id"] == "204"
    assert second["display_id"] == "204"
    assert "Historic" not in first["display_id"]

    catalog = client.get("/crm/agreements/project-units", params={"project_group": "the_temple"})
    body = catalog.json()
    assert {item["name"] for item in body["phases"]} == {"Historic", "Addition"}
    filtered = client.get(
        "/crm/agreements/project-units",
        params={"project_group": "the_temple", "phase_id": historic.json()["id"]},
    )
    assert filtered.status_code == 200, filtered.text
    rows = filtered.json()["items"]
    assert len(rows) == 1
    assert rows[0]["unit_number"] == "204"
    assert rows[0]["label"] == "Historic · 204"
    assert rows[0]["phase_name"] == "Historic"
    db.expire_all()
    stored = db.get(InventoryAsset, UUID(first["id"]))
    assert stored is not None
    assert stored.display_id == "204"


def test_string_unit_identifier_persists_for_sales_and_denied_edit_does_not(
    auth_client: TestClient, db: Session
) -> None:
    from test_auth import _login

    _login(auth_client, "admin@example.com")
    project = _project(auth_client, code="PRJ-UNIT-STR", name="Unit Strings")
    other = _project(auth_client, code="PRJ-UNIT-STR-2", name="Unit Strings Two")
    building = _building(auth_client, project["id"])
    floor = _floor(auth_client, building["id"])
    created = _asset(
        auth_client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        display_id="204",
    )
    asset_id = created["id"]

    _login(auth_client, "sales@example.com")
    saved = auth_client.patch(f"/inventory/assets/{asset_id}", json={"display_id": "A-201"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["display_id"] == "A-201"
    mismatch = auth_client.patch(f"/inventory/assets/{asset_id}", json={"project_id": other["id"]})
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"] == "inventory.errors.building_project_mismatch"
    other_building = _building(auth_client, other["id"])
    other_floor = _floor(auth_client, other_building["id"])
    moved = auth_client.patch(
        f"/inventory/assets/{asset_id}",
        json={
            "project_id": other["id"],
            "building_id": other_building["id"],
            "floor_id": other_floor["id"],
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["project_id"] == other["id"]
    db.expire_all()
    fresh = db.get(InventoryAsset, UUID(asset_id))
    assert fresh is not None
    assert fresh.display_id == "A-201"
    assert fresh.project_id == UUID(other["id"])

    _login(auth_client, "readonly@example.com")
    denied = auth_client.patch(f"/inventory/assets/{asset_id}", json={"display_id": "PH1"})
    assert denied.status_code == 403
    db.expire_all()
    unchanged = db.get(InventoryAsset, UUID(asset_id))
    assert unchanged is not None
    assert unchanged.display_id == "A-201"


def test_historical_agreement_unit_is_not_rewritten(client: TestClient, db: Session) -> None:
    project = _project(client, code="PRJ-HIST-UNIT", name="The Temple")
    building = _building(client, project["id"])
    floor = _floor(client, building["id"])
    phase = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Historic", "display_order": 1})
    assert phase.status_code == 201, phase.text
    asset = _asset(
        client,
        project_id=project["id"],
        building_id=building["id"],
        floor_id=floor["id"],
        phase_id=phase.json()["id"],
        display_id="204",
    )
    legacy = client.post(
        "/crm/agreements",
        json={
            "first_name": "Eski",
            "last_name": "Kayıt",
            "email": "legacy.unit@example.com",
            "phone": "+90 555 100 20 01",
            "project_group": "the_temple",
            "unit_number": "G-01",
        },
    )
    assert legacy.status_code == 201, legacy.text
    linked = client.post(
        "/crm/agreements",
        json={
            "first_name": "Yeni",
            "last_name": "Bağ",
            "email": "linked.unit@example.com",
            "phone": "+90 555 100 20 02",
            "project_group": "the_temple",
            "unit_number": "204",
            "phase_id": phase.json()["id"],
            "inventory_asset_id": asset["id"],
        },
    )
    assert linked.status_code == 201, linked.text
    assert linked.json()["unit_number"] == "204"

    renamed = client.patch(f"/inventory/assets/{asset['id']}", json={"display_id": "PH1"})
    assert renamed.status_code == 200, renamed.text
    renamed_phase = client.patch(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Should Not Exist"},
    )
    assert renamed_phase.status_code in {404, 405}

    db.expire_all()
    legacy_row = db.get(CrmAgreement, UUID(legacy.json()["agreement_id"]))
    linked_row = db.get(CrmAgreement, UUID(linked.json()["agreement_id"]))
    assert legacy_row is not None and linked_row is not None
    assert legacy_row.unit_number == "G-01"
    assert linked_row.unit_number == "204"
    assert linked_row.inventory_asset_id == UUID(asset["id"])
    assert format_linked_unit(project_name="The Temple", phase_name="Historic", unit_number="204") == (
        "The Temple · Historic · 204"
    )


def test_new_task_defaults_to_ten_minutes_before_istanbul(client: TestClient, db: Session) -> None:
    person = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Hatırlatma Varsayılan",
            "primary_email": "reminder.default@example.com",
        },
    )
    assert person.status_code == 201, person.text
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Varsayılan hatırlatma",
            "contact_id": person.json()["contact"]["id"],
            "due_on": "2026-11-09",
            "due_time": "11:35",
            "timezone": "Europe/Istanbul",
        },
    )
    assert created.status_code == 201, created.text
    activity = created.json()["activity"]
    reminders = activity["reminders"]
    assert len(reminders) == 1
    assert reminders[0]["channel"] == "in_app"
    assert reminders[0]["offset_minutes"] == 10
    remind_at = datetime.fromisoformat(reminders[0]["remind_at"])
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=UTC)
    local = remind_at.astimezone(ISTANBUL)
    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 11, 9, 11, 25)

    removed = client.post(
        "/crm/tasks",
        json={
            "title": "Hatırlatmasız",
            "contact_id": person.json()["contact"]["id"],
            "due_on": "2026-11-09",
            "due_time": "12:00",
            "timezone": "Europe/Istanbul",
            "reminders": [],
        },
    )
    assert removed.status_code == 201, removed.text
    assert removed.json()["activity"]["reminders"] == []

    no_due = client.post(
        "/crm/tasks",
        json={"title": "Tarihsiz", "contact_id": person.json()["contact"]["id"]},
    )
    assert no_due.status_code == 201, no_due.text
    assert no_due.json()["activity"]["reminders"] == []

    db.expire_all()
    stored = (
        db.query(CrmActivityReminder)
        .filter_by(activity_id=UUID(activity["id"]))
        .all()
    )
    assert len(stored) == 1
    assert stored[0].offset_minutes == 10


def test_due_reminder_is_created_once(client: TestClient, db: Session) -> None:
    person = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Tek Bildirim",
            "primary_email": "reminder.once@example.com",
        },
    )
    assert person.status_code == 201, person.text
    due = datetime.now(ISTANBUL) - timedelta(minutes=1)
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Geçmiş görev",
            "contact_id": person.json()["contact"]["id"],
            "due_on": due.date().isoformat(),
            "due_time": due.strftime("%H:%M"),
            "timezone": "Europe/Istanbul",
        },
    )
    assert created.status_code == 201, created.text
    activity_id = UUID(created.json()["activity"]["id"])
    first = run_crm_task_due_reminders(clock=datetime.now(UTC) + timedelta(minutes=1), db=db)
    db.commit()
    assert first["reminders_sent"] == 1
    second = run_crm_task_due_reminders(clock=datetime.now(UTC) + timedelta(minutes=2), db=db)
    db.commit()
    assert second["reminders_sent"] == 0
    notes = db.query(Notification).filter(Notification.dedupe_key.like(f"crm.task.due.{activity_id}.%")).all()
    assert len(notes) == 1
