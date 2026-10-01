"""Phase 10.3 — Stage 2 lock. No new pixels. No Stage 3. Masters unchanged."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import CHILD_REVISION_ID as PRICE_REJECTED_REVISION_ID
from investhome_api.services.creative_director.phase10_0_r1_master import CHILD_REVISION_R1_ID as PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase10_0_r1_master import REJECTED_CHILD_ASSET_ID
from investhome_api.services.creative_director.phase10_1_master import CHILD_REVISION_ID as COPY_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_2_master import CHILD_REVISION_ID as PHOTO_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_2_master import COPY_CHILD_ASSET_ID, PRICE_R1_ASSET_ID
from investhome_api.services.creative_director.phase10_3_finalize import (
    PHOTO_CHILD_ASSET_ID,
    WORKFLOW_ID_10_3,
    generate_phase10_3_stage_2_finalization,
    lock_stage_2_revision_engine,
)
from investhome_api.services.creative_director.phase10_3_revision_doctrine import (
    NEXT_PHASE,
    REVISION_DOCTRINE,
    STAGE_2_STATUS,
    USER_NEVER_SPECIFIES,
    revision_doctrine,
)
from investhome_api.services.creative_director.project_creative_master_library import add_master, bootstrap_temple_library, empty_master


def _library_with_children() -> dict:
    library = bootstrap_temple_library()
    master_01 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple — Premium Campaign 01",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=APPROVED_ASSET_ID,
        master_id=APPROVED_MASTER_ID,
    )
    master_01["master_state"] = "LOCKED_MASTER"
    master_01["router_eligible"] = True
    add_master(library, master_01)
    master_02 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_02,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=APPROVED_ASSET_02,
        master_id=TEMPLE_PREMIUM_MASTER_02_ID,
    )
    master_02["master_state"] = "LOCKED_MASTER"
    master_02["router_eligible"] = True
    add_master(library, master_02)
    master_03 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_03,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=APPROVED_ASSET_03,
        master_id=TEMPLE_PREMIUM_MASTER_03_ID,
    )
    master_03["master_state"] = "LOCKED_MASTER"
    master_03["router_eligible"] = True
    master_03["version"] = 2
    master_03["creative_concept"] = "LOOKING_CHAMBER"
    master_03["canonical_format"] = "4:5"
    master_03["derived_revisions"] = [
        {
            "revision_id": PRICE_REJECTED_REVISION_ID,
            "visual_asset": REJECTED_CHILD_ASSET_ID,
            "approval_status": "DRAFT",
            "human_review": "REJECTED",
            "router_eligible": False,
        },
        {
            "revision_id": PRICE_R1_REVISION_ID,
            "visual_asset": PRICE_R1_ASSET_ID,
            "approval_status": "DRAFT",
            "router_eligible": False,
        },
        {
            "revision_id": COPY_CHILD_REVISION_ID,
            "visual_asset": COPY_CHILD_ASSET_ID,
            "approval_status": "DRAFT",
            "router_eligible": False,
        },
        {
            "revision_id": PHOTO_CHILD_REVISION_ID,
            "visual_asset": PHOTO_CHILD_ASSET_ID,
            "approval_status": "DRAFT",
            "router_eligible": False,
        },
    ]
    add_master(library, master_03)
    library["stage_1"] = "COMPLETE"
    library["stage_2_executed"] = False
    library["premium_creative_master_library"] = "COMPLETE"
    return library


def test_doctrine_is_natural_language_first() -> None:
    doctrine = revision_doctrine()
    assert doctrine["doctrine"] == REVISION_DOCTRINE == "NATURAL_LANGUAGE_FIRST"
    assert doctrine["status"] == STAGE_2_STATUS == "COMPLETE"
    assert doctrine["stage_3_executed"] is False
    assert doctrine["format_work_executed"] is False
    assert doctrine["next_phase"] == NEXT_PHASE == "STAGE 3 — CREATIVE QUALITY ENGINE"
    assert "layer IDs" in USER_NEVER_SPECIFIES
    assert doctrine["capabilities"]["PRICE_EDIT_ONLY"]["status"] == "HUMAN_APPROVED"
    assert doctrine["capabilities"]["COPY_EDIT_ONLY"]["status"] == "HUMAN_APPROVED"
    assert doctrine["capabilities"]["VISUAL_REPLACE_ONLY"]["status"] == "HUMAN_APPROVED"
    assert doctrine["capabilities"]["VISUAL_REPLACE_ONLY"]["photo_adapts_to_design"] is True


def test_lock_approves_children_without_touching_masters() -> None:
    library = _library_with_children()
    m03_before = next(item for item in library["masters"] if item["master_id"] == TEMPLE_PREMIUM_MASTER_03_ID)
    visual_before = m03_before["visual_asset"]
    locked = lock_stage_2_revision_engine(library)
    master = locked["master_03"]
    assert master["visual_asset"] == visual_before == APPROVED_ASSET_03
    assert master["approval_status"] == "HUMAN_APPROVED"
    assert master["master_state"] == "LOCKED_MASTER"
    kids = {item["revision_id"]: item for item in master["derived_revisions"]}
    assert kids[PHOTO_CHILD_REVISION_ID]["approval_status"] == "HUMAN_APPROVED"
    assert kids[PHOTO_CHILD_REVISION_ID]["visual_asset"] == PHOTO_CHILD_ASSET_ID
    assert kids[PHOTO_CHILD_REVISION_ID]["router_eligible"] is False
    assert kids[PRICE_R1_REVISION_ID]["approval_status"] == "HUMAN_APPROVED"
    assert kids[COPY_CHILD_REVISION_ID]["approval_status"] == "HUMAN_APPROVED"
    assert kids[PRICE_REJECTED_REVISION_ID]["approval_status"] != "HUMAN_APPROVED"
    assert kids[PRICE_REJECTED_REVISION_ID]["human_review"] == "REJECTED"
    assert library["stage_2"] == "COMPLETE"
    assert library["stage_2_natural_language_revision"] == "COMPLETE"
    assert library["stage_3_executed"] is False
    assert library["next_production_phase"] == NEXT_PHASE
    m01 = next(item for item in library["masters"] if item["master_id"] == APPROVED_MASTER_ID)
    m02 = next(item for item in library["masters"] if item["master_id"] == TEMPLE_PREMIUM_MASTER_02_ID)
    assert m01["visual_asset"] == APPROVED_ASSET_ID
    assert m02["visual_asset"] == APPROVED_ASSET_02
    assert library["human_approved_premium_count"] == 3


def test_no_new_render_or_stage3() -> None:
    import investhome_api.services.creative_director.phase10_3_finalize as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "apply_exterior_replacement" not in src
    assert "apply_clean_headline_revision" not in src
    assert "apply_clean_price_revision" not in src
    assert "attach_format_child" not in src
    assert "empty_master(" not in src
    assert "stage_3_executed" in src
    assert "NEXT_PHASE" in src
    assert generate_phase10_3_stage_2_finalization
    assert WORKFLOW_ID_10_3 == "phase10_3_stage_2_natural_language_revision_lock"
    assert PHOTO_CHILD_ASSET_ID == "004a0ad8-13f9-4977-b5b6-19f859eca613"
