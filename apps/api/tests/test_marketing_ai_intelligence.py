"""Marketing AI intelligence tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingCampaign, MarketingLeadContext
from investhome_api.models.marketing_ai import (
    AIConfidenceLevel,
    AIRecommendationType,
    MarketingAIRecommendation,
)


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_ai_dashboard_loads(client: TestClient) -> None:
    response = client.get("/marketing/ai/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "executive_summary" in body
    assert "marketing_health" in body
    assert body["prediction_confidence"]["confidence"] == "unknown"


def test_predictions_framework_unknown_without_model(client: TestClient) -> None:
    response = client.get("/marketing/ai/predictions")
    assert response.status_code == 200
    frameworks = response.json()["frameworks"]
    assert len(frameworks) >= 7
    for fw in frameworks:
        assert fw["model_connected"] is False
        for item in fw["items"]:
            assert item["confidence"] == "unknown"
            assert item["value"] is None


def test_insights_returns_derived_or_empty(client: TestClient) -> None:
    response = client.get("/marketing/ai/insights")
    assert response.status_code == 200
    assert "items" in response.json()


def test_insights_with_lead_data(client: TestClient, db: Session) -> None:
    ctx = MarketingLeadContext(marketing_status="qualified", verification_status="verified")
    db.add(ctx)
    db.commit()

    response = client.get("/marketing/ai/insights")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any("lead" in i["title"].lower() for i in items)


def test_recommendations_require_evidence_fields(client: TestClient, db: Session) -> None:
    rec = MarketingAIRecommendation(
        recommendation_type=AIRecommendationType.FIX_TRACKING,
        title="Fix tracking",
        rationale="Missing evidence",
        confidence=AIConfidenceLevel.UNKNOWN,
        requires_evidence=True,
        evidence_refs=None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    accept = client.post(f"/marketing/ai/recommendations/{rec.id}/accept", json={})
    assert accept.status_code == 422


def test_copilot_insufficient_data_for_unknown_intent(client: TestClient) -> None:
    response = client.post("/marketing/ai/copilot", json={"query": "tell me something random xyz"})
    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_data"] is True
    assert body["confidence"] == "unknown"
    assert body["model_connected"] is False


def test_copilot_country_conversion_insufficient(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/copilot",
        json={"query": "What is the country conversion rate for Germany?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "country_conversion"
    assert body["insufficient_data"] is True
    assert "Insufficient data" in body["answer"]


def test_copilot_predict_leads_no_fabrication(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/copilot",
        json={"query": "Predict qualified leads for next month"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "predict_leads"
    assert body["insufficient_data"] is True
    assert "not connected" in body["answer"].lower()


def test_copilot_best_campaign_with_data(client: TestClient, db: Session) -> None:
    campaign = MarketingCampaign(name="Top Campaign", status="active")
    db.add(campaign)
    db.flush()
    db.add(MarketingLeadContext(campaign_id=campaign.id, marketing_status="new"))
    db.commit()

    response = client.post("/marketing/ai/copilot", json={"query": "Which is the best campaign?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "best_campaign"
    assert "Top Campaign" in body["answer"]
    assert body["confidence"] in ("low", "medium", "high")


def test_copilot_nl_query_parsing(client: TestClient) -> None:
    cases = [
        ("Why did leads decrease last week?", "lead_decrease"),
        ("Compare campaign performance", "comparison"),
        ("Budget allocation recommendations", "budget_allocation"),
    ]
    for query, expected_intent in cases:
        response = client.post("/marketing/ai/copilot", json={"query": query})
        assert response.status_code == 200
        assert response.json()["intent"] == expected_intent


def test_briefing_unknown_without_data(client: TestClient) -> None:
    response = client.get("/marketing/ai/briefings?period=weekly")
    assert response.status_code == 200
    briefing = response.json()["briefing"]
    assert briefing["confidence"] in ("unknown", "low", "medium", "high")


def test_ai_health_endpoint(client: TestClient) -> None:
    response = client.get("/marketing/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "unknown"
    assert any(c["key"] == "prediction_pipeline" for c in body["categories"])


def test_ai_settings(client: TestClient) -> None:
    response = client.get("/marketing/ai/settings")
    assert response.status_code == 200
    assert response.json()["model_pipeline_connected"] is False


def test_ai_permissions_readonly_denied(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.post("/marketing/ai/copilot", json={"query": "best campaign"})
    assert response.status_code == 403


def test_anomalies_empty_by_default(client: TestClient) -> None:
    response = client.get("/marketing/ai/anomalies")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_recommendation_accept_with_evidence(client: TestClient, db: Session) -> None:
    rec = MarketingAIRecommendation(
        recommendation_type=AIRecommendationType.INCREASE_BUDGET,
        title="Increase budget",
        rationale="Strong lead volume",
        confidence=AIConfidenceLevel.MEDIUM,
        requires_evidence=True,
        evidence_refs=[{"source": "analytics.kpis", "metric_key": "marketing_leads", "value": "10"}],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    accept = client.post(f"/marketing/ai/recommendations/{rec.id}/accept", json={"notes": "Approved"})
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"


def test_no_fabricated_prediction_values(client: TestClient) -> None:
    response = client.get("/marketing/ai/predictions")
    assert response.status_code == 200
    for fw in response.json()["frameworks"]:
        for item in fw["items"]:
            if item["confidence"] == "unknown":
                assert item["value"] is None
