"""Phase 7.4 — direct visual transfer. No grammar. No R1. No promotion."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase7_4_compose import MAX_IMAGE_CALLS, canvas_prompt, photo_protect_mask
from investhome_api.services.creative_director.phase7_4_direct_transfer import (
    CEILING_NOTE,
    REFERENCE_ID,
    WORKFLOW_ID_74,
    generate_phase7_4_direct_visual_reference_transfer,
)


def test_locks() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert REFERENCE_ID == "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57"
    assert WORKFLOW_ID_74 == "phase7_4_direct_visual_reference_transfer"
    assert generate_phase7_4_direct_visual_reference_transfer
    assert MAX_IMAGE_CALLS == 3
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert "PRODUCT-LEVEL" in CEILING_NOTE


def test_no_grammar_layer_or_r1() -> None:
    import investhome_api.services.creative_director.phase7_4_compose as compose
    import investhome_api.services.creative_director.phase7_4_direct_transfer as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "ReferenceCampaignGrammar" not in src
    assert "request_reference_grammars" not in src
    assert "request_suitability_and_selection" not in src
    assert "SEEDED_LAYOUTS" not in src
    assert "phase7_3_compose" not in inspect.getsource(workflow)
    assert "53da2774" not in src
    assert "compose_relational_v4(" not in src
    assert "A-R1" not in src
    assert "mask" in inspect.getsource(compose)
    assert "stage_photo" in inspect.getsource(compose)
    prompt = canvas_prompt({"composition_instruction": "mass against architecture", "how_day007_participates": "designed object"})
    assert "ORNEK_00013" in prompt
    assert "LOCKED" in prompt
    mask = photo_protect_mask({"photo_box": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.6}, "photo_shape": "rect"})
    assert mask["mask_png"][:8] == b"\x89PNG\r\n\x1a\n"
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
