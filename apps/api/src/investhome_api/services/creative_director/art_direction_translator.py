"""Advertising Art Direction Translator — CD Campaign Context → GPT Image visual plan.

Converts Creative Director strategy into a senior art director VISUAL COMMUNICATION
PLAN. No hardcoded layout coordinates — GPT Image gets creative freedom with clear
commercial hierarchy, grouping, and asset lock.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _norm(text: str) -> str:
    return (text or "").strip().lower()


@dataclass
class ArtDirectionPlan:
    """Structured visual communication plan — not pixel coordinates."""

    primary_visual_message: str
    secondary_message: str
    commercial_priority: list[str] = field(default_factory=list)
    visual_hierarchy: list[str] = field(default_factory=list)
    sales_hierarchy: list[str] = field(default_factory=list)
    price_hierarchy: dict[str, str] = field(default_factory=dict)
    emphasis_strategy: list[dict[str, str]] = field(default_factory=list)
    typography_hierarchy: list[str] = field(default_factory=list)
    information_groups: list[dict[str, Any]] = field(default_factory=list)
    cta_prominence: str = ""
    badge_callout_opportunity: str = ""
    contrast_strategy: str = ""
    negative_space_usage: str = ""
    image_text_balance: str = ""
    brand_presence: str = ""
    visual_storytelling: str = ""
    decoration_rule: str = ""
    asset_lock: dict[str, Any] = field(default_factory=dict)
    emphasis_words: list[str] = field(default_factory=list)
    first_notice: str = ""
    second_notice: str = ""
    language: str = "tr"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Priority signal weights — derived from CD fields, not hardcoded campaign order.
_PRIORITY_SIGNALS: dict[str, tuple[str, ...]] = {
    "price_hook": (
        "price",
        "launch price",
        "lansman",
        "discount",
        "advantage",
        "%",
        "400",
        "300",
        "offer",
        "fiyat",
    ),
    "creative_idea": (
        "history",
        "modern",
        "heritage",
        "tarihi",
        "modernity",
        "big idea",
        "concept",
        "character",
        "şık",
        "elegance",
    ),
    "product": ("unit", "204", "launch", "lansman", "opportunity", "fırsat", "home", "living"),
    "value": ("value", "advantage", "avantaj", "proof", "investment", "yatırım"),
    "cta": ("cta", "explore", "detay", "incele", "schedule", "viewing", "action"),
    "brand": ("temple", "investhome", "logo", "brand", "marka"),
}


def _score_priority_signals(text: str) -> dict[str, int]:
    hay = _norm(text)
    scores: dict[str, int] = {key: 0 for key in _PRIORITY_SIGNALS}
    for key, tokens in _PRIORITY_SIGNALS.items():
        for tok in tokens:
            if tok in hay:
                scores[key] += 1
    return scores


def derive_commercial_priority(
    *,
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any],
    pricing: dict[str, Any],
    texts: dict[str, str],
) -> list[str]:
    """Derive commercial priority order from CD decisions — not a fixed template."""
    presentation = _as_dict(pricing.get("price_presentation"))
    emphasis = _as_list(campaign_copy.get("emphasis") or strategy.get("emphasis"))
    blob_parts = [
        str(strategy.get("first_2_seconds") or ""),
        str(strategy.get("sales_hook") or campaign_copy.get("sales_hook") or ""),
        str(strategy.get("value_proposition") or campaign_copy.get("value_proposition") or ""),
        str(strategy.get("big_idea") or campaign_copy.get("big_idea") or ""),
        str(strategy.get("hero_message") or campaign_copy.get("hero_message") or ""),
        str(presentation.get("copy") or ""),
        str(campaign_copy.get("offer") or strategy.get("offer") or ""),
        " ".join(str(e) for e in emphasis),
        texts.get("value_badge", ""),
        texts.get("sales_hook", ""),
    ]
    scores = _score_priority_signals(" ".join(blob_parts))

    # Price pair in brief strongly elevates price_hook unless CD explicitly leads elsewhere.
    if presentation.get("list") and presentation.get("offer"):
        scores["price_hook"] += 3
    if any("price" in _norm(str(e)) or "%" in str(e) for e in emphasis):
        scores["price_hook"] += 2
    if strategy.get("first_2_seconds"):
        first = _norm(str(strategy["first_2_seconds"]))
        for key, tokens in _PRIORITY_SIGNALS.items():
            for tok in tokens:
                if tok in first:
                    scores[key] += 2

    labels = {
        "price_hook": "price hook / launch offer",
        "creative_idea": "creative idea / brand story",
        "product": "product / unit opportunity",
        "value": "value proof / advantage",
        "cta": "call to action",
        "brand": "brand presence",
    }
    ranked = sorted(scores.items(), key=lambda item: (-item[1], list(labels).index(item[0])))
    result = [labels[key] for key, score in ranked if score > 0]
    if not result:
        result = list(labels.values())
    for tail in ("call to action", "brand presence"):
        if tail not in result:
            result.append(tail)
    return result


def build_information_groups(
    *,
    texts: dict[str, str],
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any],
    pricing: dict[str, Any],
) -> list[dict[str, Any]]:
    """Group related sales messages — one story, not scattered corners."""
    presentation = _as_dict(pricing.get("price_presentation"))
    unit = texts.get("unit") or "Unit 204"
    list_price = texts.get("list_price") or str(presentation.get("list") or "")
    offer_price = texts.get("offer_price") or str(presentation.get("offer") or "")
    discount = _as_dict(presentation.get("discount") or pricing.get("discount"))
    discount_display = texts.get("value_badge") or str(discount.get("display") or "~25%")

    launch_group = {
        "name": "launch_opportunity",
        "label": "Launch opportunity cluster",
        "elements": [unit, texts.get("eyebrow") or f"{unit} Lansman Fırsatı"],
        "relationship": "Unit identity and launch framing belong together — one visual cluster.",
    }
    price_group = {
        "name": "price_story",
        "label": "Price dramatization cluster",
        "elements": [list_price, offer_price, discount_display],
        "relationship": (
            f"Old price {list_price} → dominant new {offer_price} with {discount_display} advantage — "
            "one sales story, not separated to random corners."
        ),
    }
    concept_group = {
        "name": "creative_concept",
        "label": "Creative concept cluster",
        "elements": [
            texts.get("headline") or campaign_copy.get("big_idea") or strategy.get("big_idea"),
            texts.get("hero") or campaign_copy.get("hero_message"),
        ],
        "relationship": "Headline and hero express the same Modern + Şık + Tarihi idea — keep proximate.",
    }
    action_group = {
        "name": "action",
        "label": "CTA cluster",
        "elements": [texts.get("cta") or "Detayları İncele"],
        "relationship": "Real ad CTA — button, pill, outline, or text+arrow — visible and actionable.",
    }
    return [launch_group, price_group, concept_group, action_group]


def _build_emphasis_strategy(emphasis: list[Any]) -> list[dict[str, str]]:
    """Varied treatment for CD emphasis words — not uniform styling."""
    treatments = [
        {"color": "gold", "weight": "bold", "scale": "large"},
        {"color": "navy", "weight": "semibold", "scale": "medium"},
        {"color": "ivory-on-navy", "weight": "medium", "scale": "medium"},
        {"color": "gold-accent", "weight": "bold", "scale": "small-badge"},
    ]
    words = [str(w).strip() for w in emphasis if str(w).strip()]
    out: list[dict[str, str]] = []
    for idx, word in enumerate(words):
        style = treatments[idx % len(treatments)]
        out.append(
            {
                "word": word,
                "treatment": f"{style['weight']} {style['scale']} in {style['color']}",
                "note": "Distinct from adjacent emphasis words — avoid rendering all the same.",
            }
        )
    return out


def _price_is_primary_hook(commercial_priority: list[str]) -> bool:
    return bool(commercial_priority) and "price hook" in commercial_priority[0].lower()


def translate_campaign_art_direction(
    *,
    ctx: dict[str, Any],
    texts: dict[str, str],
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    language: str,
) -> ArtDirectionPlan:
    """Load CD brief fields from Campaign Context and produce ArtDirectionPlan."""
    strategy = _as_dict(ctx.get("cd_strategy"))
    campaign_copy = _as_dict(ctx.get("campaign_copy"))
    pricing = _as_dict(ctx.get("pricing"))
    emphasis = _as_list(campaign_copy.get("emphasis") or strategy.get("emphasis"))
    presentation = _as_dict(pricing.get("price_presentation"))

    commercial_priority = derive_commercial_priority(
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        texts=texts,
    )
    info_groups = build_information_groups(
        texts=texts,
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
    )
    emphasis_strategy = _build_emphasis_strategy(emphasis)
    price_primary = _price_is_primary_hook(commercial_priority)

    list_price = texts.get("list_price") or str(presentation.get("list") or "$400,000")
    offer_price = texts.get("offer_price") or str(presentation.get("offer") or "$300,000")
    discount_display = texts.get("value_badge") or str(
        _as_dict(presentation.get("discount")).get("display") or "~25%"
    )

    first_notice = (
        f"{offer_price} launch price with {list_price} struck through"
        if price_primary
        else texts.get("headline") or str(campaign_copy.get("big_idea") or "")
    )
    second_notice = (
        texts.get("headline") or f"{texts.get('unit')} launch opportunity"
        if price_primary
        else f"{offer_price} → {discount_display} price advantage"
    )

    visual_hierarchy = [
        f"1 — FIRST GLANCE: {first_notice}",
        f"2 — SECOND READ: {second_notice}",
        f"3 — PRODUCT: {texts.get('unit')} at The Temple",
        f"4 — VALUE: {discount_display}",
        f"5 — ACTION: {texts.get('cta')}",
        f"6 — BRAND: Temple logo (OS-composited, never AI-drawn)",
    ]

    sales_hierarchy = [
        item.replace("price hook / launch offer", "price dramatization")
        for item in commercial_priority
    ]

    price_hierarchy = {
        "secondary": list_price,
        "primary": offer_price,
        "advantage": discount_display,
        "dramatization": (
            "Strikethrough old price, dominant new price, size contrast, optional badge/callout — "
            "understood at a glance like a real ad, not a catalog line."
            if price_primary
            else "Price visible but subordinate to creative story — still clear hierarchy."
        ),
    }

    cta_prominence = (
        f"Real ad CTA: '{texts.get('cta')}' as button, pill, outline, or text+arrow — "
        "large enough to invite tap; not tiny decorative footer text."
    )

    return ArtDirectionPlan(
        primary_visual_message=first_notice,
        secondary_message=second_notice,
        commercial_priority=commercial_priority,
        visual_hierarchy=visual_hierarchy,
        sales_hierarchy=sales_hierarchy,
        price_hierarchy=price_hierarchy,
        emphasis_strategy=emphasis_strategy,
        typography_hierarchy=[
            "Headline: largest serif/editorial — Modern. Şık. Tarihi. rhythm",
            "Price primary: bold numeral treatment — dominant over list price",
            "Price secondary: smaller, strikethrough or muted",
            "Eyebrow/supporting: medium sans — unit + launch context",
            "CTA: high-contrast actionable weight",
            "Brand: quiet but visible logo zone",
        ],
        information_groups=info_groups,
        cta_prominence=cta_prominence,
        badge_callout_opportunity=(
            f"Optional launch badge for {discount_display} near price cluster — only if it strengthens the offer."
        ),
        contrast_strategy="Navy / gold / ivory luxury RE palette — high contrast for price and CTA against interior warmth",
        negative_space_usage=(
            "Conscious breath around headline, price cluster, and CTA — premium composition, "
            "not meaningless empty canvas or random decorative gaps."
        ),
        image_text_balance=(
            "Locked living-room interior carries atmosphere; type and price zones get composed air — "
            "roughly 55–65% visual / 35–45% message space, flexible not fixed panels."
        ),
        brand_presence="The Temple project logo composited by OS — upper area, visible, never AI-generated",
        visual_storytelling=(
            str(strategy.get("visual_direction") or campaign_copy.get("visual_direction") or "")
            or "Historic character meets modern living inside the locked interior render."
        ),
        decoration_rule=(
            "Decoration only if it serves campaign: no random building sketch, map pin, long gold line, "
            "or watermark unless it strengthens sales or brand story."
        ),
        asset_lock={
            "interior_asset_id": str(interior_meta.get("asset_id") or ""),
            "interior_filename": interior_meta.get("filename"),
            "logo_asset_id": str(logo_meta.get("asset_id") or ""),
            "logo_filename": logo_meta.get("filename"),
            "must_not_invent_interior": True,
            "must_not_draw_logo": True,
        },
        emphasis_words=[str(w) for w in emphasis],
        first_notice=first_notice,
        second_notice=second_notice,
        language=language,
    )


def render_gpt_image_art_direction_prompt(
    plan: ArtDirectionPlan,
    *,
    texts: dict[str, str],
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    original_brief: str,
    aspect_ratio: str = "4:5",
) -> str:
    """Rich natural-language GPT Image prompt — no pixel coords or fixed templates."""
    emphasis_lines = [
        f"  - '{row['word']}': {row['treatment']}" for row in plan.emphasis_strategy
    ] or ["  - (none specified)"]
    group_lines = []
    for grp in plan.information_groups:
        group_lines.append(f"- {grp['label']}: {', '.join(str(e) for e in grp['elements'] if e)}")
        group_lines.append(f"  Relationship: {grp['relationship']}")

    lines = [
        f"MASTER Instagram {aspect_ratio} feed ad BACKGROUND for The Temple — PROJECT MODE edit.",
        f"LANGUAGE atmosphere: {plan.language} campaign (OS typesets exact Turkish copy after).",
        "",
        "=== ADVERTISING ART DIRECTION (senior art director plan — creative freedom, no fixed template) ===",
        "",
        "WHAT MUST BE NOTICED FIRST:",
        f"  {plan.first_notice}",
        "",
        "WHAT MUST BE NOTICED SECOND:",
        f"  {plan.second_notice}",
        "",
        "COMMERCIAL PRIORITY (derived from Creative Director — drives visual hierarchy):",
        *[f"  {idx + 1}. {item}" for idx, item in enumerate(plan.commercial_priority)],
        "",
        "VISUAL HIERARCHY:",
        *[f"  {item}" for item in plan.visual_hierarchy],
        "",
        "SALES HIERARCHY:",
        *[f"  {idx + 1}. {item}" for idx, item in enumerate(plan.sales_hierarchy)],
        "",
        "PRICE HIERARCHY:",
        f"  Secondary (struck/muted): {plan.price_hierarchy.get('secondary')}",
        f"  Primary (dominant): {plan.price_hierarchy.get('primary')}",
        f"  Advantage badge: {plan.price_hierarchy.get('advantage')}",
        f"  Dramatization: {plan.price_hierarchy.get('dramatization')}",
        "",
        "EMPHASIS WORDS (varied treatment — do NOT render all the same style):",
        *emphasis_lines,
        "",
        "INFORMATION GROUPING (keep clusters together — one sales story):",
        *group_lines,
        "",
        f"CTA PROMINENCE: {plan.cta_prominence}",
        f"BADGE/CALLOUT: {plan.badge_callout_opportunity}",
        "",
        "TYPOGRAPHY HIERARCHY (OS typesets — compose contrast/air only):",
        *[f"  - {item}" for item in plan.typography_hierarchy],
        "",
        f"CONTRAST STRATEGY: {plan.contrast_strategy}",
        f"NEGATIVE SPACE: {plan.negative_space_usage}",
        f"IMAGE/TEXT BALANCE: {plan.image_text_balance}",
        f"BRAND PRESENCE: {plan.brand_presence}",
        f"VISUAL STORYTELLING: {plan.visual_storytelling}",
        f"DECORATION RULE: {plan.decoration_rule}",
        "",
        "WHAT IS BEING SOLD:",
        f"  {texts.get('unit')} launch at The Temple — {texts.get('headline')}",
        "",
        "WHY NOW:",
        f"  {texts.get('value_badge')} — {texts.get('eyebrow')}",
        "",
        "WHAT NUMBER MATTERS:",
        f"  {texts.get('offer_price')} (primary) from {texts.get('list_price')} — {texts.get('value_badge')}",
        "",
        "ACTION:",
        f"  {texts.get('cta')}",
        "",
        "PROJECT ASSET LOCK — WHAT STAYS REAL:",
        f"  Interior: {interior_meta.get('filename')} (asset {interior_meta.get('asset_id')})",
        "  Preserve room geometry, windows, furniture, materials — do NOT invent another living room.",
        f"  Logo: {logo_meta.get('filename')} (asset {logo_meta.get('asset_id')}) — OS composites; never redraw.",
        "",
        "WHAT NOT TO INVENT:",
        "  No AI interior, no AI logo, no extra prices, no ROI/yield/rent, no landmarks, no map pins, "
        "no random sketches, no fixed side-panel or bottom-band template.",
        "",
        "OS FINAL COPY PREVIEW (do NOT rasterize — leave composed air/contrast):",
        f"  Eyebrow: {texts.get('eyebrow')}",
        f"  Headline: {texts.get('headline')}",
        f"  Supporting: {texts.get('supporting')}",
        f"  Price line: {texts.get('price_hierarchy')} · {texts.get('value_badge')}",
        f"  CTA: {texts.get('cta')}",
        "",
        "ORIGINAL CAMPAIGN BRIEF (context):",
        original_brief.strip(),
    ]
    return "\n".join(lines)


def append_architecture_lock_to_prompt(prompt: str, *, interior_lock: bool = True) -> str:
    """Append standard architecture lock lines for GPT Image edits."""
    lock_lines = [
        "",
        "ARCHITECTURE / ASSET LOCK:",
        "- Edit the supplied interior photograph only — graphic atmosphere around it.",
        "- Do NOT rasterize logos, prices, CTAs, or headlines into pixels.",
        "- InvestHome OS Final Composition Layer typesets real copy and logos after generation.",
    ]
    if interior_lock:
        lock_lines.insert(
            2,
            "- Preserve interior architecture, furniture layout, windows, and materials exactly.",
        )
    return prompt + "\n".join(lock_lines)
