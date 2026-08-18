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
from investhome_api.services.creative_director.orchestrator import (
    assign_capabilities,
    infer_required_capabilities,
)
from investhome_api.services.creative_director.pricing import (
    build_pricing_claims,
    compute_discount_percent,
)
from investhome_api.services.creative_director.research import pick_real_interior
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
) -> CreativeStudioMediaAsset:
    asset = CreativeStudioMediaAsset(
        id=asset_id or uuid4(),
        filename=filename,
        content_type=content_type,
        file_size=2048,
        width=1600,
        height=1200,
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
    picked = pick_real_interior([exterior, interior])
    assert picked is not None
    assert picked.asset_id == interior.asset_id
    assert pick_real_interior([exterior]) is None


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
    project = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    interior = _asset(
        db_session,
        project,
        filename="Temple_Unit_Living_Interior.jpg",
        folder_category="02_RENDER",
        tags=["interior", "living", "temple"],
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
        asset_id=TEMPLE_PRIMARY_LOGO_ID,
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

    # Exterior must not be the locked hero when interiors exist.
    for asset in brief["selected_assets"]:
        assert "exterior" not in (asset.get("filename") or "").lower()

    pricing = brief["pricing"]
    assert pricing["list"] == "$400,000"
    assert pricing["offer"] == "$300,000"
    assert pricing["discount"]["display"] == "~25%"

    claim_sources = {c["key"]: c["source"] for c in brief["claims"]}
    assert claim_sources["list_price"] == "user_campaign_input"
    assert claim_sources["launch_discount_percent"] == "derived_safe"

    assert "video_generate" in brief["missing_capabilities"]
    assert brief["hero_message"]
    assert brief["cta"]
    assert brief["concept"]

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
