"""Bounded local recomposition — content growth, mask, compositor, occupancy."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.bounded_local_recomposition import (
    EXECUTION,
    build_commercial_mask,
    compose_region,
    detect_price_content_growth,
)
from investhome_api.services.creative_director.design_spec import (
    is_provider_revision_route,
    route_revision,
)
from investhome_api.services.creative_director.edit_map import (
    analyze_raster,
    build_edit_map,
    validate_edit_map,
)
from investhome_api.services.creative_director.price_block_revision import parse_price_block
from investhome_api.services.creative_director.revision import (
    build_revision_diff,
    interpret_revision_intents,
)
from test_edit_map_v1 import COVER_V2, LOGO, SOURCE_V2, _synthetic_temple_raster

COMMAND = (
    "Liste fiyatı 675.000 USD aynı kalsın ve üzeri çizili gösterilsin.\n"
    "%35 lansman indirimi sonrası satış fiyatını 438.750 USD olarak ekle.\n"
    "Ayrıca 'Kazancınız 236.250 USD' bilgisini ekle.\n"
    "Bunun dışında tasarımda hiçbir şeyi değiştirme."
)


def test_classifier_stays_price_edit_only() -> None:
    from investhome_api.services.creative_director.master_revision_controller import (
        classify_revision_command,
    )

    plan = classify_revision_command(COMMAND)
    assert plan["intent"] == "PRICE_EDIT_ONLY"
    intents = interpret_revision_intents(COMMAND)
    diff = build_revision_diff(instruction=COMMAND, production_brief={})
    route = route_revision(instruction=COMMAND, revision_diff=diff, intents=intents)
    assert route == "PRICE_EDIT_ONLY"
    assert not is_provider_revision_route("BOUNDED_LOCAL_RECOMPOSITION")
    assert not is_provider_revision_route("PRICE_EDIT_ONLY")


def test_content_growth_one_slot_to_three() -> None:
    intent = parse_price_block(COMMAND)
    assert intent is not None
    assert intent.list_amount == 675_000
    assert intent.launch_amount == 438_750
    assert intent.savings_amount == 236_250
    edit_map = {
        "regions": [
            {
                "semantic_role": "old_price",
                "occupied": True,
                "bbox": {"x0": 400, "y0": 330, "x1": 620, "y1": 540},
            },
            {"semantic_role": "new_price", "occupied": False, "bbox": None},
            {"semantic_role": "savings_price", "occupied": False, "bbox": None},
            {
                "semantic_role": "commercial_group",
                "occupied": True,
                "bbox": {"x0": 226, "y0": 319, "x1": 882, "y1": 550},
            },
        ],
        "groups": [
            {
                "id": "commercial_group",
                "expansion": {
                    "internal_capacity": {
                        "additional_price_rows": 0,
                        "down_px_before_hero": 4,
                    }
                },
            }
        ],
    }
    growth = detect_price_content_growth(edit_map, intent)
    assert growth["content_growth"] is True
    assert growth["before"] == {
        "old_price": True,
        "new_price": False,
        "savings_price": False,
    }
    assert growth["after_request"] == {
        "old_price": True,
        "new_price": True,
        "savings_price": True,
    }
    assert growth["occupied_slots_before"] == 1
    assert growth["occupied_slots_after"] == 3
    assert growth["fits_current_geometry"] is False
    assert growth["execution"] == EXECUTION
    assert growth["mutable_region_role"] == "upper_creative_zone"
    assert growth["content_growth_route"] == "upper_creative_zone"


def test_mask_alpha_zero_only_inside_commercial_bbox() -> None:
    bbox = {"x0": 226, "y0": 319, "x1": 882, "y1": 550}
    raw = build_commercial_mask((1088, 1360), bbox)
    mask = Image.open(io.BytesIO(raw)).convert("RGBA")
    assert mask.size == (1088, 1360)
    px = mask.load()
    assert px[226, 319][3] == 0
    assert px[881, 549][3] == 0
    assert px[225, 319][3] == 255
    assert px[226, 318][3] == 255
    assert px[882, 319][3] == 255
    assert px[400, 900][3] == 255
    assert px[0, 0][3] == 255


def test_compose_region_keeps_outside_pixels_identical() -> None:
    original = Image.new("RGB", (80, 60), (10, 20, 30))
    draw = ImageDraw.Draw(original)
    draw.rectangle([0, 0, 79, 20], fill=(200, 180, 40))
    draw.rectangle([0, 40, 79, 59], fill=(20, 80, 200))
    provider = original.copy()
    pdraw = ImageDraw.Draw(provider)
    pdraw.rectangle([0, 0, 79, 59], fill=(1, 2, 3))
    bbox = {"x0": 10, "y0": 22, "x1": 70, "y1": 38}
    composed = compose_region(original, provider, bbox)
    op, cp = original.load(), composed.load()
    for y in range(60):
        for x in range(80):
            inside = bbox["x0"] <= x < bbox["x1"] and bbox["y0"] <= y < bbox["y1"]
            if inside:
                assert cp[x, y] == (1, 2, 3)
            else:
                assert cp[x, y] == op[x, y]


def test_occupied_new_and_savings_require_bbox() -> None:
    im = _synthetic_temple_raster()
    layout = analyze_raster(im)
    edit_map = build_edit_map(
        layout,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        occupied_price_slots={
            "old_price": True,
            "new_price": True,
            "savings_price": True,
        },
    )
    result = validate_edit_map(
        edit_map,
        expected_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        current_cover_asset_id=COVER_V2,
    )
    assert result["status"] == "pass", result["failures"]
    regions = {r["semantic_role"]: r for r in edit_map["regions"]}
    assert regions["old_price"]["occupied"] is True
    assert regions["new_price"]["occupied"] is True
    assert regions["savings_price"]["occupied"] is True
    assert regions["new_price"]["bbox"]
    assert regions["savings_price"]["bbox"]
    assert edit_map["future_slots"]["new_price"]["occupied"] is True
    assert edit_map["future_slots"]["savings_price"]["occupied"] is True
    group = next(g for g in edit_map["groups"] if g["id"] == "commercial_group")
    assert "new_price" in group["children"]
    assert "savings_price" in group["children"]
    assert group["column_relationship"]["layout"] == "restacked_price_hierarchy"


def test_commercial_bbox_requires_safe_bbox() -> None:
    from fastapi import HTTPException

    from investhome_api.services.creative_director.bounded_local_recomposition import (
        commercial_bbox,
    )

    edit_map = {
        "regions": [
            {
                "semantic_role": "commercial_group",
                "bbox": {"x0": 226, "y0": 319, "x1": 882, "y1": 550},
            }
        ]
    }
    try:
        commercial_bbox(edit_map)
        raise AssertionError("Phase 1 semantic bbox must not be used")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "safe_bbox" in str(exc.detail)


def test_content_growth_bbox_uses_upper_creative_zone() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        commercial_bbox,
    )

    upper = {"x0": 0, "y0": 0, "x1": 1088, "y1": 554}
    zone = {"x0": 220, "y0": 248, "x1": 890, "y1": 554}
    group = {"x0": 221, "y0": 303, "x1": 886, "y1": 554}
    edit_map = {
        "regions": [
            {
                "semantic_role": "commercial_group",
                "safe_bbox": group,
            },
            {
                "semantic_role": "commercial_content_zone",
                "safe_bbox": zone,
            },
            {
                "semantic_role": "upper_creative_zone",
                "safe_bbox": upper,
            },
        ]
    }
    assert commercial_bbox(edit_map) == group
    assert commercial_bbox(edit_map, content_growth=True) == upper


def test_ghost_check_rejects_unchanged_original_tails() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        ghost_check,
    )

    original = Image.new("RGB", (120, 80), (8, 12, 28))
    draw = ImageDraw.Draw(original)
    draw.rectangle([10, 8, 110, 18], fill=(220, 180, 60))
    draw.rectangle([10, 62, 110, 72], fill=(230, 230, 230))
    composed = original.copy()
    bbox = {"x0": 8, "y0": 4, "x1": 114, "y1": 76}
    edit_map = {
        "regions": [
            {
                "semantic_role": "commercial_group",
                "semantic_bbox": {"x0": 8, "y0": 20, "x1": 114, "y1": 60},
                "visual_bbox": {"x0": 8, "y0": 8, "x1": 114, "y1": 74},
                "safe_bbox": bbox,
            },
            {"semantic_role": "hero_visual", "bbox": {"x0": 0, "y0": 76, "x1": 120, "y1": 80}},
        ]
    }
    result = ghost_check(original, composed, bbox, edit_map)
    assert result["status"] == "fail"
    assert any("ghost_residual" in f for f in result["failures"])


def test_ghost_check_passes_when_tails_are_rewritten() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        ghost_check,
    )

    original = Image.new("RGB", (120, 80), (8, 12, 28))
    draw = ImageDraw.Draw(original)
    draw.rectangle([10, 8, 110, 18], fill=(220, 180, 60))
    draw.rectangle([10, 62, 110, 72], fill=(230, 230, 230))
    composed = Image.new("RGB", (120, 80), (8, 12, 28))
    cdraw = ImageDraw.Draw(composed)
    cdraw.rectangle([18, 22, 100, 54], fill=(240, 240, 240))
    cdraw.rectangle([18, 40, 70, 52], fill=(210, 170, 70))
    bbox = {"x0": 8, "y0": 4, "x1": 114, "y1": 76}
    edit_map = {
        "regions": [
            {
                "semantic_role": "commercial_group",
                "semantic_bbox": {"x0": 8, "y0": 20, "x1": 114, "y1": 60},
                "visual_bbox": {"x0": 8, "y0": 8, "x1": 114, "y1": 74},
                "safe_bbox": bbox,
            },
            {"semantic_role": "hero_visual", "bbox": {"x0": 0, "y0": 76, "x1": 120, "y1": 80}},
        ]
    }
    result = ghost_check(original, composed, bbox, edit_map)
    assert result["status"] == "pass", result


def test_commercial_bbox_prefers_safe_bbox() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        commercial_bbox,
    )

    edit_map = {
        "regions": [
            {
                "semantic_role": "commercial_group",
                "bbox": {"x0": 226, "y0": 319, "x1": 882, "y1": 550},
                "safe_bbox": {"x0": 221, "y0": 303, "x1": 886, "y1": 554},
            }
        ]
    }
    box = commercial_bbox(edit_map)
    assert box == {"x0": 221, "y0": 303, "x1": 886, "y1": 554}


def test_fact_check_does_not_fail_on_glyph_miss(monkeypatch) -> None:
    from investhome_api.services.creative_director import bounded_local_recomposition as blr

    monkeypatch.setattr(blr, "_token_present", lambda *_a, **_k: False)
    im = Image.new("RGB", (220, 140), (8, 12, 28))
    draw = ImageDraw.Draw(im)
    draw.rectangle([8, 8, 70, 55], fill=(240, 240, 240))
    draw.rectangle([78, 8, 140, 55], fill=(240, 240, 240))
    draw.rectangle([148, 8, 210, 55], fill=(210, 170, 70))
    draw.rectangle([20, 70, 100, 120], fill=(240, 240, 240))
    intent = parse_price_block(COMMAND)
    result = blr.fact_check(im, {"x0": 0, "y0": 0, "x1": 220, "y1": 140}, intent)
    assert result["status"] == "pass", result
    assert not any(str(f).startswith("missing_fact:") for f in result["failures"])
    assert "local_glyph_matcher" in result["strategy"]["advisory_only"]
    assert result["signals"]["glyph_matcher_advisory"]["confidence"] == 0.0


def test_fact_check_fails_when_commercial_type_unreadable() -> None:
    from investhome_api.services.creative_director import bounded_local_recomposition as blr

    im = Image.new("RGB", (80, 80), (8, 12, 28))
    intent = parse_price_block(COMMAND)
    result = blr.fact_check(im, {"x0": 0, "y0": 0, "x1": 80, "y1": 80}, intent)
    assert result["status"] == "fail"
    assert "commercial_type_not_readable" in result["failures"]


def test_region_prompt_recomposes_upper_header() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        build_region_edit_prompt,
    )

    intent = parse_price_block(COMMAND)
    prompt = build_region_edit_prompt(intent, region_role="upper_creative_zone", hero_y=554)
    assert "Do NOT change the subheadline" not in prompt
    assert "Do NOT recreate the advertisement" in prompt
    assert "Do NOT redesign this ad" in prompt
    assert "authorized upper header" in prompt.lower()
    assert "438.750" in prompt
    assert "236.250" in prompt
    assert "y=554" in prompt
    assert "ALIRKEN KAZAN" in prompt
    assert "Do not enlarge typography merely to fill space" in prompt


def test_subheadline_lock_skipped_when_inside_content_zone() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        immutable_region_deltas,
    )

    original = Image.new("RGB", (100, 100), (8, 12, 28))
    composed = original.copy()
    ImageDraw.Draw(composed).rectangle([20, 30, 80, 70], fill=(240, 240, 240))
    edit_map = {
        "regions": [
            {"semantic_role": "headline", "bbox": {"x0": 10, "y0": 0, "x1": 90, "y1": 20}},
            {"semantic_role": "subheadline", "bbox": {"x0": 10, "y0": 22, "x1": 90, "y1": 40}},
            {"semantic_role": "hero_visual", "bbox": {"x0": 0, "y0": 80, "x1": 100, "y1": 100}},
            {"semantic_role": "cta", "bbox": {"x0": 20, "y0": 82, "x1": 80, "y1": 90}},
            {"semantic_role": "logo", "bbox": {"x0": 30, "y0": 92, "x1": 70, "y1": 98}},
        ]
    }
    zone = {"x0": 10, "y0": 20, "x1": 90, "y1": 80}
    locks = immutable_region_deltas(original, composed, edit_map, mutable_bbox=zone)
    assert locks["headline"]["status"] == "pass"
    assert locks["hero_visual"]["status"] == "pass"
    assert locks["cta"]["status"] == "pass"
    assert locks["logo"]["status"] == "pass"
    assert locks["subheadline"]["status"] == "skip"


def test_headline_lock_skipped_when_inside_upper_zone() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        immutable_region_deltas,
    )

    original = Image.new("RGB", (100, 100), (8, 12, 28))
    composed = original.copy()
    ImageDraw.Draw(composed).rectangle([0, 0, 99, 79], fill=(240, 240, 240))
    edit_map = {
        "regions": [
            {"semantic_role": "headline", "bbox": {"x0": 10, "y0": 0, "x1": 90, "y1": 20}},
            {"semantic_role": "subheadline", "bbox": {"x0": 10, "y0": 22, "x1": 90, "y1": 40}},
            {"semantic_role": "hero_visual", "bbox": {"x0": 0, "y0": 80, "x1": 100, "y1": 100}},
            {"semantic_role": "cta", "bbox": {"x0": 20, "y0": 82, "x1": 80, "y1": 90}},
            {"semantic_role": "logo", "bbox": {"x0": 30, "y0": 92, "x1": 70, "y1": 98}},
        ]
    }
    zone = {"x0": 0, "y0": 0, "x1": 100, "y1": 80}
    locks = immutable_region_deltas(original, composed, edit_map, mutable_bbox=zone)
    assert locks["headline"]["status"] == "skip"
    assert locks["subheadline"]["status"] == "skip"
    assert locks["hero_visual"]["status"] == "pass"
    assert locks["cta"]["status"] == "pass"
    assert locks["logo"]["status"] == "pass"


def test_small_copy_inside_large_upper_zone_is_skipped() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        immutable_region_deltas,
    )

    original = Image.new("RGB", (200, 120), (8, 12, 28))
    composed = original.copy()
    ImageDraw.Draw(composed).rectangle([0, 0, 199, 79], fill=(240, 240, 240))
    edit_map = {
        "regions": [
            {"semantic_role": "headline", "bbox": {"x0": 20, "y0": 4, "x1": 180, "y1": 22}},
            {"semantic_role": "subheadline", "bbox": {"x0": 30, "y0": 26, "x1": 170, "y1": 38}},
            {"semantic_role": "supporting_copy", "bbox": {"x0": 40, "y0": 42, "x1": 160, "y1": 52}},
            {"semantic_role": "hero_visual", "bbox": {"x0": 0, "y0": 80, "x1": 200, "y1": 120}},
            {"semantic_role": "cta", "bbox": {"x0": 40, "y0": 90, "x1": 160, "y1": 100}},
            {"semantic_role": "logo", "bbox": {"x0": 70, "y0": 105, "x1": 130, "y1": 116}},
        ]
    }
    zone = {"x0": 0, "y0": 0, "x1": 200, "y1": 80}
    locks = immutable_region_deltas(original, composed, edit_map, mutable_bbox=zone)
    assert locks["headline"]["status"] == "skip"
    assert locks["subheadline"]["status"] == "skip"
    assert locks["supporting_copy"]["status"] == "skip"
    assert locks["hero_visual"]["status"] == "pass"
    assert locks["cta"]["status"] == "pass"
    assert locks["logo"]["status"] == "pass"


def test_clipping_check_flags_type_on_hero_edge() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        clipping_check,
    )

    im = Image.new("RGB", (200, 80), (8, 12, 28))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 77, 199, 79], fill=(240, 240, 240))
    bbox = {"x0": 0, "y0": 0, "x1": 200, "y1": 80}
    result = clipping_check(im, bbox)
    assert result["status"] == "fail"
    assert "commercial_clipped_at_hero_boundary" in result["failures"]


def test_clipping_check_allows_inset_headline_at_canvas_top() -> None:
    from investhome_api.services.creative_director.bounded_local_recomposition import (
        clipping_check,
    )

    im = Image.new("RGB", (200, 80), (8, 12, 28))
    draw = ImageDraw.Draw(im)
    draw.rectangle([20, 8, 180, 28], fill=(240, 240, 240))
    bbox = {"x0": 0, "y0": 0, "x1": 200, "y1": 80}
    result = clipping_check(im, bbox)
    assert result["status"] == "pass", result
    assert "commercial_clipped_at_canvas_top" not in result["failures"]
    assert "commercial_clipped_at_headline_lock" not in result["failures"]
