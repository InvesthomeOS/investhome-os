"""Production Brief — CD Campaign Context → image provider instructions."""

from __future__ import annotations

import re
from typing import Any

# Common English ad copy that must not leak into Turkish finished ads.
_EN_COPY_MARKERS = (
    "history meets",
    "explore details",
    "explore unit",
    "schedule a",
    "launch opportunity",
    "launch price advantage",
    "own a piece",
    "modern twist",
    "discover the",
    "prestigious",
    "learn more",
    "book now",
    "see the details",
    "claim launch",
    "exclusive launch",
    "perfect blend",
    "gateway to",
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_turkish_chars(text: str) -> bool:
    return any(ch in (text or "") for ch in "çÇğĞıİöÖşŞüÜ")


def looks_english_ad_copy(text: str | None) -> bool:
    """Heuristic: Latin slogan/CTA/headline without Turkish script markers."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _has_turkish_chars(raw):
        return False
    low = raw.lower()
    if any(m in low for m in _EN_COPY_MARKERS):
        return True
    # Multi-word Latin sentence without Turkish letters → treat as English leak.
    words = re.findall(r"[A-Za-z]{3,}", raw)
    return len(words) >= 2 and not re.search(r"[çğıöşüÇĞİÖŞÜ]", raw)


def lock_copy_to_language(text: str | None, *, language: str, fallback: str = "") -> str:
    """When language=tr, drop English user-facing strings."""
    raw = (text or "").strip()
    lang = (language or "tr").strip().lower() or "tr"
    if not lang.startswith("tr"):
        return raw
    if not raw:
        return fallback
    if looks_english_ad_copy(raw):
        return fallback
    return raw


def lock_supporting_messages(
    messages: list[Any],
    *,
    language: str,
    max_items: int = 3,
) -> list[str]:
    """Cap supporting messages and drop English leaks when language=tr."""
    out: list[str] = []
    for item in messages:
        s = str(item).strip() if item is not None else ""
        if not s:
            continue
        locked = lock_copy_to_language(s, language=language, fallback="")
        if locked and locked not in out:
            out.append(locked)
        if len(out) >= max_items:
            break
    return out[:max_items]


CREATIVE_SIMPLICITY_PRINCIPLES: tuple[str, ...] = (
    "Do not clutter the ad with unnecessary information.",
    "Use one main sales message + offer + at most 3 supporting messages + a single CTA.",
    "Keep the visual as visible as possible — let the photograph breathe.",
    "Avoid large bottom bands, unnecessary badges, and repeating price messages.",
)


def verify_logo_lock(logo_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Require a verified real project logo Asset ID before final production."""
    meta = _as_dict(logo_meta)
    asset_id = str(meta.get("asset_id") or meta.get("id") or "").strip()
    role = str(meta.get("role") or "").strip().lower()
    locked = bool(asset_id) and role in {"", "project_logo", "logo"}
    return {
        "logo_asset_id": asset_id or None,
        "logo_filename": meta.get("filename"),
        "logo_locked": bool(asset_id),
        "verified_project_logo": locked and bool(asset_id),
        "ai_must_not_draw_logo": True,
        "no_duplicate_logos": True,
        "status": "pass" if asset_id else "fail",
    }


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
    logo_lock = verify_logo_lock(logo_meta)

    supporting = lock_supporting_messages(
        _as_list(campaign_copy.get("supporting_messages") or strategy.get("supporting_messages")),
        language=language,
        max_items=3,
    )
    # Prefer language-locked final texts; never fall back to English CD leaks when lang=tr.
    hero = lock_copy_to_language(
        texts.get("hero") or campaign_copy.get("hero_message") or strategy.get("hero_message"),
        language=language,
        fallback=str(texts.get("hero") or ""),
    )
    sales_hook = lock_copy_to_language(
        texts.get("sales_hook") or campaign_copy.get("sales_hook") or strategy.get("sales_hook"),
        language=language,
        fallback=str(texts.get("sales_hook") or texts.get("eyebrow") or ""),
    )
    big_idea = lock_copy_to_language(
        campaign_copy.get("big_idea") or strategy.get("big_idea") or strategy.get("concept") or texts.get("big_idea"),
        language=language,
        fallback=str(texts.get("headline") or texts.get("big_idea") or ""),
    )
    offer = lock_copy_to_language(
        texts.get("offer")
        or campaign_copy.get("offer")
        or strategy.get("offer")
        or presentation.get("copy"),
        language=language,
        fallback=str(texts.get("offer") or texts.get("price_hierarchy") or ""),
    )
    cta = lock_copy_to_language(
        texts.get("cta") or campaign_copy.get("cta") or strategy.get("cta"),
        language=language,
        fallback=str(texts.get("cta") or "Detayları İncele"),
    )

    return {
        "objective": strategy.get("objective") or campaign_copy.get("objective"),
        "big_idea": big_idea,
        "hero": hero,
        "sales_hook": sales_hook,
        "offer": offer,
        "supporting": supporting,
        "cta": cta,
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
        "language_lock": (language or "tr").strip().lower().startswith("tr"),
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
            "logo_asset_id": logo_lock.get("logo_asset_id") or logo_meta.get("asset_id"),
            "logo_filename": logo_meta.get("filename"),
            "interior_architecture_locked": True,
            "logo_locked": bool(logo_lock.get("logo_locked")),
            "verified_project_logo": bool(logo_lock.get("verified_project_logo")),
            "ai_must_not_draw_logo": True,
            "no_duplicate_logos": True,
        },
        "logo_lock": logo_lock,
        "creative_simplicity": list(CREATIVE_SIMPLICITY_PRINCIPLES),
        "max_supporting_messages": 3,
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
    lang = str(production_brief.get("language") or "tr").strip().lower() or "tr"

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
    simplicity = _as_list(production_brief.get("creative_simplicity")) or list(
        CREATIVE_SIMPLICITY_PRINCIPLES
    )

    lines = [
        f"FINISHED PROFESSIONAL INSTAGRAM AD — {production_brief.get('format') or '4:5'} — "
        f"LANGUAGE: {lang}.",
        "Deliver a publishable, flattened social advertisement — typography, price hierarchy, CTA, and brand lockups "
        "integrated in the composition (not a blank background for later overlay).",
        "",
        "LANGUAGE LOCK:",
        f"- Campaign language is {lang}. All user-visible slogans, headlines, CTAs, and supporting lines MUST be {lang}.",
        "- Do not invent or render English slogans/headlines/CTAs when language is tr.",
        "",
        "CREATIVE DIRECTOR PRODUCTION BRIEF:",
        f"- Objective: {production_brief.get('objective')}",
        f"- Big Idea: {production_brief.get('big_idea')}",
        f"- Hero: {production_brief.get('hero')}",
        f"- Sales Hook: {production_brief.get('sales_hook')}",
        f"- Offer: {production_brief.get('offer')}",
        f"- Supporting (max 3): {'; '.join(str(x) for x in (production_brief.get('supporting') or [])[:3])}",
        f"- CTA: {production_brief.get('cta')}",
        "",
        "CREATIVE SIMPLICITY (quality principle — not a fixed layout):",
        *[f"  - {item}" for item in simplicity],
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
            f"- Project logo Asset ID (LOCKED): {asset_lock.get('logo_asset_id')} — file {asset_lock.get('logo_filename')}.",
            "  Composite the verified real logo mark from Drive/Media Library reference — never invent, redraw, or AI-generate a logo.",
            "  Never duplicate the logo. One project logo lockup only.",
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
