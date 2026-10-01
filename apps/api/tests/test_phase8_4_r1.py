"""Phase 8.4-R1 — 1:1 spatial polish. CTA + editorial only."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase8_4_adapt import FORMAT_CHILD_1X1_ID
from investhome_api.services.creative_director.phase8_4_format_1x1 import PLAN_1X1, plan_1x1
from investhome_api.services.creative_director.phase8_4_r1_compose import (
    PARENT_CHILD_ASSET_84,
    PARENT_CHILD_ID_84,
    R1_CTA,
    R1_EDITORIAL,
    only_cta_editorial_changed,
    parent_plan,
    r1_plan,
)
from investhome_api.services.creative_director.phase8_4_r1_polish import (
    FORMAT_CHILD_1X1_R1_ID,
    WORKFLOW_ID_84_R1,
    generate_phase8_4_r1_format_child_spatial_polish,
)


def test_locks() -> None:
    assert PARENT_CHILD_ID_84 == FORMAT_CHILD_1X1_ID
    assert PARENT_CHILD_ID_84 == "f1ad1f5a-0fe0-5eb5-a49d-f8233a6b6149"
    assert PARENT_CHILD_ASSET_84 == "47f746ba-e445-48de-b185-8b6e71f02725"
    assert FORMAT_CHILD_1X1_R1_ID != PARENT_CHILD_ID_84
    assert FORMAT_CHILD_1X1_R1_ID != APPROVED_MASTER_ID
    assert APPROVED_ASSET_ID == "a6c87a3c-835e-4e8b-9179-b247720fe61b"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_84_R1 == "phase8_4_r1_format_child_spatial_polish"
    assert generate_phase8_4_r1_format_child_spatial_polish


def test_only_cta_and_editorial_move() -> None:
    old = parent_plan()
    new = r1_plan()
    assert only_cta_editorial_changed(old, new)
    assert old["HEADLINE_TERRITORY"] == PLAN_1X1["HEADLINE_TERRITORY"] == new["HEADLINE_TERRITORY"]
    assert old["OFFER_TERRITORY"] == new["OFFER_TERRITORY"]
    assert old["SECONDARY_COMMERCIAL_TERRITORY"] == new["SECONDARY_COMMERCIAL_TERRITORY"]
    assert old["BRAND_TERRITORY"] == new["BRAND_TERRITORY"]
    assert new["CTA_TERRITORY"] == R1_CTA
    assert new["EDITORIAL_CLOSURE_TERRITORY"] == R1_EDITORIAL
    assert new["CTA_TERRITORY"]["y"] < old["CTA_TERRITORY"]["y"]
    assert new["EDITORIAL_CLOSURE_TERRITORY"]["y"] < old["EDITORIAL_CLOSURE_TERRITORY"]["y"]
    assert new["EDITORIAL_CLOSURE_TERRITORY"]["y"] + new["EDITORIAL_CLOSURE_TERRITORY"]["h"] <= 0.545
    assert plan_1x1()["CTA_TERRITORY"]["y"] == 0.505


def test_no_redesign_or_new_master() -> None:
    import investhome_api.services.creative_director.phase8_4_r1_compose as compose
    import investhome_api.services.creative_director.phase8_4_r1_polish as workflow

    src = inspect.getsource(compose)
    adapt = inspect.getsource(workflow)
    assert "add_master" not in adapt
    assert "load_catalog" not in adapt
    assert "select_temple_photo" not in adapt
    assert "spatial_cta_editorial_only" in adapt
    assert "overlay_spatial_polish" in src
    assert "FORMAT_ADAPTATION_FINAL_PENDING_HUMAN_APPROVAL" in adapt
    assert "is_premium_master" in adapt
    assert "persist_gpt_image" in adapt
    assert "provider_call_count" in adapt
    assert "canonical_master_changed" in adapt
