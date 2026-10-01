"""Phase 9.1-R2 — approve and lock Premium Campaign 03. No new pixels. No Stage 2."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import PARENT_MASTER_03_ASSET
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import (
    APPROVED_ASSET_03,
    CREATIVE_CONCEPT,
    FORBIDDEN_ASSETS,
    NEXT_PHASE,
    WORKFLOW_ID_91_R2,
    generate_phase9_1_r2_approve_lock_premium_master_03,
    lock_premium_campaign_03,
)
from investhome_api.services.creative_director.project_creative_master_library import add_master, bootstrap_temple_library, empty_master


def test_locks() -> None:
    assert APPROVED_ASSET_03 == "7ccf1c4b-26b8-4356-a774-a60e61d5687a"
    assert APPROVED_ASSET_03 != PARENT_MASTER_03_ASSET
    assert APPROVED_ASSET_03 != APPROVED_ASSET_ID
    assert APPROVED_ASSET_03 != APPROVED_ASSET_02
    assert PARENT_MASTER_03_ASSET in FORBIDDEN_ASSETS
    assert MASTER_NAME_03 == "The Temple — Premium Campaign 03"
    assert TEMPLE_PREMIUM_MASTER_03_ID != APPROVED_MASTER_ID
    assert TEMPLE_PREMIUM_MASTER_03_ID != TEMPLE_PREMIUM_MASTER_02_ID
    assert CREATIVE_CONCEPT == "LOOKING_CHAMBER"
    assert WORKFLOW_ID_91_R2 == "phase9_1_r2_premium_master_03_human_approval"
    assert NEXT_PHASE == "STAGE 2 — NATURAL-LANGUAGE REVISION"
    assert generate_phase9_1_r2_approve_lock_premium_master_03


def test_lock_uses_r1_and_keeps_history() -> None:
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
        approval_status="DRAFT",
        visual_asset=APPROVED_ASSET_03,
        master_id=TEMPLE_PREMIUM_MASTER_03_ID,
    )
    master_03["router_eligible"] = False
    master_03["version"] = 2
    master_03["visual_history"] = [
        {"asset_id": PARENT_MASTER_03_ASSET, "human_review": "REJECTED", "phase": "9.1"},
    ]
    add_master(library, master_03)
    locked = lock_premium_campaign_03(library, asset_id=APPROVED_ASSET_03)
    assert locked["approval_status"] == "HUMAN_APPROVED"
    assert locked["master_state"] == "LOCKED_MASTER"
    assert locked["router_eligible"] is True
    assert locked["visual_asset"] == APPROVED_ASSET_03
    assert locked["version"] == 2
    assert locked["creative_concept"] == "LOOKING_CHAMBER"
    hist = {item["asset_id"] for item in locked["visual_history"]}
    assert PARENT_MASTER_03_ASSET in hist
    assert APPROVED_ASSET_03 not in hist
    assert library["human_approved_premium_count"] == 3
    assert library["creative_family_count"] == 3
    assert library["premium_creative_master_library"] == "COMPLETE"
    assert library["stage_1"] == "COMPLETE"
    assert library["stage_2_executed"] is False
    assert library["next_production_phase"] == NEXT_PHASE
    m01 = next(item for item in library["masters"] if item["master_id"] == APPROVED_MASTER_ID)
    m02 = next(item for item in library["masters"] if item["master_id"] == TEMPLE_PREMIUM_MASTER_02_ID)
    assert m01["visual_asset"] == APPROVED_ASSET_ID
    assert m01["approval_status"] == "HUMAN_APPROVED"
    assert m02["visual_asset"] == APPROVED_ASSET_02
    assert m02["approval_status"] == "HUMAN_APPROVED"


def test_refuses_rejected_original() -> None:
    library = bootstrap_temple_library()
    master_03 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_03,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=PARENT_MASTER_03_ASSET,
        master_id=TEMPLE_PREMIUM_MASTER_03_ID,
    )
    master_03["visual_history"] = []
    add_master(library, master_03)
    try:
        lock_premium_campaign_03(library, asset_id=PARENT_MASTER_03_ASSET)
        raise AssertionError("rejected original Master 03 must not lock")
    except RuntimeError:
        pass


def test_no_new_render_or_stage2() -> None:
    import investhome_api.services.creative_director.phase9_1_r2_approve_lock as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "compose_master_03" not in src
    assert "render_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "empty_master(" not in src
    assert "visual_regenerated" in src
    assert "LOCKED_MASTER" in src
    assert "stage_2_executed" in src
    assert "STAGE 2" in src
