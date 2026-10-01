"""Phase 5.5B-R1 gates. Approved draft reconstruction. No new draft. GPT Image = 0."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_5b_r1_structured_reconstruction import (
    WORKFLOW_ID_55B_R1,
    generate_visual_draft_reconstruction_55b_r1,
)
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.visual_draft_reconstruction import (
    APPROVED_DRAFT_ASSET_ID,
    DAY007_ASSET_ID,
    detect_navy_split,
    logo_visual_match,
    reconstruction_fidelity_pass,
    reconstruction_plan_from_structure,
)


def test_locks_approved_draft_and_real_brand() -> None:
    assert APPROVED_DRAFT_ASSET_ID == "56c40551-5890-44e7-a2dd-7e8660edb881"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2
    assert generate_visual_draft_reconstruction_55b_r1
    assert WORKFLOW_ID_55B_R1 == "phase5_5b_r1_structured_reconstruction"


def test_no_new_draft_and_no_gpt_image() -> None:
    import investhome_api.services.creative_director.phase5_5b_r1_structured_reconstruction as workflow
    import investhome_api.services.creative_director.visual_draft_reconstruction as recon

    flow = inspect.getsource(workflow)
    engine = inspect.getsource(recon)
    assert "edit_image" not in flow
    assert "generate_image" not in flow
    assert "edit_image" not in engine
    assert "generate_image" not in engine
    assert "images/generations" not in flow
    assert "new_draft_generated" in flow
    assert "must not call GPT Image" in flow
    assert inspect.signature(compose_graphic_design_v3).parameters["art_plan"].default is None


def test_plan_is_navy_photo_split_with_real_logo() -> None:
    plan = reconstruction_plan_from_structure({"navy_field_width": 0.38, "navy_color": [18, 32, 54], "boxes": {}})
    assert plan["composition"] == "navy_left_photo_right"
    assert plan["real_logo_asset_id"] == LOCKED_LOGO_ASSET_ID
    assert plan["cta_treatment"] == "editorial_gold_rule"
    assert plan["no_investhome_brand"] is True
    assert 0.32 <= plan["split_x"] <= 0.42


def test_fidelity_requires_all_eights() -> None:
    scores = {key: 8 for key in (
        "overall_composition",
        "navy_photo_proportion",
        "visual_mass",
        "headline_mass",
        "commercial_mass",
        "brand_role",
        "CTA_role",
        "spacing_rhythm",
        "whole_canvas_balance",
        "architecture_relationship",
        "premium_character",
    )}
    assert reconstruction_fidelity_pass(scores) is True
    scores["headline_mass"] = 7
    assert reconstruction_fidelity_pass(scores) is False


def test_navy_split_detects_left_field() -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (200, 250), (180, 170, 160))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 76, 250), fill=(16, 28, 48))
    split = detect_navy_split(image)
    assert 0.32 <= split <= 0.42
