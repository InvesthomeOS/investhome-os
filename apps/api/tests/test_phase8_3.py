"""Phase 8.3 — approve and lock first Temple Premium Master. No new pixels."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import (
    PRICE_EDIT_ONLY,
    ROUTE_PREMIUM_MASTER,
    ROUTE_QUICK,
    ROUTE_REVISION,
    VISUAL_REPLACE_ONLY,
    classify_production_intent,
    route_creative,
)
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase8_1_first_premium_master import TEMPLE_PREMIUM_MASTER_01_ID
from investhome_api.services.creative_director.phase8_2_r1_compose import DAY003_ASSET_ID, PARENT_MASTER_ID_82
from investhome_api.services.creative_director.phase8_3_approve_lock import (
    APPROVED_ASSET_ID,
    APPROVED_MASTER_ID,
    APPROVED_MASTER_NAME,
    WORKFLOW_ID_83,
    generate_phase8_3_approve_lock_first_premium_master,
    smoke_routing,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    approve_and_lock_master,
    archive_human_rejected_master,
    archive_superseded_draft,
    bootstrap_temple_library,
    empty_master,
    synthetic_approved_temple_library,
)


def test_locks() -> None:
    assert APPROVED_MASTER_ID == "30b8d880-61d3-556a-b6c3-329e3632ed69"
    assert APPROVED_ASSET_ID == "a6c87a3c-835e-4e8b-9179-b247720fe61b"
    assert APPROVED_MASTER_NAME == "The Temple — Premium Campaign 01"
    assert DAY003_ASSET_ID == "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_83 == "phase8_3_approve_lock_first_premium_master"
    assert generate_phase8_3_approve_lock_first_premium_master
    assert APPROVED_MASTER_ID != TEMPLE_PREMIUM_MASTER_01_ID
    assert APPROVED_MASTER_ID != PARENT_MASTER_ID_82


def test_approve_lock_and_smoke_routing() -> None:
    library = bootstrap_temple_library()
    rejected = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=APPROVED_MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_01_ID,
    )
    add_master(library, rejected)
    archive_human_rejected_master(library, master_id=TEMPLE_PREMIUM_MASTER_01_ID, reason="human rejected")
    parent = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=APPROVED_MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset="f5d779ff-6074-4f7b-8b91-692427a5b1f8",
        master_id=PARENT_MASTER_ID_82,
    )
    add_master(library, parent)
    r1 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple — Premium Campaign 01 — R1",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=APPROVED_ASSET_ID,
        master_id=APPROVED_MASTER_ID,
    )
    r1["router_eligible"] = False
    add_master(library, r1)
    locked = approve_and_lock_master(
        library,
        master_id=APPROVED_MASTER_ID,
        asset_id=APPROVED_ASSET_ID,
        master_name=APPROVED_MASTER_NAME,
        lock={"photo_asset_id": DAY003_ASSET_ID},
    )
    archive_superseded_draft(library, master_id=PARENT_MASTER_ID_82, superseded_by=APPROVED_MASTER_ID)
    assert locked["approval_status"] == "HUMAN_APPROVED"
    assert locked["master_state"] == "LOCKED_MASTER"
    assert locked["router_eligible"] is True
    assert locked["canonical_format"] == "4:5"
    assert locked["visual_asset"] == APPROVED_ASSET_ID
    assert locked["revision_contract"]["PRICE_EDIT_ONLY"]["status"] == "ACTIVE"
    assert locked["revision_contract"]["PRICE_EDIT_ONLY"]["creates_child_revision"] is True
    assert locked["revision_contract"]["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert library["human_approved_premium_count"] == 1
    parent_row = next(item for item in library["masters"] if item["master_id"] == PARENT_MASTER_ID_82)
    assert parent_row["approval_status"] == "ARCHIVED"
    rejected_row = next(item for item in library["masters"] if item["master_id"] == TEMPLE_PREMIUM_MASTER_01_ID)
    assert rejected_row["approval_status"] == "ARCHIVED"
    smoke = smoke_routing(library)
    assert smoke["pass"] is True


def test_live_smoke_phrases() -> None:
    library = bootstrap_temple_library()
    r1 = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=APPROVED_MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=APPROVED_ASSET_ID,
        master_id=APPROVED_MASTER_ID,
    )
    r1["router_eligible"] = True
    add_master(library, r1)
    premium = route_creative(user_text="Temple için premium reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert premium["route"] == ROUTE_PREMIUM_MASTER
    assert premium["selected_master_id"] == APPROVED_MASTER_ID
    lansman = route_creative(user_text="Temple için %35 lansman avantajı reklamı hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert lansman["route"] == ROUTE_PREMIUM_MASTER
    price = route_creative(user_text="Fiyatı değiştir.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert price["route"] == ROUTE_REVISION
    assert price["revision_intent"] == PRICE_EDIT_ONLY
    assert classify_production_intent("Fiyatı değiştir.")["is_revision"] is True
    visual = route_creative(user_text="Başka dış cephe görselini kullan.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert visual["route"] == ROUTE_REVISION
    assert visual["revision_intent"] == VISUAL_REPLACE_ONLY
    alt = route_creative(user_text="Bambaşka bir tasarım göster.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert alt["route"] == ROUTE_QUICK
    assert alt["selected_master_id"] is None


def test_synthetic_alternative_still_picks_other_approved() -> None:
    library = synthetic_approved_temple_library()
    first = route_creative(
        user_text="Başka bir tasarım göster.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
        current_master_id="synthetic-premium-01",
    )
    assert first["route"] == ROUTE_PREMIUM_MASTER
    assert first["selected_master_id"] == "synthetic-editorial-01"


def test_no_new_render_or_cover_change() -> None:
    import investhome_api.services.creative_director.phase8_3_approve_lock as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "render_html_to_png" not in src
    assert "render_r1_type" not in src
    assert "production_cover_changed" in src
    assert "FIRST_PROJECT_PREMIUM_MASTER_APPROVED" in src
    assert "LOCKED_MASTER" in src
