"""Phase 4.0A — NativeMasterDesignSpecV1.1 creative quality polish."""

from __future__ import annotations

from copy import deepcopy

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.native_master import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PHASE4_MASTER_ID,
    PHASE4_PARENT_SPEC_ID,
    POLISH_REASON,
    SCHEMA,
    SCHEMA_V1_1,
    TEMPLE_PROJECT_ID,
    consistency_report,
    inspect_application_font_assets,
    materialize_native_master_spec,
    persist_phase4_native_master,
    polish_native_master_v1_1,
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
    im = Image.new("RGB", (2268, 1234), (42, 58, 72))
    draw = ImageDraw.Draw(im)
    draw.rectangle([620, 280, 1640, 1180], fill=(90, 96, 102))
    draw.polygon([(1100, 80), (1180, 1180), (1020, 1180)], fill=(160, 150, 130))
    return im


def _logo() -> Image.Image:
    im = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([40, 55, 360, 105], fill=(201, 168, 92, 255))
    return im


def _parent():
    return materialize_native_master_spec(
        direction=__import__(
            "investhome_api.services.creative_director.native_master",
            fromlist=["direct_native_master_creative"],
        ).direct_native_master_creative(),
        source_size=_source().size,
        project_id=TEMPLE_PROJECT_ID,
        campaign_id=CAMPAIGN,
        hero_asset_id=LOCKED_HERO_ASSET_ID,
        logo_asset_id=LOCKED_LOGO_ASSET_ID,
        phase4_master_id=PHASE4_MASTER_ID,
        spec_id=PHASE4_PARENT_SPEC_ID,
    )


def test_font_inventory_does_not_invent_faces() -> None:
    report = inspect_application_font_assets()
    assert report["inventory_count"] >= 1
    assert "DejaVu" in report["decision"] or report["premium_faces_found"]


def test_v1_parent_preserved_and_v11_is_child() -> None:
    parent = _parent()
    parent_id = parent["native_master_design_spec_id"]
    direction, spec = polish_native_master_v1_1(parent, source_size=_source().size)
    assert parent["schema"] == SCHEMA
    assert parent["native_master_design_spec_id"] == parent_id
    assert spec["schema"] == SCHEMA_V1_1
    assert spec["parent_native_master_design_spec_id"] == PHASE4_PARENT_SPEC_ID
    assert spec["polish_reason"] == POLISH_REASON
    assert spec["content"] == parent["content"]
    assert spec["provenance"]["rendered_at"] is None
    assert spec["provenance"]["spec_created_before_render"] is True
    assert direction["layout_model"] == "editorial_field_above_architecture"


def test_architecture_collision_resolved() -> None:
    parent = _parent()
    _, spec = polish_native_master_v1_1(parent, source_size=_source().size)
    geom = spec["geometry"]
    assert geom["commercial_group"]["y1"] <= geom["hero_visual"]["y0"]
    assert spec["validation"]["status"] == "pass"
    image, drawn = render_native_master(spec, source_image=_source(), logo_image=_logo())
    assert image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
    report = consistency_report(spec, drawn)
    assert report["status"] == "pass", report
    assert report["architecture_collision"] == "RESOLVED"
    blob = " ".join(drawn["drawn_content"])
    for token in ("ALIRKEN", "KAZAN", "2+1", "DAİRE", "675.000 USD", "%35", "LANSMAN AVANTAJI", "PROJEYİ KEŞFET"):
        assert token in blob
    crop = spec["image_treatments"]["hero"]["source_crop_rectangle"]
    dest = spec["image_treatments"]["hero"]["destination_geometry"]
    assert dest["y0"] > 0
    assert crop["x1"] > crop["x0"]
    assert spec["content_capacity"]["current_capacity"] == 3
    assert spec["content_capacity"]["max_before_reflow"] == 5
    assert spec["assets"]["hero_visual"]["asset_id"] == LOCKED_HERO_ASSET_ID
    assert spec["assets"]["logo"]["asset_id"] == LOCKED_LOGO_ASSET_ID
    assert drawn["image_provider_calls"] == 0
    assert drawn["ai_architecture_generation"] is False


def test_persist_keeps_v1_and_does_not_touch_production() -> None:
    parent = _parent()
    _, spec = polish_native_master_v1_1(parent, source_size=_source().size)
    ctx = deepcopy(COPY_CTX)
    persist_phase4_native_master(ctx, parent)
    persist_phase4_native_master(ctx, spec)
    assert PHASE4_PARENT_SPEC_ID in ctx["phase4_native_masters"]
    assert spec["native_master_design_spec_id"] in ctx["phase4_native_masters"]
    assert ctx["phase4_native_master_v1_spec_id"] == PHASE4_PARENT_SPEC_ID
    before = {
        **snapshot_identity(COPY_CTX),
        "master_creative": dict(COPY_CTX["master_creative"]),
        "current_master_design_spec_id": COPY_CTX["current_master_design_spec_id"],
    }
    after = {
        **snapshot_identity(ctx),
        "master_creative": dict(ctx["master_creative"]),
        "current_master_design_spec_id": ctx["current_master_design_spec_id"],
    }
    assert production_pointers_unchanged(before, after) == {}
    assert ctx["current_cover_asset_id"] == COVER_V2
    assert ctx["master_creative"]["current_version"] == 2
