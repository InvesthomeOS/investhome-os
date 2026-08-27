"""Edit Map v1 — raster-aware map, current-cover SoT, validation."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.edit_map import (
    EDIT_MAP_PROVIDER_CAPABILITIES,
    analyze_raster,
    bbox_iou,
    build_edit_map,
    persist_edit_map,
    render_debug_overlay,
    resolve_current_cover_asset_id,
    stamp_current_cover,
    validate_edit_map,
)
from investhome_api.services.creative_director.provider_router import (
    EDIT_MAP_PROVIDER_CAPABILITIES as ROUTER_CAPS,
)
from investhome_api.services.creative_director.revision import (
    resolve_master_asset_id,
    resolve_revision_visual_asset_id,
)

COVER_V2 = "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
COVER_V1 = "b297693c-e170-4bf2-8556-80af9375d3ed"
SOURCE_V2 = "299bd265-a0ea-486d-866d-1947f103fd57"
LOGO = "7b58877e-efca-4e9a-9027-6fd18fb1b345"
COVER_V3 = "647e8e78-be87-482e-9236-fa1edf539e85"


def _synthetic_temple_raster(width: int = 400, height: int = 500) -> Image.Image:
    """Navy plate + 3-column stats + photo + gold CTA + footer logo. Not a design template."""
    im = Image.new("RGB", (width, height), (8, 12, 28))
    draw = ImageDraw.Draw(im)
    photo_y = int(height * 0.42)
    footer_y = int(height * 0.90)
    for y in range(photo_y, footer_y):
        for x in range(width):
            im.putpixel((x, y), (70 + (x % 40), 90 + (y % 30), 110))
    draw.rectangle([90, 28, 310, 70], fill=(240, 240, 240))
    draw.rectangle([80, 78, 320, 112], fill=(210, 170, 70))
    draw.rectangle([70, 118, 330, 138], fill=(205, 165, 75))
    cy0, cy1 = 155, photo_y - 8
    draw.rectangle([40, cy0, 130, cy1], fill=(235, 235, 235))
    draw.rectangle([155, cy0, 250, cy1], fill=(240, 240, 240))
    draw.rectangle([275, cy0, 360, cy1], fill=(235, 235, 235))
    cta_y0 = int(height * 0.82)
    draw.rectangle([90, cta_y0, 310, cta_y0 + 28], fill=(210, 170, 70))
    draw.rectangle([150, footer_y + 8, 250, height - 8], fill=(230, 230, 230))
    return im


def _map_from_synthetic() -> dict:
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
    return edit_map


def test_current_cover_is_visual_sot_not_v1_master() -> None:
    ctx = {
        "master_asset_id": COVER_V1,
        "master_finished_ad_asset_id": COVER_V1,
        "latest_master_ad_asset_id": COVER_V2,
        "finished_ad_raster_asset_id": COVER_V2,
        "master_creative": {
            "master_asset_id": COVER_V1,
            "current_cover_asset_id": COVER_V2,
        },
    }
    master = resolve_master_asset_id(ctx)
    cover = resolve_current_cover_asset_id(ctx)
    visual = resolve_revision_visual_asset_id(
        ctx, smb_current_final_asset_id=__import__("uuid").UUID(COVER_V3)
    )
    assert str(master) == COVER_V1
    assert str(cover) == COVER_V2
    assert str(visual) == COVER_V2
    assert str(visual) != COVER_V1
    assert str(visual) != COVER_V3


def test_stamp_current_cover_does_not_overwrite_master() -> None:
    ctx = {"master_creative": {"master_asset_id": COVER_V1}}
    stamp_current_cover(ctx, COVER_V2, edit_map_id="map-1")
    assert ctx["current_cover_asset_id"] == COVER_V2
    assert ctx["master_creative"]["current_cover_asset_id"] == COVER_V2
    assert ctx["master_creative"]["current_edit_map_id"] == "map-1"
    assert ctx["master_creative"]["master_asset_id"] == COVER_V1


def test_synthetic_raster_edit_map_passes() -> None:
    edit_map = _map_from_synthetic()
    assert edit_map["validation_status"] == "pass"
    assert edit_map["edit_map_version"] == "1.2"
    assert edit_map["cover_asset_id"] == COVER_V2
    assert edit_map["source_visual_asset_id"] == SOURCE_V2
    assert edit_map["logo_asset_id"] == LOGO
    assert edit_map["created_from"]["provider_calls"] == 0
    assert edit_map["created_from"]["design_spec_authoritative"] is False
    assert edit_map["created_from"]["debug_overlay_role"] == "internal_evidence_only"
    assert edit_map["confidence"] >= 0.55

    regions = {r["semantic_role"]: r for r in edit_map["regions"]}
    for role in (
        "hero_visual",
        "headline",
        "subheadline",
        "unit_label",
        "old_price",
        "discount",
        "logo",
        "cta",
        "supporting_copy",
        "commercial_group",
        "commercial_content_zone",
    ):
        assert role in regions, role
        assert regions[role]["occupied"] is True, role
        assert regions[role]["bbox"], role
        assert regions[role]["confidence"] > 0

    assert regions["old_price"]["occupied"] is True
    assert regions["new_price"]["occupied"] is False
    assert regions["savings_price"]["occupied"] is False
    assert regions["new_price"]["bbox"] is None
    assert regions["savings_price"]["bbox"] is None
    assert regions["new_price"]["rendered_pixels"] is False
    assert regions["old_price"]["group_id"] == "commercial_group"

    group = next(g for g in edit_map["groups"] if g["id"] == "commercial_group")
    assert set(group["children"]) == {"unit_label", "old_price", "discount"}
    assert group["column_relationship"]["layout"] == "three_column_row"
    assert isinstance(group["expansion"]["internal_capacity"]["down_px_before_hero"], int)
    assert group["blocked_boundaries"]["below"] == "hero_visual"

    hero = regions["hero_visual"]["bbox"]
    commercial = regions["commercial_group"]["bbox"]
    assert bbox_iou(hero, commercial) < 0.25
    assert commercial["y1"] <= hero["y0"]

    assert edit_map["future_slots"]["old_price"]["occupied"] is True
    assert edit_map["future_slots"]["new_price"]["occupied"] is False
    assert edit_map["future_slots"]["savings_price"]["occupied"] is False

    pres = edit_map["immutable_mask_metadata"]
    assert pres["PRICE_EDIT_ONLY"]["mutable"] == [
        "commercial_group",
        "unit_label",
        "old_price",
        "discount",
    ]
    assert "hero_visual" in pres["PRICE_EDIT_ONLY"]["immutable"]
    assert pres["PRICE_EDIT_ONLY"]["content_growth"]["mutable_region"] == "commercial_content_zone"
    zone = regions["commercial_content_zone"]
    assert zone["occupancy"]["supporting_copy"] is True
    assert zone["occupancy"]["old_price"] is True
    assert zone["occupancy"]["new_price"] is False
    assert zone["occupancy"]["savings_price"] is False
    assert "supporting_copy" in zone["children"]
    assert zone["safe_bbox"]["y1"] <= hero["y0"]
    assert zone["top_lock_y"] <= zone["safe_bbox"]["y0"]
    assert edit_map["content_growth"]["when_cannot_fit"] == "commercial_content_zone"
    assert pres["VISUAL_REPLACE_ONLY"]["mutable"] == ["hero_visual"]
    assert "old_price" in pres["VISUAL_REPLACE_ONLY"]["immutable"]
    assert "cta" in pres["VISUAL_REPLACE_ONLY"]["immutable"]


def test_edit_map_belongs_to_one_cover() -> None:
    edit_map = _map_from_synthetic()
    ctx: dict = {"master_creative": {"master_asset_id": COVER_V1}}
    persist_edit_map(ctx, edit_map)
    assert ctx["current_cover_asset_id"] == COVER_V2
    assert ctx["current_edit_map_id"] == edit_map["id"]
    assert ctx["edit_maps_by_cover"][COVER_V2] == edit_map["id"]
    other = dict(edit_map)
    other["cover_asset_id"] = COVER_V3
    result = validate_edit_map(
        other,
        expected_cover_asset_id=COVER_V2,
        current_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
    )
    assert result["status"] == "fail"
    assert "cover_asset_id_mismatch" in result["failures"]


def test_unoccupied_slots_cannot_claim_pixels() -> None:
    edit_map = _map_from_synthetic()
    regions = {r["id"]: r for r in edit_map["regions"]}
    regions["new_price"]["occupied"] = False
    regions["new_price"]["bbox"] = {"x0": 10, "y0": 10, "x1": 40, "y1": 40}
    regions["new_price"]["rendered_pixels"] = True
    result = validate_edit_map(
        edit_map,
        expected_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        current_cover_asset_id=COVER_V2,
    )
    assert result["status"] == "fail"
    assert "unoccupied_slot_has_pixel_bbox:new_price" in result["failures"]
    assert "unoccupied_slot_has_rendered_pixels:new_price" in result["failures"]


def test_hero_must_not_become_commercial_group() -> None:
    edit_map = _map_from_synthetic()
    regions = {r["id"]: r for r in edit_map["regions"]}
    regions["commercial_group"]["bbox"] = dict(regions["hero_visual"]["bbox"])
    result = validate_edit_map(
        edit_map,
        expected_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        current_cover_asset_id=COVER_V2,
    )
    assert result["status"] == "fail"
    assert "safe_bbox_invades_hero" in result["failures"]


def test_ornament_row_does_not_steal_photo_start() -> None:
    im = Image.new("RGB", (400, 500), (8, 12, 28))
    for y in range(90, 94):
        for x in range(400):
            im.putpixel((x, y), (80, 95, 110))
    for y in range(220, 450):
        for x in range(400):
            im.putpixel((x, y), (70 + (x % 30), 95, 115))
    layout = analyze_raster(im)
    assert layout["photo_start"] is not None
    assert layout["photo_start"] >= 200
    assert layout["photo_start"] < 240


def test_insufficient_confidence_is_not_faked() -> None:
    im = Image.new("RGB", (200, 200), (8, 12, 28))
    layout = analyze_raster(im)
    assert layout.get("photo_start") is None
    assert layout["confidence"] < 0.55


def test_debug_overlay_is_not_blank_and_same_size() -> None:
    im = _synthetic_temple_raster()
    layout = analyze_raster(im)
    edit_map = build_edit_map(
        layout,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        image=im,
    )
    debug = render_debug_overlay(im, edit_map)
    assert debug.size == im.size
    buf = io.BytesIO()
    debug.save(buf, format="PNG")
    assert len(buf.getvalue()) > 1000


def test_provider_capabilities_are_os_names_not_gpt_hardcode() -> None:
    assert "analyze_design" in EDIT_MAP_PROVIDER_CAPABILITIES
    assert "edit_region" in EDIT_MAP_PROVIDER_CAPABILITIES
    assert ROUTER_CAPS == EDIT_MAP_PROVIDER_CAPABILITIES
    assert "gpt-image" not in ROUTER_CAPS
    assert "gpt_image" not in ROUTER_CAPS


def test_safe_bbox_covers_visual_and_stops_at_hero() -> None:
    from investhome_api.services.creative_director.edit_map import render_geometry_debug

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
    assert edit_map["validation_status"] == "pass"
    commercial = next(r for r in edit_map["regions"] if r["semantic_role"] == "commercial_group")
    hero = next(r for r in edit_map["regions"] if r["semantic_role"] == "hero_visual")
    assert commercial["semantic_bbox"]
    assert commercial["visual_bbox"]
    assert commercial["safe_bbox"] == commercial["bbox"]
    assert commercial["safe_bbox"]["y1"] <= hero["bbox"]["y0"]
    assert commercial["hero_boundary"]["y"] == hero["bbox"]["y0"]
    assert commercial["pixel_coverage"]["strict_outside_safe"] == 0
    assert commercial["pixel_coverage"]["ghost_risk"] is False
    zone = next(r for r in edit_map["regions"] if r["semantic_role"] == "commercial_content_zone")
    assert zone["safe_bbox"]["y0"] >= zone["top_lock_y"]
    assert zone["safe_bbox"]["y1"] <= hero["bbox"]["y0"]
    assert bbox_iou(zone["safe_bbox"], hero["bbox"]) == 0.0
    supporting = next(r for r in edit_map["regions"] if r["semantic_role"] == "supporting_copy")
    assert supporting["bbox"]
    group = next(g for g in edit_map["groups"] if g["id"] == "commercial_group")
    assert "up_px" in group["expansion"]
    assert "down_px" in group["expansion"]
    debug = render_geometry_debug(im, edit_map)
    assert debug.size == im.size


def test_commercial_content_zone_sits_between_headline_and_hero() -> None:
    from investhome_api.services.creative_director.edit_map import (
        bbox_contains,
        render_content_zone_debug,
    )

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
    assert edit_map["validation_status"] == "pass"
    regions = {r["semantic_role"]: r for r in edit_map["regions"]}
    zone = regions["commercial_content_zone"]
    headline = regions["headline"]
    hero = regions["hero_visual"]
    commercial = regions["commercial_group"]
    supporting = regions["supporting_copy"]
    cta = regions["cta"]
    logo = regions["logo"]
    assert zone["occupied"] is True
    assert zone["safe_bbox"] == zone["bbox"]
    assert zone["safe_bbox"]["y0"] >= zone["top_lock_y"]
    assert zone["safe_bbox"]["y1"] <= hero["bbox"]["y0"]
    assert zone["safe_bbox"]["y0"] >= headline["bbox"]["y0"]
    assert bbox_contains(zone["safe_bbox"], supporting["bbox"], slack=24)
    assert bbox_contains(zone["safe_bbox"], commercial["visual_bbox"] or commercial["bbox"], slack=8)
    assert bbox_iou(zone["safe_bbox"], hero["bbox"]) == 0.0
    assert bbox_iou(zone["safe_bbox"], cta["bbox"]) == 0.0
    assert bbox_iou(zone["safe_bbox"], logo["bbox"]) == 0.0
    assert zone["occupancy"]["new_price"] is False
    assert zone["occupancy"]["savings_price"] is False
    debug = render_content_zone_debug(im, edit_map)
    assert debug.size == im.size


def test_glyph_tails_below_semantic_are_inside_safe_bbox() -> None:
    """Type pixels just above the hero must sit inside the mutable mask."""
    im = _synthetic_temple_raster(width=400, height=500)
    photo_y = int(500 * 0.42)
    for y in range(photo_y - 6, photo_y):
        for x in range(50, 350):
            im.putpixel((x, y), (240, 240, 240))
    layout = analyze_raster(im)
    semantic = layout["commercial_bbox"]
    edit_map = build_edit_map(
        layout,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        image=im,
    )
    commercial = next(r for r in edit_map["regions"] if r["semantic_role"] == "commercial_group")
    safe = commercial["safe_bbox"]
    visual = commercial["visual_bbox"]
    assert visual["y1"] > semantic["y1"] or visual["y1"] >= photo_y - 1
    assert safe["y1"] >= visual["y1"]
    assert safe["y1"] <= layout["hero_bbox"]["y0"]
    assert commercial["pixel_coverage"]["strict_outside_safe"] == 0
