"""Phase 12.6 — family-wide COPY_ONLY. No generation. No 16:9. No auto-approval."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
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
    FILE_1X1_VARIANT,
    FILE_4X5,
    FILE_9X16,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
)
from investhome_api.services.creative_director.phase12_3_lock import selected_family_record
from investhome_api.services.creative_director.phase12_4_approve_lock import apply_human_approval
from investhome_api.services.creative_director.phase12_5_lock import CHILD_1X1_ID as PRICE_CHILD_1X1_ID
from investhome_api.services.creative_director.phase12_5_lock import CHILD_9X16_ID as PRICE_CHILD_9X16_ID
from investhome_api.services.creative_director.phase12_5_r1_lock import CHILD_1X1_ASSET as PRICE_CHILD_1X1_ASSET
from investhome_api.services.creative_director.phase12_5_r1_lock import CHILD_9X16_ASSET as PRICE_CHILD_9X16_ASSET
from investhome_api.services.creative_director.phase12_6_copy_revise import (
    NEW_COPY,
    OLD_COPY,
    apply_feed_copy_revision,
    apply_square_copy_revision,
    apply_story_copy_revision,
)
from investhome_api.services.creative_director.phase12_6_lock import (
    CHILD_1X1_ID,
    CHILD_4X5_ID,
    CHILD_9X16_ID,
    ORIGINAL_PARENTS,
    PHASE_12_6_COMMAND,
    PRICE_CHILDREN,
    REVISION_TYPE,
    STATUS_FAIL,
    STATUS_PENDING,
    WORKFLOW_ID_12_6,
    generate_phase12_6_family_wide_copy_revision,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SKIP_FORMAT_MASTER_MISSING,
    SQUARE,
    STORY_REEL,
    route_family_wide_revision,
)
from investhome_api.services.creative_director.project_creative_master_library import empty_library


def _catalog() -> dict:
    return {
        FILE_4X5: {"filename": FILE_4X5, "asset_id": ASSET_4X5, "sha256": "a", "width": 4252, "height": 5315, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        FILE_9X16: {"filename": FILE_9X16, "asset_id": ASSET_9X16, "sha256": "b", "width": 1080, "height": 1920, "format": STORY_REEL, "folder": "DESIGN_REFERENCE"},
        FILE_1X1: {"filename": FILE_1X1, "asset_id": ASSET_1X1, "sha256": "c", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        FILE_1X1_VARIANT: {"filename": FILE_1X1_VARIANT, "asset_id": "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279", "sha256": "d", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
    }


def test_command_routes_family_wide_copy_only() -> None:
    classified = classify_production_intent(PHASE_12_6_COMMAND)
    assert classified["intent"] == FAMILY_WIDE_REVISION
    assert classified["family_wide_territory"] == COPY_EDIT_ONLY
    assert REVISION_TYPE == "COPY_ONLY"
    assert OLD_COPY == "Son Daireler!"
    assert NEW_COPY == "Son Fırsatlar!"
    family = apply_human_approval(selected_family_record(_catalog()))
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [family]
    wide = route_family_wide_revision(
        classified=classified,
        library=library,
        family_id=FAMILY_ID,
        target_phrase=OLD_COPY,
    )
    assert [item["format"] for item in wide["targets"]] == [FEED_PORTRAIT, STORY_REEL, SQUARE]
    skipped = {item["format"]: item for item in wide["skipped"]}
    assert skipped[LANDSCAPE]["reason"] == SKIP_FORMAT_MASTER_MISSING
    assert FEED_PORTRAIT not in skipped
    assert wide["never_invent_missing_semantic"] is True


def test_empty_canvas_does_not_invent_badge() -> None:
    parent = Image.new("RGB", (400, 500), (40, 47, 56))
    child, meta = apply_feed_copy_revision(parent)
    assert child is None
    assert meta["status"] == "SKIPPED_TARGET_NOT_PRESENT"


def test_children_are_draft_and_do_not_generate() -> None:
    import investhome_api.services.creative_director.phase12_6_lock as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" in src
    assert "provider_generation_id=None" in src
    assert '"approval_status": "DRAFT"' in src
    assert "generate_gpt_image" not in src
    live = inspect.getsource(workflow.generate_phase12_6_family_wide_copy_revision).lower()
    assert "openai" not in live
    assert "generate_ideogram" not in live
    assert STATUS_FAIL == "FAMILY_WIDE_COPY_REVISION_FAIL"
    assert STATUS_PENDING == "FAMILY_WIDE_COPY_REVISION_PENDING_HUMAN_REVIEW"
    assert WORKFLOW_ID_12_6 == "phase12_6_family_wide_copy_revision_proof"
    assert CHILD_4X5_ID != CHILD_9X16_ID != CHILD_1X1_ID
    assert CHILD_9X16_ID != PRICE_CHILD_9X16_ID
    assert CHILD_1X1_ID != PRICE_CHILD_1X1_ID
    assert ASSET_4X5 in ORIGINAL_PARENTS
    assert PRICE_CHILD_9X16_ASSET in PRICE_CHILDREN
    assert PRICE_CHILD_1X1_ASSET in PRICE_CHILDREN
    assert MASTER_4X5_ID != MASTER_9X16_ID != MASTER_1X1_ID
    assert FAMILY_ID != ORNEK_FAMILY_ID
    assert generate_phase12_6_family_wide_copy_revision


def test_copy_engine_does_not_call_image_models() -> None:
    import investhome_api.services.creative_director.phase12_6_copy_revise as engine

    full = inspect.getsource(engine)
    assert "openai" not in full.lower()
    assert "generate_gpt_image" not in full
    assert "generate_ideogram" not in full.lower()
    assert apply_story_copy_revision
    assert apply_square_copy_revision
    assert ImageDraw
