"""Phase 8.2 — one Temple Premium Master from ORNEK_00001. No promotion. No A/B/C."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase8_1_first_premium_master import TEMPLE_PREMIUM_MASTER_01_ID
from investhome_api.services.creative_director.phase8_2_compose import SOURCE_FILENAME, SOURCE_ID, composition_plan_v1, master_html
from investhome_api.services.creative_director.phase8_2_human_selected_master import (
    MASTER_NAME,
    TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID,
    WORKFLOW_ID_82,
    generate_phase8_2_human_selected_premium_master,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    archive_human_rejected_master,
    bootstrap_temple_library,
    empty_master,
)


def test_locks() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert SOURCE_FILENAME == "ORNEK_00001.jpg"
    assert SOURCE_ID == "3a3c4832-a8c1-5a43-a518-d895ee78fbe1"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert WORKFLOW_ID_82 == "phase8_2_human_selected_premium_master"
    assert MASTER_NAME == "The Temple — Premium Campaign 01"
    assert TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID != TEMPLE_PREMIUM_MASTER_01_ID
    assert generate_phase8_2_human_selected_premium_master
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert rev["executed"] is False


def test_composition_plan_from_occupancy_not_sidebar() -> None:
    occupancy = {
        "sky_area": 0.26,
        "architecture_centroid_x": 0.60,
        "coverage": {"hard_protected": 0.48, "sky_left": 0.18, "sky_right": 0.08},
        "pockets": {
            "left": {"x": 0.05, "y": 0.03, "w": 0.46, "h": 0.34, "area": 0.14},
            "right": {"x": 0.58, "y": 0.03, "w": 0.30, "h": 0.18, "area": 0.05},
        },
        "regions": {"hard_protected": {"x": 0.32, "y": 0.24, "w": 0.58, "h": 0.70}},
    }
    plan = composition_plan_v1(occupancy)
    assert plan["schema"] == "CompositionPlanV1"
    assert plan["origin"] == "left"
    assert plan["source"] == SOURCE_FILENAME
    for key in (
        "PHOTO_FOCAL_AREA",
        "NATURAL_NEGATIVE_SPACE",
        "HEADLINE_TERRITORY",
        "LOCATION_TERRITORY",
        "OFFER_TERRITORY",
        "SECONDARY_COMMERCIAL_TERRITORY",
        "BRAND_TERRITORY",
        "CTA_TERRITORY",
        "EDITORIAL_CLOSURE_TERRITORY",
    ):
        box = plan[key]
        assert box["w"] > 0 and box["h"] > 0
    assert plan["HEADLINE_TERRITORY"]["h"] > plan["LOCATION_TERRITORY"]["h"]
    assert plan["EDITORIAL_CLOSURE_TERRITORY"]["y"] + plan["EDITORIAL_CLOSURE_TERRITORY"]["h"] <= 0.52
    assert plan["quality_gate"] == "PASS"


def test_master_html_full_canvas_temple_copy() -> None:
    occupancy = {
        "sky_area": 0.26,
        "coverage": {"hard_protected": 0.48, "sky_left": 0.18, "sky_right": 0.08},
        "pockets": {"left": {"x": 0.06, "y": 0.04, "w": 0.48, "h": 0.33, "area": 0.14}},
        "regions": {},
    }
    html = master_html(photo_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="", plan=composition_plan_v1(occupancy))
    assert 'data-semantic="project_photo"' in html
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
    assert "pill" not in html.lower()


def test_draft_not_router_eligible_and_81_stays_archived() -> None:
    library = bootstrap_temple_library()
    archived = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_01_ID,
    )
    add_master(library, archived)
    archive_human_rejected_master(library, master_id=TEMPLE_PREMIUM_MASTER_01_ID, reason="human rejected")
    draft = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID,
    )
    draft["router_eligible"] = False
    draft["human_selected_source"] = SOURCE_FILENAME
    add_master(library, draft)
    result = route_creative(user_text="Temple için reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    assert result["route"] == ROUTE_QUICK
    assert result["selected_master_id"] not in {TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID, TEMPLE_PREMIUM_MASTER_01_ID}
    assert draft["approval_status"] == "DRAFT"
    archived_row = next(item for item in library["masters"] if item["master_id"] == TEMPLE_PREMIUM_MASTER_01_ID)
    assert archived_row["approval_status"] == "ARCHIVED"
    assert library["human_approved_premium_count"] == 0


def test_no_retry_engine_or_promotion() -> None:
    import investhome_api.services.creative_director.phase8_2_compose as compose
    import investhome_api.services.creative_director.phase8_2_human_selected_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "compose_relational_v4(" not in src
    assert "generate_around_photo" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "CANDIDATE_IDS" not in src
    assert "phase7_5" not in src
    assert "MASTER_LAYOUT" not in src
    assert "A-R1" not in src
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "PREMIUM_MASTER_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert "ORNEK_00001" in inspect.getsource(workflow)
    assert "recalculate" in inspect.getsource(workflow).lower()
