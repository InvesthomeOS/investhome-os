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
