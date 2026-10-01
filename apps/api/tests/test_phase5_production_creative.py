"""Phase 5.2 — production creative system. Architecture lock + fonts + gates."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry, resolve_role
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_production_creative import (
    CONCEPT_SEEDS,
    HEURISTIC_PROTECTION,
    WORKFLOW_ID_52,
    _fallback_plan,
    build_scene_spec,
    critic_hard_reject,
    generate_production_creative_4x5,
    plan_quality_gate,
    text_on_photo_detection,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_font_registry_prefers_open_display_not_dejavu() -> None:
    registry = build_font_registry()
    display = resolve_role("DISPLAY_SERIF")
    number = resolve_role("COMMERCIAL_NUMBER")
    cta = resolve_role("CTA")
    assert registry["premium_or_brand_available"] is True
    assert display["fallback_kind"] == "none"
    assert display.get("premium_open") is True
    assert number.get("premium_open") is True
    assert cta.get("premium_open") is True


def test_plan_gate_rejects_spire_collision_and_weak_rationale() -> None:
    protection = {"regions": dict(HEURISTIC_PROTECTION)}
    bad = {
        "photo_specific_rationale": "looks nice",
        "regions": {
            "headline": {"x": 0.30, "y": 0.04, "w": 0.22, "h": 0.12},
            "commercial": {"x": 0.10, "y": 0.80, "w": 0.85, "h": 0.12},
            "cta": {"x": 0.30, "y": 0.20, "w": 0.2, "h": 0.08},
        },
    }
    gate = plan_quality_gate(bad, protection)
    assert gate["pass"] is False
    assert "photo_specific_rationale_weak" in gate["failures"]
    assert "headline_through_spire" in gate["failures"]
    assert "bottom_information_strip" in gate["failures"]
    good = _fallback_plan(CONCEPT_SEEDS[0], dict(REQUIRED_FACTS))
    assert plan_quality_gate(good, protection)["pass"] is True


def test_critic_thresholds_and_text_on_photo() -> None:
    assert critic_hard_reject({"architecture_truth": 9, "professional_design_quality": 9, "photo_design_integration": 9, "visual_hierarchy": 9, "commercial_readability": 9, "text_on_photo_likeness": 1, "template_likeness": 1}) is True
    assert critic_hard_reject({"architecture_truth": 10, "professional_design_quality": 8, "photo_design_integration": 8, "visual_hierarchy": 8, "commercial_readability": 8, "text_on_photo_likeness": 3, "template_likeness": 3}) is False
    assert critic_hard_reject({"architecture_truth": 10, "professional_design_quality": 8, "photo_design_integration": 8, "visual_hierarchy": 8, "commercial_readability": 8, "text_on_photo_likeness": 4, "template_likeness": 1}) is True
    fonts = build_font_registry()
    protection = {"regions": dict(HEURISTIC_PROTECTION)}
    plan = _fallback_plan(CONCEPT_SEEDS[0], dict(REQUIRED_FACTS))
    spec = build_scene_spec(plan, dict(REQUIRED_FACTS), protection, fonts)
    foundation = Image.new("RGB", CANVAS_4X5, (180, 190, 200))
    report = text_on_photo_detection(foundation, spec, protection)
    assert "headline_through_spire" not in report["flags"]
    spec["type"][0]["box"] = {"x": 0.30, "y": 0.05, "w": 0.2, "h": 0.08}
    spec["type"][1]["box"] = {"x": 0.30, "y": 0.12, "w": 0.2, "h": 0.08}
    report2 = text_on_photo_detection(foundation, spec, protection)
    assert report2["reject"] is True


def test_scene_spec_preserves_editability() -> None:
    fonts = build_font_registry()
    plan = _fallback_plan(CONCEPT_SEEDS[1], dict(REQUIRED_FACTS))
    spec = build_scene_spec(plan, dict(REQUIRED_FACTS), {"regions": dict(HEURISTIC_PROTECTION)}, fonts)
    assert spec["schema"] == "CreativeSceneSpecV1"
    assert "list_price" in spec["hierarchy"]
    assert spec["facts"]["list_price"] == "675.000 USD"
    assert "commercial_lockup" in spec["groups"]
    assert spec["protected_architecture"]["SPIRE"]
    assert spec["fonts"]["DISPLAY_SERIF"]["font_file"]


def test_production_generate_does_not_touch_history(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_production_creative as prod

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P52-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    master_51e = [{"workflow": "phase5_1e_final_master", "keep": True}]
    overlay = [{"workflow": "phase5_1d_r2_photo_aware", "keep": True}]
    photo = [{"workflow": "phase5_1b_photo_foundation", "keep": True}]
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {"current_version": 2, "current_cover_asset_id": PRODUCTION_COVER_V2},
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {"5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}},
            "photo_foundation_tests": photo,
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": overlay,
            "creative_master_tests": master_51e,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.2 test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    ImageDraw.Draw(hero).rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return _png(hero)

    monkeypatch.setattr(prod, "_read_bytes", fake_read)
    monkeypatch.setattr(prod, "analyze_reference_dna", lambda *_a, **_k: ({"schema": "CreativeReferenceAnalysisV1", "mode": "mock"}, 0))
    monkeypatch.setattr(prod, "request_protection_map", lambda *_a, **_k: ({"schema": "ProtectedArchitectureMapV1", "regions": dict(HEURISTIC_PROTECTION), "mode": "mock"}, 0))
    monkeypatch.setattr(prod, "request_art_direction_plan", lambda **k: (_fallback_plan(k["seed"], dict(REQUIRED_FACTS)), 0))
    monkeypatch.setattr(
        prod,
        "request_design_critic",
        lambda **k: (
            {
                "architecture_truth": 10,
                "professional_design_quality": 8,
                "photo_design_integration": 8,
                "visual_hierarchy": 8,
                "commercial_readability": 8,
                "typography_quality": 8,
                "template_likeness": 2,
                "text_on_photo_likeness": 2,
                "art_director_would_present": True,
                "mode": "mock",
            },
            0,
        ),
    )
    monkeypatch.setattr(prod, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(prod, "asset_url", lambda _id: f"/media/{_id}")

    result = generate_production_creative_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_52
    assert result["architecture_generation_used"] is False
    assert result["gpt_image_edit_calls"] == 0
    assert result["final_size"] == list(CANVAS_4X5)
    assert result["candidates_generated"] >= 1
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("creative_master_tests") == master_51e
    assert phase5.get("creative_overlay_tests") == overlay
    assert phase5.get("photo_foundation_tests") == photo
    assert any(t.get("workflow") == WORKFLOW_ID_52 for t in phase5.get("production_creative_tests") or [])
    db.rollback()
    db.close()
