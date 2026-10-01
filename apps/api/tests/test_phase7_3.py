"""Phase 7.3 — reference-led master. No C-R2. No ellipse polish. No promotion."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME, WRONG_PREFIX_NAMES
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase7_3_compose import canvas_artist_prompt
from investhome_api.services.creative_director.phase7_3_grammar import (
    CANDIDATE_IDS,
    FIDELITY_KEYS,
    GRAMMAR_FIELDS,
    MAX_IMAGE_CALLS,
    locked_grade_a,
)
from investhome_api.services.creative_director.phase7_3_reference_led import (
    WORKFLOW_ID_73,
    generate_phase7_3_reference_led_campaign_master,
)


def test_locks_and_grade_a_set() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert WORKFLOW_ID_73 == "phase7_3_reference_led_campaign_master"
    assert CANONICAL_FOLDER_NAME == "DESIGN_REFERENCES"
    assert "12_DESIGN_REFERENCES" in WRONG_PREFIX_NAMES
    assert locked_grade_a() == GRADE_A_REFERENCES
    ids = {item[0] for item in GRADE_A_REFERENCES}
    names = {item[1] for item in GRADE_A_REFERENCES}
    assert ids == {
        "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57",
        "3a3c4832-a8c1-5a43-a518-d895ee78fbe1",
        "15e71ec3-ff92-5604-84aa-2582510d0615",
        "b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd",
        "a1046460-04ad-5ef1-bd42-88042c4d9760",
        "1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2",
    }
    assert names == {
        "ORNEK_00013.jpg",
        "ORNEK_00001.jpg",
        "ORNEK_00006.jpg",
        "ORNEK_00015.jpg",
        "ORNEK_00011.jpg",
        "ORNEK_00008.jpg",
    }
    assert generate_phase7_3_reference_led_campaign_master
    assert CANDIDATE_IDS == ("A", "B", "C")
    assert MAX_IMAGE_CALLS == 3
    assert "COMPOSITIONAL_GRAVITY" in GRAMMAR_FIELDS
    assert "CRAFT_SOPHISTICATION_TRANSFER" in FIDELITY_KEYS


def test_revision_and_no_c_branch() -> None:
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]
    assert rev["executed"] is False
    import investhome_api.services.creative_director.phase7_3_compose as compose
    import investhome_api.services.creative_director.phase7_3_grammar as grammar
    import investhome_api.services.creative_director.phase7_3_reference_led as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose) + inspect.getsource(grammar)
    assert "PARENT_C_ASSET_ID" not in src
    assert "phase7_2_r1_polish" not in src
    assert "generate_phase7_2_r1" not in src
    assert "SEEDED_LAYOUTS" not in src
    assert "3d0ae3c4-5394-44bf-85f9-551337875b3c" not in src
    assert "compose_relational_v4(" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    prompt = canvas_artist_prompt(
        grammar={"fields": {"PHOTO_GEOMETRY": "designed mass"}},
        why="fits Day_007",
        layout={"photo_role": "designed_photographic_mass"},
    )
    assert "Do NOT copy" in prompt
    assert "ellipse" in prompt.casefold()
    assert "left/right split" in prompt or "left half" in prompt.casefold()
    assert "Do not draw" in prompt or "No logo" in prompt
