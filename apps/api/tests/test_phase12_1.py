"""Phase 12.1 tests — brand scope lock, no Temple substitution, no Stage 4."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import select_approved_master
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.phase12_1_approve_lock import (
    NEXT_PHASE,
    STATUS,
    apply_brand_approval,
    generate_phase12_1_approve_lock,
)
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    STAGE4_PROOF_SCOPE,
    adapter_contract,
    is_production_premium_master,
    select_production_premium_master,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    approved_masters,
    empty_library,
    empty_master,
)


UNILOFT_PROJECT_ID = "uniloft-project"


def _approved_brand_library() -> dict:
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    master = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="brand",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=SELECTED_ASSET_ID,
        master_id=PRODUCTION_MASTER_ID,
    )
    master["source"] = "INVESTHOME_APPROVED"
    master["canonical_format"] = "4:5"
    apply_brand_approval(master)
    add_master(library, master)
    return library


def test_brand_master_is_not_selectable_as_temple() -> None:
    library = _approved_brand_library()
    master = library["masters"][0]
    assert master["project_id"] is None
    assert master["master_scope"] == "BRAND"
    assert master["brand_id"] == "INVESTHOME"
    assert master["cross_project_reuse"] is False
    assert master["project_asset_substitution"] == "NOT ALLOWED"
    assert master["router_eligible"] is True
    assert is_production_premium_master(master) is True
    assert select_production_premium_master(library, project_id=TEMPLE_PROJECT_ID) is None
    assert select_production_premium_master(library, project_id=UNILOFT_PROJECT_ID) is None
    assert approved_masters(library, project_id=TEMPLE_PROJECT_ID) == []
    assert select_approved_master(library, project_id=TEMPLE_PROJECT_ID, preference="PREMIUM_CAMPAIGN") is None
    brand = select_production_premium_master(library, scope="BRAND", brand_id="INVESTHOME")
    assert brand is not None
    assert brand["master_id"] == PRODUCTION_MASTER_ID
    assert brand["visual_asset"] == SELECTED_ASSET_ID


def test_stage4_proof_scope_is_brand_not_temple() -> None:
    contract = adapter_contract()
    assert contract["proof_scope"]["identity"] == STAGE4_PROOF_SCOPE
    assert contract["proof_scope"]["not"] == "THE TEMPLE PROJECT MASTER → STORY"
    assert STAGE4_PROOF_SCOPE == "INVESTHOME BRAND MASTER → STORY"


def test_approval_workflow_does_not_run_stage_4_or_generate() -> None:
    src = inspect.getsource(generate_phase12_1_approve_lock)
    assert "persist_gpt_image" not in src
    assert "attach_format_child" not in src
    assert "adapt_premium_master_to_format" not in src
    assert NEXT_PHASE == "STAGE 4.0 RETRY — INVESTHOME BRAND MASTER 4:5 → 9:16 STORY"
    assert "stage_4_executed" in src
    assert STATUS == "PRODUCTION_PREMIUM_MASTER_APPROVED"
    assert "NOT AVAILABLE" in src
