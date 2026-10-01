"""Phase 8.4 — 1:1 intelligent format adaptation. Format child, not a new Master."""

from __future__ import annotations

import inspect

from PIL import Image

from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase8_2_r1_compose import DAY003_ASSET_ID
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID, APPROVED_MASTER_NAME
from investhome_api.services.creative_director.phase8_4_adapt import FORMAT_CHILD_1X1_ID, WORKFLOW_ID_84, generate_phase8_4_format_adaptation_1x1
from investhome_api.services.creative_director.phase8_4_format_1x1 import (
    CANVAS_1X1,
    SCALES_1X1,
    SEMANTIC_CONTENT,
    identity_validation,
    plan_1x1,
    square_html,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    approve_and_lock_master,
    attach_format_child,
    bootstrap_temple_library,
    count_approved_premium,
    empty_master,
)


def test_locks() -> None:
    assert APPROVED_MASTER_ID == "30b8d880-61d3-556a-b6c3-329e3632ed69"
    assert APPROVED_ASSET_ID == "a6c87a3c-835e-4e8b-9179-b247720fe61b"
    assert DAY003_ASSET_ID == "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert FORMAT_CHILD_1X1_ID != APPROVED_MASTER_ID
    assert len(FORMAT_CHILD_1X1_ID) == 36
    assert CANVAS_1X1 == (1088, 1088)
    assert CANVAS_4X5 == (1088, 1360)
    assert WORKFLOW_ID_84 == "phase8_4_intelligent_format_adaptation_1x1"
    assert generate_phase8_4_format_adaptation_1x1
    assert APPROVED_MASTER_NAME == "The Temple — Premium Campaign 01"


def test_square_html_preserves_campaign() -> None:
    html = square_html(
        photo_uri="data:image/jpeg;base64,xx",
        logo_markup='<svg data-semantic="project_logo"></svg>',
        font_css="",
        plan=plan_1x1(),
    )
    assert "ALIRKEN" in html and "KAZAN" in html
    assert '<p class="line1">ALIRKEN</p>' in html
    assert '<p class="line2">KAZAN</p>' in html
    assert "%35" in html and "LANSMAN AVANTAJI" in html
    assert "675.000 USD" in html
    assert "2+1" in html and "DAİRE" in html
    assert "PROJEYİ KEŞFET" in html
    assert APPROVED_BOTTOM_COPY in html
    assert "WASHINGTON D.C." in html
    assert "THE TEMPLE" not in html
    assert "investhome" not in html.lower()
    assert "border-radius:999" not in html
    assert "pill" not in html.lower()
    assert "1088px" in html
    assert min(SCALES_1X1[k] for k in ("HEADLINE", "OFFER", "PRICE")) >= 0.80
    assert SEMANTIC_CONTENT["headline"] == "ALIRKEN / KAZAN"


def test_format_child_does_not_become_a_master() -> None:
    library = bootstrap_temple_library()
    parent = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=APPROVED_MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=APPROVED_ASSET_ID,
        master_id=APPROVED_MASTER_ID,
    )
    add_master(library, parent)
    locked = approve_and_lock_master(
        library,
        master_id=APPROVED_MASTER_ID,
        asset_id=APPROVED_ASSET_ID,
        master_name=APPROVED_MASTER_NAME,
        lock={"photo_asset_id": DAY003_ASSET_ID},
    )
    child = {
        "schema": "FormatAdaptationV1",
        "child_id": FORMAT_CHILD_1X1_ID,
        "parent_master_id": APPROVED_MASTER_ID,
        "parent_asset_id": APPROVED_ASSET_ID,
        "visual_asset": "11111111-2222-3333-4444-555555555555",
        "source_format": "4:5",
        "target_format": "1:1",
        "is_premium_master": False,
    }
    attach_format_child(library, parent_master_id=APPROVED_MASTER_ID, child=child)
    assert locked["visual_asset"] == APPROVED_ASSET_ID
    assert locked["approval_status"] == "HUMAN_APPROVED"
    assert locked["router_eligible"] is True
    assert count_approved_premium(library) == 1
    assert any(c.get("child_id") == FORMAT_CHILD_1X1_ID for c in locked.get("format_children") or [])
    assert not any(str(item.get("master_id")) == FORMAT_CHILD_1X1_ID for item in library["masters"])


def test_identity_validation_square() -> None:
    html = square_html(
        photo_uri="data:image/jpeg;base64,xx",
        logo_markup='<svg data-semantic="project_logo"></svg>',
        font_css="",
        plan=plan_1x1(),
    )
    square = Image.new("RGB", CANVAS_1X1, (200, 200, 200))
    canonical = Image.new("RGB", CANVAS_4X5, (180, 180, 180))
    identity = identity_validation(html=html, square=square, canonical=canonical, plan=plan_1x1())
    assert identity["ARCHITECTURE_FIDELITY"] == 10
    assert identity["SAME_CAMPAIGN_FAMILY"] == "YES"
    assert identity["INDEPENDENTLY_PUBLISHABLE_1X1"] == "YES"
    assert all(v >= 8 for v in identity["scores"].values())


def test_no_new_master_or_gpt_image_in_compose() -> None:
    import investhome_api.services.creative_director.phase8_4_adapt as workflow
    import investhome_api.services.creative_director.phase8_4_format_1x1 as compose

    src = inspect.getsource(compose)
    adapt = inspect.getsource(workflow)
    assert "load_catalog" not in src
    assert "select_temple_photo" not in src
    assert "load_catalog" not in adapt
    assert "select_temple_photo" not in adapt
    assert "add_master" not in adapt
    assert "FORMAT_ADAPTATION_PENDING_HUMAN_APPROVAL" in adapt
    assert "is_premium_master" in adapt
    assert "persist_gpt_image" in adapt
    assert "provider_call_count" in adapt
    assert "canonical_master_changed" in adapt
