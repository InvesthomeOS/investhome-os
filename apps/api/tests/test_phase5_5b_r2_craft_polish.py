"""Phase 5.5B-R2 gates. Craft polish only. No new draft. GPT Image = 0."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.commercial_number_renderer import render_price
from investhome_api.services.creative_director.phase5_5b_r2_craft_polish import (
    R1_CANDIDATE_ASSET_ID,
    WORKFLOW_ID_55B_R2,
    generate_craft_polish_55b_r2,
)
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID
from investhome_api.services.creative_director.visual_draft_reconstruction import FIDELITY_R2, measure_tracked_glyphs


def test_locks_r1_base_and_real_logo() -> None:
    assert R1_CANDIDATE_ASSET_ID == "abe022be-33b5-4236-a610-012ca20af267"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert WORKFLOW_ID_55B_R2 == "phase5_5b_r2_craft_polish"
    assert generate_craft_polish_55b_r2


def test_no_gpt_image_or_new_draft() -> None:
    import investhome_api.services.creative_director.phase5_5b_r2_craft_polish as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "new_draft_generated" in src
    assert "must not call GPT Image" in src
    assert "headline_glyph_clipping" in src


def test_price_renderer_accepts_tight_gap() -> None:
    assert "gap" in inspect.signature(render_price).parameters
    assert "parts" in inspect.signature(render_price).parameters


def test_fidelity_r2_keys() -> None:
    assert "headline_mass" in FIDELITY_R2
    assert "spacing_rhythm" in FIDELITY_R2


def test_glyph_measure_returns_box() -> None:
    from PIL import ImageFont

    font = ImageFont.load_default()
    box = measure_tracked_glyphs("ALIRKEN", font, 0)
    assert box[2] >= box[0]
    assert box[3] >= box[1]


def test_glyph_measure_uses_wide_canvas() -> None:
    from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
    from investhome_api.services.creative_director.visual_draft_reconstruction import _text_width

    fonts = build_font_registry()
    font = font_for_role(fonts, "DISPLAY_SERIF", 90)
    box = measure_tracked_glyphs("ALIRKEN", font, 0.0)
    nominal = _text_width(font, "ALIRKEN", tracking=0.0, size=90)
    assert box[2] >= int(nominal) - 24
    assert box[2] > 300
