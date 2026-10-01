"""Phase 10.2 — VISUAL_REPLACE_ONLY child. No full regeneration. No Stage 3."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import attach_derived_revision
from investhome_api.services.creative_director.phase10_2_master import CHILD_REVISION_ID, FORBIDDEN_ASSETS, WORKFLOW_ID_10_2, generate_phase10_2_photo_replacement
from investhome_api.services.creative_director.phase10_2_parse import (
    OLD_EXTERIOR_ASSET_ID,
    REVISION_TYPE,
    TARGET_OBJECT,
    USER_COMMAND,
    parse_visual_replace_command,
)
from investhome_api.services.creative_director.phase10_2_replace import SELECTED_ASSET_ID, apply_exterior_replacement


def test_parse_exact_command() -> None:
    parsed = parse_visual_replace_command(USER_COMMAND)
    assert parsed["pass"] is True
    assert parsed["revision_type"] == REVISION_TYPE == "VISUAL_REPLACE_ONLY"
    assert parsed["target_object"] == TARGET_OBJECT == "PROJECT_EXTERIOR_REVEAL"
    assert parsed["preserve_everything_else"] is True
    assert parsed["preserve_interior"] is True
    assert "dış cephe" in USER_COMMAND
    assert "başka hiçbir şeyi değiştirme" in USER_COMMAND


def test_parse_rejects_copy_price_format() -> None:
    copy = parse_visual_replace_command("ALIRKEN KAZAN başlığını değiştir, başka hiçbir şeyi değiştirme.")
    assert copy["pass"] is False
    price = parse_visual_replace_command("Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme.")
    assert price["pass"] is False
    story = parse_visual_replace_command("Sağdaki dış cephe görselini değiştir ve Story yap.")
    assert story["pass"] is False


def test_child_does_not_replace_parent() -> None:
    parent = {
        "visual_asset": APPROVED_ASSET_03,
        "approval_status": "HUMAN_APPROVED",
        "master_state": "LOCKED_MASTER",
        "router_eligible": True,
        "version": 2,
    }
    child = {
        "revision_id": CHILD_REVISION_ID,
        "visual_asset": "33333333-3333-3333-3333-333333333333",
        "approval_status": "DRAFT",
        "router_eligible": False,
        "revision_type": "VISUAL_REPLACE_ONLY",
    }
    attach_derived_revision(parent, child)
    assert parent["visual_asset"] == APPROVED_ASSET_03
    assert parent["approval_status"] == "HUMAN_APPROVED"
    assert parent["router_eligible"] is True


def test_locks() -> None:
    assert APPROVED_ASSET_03 in FORBIDDEN_ASSETS
    assert OLD_EXTERIOR_ASSET_ID in FORBIDDEN_ASSETS
    assert SELECTED_ASSET_ID != OLD_EXTERIOR_ASSET_ID
    assert WORKFLOW_ID_10_2 == "phase10_2_natural_language_photo_replacement"
    src = inspect.getsource(apply_exterior_replacement)
    assert "choose_crop" in src
    workflow = inspect.getsource(generate_phase10_2_photo_replacement)
    assert "empty_master(" not in workflow
    assert "attach_format_child" not in workflow
    assert "APPROVED_ASSET_03" in workflow
