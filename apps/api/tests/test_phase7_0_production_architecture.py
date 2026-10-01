"""Phase 7.0 — quality-first visual master. No auto promotion. Research 6.1–6.4 retired."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase7_0_doctrine import (
    MASTER_TYPE,
    PRIMARY_CREATIVE_ENGINE,
    PRODUCTION_DOCTRINE,
    RETIRED_RESEARCH_BRANCHES,
    SEMANTIC_COPY_FIELDS,
    VISUAL_TERRITORIES,
    empty_semantic_spec,
    format_adaptation_spec,
    production_doctrine,
    semantic_revision_contract,
)
from investhome_api.services.creative_director.phase7_0_production_reset import (
    CANDIDATE_IDS,
    MAX_IMAGE_CALLS,
    WORKFLOW_ID_70,
    artist_prompt,
    generate_phase7_0_production_reset,
)


def test_locks_and_no_promotion() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_70 == "phase7_0_production_architecture_reset"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert MASTER_TYPE == "VISUAL_MASTER"
    assert PRIMARY_CREATIVE_ENGINE == "GPT_IMAGE_EDIT_VISUAL_MASTER"
    assert generate_phase7_0_production_reset
    assert CANDIDATE_IDS == ("A", "B", "C")
    assert MAX_IMAGE_CALLS == 3


def test_doctrine_and_contracts() -> None:
    doctrine = production_doctrine()
    assert doctrine["full_editability_required"] is False
    assert doctrine["no_phase_6_5"] is True
    assert list(RETIRED_RESEARCH_BRANCHES) == ["6.1", "6.1-R1", "6.2", "6.3", "6.3A", "6.3B", "6.4"]
    spec = empty_semantic_spec()
    assert set(spec["semantic_copy"]) >= set(SEMANTIC_COPY_FIELDS)
    assert set(spec["visual_territories"]) == set(VISUAL_TERRITORIES)
    assert spec["pixel_complete_scene_graph"] is False
    rev = semantic_revision_contract()
    assert rev["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert rev["COPY_EDIT_ONLY"]["status"] == "PASS"
    assert rev["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
    assert rev["executed"] is False
    assert "COMMERCIAL_TERRITORY" in rev["PRICE_EDIT_ONLY"]["allowed"]
    assert "PROJECT_PHOTO_TERRITORY" in rev["VISUAL_REPLACE_ONLY"]["allowed"]
    fmt = format_adaptation_spec()
    assert fmt["implemented"] is False
    assert fmt["status"] == "PASS"
    assert set(fmt["formats"]) >= {"4:5", "1:1", "9:16", "16:9"}


def test_does_not_promote_or_reconstruct() -> None:
    import investhome_api.services.creative_director.phase7_0_production_reset as workflow

    src = inspect.getsource(workflow)
    assert "compose_relational_v4(" not in src
    assert "new_master_created" in src
    assert "promoted_to_master" in src
    assert "edit_image" in src
    prompt = artist_prompt({"visual_idea": "campaign depth", "creative_brief": "agency finish"})
    assert "Do not invent a different building" in prompt
    assert "Do not pixel-copy Concept 3" in prompt
    assert "sidebar" not in prompt.lower()
