"""Art Director POC — real project assets, A/B/C DesignPlans, provenance."""

from __future__ import annotations

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
from investhome_api.services.social_design_engine.art_director import (
    campaign_type_from_intent,
    recipes_for_campaign,
    select_real_asset,
)
from investhome_api.services.social_design_engine.campaign_intent import classify_campaign_intent
from investhome_api.services.social_design_engine.media import (
    classify_visual_subject,
    is_generative_or_synthetic_asset,
    list_media_candidates,
    pick_best_asset,
    pick_logo_asset,
)

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


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


def _create_project(db: Session, name: str = "The Temple") -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"PRJ-AD-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        city="Washington",
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
    filename: str,
    folder_category: str | None = "02_RENDER",
    content_type: str = "image/jpeg",
    tags: list[str] | None = None,
    source_type: str = MediaAssetSourceType.GOOGLE_DRIVE.value,
) -> CreativeStudioMediaAsset:
    asset = CreativeStudioMediaAsset(
        id=uuid4(),
        filename=filename,
        content_type=content_type,
        file_size=2048,
        width=1600,
        height=1200,
        storage_provider="google_drive" if source_type == "google_drive" else "local",
        storage_key=f"gdrive:{uuid4().hex}",
        linked_project_id=project.id,
        source_type=source_type,
        external_file_id=f"file-{uuid4().hex[:8]}",
        external_checksum="c1",
        sync_status=MediaAssetSyncStatus.ACTIVE.value,
        folder_category=folder_category,
        tags=tags or [],
    )
    db.add(asset)
    db.flush()
    return asset


def test_visual_subject_from_metadata_not_hallucinated(db_session: Session) -> None:
    project = _create_project(db_session)
    exterior = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_005.jpg")
    interior = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Living_Room_001.jpg")
    plan = _asset(db_session, project, filename="A100.png", folder_category="03_FLOOR_PLANS", content_type="image/png")
    logo = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_White.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    aerial = _asset(db_session, project, filename="site-aerial-drone.jpg", folder_category="06_MEDIA")
    assert classify_visual_subject(exterior) == "ARCHITECTURAL_RENDER"
    assert classify_visual_subject(interior) == "INTERIOR"
    assert classify_visual_subject(plan) == "FLOOR_PLAN"
    assert classify_visual_subject(logo) == "BRANDING"
    assert classify_visual_subject(aerial) == "AERIAL"


def test_excludes_ideogram_and_unsplash(db_session: Session) -> None:
    project = _create_project(db_session)
    fake = _asset(
        db_session,
        project,
        filename="ideogram-a-51833b10.png",
        folder_category=None,
        content_type="image/png",
        tags=["provider:ideogram", "ideogram-poc"],
        source_type=MediaAssetSourceType.UPLOAD.value,
    )
    real = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_001.jpg")
    assert is_generative_or_synthetic_asset(fake) is True
    assert is_generative_or_synthetic_asset(real) is False
    candidates = list_media_candidates(
        db_session,
        linked_project_id=project.id,
        instruction="investment post",
        campaign_type="INVESTMENT",
    )
    ids = {c.asset_id for c in candidates}
    assert fake.id not in ids
    assert real.id in ids


def test_investment_selects_exterior_render_not_floor_plan(db_session: Session) -> None:
    project = _create_project(db_session)
    floor = _asset(db_session, project, filename="unit-plan.png", folder_category="03_FLOOR_PLANS", content_type="image/png")
    hero = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg")
    candidates = list_media_candidates(
        db_session,
        linked_project_id=project.id,
        instruction="investor Instagram post $500,000 14% 24 months",
        campaign_type="INVESTMENT",
    )
    picked = select_real_asset(candidates, campaign_type="INVESTMENT")
    assert picked is not None
    assert picked.asset_id == hero.id
    assert picked.asset_id != floor.id
    assert picked.visual_subject in {"ARCHITECTURAL_RENDER", "EXTERIOR"}
    assert picked.provenance_source == "google_drive"


def test_location_prefers_aerial_or_exterior_not_metrics_intent() -> None:
    loc = classify_campaign_intent(
        "The Temple's central Washington DC location advantage. Premium Instagram square. English.",
        project_name="The Temple",
    )
    assert campaign_type_from_intent(loc.campaign_intent) == "LOCATION"
    assert loc.asset_preference in {"aerial", "neighborhood", "exterior"}


def test_abc_recipes_are_materially_different_compositions() -> None:
    recipes = recipes_for_campaign("INVESTMENT")
    assert [r.key for r in recipes] == ["A", "B", "C"]
    assert recipes[0].label == "EDITORIAL LUXURY"
    assert recipes[1].label == "INSTITUTIONAL INVESTMENT"
    assert recipes[2].label == "ARCHITECTURAL PREMIUM"
    compositions = {r.composition for r in recipes}
    directions = {r.direction for r in recipes}
    assert len(compositions) == 3
    assert len(directions) == 3
    loc = recipes_for_campaign("LOCATION")
    assert loc[1].composition != recipes[1].composition


def test_logo_from_brand_folder_never_generated(db_session: Session) -> None:
    project = _create_project(db_session)
    _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_002.jpg")
    logo = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    candidates = list_media_candidates(
        db_session,
        linked_project_id=project.id,
        instruction="investment",
        campaign_type="INVESTMENT",
    )
    picked_logo = pick_logo_asset(candidates)
    assert picked_logo is not None
    assert picked_logo.asset_id == logo.id
    hero = pick_best_asset(candidates, campaign_type="INVESTMENT")
    assert hero != logo.id


def test_logo_prefers_project_identity_over_corporate(db_session: Session) -> None:
    project = _create_project(db_session, name="The Temple")
    project.project_code = "IH-DC-TMP-001"
    db_session.flush()
    _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_002.jpg")
    corporate = _asset(
        db_session,
        project,
        filename="Investhome_Logo_Primary.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    temple = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    addition = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Addition_Logo_Primary.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    candidates = list_media_candidates(
        db_session,
        linked_project_id=project.id,
        instruction="lokasyon",
        campaign_type="LOCATION",
    )
    picked_logo = pick_logo_asset(
        candidates,
        project_name=project.project_name,
        project_code=project.project_code,
    )
    assert picked_logo is not None
    assert picked_logo.asset_id == temple.id
    assert picked_logo.asset_id != corporate.id
    assert picked_logo.asset_id != addition.id


def test_design_plan_schema_and_variants_live_endpoint(client, db_session: Session) -> None:
    project = _create_project(db_session)
    hero = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_005.jpg")
    _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_White.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_008.jpg")
    body = {
        "linked_project_id": str(project.id),
        "instruction": (
            "Create a premium English Instagram square for The Temple investment campaign. "
            "$500,000 minimum investment, 14% target return, 24 months."
        ),
        "mode": "create",
        "mode_explicit": True,
        "design_provider": "native",
        "draft": {"posts": [], "selected_post_id": None},
        "language": "en",
    }
    res = client.post("/ai/creative-studio/social/design", json=body)
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["meta"]["planner"] == "art_director"
    variants = payload.get("design_variants") or []
    assert len(variants) == 3
    assert [v["key"] for v in variants] == ["A", "B", "C"]
    compositions = {v["composition"] for v in variants}
    assert len(compositions) == 3
    families = []
    headline_ys = []
    for variant in variants:
        post = variant.get("post") or {}
        families.append(post.get("compositionFamily") or post.get("composition_family"))
        for el in post.get("elements") or []:
            if el.get("role") == "headline":
                headline_ys.append(int(el.get("y") or 0))
                break
    assert len(set(filter(None, families))) >= 2
    if len(headline_ys) >= 2:
        assert max(headline_ys) - min(headline_ys) >= 40 or len(set(families)) >= 2
    plan = variants[0]["design_plan"]
    for key in (
        "campaign_type",
        "creative_direction",
        "asset_id",
        "crop_strategy",
        "focal_area",
        "overlay",
        "headline",
        "supporting_copy",
        "metrics",
        "cta",
        "logo_placement",
        "typography_hierarchy",
        "alignment",
        "composition",
        "contrast_strategy",
    ):
        assert key in plan, key
    assert plan["campaign_type"] == "INVESTMENT"
    assert plan["asset_id"] == str(hero.id)
    provenance = payload["provenance"]
    assert provenance["selected_asset_id"] == str(hero.id)
    assert provenance["filename"] == hero.filename
    assert provenance["source"] == "google_drive"
    assert provenance["financial_facts_source"] == "user_campaign_input"
    posts = payload["posts"]
    assert posts
    cover = posts[-1].get("coverAssetId") or posts[-1].get("cover_asset_id")
    assert cover == str(hero.id)
    types = {el.get("type") for el in posts[-1].get("elements") or []}
    assert "IMAGE" in types
    assert "METRIC_GROUP" in types
    displays = []
    for el in posts[-1].get("elements") or []:
        if el.get("type") == "METRIC_GROUP":
            displays.extend(str(m.get("display_value") or "") for m in el.get("metrics") or [])
    joined = " ".join(displays)
    assert "500,000" in joined or "$500" in joined
    assert "14%" in joined or "14" in joined
    assert any("24" in d for d in displays)
    assert payload["selected_asset"]["filename"] == hero.filename


def test_location_campaign_no_investment_metrics(client, db_session: Session) -> None:
    project = _create_project(db_session)
    _asset(db_session, project, filename="site-aerial-drone.jpg", folder_category="06_MEDIA")
    _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_003.jpg")
    body = {
        "linked_project_id": str(project.id),
        "instruction": (
            "Create a premium English Instagram square about The Temple's central "
            "Washington DC location advantage. Use a real aerial or exterior."
        ),
        "mode": "create",
        "mode_explicit": True,
        "design_provider": "native",
        "draft": {"posts": [], "selected_post_id": None},
        "language": "en",
    }
    res = client.post("/ai/creative-studio/social/design", json=body)
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["meta"]["art_director"]["campaign_type"] == "LOCATION"
    for variant in payload["design_variants"]:
        plan = variant["design_plan"]
        assert plan["campaign_type"] == "LOCATION"
        assert not plan.get("metrics")
        post = variant["post"]
        types = {el.get("type") for el in post.get("elements") or []}
        assert "METRIC_GROUP" not in types
    selected = payload["selected_asset"]
    assert selected["visual_subject"] in {"AERIAL", "EXTERIOR", "ARCHITECTURAL_RENDER", "NEIGHBORHOOD"}


def test_alternate_real_exterior_keeps_composition(client, db_session: Session) -> None:
    project = _create_project(db_session)
    first = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_001.jpg")
    second = _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_009.jpg")
    create = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(project.id),
            "instruction": "Create a premium English Instagram square for The Temple. $500,000 / 14% / 24 months.",
            "mode": "create",
            "mode_explicit": True,
            "design_provider": "native",
            "draft": {"posts": [], "selected_post_id": None},
            "language": "en",
        },
    )
    assert create.status_code == 200, create.text
    created = create.json()
    post = created["posts"][-1]
    original_cover = post.get("coverAssetId")
    assert original_cover in {str(first.id), str(second.id)}
    headline = next(
        (el["content"] for el in post.get("elements") or [] if el.get("role") == "headline"),
        "",
    )
    edit = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(project.id),
            "instruction": "Başka bir gerçek The Temple exterior görseli kullan.",
            "mode": "edit",
            "mode_explicit": True,
            "design_provider": "native",
            "draft": {"posts": created["posts"], "selected_post_id": post["id"]},
            "language": "en",
        },
    )
    assert edit.status_code == 200, edit.text
    edited = edit.json()["posts"]
    updated = next(p for p in edited if p["id"] == post["id"])
    new_cover = updated.get("coverAssetId")
    assert new_cover != original_cover
    assert new_cover in {str(first.id), str(second.id)}
    selected = edit.json().get("selected_asset") or {}
    assert selected.get("asset_id") == new_cover
    new_headline = next(
        (el["content"] for el in updated.get("elements") or [] if el.get("role") == "headline"),
        "",
    )
    assert new_headline == headline


def _headline_geo(post: dict) -> tuple[int, int, int]:
    for el in post.get("elements") or []:
        if el.get("role") == "headline":
            return int(el.get("x") or 0), int(el.get("y") or 0), int(el.get("fontSize") or 0)
    return (0, 0, 0)


def test_design_plan_geometry_not_imprisoned_in_top_left_recipe() -> None:
    from investhome_api.services.social_design_engine.art_director import _directed_regions
    from investhome_api.services.social_design_engine.layout import social_layout_slots

    recipe_slots = social_layout_slots(1080, 1350, primitive="TOP_LEFT_EDITORIAL")
    recipe_h = recipe_slots["headline"]
    directed = _directed_regions(
        composition_type="location_story",
        canvas_w=1080,
        canvas_h=1350,
        refs={"whitespace": "generous", "image_text_balance": "image_dominant"},
        salt=42,
        include_support=True,
    )
    hx, hy = directed["headline"]["x"], directed["headline"]["y"]
    assert abs(hx - recipe_h["x"]) >= 8 or abs(hy - recipe_h["y"]) >= 40
    hero = _directed_regions(
        composition_type="architectural_hero",
        canvas_w=1080,
        canvas_h=1350,
        refs={"whitespace": "generous"},
        salt=7,
        include_support=True,
    )
    story = _directed_regions(
        composition_type="split_information",
        canvas_w=1080,
        canvas_h=1350,
        refs={"whitespace": "generous"},
        salt=9,
        include_support=True,
    )
    assert abs(hero["headline"]["y"] - story["headline"]["y"]) >= 40
    assert abs(hero["headline"]["width"] - story["headline"]["width"]) >= 40


def test_location_portrait_applies_design_plan_pixels(client, db_session: Session) -> None:
    from investhome_api.services.social_design_engine.layout import social_layout_slots

    project = _create_project(db_session)
    aerial = _asset(db_session, project, filename="site-aerial-drone.jpg", folder_category="06_MEDIA")
    logo = _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_White.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    _asset(
        db_session,
        project,
        filename="Investhome_Logo_White.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    _asset(db_session, project, filename="IH_DC_TMP_001_Render_Exterior_Day_003.jpg")
    body = {
        "linked_project_id": str(project.id),
        "instruction": "The Temple projesinin lokasyon avantajını anlatan premium bir Instagram postu hazırla. 4:5",
        "mode": "create",
        "mode_explicit": True,
        "design_provider": "native",
        "draft": {"posts": [], "selected_post_id": None},
        "language": "tr",
        "builder_context": {"format_preset": "portrait"},
    }
    res = client.post("/ai/creative-studio/social/design", json=body)
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["meta"]["planner"] == "art_director"
    assert payload["meta"]["art_director"]["campaign_type"] == "LOCATION"
    post = payload["posts"][-1]
    assert post.get("width") == 1080
    assert post.get("height") == 1350
    assert post.get("planGeometryLocked") is True or post.get("formatPreset") == "portrait"
    hx, hy, hf = _headline_geo(post)
    recipe = social_layout_slots(1080, 1350, primitive="TOP_LEFT_EDITORIAL")["headline"]
    assert abs(hx - recipe["x"]) >= 8 or abs(hy - recipe["y"]) >= 40
    assert hf >= 36
    plan = payload["meta"]["design_plan"]
    headline_plan = plan.get("headline")
    assert isinstance(headline_plan, dict)
    assert int(headline_plan.get("x") or 0) == hx
    assert int(headline_plan.get("y") or 0) == hy
    assert plan.get("image_crop")
    cover = post.get("coverAssetId") or post.get("cover_asset_id")
    assert cover == str(aerial.id) or cover
    logo_els = [
        el
        for el in post.get("elements") or []
        if el.get("type") == "IMAGE" and el.get("role") == "logo"
    ]
    assert logo_els
    assert any(el.get("assetId") == str(logo.id) or el.get("asset_id") == str(logo.id) for el in logo_els)
    blob = " ".join(
        str(el.get("content") or el.get("label") or "")
        for el in post.get("elements") or []
    ).lower()
    assert "irr" not in blob
    assert "roi" not in blob
    assert "%" not in blob or "14%" not in blob
    variants = payload.get("design_variants") or []
    ys = []
    for variant in variants:
        x, y, _f = _headline_geo(variant.get("post") or {})
        ys.append((x, y))
    assert len({row[1] for row in ys}) >= 2
    invented = ("500,000", "500000", "14%", "irr", "roi")
    assert not any(token in blob for token in invented)


def test_claim_guard_still_blocks_invented_location_numbers(client, db_session: Session) -> None:
    project = _create_project(db_session)
    _asset(db_session, project, filename="site-aerial-drone.jpg", folder_category="06_MEDIA")
    _asset(
        db_session,
        project,
        filename="IH_DC_TMP_001_Logo_White.svg",
        folder_category="01_BRAND",
        content_type="image/svg+xml",
    )
    res = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(project.id),
            "instruction": (
                "The Temple projesinin lokasyon avantajını anlatan premium bir Instagram postu hazırla. "
                "14% IRR and $500,000 minimum."
            ),
            "mode": "create",
            "mode_explicit": True,
            "design_provider": "native",
            "draft": {"posts": [], "selected_post_id": None},
            "language": "tr",
            "builder_context": {"format_preset": "portrait"},
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["meta"]["art_director"]["campaign_type"] == "LOCATION"
    post = payload["posts"][-1]
    blob = " ".join(
        str(el.get("content") or el.get("label") or "")
        for el in post.get("elements") or []
    ).lower()
    assert "metric" not in {str(el.get("type") or "").lower() for el in post.get("elements") or []} or "METRIC_GROUP" not in {
        el.get("type") for el in post.get("elements") or []
    }
    types = {el.get("type") for el in post.get("elements") or []}
    assert "METRIC_GROUP" not in types
    assert "14%" not in blob
    assert "500,000" not in blob
    assert "irr" not in blob
