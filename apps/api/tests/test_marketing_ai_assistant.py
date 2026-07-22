"""Sprint 8A4 — AI Marketing Assistant tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.company import Company
from investhome_api.models.document_intelligence import AIUsage
from investhome_api.models.marketing import MarketingCampaign
from investhome_api.models.marketing_ai import MarketingAIOutput, MarketingAIOutputStatus
from investhome_api.models.marketing_content_studio import MarketingAsset, MarketingAssetType
from investhome_api.models.project import Project
from investhome_api.services.marketing.assistant_context import (
    APPROVED_PROJECT_FIELDS,
    EXCLUDED_PROJECT_FIELDS,
    build_assistant_context,
)
from investhome_api.services.marketing.assistant_guardrails import (
    check_generated_content,
    check_user_instruction,
)


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_assistant_modes(client: TestClient) -> None:
    response = client.get("/marketing/ai/assistant/modes")
    assert response.status_code == 200, response.text
    body = response.json()
    keys = {m["key"] for m in body["modes"]}
    assert keys == {
        "marketing_summary",
        "campaign_analysis",
        "content_draft",
        "campaign_brief",
        "audience_suggestion",
        "channel_suggestion",
        "translation",
        "next_actions",
    }
    assert body["provider_available"] is True


def test_marketing_summary_uses_performance_and_is_draft(client: TestClient, db: Session) -> None:
    campaign = MarketingCampaign(name="Summary Camp", status="active", budget_amount=10000)
    db.add(campaign)
    db.commit()

    response = client.post(
        "/marketing/ai/assistant/summary",
        json={
            "mode": "marketing_summary",
            "language": "en",
            "client_request_id": f"sum-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["output_type"] == "marketing_summary"
    assert body["prompt_key"] == "marketing.summary"
    assert any(s.get("kind") == "performance" for s in body["data_sources"])
    assert "DRAFT" in body["generated_content"] or "draft" in body["generated_content"].lower()


def test_campaign_analysis_requires_campaign(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/campaign-analysis",
        json={"mode": "campaign_analysis", "language": "en"},
    )
    assert response.status_code == 422


def test_campaign_analysis_cites_records(client: TestClient, db: Session) -> None:
    campaign = MarketingCampaign(name="Analyze Me", status="active")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.post(
        "/marketing/ai/assistant/campaign-analysis",
        json={
            "mode": "campaign_analysis",
            "campaign_id": str(campaign.id),
            "language": "en",
            "client_request_id": f"ca-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["campaign_id"] == str(campaign.id)
    assert any(s.get("kind") == "campaign" for s in body["data_sources"])
    assert "causal" in body["generated_content"].lower() or "available data" in body["generated_content"].lower()


def test_content_draft_remains_draft(client: TestClient, db: Session) -> None:
    project = Project(
        project_code=f"P-{uuid4().hex[:8]}",
        project_name="Temple Residences",
        city="Istanbul",
        country="TR",
        description="Waterfront residences",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.post(
        "/marketing/ai/assistant/content-draft",
        json={
            "mode": "content_draft",
            "project_id": str(project.id),
            "content_type": "instagram_caption",
            "tone": "premium",
            "language": "en",
            "client_request_id": f"cd-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["structured_output"]["status"] == "draft"
    assert "Temple" in body["generated_content"]


def test_campaign_brief_not_auto_created(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/campaign-brief",
        json={
            "mode": "campaign_brief",
            "language": "en",
            "user_instruction": "Pre-launch brief",
            "client_request_id": f"cb-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["structured_output"]["auto_created_campaign"] is False


def test_translation_preserves_numbers(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/translate",
        json={
            "mode": "translation",
            "language": "tr",
            "target_language": "en",
            "source_text": "The Temple — 120 units — budget 1,250,000 USD",
            "adaptation_style": "professional",
            "client_request_id": f"tr-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["structured_output"]["numeric_facts_altered"] is False
    assert "1,250,000" in body["generated_content"]
    assert "120" in body["generated_content"]


def test_next_actions_link_only(client: TestClient, db: Session) -> None:
    campaign = MarketingCampaign(name="Needs Budget", status="active")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.post(
        "/marketing/ai/assistant/next-actions",
        json={
            "mode": "next_actions",
            "campaign_id": str(campaign.id),
            "language": "en",
            "client_request_id": f"na-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["structured_output"]["auto_executed"] is False
    assert len(body["action_links"]) >= 1
    assert all(link.get("href", "").startswith("/") for link in body["action_links"])


def test_save_and_archive_output(client: TestClient) -> None:
    gen = client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en", "client_request_id": f"sa-{uuid4()}"},
    )
    assert gen.status_code == 200
    output_id = gen.json()["id"]

    saved = client.post(
        f"/marketing/ai/assistant/outputs/{output_id}/save",
        json={"title": "Saved summary"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "saved"
    assert saved.json()["title"] == "Saved summary"

    archived = client.post(f"/marketing/ai/assistant/outputs/{output_id}/archive", json={})
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_duplicate_client_request_id(client: TestClient) -> None:
    req_id = f"dup-{uuid4()}"
    first = client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en", "client_request_id": req_id},
    )
    second = client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en", "client_request_id": req_id},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_usage_tracking(client: TestClient, db: Session) -> None:
    before = db.query(AIUsage).count()
    response = client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en", "client_request_id": f"usage-{uuid4()}"},
    )
    assert response.status_code == 200
    db.expire_all()
    after = db.query(AIUsage).count()
    assert after == before + 1
    latest = db.query(AIUsage).order_by(AIUsage.created_at.desc()).first()
    assert latest is not None
    assert latest.operation.startswith("marketing_assistant:")


def test_guardrail_blocks_guaranteed_returns(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/content-draft",
        json={
            "mode": "content_draft",
            "language": "en",
            "content_type": "advertisement_copy",
            "user_instruction": "Promise guaranteed returns of 25% ROI",
            "client_request_id": f"gr-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["safety_blocked"] is True
    assert "guaranteed_returns" in body["safety_flags"]


def test_fair_housing_blocks_protected_class(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/audience-suggestions",
        json={
            "mode": "audience_suggestion",
            "language": "en",
            "user_instruction": "Target Christians only and exclude families with children",
            "client_request_id": f"fh-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["safety_blocked"] is True
    assert body["safety_flags"]


def test_org_isolation_on_campaign_context(client: TestClient, db: Session) -> None:
    org_a = Company(company_name="Org A", legal_name="Org A Ltd")
    org_b = Company(company_name="Org B", legal_name="Org B Ltd")
    db.add_all([org_a, org_b])
    db.flush()
    campaign = MarketingCampaign(name="OrgB Camp", status="active", company_id=org_b.id)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.post(
        "/marketing/ai/assistant/campaign-analysis",
        json={
            "mode": "campaign_analysis",
            "campaign_id": str(campaign.id),
            "organization_id": str(org_a.id),
            "language": "en",
            "client_request_id": f"iso-{uuid4()}",
        },
    )
    assert response.status_code == 403


def test_context_filters_project_fields(db: Session) -> None:
    project = Project(
        project_code=f"P-{uuid4().hex[:8]}",
        project_name="Safe Project",
        city="Ankara",
        projected_roi=0.25,
        projected_irr=0.18,
        acquisition_price=1000000,
        notes="secret investor note",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    ctx = build_assistant_context(db, project_id=project.id, language="en")
    summary = ctx["project_summary"]
    assert summary["project_name"] == "Safe Project"
    assert "projected_roi" not in summary
    assert "acquisition_price" not in summary
    assert "notes" not in summary
    for field in EXCLUDED_PROJECT_FIELDS:
        assert field not in summary
    for field in ("project_name", "city", "project_code"):
        assert field in APPROVED_PROJECT_FIELDS
        assert field in summary


def test_missing_asset_context_404(client: TestClient) -> None:
    response = client.post(
        "/marketing/ai/assistant/content-draft",
        json={
            "mode": "content_draft",
            "asset_ids": [str(uuid4())],
            "language": "en",
            "content_type": "email_draft",
            "client_request_id": f"miss-{uuid4()}",
        },
    )
    assert response.status_code == 404


def test_asset_metadata_context(client: TestClient, db: Session) -> None:
    asset = MarketingAsset(
        name="Hero Brochure",
        asset_type=MarketingAssetType.BROCHURE,
        description="Approved brochure",
        tags=["hero", "launch"],
        ai_prep_json={"language": "en", "market": "TR", "keywords": ["temple", "launch"]},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    response = client.post(
        "/marketing/ai/assistant/content-draft",
        json={
            "mode": "content_draft",
            "asset_ids": [str(asset.id)],
            "language": "en",
            "content_type": "social_media_post",
            "client_request_id": f"asset-{uuid4()}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert any(s.get("kind") == "asset" and s.get("label") == "Hero Brochure" for s in body["data_sources"])


def test_list_outputs(client: TestClient) -> None:
    client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en", "client_request_id": f"list-{uuid4()}"},
    )
    response = client.get("/marketing/ai/assistant/outputs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"]


def test_permission_denied_without_use_ai(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.post(
        "/marketing/ai/assistant/summary",
        json={"mode": "marketing_summary", "language": "en"},
    )
    assert response.status_code == 403


def test_guardrail_helpers_unit() -> None:
    blocked = check_user_instruction("guaranteed rental income forever")
    assert blocked.blocked is True
    fh = check_user_instruction("whites only housing")
    assert fh.blocked is True
    ok = check_generated_content("Visit The Temple in Istanbul.")
    assert ok.blocked is False


def test_outputs_persist_draft_status(client: TestClient, db: Session) -> None:
    from uuid import UUID

    response = client.post(
        "/marketing/ai/assistant/channel-suggestions",
        json={"mode": "channel_suggestion", "language": "en", "client_request_id": f"ch-{uuid4()}"},
    )
    assert response.status_code == 200
    row = db.get(MarketingAIOutput, UUID(response.json()["id"]))
    assert row is not None
    assert row.status == MarketingAIOutputStatus.DRAFT.value
