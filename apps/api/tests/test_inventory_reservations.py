"""Inventory reservation workflow integration tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.finance import AccountStatus, AccountType, FinancialAccount
from investhome_api.models.inventory import (
    AvailabilityStatus,
    BuildingType,
    InventoryAssetType,
    InventorySalesStatus,
    ReservationRecordStatus,
    StructureStatus,
    UsageType,
)
from investhome_api.models.notification import Notification
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.inventory.reservation_jobs import run_expire_soft_holds
from investhome_api.services.inventory.reservation_service import SOFT_HOLD_DEFAULT_HOURS


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _create_project(client: TestClient, *, code: str = "PRJ-RSV-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Reservation Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_investor(client: TestClient, *, email: str = "buyer@example.com") -> dict:
    response = client.post(
        "/investors",
        json={
            "full_name": "Reservation Buyer",
            "email": email,
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


def _create_available_asset(client: TestClient, project_id: str, *, display_id: str = "12A") -> dict:
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


def _create_financial_account(db: Session) -> FinancialAccount:
    account = FinancialAccount(
        account_name="Operating",
        account_type=AccountType.OPERATING,
        currency="USD",
        current_balance=Decimal("100000"),
        available_balance=Decimal("100000"),
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.commit()
    return account


def _soft_hold_payload(asset_id: str, investor_id: str, **overrides: object) -> dict:
    payload = {
        "inventory_asset_id": asset_id,
        "investor_id": investor_id,
        "notes": "Test soft hold",
    }
    payload.update(overrides)
    return payload


def test_soft_hold_default_48h(client: TestClient) -> None:
    project = _create_project(client)
    investor = _create_investor(client)
    asset = _create_available_asset(client, project["id"])

    before = datetime.now(UTC)
    response = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == ReservationRecordStatus.ACTIVE.value
    assert body["reservation_type"] == "soft_hold"
    assert body["expires_at"] is not None

    expires = _parse_utc(body["expires_at"])
    delta_hours = (expires - before).total_seconds() / 3600
    assert SOFT_HOLD_DEFAULT_HOURS - 0.1 <= delta_hours <= SOFT_HOLD_DEFAULT_HOURS + 1

    asset_detail = client.get(f"/inventory/assets/{asset['id']}").json()
    assert asset_detail["availability_status"] == AvailabilityStatus.HOLD.value
    assert asset_detail["reservation_status"] == "soft_hold"


def test_soft_hold_conflict_on_same_asset(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-002")
    investor_a = _create_investor(client, email="a@example.com")
    investor_b = _create_investor(client, email="b@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12B")

    first = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor_a["id"]),
    )
    assert first.status_code == 201

    second = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor_b["id"]),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "inventory.errors.active_reservation_exists"


def test_soft_hold_requires_available_asset(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-003")
    investor = _create_investor(client, email="c@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12C")

    client.post(
        f"/inventory/assets/{asset['id']}/status",
        json={
            "status_category": "availability",
            "new_status": AvailabilityStatus.UNAVAILABLE.value,
        },
    )

    response = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "inventory.errors.asset_not_available"


def test_release_soft_hold_restores_availability(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-004")
    investor = _create_investor(client, email="d@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12D")

    created = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    ).json()

    released = client.post(
        f"/inventory/reservations/{created['id']}/release",
        json={"reason": "Buyer withdrew"},
    )
    assert released.status_code == 200
    assert released.json()["status"] == ReservationRecordStatus.RELEASED.value

    asset_detail = client.get(f"/inventory/assets/{asset['id']}").json()
    assert asset_detail["availability_status"] == AvailabilityStatus.AVAILABLE.value
    assert asset_detail["reservation_status"] == "none"


def test_reservation_approval_flow(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-005")
    investor = _create_investor(client, email="e@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12E")

    hold = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    ).json()

    requested = client.post(
        f"/inventory/reservations/{hold['id']}/request",
        json={"notes": "Formal reservation request"},
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == ReservationRecordStatus.REQUESTED.value

    approved = client.post(
        f"/inventory/reservations/{hold['id']}/approve",
        json={"notes": "Approved by manager"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == ReservationRecordStatus.APPROVED.value

    asset_detail = client.get(f"/inventory/assets/{asset['id']}").json()
    assert asset_detail["reservation_status"] == "confirmed"


def test_deposit_received_creates_finance_draft(client: TestClient) -> None:
    from investhome_api.db.session import SessionLocal

    project = _create_project(client, code="PRJ-RSV-006")
    investor = _create_investor(client, email="f@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12F")

    with SessionLocal() as db:
        _create_financial_account(db)

    hold = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"], deposit_amount="5000.00"),
    ).json()
    client.post(f"/inventory/reservations/{hold['id']}/request", json={})
    client.post(f"/inventory/reservations/{hold['id']}/approve", json={})

    received = client.post(
        f"/inventory/reservations/{hold['id']}/deposit-received",
        json={"reference_number": "DEP-001"},
    )
    assert received.status_code == 200
    body = received.json()
    assert body["status"] == ReservationRecordStatus.DEPOSIT_RECEIVED.value
    assert body["finance_transaction_id"] is not None


def test_convert_reservation(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-007")
    investor = _create_investor(client, email="g@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12G")

    hold = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    ).json()
    client.post(f"/inventory/reservations/{hold['id']}/request", json={})
    client.post(f"/inventory/reservations/{hold['id']}/approve", json={})

    converted = client.post(
        f"/inventory/reservations/{hold['id']}/convert",
        json={"notes": "Ready for contract"},
    )
    assert converted.status_code == 200
    assert converted.json()["status"] == ReservationRecordStatus.CONVERTED.value


def test_expire_soft_holds_job(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-008")
    investor = _create_investor(client, email="h@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12H")

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    created = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"], expires_at=past),
    )
    assert created.status_code == 201

    result = run_expire_soft_holds(clock=datetime.now(UTC))
    assert result["expired_count"] == 1

    detail = client.get(f"/inventory/reservations/{created.json()['id']}").json()
    assert detail["status"] == ReservationRecordStatus.EXPIRED.value

    asset_detail = client.get(f"/inventory/assets/{asset['id']}").json()
    assert asset_detail["availability_status"] == AvailabilityStatus.AVAILABLE.value


def test_reservation_history_by_asset(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-009")
    investor = _create_investor(client, email="i@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12I")

    hold = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    ).json()
    client.post(f"/inventory/reservations/{hold['id']}/release", json={})

    history = client.get(f"/inventory/reservations/by-asset/{asset['id']}/history")
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) >= 1
    assert rows[0]["reservation"]["id"] == hold["id"]
    assert len(rows[0]["events"]) >= 2


def test_list_expiring_reservations(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-010")
    investor = _create_investor(client, email="j@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12J")

    soon = (datetime.now(UTC) + timedelta(hours=12)).isoformat()
    client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"], expires_at=soon),
    )

    listed = client.get("/inventory/reservations/expiring", params={"within_hours": 48})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


def test_notification_dedupe_on_soft_hold(client: TestClient) -> None:
    from investhome_api.db.session import SessionLocal

    project = _create_project(client, code="PRJ-RSV-011")
    investor = _create_investor(client, email="k@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12K")

    created = client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    )
    assert created.status_code == 201
    reservation_id = UUID(created.json()["id"])

    with SessionLocal() as db:
        count = db.query(Notification).filter(
            Notification.title_key == "notifications.inventory.soft_hold_created.title",
            Notification.related_entity_id == reservation_id,
        ).count()
        assert count <= 1


def test_party_required_validation(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-012")
    asset = _create_available_asset(client, project["id"], display_id="12L")

    response = client.post(
        "/inventory/reservations/soft-hold",
        json={"inventory_asset_id": asset["id"]},
    )
    assert response.status_code == 422


def test_search_reservations(client: TestClient) -> None:
    project = _create_project(client, code="PRJ-RSV-013")
    investor = _create_investor(client, email="m@example.com")
    asset = _create_available_asset(client, project["id"], display_id="12M")

    client.post(
        "/inventory/reservations/soft-hold",
        json=_soft_hold_payload(asset["id"], investor["id"]),
    )

    results = client.get("/search", params={"q": "12M", "entity_types": "inventory_reservation"})
    assert results.status_code == 200
    groups = results.json()["groups"]
    reservation_group = next((g for g in groups if g["entity_type"] == "inventory_reservation"), None)
    assert reservation_group is not None
    assert reservation_group["total"] >= 1
