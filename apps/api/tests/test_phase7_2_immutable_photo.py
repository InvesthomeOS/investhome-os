"""Phase 7.2 — immutable photo object. No paste-back. No C-R2. No promotion."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, TERRITORIES_72, revision_readiness_72
from investhome_api.services.creative_director.phase7_2_immutable_photo import (
    CANDIDATE_IDS,
    MAX_IMAGE_CALLS,
    WORKFLOW_ID_72,
    canvas_artist_prompt,
    generate_phase7_2_immutable_photo_object,
)
from investhome_api.services.creative_director.phase7_2_photo_object import SEEDED_LAYOUTS, clamp_photo_mass, photo_percentage


def test_locks_and_no_promotion() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert WORKFLOW_ID_72 == "phase7_2_immutable_project_photo_object"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert generate_phase7_2_immutable_photo_object
    assert CANDIDATE_IDS == ("A", "B", "C")
    assert MAX_IMAGE_CALLS == 3
    assert "PROJECT_PHOTO_OBJECT" in TERRITORIES_72


def test_photo_object_mass_and_revision_target() -> None:
    for sid, layout in SEEDED_LAYOUTS.items():
        box = clamp_photo_mass(dict(layout["photo_box"]))
        mass = photo_percentage(box)
        assert 0.35 <= mass <= 0.70, (sid, mass)
    roles = {layout["photo_role"] for layout in SEEDED_LAYOUTS.values()}
    assert len(roles) == 3
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert rev["executed"] is False


def test_does_not_paste_back_or_promote() -> None:
    import investhome_api.services.creative_director.phase7_2_immutable_photo as workflow
    import investhome_api.services.creative_director.phase7_2_photo_object as photo

    src = inspect.getsource(workflow) + inspect.getsource(photo)
    assert "compose_relational_v4(" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "phase7_1_candidate_c_r1" not in inspect.getsource(photo)
    assert "generate_phase7_1" not in inspect.getsource(workflow)
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    prompt = canvas_artist_prompt({"visual_idea": "aperture", "creative_brief": "agency"}, SEEDED_LAYOUTS["B"])
    assert "Do NOT draw a logo" in prompt
    assert "Do NOT draw any building representing the project" in prompt
    assert "magenta" in prompt.lower()
