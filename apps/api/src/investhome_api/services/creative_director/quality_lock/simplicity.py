"""Simplicity Director — default element caps; premium ≠ more elements."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SimplicityCaps:
    max_headlines: int = 1
    max_supporting: int = 3
    max_cta: int = 1
    max_logos: int = 1
    allow_badges: bool = False
    allow_icons: bool = False
    allow_price_block: bool = False
    density_label: str = "medium"
    principles: tuple[str, ...] = (
        "ONE AD = ONE PRIMARY MESSAGE.",
        "Default: 1 headline, 0–3 supporting, 1 CTA, 1 logo.",
        "Extra badges/icons/price blocks only when campaign intent requires them.",
        "Premium ≠ more elements — let the photograph breathe.",
        "Do not invent decorative panels, left rails, or bottom bands.",
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["principles"] = list(self.principles)
        return payload


def simplicity_caps_for_intent(intent: str | None) -> SimplicityCaps:
    """Density and optional extras driven by campaign intent."""
    kind = str(intent or "general_awareness").strip().lower()
    if kind in {"price_campaign", "sales_offer", "launch"}:
        return SimplicityCaps(
            max_supporting=2,
            allow_badges=True,
            allow_price_block=True,
            density_label="medium",
        )
    if kind in {"amenities"}:
        return SimplicityCaps(
            max_supporting=3,
            allow_badges=False,
            allow_icons=False,
            density_label="medium",
        )
    if kind in {"lifestyle", "location", "architecture", "investment"}:
        return SimplicityCaps(
            max_supporting=2,
            density_label="sparse",
        )
    if kind in {"educational", "project_brand", "general_awareness", "event"}:
        return SimplicityCaps(
            max_supporting=1,
            density_label="sparse",
        )
    return SimplicityCaps()


def apply_simplicity_caps(
    *,
    supporting_messages: list[Any],
    caps: SimplicityCaps,
    include_price_block: bool = False,
) -> dict[str, Any]:
    """Clamp supporting messages and report allowed element budget."""
    cleaned: list[str] = []
    for item in supporting_messages or []:
        s = str(item).strip() if item is not None else ""
        if s and s not in cleaned:
            cleaned.append(s)
        if len(cleaned) >= caps.max_supporting:
            break
    return {
        "supporting_messages": cleaned,
        "max_headlines": caps.max_headlines,
        "max_supporting": caps.max_supporting,
        "max_cta": caps.max_cta,
        "max_logos": caps.max_logos,
        "allow_badges": caps.allow_badges and include_price_block,
        "allow_icons": caps.allow_icons,
        "allow_price_block": caps.allow_price_block and include_price_block,
        "density": caps.density_label,
        "principles": list(caps.principles),
        "element_budget": {
            "headline": caps.max_headlines,
            "supporting": len(cleaned),
            "cta": caps.max_cta,
            "logo": caps.max_logos,
            "price_block": 1 if (caps.allow_price_block and include_price_block) else 0,
            "badges": 1 if (caps.allow_badges and include_price_block) else 0,
            "icons": 0,
        },
    }
