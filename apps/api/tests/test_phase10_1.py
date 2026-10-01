"""Phase 10.1 — HEADLINE_ONLY child. No full regeneration. No Stage 3."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import attach_derived_revision
from investhome_api.services.creative_director.phase10_1_headline_revise import apply_clean_headline_revision
from investhome_api.services.creative_director.phase10_1_master import CHILD_REVISION_ID, FORBIDDEN_ASSETS, WORKFLOW_ID_10_1, generate_phase10_1_copy_revision
from investhome_api.services.creative_director.phase10_1_parse import NEW_COPY, OLD_COPY, REVISION_TYPE, USER_COMMAND, parse_headline_only_command


def test_parse_exact_command() -> None:
    parsed = parse_headline_only_command(USER_COMMAND)
    assert parsed["pass"] is True
    assert parsed["revision_type"] == REVISION_TYPE == "HEADLINE_ONLY"
    assert parsed["old_copy"] == OLD_COPY == "ALIRKEN KAZAN"
    assert parsed["new_copy"] == NEW_COPY == "ŞİMDİ YATIRIM ZAMANI"
    assert parsed["preserve_everything_else"] is True
    assert "ALIRKEN KAZAN başlığını ŞİMDİ YATIRIM ZAMANI olarak değiştir" in USER_COMMAND
    assert "başka hiçbir şeyi değiştirme" in USER_COMMAND


def test_parse_rejects_price_and_format() -> None:
    price = parse_headline_only_command("Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme.")
    assert price["pass"] is False
    story = parse_headline_only_command("ALIRKEN KAZAN başlığını ŞİMDİ YATIRIM ZAMANI olarak değiştir ve Story yap.")
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
        "visual_asset": "22222222-2222-2222-2222-222222222222",
        "approval_status": "DRAFT",
        "router_eligible": False,
        "revision_type": "HEADLINE_ONLY",
    }
    attach_derived_revision(parent, child)
    assert parent["visual_asset"] == APPROVED_ASSET_03
    assert parent["approval_status"] == "HUMAN_APPROVED"
    assert parent["router_eligible"] is True
    assert parent["derived_revisions"][0]["revision_id"] == CHILD_REVISION_ID


def test_locks_and_clean_rebuild() -> None:
    assert APPROVED_ASSET_03 in FORBIDDEN_ASSETS
    assert WORKFLOW_ID_10_1 == "phase10_1_natural_language_copy_revision"
    assert generate_phase10_1_copy_revision
    assert apply_clean_headline_revision
    src = inspect.getsource(apply_clean_headline_revision)
    assert "inpaint_holes" in src
    assert "composite_glyphs" not in src
    workflow = inspect.getsource(generate_phase10_1_copy_revision)
    assert "attach_format_child" not in workflow
    assert "empty_master(" not in workflow
    assert "APPROVED_ASSET_03" in workflow
