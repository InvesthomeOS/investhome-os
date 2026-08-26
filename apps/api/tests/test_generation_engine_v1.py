"""Creative Generation Engine v1 — short Turkish brief → brand/project production."""

from __future__ import annotations

from unittest.mock import patch
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
from investhome_api.schemas.gpt_image_design import (
    GptImageDesignResponse,
    GptImageOutput,
    GptImageSourceImage,
)
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_director.generation_engine import (
    classify_ad_scope,
    detect_output_format,
    interpret_short_user_brief,
)
from investhome_api.services.creative_director.research import pick_city_visual
from investhome_api.services.gpt_image_design.source import TEMPLE_PRIMARY_LOGO_ID

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")
TEMPLE_INTERIOR_ID = UUID("c3d11c35-d8b7-485c-b216-0a4da68b751a")
TEMPLE_LOGO_ID = UUID("7b58877e-efca-4e9a-9027-6fd18fb1b345")

DC_BRIEF = (
    "Washington DC'deki gayrimenkul yatırım fırsatlarını Türkiye'deki yatırımcılara "
    "anlatan çarpıcı bir Instagram postu hazırla. Amerikan renklerini kullan."
)
TEMPLE_BRIEF = "The Temple için Cherry Blossom dönemine özel lansman reklamı hazırla."
EXTERIOR_BRIEF = "The Temple için dış cephe görseli kullanan bir reklam hazırla."


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
    project: Project | None,
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
        linked_project_id=project.id if project is not None else None,
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


def test_short_dc_brief_classifies_as_brand_investment_45() -> None:
    parsed = interpret_short_user_brief(DC_BRIEF, project_name="The Temple")
    assert parsed["ad_scope"] == "brand"
    assert parsed["investment_message"] is True
    assert parsed["price_mentioned"] is False
    assert "no_price_invented" in parsed["invented_facts_blocked"]
    assert parsed["format"]["format_preset"] == "portrait"
    assert parsed["format"]["aspect_ratio"] == "4:5"
    assert parsed["visual_kind"] == "city"
    assert parsed["american_colors"] is True
    assert parsed["logo_role"] == "investhome_logo"
    assert parsed["production_mode"] == "finished_ad"
    assert parsed["native_renderer_primary"] is False
    assert "the_temple_as_product" in parsed["forbidden_changes"]
    commercial = " ".join(
        [
            str(parsed.get("purpose") or ""),
            str(parsed.get("audience") or ""),
            str(parsed.get("place") or ""),
            str(parsed.get("primary_message") or ""),
        ]
    ).lower()
    assert "$" not in commercial
    assert "roi" not in commercial


def test_temple_named_brief_stays_project() -> None:
    assert classify_ad_scope(TEMPLE_BRIEF, project_name="The Temple") == "project"
    parsed = interpret_short_user_brief(TEMPLE_BRIEF, project_name="The Temple")
    assert parsed["ad_scope"] == "project"
    assert parsed["logo_role"] == "project_logo"


def test_exterior_visual_kind_from_short_brief() -> None:
    parsed = interpret_short_user_brief(EXTERIOR_BRIEF, project_name="The Temple")
    assert parsed["ad_scope"] == "project"
    assert parsed["visual_kind"] == "exterior"
    assert "interior_as_hero" in parsed["forbidden_changes"]


def test_format_detectors() -> None:
    assert detect_output_format("kare post")["aspect_ratio"] == "1:1"
    assert detect_output_format("Instagram story hazırla")["aspect_ratio"] == "9:16"
    assert detect_output_format("reel cover")["format_preset"] == "reelsCover"
    assert detect_output_format("sadece reklam hazırla")["specified"] is False


def test_pick_city_visual_skips_interior_and_temple_exterior() -> None:
    interior = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="Temple_Living_Interior.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["interior"],
        score=20.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="INTERIOR",
        source_type="google_drive",
    )
    exterior = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="Temple_Exterior_Facade.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["exterior", "facade"],
        score=18.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="EXTERIOR",
        source_type="google_drive",
    )
    city = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="Washington_DC_Skyline_Location.jpg",
        content_type="image/jpeg",
        folder_category="05_LOCATION",
        tags=["washington", "dc", "skyline", "location"],
        score=4.0,
        linked_project_id=TEMPLE_PROJECT_ID,
        visual_subject="LOCATION",
        source_type="google_drive",
    )
    picked, score, reason = pick_city_visual([interior, exterior, city], brief=DC_BRIEF)
    assert picked is not None
    assert picked.asset_id == city.asset_id
    assert score is not None and score > 4.0
    assert reason and "city_place_visual" in reason


def test_create_campaign_dc_brief_locks_brand_assets(client, db_session: Session) -> None:
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
        filename="Temple_Exterior_Facade.jpg",
        folder_category="02_RENDER",
        tags=["exterior", "facade", "temple"],
    )
    city = _asset(
        db_session,
        project,
        filename="Washington_DC_Skyline_Location.jpg",
        folder_category="05_LOCATION",
        tags=["washington", "dc", "skyline", "location"],
        width=2400,
        height=1600,
    )
    _asset(
        db_session,
        project,
        filename="Temple_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary", "temple"],
    )
    brand_logo = _asset(
        db_session,
        None,
        filename="Investhome_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary", "investhome"],
    )
    db_session.commit()

    response = client.post(
        "/ai/creative-studio/campaigns",
        json={
            "project_id": str(project.id),
            "brief": DC_BRIEF,
            "mode": "project",
            "language": "tr",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    ctx = body["campaign_context"]
    engine = ctx["generation_engine"]
    assert engine["ad_scope"] == "brand"
    assert engine["format_preset"] == "portrait"
    assert engine["aspect_ratio"] == "4:5"
    assert engine["production_mode"] == "finished_ad"
    assert engine["native_renderer_primary"] is False

    hero = ctx["drive_research"]["selected_interior"]
    logo = ctx["drive_research"]["selected_logo"]
    assert hero["asset_id"] == str(city.id)
    assert hero["role"] == "city_visual"
    assert hero["asset_id"] != str(interior.id)
    assert logo["role"] == "investhome_logo"
    assert "temple" not in (logo.get("filename") or "").lower()
    assert "investhome" in (logo.get("filename") or "").lower()
    assert logo["asset_id"] != str(interior.id)

    pb = ctx["production_brief"]
    assert pb["format_preset"] == "portrait"
    assert pb["aspect_ratio"] == "4:5"
    assert pb["generation_engine"]["ad_scope"] == "brand"
    strategy = ctx["cd_strategy"]
    blob = " ".join(
        [
            str(strategy.get("big_idea") or ""),
            str(strategy.get("hero_message") or ""),
            str(strategy.get("concept") or ""),
        ]
    ).lower()
    assert "washington" in blob
    assert "the temple" not in blob
    assert "$" not in blob
    assert "roi" not in blob


def test_generate_ad_overrides_smb_square_and_skips_project_logo(
    client,
    db_session: Session,
) -> None:
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign

    project = _create_project(db_session, project_id=uuid4())
    city = _asset(
        db_session,
        project,
        filename="Washington_DC_Skyline_Location.jpg",
        folder_category="05_LOCATION",
        tags=["washington", "dc", "location"],
    )
    logo = _asset(
        db_session,
        None,
        filename="Investhome_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "investhome"],
    )
    city_meta = {
        "asset_id": str(city.id),
        "filename": city.filename,
        "content_type": city.content_type,
        "folder_category": city.folder_category,
        "visual_subject": "LOCATION",
        "tags": list(city.tags or []),
        "role": "city_visual",
        "provenance_source": "google_drive",
    }
    logo_meta = {
        "asset_id": str(logo.id),
        "filename": logo.filename,
        "content_type": logo.content_type,
        "folder_category": logo.folder_category,
        "visual_subject": "BRANDING",
        "tags": list(logo.tags or []),
        "role": "investhome_logo",
        "provenance_source": "google_drive",
    }
    parsed = interpret_short_user_brief(DC_BRIEF, project_name="The Temple")
    ctx = {
        "original_user_brief": DC_BRIEF,
        "language": "tr",
        "generation_engine": {
            "ad_scope": "brand",
            "format_specified": True,
            "format_preset": "portrait",
            "aspect_ratio": "4:5",
            "production_mode": "finished_ad",
            "native_renderer_primary": False,
            "logo_role": "investhome_logo",
        },
        "user_brief_analysis": parsed,
        "campaign_intent": "investment",
        "cd_strategy": {
            "big_idea": "Washington DC — Amerikan gayrimenkulünün kapısı",
            "hero_message": "Washington DC'de yatırım zamanı",
            "cta": "Fırsatları İncele",
            "visual_direction": "City photography, Investhome logo",
        },
        "campaign_copy": {
            "big_idea": "Washington DC — Amerikan gayrimenkulünün kapısı",
            "hero_message": "Washington DC'de yatırım zamanı",
            "cta": "Fırsatları İncele",
        },
        "approved_claims": [],
        "pricing": {"claims": []},
        "selected_assets": [city_meta],
        "selected_logo": logo_meta,
        "drive_research": {
            "selected_interior": city_meta,
            "selected_logo": logo_meta,
            "architecture_truth": {"fail_closed": False, "status": "brand_place_visual"},
        },
        "generated_assets": [],
        "output_history": [],
        "image_generation_performed": False,
    }
    row = CreativeDirectorCampaign(
        linked_project_id=project.id,
        mode="project",
        original_brief=DC_BRIEF,
        context_json=ctx,
        status="draft",
    )
    db_session.add(row)
    db_session.flush()
    db_session.commit()

    captured: dict = {}
    final_id = uuid4()

    def fake_generate(db, user, body):
        captured["body"] = body
        assert body.format_preset == "portrait"
        assert body.aspect_ratio == "4:5"
        assert body.selected_asset_ids == [city.id]
        assert body.builder_context["interior_project_asset_lock"] is False
        assert body.builder_context["skip_project_logo"] is True
        assert body.builder_context["brand_market_ad"] is True
        assert body.builder_context["production_mode"] == "finished_ad"
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id="test-session",
            linked_project_id=project.id,
            campaign_context_id=str(row.id),
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=city.id,
                filename=city.filename,
                content_type=city.content_type,
                folder_category=city.folder_category,
                tags=list(city.tags or []),
                role="source",
            ),
            extra_images=[
                GptImageSourceImage(
                    asset_id=logo.id,
                    filename=logo.filename,
                    content_type=logo.content_type,
                    folder_category=logo.folder_category,
                    role="investhome_logo",
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
            f"/ai/creative-studio/campaigns/{row.id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "1:1", "format_preset": "square"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["format_preset"] == "portrait"
    assert body["aspect_ratio"] == "4:5"
    assert body["production_mode"] == "finished_ad"
    assert body["interior_asset_id"] == str(city.id)
    assert body["logo_asset_id"] == str(logo.id)
    assert body["interior_asset_id"] != str(TEMPLE_INTERIOR_ID)
    assert body["logo_asset_id"] != str(TEMPLE_LOGO_ID)
    assert captured["body"].format_preset == "portrait"
    _ = TEMPLE_PRIMARY_LOGO_ID
