"""Phase 12.4 — approve UniLoft Last Units family. No generation. No price revision."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import (
    FAMILY_WIDE_REVISION,
    classify_production_intent,
)
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import (
    ASSET_1X1,
    ASSET_4X5,
    ASSET_9X16,
    FAMILY_ID,
    FILE_1X1,
    FILE_4X5,
    FILE_9X16,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
)
from investhome_api.services.creative_director.phase12_3_lock import selected_family_record
from investhome_api.services.creative_director.phase12_4_approve_lock import (
    NEXT_PHASE,
    PHASE_12_5_COMMAND,
    STATUS,
    UNILOFT_PROJECT_ID,
    apply_human_approval,
    family_wide_revision_ready,
    generate_phase12_4_family_approval,
    routing_tests,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STATUS_FORMAT_MISSING,
    STORY_REEL,
    lookup_format_master,
    ornek_00013_family,
    resolve_family,
)
from investhome_api.services.creative_director.project_creative_master_library import empty_library


def _catalog() -> dict:
    return {
        FILE_4X5: {"filename": FILE_4X5, "asset_id": ASSET_4X5, "sha256": "a", "width": 4252, "height": 5315, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        FILE_9X16: {"filename": FILE_9X16, "asset_id": ASSET_9X16, "sha256": "b", "width": 1080, "height": 1920, "format": STORY_REEL, "folder": "DESIGN_REFERENCE"},
        FILE_1X1: {"filename": FILE_1X1, "asset_id": ASSET_1X1, "sha256": "c", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00004.jpg": {"filename": "ORNEK_00004.jpg", "asset_id": "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279", "sha256": "d", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
    }


def _approved_library() -> tuple[dict, dict]:
    family = apply_human_approval(selected_family_record(_catalog()))
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [ornek_00013_family(), family]
    return family, library


def test_family_is_human_approved_and_router_eligible() -> None:
    family, _library = _approved_library()
    assert family["FAMILY_ID"] == FAMILY_ID
    assert family["approval_status"] == "HUMAN_APPROVED"
    assert family["router_eligible"] is True
    assert family["production_status"] == "ACTIVE"
    assert family["project_id"] == UNILOFT_PROJECT_ID
    assert family["brand_id"] == "INVESTHOME"
    assert family["PROJECT_SCOPE"] == "UNILOFT"
    assert family["cross_project_reuse"] is False
    assert family["inventory"] == {
        FEED_PORTRAIT: "HUMAN_APPROVED",
        STORY_REEL: "HUMAN_APPROVED",
        SQUARE: "HUMAN_APPROVED",
        LANDSCAPE: "MISSING",
    }
    assert family["formats"][FEED_PORTRAIT]["SOURCE_FILENAME"] == FILE_4X5
    assert family["formats"][STORY_REEL]["SOURCE_FILENAME"] == FILE_9X16
    assert family["formats"][SQUARE]["SOURCE_FILENAME"] == FILE_1X1
    assert family["formats"][LANDSCAPE]["FORMAT_MASTER_ID"] is None
    assert family["formats"][LANDSCAPE]["APPROVAL_STATUS"] == "MISSING"


def test_routing_uses_each_approved_format_master() -> None:
    family, library = _approved_library()
    tests = routing_tests(family, library)
    assert tests["family_lookup"] == "PASS"
    assert tests["family_lookup_by_project"] == "PASS"
    assert tests["temple_does_not_receive_uniloft_family"] == "PASS"
    assert tests["brand_lookup_still_ornek"] == "PASS"
    assert tests["feed_4x5"]["selected_master_id"] == MASTER_4X5_ID
    assert tests["feed_4x5"]["source_filename_routed"] == FILE_4X5
    assert tests["feed_4x5"]["source_asset_id"] == ASSET_4X5
    assert tests["story_9x16"]["selected_master_id"] == MASTER_9X16_ID
    assert tests["story_9x16"]["source_filename_routed"] == FILE_9X16
    assert tests["story_9x16"]["source_asset_id"] == ASSET_9X16
    assert tests["square_1x1"]["selected_master_id"] == MASTER_1X1_ID
    assert tests["square_1x1"]["source_filename_routed"] == FILE_1X1
    assert tests["square_1x1"]["source_asset_id"] == ASSET_1X1
    assert tests["landscape_16x9"]["status"] == STATUS_FORMAT_MISSING
    assert tests["landscape_16x9"]["route"] == STATUS_FORMAT_MISSING
    assert tests["landscape_16x9"]["selected_master_id"] is None
    assert lookup_format_master(family, LANDSCAPE)["status"] == STATUS_FORMAT_MISSING


def test_family_wide_revision_is_ready_but_not_executed() -> None:
    family, _library = _approved_library()
    classified = classify_production_intent(PHASE_12_5_COMMAND)
    assert classified["intent"] == FAMILY_WIDE_REVISION
    ready = family_wide_revision_ready(family)
    assert ready["status"] == "READY"
    assert ready["executed"] is False
    assert ready["classified_intent"] == FAMILY_WIDE_REVISION
    assert [item["format"] for item in ready["route"]["targets"]] == [STORY_REEL, SQUARE]
    skipped = {item["format"]: item for item in ready["route"].get("skipped") or []}
    assert skipped[FEED_PORTRAIT]["reason"] == "SKIP_TARGET_NOT_PRESENT"
    assert LANDSCAPE in ready["route"]["missing_formats"]
    by_fmt = {item["format"]: item for item in ready["price_territories"]}
    assert by_fmt[FEED_PORTRAIT]["PRICE_present"] is False
    assert by_fmt[STORY_REEL]["PRICE_present"] is True
    assert by_fmt[SQUARE]["PRICE_present"] is True
    assert "photos" in ready["do_not_change"]
    assert ready["approved_masters_remain_immutable"] is True


def test_ornek_family_is_unchanged() -> None:
    family, library = _approved_library()
    ornek = resolve_family(library, brand_id="INVESTHOME", family_id=ORNEK_FAMILY_ID)
    assert ornek is not None
    assert ornek["FAMILY_ID"] == ORNEK_FAMILY_ID == "716e4e5b-d25c-5669-b035-30a3c84bea9c"
    assert ornek["inventory"][FEED_PORTRAIT] == "HUMAN_APPROVED"
    assert ornek["inventory"][STORY_REEL] == "MISSING"
    assert ornek["inventory"][SQUARE] == "MISSING"
    assert ornek["inventory"][LANDSCAPE] == "MISSING"
    assert family["FAMILY_ID"] != ORNEK_FAMILY_ID


def test_approval_does_not_generate_or_revise_price() -> None:
    src = inspect.getsource(generate_phase12_4_family_approval)
    assert "persist_gpt_image" not in src
    assert "openai" not in src.lower()
    assert "compose_story" not in src
    assert "execute_ornek_00013_story" not in src
    assert "price_revision_executed" in src
    assert "PHASE_12_5_COMMAND" in inspect.getsource(family_wide_revision_ready)
    assert PHASE_12_5_COMMAND.startswith("Bu kampanyadaki 357.000")
    assert "executed" in inspect.getsource(family_wide_revision_ready)
    assert STATUS == "PRODUCTION_PREMIUM_CREATIVE_FAMILY_APPROVED"
    assert NEXT_PHASE == "12.5 FAMILY-WIDE NATURAL LANGUAGE REVISION PROOF"
