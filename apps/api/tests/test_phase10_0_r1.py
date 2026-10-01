"""Phase 10.0-R1 — clean PRICE_ONLY child. No full regeneration. No overwrite of rejected child."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_0_parse import USER_COMMAND
from investhome_api.services.creative_director.phase10_0_r1_master import (
    CHILD_REVISION_R1_ID,
    REJECTED_CHILD_ASSET_ID,
    WORKFLOW_ID_10_R1,
    generate_phase10_0_r1_clean_price_revision,
)
from investhome_api.services.creative_director.phase10_0_r1_price_revise import apply_clean_price_revision


def test_locks() -> None:
    assert CHILD_REVISION_R1_ID != CHILD_REVISION_ID
    assert REJECTED_CHILD_ASSET_ID == "0586f984-b2d7-43d2-9394-1abeead0fba6"
    assert REJECTED_CHILD_ASSET_ID != APPROVED_ASSET_03
    assert WORKFLOW_ID_10_R1 == "phase10_0_r1_clean_price_revision"
    assert USER_COMMAND == "Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme."
    assert generate_phase10_0_r1_clean_price_revision
    assert apply_clean_price_revision


def test_no_paint_over_old_glyphs() -> None:
    import investhome_api.services.creative_director.phase10_0_r1_master as workflow
    import investhome_api.services.creative_director.phase10_0_r1_price_revise as revise

    src = inspect.getsource(revise)
    assert "inpaint_holes" in src
    assert "composite_glyphs" not in src
    assert "attach_format_child" not in inspect.getsource(workflow)
    assert "empty_master(" not in inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "REJECTED_CHILD_ASSET_ID" in inspect.getsource(workflow)
