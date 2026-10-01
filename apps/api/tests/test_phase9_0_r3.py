"""Phase 9.0-R3 — approve and lock Premium Campaign 02. No new pixels."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r1_compose import PARENT_MASTER_02_ASSET
from investhome_api.services.creative_director.phase9_0_r2_compose import PARENT_R1_ASSET
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import (
    APPROVED_ASSET_02,
    CREATIVE_CONCEPT,
    FORBIDDEN_ASSETS,
    WORKFLOW_ID_90_R3,
    generate_phase9_0_r3_approve_lock_premium_master_02,
    lock_premium_campaign_02,
)
from investhome_api.services.creative_director.project_creative_master_library import add_master, bootstrap_temple_library, empty_master


def test_locks() -> None:
    assert APPROVED_ASSET_02 == "48819baf-c2a9-43e0-9c27-a55deb15efdd"
    assert APPROVED_ASSET_02 != PARENT_R1_ASSET
    assert APPROVED_ASSET_02 != PARENT_MASTER_02_ASSET
    assert APPROVED_ASSET_02 != APPROVED_ASSET_ID
    assert PARENT_R1_ASSET in FORBIDDEN_ASSETS
    assert PARENT_MASTER_02_ASSET in FORBIDDEN_ASSETS
    assert MASTER_NAME_02 == "The Temple — Premium Campaign 02"
    assert TEMPLE_PREMIUM_MASTER_02_ID != APPROVED_MASTER_ID
    assert CREATIVE_CONCEPT == "THE TEMPLE RISES THROUGH THE EDITORIAL PAGE"
    assert WORKFLOW_ID_90_R3 == "phase9_0_r3_premium_master_02_human_approval"
    assert generate_phase9_0_r3_approve_lock_premium_master_02


def test_lock_uses_r2_and_keeps_history() -> None:
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
        approval_status="DRAFT",
        visual_asset=APPROVED_ASSET_02,
        master_id=TEMPLE_PREMIUM_MASTER_02_ID,
    )
    master_02["router_eligible"] = False
    master_02["version"] = 3
    master_02["visual_history"] = [
        {"asset_id": PARENT_MASTER_02_ASSET, "human_review": "REJECTED", "phase": "9.0"},
        {"asset_id": PARENT_R1_ASSET, "human_review": "REJECTED", "phase": "9.0-R1"},
    ]
    add_master(library, master_02)
    locked = lock_premium_campaign_02(library, asset_id=APPROVED_ASSET_02)
    assert locked["approval_status"] == "HUMAN_APPROVED"
    assert locked["master_state"] == "LOCKED_MASTER"
    assert locked["router_eligible"] is True
    assert locked["visual_asset"] == APPROVED_ASSET_02
    assert locked["version"] == 3
    hist = {item["asset_id"] for item in locked["visual_history"]}
    assert PARENT_MASTER_02_ASSET in hist
    assert PARENT_R1_ASSET in hist
    assert APPROVED_ASSET_02 not in hist
    assert library["human_approved_premium_count"] == 2
    m01 = next(item for item in library["masters"] if item["master_id"] == APPROVED_MASTER_ID)
    assert m01["visual_asset"] == APPROVED_ASSET_ID
    assert m01["approval_status"] == "HUMAN_APPROVED"


def test_refuses_r1_and_original() -> None:
    library = bootstrap_temple_library()
    master_02 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_02,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=PARENT_R1_ASSET,
        master_id=TEMPLE_PREMIUM_MASTER_02_ID,
    )
    master_02["visual_history"] = [{"asset_id": PARENT_MASTER_02_ASSET}]
    add_master(library, master_02)
    try:
        lock_premium_campaign_02(library, asset_id=PARENT_R1_ASSET)
        raise AssertionError("R1 must not lock")
    except RuntimeError:
        pass
    try:
        lock_premium_campaign_02(library, asset_id=PARENT_MASTER_02_ASSET)
        raise AssertionError("original Master 02 must not lock")
    except RuntimeError:
        pass


def test_no_new_render_or_format() -> None:
    import investhome_api.services.creative_director.phase9_0_r3_approve_lock as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "compose_master_02" not in src
    assert "render_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "empty_master(" not in src
    assert "visual_regenerated" in src
    assert "LOCKED_MASTER" in src
