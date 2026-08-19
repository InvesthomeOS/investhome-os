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
