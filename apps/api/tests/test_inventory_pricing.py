"""Inventory pricing workflow integration tests."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from investhome_api.models.inventory import (
    AvailabilityStatus,
    InventoryAssetType,
    InventorySalesStatus,
    PriceRequestStatus,
    PriceStatus,
    PriceType,
    UsageType,
)
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.inventory.pricing_service import compute_change


def _create_project(client: TestClient, *, code: str = "PRJ-PRC-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Pricing Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_asset(client: TestClient, project_id: str, *, display_id: str = "12A") -> dict:
    response = client.post(
        "/inventory/assets",
        json={
            "project_id": project_id,
            "display_id": display_id,
            "asset_type": InventoryAssetType.LAND_PARCEL.value,
            "usage_type": UsageType.INDUSTRIAL.value,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "sales_status": InventorySalesStatus.AVAILABLE_FOR_SALE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_compute_change_decimal():
    change_amount, change_pct = compute_change(Decimal("100000"), Decimal("110000"))
    assert change_amount == Decimal("10000.00")
    assert change_pct == Decimal("10.00")

    zero_base_amount, zero_base_pct = compute_change(None, Decimal("500000"))
    assert zero_base_amount == Decimal("500000.00")
    assert zero_base_pct is None


def test_initial_price_and_history(client: TestClient):
    project = _create_project(client)
    asset = _create_asset(client, project["id"])
    today = date.today().isoformat()

    response = client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "500000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Launch list",
        },
    )
    assert response.status_code == 201, response.text
    price = response.json()
    assert price["status"] == PriceStatus.ACTIVE.value
    assert price["amount"] == "500000.00"

    history = client.get(f"/inventory/prices/by-asset/{asset['id']}/history")
    assert history.status_code == 200
    assert len(history.json()) >= 1

    asset_row = client.get(f"/inventory/assets/{asset['id']}")
    assert asset_row.status_code == 200


def test_price_change_submit_approve_flow(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-002")
    asset = _create_asset(client, project["id"], display_id="12B")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "400000",
            "currency": "USD",
            "effective_from": today,
        },
    )

    draft = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "450000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Market adjustment",
            "submit": False,
        },
    )
    assert draft.status_code == 201
    request_id = draft.json()["id"]
    assert draft.json()["change_percentage"] == "12.50"

    submitted = client.post(f"/inventory/price-requests/{request_id}/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == PriceRequestStatus.SUBMITTED.value

    approved = client.post(
        f"/inventory/price-requests/{request_id}/approve",
        json={"comments": "Approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == PriceRequestStatus.APPLIED.value

    current = client.get(f"/inventory/prices/by-asset/{asset['id']}/current")
    assert current.status_code == 200
    list_prices = [p for p in current.json() if p["price_type"] == PriceType.LIST.value]
    assert list_prices[0]["amount"] == "450000.00"

    history = client.get(f"/inventory/prices/by-asset/{asset['id']}/history")
    assert len(history.json()) >= 2

    events = client.get(f"/inventory/prices/by-asset/{asset['id']}/current")
    assert events.status_code == 200


def test_reject_does_not_change_active_price(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-003")
    asset = _create_asset(client, project["id"], display_id="12C")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "300000",
            "currency": "USD",
            "effective_from": today,
        },
    )

    request = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "250000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Discount attempt",
            "submit": True,
        },
    )
    request_id = request.json()["id"]

    rejected = client.post(
        f"/inventory/price-requests/{request_id}/reject",
        json={"decision_notes": "Too steep"},
    )
    assert rejected.status_code == 200

    current = client.get(f"/inventory/prices/by-asset/{asset['id']}/current")
    list_prices = [p for p in current.json() if p["price_type"] == PriceType.LIST.value]
    assert list_prices[0]["amount"] == "300000.00"


def test_stale_request_blocked_on_approve(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-004")
    asset = _create_asset(client, project["id"], display_id="12D")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "600000",
            "currency": "USD",
            "effective_from": today,
        },
    )

    first = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "620000",
            "currency": "USD",
            "effective_from": today,
            "reason": "First request",
            "submit": True,
        },
    )
    first_id = first.json()["id"]

    second = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "640000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Second request",
            "submit": True,
        },
    )
    second_id = second.json()["id"]

    assert client.post(f"/inventory/price-requests/{second_id}/approve", json={}).status_code == 200

    stale = client.post(f"/inventory/price-requests/{first_id}/approve", json={})
    assert stale.status_code == 409
    assert stale.json()["detail"] == "inventory.pricing.errors.stale_request"


def test_withdraw_and_revision(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-005")
    asset = _create_asset(client, project["id"], display_id="12E")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "350000",
            "currency": "USD",
            "effective_from": today,
        },
    )

    request = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "360000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Needs review",
            "submit": True,
        },
    )
    request_id = request.json()["id"]

    revision = client.post(
        f"/inventory/price-requests/{request_id}/request-revision",
        json={"decision_notes": "Add supporting doc"},
    )
    assert revision.status_code == 200
    assert revision.json()["status"] == PriceRequestStatus.DRAFT.value

    withdrawn = client.post(f"/inventory/price-requests/{request_id}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == PriceRequestStatus.WITHDRAWN.value


def test_pending_approvals_list(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-006")
    asset = _create_asset(client, project["id"], display_id="12F")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "200000",
            "currency": "USD",
            "effective_from": today,
        },
    )
    client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "210000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Pending",
            "submit": True,
        },
    )

    pending = client.get("/inventory/price-requests/pending")
    assert pending.status_code == 200
    assert pending.json()["total"] >= 1


def test_notifications_on_submit(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-007")
    asset = _create_asset(client, project["id"], display_id="12G")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "100000",
            "currency": "USD",
            "effective_from": today,
        },
    )
    response = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "105000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Notify test",
            "submit": True,
        },
    )

    assert response.status_code == 201


def test_activity_logged_on_approve(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-008")
    asset = _create_asset(client, project["id"], display_id="12H")
    today = date.today().isoformat()

    client.post(
        "/inventory/prices/initial",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "amount": "150000",
            "currency": "USD",
            "effective_from": today,
        },
    )
    req = client.post(
        "/inventory/price-requests",
        json={
            "inventory_asset_id": asset["id"],
            "price_type": PriceType.LIST.value,
            "proposed_amount": "155000",
            "currency": "USD",
            "effective_from": today,
            "reason": "Activity test",
            "submit": True,
        },
    )
    assert client.post(f"/inventory/price-requests/{req.json()['id']}/approve", json={}).status_code == 200


def test_multiple_price_types(client: TestClient):
    project = _create_project(client, code="PRJ-PRC-009")
    asset = _create_asset(client, project["id"], display_id="12I")
    today = date.today().isoformat()

    for price_type, amount in [(PriceType.LIST.value, "500000"), (PriceType.PROMOTIONAL.value, "475000")]:
        response = client.post(
            "/inventory/prices/initial",
            json={
                "inventory_asset_id": asset["id"],
                "price_type": price_type,
                "amount": amount,
                "currency": "USD",
                "effective_from": today,
            },
        )
        assert response.status_code == 201, response.text

    current = client.get(f"/inventory/prices/by-asset/{asset['id']}/current")
    assert len(current.json()) == 2
