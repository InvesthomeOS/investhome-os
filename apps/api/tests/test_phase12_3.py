"""Phase 12.3 — existing multi-format family ingestion. No generation. No routing."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase12_3_family_ingest import (
    ASSET_1X1,
    ASSET_4X5,
    ASSET_9X16,
    FAMILY_ID,
    FILE_1X1,
    FILE_4X5,
    FILE_9X16,
    STATUS_PENDING,
    candidate_families,
    semantic_map_1x1,
    semantic_map_4x5,
    semantic_map_9x16,
)
from investhome_api.services.creative_director.phase12_3_lock import (
    format_master_inventory,
    generate_phase12_3_family_ingest,
    selected_family_record,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STORY_REEL,
    ornek_00013_family,
)


def _catalog() -> dict:
    return {
        FILE_4X5: {"filename": FILE_4X5, "asset_id": ASSET_4X5, "sha256": "a", "width": 4252, "height": 5315, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        FILE_9X16: {"filename": FILE_9X16, "asset_id": ASSET_9X16, "sha256": "b", "width": 1080, "height": 1920, "format": STORY_REEL, "folder": "DESIGN_REFERENCE"},
        FILE_1X1: {"filename": FILE_1X1, "asset_id": ASSET_1X1, "sha256": "c", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00004.jpg": {"filename": "ORNEK_00004.jpg", "asset_id": "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279", "sha256": "d", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00001.jpg": {"filename": "ORNEK_00001.jpg", "asset_id": "1d61bf43-5c14-446a-bf4d-96b29435876e", "sha256": "e", "width": 1080, "height": 1350, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00008.jpg": {"filename": "ORNEK_00008.jpg", "asset_id": "2537b300-8955-4e1a-b892-624d7db19fb7", "sha256": "f", "width": 1080, "height": 1350, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00013.jpg": {"filename": "ORNEK_00013.jpg", "asset_id": "a60a051f-5895-47df-958b-a738cbaf7d1f", "sha256": "g", "width": 1080, "height": 1350, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00009.jpg": {"filename": "ORNEK_00009.jpg", "asset_id": "e6f94897-f540-46f0-90ca-a359943a181f", "sha256": "h", "width": 1080, "height": 1350, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
    }


def test_selected_family_has_three_native_formats() -> None:
    family = selected_family_record(_catalog())
    assert family["FAMILY_ID"] == FAMILY_ID
    assert family["FAMILY_ID"] != ORNEK_FAMILY_ID
    assert family["approval_status"] == "PENDING HUMAN REVIEW"
    assert family["router_eligible"] is False
    assert family["inventory"] == {FEED_PORTRAIT: "FOUND", STORY_REEL: "FOUND", SQUARE: "FOUND", LANDSCAPE: "MISSING"}
    assert family["formats"][FEED_PORTRAIT]["SOURCE_ASSET_ID"] == ASSET_4X5
    assert family["formats"][STORY_REEL]["SOURCE_ASSET_ID"] == ASSET_9X16
    assert family["formats"][SQUARE]["SOURCE_ASSET_ID"] == ASSET_1X1
    assert family["formats"][LANDSCAPE]["FORMAT_MASTER_ID"] is None
    inventory = format_master_inventory(family)
    assert inventory["formats"][3]["STATUS"] == "MISSING"
    candidates = candidate_families(_catalog())
    assert len(candidates) == 5
    assert candidates[0]["selected"] is True
    assert sum(1 for item in candidates if item["selected"]) == 1


def test_ornek_family_is_unchanged_and_not_this_ingestion() -> None:
    family = ornek_00013_family()
    assert family["FAMILY_ID"] == ORNEK_FAMILY_ID == "716e4e5b-d25c-5669-b035-30a3c84bea9c"
    assert family["inventory"]["4:5"] == "HUMAN_APPROVED"
    assert family["inventory"]["9:16"] == "MISSING"
    assert family["inventory"]["1:1"] == "MISSING"
    assert family["inventory"]["16:9"] == "MISSING"


def test_semantic_maps_do_not_invent_cta() -> None:
    for semantic in (semantic_map_4x5(), semantic_map_9x16(), semantic_map_1x1()):
        by_id = {item["id"]: item for item in semantic["territories"]}
        assert by_id["CTA"]["present"] is False
        assert semantic["never_originate_design_from_map"] is True
    price_4x5 = next(item for item in semantic_map_4x5()["territories"] if item["id"] == "PRICE")
    assert price_4x5["present"] is False
    price_story = next(item for item in semantic_map_9x16()["territories"] if item["id"] == "PRICE")
    assert price_story["present"] is True


def test_ingestion_does_not_generate_or_activate() -> None:
    src = inspect.getsource(generate_phase12_3_family_ingest)
    assert "persist_gpt_image" not in src
    assert "openai" not in src.lower()
    assert "compose_story" not in src
    assert "execute_ornek_00013_story" not in src
    assert "PENDING HUMAN REVIEW" in src
    assert "router_eligible" in src
    assert STATUS_PENDING == "MULTI_FORMAT_FAMILY_PENDING_HUMAN_REVIEW"
