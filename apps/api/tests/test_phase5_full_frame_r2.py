"""Phase 5.4K-R2 gates. Single editorial lockup. Does not polish R1."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.full_frame_architectural_family import (
    FAMILY_ID,
    compose_full_frame_campaign,
    lockup_is_single_side,
)
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_full_frame_r2 import (
    BASE_CANDIDATE_ASSET_ID,
    DAY007_ASSET_ID,
    LOCKED_CENTERING,
    LOCKED_SOURCE_CROP,
    WORKFLOW_ID_54K_R2,
    generate_full_frame_r2_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2


def test_r2_locks_day007_and_r1_base() -> None:
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert LOCKED_CENTERING == (0.50, 0.42)
    assert LOCKED_SOURCE_CROP == [161.06, 0.0, 1256.26, 1369.0]
    assert BASE_CANDIDATE_ASSET_ID == "e487905f-60e7-45c6-a237-6a9f2a10c29a"
    assert FAMILY_ID == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN"


def test_r2_does_not_call_image_models() -> None:
    import investhome_api.services.creative_director.phase5_full_frame_r2 as workflow

    source = inspect.getsource(workflow)
    assert "edit_image" not in source
    assert "generate_image" not in source
    assert "images/generations" not in source
    assert "lockup=True" in source
    assert "polish=True" not in source
    assert WORKFLOW_ID_54K_R2 in source
    assert PRODUCTION_COVER_V2
    assert generate_full_frame_r2_4x5


def test_lockup_kwarg_defaults_off() -> None:
    assert inspect.signature(compose_graphic_design_v3).parameters["lockup"].default is False
    assert inspect.signature(compose_full_frame_campaign).parameters["lockup"].default is False
    assert inspect.signature(compose_graphic_design_v3).parameters["polish"].default is False


def test_single_side_helper_rejects_split() -> None:
    left = {"headline": {"px": [40, 40, 200, 80]}, "price": {"px": [40, 90, 180, 120]}}
    split = {"headline": {"px": [800, 40, 1000, 80]}, "price": {"px": [40, 90, 180, 120]}}
    assert lockup_is_single_side(left, "left", (1088, 1360)) is True
    assert lockup_is_single_side(split, "left", (1088, 1360)) is False
    assert lockup_is_single_side(split, "right", (1088, 1360)) is False
