"""Phase 4.0B — Generative Creative Director → AIArtDirectionPlanV1 → NativeMasterDesignSpecV2."""

from __future__ import annotations

from copy import deepcopy

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.generative_creative_director import (
    FINGERPRINT_40A,
    PHASE4B_TEST_KEY,
    PLAN_SCHEMA,
    compile_art_direction_plan,
    generate_art_direction_plan,
    generate_native_master_from_director,
    persist_phase4b,
    structural_fingerprint,
    validate_art_direction_plan,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.native_master import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PHASE4_MASTER_ID,
    PHASE4_PARENT_SPEC_ID,
    SCHEMA,
    SCHEMA_V1_1,
    SCHEMA_V2,
    TEMPLE_PROJECT_ID,
    consistency_report,
    persist_phase4_native_master,
    production_pointers_unchanged,
)
from investhome_api.services.creative_director.native_master_render import render_native_master

COVER_V2 = "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
CAMPAIGN = "e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5"

COPY_CTX = {
    "master_creative": {
        "project_id": TEMPLE_PROJECT_ID,
        "current_version": 2,
        "current_cover_asset_id": COVER_V2,
        "current_edit_map_id": "map-v2",
        "source_visual_asset_id": LOCKED_HERO_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "revision_history": [{"version": 2}],
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
    },
    "current_cover_asset_id": COVER_V2,
    "current_edit_map_id": "map-v2",
    "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
    "latest_master_ad_asset_id": COVER_V2,
    "finished_ad_raster_asset_id": COVER_V2,
}


def _source() -> Image.Image:
    im = Image.new("RGB", (2268, 1234), (150, 170, 190))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, 2268, 220], fill=(176, 196, 214))
    draw.polygon([(1080, 40), (1180, 1180), (980, 1180)], fill=(120, 108, 92))
    draw.rectangle([1260, 360, 2100, 1180], fill=(88, 92, 98))
    draw.rectangle([0, 1080, 2268, 1234], fill=(48, 52, 46))
    return im


def _logo() -> Image.Image:
    im = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([40, 55, 360, 105], fill=(201, 168, 92, 255))
    return im


def test_plan_exists_before_spec_and_spec_before_render() -> None:
    analysis, plan, spec = generate_native_master_from_director(_source())
    assert plan["schema"] == PLAN_SCHEMA
    assert plan["ai_art_direction_plan_id"]
    assert plan["compiled_spec_id"] == spec["native_master_design_spec_id"]
    assert spec["schema"] == SCHEMA_V2
    assert spec["ai_art_direction_plan_id"] == plan["ai_art_direction_plan_id"]
    assert spec["provenance"]["art_direction_plan_created_before_spec"] is True
    assert spec["provenance"]["spec_created_before_render"] is True
    assert spec["provenance"]["rendered_at"] is None
    assert spec["rendered_master_visual_asset_id"] is None
    assert analysis["source_size"]["width"] == 2268
    assert analysis["text_safe_left_of_spire"] is True
    assert spec["creative_direction"]["not_phase40a_plate"] is True


def test_anti_template_and_novelty_reject_phase40a() -> None:
    analysis, plan, spec = generate_native_master_from_director(_source())
    gate = validate_art_direction_plan(plan)
    assert gate["status"] == "pass"
    assert gate["anti_template"] == "pass"
    assert gate["novelty_vs_phase40a"] >= 4
    fp = structural_fingerprint(plan)
    assert fp != FINGERPRINT_40A
    assert fp["dominant_color_field"] != "full_width_navy_plate"
    assert fp["cta_anchor"] != "full_width_seam"
    assert spec["cta_treatment"]["shape"] == "underlined_action"
    clone = dict(plan)
    clone.update(FINGERPRINT_40A)
    clone["geometry_intent"] = {
        **plan["geometry_intent"],
        "sky_wash": {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 0.33},
    }
    rejected = validate_art_direction_plan(clone)
    assert rejected["status"] == "fail"
    assert "too_similar_to_phase40a" in rejected["errors"] or "generic_plate" in rejected["errors"]
    try:
        compile_art_direction_plan(clone, analysis)
    except ValueError as exc:
        assert "rejected before compile" in str(exc)
    else:
        raise AssertionError("compiler must not silently template-ize a 4.0A plate")


def test_locked_assets_content_and_render() -> None:
    _, plan, spec = generate_native_master_from_director(_source())
    assert spec["asset_policy"] == "PROJECT_LOCKED"
    assert spec["assets"]["hero_visual"]["asset_id"] == LOCKED_HERO_ASSET_ID
    assert spec["assets"]["logo"]["asset_id"] == LOCKED_LOGO_ASSET_ID
    assert spec["assets"]["logo"]["replaceable"] is False
    content = spec["content"]
    assert content["headline"] == "ALIRKEN KAZAN"
    assert content["list_price"] == "675.000 USD"
    assert content["cta"] == "PROJEYİ KEŞFET"
    assert "438.750" not in str(content)
    assert spec["content_capacity"]["current_capacity"] == 3
    assert spec["content_capacity"]["max_before_reflow"] == 5
    assert "left_voice_column" in spec["content_capacity"]["preferred_growth_direction"]
    assert spec["revision_policy"]["implemented"] is False
    assert spec["format_adaptation_policy"]["implemented"] is False
    assert spec["identity"]["production"] is False
    assert spec["test_status"] == PHASE4B_TEST_KEY
    image, drawn = render_native_master(spec, source_image=_source(), logo_image=_logo())
    assert image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
    assert spec["provenance"]["rendered_at"]
    assert drawn["image_provider_calls"] == 0
    assert drawn["ai_architecture_generation"] is False
    assert drawn["layout_invented"] is False
    report = consistency_report(spec, drawn)
    assert report["status"] == "pass", report
    blob = " ".join(drawn["drawn_content"])
    for token in ("ALIRKEN", "KAZAN", "2+1", "DAİRE", "675.000 USD", "%35", "LANSMAN AVANTAJI", "PROJEYİ KEŞFET"):
        assert token in blob
    assert spec["typography"]["roles"]["headline_line_2"]["alignment"] == "left"
    protected = spec["geometry"]["protected_architecture"]
    commercial = spec["geometry"]["commercial_group"]
    assert commercial["x1"] <= protected["x0"] or commercial["y1"] <= protected["y0"]
    assert plan["image_type_relationship"]


def test_persist_does_not_overwrite_prior_phases_or_production() -> None:
    _, plan, spec = generate_native_master_from_director(_source())
    ctx = deepcopy(COPY_CTX)
    ctx["phase4_native_masters"] = {
        PHASE4_PARENT_SPEC_ID: {"schema": SCHEMA, "native_master_design_spec_id": PHASE4_PARENT_SPEC_ID, "phase4_master_id": PHASE4_MASTER_ID},
        "62df86cc-b9c0-467d-a6a3-a2b296c2c0db": {
            "schema": SCHEMA_V1_1,
            "native_master_design_spec_id": "62df86cc-b9c0-467d-a6a3-a2b296c2c0db",
            "phase4_master_id": PHASE4_MASTER_ID,
            "parent_native_master_design_spec_id": PHASE4_PARENT_SPEC_ID,
        },
    }
    ctx["phase4a_native_master_spec_id"] = "62df86cc-b9c0-467d-a6a3-a2b296c2c0db"
    ctx["phase4_native_master_v1_spec_id"] = PHASE4_PARENT_SPEC_ID
    before = {
        **snapshot_identity(ctx),
        "master_creative": dict(ctx["master_creative"]),
        "current_master_design_spec_id": ctx["current_master_design_spec_id"],
    }
    persist_phase4b(ctx, plan, spec)
    persist_phase4_native_master(ctx, spec)
    after = {
        **snapshot_identity(ctx),
        "master_creative": dict(ctx["master_creative"]),
        "current_master_design_spec_id": ctx["current_master_design_spec_id"],
    }
    assert production_pointers_unchanged(before, after) == {}
    assert ctx["current_cover_asset_id"] == COVER_V2
    assert ctx["master_creative"]["current_version"] == 2
    assert PHASE4_PARENT_SPEC_ID in ctx["phase4_native_masters"]
    assert "62df86cc-b9c0-467d-a6a3-a2b296c2c0db" in ctx["phase4_native_masters"]
    assert spec["native_master_design_spec_id"] in ctx["phase4_native_masters"]
    assert ctx["phase4a_native_master_spec_id"] == "62df86cc-b9c0-467d-a6a3-a2b296c2c0db"
    assert ctx["phase4b_art_direction_plans"][plan["ai_art_direction_plan_id"]]["schema"] == PLAN_SCHEMA
    assert spec["phase4_master_id"] != PHASE4_MASTER_ID
    assert ctx["phase4_native_master_tests"][spec["phase4_master_id"]]["production"] is False
    assert ctx["phase4_native_master_tests"][spec["phase4_master_id"]]["ai_art_direction_plan_id"] == plan["ai_art_direction_plan_id"]
