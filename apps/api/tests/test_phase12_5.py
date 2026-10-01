"""Phase 12.5 — family-wide PRICE_ONLY. No generation. No 16:9. No auto-approval."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_router_v2 import (
    FAMILY_WIDE_REVISION,
    classify_production_intent,
)
from investhome_api.services.creative_director.phase12_3_family_ingest import FAMILY_ID, MASTER_1X1_ID, MASTER_4X5_ID, MASTER_9X16_ID
from investhome_api.services.creative_director.phase12_4_approve_lock import PHASE_12_5_COMMAND
from investhome_api.services.creative_director.phase12_5_lock import (
    CHILD_1X1_ID,
    CHILD_9X16_ID,
    REVISION_TYPE,
    STATUS_FAIL,
    WORKFLOW_ID_12_5,
    generate_phase12_5_family_wide_revision,
)
from investhome_api.services.creative_director.phase12_5_price_revise import (
    NEW_VALUE,
    OLD_VALUE,
    apply_feed_price_revision,
    apply_story_price_revision,
    swap_357_to_375,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import ORNEK_FAMILY_ID


def test_command_routes_family_wide_price_only() -> None:
    classified = classify_production_intent(PHASE_12_5_COMMAND)
    assert classified["intent"] == FAMILY_WIDE_REVISION
    assert REVISION_TYPE == "PRICE_ONLY"
    assert OLD_VALUE == "357.000"
    assert NEW_VALUE == "375.000"
    assert PHASE_12_5_COMMAND.startswith("Bu kampanyadaki 357.000")


def test_feed_does_not_invent_price() -> None:
    parent = Image.new("RGB", (400, 500), (40, 47, 56))
    child, meta = apply_feed_price_revision(parent)
    assert child is None
    assert meta["status"] == "SKIPPED_TARGET_NOT_PRESENT"
    assert "absent" in meta["reason"].lower()


def test_story_glyph_swap_zero_outside_delta() -> None:
    parent = Image.new("RGB", (1080, 1920), (24, 26, 30))
    draw = ImageDraw.Draw(parent)
    draw.rectangle((180, 430, 900, 518), fill=(255, 255, 255))
    black = (0, 0, 0)
    x = 230
    for width in (24, 24, 24, 24, 4, 24, 24, 24):
        draw.rectangle((x, 444, x + width - 1, 504), fill=black)
        x += width + 3
    child, meta = apply_story_price_revision(parent)
    assert meta["pixel_delta"]["outside_changed_pixels"] == 0
    assert meta["pixel_delta"]["pass"] is True
    assert meta["old_value"] == OLD_VALUE
    assert meta["new_value"] == NEW_VALUE
    assert child.size == parent.size


def test_children_are_draft_and_do_not_generate() -> None:
    import investhome_api.services.creative_director.phase12_5_lock as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" in src
    assert "provider_generation_id=None" in src
    assert '"approval_status": "DRAFT"' in src
    assert "generate_gpt_image" not in src
    assert "openai" not in inspect.getsource(workflow.generate_phase12_5_family_wide_revision).lower()
    assert "compose_story" not in src
    assert STATUS_FAIL == "FAMILY_WIDE_REVISION_FAIL"
    assert WORKFLOW_ID_12_5 == "phase12_5_family_wide_natural_language_revision_proof"
    assert CHILD_9X16_ID != CHILD_1X1_ID
    assert MASTER_4X5_ID != MASTER_9X16_ID != MASTER_1X1_ID
    assert FAMILY_ID != ORNEK_FAMILY_ID
    assert "LANDSCAPE" in src
    assert "MASTER MISSING" in src
    assert generate_phase12_5_family_wide_revision


def test_swap_uses_native_glyphs() -> None:
    src = inspect.getsource(swap_357_to_375)
    assert "glyph5" in src
    assert "glyph7" in src
    assert "openai" not in src.lower()
    assert "ImageFont" not in src
