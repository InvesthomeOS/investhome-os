"""Phase 5.4G — adaptive composition engine gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.adaptive_composition_engine import MAX_SOLVE_ITERS, compose_adaptive
from investhome_api.services.creative_director.commercial_offer_composer import measure_production_copy
from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard, objects_hit_hard_occupancy
from investhome_api.services.creative_director.creative_contrast_engine import contrast_ratio, evaluate_group
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import build_family_library, family_by_id, seeded_reference_family
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.family_composition_constraints import PROOF_FAMILIES, family_constraints
from investhome_api.services.creative_director.phase5_final_composition import WORKFLOW_ID_54G, generate_final_composition_4x5
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, REQUIRED_FACTS, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.reference_quality_filter import GRADE_A
from investhome_api.services.creative_director.structured_typography_compositor_v2 import revision_readiness, turkish_copy_is_valid


def _library():
    catalog = {name: seeded_reference_family(name) for name in GRADE_A.values()}
    return build_family_library(catalog)


def test_graphic_field_semantic_role_unlocks_visual_replace() -> None:
    spec = {
        "project_photo": {"asset_id": "photo"},
        "graphic_field": {"semantic_role": "graphic_field", "overlay": "right_top_charcoal_dissolve", "asset_id": "field"},
        "headline": {"bounds": {"x": 0.5, "y": 0.1, "w": 0.4, "h": 0.12}},
        "price": {"bounds": {"x": 0.5, "y": 0.4, "w": 0.3, "h": 0.08}},
    }
    ready = revision_readiness(spec)
    assert ready["checks"]["VISUAL_REPLACE_ONLY"] == "PASS"
    assert ready["checks"]["PRICE_EDIT_ONLY"] == "PASS"
    assert ready["checks"]["COPY_EDIT_ONLY"] == "PASS"
    alias = dict(spec)
    alias.pop("graphic_field")
    alias["family_field"] = {"asset_id": "field"}
    assert revision_readiness(alias)["checks"]["VISUAL_REPLACE_ONLY"] == "PASS"


def test_turkish_copy_accepts_utf8_and_rejects_mojibake() -> None:
    facts = {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }
    assert turkish_copy_is_valid(facts) is True
    assert "İ" in facts["unit_type"]
    assert "Ş" in facts["cta"]
    bad = dict(facts)
    bad["unit_type"] = "2+1 DAÄ°RE"
    assert turkish_copy_is_valid(bad) is False


def test_occupancy_is_not_one_rectangle() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (168, 186, 210))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((300, 80, 620, 900), fill=(150, 140, 128))
    occ = build_photo_occupancy_map(photo)
    assert occ["schema"] == "PhotoOccupancyMapV1"
    layers = occ["layers"]
    for name in ("hard_protected", "soft_occupied", "preferred_negative_space", "graphically_extendable", "text_safe"):
        assert name in layers
        assert layers[name].size == CANVAS_4X5
    assert occ["coverage"]["hard_protected"] > 0.02
    assert occ["sky_area"] > 0.05


def test_collision_uses_silhouette_not_fat_spire_rect() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (180, 195, 215))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((360, 120, 560, 720), fill=(155, 145, 135))
    occ = build_photo_occupancy_map(photo)
    hard = occ["layers"]["hard_protected"]
    sky_box = (40, 40, 180, 120)
    assert box_hits_hard(hard, sky_box) is False
    objects = {"headline": {"px": list(sky_box)}}
    assert objects_hit_hard_occupancy(objects, hard) is False
    building_box = (380, 180, 520, 280)
    assert box_hits_hard(hard, building_box) is True


def test_typography_metrics_are_real() -> None:
    fonts = build_font_registry()
    family = family_by_id(_library(), "EDITORIAL_DARK_FIELD")
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=CANVAS_4X5, scale=1.0)
    for key in ("headline", "unit_type", "price", "discount", "discount_label", "cta"):
        assert metrics[key]["width"] > 24
        assert metrics[key]["height"] > 10
        assert metrics[key]["placeholder"] is False
    assert metrics["price"]["width"] > 80
    assert metrics["discount"]["height"] >= 20


def test_family_constraints_are_relationships() -> None:
    for fid in PROOF_FAMILIES:
        spec = family_constraints(fid)
        assert "required" in spec and "forbidden" in spec
        assert "source_coordinates_as_placement" in spec["forbidden"]
        assert spec["flex_modes"]
        assert "x = 0.72" not in str(spec)


def test_contrast_engine_rejects_dark_on_dark() -> None:
    image = Image.new("RGB", (200, 80), (18, 22, 28))
    report = evaluate_group(image, box=(10, 10, 180, 60), color=(22, 26, 32), role="headline")
    assert report["pass"] is False
    assert contrast_ratio((244, 239, 228), (20, 24, 30)) > 8


def test_adaptive_engine_has_no_image_model() -> None:
    import investhome_api.services.creative_director.adaptive_composition_engine as engine
    import investhome_api.services.creative_director.phase5_final_composition as prod

    assert "edit_image" not in inspect.getsource(engine)
    assert "generate_image" not in inspect.getsource(engine)
    assert "edit_image" not in inspect.getsource(prod)
    assert "generate_image" not in inspect.getsource(prod)
    assert "images/generations" not in inspect.getsource(prod)
    assert MAX_SOLVE_ITERS == 10
    assert list(PROOF_FAMILIES) == ["EDITORIAL_DARK_FIELD", "TYPE_IN_PLANE", "SKY_EDITORIAL"]


def test_adaptive_compose_emits_turkish_and_plan() -> None:
    photo = Image.new("RGB", (1600, 2000), (170, 188, 210))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((520, 200, 980, 1400), fill=(158, 148, 136))
    fonts = build_font_registry()
    family = family_by_id(_library(), "SKY_EDITORIAL")
    pack = compose_adaptive(source=photo, family=family, fonts=fonts, logo_rgba=None)
    assert pack["schema"] == "AdaptiveCompositionPlanV1"
    assert pack["facts"]["cta"] == "PROJEYİ KEŞFET"
    assert "İ" in pack["facts"]["unit_type"]
    assert pack["iterations"] <= 10
    assert pack["objects"]["price"]["bounds"]["w"] > 0.08
    assert pack["flex_mode"] in family_constraints("SKY_EDITORIAL")["flex_modes"]


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_final_composition as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54G-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    r1 = [{"workflow": "phase5_4a_r1_final_polish", "keep": True}]
    revision = [{"workflow": "phase5_5_master_revision", "keep": True}]
    gf54e = [{"workflow": "phase5_4e_graphic_field_master", "keep": True}]
    fam54f = [{"workflow": "phase5_4f_master_families", "keep": True}]
    approved = {MASTER_COMMERCIAL_R1_ID: {"approval_status": "HUMAN_APPROVED"}}
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {"current_version": 2, "current_cover_asset_id": PRODUCTION_COVER_V2},
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {},
            "approved_creative_masters": approved,
            "photo_foundation_tests": [{"keep": True}],
            "creative_design_tests": [{"keep": True}],
            "creative_overlay_tests": [{"keep": True}],
            "creative_master_tests": [{"keep": True}],
            "production_creative_tests": [{"keep": True}],
            "visual_art_director_tests": [{"keep": True}],
            "design_scene_tests": [{"keep": True}],
            "creative_master_library_tests": [{"keep": True}],
            "premium_commercial_final_tests": [{"keep": True}],
            "premium_commercial_r1_tests": r1,
            "master_revision_tests": revision,
            "architecture_lock_tests": [{"keep": True}],
            "creative_quality_tests": [{"keep": True}],
            "creative_quality_r1_tests": [{"keep": True}],
            "generative_master_tests": [{"keep": True}],
            "graphic_field_master_tests": gf54e,
            "master_family_tests": fam54f,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4g test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    monkeypatch.setattr(
        pm,
        "locate_design_references",
        lambda *_a, **_k: {
            "found": False,
            "fail_fast": True,
            "reason": "missing",
            "canonical_folder_name": CANONICAL_FOLDER_NAME,
            "media_library_search": {"folder_count_scanned": 0},
            "drive_walk": {"root_name": "Investhome OS", "root_folder_id": "x", "visited": 1},
            "drive_name_query": {"matches": []},
        },
    )
    result = generate_final_composition_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54G
    assert result["status"] == "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["phase55_executed"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("graphic_field_master_tests") == gf54e
    assert phase5.get("master_family_tests") == fam54f
    assert phase5.get("approved_creative_masters") == approved
    assert result["candidates"] == []
    db.rollback()
    db.close()
