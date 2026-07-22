"""Marketing analytics dashboard tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingCampaign, MarketingLeadContext
from investhome_api.models.marketing_analytics import MarketingExecutiveAlert, MarketingMetricsRegistry


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_executive_dashboard_loads(client: TestClient) -> None:
    response = client.get("/marketing/analytics/executive")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "kpis" in body
    assert "funnel" in body
    assert "health" in body
    assert "widgets" in body
    assert len(body["kpis"]) >= 10


def test_kpis_honest_unknown_states(client: TestClient) -> None:
    response = client.get("/marketing/analytics/kpis")
    assert response.status_code == 200
    kpis = {k["key"]: k for k in response.json()["kpis"]}
    assert kpis["meetings"]["state"] == "unknown"
    assert kpis["reservations"]["state"] == "unknown"
    assert kpis["sales"]["state"] == "unknown"
    assert kpis["revenue"]["state"] == "unknown"
    assert kpis["conversion_rate"]["state"] == "unknown"


def test_kpis_with_lead_data(client: TestClient, db: Session) -> None:
    ctx = MarketingLeadContext(marketing_status="qualified", verification_status="verified")
    db.add(ctx)
    db.commit()

    response = client.get("/marketing/analytics/kpis")
    assert response.status_code == 200
    kpis = {k["key"]: k for k in response.json()["kpis"]}
    assert kpis["marketing_leads"]["state"] == "ready"
    assert kpis["marketing_leads"]["value"] == 1
    assert kpis["qualified_leads"]["value"] == 1


def test_funnel_unknown_stages(client: TestClient) -> None:
    response = client.get("/marketing/analytics/funnel")
    assert response.status_code == 200
    stages = {s["key"]: s for s in response.json()["stages"]}
    assert stages["visitors"]["state"] == "unknown"
    assert stages["landing_page_views"]["state"] == "unknown"
    assert stages["opportunity"]["state"] == "unknown"
    assert stages["sale"]["state"] == "unknown"


def test_health_categories(client: TestClient) -> None:
    response = client.get("/marketing/analytics/health")
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] in ("healthy", "warning", "critical", "unknown")
    assert len(body["categories"]) == 10
    keys = {c["key"] for c in body["categories"]}
    assert "tracking" in keys
    assert "consent" in keys


def test_tracking_health_requires_attribution_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/marketing/analytics/health/tracking")
    assert response.status_code == 403


def test_widgets_endpoint(client: TestClient) -> None:
    response = client.get("/marketing/analytics/widgets")
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_key"] == "executive"
    assert len(body["widgets"]) >= 5


def test_saved_views_crud(client: TestClient) -> None:
    create = client.post(
        "/marketing/analytics/saved-views",
        json={"name": "My Executive View", "dashboard_key": "executive", "filters_json": {"campaign_id": None}},
    )
    assert create.status_code == 201, create.text
    view_id = create.json()["id"]

    listed = client.get("/marketing/analytics/saved-views")
    assert listed.status_code == 200
    assert any(v["id"] == view_id for v in listed.json())

    updated = client.put(f"/marketing/analytics/saved-views/{view_id}", json={"name": "Updated View"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated View"

    deleted = client.delete(f"/marketing/analytics/saved-views/{view_id}")
    assert deleted.status_code == 204


def test_layout_crud(client: TestClient) -> None:
    create = client.post(
        "/marketing/analytics/layouts",
        json={"name": "Executive Default", "dashboard_key": "executive", "widgets_json": [{"key": "kpi_bar"}]},
    )
    assert create.status_code == 201, create.text
    layout_id = create.json()["id"]

    listed = client.get("/marketing/analytics/layouts")
    assert listed.status_code == 200
    assert any(l["id"] == layout_id for l in listed.json())

    deleted = client.delete(f"/marketing/analytics/layouts/{layout_id}")
    assert deleted.status_code == 204


def test_executive_alerts(client: TestClient, db: Session) -> None:
    from investhome_api.models.marketing_analytics import ExecutiveAlertSeverity

    alert = MarketingExecutiveAlert(
        title="Missing tracking on campaign",
        message="Campaign has no UTM defaults configured",
        category="tracking",
        severity=ExecutiveAlertSeverity.WARNING,
        evidence_json={"campaign_id": str(uuid4()), "issue": "no_utm"},
        is_resolved=False,
    )
    db.add(alert)
    db.commit()

    response = client.get("/marketing/analytics/alerts")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1
    assert response.json()["items"][0]["evidence_json"] is not None


def test_metrics_registry_seeded(client: TestClient, db: Session) -> None:
    from sqlalchemy import func, select

    count = db.scalar(select(func.count()).select_from(MarketingMetricsRegistry)) or 0
    if count == 0:
        from investhome_api.models.marketing_analytics import MetricAggregationType

        db.add(
            MarketingMetricsRegistry(
                metric_key="marketing_leads",
                label="Marketing Leads",
                source_entity="marketing_lead_contexts",
                aggregation_type=MetricAggregationType.COUNT,
                permission_requirement="view_leads",
            )
        )
        db.commit()

    response = client.get("/marketing/analytics/kpis")
    assert response.status_code == 200
    assert any(k["key"] == "marketing_leads" for k in response.json()["kpis"])


def test_time_filter_presets(client: TestClient) -> None:
    for preset in ("today", "last_7_days", "last_30_days", "quarter", "year"):
        response = client.get(f"/marketing/analytics/kpis?preset={preset}")
        assert response.status_code == 200, f"preset {preset} failed"
        assert response.json()["time_filter"]["preset"] == preset


def test_dashboard_permissions_forbidden(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.get("/marketing/analytics/executive")
    assert response.status_code == 403


def test_campaign_filter(client: TestClient, db: Session) -> None:
    campaign = MarketingCampaign(name=f"Filter Test {uuid4().hex[:6]}")
    db.add(campaign)
    db.flush()
    db.add(MarketingLeadContext(campaign_id=campaign.id))
    db.add(MarketingLeadContext())
    db.commit()

    response = client.get(f"/marketing/analytics/kpis?campaign_id={campaign.id}")
    assert response.status_code == 200
    kpis = {k["key"]: k for k in response.json()["kpis"]}
    assert kpis["marketing_leads"]["value"] == 1
