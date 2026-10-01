"""Phase 9.0 — one Temple Premium Campaign 02 from ORNEK_00012. No promotion. No format work."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_PREMIUM_MASTER, route_creative
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID, APPROVED_MASTER_NAME
from investhome_api.services.creative_director.phase9_0_compose import (
    INK,
    ORNEK_FILENAME,
    SUNSET_ASSET_ID,
    SUNSET_FILENAME,
    html_copy_ok,
    master_html,
)
from investhome_api.services.creative_director.phase9_0_master import (
    MASTER_NAME_02,
    TEMPLE_PREMIUM_MASTER_02_ID,
    WORKFLOW_ID_90,
    generate_phase9_0_premium_master_02,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    bootstrap_temple_library,
    count_approved_premium,
    empty_master,
)


def test_locks() -> None:
    assert ORNEK_FILENAME == "ORNEK_00012.jpg"
    assert SUNSET_FILENAME == "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg"
    assert SUNSET_ASSET_ID == "65f68756-a006-43d4-9c86-2c0ec25ad229"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert APPROVED_MASTER_ID == "30b8d880-61d3-556a-b6c3-329e3632ed69"
    assert APPROVED_ASSET_ID == "a6c87a3c-835e-4e8b-9179-b247720fe61b"
    assert MASTER_NAME_02 == "The Temple — Premium Campaign 02"
    assert TEMPLE_PREMIUM_MASTER_02_ID != APPROVED_MASTER_ID
    assert WORKFLOW_ID_90 == "phase9_0_premium_master_02_creative_first"
    assert INK == "#2A1F16"
    assert generate_phase9_0_premium_master_02


def test_html_is_field_merge_not_panel_or_listing() -> None:
    html = master_html(photo_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert html_copy_ok(html)
    assert 'data-semantic="project_photo"' in html
    assert 'data-semantic="atmospheric_field"' in html
    assert "object-fit:cover" in html
    assert "inset:0" in html
    assert "WASHINGTON D.C." in html
    assert "ALIRKEN" in html and "KAZAN" in html
    assert "%35" in html and "LANSMAN AVANTAJI" in html
    assert "675.000 USD" in html
    assert "2+1" in html and "DAİRE" in html
    assert "PROJEYİ KEŞFET" in html
    assert APPROVED_BOTTOM_COPY in html
    assert "THE TEMPLE" not in html
    assert "investhome" not in html.lower()
    assert "UniLoft" not in html
    assert "border-radius:999" not in html
    assert "#1A2330" not in html
    assert "sidebar" not in html.lower()
    assert "linear-gradient(180deg" in html
    assert html.count('data-semantic="project_logo"') <= 1


def test_draft_does_not_route_and_master_01_stays_approved() -> None:
    library = bootstrap_temple_library()
    locked = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=APPROVED_MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=APPROVED_ASSET_ID,
        master_id=APPROVED_MASTER_ID,
    )
    locked["router_eligible"] = True
    add_master(library, locked)
    draft = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_02,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_02_ID,
    )
    draft["router_eligible"] = False
    draft["human_selected_source"] = ORNEK_FILENAME
    add_master(library, draft)
    result = route_creative(user_text="Temple için premium reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert result["route"] == ROUTE_PREMIUM_MASTER
    assert result["selected_master_id"] == APPROVED_MASTER_ID
    assert result["selected_master_id"] != TEMPLE_PREMIUM_MASTER_02_ID
    assert draft["approval_status"] == "DRAFT"
    assert count_approved_premium(library) == 1
    master_01 = next(item for item in library["masters"] if item["master_id"] == APPROVED_MASTER_ID)
    assert master_01["approval_status"] == "HUMAN_APPROVED"
    assert str(master_01["visual_asset"]) == APPROVED_ASSET_ID


def test_no_retry_format_or_promotion() -> None:
    import investhome_api.services.creative_director.phase9_0_compose as compose
    import investhome_api.services.creative_director.phase9_0_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "compose_relational_v4(" not in src
    assert "generate_around_photo" not in src
    assert "CANDIDATE_IDS" not in src
    assert "phase7_5" not in src
    assert "approve_and_lock_master" not in src
    assert "attach_format_child" not in src
    assert "9:16" not in src
    assert "16:9" not in src
    assert "Day_003" not in src or "rejected_day_003" in src
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "PREMIUM_MASTER_02_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert "ORNEK_00012" in inspect.getsource(workflow)
    assert "Sunset_001" in src or "SUNSET" in src
