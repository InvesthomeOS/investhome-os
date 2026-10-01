"""Phase 8.1 — one Temple Premium Master draft. No promotion. No A/B/C."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase7_2_photo_object import photo_percentage
from investhome_api.services.creative_director.phase7_4_direct_transfer import REFERENCE_ID
from investhome_api.services.creative_director.phase8_1_compose import MASTER_LAYOUT, locked_layout, master_field_html
from investhome_api.services.creative_director.phase8_1_first_premium_master import (
    MASTER_NAME,
    TEMPLE_PREMIUM_MASTER_01_ID,
    WORKFLOW_ID_81,
    generate_phase8_1_first_project_premium_master,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    bootstrap_temple_library,
    empty_master,
)


def test_locks() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert REFERENCE_ID == "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert WORKFLOW_ID_81 == "phase8_1_first_project_premium_master"
    assert MASTER_NAME == "The Temple — Premium Campaign 01"
    assert generate_phase8_1_first_project_premium_master
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert rev["executed"] is False


def test_one_curated_layout_and_photo_mass() -> None:
    layout = locked_layout()
    mass = photo_percentage(layout["photo_box"])
    assert 0.35 <= mass <= 0.70
    assert layout["photo_shape"] == "rect"
    assert MASTER_LAYOUT["photo_role"] == "lower_left_architectural_object"
    html = master_field_html("")
    assert "ALIRKEN" in html and "KAZAN" in html
    assert "%35" in html and "LANSMAN AVANTAJI" in html
    assert "675.000" in html and "PROJEYİ KEŞFET" in html
    assert "THE TEMPLE" not in html
    assert "investhome" not in html.lower()
    assert "ORNEK" not in html


def test_draft_not_router_eligible() -> None:
    library = bootstrap_temple_library()
    draft = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_01_ID,
    )
    draft["router_eligible"] = False
    add_master(library, draft)
    result = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert result["route"] == ROUTE_QUICK
    assert result["selected_master_id"] != TEMPLE_PREMIUM_MASTER_01_ID
    assert draft["approval_status"] == "DRAFT"
    assert library["human_approved_premium_count"] == 0


def test_no_experimental_engine_or_promotion() -> None:
    import investhome_api.services.creative_director.phase8_1_compose as compose
    import investhome_api.services.creative_director.phase8_1_first_premium_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "compose_relational_v4(" not in src
    assert "generate_around_photo" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "CANDIDATE_IDS" not in src
    assert "phase7_5" not in src
    assert "A-R1" not in src
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "PREMIUM_MASTER_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert "diagnostics_only" in inspect.getsource(workflow)
