"""Sprint 8A3 — campaign performance and lead attribution tests."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.marketing import (
    CampaignBudgetAllocation,
    MarketingCampaign,
    MarketingCampaignObjective,
    MarketingCampaignPrimaryChannel,
    MarketingCampaignStatus,
    MarketingCampaignType,
)
from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution
from investhome_api.models.sales import OpportunityStage, SalesOpportunity
from investhome_api.services.marketing.lead_status_mapping import (
    AttributionLeadStatus,
    map_lead_status,
    resolve_lead_attribution_status,
)


def _login(client: TestClient) -> None:
    pass


def _create_campaign(client: TestClient, **overrides) -> dict:
    payload = {
        "name": f"Perf Campaign {uuid4().hex[:6]}",
        "objective": "lead_generation",
        "campaign_type": "lead_generation",
        "priority": "normal",
        "budget_amount": "5000.00",
        "budget_currency": "USD",
        "primary_channel": "meta",
        "channel_ids": [],
        "audience_ids": [],
    }
    payload.update(overrides)
    response = client.post("/marketing/campaigns", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["campaign"]


def _create_lead(client: TestClient, **overrides) -> dict:
    payload = {
        "full_name": f"Lead {uuid4().hex[:6]}",
        "email": f"lead-{uuid4().hex[:6]}@example.com",
        "status": "New",
    }
    payload.update(overrides)
    response = client.post("/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_attribution(client: TestClient, lead_id: str, campaign_id: str, **overrides) -> dict:
    payload = {
        "lead_id": lead_id,
        "campaign_id": campaign_id,
        "attribution_source": "manual",
        **overrides,
    }
    response = client.post("/marketing/performance/attributions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_attribution_and_get(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    body = _create_attribution(client, lead["id"], campaign["id"])
    assert body["lead_id"] == lead["id"]
    assert body["campaign_id"] == campaign["id"]
    assert body["attribution_source"] == "manual"


def test_attribution_duplicate_rejected(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    _create_attribution(client, lead["id"], campaign["id"])
    dup = client.post(
        "/marketing/performance/attributions",
        json={"lead_id": lead["id"], "campaign_id": campaign["id"], "attribution_source": "manual"},
    )
    assert dup.status_code == 409


def test_archived_campaign_not_selectable(client: TestClient, db: Session) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    row = db.get(MarketingCampaign, UUID(campaign["id"]))
    row.status = MarketingCampaignStatus.ARCHIVED
    db.commit()
    response = client.post(
        "/marketing/performance/attributions",
        json={"lead_id": lead["id"], "campaign_id": campaign["id"], "attribution_source": "manual"},
    )
    assert response.status_code == 409


def test_update_attribution_manual_change(client: TestClient) -> None:
    _login(client)
    campaign_a = _create_campaign(client, name="Campaign A")
    campaign_b = _create_campaign(client, name="Campaign B")
    lead = _create_lead(client)
    created = _create_attribution(client, lead["id"], campaign_a["id"])
    updated = client.put(
        f"/marketing/performance/attributions/{created['id']}",
        json={"campaign_id": campaign_b["id"], "attribution_reason": "Corrected source"},
    )
    assert updated.status_code == 200
    assert updated.json()["campaign_id"] == campaign_b["id"]


def test_campaign_performance_metrics(client: TestClient, db: Session) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client, status="Qualified")
    _create_attribution(client, lead["id"], campaign["id"])

    allocation = CampaignBudgetAllocation(
        campaign_id=UUID(campaign["id"]),
        name="Main",
        planned_amount=Decimal("5000"),
        spent_amount=Decimal("1000"),
        currency="USD",
    )
    db.add(allocation)
    db.commit()

    response = client.get(f"/marketing/performance/campaigns/{campaign['id']}")
    assert response.status_code == 200
    body = response.json()
    metrics = body["metrics"]
    assert metrics["total_leads"]["value"] == 1
    assert metrics["actual_spend"]["state"] == "ready"
    assert metrics["cpl"]["state"] == "ready"


def test_zero_division_safe_metrics(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    response = client.get(f"/marketing/performance/campaigns/{campaign['id']}")
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["conversion_rate"]["state"] == "unavailable"
    assert metrics["cpl"]["state"] == "unavailable"


def test_channel_and_project_reports(client: TestClient) -> None:
    _login(client)
    _create_campaign(client, primary_channel="google")
    channels = client.get("/marketing/performance/channels")
    assert channels.status_code == 200
    assert any(item["channel"] == "GOOGLE" for item in channels.json()["items"])
    projects = client.get("/marketing/performance/projects")
    assert projects.status_code == 200
    assert any(item["project_name"] == "Unassigned" for item in projects.json()["items"])


def test_performance_overview(client: TestClient) -> None:
    _login(client)
    _create_campaign(client)
    response = client.get("/marketing/performance/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["total_campaigns"]["value"] >= 1


def test_lead_create_with_attribution(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    response = client.post(
        "/leads",
        json={
            "full_name": "Attributed Lead",
            "email": f"attr-{uuid4().hex[:6]}@example.com",
            "attribution": {
                "campaign_id": campaign["id"],
                "utm_source": "google",
                "utm_medium": "cpc",
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["attribution"] is not None
    assert body["attribution"]["campaign_id"] == campaign["id"]
    assert body["attribution"]["utm_source"] == "google"


def test_campaign_leads_breakdown(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    _create_attribution(client, lead["id"], campaign["id"])
    response = client.get(f"/marketing/performance/campaigns/{campaign['id']}/leads")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["lead_id"] == lead["id"]


def test_csv_export_campaigns(client: TestClient) -> None:
    _login(client)
    _create_campaign(client)
    response = client.get("/marketing/performance/export/campaigns")
    assert response.status_code == 200
    assert "campaign_id" in response.text


def test_lead_status_mapping(db: Session) -> None:
    assert map_lead_status(LeadStatus.NEW) == AttributionLeadStatus.NEW
    assert map_lead_status(LeadStatus.WON) == AttributionLeadStatus.CONVERTED

    lead = Lead(full_name="Opp Lead", email=f"opp-{uuid4().hex[:6]}@example.com", status=LeadStatus.QUALIFIED)
    db.add(lead)
    db.flush()
    opp = SalesOpportunity(
        opportunity_code=f"OPP-{uuid4().hex[:8].upper()}",
        lead_id=lead.id,
        party_id=lead.id,
        party_type="lead",
        stage=OpportunityStage.WON,
        expected_revenue=Decimal("100000"),
        currency="USD",
    )
    db.add(opp)
    db.flush()
    assert resolve_lead_attribution_status(db, lead.id) == AttributionLeadStatus.CONVERTED


def test_list_attributions_filter_by_campaign(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    _create_attribution(client, lead["id"], campaign["id"])
    response = client.get(f"/marketing/performance/attributions?campaign_id={campaign['id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_delete_attribution(client: TestClient) -> None:
    _login(client)
    campaign = _create_campaign(client)
    lead = _create_lead(client)
    created = _create_attribution(client, lead["id"], campaign["id"])
    deleted = client.delete(f"/marketing/performance/attributions/{created['id']}?reason=test")
    assert deleted.status_code == 204
    listing = client.get("/marketing/performance/attributions")
    assert listing.json()["total"] == 0
