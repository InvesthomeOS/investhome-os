"""Phase 5.4K-R1 gates. Does not redesign compositor or family."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, compose_full_frame_campaign
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_full_frame_r1 import (
    BASE_CANDIDATE_ASSET_ID,
    DAY007_ASSET_ID,
    LOCKED_CENTERING,
    LOCKED_SOURCE_CROP,
    WORKFLOW_ID_54K_R1,
    generate_full_frame_r1_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2


def test_r1_locks_day007_and_crop() -> None:
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert LOCKED_CENTERING == (0.50, 0.42)
    assert LOCKED_SOURCE_CROP == [161.06, 0.0, 1256.26, 1369.0]
    assert BASE_CANDIDATE_ASSET_ID == "fd623439-5730-45c9-898b-30a80df42d00"
    assert FAMILY_ID == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN"


def test_r1_does_not_call_image_models() -> None:
    import investhome_api.services.creative_director.phase5_full_frame_r1 as workflow

    source = inspect.getsource(workflow)
    assert "edit_image" not in source
    assert "generate_image" not in source
    assert "images/generations" not in source
    assert "polish=True" in source
    assert WORKFLOW_ID_54K_R1 in source
    assert PRODUCTION_COVER_V2


def test_v3_polish_kwarg_defaults_off() -> None:
    assert "polish" in inspect.signature(compose_graphic_design_v3).parameters
    assert "polish" in inspect.signature(compose_full_frame_campaign).parameters
    assert inspect.signature(compose_full_frame_campaign).parameters["polish"].default is False
