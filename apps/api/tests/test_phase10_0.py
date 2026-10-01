"""Phase 10.0 — natural-language PRICE_ONLY child. No full regeneration. No Stage 3."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import (
    CHILD_REVISION_ID,
    WORKFLOW_ID_10,
    attach_derived_revision,
    generate_phase10_0_natural_language_price_revision,
)
from investhome_api.services.creative_director.phase10_0_parse import (
    NEW_PRICE,
    OLD_PRICE,
    REVISION_TYPE,
    USER_COMMAND,
    parse_price_only_command,
)
from investhome_api.services.creative_director.phase10_0_price_revise import pixel_delta_outside


def test_parse_exact_command() -> None:
    parsed = parse_price_only_command(USER_COMMAND, current_price=OLD_PRICE)
    assert parsed["pass"] is True
    assert parsed["revision_type"] == REVISION_TYPE == "PRICE_ONLY"
    assert parsed["old_value"] == "675.000 USD"
    assert parsed["new_value"] == "750.000 USD"
    assert parsed["preserve_everything_else"] is True
    assert USER_COMMAND == "Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme."


def test_parse_rejects_copy_and_format() -> None:
    bad = parse_price_only_command("Başlığı değiştir ve fiyatı 750.000 USD yap.")
    assert bad["pass"] is False
    story = parse_price_only_command("Fiyatı 750.000 USD yap ve Story yap.")
    assert story["pass"] is False


def test_pixel_delta_outside_is_exact_zero() -> None:
    parent = Image.new("RGB", (40, 30), (12, 10, 8))
    draw = ImageDraw.Draw(parent)
    draw.rectangle([2, 2, 10, 10], fill=(200, 180, 150))
    child = parent.copy()
    ImageDraw.Draw(child).rectangle([16, 8, 28, 18], fill=(240, 220, 190))
    box = (15, 7, 30, 20)
    report = pixel_delta_outside(parent, child, box)
    assert report["outside_changed_pixels"] == 0
    assert report["outside_max_channel_delta"] == 0
    assert report["pass"] is True
    leaked = child.copy()
    leaked.putpixel((1, 1), (255, 0, 0))
    fail = pixel_delta_outside(parent, leaked, box)
    assert fail["outside_changed_pixels"] == 1
    assert fail["pass"] is False


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
        "visual_asset": "11111111-1111-1111-1111-111111111111",
        "approval_status": "DRAFT",
        "router_eligible": False,
        "revision_type": "PRICE_ONLY",
    }
    attach_derived_revision(parent, child)
    assert parent["visual_asset"] == APPROVED_ASSET_03
    assert parent["approval_status"] == "HUMAN_APPROVED"
    assert parent["router_eligible"] is True
    assert parent["derived_revisions"][0]["revision_id"] == CHILD_REVISION_ID


def test_no_regeneration_or_format() -> None:
    import investhome_api.services.creative_director.phase10_0_master as workflow
    import investhome_api.services.creative_director.phase10_0_price_revise as revise

    src = inspect.getsource(workflow) + inspect.getsource(revise)
    assert "compose_master_03_r1" not in inspect.getsource(workflow)
    assert "attach_format_child" not in src
    assert "empty_master(" not in inspect.getsource(workflow)
    assert "persist_gpt_image" not in inspect.getsource(revise)
    assert WORKFLOW_ID_10 == "phase10_0_natural_language_price_revision"
    assert generate_phase10_0_natural_language_price_revision
