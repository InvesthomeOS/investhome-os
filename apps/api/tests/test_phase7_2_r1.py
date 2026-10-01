"""Phase 7.2-R1 — Candidate C polish. No redesign. No promotion. No GPT photo edit."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase7_2_photo_object import photo_percentage
from investhome_api.services.creative_director.phase7_2_r1_candidate_c import WORKFLOW_ID_72R1, generate_phase7_2_r1_candidate_c
from investhome_api.services.creative_director.phase7_2_r1_polish import C_R1_LAYOUT, PARENT_C_ASSET_ID


def test_locks_and_no_promotion() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PARENT_C_ASSET_ID == "3d0ae3c4-5394-44bf-85f9-551337875b3c"
    assert WORKFLOW_ID_72R1 == "phase7_2_r1_candidate_c_final_polish"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert generate_phase7_2_r1_candidate_c
    mass = photo_percentage(C_R1_LAYOUT["photo_box"])
    assert 0.42 <= mass <= 0.48, mass
    assert C_R1_LAYOUT["photo_shape"] == "ellipse"


def test_does_not_redesign_or_edit_photo() -> None:
    import investhome_api.services.creative_director.phase7_2_r1_candidate_c as workflow
    import investhome_api.services.creative_director.phase7_2_r1_polish as polish

    src = inspect.getsource(workflow) + inspect.getsource(polish)
    assert "compose_relational_v4(" not in src
    assert "edit_image" not in inspect.getsource(workflow)
    assert "generate_image" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "FINAL_MASTER_CANDIDATE_PENDING_HUMAN_APPROVAL" in inspect.getsource(workflow)
    assert C_R1_LAYOUT["photo_role"] == "offset_photographic_cutout"
