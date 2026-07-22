"""Marketing campaign management API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    CampaignTracking,
    MarketingApproval,
    MarketingApprovalStatus,
    MarketingApprovalType,
    MarketingCampaign,
    MarketingCampaignStatus,
    MarketingChannel,
    MarketingChannelCategory,
    MarketingChannelStatus,
    MarketingConnectionStatus,
)


def _login(client: TestClient) -> None:
    """No-op when API_AUTH_ENABLED=false (default test configuration)."""
    pass


def _campaign_payload(**overrides) -> dict:
    base = {
        "name": f"Test Campaign {uuid4().hex[:6]}",
        "objective": "lead_generation",
        "campaign_type": "lead_generation",
        "priority": "normal",
        "budget_amount": "10000.00",
        "budget_currency": "USD",
        "channel_ids": [],
        "audience_ids": [],
    }
    base.update(overrides)
    return base


def _create_channel(db: Session) -> MarketingChannel:
    channel = MarketingChannel(
        name=f"Test Channel {uuid4().hex[:4]}",
        category=MarketingChannelCategory.PAID_SOCIAL,
        provider="meta",
        status=MarketingChannelStatus.INACTIVE,
        connection_status=MarketingConnectionStatus.NOT_CONNECTED,
    )
    db.add(channel)
    db.flush()
    return channel


def test_create_campaign(client: TestClient) -> None:
    _login(client)
    response = client.post("/marketing/campaigns", json=_campaign_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["campaign"]["status"] == "draft"
    assert body["campaign"]["name"].startswith("Test Campaign")


def test_get_campaign_detail(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.get(f"/marketing/campaigns/{campaign_id}")
    assert response.status_code == 200
    assert response.json()["id"] == campaign_id


def test_update_campaign(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.put(
        f"/marketing/campaigns/{campaign_id}",
        json={"name": "Updated Campaign Name", "priority": "high"},
    )
    assert response.status_code == 200
    assert response.json()["campaign"]["name"] == "Updated Campaign Name"
    assert response.json()["campaign"]["priority"] == "high"


def test_list_campaigns_with_summary(client: TestClient) -> None:
    _login(client)
    client.post("/marketing/campaigns", json=_campaign_payload())
    list_resp = client.get("/marketing/campaigns?page=1&page_size=10")
    assert list_resp.status_code == 200
    summary_resp = client.get("/marketing/campaigns/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["total"] >= 1


def test_invalid_status_transition(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    response = client.post(
        f"/marketing/campaigns/{campaign_id}/validate-transition",
        json={"target_status": "active"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert "active" in body["target_status"]


def test_submit_and_approve_campaign(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    submit = client.post(f"/marketing/campaigns/{campaign_id}/submit-approval")
    assert submit.status_code == 200
    assert submit.json()["campaign"]["status"] == "pending_approval"
    approve = client.post(f"/marketing/campaigns/{campaign_id}/approve", json={"notes": "Looks good"})
    assert approve.status_code == 200
    assert approve.json()["campaign"]["status"] == "approved"


def test_activation_blocked_without_readiness(client: TestClient) -> None:
    _login(client)
    created = client.post(
        "/marketing/campaigns",
        json=_campaign_payload(budget_amount=None, channel_ids=[], audience_ids=[]),
    ).json()
    campaign_id = created["campaign"]["id"]
    client.post(f"/marketing/campaigns/{campaign_id}/submit-approval")
    client.post(f"/marketing/campaigns/{campaign_id}/approve", json={})
    activate = client.post(f"/marketing/campaigns/{campaign_id}/activate")
    assert activate.status_code == 409


def test_activation_readiness_check(client: TestClient, db: Session) -> None:
    _login(client)
    channel = _create_channel(db)
    db.commit()
    created = client.post(
        "/marketing/campaigns",
        json=_campaign_payload(
            channel_ids=[str(channel.id)],
            audience_ids=["audience-1"],
            budget_amount="5000.00",
        ),
    ).json()
    campaign_id = created["campaign"]["id"]
    client.put(
        f"/marketing/campaigns/{campaign_id}/tracking",
        json={"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "test_launch"},
    )
    readiness = client.get(f"/marketing/campaigns/{campaign_id}/readiness")
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["overall_state"] in ("ready", "warning", "blocked")
    assert "checks" in body


def test_duplicate_campaign(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload(name="Original Campaign")).json()
    campaign_id = created["campaign"]["id"]
    dup = client.post(
        f"/marketing/campaigns/{campaign_id}/duplicate",
        json={"name": "Duplicated Campaign"},
    )
    assert dup.status_code == 201
    assert dup.json()["campaign"]["name"] == "Duplicated Campaign"
    assert dup.json()["campaign"]["status"] == "draft"
    assert dup.json()["campaign"]["id"] != campaign_id


def test_archive_and_restore(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    client.put(f"/marketing/campaigns/{campaign_id}", json={"status": "cancelled"})
    archive = client.post(
        f"/marketing/campaigns/{campaign_id}/archive",
        json={"reason": "No longer needed"},
    )
    assert archive.status_code == 200
    assert archive.json()["campaign"]["status"] == "archived"
    restore = client.post(f"/marketing/campaigns/{campaign_id}/restore")
    assert restore.status_code == 200
    assert restore.json()["campaign"]["status"] == "draft"


def test_bulk_action_eligibility(client: TestClient) -> None:
    _login(client)
    c1 = client.post("/marketing/campaigns", json=_campaign_payload()).json()["campaign"]["id"]
    c2 = client.post("/marketing/campaigns", json=_campaign_payload()).json()["campaign"]["id"]
    response = client.post(
        "/marketing/campaigns/bulk",
        json={"campaign_ids": [c1, c2], "action": "submit_approval"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible_count"] >= 1
    assert body["eligible_count"] + body["ineligible_count"] == 2


def test_campaign_brief_crud(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    update = client.put(
        f"/marketing/campaigns/{campaign_id}/brief",
        json={"executive_summary": "Launch Q3 investor campaign", "objectives": "Generate 100 leads"},
    )
    assert update.status_code == 200
    assert update.json()["executive_summary"] == "Launch Q3 investor campaign"
    get_brief = client.get(f"/marketing/campaigns/{campaign_id}/brief")
    assert get_brief.status_code == 200


def test_campaign_milestones(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    create_ms = client.post(
        f"/marketing/campaigns/{campaign_id}/milestones",
        json={"name": "Content Ready", "milestone_type": "content"},
    )
    assert create_ms.status_code == 201
    list_ms = client.get(f"/marketing/campaigns/{campaign_id}/milestones")
    assert list_ms.status_code == 200
    assert len(list_ms.json()) >= 1


def test_tracking_validation(client: TestClient) -> None:
    _login(client)
    created = client.post("/marketing/campaigns", json=_campaign_payload()).json()
    campaign_id = created["campaign"]["id"]
    incomplete = client.put(
        f"/marketing/campaigns/{campaign_id}/tracking",
        json={"utm_source": "email"},
    )
    assert incomplete.status_code == 200
    assert incomplete.json()["readiness_status"] in ("incomplete", "not_configured")
    complete = client.put(
        f"/marketing/campaigns/{campaign_id}/tracking",
        json={"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "spring_launch"},
    )
    assert complete.status_code == 200
    validate = client.post(f"/marketing/campaigns/{campaign_id}/tracking/validate")
    assert validate.status_code == 200
    assert validate.json()["readiness_status"] == "ready"


def test_saved_views_crud(client: TestClient) -> None:
    _login(client)
    create = client.post(
        "/marketing/campaigns/saved-views",
        json={"name": "My Active Campaigns", "filters_json": {"status": "active"}},
    )
    assert create.status_code == 201
    view_id = create.json()["id"]
    list_views = client.get("/marketing/campaigns/saved-views")
    assert list_views.status_code == 200
    assert any(v["id"] == view_id for v in list_views.json())
    delete = client.delete(f"/marketing/campaigns/saved-views/{view_id}")
    assert delete.status_code == 204


def test_permissions_required(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    from investhome_api.config.settings import get_settings
    get_settings.cache_clear()
    response = client.get("/marketing/campaigns/summary")
    assert response.status_code in (401, 403)


def test_workspace_overview_honest_metrics(client: TestClient) -> None:
    _login(client)
    client.post(
        "/marketing/campaigns",
        json=_campaign_payload(
            budget_amount="2500.00",
            budget_currency="USD",
            primary_channel="meta",
            notes="Foundation campaign",
            targets_json={"estimated_leads": 40},
        ),
    )
    response = client.get("/marketing/campaigns/overview")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_campaigns"]["available"] is True
    assert body["total_campaigns"]["value"] >= 1
    assert body["active_campaigns"]["available"] is True
    assert body["budget"]["available"] is True
    assert body["spend"]["available"] is False
    assert body["spend"]["reason"] == "no_spend_data"
    assert body["estimated_leads"]["available"] is True
    assert body["actual_leads"]["available"] is True
    assert body["estimated_roi"]["available"] is False
    assert body["top_performing"]["available"] is False
    assert body["upcoming"]["available"] is True


def test_campaign_project_link_and_filters(client: TestClient) -> None:
    _login(client)
    project_id = str(uuid4())
    created = client.post(
        "/marketing/campaigns",
        json=_campaign_payload(
            project_ids=[project_id],
            primary_channel="google",
            notes="Linked to project",
        ),
    )
    assert created.status_code == 201, created.text
    campaign = created.json()["campaign"]
    assert project_id in (campaign["project_ids"] or [])
    assert campaign["primary_channel"] == "google"
    assert campaign["notes"] == "Linked to project"

    filtered = client.get(f"/marketing/campaigns?project_id={project_id}&primary_channel=google")
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1
    assert any(item["id"] == campaign["id"] for item in filtered.json()["items"])

    updated = client.put(
        f"/marketing/campaigns/{campaign['id']}",
        json={"notes": "Updated notes", "budget_amount": "5000.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["campaign"]["notes"] == "Updated notes"


def test_campaign_export_csv(client: TestClient) -> None:
    _login(client)
    client.post("/marketing/campaigns", json=_campaign_payload(name="Exportable Campaign"))
    response = client.get("/marketing/campaigns/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "Exportable Campaign" in response.text
    assert "id,name,code,status" in response.text.splitlines()[0]


def test_campaign_overview_budget_remaining(client: TestClient, db: Session) -> None:
    _login(client)
    created = client.post(
        "/marketing/campaigns",
        json=_campaign_payload(budget_amount="1000.00", budget_currency="USD"),
    ).json()
    campaign_id = created["campaign"]["id"]
    allocation = client.post(
        f"/marketing/campaigns/{campaign_id}/budget",
        json={"name": "Meta Ads", "planned_amount": "1000.00", "currency": "USD"},
    )
    assert allocation.status_code == 201, allocation.text
    allocation_id = allocation.json()["id"]
    spend = client.post(
        f"/marketing/campaigns/{campaign_id}/budget/spend",
        json={"amount": "250.00", "reason": "Initial media spend", "allocation_id": allocation_id},
    )
    assert spend.status_code == 200, spend.text
    overview = client.get(f"/marketing/campaigns/{campaign_id}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["budget_summary"]["planned"] == "1000.00"
    assert body["spend_summary"]["state"] == "ready"
    assert body["spend_summary"]["amount"] == "250.00"
    assert body["remaining_budget"] == "750.00"


def test_marketing_dashboard_includes_workspace_overview(client: TestClient) -> None:
    _login(client)
    response = client.get("/marketing/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body.get("workspace_overview") is not None
    assert body["workspace_overview"]["total_campaigns"]["available"] is True
