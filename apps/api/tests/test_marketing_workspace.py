"""Marketing workspace API tests."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _campaign_payload(**overrides) -> dict:
    base = {
        "name": f"Test Campaign {uuid4().hex[:6]}",
        "objective": "lead_generation",
        "campaign_type": "lead_generation",
        "status": "draft",
        "priority": "normal",
    }
    base.update(overrides)
    return base


def test_marketing_dashboard_load(client: TestClient) -> None:
    response = client.get("/marketing/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "widgets" in body
    assert isinstance(body["widgets"], list)
    assert len(body["widgets"]) >= 10
    assert body["campaign_count"] == 0


def test_marketing_navigation(client: TestClient) -> None:
    response = client.get("/marketing/navigation")
    assert response.status_code == 200
    groups = response.json()["groups"]
    assert len(groups) >= 5
    hrefs = [item["href"] for group in groups for item in group["items"]]
    assert "/workspaces/marketing/dashboard" in hrefs
    assert "/workspaces/marketing/campaigns" in hrefs


def test_marketing_quick_actions(client: TestClient) -> None:
    response = client.get("/marketing/quick-actions")
    assert response.status_code == 200
    actions = response.json()["actions"]
    assert len(actions) >= 5
    assert any(a["key"] == "create_campaign" for a in actions)


def test_create_campaign(client: TestClient, db: Session) -> None:
    payload = _campaign_payload()
    response = client.post("/marketing/campaigns", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["campaign"]["name"] == payload["name"]
    assert body["campaign"]["status"] == "draft"

    audit = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.MARKETING_CAMPAIGN,
            ActivityLog.entity_id == UUID(body["campaign"]["id"]),
        )
    ).first()
    assert audit is not None


def test_list_campaigns(client: TestClient) -> None:
    client.post("/marketing/campaigns", json=_campaign_payload())
    response = client.get("/marketing/campaigns")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


def test_get_campaign_detail(client: TestClient) -> None:
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.get(f"/marketing/campaigns/{campaign_id}")
    assert response.status_code == 200
    assert response.json()["id"] == campaign_id


def test_update_campaign(client: TestClient) -> None:
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.put(
        f"/marketing/campaigns/{campaign_id}",
        json={"name": "Updated Campaign Name", "priority": "high"},
    )
    assert response.status_code == 200
    assert response.json()["campaign"]["name"] == "Updated Campaign Name"
    assert response.json()["campaign"]["priority"] == "high"


def test_marketing_permissions_forbidden(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/marketing/dashboard")
    assert response.status_code == 403


def test_marketing_campaign_create_forbidden(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.post("/marketing/campaigns", json=_campaign_payload())
    assert response.status_code == 403


def test_archive_campaign(client: TestClient) -> None:
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.post(f"/marketing/campaigns/{campaign_id}/archive", json={"reason": "Test archive"})
    assert response.status_code == 200
    assert response.json()["campaign"]["status"] == "archived"
