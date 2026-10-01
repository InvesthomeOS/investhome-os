"""BrandIntegrationEngineV1 + EditorialCTAComposerV1."""

from __future__ import annotations

from typing import Any


def integrate_brand(
    *,
    campaign_bbox: tuple[int, int, int, int],
    offer_bbox: tuple[int, int, int, int],
    architecture_x: float,
    canvas: tuple[int, int],
    logo_size: tuple[int, int],
    mode: str,
) -> dict[str, Any]:
    w, h = canvas
    lw, lh = logo_size
    cx0, cy0, cx1, cy1 = campaign_bbox
    ox0, oy0, ox1, oy1 = offer_bbox
    if mode == "GROUND_PLANE":
        x = max(int(w * 0.05), ox0 - lw - int(w * 0.028))
        y = oy0 + max(0, ((oy1 - oy0) - lh) // 2)
        reason = "brand shares the ground lockup baseline as a designed member, not a free rectangle"
        relation = "BELONGS_TO_GROUND_LOCKUP"
    elif mode == "COLUMN_OPEN":
        x = min(int(w * 0.055), cx0)
        y = max(int(h * 0.036), cy0 - lh - int(h * 0.018))
        reason = "brand opens the editorial column as the first designed member"
        relation = "OPENS_COLUMN"
    else:
        x = min(int(w * (architecture_x - 0.16)), ox1 + int(w * 0.04))
        x = max(ox1 + int(w * 0.024), x)
        y = oy0
        if x + lw > int(w * 0.92):
            x = int(w * 0.92) - lw
        reason = "logo balances the offer/campaign column on a shared sky band"
        relation = "BALANCES_CAMPAIGN"
    box = (x, y, x + lw, y + lh)
    return {
        "schema": "BrandIntegrationEngineV1",
        "px": box,
        "relationship_to_headline": relation,
        "relationship_to_architecture": "clear_of_silhouette",
        "relationship_to_offer": "adjacent_not_isolated",
        "visual_counterweight": True,
        "brand_visibility": "tonal_field",
        "tonal_support": True,
        "clear_space": 0.028,
        "reading_flow_position": "after_offer" if mode == "GROUND_PLANE" else "with_campaign",
        "visual_reason": reason,
        "find_free_rectangle": False,
        "immutable_logo": True,
    }


def compose_editorial_cta(
    *,
    offer_bbox: tuple[int, int, int, int],
    unit_size: tuple[int, int],
    cta_size: tuple[int, int],
    canvas: tuple[int, int],
    mode: str,
    alignment: str = "left",
) -> dict[str, Any]:
    w, h = canvas
    ox0, _oy0, ox1, oy1 = offer_bbox
    uw, uh = unit_size
    cw, ch = cta_size
    if mode == "GROUND_PLANE":
        x = ox1 + int(w * 0.03)
        y_unit = oy1 - max(uh, ch) - 4
        y_cta = y_unit + uh + 8
        closure = "lockup_baseline_closure"
    else:
        x = ox0 if alignment == "left" else ox1 - max(uw, cw)
        y_unit = oy1 + int(h * 0.018)
        y_cta = y_unit + uh + int(h * 0.012)
        closure = "column_editorial_closure"
    unit_box = (x, y_unit, x + uw, y_unit + uh)
    cta_box = (x, y_cta, x + cw, y_cta + ch)
    rule = (x, y_cta - 8, x + cw, y_cta - 6)
    return {
        "schema": "EditorialCTAComposerV1",
        "unit_px": unit_box,
        "cta_px": cta_box,
        "rule_px": rule,
        "closure": closure,
        "pill": False,
        "button_rectangle": False,
        "floating_ui": False,
        "modes": ["editorial_inscription", "rule_connected", "baseline_closure", "edge_closure", "tonal_closure"],
    }
