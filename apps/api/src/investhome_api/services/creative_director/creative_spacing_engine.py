"""CreativeSpacingEngineV1 — proportional family rhythm, not arbitrary pixel gaps."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens


def spacing_plan(family: dict[str, Any], canvas: tuple[int, int], *, scale: float = 1.0) -> dict[str, Any]:
    tokens = execution_tokens(family)
    h = canvas[1]
    ratios = dict(tokens.get("group_spacing_ratio") or {})
    px = {key: max(4, int(h * float(value) * scale)) for key, value in ratios.items()}
    return {
        "schema": "CreativeSpacingEngineV1",
        "family_id": family.get("family_id"),
        "scale": scale,
        "ratios": ratios,
        "pixels": px,
        "headline_internal_leading": px.get("headline_internal"),
        "headline_to_unit": px.get("headline_to_unit"),
        "unit_to_commercial": px.get("unit_to_commercial"),
        "price_to_advantage": px.get("price_to_advantage"),
        "commercial_to_cta": px.get("commercial_to_cta"),
        "logo_clear_space": px.get("logo_clear"),
    }
