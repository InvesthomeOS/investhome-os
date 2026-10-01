"""Phase 3.1 — MasterDesignSpecV2 price revision, structured reconstruction."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.edit_map import analyze_raster, build_edit_map, validate_edit_map
from investhome_api.services.creative_director.master_design_spec import (
    build_master_design_spec,
    derive_price_revision_spec,
    persist_master_design_spec,
    snapshot_identity,
)
from investhome_api.services.creative_director.master_revision_controller import classify_revision_command
from investhome_api.services.creative_director.price_block_revision import parse_price_block
from investhome_api.services.creative_director.structured_reconstruction import (
    reconstruct_from_spec,
    validate_render,
)
from test_edit_map_v1 import COVER_V2, LOGO, SOURCE_V2, _synthetic_temple_raster
from test_master_design_spec_v1 import COPY_CTX, PROJECT

COMMAND = (
    "Liste fiyatı 675.000 USD aynı kalsın ve üzeri çizili gösterilsin.\n"
    "%35 lansman indirimi sonrası satış fiyatını 438.750 USD olarak ekle.\n"
    "Ayrıca 'Kazancınız 236.250 USD' bilgisini ekle.\n"
    "Bunun dışında tasarımda hiçbir şeyi değiştirme."
)


def _v1():
    im = _synthetic_temple_raster()
    layout = analyze_raster(im)
    edit_map = build_edit_map(
        layout,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        image=im,
    )
    validate_edit_map(
        edit_map,
        expected_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        current_cover_asset_id=COVER_V2,
    )
    spec = build_master_design_spec(
        ctx=COPY_CTX,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        project_id=PROJECT,
        edit_map=edit_map,
        layout=layout,
        image=im,
        source_version=2,
    )
    return im, spec


def test_command_is_price_edit_only() -> None:
    plan = classify_revision_command(COMMAND)
    assert plan["intent"] == "PRICE_EDIT_ONLY"
    intent = parse_price_block(COMMAND)
    assert intent is not None
    assert intent.list_amount == 675_000
    assert intent.launch_amount == 438_750
    assert intent.savings_amount == 236_250


def test_v2_spec_derived_not_mutated_parent() -> None:
    _im, v1 = _v1()
    parent_id = v1["master_design_spec_id"]
    intent = parse_price_block(COMMAND)
    v2 = derive_price_revision_spec(v1, intent)
    assert v1["master_design_spec_id"] == parent_id
    assert v1["spec_version"] == 1
    assert v1["schema"] == "MasterDesignSpecV1"
    assert not any(e.get("semantic_role") == "launch_price" for e in v1["elements"])
    assert v2["schema"] == "MasterDesignSpecV2"
    assert v2["spec_version"] == 2
    assert v2["parent_spec_id"] == parent_id
    assert v2["revision_intent"] == "PRICE_EDIT_ONLY"
    assert v2["preview_only"] is True
    assert v2["validation_status"] == "pass", v2["validation"]
    elements = {e["semantic_role"]: e for e in v2["elements"]}
    assert elements["list_price"]["strikethrough"] is True
    assert "438.750" in elements["launch_price"]["exact_content"]
    assert "236.250" in elements["savings"]["exact_content"]
    assert elements["headline"]["exact_content"] == "ALIRKEN KAZAN"
    assert elements["cta"]["exact_content"] == "PROJEYİ KEŞFET"
    commercial = next(g for g in v2["groups"] if g["id"] == "commercial_group")
    assert commercial["layout_model"] != "three_column_row"
    assert commercial["layout_model"] == "primary_price_plus_supporting_metrics"


def test_derive_does_not_persist() -> None:
    im, v1 = _v1()
    ctx = dict(COPY_CTX)
    ctx["master_creative"] = dict(COPY_CTX["master_creative"])
    persist_master_design_spec(ctx, v1)
    before = snapshot_identity(ctx)
    current_spec = ctx["current_master_design_spec_id"]
    v2 = derive_price_revision_spec(v1, parse_price_block(COMMAND))
    after = snapshot_identity(ctx)
    assert after == before
    assert ctx["current_master_design_spec_id"] == current_spec
    assert v2["master_design_spec_id"] not in (ctx.get("master_design_specs") or {})


def test_reconstruct_from_spec_no_provider() -> None:
    cover, v1 = _v1()
    v2 = derive_price_revision_spec(v1, parse_price_block(COMMAND))
    source = Image.new("RGB", (600, 800), (90, 110, 130))
    ImageDraw.Draw(source).rectangle([200, 80, 400, 700], fill=(180, 170, 140))
    logo = Image.new("RGBA", (80, 40), (220, 180, 70, 255))
    preview, report = reconstruct_from_spec(
        v2,
        source_visual=source,
        logo=logo,
        reference_cover=cover,
    )
    assert preview.size == (v2["canvas"]["width"], v2["canvas"]["height"])
    assert report["provider_image_calls"] == 0
    assert report["raster_surgery"] is False
    assert report["native_renderer"] is False
    rendered = validate_render(preview, v2, report)
    assert rendered["status"] == "pass", rendered
