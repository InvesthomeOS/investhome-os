"""Creative Director foundation tests — mock LLM, real asset lock, Claim Guard honesty."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.creative_director.brief import (
    contains_cliche,
    generate_creative_strategy,
)
from investhome_api.services.creative_director.orchestrator import (
    assign_capabilities,
    infer_required_capabilities,
)
from investhome_api.services.creative_director.pricing import (
    build_pricing_claims,
    compute_discount_percent,
)
from investhome_api.services.creative_director.research import (
    pick_real_interior,
    pick_real_logo,
    score_interior_candidate,
)
from investhome_api.services.gpt_image_design.source import TEMPLE_PRIMARY_LOGO_ID
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")

BRIEF = (
    "The Temple projesinin gerçek interior görsellerini kullan. "
    "Unit 204 lansman kampanyası yapıyoruz. "
    "Normal fiyat $400,000, lansman fiyatı $300,000. "
    "Modern, şık ve tarihi karakterini ön plana çıkar. "
    "Bunu Washington DC'de seçkin bir yaşam ve yatırım fırsatı olarak anlat."
)


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    return _db()


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "local")
    monkeypatch.setenv("AI_MODEL", "local-grounded-v1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_project(db: Session, *, project_id: UUID | None = None) -> Project:
    pid = project_id or uuid4()
    existing = db.get(Project, pid)
    if existing is not None:
        return existing
    project = Project(
        id=pid,
        project_code=f"TMP-{uuid4().hex[:6]}",
        project_name="The Temple",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        city="Washington",
        state="DC",
        country="US",
        address="1610 Columbia Rd NW",
        total_units=120,
    )
    db.add(project)
    db.flush()
    return project


def _asset(
    db: Session,
    project: Project,
    *,
    asset_id: UUID | None = None,
    filename: str,
    content_type: str = "image/jpeg",
    folder_category: str = "02_RENDER",
    tags: list[str] | None = None,
    width: int = 1600,
    height: int = 1200,
) -> CreativeStudioMediaAsset:
    asset = CreativeStudioMediaAsset(
        id=asset_id or uuid4(),
        filename=filename,
        content_type=content_type,
        file_size=2048,
        width=width,
        height=height,
        storage_provider="google_drive",
        storage_key=f"gdrive:{uuid4().hex}",
        linked_project_id=project.id,
        source_type=MediaAssetSourceType.GOOGLE_DRIVE.value,
        external_file_id=f"file-{uuid4().hex[:8]}",
        external_checksum="c1",
        sync_status=MediaAssetSyncStatus.ACTIVE.value,
        folder_category=folder_category,
        tags=tags or [],
    )
    db.add(asset)
    db.flush()
    return asset


def test_discount_percent_is_deterministic() -> None:
    pct = compute_discount_percent(Decimal("400000"), Decimal("300000"))
    assert pct == Decimal("25.00")


def test_pricing_claims_tag_user_brief_sources() -> None:
    result = build_pricing_claims(brief=BRIEF, drive_prices={"units": {}})
    assert result["list_price"] == 400000.0
    assert result["launch_price"] == 300000.0
    assert result["discount"]["percent"] == 25.0
    assert result["discount"]["display"] == "~25%"
    assert result["honesty"]["prices_from_user_brief"] is True
    assert result["honesty"]["invented_yields"] is False
    sources = {c["key"]: c["source"] for c in result["claims"]}
    assert sources["list_price"] == "user_campaign_input"
    assert sources["launch_price"] == "user_campaign_input"
    assert sources["launch_discount_percent"] == "derived_safe"
    assert sources["unit_code"] == "user_campaign_input"
    copy = result["price_presentation"]["copy"]
    assert "launch price advantage" in copy
    assert "% off" not in copy.lower()
    assert "roi" not in copy.lower()
    assert "return" not in copy.lower()


def test_local_strategy_avoids_listing_cliches() -> None:
    pricing = build_pricing_claims(brief=BRIEF)
    strategy = generate_creative_strategy(
        user_brief=BRIEF,
        project={"name": "The Temple", "city": "Washington", "state": "DC"},
        research_summary={},
        pricing=pricing,
        mode="project",
    )
    blob = " ".join(
        [
            str(strategy.get("big_idea") or ""),
            str(strategy.get("hero_message") or ""),
            str(strategy.get("cta") or ""),
            str(strategy.get("sales_hook") or ""),
            str(strategy.get("value_proposition") or ""),
            " ".join(str(m) for m in (strategy.get("supporting_messages") or [])),
        ]
    )
    assert not contains_cliche(blob)
    assert "discover the elegance" not in blob.lower()
    assert "schedule a viewing" not in blob.lower()
    assert "prestigious address" not in blob.lower()
    assert "launch price advantage" in str(strategy.get("value_proposition") or "").lower()
    assert strategy.get("big_idea")
    assert strategy.get("cta")


def test_pick_real_interior_rejects_exterior_fallback() -> None:
    exterior = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="temple_exterior_facade.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["exterior", "facade"],
        score=9.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="EXTERIOR",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    interior = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="temple_living_interior.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
        score=5.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="INTERIOR",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    picked, _, _ = pick_real_interior([exterior, interior], brief=BRIEF)
    assert picked is not None
    assert picked.asset_id == interior.asset_id
    none_pick, _, _ = pick_real_interior([exterior], brief=BRIEF)
    assert none_pick is None


def test_interior_scoring_prefers_better_living_candidate() -> None:
    """Filename-first bedroom must lose to higher-quality living interior."""
    weak_bedroom = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="AAA_Render_Bedroom_001.jpg",  # sorts first alphabetically
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["interior", "bedroom"],
        score=9.5,  # high retrieval score alone must not win
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="INTERIOR",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    strong_living = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="ZZZ_Living_Room_Hero.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living", "lobby"],
        score=4.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="INTERIOR",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    dims = {
        weak_bedroom.asset_id: (800, 1200),  # low-res portrait
        strong_living.asset_id: (2400, 1600),  # hi-res landscape
    }
    weak_score, _ = score_interior_candidate(
        weak_bedroom, brief=BRIEF, width=800, height=1200
    )
    strong_score, reason = score_interior_candidate(
        strong_living, brief=BRIEF, width=2400, height=1600
    )
    assert strong_score > weak_score
    assert "living" in reason or "brief_character_fit" in reason

    picked, score, pick_reason = pick_real_interior(
        [weak_bedroom, strong_living],
        brief=BRIEF,
        dimensions=dims,
    )
    assert picked is not None
    assert picked.asset_id == strong_living.asset_id
    assert score is not None and score > 0
    assert pick_reason


def test_logo_lock_prefers_temple_primary() -> None:
    other = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="random_mark.png",
        content_type="image/png",
        folder_category="01_BRAND",
        tags=["logo"],
        score=8.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="BRANDING",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    primary = SocialDesignMediaCandidate(
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary", "temple"],
        score=3.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="BRANDING",
        source_type="google_drive",
        provenance_source="google_drive",
    )
    picked = pick_real_logo(
        [other, primary],
        project_name="The Temple",
        project_code="IH-DC-TMP-001",
    )
    assert picked is not None
    assert picked.asset_id == TEMPLE_PRIMARY_LOGO_ID


def test_missing_video_capability_reported_without_silent_fallback() -> None:
    required = infer_required_capabilities(brief=BRIEF, mode="project")
    required = list(required) + ["video_generate"]
    plan = assign_capabilities(required)
    assert "video_generate" in plan.missing_capabilities
    video = next(a for a in plan.assignments if a.capability == "video_generate")
    assert video.missing is True
    assert video.available is False
    # text/reasoning still available via local GPT mapping
    text = next(a for a in plan.assignments if a.capability == "text")
    assert text.available is True
    assert text.missing is False


def test_create_campaign_endpoint_locks_interior_and_logo(
    client,
    db_session: Session,
) -> None:
    # Isolated project so real Temple Drive assets cannot steal the interior pick.
    project = _create_project(db_session, project_id=uuid4())
    interior = _asset(
        db_session,
        project,
        filename="Temple_Unit_Living_Interior.jpg",
        folder_category="02_RENDER",
        tags=["interior", "living", "temple"],
        width=2400,
        height=1600,
    )
    _asset(
        db_session,
        project,
        filename="AAA_Bedroom_001.jpg",
        folder_category="02_RENDER",
        tags=["interior", "bedroom"],
        width=800,
        height=600,
    )
    _asset(
        db_session,
        project,
        filename="Temple_Exterior_Street.jpg",
        folder_category="06_MEDIA",
        tags=["exterior", "street"],
    )
    logo = _asset(
        db_session,
        project,
        filename="Temple_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary", "temple"],
    )
    db_session.commit()

    response = client.post(
        "/ai/creative-studio/campaigns",
        json={
            "project_id": str(project.id),
            "brief": BRIEF,
            "mode": "project",
            "include_video_capability": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    brief = body["brief"]

    assert body["campaign_id"]
    assert brief["image_generation_performed"] is False
    assert brief["generated_assets"] == []

    selected_ids = {a["asset_id"] for a in brief["selected_assets"]}
    assert str(interior.id) in selected_ids
    assert str(logo.id) in {a["asset_id"] for a in brief["brand_assets"]}
    # Real project logo only — never invent a global Investhome mark as substitute.
    for brand in brief["brand_assets"]:
        assert "investhome" not in (brand.get("filename") or "").lower() or "temple" in (
            brand.get("filename") or ""
        ).lower()
        assert brand.get("role") == "project_logo"

    # Exterior must not be the locked hero when interiors exist.
    for asset in brief["selected_assets"]:
        assert "exterior" not in (asset.get("filename") or "").lower()
        assert asset.get("selection_reason")

    pricing = brief["pricing"]
    assert pricing["list"] == "$400,000"
    assert pricing["offer"] == "$300,000"
    assert pricing["discount"]["display"] == "~25%"
    assert "launch price advantage" in (pricing.get("copy") or "")

    claim_sources = {c["key"]: c["source"] for c in brief["claims"]}
    assert claim_sources["list_price"] == "user_campaign_input"
    assert claim_sources["launch_discount_percent"] == "derived_safe"

    assert "video_generate" in brief["missing_capabilities"]
    assert brief["hero_message"]
    assert brief["cta"]
    assert brief["concept"]
    assert brief.get("big_idea")
    assert not contains_cliche(brief["hero_message"])
    assert not contains_cliche(brief["cta"])
    assert "launch price advantage" in str(brief.get("value_proposition") or "").lower()

    # Persist round-trip
    get_resp = client.get(f"/ai/creative-studio/campaigns/{body['campaign_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["campaign_id"] == body["campaign_id"]
    assert get_resp.json()["campaign_context"]["original_user_brief"] == BRIEF

    revise = client.post(
        f"/ai/creative-studio/campaigns/{body['campaign_id']}/revise",
        json={"instruction": "Make the CTA softer"},
    )
    assert revise.status_code == 200
    assert revise.json()["campaign_context"]["latest_revision_instruction"] == "Make the CTA softer"


def test_no_silent_image_provider_fallback_in_registry() -> None:
    """Missing image providers must be flagged — never pretend another provider ran."""
    plan = assign_capabilities(["image_generate", "image_edit", "video_generate"])
    for assignment in plan.assignments:
        if not assignment.available:
            assert assignment.missing is True
            assert assignment.reason


def _seed_campaign_context(
    db: Session,
    *,
    project: Project,
    interior: CreativeStudioMediaAsset,
    logo: CreativeStudioMediaAsset,
    language: str | None = None,
) -> UUID:
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign

    pricing = build_pricing_claims(brief=BRIEF, drive_prices={"units": {"204": {"found": True}}})
    interior_meta = {
        "asset_id": str(interior.id),
        "filename": interior.filename,
        "content_type": interior.content_type,
        "folder_category": interior.folder_category,
        "visual_subject": "INTERIOR",
        "tags": list(interior.tags or []),
        "role": "hero_interior",
        "provenance_source": "google_drive",
    }
    logo_meta = {
        "asset_id": str(logo.id),
        "filename": logo.filename,
        "content_type": logo.content_type,
        "folder_category": logo.folder_category,
        "visual_subject": "BRANDING",
        "tags": list(logo.tags or []),
        "role": "project_logo",
        "provenance_source": "google_drive",
    }
    ctx = {
        "original_user_brief": BRIEF,
        "language": language,
        "cd_strategy": {
            "big_idea": "History Meets Modernity",
            "hero_message": "Own a Piece of History with a Modern Twist",
            "sales_hook": "Unit 204 Launch Opportunity",
            "offer": "$400,000 → $300,000 (~25% launch price advantage)",
            "value_proposition": "~25% launch price advantage",
            "cta": "Explore Unit 204 Details",
            "tone": "premium luxury editorial",
            "visual_direction": "Real interior, historic + modern living",
            "composition_direction": "Flexible premium editorial",
            "emphasis": ["History", "Modern", "Launch Price", "25% Advantage"],
            "supporting_messages": [
                "The Temple, Washington DC, historic, modern living",
            ],
        },
        "campaign_copy": {
            "big_idea": "History Meets Modernity",
            "hero_message": "Own a Piece of History with a Modern Twist",
            "sales_hook": "Unit 204 Launch Opportunity",
            "offer": "Launch Price: $300,000",
            "cta": "Explore Unit 204 Details",
            "value_proposition": "~25% launch price advantage",
            "emphasis": ["History", "Modern", "Launch Price", "25% Advantage"],
            "supporting_messages": [
                "The Temple, Washington DC, historic, modern living",
            ],
        },
        "approved_claims": pricing["claims"],
        "pricing": pricing,
        "selected_assets": [interior_meta],
        "selected_logo": logo_meta,
        "drive_research": {
            "selected_interior": interior_meta,
            "selected_logo": logo_meta,
        },
        "generated_assets": [],
        "output_history": [],
        "image_generation_performed": False,
    }
    row = CreativeDirectorCampaign(
        linked_project_id=project.id,
        mode="project",
        original_brief=BRIEF,
        context_json=ctx,
        status="draft",
    )
    db.add(row)
    db.flush()
    return row.id


def test_generate_ad_finished_ad_default_skips_os_compose_path(
    client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    from investhome_api.schemas.gpt_image_design import (
        GptImageDesignResponse,
        GptImageOutput,
        GptImageSourceImage,
    )

    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    project = _create_project(db_session, project_id=uuid4())
    interior = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
    )
    logo = _asset(
        db_session,
        project,
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary"],
    )
    campaign_id = _seed_campaign_context(
        db_session,
        project=project,
        interior=interior,
        logo=logo,
        language=None,
    )
    db_session.commit()

    final_id = uuid4()
    captured: dict = {}

    def fake_generate(db, user, body):
        captured["body"] = body
        assert body.language == "tr"
        assert body.selected_asset_ids == [interior.id]
        assert body.builder_context["finished_ad"] is True
        assert body.builder_context["production_mode"] == "finished_ad"
        assert body.builder_context.get("production_brief")
        assert body.builder_context.get("image_provider_route")
        assert "FINISHED PROFESSIONAL" in body.instruction
        assert "Living_Room_003" in body.instruction
        assert body.builder_context.get("master_ad") is not True
        tokens = body.builder_context["approved_financial_tokens"]
        assert "$400,000" in tokens
        assert "$300,000" in tokens
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id="test-session",
            linked_project_id=project.id,
            campaign_context_id=str(campaign_id),
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=interior.id,
                filename=interior.filename,
                content_type=interior.content_type,
                folder_category=interior.folder_category,
                tags=list(interior.tags or []),
                role="source",
            ),
            brief={"prompt": body.instruction[:500]},
            outputs=[
                GptImageOutput(
                    local_asset_id=final_id,
                    local_asset_url=f"/creative-studio/media/assets/{final_id}/content",
                    metadata={"production_mode": "finished_ad"},
                )
            ],
            warnings=[],
            provider_call_count=1,
            latency_ms=12,
        )

    with patch(
        "investhome_api.services.creative_director.generate_ad.generate_gpt_image_creatives",
        side_effect=fake_generate,
    ):
        resp = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "format_preset": "portrait"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["production_mode"] == "finished_ad"
    assert body.get("provider_route")
    assert body["final_asset_id"] == str(final_id)
    assert body["claim_guard"]["status"] == "pass"


def test_generate_ad_os_compose_mode_still_available(
    client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    from investhome_api.schemas.gpt_image_design import (
        GptImageDesignResponse,
        GptImageOutput,
        GptImageSourceImage,
    )

    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    project = _create_project(db_session, project_id=uuid4())
    interior = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
    )
    logo = _asset(
        db_session,
        project,
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary"],
    )
    campaign_id = _seed_campaign_context(
        db_session,
        project=project,
        interior=interior,
        logo=logo,
        language=None,
    )
    db_session.commit()

    def fake_generate(db, user, body):
        assert body.builder_context.get("master_ad") is True
        assert body.builder_context.get("finished_ad") is not True
        assert "ADVERTISING ART DIRECTION" in body.instruction
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id="test-session",
            linked_project_id=project.id,
            campaign_context_id=str(campaign_id),
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=interior.id,
                filename=interior.filename,
                content_type=interior.content_type,
                folder_category=interior.folder_category,
                tags=list(interior.tags or []),
                role="source",
            ),
            brief={"prompt": body.instruction[:500]},
            outputs=[
                GptImageOutput(
                    local_asset_id=uuid4(),
                    local_asset_url="/creative-studio/media/assets/x/content",
                    metadata={},
                )
            ],
            warnings=[],
            provider_call_count=1,
            latency_ms=12,
        )

    with patch(
        "investhome_api.services.creative_director.generate_ad.generate_gpt_image_creatives",
        side_effect=fake_generate,
    ):
        resp = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            json={
                "language": "tr",
                "production_mode": "os_compose",
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["production_mode"] == "os_compose"


def test_create_campaign_includes_production_brief(client, db_session: Session) -> None:
    project = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    interior = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        folder_category="02_RENDER",
        tags=["interior"],
    )
    logo = _asset(
        db_session,
        project,
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo"],
    )
    db_session.commit()
    resp = client.post(
        "/ai/creative-studio/campaigns",
        json={
            "project_id": str(TEMPLE_PROJECT_ID),
            "brief": BRIEF,
            "mode": "project",
            "language": "tr",
        },
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    ctx = payload.get("campaign_context") or {}
    brief = ctx.get("production_brief") or {}
    assert brief.get("big_idea")
    assert brief.get("language") == "tr"
    assert brief.get("asset_lock", {}).get("interior_filename")


def test_generate_ad_locks_interior_logo_language_and_claim_guard(
    client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    from investhome_api.schemas.gpt_image_design import (
        GptImageDesignResponse,
        GptImageOutput,
        GptImageSourceImage,
    )

    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    project = _create_project(db_session, project_id=uuid4())
    interior = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
    )
    logo = _asset(
        db_session,
        project,
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary"],
    )
    campaign_id = _seed_campaign_context(
        db_session,
        project=project,
        interior=interior,
        logo=logo,
        language=None,
    )
    db_session.commit()

    final_id = uuid4()
    captured: dict = {}

    def fake_generate(db, user, body):
        captured["body"] = body
        assert body.language == "tr"
        assert body.selected_asset_ids == [interior.id]
        assert body.aspect_ratio == "4:5"
        assert body.builder_context["creative_director_campaign_id"] == str(campaign_id)
        assert body.builder_context["interior_project_asset_lock"] is True
        assert body.builder_context["finished_ad"] is True
        tokens = body.builder_context["approved_financial_tokens"]
        assert "$400,000" in tokens
        assert "$300,000" in tokens
        assert "FINISHED PROFESSIONAL" in body.instruction
        assert "Living_Room_003" in body.instruction
        assert str(interior.id) in body.instruction
        assert body.builder_context.get("production_brief")
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id="test-session",
            linked_project_id=project.id,
            campaign_context_id=str(campaign_id),
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=interior.id,
                filename=interior.filename,
                content_type=interior.content_type,
                folder_category=interior.folder_category,
                tags=list(interior.tags or []),
                role="source",
            ),
            extra_images=[
                GptImageSourceImage(
                    asset_id=logo.id,
                    filename=logo.filename,
                    content_type=logo.content_type,
                    folder_category=logo.folder_category,
                    role="project_logo",
                )
            ],
            brief={"prompt": body.instruction[:500]},
            outputs=[
                GptImageOutput(
                    local_asset_id=final_id,
                    local_asset_url=f"/creative-studio/media/assets/{final_id}/content",
                    metadata={},
                )
            ],
            warnings=[],
            provider_call_count=1,
            latency_ms=12,
        )

    with patch(
        "investhome_api.services.creative_director.generate_ad.generate_gpt_image_creatives",
        side_effect=fake_generate,
    ):
        resp = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "format_preset": "portrait"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] == "tr"
    assert body["interior_asset_id"] == str(interior.id)
    assert body["logo_asset_id"] == str(logo.id)
    assert body["final_asset_id"] == str(final_id)
    assert body["claim_guard"]["status"] == "pass"
    assert body["project_asset_lock"]["status"] == "pass"
    assert body["project_asset_lock"]["interior_asset_id"] == str(interior.id)
    assert body["final_turkish_texts"]["list_price"] == "$400,000"
    assert body["final_turkish_texts"]["offer_price"] == "$300,000"
    assert "lansman" in body["final_turkish_texts"]["value_badge"].lower()
    assert "Unit 204" in body["final_turkish_texts"]["unit"]
    # No invented ROI / yield language in forced public texts
    blob = " ".join(str(v) for v in body["final_turkish_texts"].values()).lower()
    assert "roi" not in blob
    assert "irr" not in blob
    assert "yield" not in blob


def test_generate_ad_404_when_campaign_missing(client) -> None:
    missing = uuid4()
    resp = client.post(
        f"/ai/creative-studio/campaigns/{missing}/generate-ad",
        json={"language": "tr"},
    )
    assert resp.status_code == 404
    assert "campaign" in str(resp.json().get("detail") or "").lower()
    # Must not attempt image generation for missing campaign
    assert resp.json().get("final_asset_id") is None


def test_adapt_turkish_texts_claim_guard_helpers() -> None:
    from investhome_api.services.creative_director.generate_ad import (
        adapt_final_turkish_texts,
        claim_guard_summary,
    )

    pricing = build_pricing_claims(brief=BRIEF)
    texts = adapt_final_turkish_texts(
        language="tr",
        strategy={"big_idea": "History Meets Modernity", "cta": "Explore Details"},
        campaign_copy={
            "big_idea": "History Meets Modernity",
            "emphasis": ["History", "Modern"],
            "sales_hook": "Unit 204 Launch Opportunity",
            "cta": "Explore Unit 204 Details",
        },
        pricing=pricing,
        approved_claims=pricing["claims"],
        original_brief=BRIEF,
    )
    assert texts["headline"] == "Modern. Şık. Tarihi."
    assert texts["list_price"] == "$400,000"
    assert texts["offer_price"] == "$300,000"
    assert "~25%" in texts["value_badge"]
    assert "Unit 204" in texts["supporting"]
    assert "Unit 204" in texts["eyebrow"]
    assert texts["cta"] == "Detayları İncele"
    guard = claim_guard_summary(
        approved_claims=pricing["claims"],
        allowed_tokens=["$400,000", "$300,000", "~25%", "25%", "Unit 204"],
        texts=texts,
    )
    assert guard["status"] == "pass"
    assert guard["invented_financial_claims_blocked"] is True


def test_art_direction_translator_derives_priority_and_groups() -> None:
    from investhome_api.services.creative_director.art_direction_translator import (
        build_information_groups,
        derive_commercial_priority,
        render_gpt_image_art_direction_prompt,
        translate_campaign_art_direction,
    )
    from investhome_api.services.creative_director.generate_ad import adapt_final_turkish_texts

    pricing = build_pricing_claims(brief=BRIEF)
    strategy = {
        "big_idea": "History Meets Modernity",
        "hero_message": "Own a Piece of History with a Modern Twist",
        "sales_hook": "Unit 204 Launch Opportunity",
        "value_proposition": "~25% launch price advantage",
        "first_2_seconds": "Launch price $300,000 from $400,000",
        "emphasis": ["History", "Modern", "Launch Price", "25% Advantage"],
        "visual_direction": "Real interior blend of historic and modern",
    }
    campaign_copy = {
        "big_idea": "History Meets Modernity",
        "sales_hook": "Unit 204 Launch Opportunity",
        "emphasis": ["History", "Modern", "Launch Price", "25% Advantage"],
    }
    texts = adapt_final_turkish_texts(
        language="tr",
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        approved_claims=pricing["claims"],
        original_brief=BRIEF,
    )
    priority = derive_commercial_priority(
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        texts=texts,
    )
    assert priority[0] == "price hook / launch offer"
    assert "call to action" in priority

    groups = build_information_groups(
        texts=texts,
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
    )
    names = {g["name"] for g in groups}
    assert "launch_opportunity" in names
    assert "price_story" in names
    price_grp = next(g for g in groups if g["name"] == "price_story")
    assert "$400,000" in price_grp["elements"]
    assert "$300,000" in price_grp["elements"]

    ctx = {
        "cd_strategy": strategy,
        "campaign_copy": campaign_copy,
        "pricing": pricing,
        "original_user_brief": BRIEF,
    }
    interior_meta = {
        "asset_id": "caf8eb97-c767-4aa1-841b-759cf3500062",
        "filename": "IH_DC_TMP_001_Render_Living_Room_003.jpeg",
    }
    logo_meta = {
        "asset_id": "7b58877e-efca-4e9a-9027-6fd18fb1b345",
        "filename": "IH_DC_TMP_001_Logo_Primary.svg",
    }
    plan = translate_campaign_art_direction(
        ctx=ctx,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        language="tr",
    )
    assert plan.first_notice
    assert plan.second_notice
    assert plan.emphasis_words == ["History", "Modern", "Launch Price", "25% Advantage"]
    assert plan.asset_lock["interior_asset_id"] == str(interior_meta["asset_id"])
    assert plan.asset_lock["must_not_invent_interior"] is True

    prompt = render_gpt_image_art_direction_prompt(
        plan,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        original_brief=BRIEF,
    )
    assert "WHAT MUST BE NOTICED FIRST" in prompt
    assert "WHAT MUST BE NOTICED SECOND" in prompt
    assert "Position the building on the left" not in prompt
    assert "left two-thirds" not in prompt
    assert "History" in prompt
    assert "Modern" in prompt
    assert "Launch Price" in prompt
    assert "Living_Room_003" in prompt
    assert "Detayları İncele" in prompt


INTERIOR_BRIEF = (
    "The Temple için projenin iç özelliklerini ve yaşam deneyimini anlatan premium bir sosyal medya reklamı hazırla. "
    "Bu kampanyada fiyat veya Unit 204 kullanma. Türkçe çalış."
)
INTERIOR_CAMPAIGN_ID = UUID("ec3021d7-3d2f-4eca-bd75-e747571e1bb9")


def _seed_interior_campaign_context(
    db: Session,
    *,
    project: Project,
    interior: CreativeStudioMediaAsset,
    logo: CreativeStudioMediaAsset,
    campaign_id: UUID | None = None,
) -> UUID:
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign

    interior_meta = {
        "asset_id": str(interior.id),
        "filename": interior.filename,
        "content_type": interior.content_type,
        "folder_category": interior.folder_category,
        "visual_subject": "INTERIOR",
        "tags": list(interior.tags or []),
        "role": "hero_interior",
        "provenance_source": "google_drive",
    }
    logo_meta = {
        "asset_id": str(logo.id),
        "filename": logo.filename,
        "content_type": logo.content_type,
        "folder_category": logo.folder_category,
        "visual_subject": "BRANDING",
        "tags": list(logo.tags or []),
        "role": "project_logo",
        "provenance_source": "google_drive",
    }
    stale_unit_claim = {
        "key": "unit_code",
        "display": "Unit 204",
        "value": "204",
        "source": "retrieved",
        "verified": True,
        "is_financial": False,
    }
    ctx = {
        "original_user_brief": INTERIOR_BRIEF,
        "language": "tr",
        "campaign_intent": "lifestyle",
        "cd_strategy": {
            "big_idea": "Eviniz, Sığınak",
            "hero_message": "Şehrin Kalbinde Sakin Bir Sığınak",
            "sales_hook": "Şehrin kalbinde huzur dolu bir yaşam",
            "supporting_messages": [
                "Zarif tasarım detaylarıyla dolu yaşam alanları",
                "Özel ortak alanlar ve sosyal olanaklar",
                "Modern ve fonksiyonel iç mekanlar",
            ],
            "emphasis": ["Sakin", "Zarif", "Özel"],
            "cta": "Detayları Keşfet",
            "first_2_seconds": "Zarif ve huzur dolu bir yaşam alanı",
            "visual_direction": "Sakin ve zarif bir yaşam alanı atmosferi",
        },
        "campaign_copy": {
            "big_idea": "Eviniz, Sığınak",
            "hero_message": "Şehrin Kalbinde Sakin Bir Sığınak",
            "sales_hook": "Şehrin kalbinde huzur dolu bir yaşam",
            "supporting_messages": [
                "Zarif tasarım detaylarıyla dolu yaşam alanları",
                "Özel ortak alanlar ve sosyal olanaklar",
                "Modern ve fonksiyonel iç mekanlar",
            ],
            "emphasis": ["Sakin", "Zarif", "Özel"],
            "cta": "Detayları Keşfet",
        },
        "approved_claims": [stale_unit_claim],
        "pricing": {
            "price_presentation": None,
            "list_price": None,
            "launch_price": None,
            "claims": [stale_unit_claim],
        },
        "selected_assets": [interior_meta],
        "selected_logo": logo_meta,
        "drive_research": {
            "selected_interior": interior_meta,
            "selected_logo": logo_meta,
        },
        "generated_assets": [],
        "output_history": [],
        "image_generation_performed": False,
    }
    row = CreativeDirectorCampaign(
        id=campaign_id or uuid4(),
        linked_project_id=project.id,
        mode="project",
        original_brief=INTERIOR_BRIEF,
        context_json=ctx,
        status="draft",
    )
    db.add(row)
    db.flush()
    return row.id


def test_generate_ad_interior_lifestyle_no_unit204_no_price(
    client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    from investhome_api.schemas.gpt_image_design import (
        GptImageDesignResponse,
        GptImageOutput,
        GptImageSourceImage,
    )

    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    get_settings.cache_clear()

    project = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    interior = _asset(
        db_session,
        project,
        asset_id=UUID("caf8eb97-c767-4aa1-841b-759cf3500062"),
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
    )
    logo = _asset(
        db_session,
        project,
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary"],
    )
    campaign_id = _seed_interior_campaign_context(
        db_session,
        project=project,
        interior=interior,
        logo=logo,
        campaign_id=INTERIOR_CAMPAIGN_ID,
    )
    db_session.commit()

    final_id = uuid4()
    captured: dict = {}

    def fake_generate(db, user, body):
        captured["body"] = body
        assert body.builder_context.get("campaign_mode") == "lifestyle"
        assert body.builder_context["forced_verified_lines"] == []
        assert body.builder_context["approved_financial_tokens"] == []
        forced = body.builder_context["forced_visible_copy"]
        blob = " ".join(str(v) for v in forced.values()).lower()
        assert "unit 204" not in blob
        assert "$400" not in blob
        assert "$300" not in blob
        assert "detayları keşfet" in blob
        assert "/ai/creative-studio/social/design" not in body.instruction
        assert "ADVERTISING ART DIRECTION" in body.instruction
        assert "No price dramatization" in body.instruction
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id="test-session",
            linked_project_id=project.id,
            campaign_context_id=str(campaign_id),
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=interior.id,
                filename=interior.filename,
                content_type=interior.content_type,
                folder_category=interior.folder_category,
                tags=list(interior.tags or []),
                role="source",
            ),
            extra_images=[
                GptImageSourceImage(
                    asset_id=logo.id,
                    filename=logo.filename,
                    content_type=logo.content_type,
                    folder_category=logo.folder_category,
                    role="project_logo",
                )
            ],
            brief={"prompt": body.instruction[:500]},
            outputs=[
                GptImageOutput(
                    local_asset_id=final_id,
                    local_asset_url=f"/creative-studio/media/assets/{final_id}/content",
                    metadata={},
                )
            ],
            warnings=[],
            provider_call_count=1,
            latency_ms=12,
        )

    with patch(
        "investhome_api.services.creative_director.generate_ad.generate_gpt_image_creatives",
        side_effect=fake_generate,
    ):
        resp = client.post(
            f"/ai/creative-studio/campaigns/{INTERIOR_CAMPAIGN_ID}/generate-ad",
            json={
                "language": "tr",
                "aspect_ratio": "4:5",
                "format_preset": "portrait",
                "production_mode": "os_compose",
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["campaign_id"] == str(INTERIOR_CAMPAIGN_ID)
    assert body["interior_asset_id"] == str(interior.id)
    assert body["logo_asset_id"] == str(logo.id)
    assert body["claim_guard"]["status"] == "pass"
    assert body["claim_guard"]["campaign_mode"] == "lifestyle"
    assert body["project_asset_lock"]["status"] == "pass"
    texts_blob = " ".join(str(v) for v in body["final_turkish_texts"].values()).lower()
    assert "unit 204" not in texts_blob
    assert "$400" not in texts_blob
    assert "$300" not in texts_blob
    assert body["final_turkish_texts"]["headline"] == "Eviniz, Sığınak"
    assert body["final_turkish_texts"]["cta"] == "Detayları Keşfet"
    assert body["provider_call_count"] == 1
    art = body["creative_brief_summary"]["art_direction"]
    assert "price hook" not in art["commercial_priority"][0].lower()


def test_art_direction_prompt_has_clean_canvas_no_text_no_logo_locks() -> None:
    from investhome_api.services.creative_director.art_direction_translator import (
        render_gpt_image_art_direction_prompt,
        translate_campaign_art_direction,
    )
    from investhome_api.services.creative_director.generate_ad import adapt_final_turkish_texts

    texts = adapt_final_turkish_texts(
        language="tr",
        strategy={
            "big_idea": "Eviniz, Sığınak",
            "hero_message": "Şehrin Kalbinde Sakin Bir Sığınak",
            "sales_hook": "Şehrin kalbinde huzur dolu bir yaşam",
            "cta": "Detayları Keşfet",
            "supporting_messages": [
                "Zarif tasarım detaylarıyla dolu yaşam alanları",
                "Özel ortak alanlar ve sosyal olanaklar",
                "Modern ve fonksiyonel iç mekanlar",
            ],
        },
        campaign_copy={
            "big_idea": "Eviniz, Sığınak",
            "supporting_messages": [
                "Zarif tasarım detaylarıyla dolu yaşam alanları",
                "Özel ortak alanlar ve sosyal olanaklar",
                "Modern ve fonksiyonel iç mekanlar",
            ],
            "cta": "Detayları Keşfet",
        },
        pricing={"price_presentation": None},
        approved_claims=[],
        original_brief=INTERIOR_BRIEF,
        lifestyle=True,
    )
    ctx = {
        "cd_strategy": {"big_idea": "Eviniz, Sığınak", "visual_direction": "Sakin yaşam"},
        "campaign_copy": {"big_idea": "Eviniz, Sığınak"},
        "pricing": {},
        "original_user_brief": INTERIOR_BRIEF,
        "campaign_intent": "lifestyle",
    }
    interior_meta = {
        "asset_id": "caf8eb97-c767-4aa1-841b-759cf3500062",
        "filename": "IH_DC_TMP_001_Render_Living_Room_003.jpeg",
    }
    logo_meta = {
        "asset_id": "7b58877e-efca-4e9a-9027-6fd18fb1b345",
        "filename": "IH_DC_TMP_001_Logo_Primary.svg",
    }
    plan = translate_campaign_art_direction(
        ctx=ctx,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        language="tr",
        lifestyle=True,
    )
    prompt = render_gpt_image_art_direction_prompt(
        plan,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        original_brief=INTERIOR_BRIEF,
    )
    upper = prompt.upper()
    assert "NO TEXT" in upper
    assert "NO LOGOS" in upper
    assert "NO TYPOGRAPHY" in upper
    assert "COMPOSITION ZONES" in prompt
    assert "OS FINAL COPY PREVIEW" not in prompt
    assert "Detayları Keşfet" in prompt
    assert "Eviniz, Sığınak" in prompt


def test_compose_duplication_guard_and_background_layer() -> None:
    import io
    from uuid import uuid4

    from PIL import Image

    from investhome_api.services.gpt_image_design.compose import (
        CompositionSlotPlan,
        compose_final_layers,
        run_duplication_guard,
    )
    from investhome_api.services.gpt_image_design.design_plan import build_gpt_image_design_plan
    from investhome_api.services.gpt_image_design.source import ResolvedSourceImage

    def png_bytes(w: int, h: int, color: tuple[int, int, int] = (20, 40, 70)) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (w, h), color).save(buf, format="PNG")
        return buf.getvalue()

    base = png_bytes(400, 500)
    logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo"],
        image_bytes=png_bytes(80, 32, (220, 40, 40)),
        width=80,
        height=32,
        role="project_logo",
    )
    plan = build_gpt_image_design_plan(
        canvas_width=400,
        canvas_height=500,
        art_direction="lifestyle",
        has_project_logo=True,
        include_slogan=False,
    )
    dup_slots = CompositionSlotPlan(
        headline="Eviniz, Sığınak",
        subhead="Eviniz, Sığınak",
        cta="Detayları Keşfet",
        include_slogan=False,
    )
    guard = run_duplication_guard(dup_slots, logos=[logo], plan=plan)
    assert guard.status == "fail"
    assert "headline_equals_subhead" in guard.violations
    assert guard.counts["project_logo_assets"] == 1
    assert guard.counts["primary_cta"] == 1
    assert guard.counts["primary_headline"] == 1

    base_id = uuid4()
    result = compose_final_layers(
        base,
        logos=[logo],
        slots=dup_slots,
        canvas_width=400,
        canvas_height=500,
        base_asset_id=base_id,
        plan=plan,
    )
    assert result.duplication_guard["status"] == "fail"
    assert result.duplication_guard["gpt_generated_text_count"] == 0
    assert result.duplication_guard["gpt_generated_logo_count"] == 0
    bg = next(el for el in result.layers if el.get("id") == "background-gpt-image")
    assert bg["type"] == "IMAGE"
    assert bg["role"] == "background"
    assert bg["assetId"] == str(base_id)
    logos = [el for el in result.layers if el.get("role") == "logo"]
    assert len(logos) == 1
    headlines = [el for el in result.layers if el.get("role") == "headline"]
    assert len(headlines) == 1
    ctas = [el for el in result.layers if el.get("type") == "BUTTON"]
    assert len(ctas) == 1