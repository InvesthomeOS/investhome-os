"""TypographicCompositionEngineV1 — type as visual form, not a text dump."""

from __future__ import annotations

from typing import Any

from PIL import ImageDraw, ImageFont

from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked


def optical_origin(x: int, *, serif: bool = True) -> int:
    return x - 2 if serif else x


def compose_campaign_type(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    first: str,
    last: str,
    display: ImageFont.ImageFont,
    display_sm: ImageFont.ImageFont,
    fill: tuple[int, int, int] = IVORY,
    accent: tuple[int, int, int] = GOLD,
    tracking: float = 20.0,
) -> dict[str, Any]:
    ox, oy = origin
    ox = optical_origin(ox, serif=True)
    b1 = _draw_tracked(draw, (ox, oy), first, display, fill, tracking=tracking, anchor="lt")
    leading = max(2, int((b1[3] - b1[1]) * 0.08))
    b2 = _draw_tracked(draw, (ox, b1[3] + leading), last or first, display_sm, accent, tracking=8, anchor="lt")
    rule_y = b2[3] + 6
    draw.line((b2[0], rule_y, b2[2], rule_y), fill=accent, width=2)
    bbox = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), rule_y + 2)
    return {
        "schema": "TypographicCompositionEngineV1",
        "headline": bbox,
        "first": b1,
        "last": b2,
        "editorial_rule": (b2[0], rule_y, b2[2], rule_y + 2),
        "optical_alignment": True,
        "display_support_scale": round((b2[3] - b2[1]) / max(1, b1[3] - b1[1]), 3),
        "vertical_rhythm": leading,
        "line_break": [first, last],
        "mixed_serif_sans": False,
        "text_as_visual_form": True,
    }
