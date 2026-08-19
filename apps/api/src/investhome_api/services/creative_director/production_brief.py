"""Production Brief — CD Campaign Context → image provider instructions."""

from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_production_brief(
    *,
    ctx: dict[str, Any],
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any],
    pricing: dict[str, Any],
    texts: dict[str, str],
    approved_claims: list[Any],
    blocked_claims: list[Any],
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    language: str,
    aspect_ratio: str,
    format_preset: str,
    art_direction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured production brief for AI image providers (finished-ad mode)."""
    presentation = _as_dict(pricing.get("price_presentation"))
    selected_assets = _as_list(ctx.get("selected_assets"))
    if interior_meta and not any(
        isinstance(a, dict) and a.get("asset_id") == interior_meta.get("asset_id") for a in selected_assets
    ):
        selected_assets = [interior_meta, *selected_assets]
    brand_assets = [logo_meta] if logo_meta else []

    return {
        "objective": strategy.get("objective") or campaign_copy.get("objective"),
        "big_idea": campaign_copy.get("big_idea") or strategy.get("big_idea") or strategy.get("concept"),
        "hero": texts.get("hero") or campaign_copy.get("hero_message") or strategy.get("hero_message"),
        "sales_hook": texts.get("sales_hook") or campaign_copy.get("sales_hook") or strategy.get("sales_hook"),
        "offer": texts.get("offer")
        or campaign_copy.get("offer")
        or strategy.get("offer")
        or presentation.get("copy"),
        "supporting": _as_list(
            campaign_copy.get("supporting_messages") or strategy.get("supporting_messages")
        ),
        "cta": texts.get("cta") or campaign_copy.get("cta") or strategy.get("cta"),
        "commercial_priority": _as_list((art_direction or {}).get("commercial_priority")),
        "visual_hierarchy": _as_list((art_direction or {}).get("visual_hierarchy")),
        "visual_direction": strategy.get("visual_direction") or campaign_copy.get("visual_direction"),
        "brand_direction": {
            "tone": strategy.get("tone"),
            "color_direction": strategy.get("color_direction"),
            "typography_direction": strategy.get("typography_direction"),
            "composition_direction": strategy.get("composition_direction"),
        },
        "selected_assets": selected_assets,
        "brand_assets": brand_assets,
        "approved_claims": list(approved_claims),
        "forbidden_claims": list(blocked_claims),
        "language": language,
        "format": f"Instagram {aspect_ratio}" if aspect_ratio == "4:5" else f"Social {aspect_ratio}",
        "format_preset": format_preset,
        "aspect_ratio": aspect_ratio,
        "final_copy": {
            "eyebrow": texts.get("eyebrow"),
            "headline": texts.get("headline"),
            "supporting": texts.get("supporting"),
            "list_price": texts.get("list_price"),
            "offer_price": texts.get("offer_price"),
            "value_badge": texts.get("value_badge"),
            "unit": texts.get("unit"),
            "price_hierarchy": texts.get("price_hierarchy"),
            "cta": texts.get("cta"),
        },
        "asset_lock": {
            "interior_asset_id": interior_meta.get("asset_id"),
            "interior_filename": interior_meta.get("filename"),
            "logo_asset_id": logo_meta.get("asset_id"),
            "logo_filename": logo_meta.get("filename"),
            "interior_architecture_locked": True,
        },
        "campaign_mode": texts.get("campaign_mode"),
    }


def render_finished_ad_production_prompt(
    *,
    production_brief: dict[str, Any],
    art_direction: dict[str, Any] | None = None,
    original_brief: str,
    lifestyle: bool = False,
) -> str:
    """Comprehensive art direction for GPT Image finished-ad output (text + logo in-image)."""
    final = _as_dict(production_brief.get("final_copy"))
    approved = production_brief.get("approved_claims") or []
    forbidden = production_brief.get("forbidden_claims") or []
    asset_lock = _as_dict(production_brief.get("asset_lock"))
    art = art_direction or {}

    approved_lines = [
        f"- {c.get('key')}: {c.get('display')}"
        for c in approved
        if isinstance(c, dict) and c.get("display")
    ]
    forbidden_lines = [
        f"- {c.get('key') or c.get('fact_key')}: ineligible"
        for c in forbidden
        if isinstance(c, dict)
    ]

    lines = [
        f"FINISHED PROFESSIONAL INSTAGRAM AD — {production_brief.get('format') or '4:5'} — "
        f"LANGUAGE: {production_brief.get('language') or 'tr'}.",
        "Deliver a publishable, flattened social advertisement — typography, price hierarchy, CTA, and brand lockups "
        "integrated in the composition (not a blank background for later overlay).",
        "",
        "CREATIVE DIRECTOR PRODUCTION BRIEF:",
        f"- Objective: {production_brief.get('objective')}",
        f"- Big Idea: {production_brief.get('big_idea')}",
        f"- Hero: {production_brief.get('hero')}",
        f"- Sales Hook: {production_brief.get('sales_hook')}",
        f"- Offer: {production_brief.get('offer')}",
        f"- Supporting: {'; '.join(str(x) for x in (production_brief.get('supporting') or [])[:4])}",
        f"- CTA: {production_brief.get('cta')}",
        "",
        "COMMERCIAL PRIORITY (visual hierarchy):",
        *[f"  {i + 1}. {item}" for i, item in enumerate(production_brief.get("commercial_priority") or [])],
        "",
        "VISUAL HIERARCHY:",
        *[f"  - {item}" for item in (production_brief.get("visual_hierarchy") or [])],
        "",
        f"VISUAL DIRECTION: {production_brief.get('visual_direction')}",
        f"BRAND / TONE: {_as_dict(production_brief.get('brand_direction')).get('tone')}",
        "",
        "FINAL COPY TO RENDER (exact facts — Turkish if language is tr):",
        f"- Eyebrow: {final.get('eyebrow')}",
        f"- Headline: {final.get('headline')}",
        f"- Supporting: {final.get('supporting')}",
        f"- CTA: {final.get('cta')}",
    ]
    if not lifestyle:
        lines.extend(
            [
                f"- List price (secondary / strikethrough): {final.get('list_price')}",
                f"- Offer price (dominant): {final.get('offer_price')}",
                f"- Value badge: {final.get('value_badge')}",
                f"- Unit: {final.get('unit')}",
            ]
        )
    lines.extend(
        [
            "",
            "APPROVED CLAIMS ONLY:",
            *(approved_lines or ["- (none listed)"]),
            "",
            "FORBIDDEN / BLOCKED CLAIMS (never render):",
            *(forbidden_lines or ["- (none)"]),
            "",
            "PROJECT ASSET LOCK:",
            f"- Base photograph: {asset_lock.get('interior_filename')} (asset {asset_lock.get('interior_asset_id')}).",
            "  Preserve interior architecture, room geometry, windows, furniture layout, materials — do NOT redesign.",
            f"- Project logo: {asset_lock.get('logo_filename')} (asset {asset_lock.get('logo_asset_id')}).",
            "  Composite the real logo mark from supplied reference — never invent a fake wordmark.",
            "  If SVG cannot embed cleanly, place an honest rasterized logo lockup without duplicating text elsewhere.",
            "",
            "QUALITY BAR:",
            "- Premium luxury real-estate campaign, strong sales message, clear CTA, no duplicate logo/text.",
            "- No invented project info, ROI, yield, rent, or extra prices.",
            "- Professional art direction: modern, editorial, high contrast readability.",
            "",
            "ART DIRECTION PLAN:",
            f"- Primary message: {art.get('primary_visual_message')}",
            f"- First notice: {art.get('first_notice')}",
            f"- Second notice: {art.get('second_notice')}",
            "",
            "ORIGINAL USER BRIEF:",
            original_brief.strip(),
        ]
    )
    return "\n".join(lines)
