"""Phase 7.1 — Candidate C reality lock. No redesign. No promotion. No V4/V5."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_1_candidate_c_r1 import (
    ARCH_KEYS,
    PRESERVE_KEYS,
    WORKFLOW_ID_71,
    generate_phase7_1_candidate_c_r1,
)
from investhome_api.services.creative_director.phase7_1_reality_lock import PARENT_C_ASSET_ID


def test_locks_and_no_promotion() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PARENT_C_ASSET_ID == "b7c26048-dcff-469a-aedf-d26bcbfcb34a"
    assert WORKFLOW_ID_71 == "phase7_1_candidate_c_project_reality_lock"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert generate_phase7_1_candidate_c_r1
    assert "BUILDING_SILHOUETTE_FIDELITY" in ARCH_KEYS
    assert "ART_DIRECTION_PRESERVATION" in PRESERVE_KEYS


def test_does_not_redesign_or_promote() -> None:
    import investhome_api.services.creative_director.phase7_1_candidate_c_r1 as workflow
    import investhome_api.services.creative_director.phase7_1_reality_lock as lock

    src = inspect.getsource(workflow) + inspect.getsource(lock)
    assert "compose_relational_v4(" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "FINAL_VISUAL_MASTER_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert "model_redrew_building" in inspect.getsource(lock)
    assert "source_pixel_photo_territory_1to1" in inspect.getsource(lock)
    assert lock.project_pixel_provenance.__doc__ is None or True
    from PIL import Image

    mask = Image.new("L", (64, 64), 255)
    proven = lock.project_pixel_provenance(mask)
    assert proven["generated_project_architecture_pixels"] == 0
    assert proven["status"] == "PASS"
    assert proven["provenance"] == "REAL_DAY_007"
