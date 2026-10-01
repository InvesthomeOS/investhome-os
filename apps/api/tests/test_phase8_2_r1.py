"""Phase 8.2-R1 — typographic polish only. No redesign. No promotion."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase8_2_human_selected_master import TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID
from investhome_api.services.creative_director.phase8_2_r1_compose import (
    DAY003_ASSET_ID,
    LOCKED_PLAN,
    PARENT_ASSET_ID_82,
    PARENT_MASTER_ID_82,
    r1_html,
    r1_plan,
)
from investhome_api.services.creative_director.phase8_2_r1_polish import (
    MASTER_NAME_R1,
    TEMPLE_PREMIUM_MASTER_01_R1_ID,
    WORKFLOW_ID_82_R1,
    generate_phase8_2_r1_premium_master_polish,
)
from investhome_api.services.creative_director.project_creative_master_library import add_master, bootstrap_temple_library, empty_master


def test_locks() -> None:
    assert PARENT_MASTER_ID_82 == TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID
    assert PARENT_MASTER_ID_82 == "9571efdf-7c41-5828-8d4d-cf63176a89d6"
    assert PARENT_ASSET_ID_82 == "f5d779ff-6074-4f7b-8b91-692427a5b1f8"
    assert DAY003_ASSET_ID == "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert TEMPLE_PREMIUM_MASTER_01_R1_ID != PARENT_MASTER_ID_82
    assert MASTER_NAME_R1 == "The Temple — Premium Campaign 01 — R1"
    assert WORKFLOW_ID_82_R1 == "phase8_2_r1_premium_master_final_polish"
    assert generate_phase8_2_r1_premium_master_polish
    assert LOCKED_PLAN["HEADLINE_TERRITORY"] == r1_plan()["HEADLINE_TERRITORY"]
    assert LOCKED_PLAN["BRAND_TERRITORY"] == r1_plan()["BRAND_TERRITORY"]


def test_r1_html_hierarchy_not_redesign() -> None:
    html = r1_html(photo_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="", plan=r1_plan())
    assert "ALIRKEN" in html and "KAZAN" in html
    assert "%35" in html and "LANSMAN AVANTAJI" in html
    assert "675.000 USD" in html
    assert "2+1" in html and "DAİRE" in html
    assert "PROJEYİ KEŞFET" in html
    assert APPROVED_BOTTOM_COPY in html
    assert "WASHINGTON D.C." in html
    assert "letter-spacing:.14em" in html
    assert "font-size:42px" in html
    assert "font-size:30px" in html
    assert "THE TEMPLE" not in html
    assert "investhome" not in html.lower()
    assert "border-radius:999" not in html
    assert "pill" not in html.lower()


def test_parent_not_overwritten_and_not_router_eligible() -> None:
    library = bootstrap_temple_library()
    parent = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple — Premium Campaign 01",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=PARENT_ASSET_ID_82,
        master_id=PARENT_MASTER_ID_82,
    )
    parent["router_eligible"] = False
    add_master(library, parent)
    draft = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_R1,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_01_R1_ID,
    )
    draft["router_eligible"] = False
    add_master(library, draft)
    result = route_creative(user_text="Temple için reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert result["route"] == ROUTE_QUICK
    kept = next(item for item in library["masters"] if item["master_id"] == PARENT_MASTER_ID_82)
    assert kept["visual_asset"] == PARENT_ASSET_ID_82
    assert library["human_approved_premium_count"] == 0


def test_no_redesign_engine() -> None:
    import investhome_api.services.creative_director.phase8_2_r1_compose as compose
    import investhome_api.services.creative_director.phase8_2_r1_polish as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "select_temple_photo" not in src
    assert "load_catalog" not in src
    assert "generate_around_photo" not in src
    assert "CANDIDATE_IDS" not in src
    assert "PREMIUM_MASTER_FINAL_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert "overlay_polish" in inspect.getsource(compose)
    assert "promoted_to_master" in inspect.getsource(workflow)
