"""Phase 4.0 — NativeMasterDesignSpecV1 created before render, v2 untouched."""

from __future__ import annotations

from copy import deepcopy

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.native_master import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    SCHEMA,
    TEMPLE_PROJECT_ID,
    build_finalized_native_master,
    consistency_report,
    persist_phase4_native_master,
    production_pointers_unchanged,
)
from investhome_api.services.creative_director.native_master_render import render_native_master

CAMPAIGN = "e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5"
COVER_V2 = "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"

COPY_CTX = {
    "master_creative": {
        "project_id": TEMPLE_PROJECT_ID,
        "current_version": 2,
        "current_cover_asset_id": COVER_V2,
        "current_edit_map_id": "map-v2",
        "source_visual_asset_id": LOCKED_HERO_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "revision_history": [{"version": 2}],
    },
    "current_cover_asset_id": COVER_V2,
    "current_edit_map_id": "map-v2",
    "latest_master_ad_asset_id": COVER_V2,
    "finished_ad_raster_asset_id": COVER_V2,
}


def _source() -> Image.Image:
    im = Image.new("RGB", (2268, 1234), (42, 58, 72))
    draw = ImageDraw.Draw(im)
    draw.rectangle([620, 280, 1640, 1180], fill=(90, 96, 102))
    draw.rectangle([900, 420, 1360, 980], fill=(120, 110, 95))
    return im


def _logo() -> Image.Image:
    im = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([20, 40, 380, 120], outline=(201, 168, 92, 255), width=4)
    draw.rectangle([40, 55, 360, 105], fill=(201, 168, 92, 255))
    return im


def _finalized():
    return build_finalized_native_master(
        source_size=_source().size,
        project_id=TEMPLE_PROJECT_ID,
        campaign_id=CAMPAIGN,
        hero_asset_id=LOCKED_HERO_ASSET_ID,
        logo_asset_id=LOCKED_LOGO_ASSET_ID,
    )


def test_spec_exists_before_render() -> None:
    direction, spec = _finalized()
    assert spec["schema"] == SCHEMA
    assert spec["provenance"]["spec_created_before_render"] is True
    assert spec["provenance"]["extracted_from_raster"] is False
    assert spec["provenance"]["rendered_at"] is None
    assert spec["rendered_master_visual_asset_id"] is None
    assert spec["provenance"]["spec_finalized_at"]
    assert "E_render_from_spec" not in spec["provenance"]["pipeline"]
    assert direction["layout_model"] == "editorial_hero_led_overlay"
    assert direction["commercial_layout"] == "price_led_editorial_lockup"
    assert direction["not_a_template_fill"] is True


def test_locked_assets_and_content() -> None:
    _, spec = _finalized()
    assert spec["asset_policy"] == "PROJECT_LOCKED"
    assert spec["assets"]["hero_visual"]["asset_id"] == LOCKED_HERO_ASSET_ID
    assert spec["assets"]["logo"]["asset_id"] == LOCKED_LOGO_ASSET_ID
    assert spec["assets"]["logo"]["replaceable"] is False
    content = spec["content"]
    assert content["headline"] == "ALIRKEN KAZAN"
    assert content["supporting_copy"] == "The Temple'da yerinizi lansman döneminde alın."
    assert content["unit_value"] == "2+1"
    assert content["unit_label"] == "DAİRE"
    assert content["list_price"] == "675.000 USD"
    assert content["discount_value"] == "%35"
    assert content["discount_label"] == "LANSMAN AVANTAJI"
    assert content["cta"] == "PROJEYİ KEŞFET"


def test_actual_fonts_and_canvas_stored() -> None:
    _, spec = _finalized()
    assert spec["canvas"]["width"] == CANVAS_WIDTH
    assert spec["canvas"]["height"] == CANVAS_HEIGHT
    assert spec["canvas"]["canonical"] is True
    fonts = spec["typography"]["actual_fonts_used"]
    assert fonts
    headline = spec["typography"]["roles"]["headline_line_2"]
    assert headline["actual_available_family"]
    assert headline.get("invented") is False
    crop = spec["image_treatments"]["hero"]["source_crop_rectangle"]
    assert crop["x1"] > crop["x0"]
    assert spec["image_treatments"]["hero"]["ai_architecture_generation"] is False


def test_commercial_is_not_kpi_or_v2_row() -> None:
    _, spec = _finalized()
    group = next(g for g in spec["groups"] if g["id"] == "commercial_group")
    assert group["layout_model"] != "three_column_row"
    assert group["not_kpi_cards"] is True
    assert spec["content_capacity"]["current_capacity"] == 3
    assert spec["content_capacity"]["max_before_reflow"] == 5
    assert spec["revision_policy"]["implemented"] is False
    assert spec["format_adaptation_policy"]["implemented"] is False


def test_render_from_finalized_spec() -> None:
    _, spec = _finalized()
    finalized_at = spec["provenance"]["spec_finalized_at"]
    image, drawn = render_native_master(spec, source_image=_source(), logo_image=_logo())
    assert image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
    assert spec["provenance"]["rendered_at"]
    assert spec["provenance"]["spec_finalized_at"] == finalized_at
    assert spec["provenance"]["rendered_at"] >= finalized_at
    assert "E_render_from_spec" in spec["provenance"]["pipeline"]
    assert drawn["ai_architecture_generation"] is False
    assert drawn["image_provider_calls"] == 0
    assert drawn["layout_invented"] is False
    report = consistency_report(spec, drawn)
    assert report["status"] == "pass", report
    blob = " ".join(drawn["drawn_content"])
    for token in ("ALIRKEN", "KAZAN", "2+1", "DAİRE", "675.000 USD", "%35", "LANSMAN AVANTAJI", "PROJEYİ KEŞFET"):
        assert token in blob


def test_persist_does_not_touch_production_v2() -> None:
    _, spec = _finalized()
    ctx = deepcopy(COPY_CTX)
    ctx["current_master_design_spec_id"] = "f07d9813-e1e7-4f71-9996-9ed2203fdfe6"
    ctx["master_creative"] = dict(ctx["master_creative"])
    ctx["master_creative"]["current_master_design_spec_id"] = "f07d9813-e1e7-4f71-9996-9ed2203fdfe6"
    before_snap = snapshot_identity(ctx)
    before = {
        **before_snap,
        "master_creative": dict(ctx["master_creative"]),
        "current_master_design_spec_id": ctx["current_master_design_spec_id"],
    }
    persist_phase4_native_master(ctx, spec)
    after = {
        **snapshot_identity(ctx),
        "master_creative": dict(ctx["master_creative"]),
        "current_master_design_spec_id": ctx["current_master_design_spec_id"],
    }
    assert production_pointers_unchanged(before, after) == {}
    assert ctx["current_cover_asset_id"] == COPY_CTX["current_cover_asset_id"]
    assert ctx["master_creative"]["current_version"] == 2
    assert ctx["current_master_design_spec_id"] == "f07d9813-e1e7-4f71-9996-9ed2203fdfe6"
    assert spec["native_master_design_spec_id"] in ctx["phase4_native_masters"]
    assert ctx["phase4_native_master_tests"][spec["phase4_master_id"]]["production"] is False
