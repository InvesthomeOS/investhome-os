"""Phase 12.5-R1 — family-wide revision result lock. No pixels. No Phase 12.6."""

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
)
from investhome_api.services.creative_director.phase12_3_lock import selected_family_record
from investhome_api.services.creative_director.phase12_4_approve_lock import apply_human_approval, family_wide_revision_ready
from investhome_api.services.creative_director.phase12_5_lock import CHILD_1X1_ID, CHILD_9X16_ID
from investhome_api.services.creative_director.phase12_5_r1_lock import (
    CHILD_1X1_ASSET,
    CHILD_9X16_ASSET,
    NEXT_PHASE,
    WORKFLOW_ID_12_5_R1,
    format_results,
    generate_phase12_5_r1_revision_lock,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    COMPLETE_SUCCESS,
    ENGINE_PRODUCTION_READY,
    FAIL,
    FEED_PORTRAIT,
    LANDSCAPE,
    PARTIAL_SUCCESS,
    SKIP_FORMAT_MASTER_MISSING,
    SKIP_TARGET_NOT_PRESENT,
    SQUARE,
    STATUS_FAMILY_WIDE_PARTIAL,
    STORY_REEL,
    family_wide_user_confirmation,
    ornek_00013_family,
    route_family_wide_revision,
    score_family_wide_revision,
)
from investhome_api.services.creative_director.premium_creative_product_model import premium_revision_contract
from investhome_api.services.creative_director.project_creative_master_library import empty_library


def _catalog() -> dict:
    return {
        FILE_4X5: {"filename": FILE_4X5, "asset_id": ASSET_4X5, "sha256": "a", "width": 4252, "height": 5315, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        FILE_9X16: {"filename": FILE_9X16, "asset_id": ASSET_9X16, "sha256": "b", "width": 1080, "height": 1920, "format": STORY_REEL, "folder": "DESIGN_REFERENCE"},
        FILE_1X1: {"filename": FILE_1X1, "asset_id": ASSET_1X1, "sha256": "c", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00004.jpg": {"filename": "ORNEK_00004.jpg", "asset_id": "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279", "sha256": "d", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
    }


def test_legitimate_skip_is_partial_success_not_fail() -> None:
    assert score_family_wide_revision(format_results()) == PARTIAL_SUCCESS
    assert score_family_wide_revision(format_results()) != FAIL
    all_done = [
        {"format": STORY_REEL, "outcome": "REVISED", "applicable": True},
        {"format": SQUARE, "outcome": "REVISED", "applicable": True},
    ]
    assert score_family_wide_revision(all_done) == COMPLETE_SUCCESS
    failed = [{"format": STORY_REEL, "outcome": FAIL, "applicable": True}]
    assert score_family_wide_revision(failed) == FAIL


def test_price_command_skips_missing_target_and_missing_format() -> None:
    family = apply_human_approval(selected_family_record(_catalog()))
    classified = classify_production_intent("Fiyatı tüm kampanyada 375.000 USD yap.")
    assert classified["intent"] == FAMILY_WIDE_REVISION
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [ornek_00013_family(), family]
    wide = route_family_wide_revision(classified=classified, library=library, family_id=FAMILY_ID)
    assert [item["format"] for item in wide["targets"]] == [STORY_REEL, SQUARE]
    skipped = {item["format"]: item for item in wide["skipped"]}
    assert skipped[FEED_PORTRAIT]["reason"] == SKIP_TARGET_NOT_PRESENT
    assert skipped[LANDSCAPE]["reason"] == SKIP_FORMAT_MASTER_MISSING
    assert wide["never_invent_missing_semantic"] is True
    ready = family_wide_revision_ready(family)
    assert [item["format"] for item in ready["route"]["targets"]] == [STORY_REEL, SQUARE]


def test_user_facing_confirmation_is_plain_language() -> None:
    text = family_wide_user_confirmation(territory="PRICE", revised_count=2)
    assert text == "Fiyat, kampanyada fiyat bilgisi bulunan 2 tasarımda güncellendi."
    assert "SKIP_" not in text
    assert "PARTIAL_SUCCESS" not in text


def test_lock_does_not_generate_or_start_copy_revision() -> None:
    src = inspect.getsource(generate_phase12_5_r1_revision_lock)
    assert "persist_gpt_image" not in src
    assert "generate_gpt_image" not in src
    assert "openai" not in src.lower()
    assert '"ideogram_calls": 0' in src
    assert "phase12_6_executed" in src
    assert NEXT_PHASE == "12.6 FAMILY-WIDE COPY REVISION PROOF"
    assert WORKFLOW_ID_12_5_R1 == "phase12_5_r1_family_wide_revision_result_lock"
    assert STATUS_FAMILY_WIDE_PARTIAL == "FAMILY_WIDE_REVISION_PARTIAL_SUCCESS"
    assert ENGINE_PRODUCTION_READY == "PRODUCTION READY"
    assert CHILD_9X16_ID != CHILD_1X1_ID
    assert CHILD_9X16_ASSET != CHILD_1X1_ASSET
    assert premium_revision_contract()["family_wide_revision"]["status"] == ENGINE_PRODUCTION_READY
    assert "must not create or keep a 4:5 revision child" in src
