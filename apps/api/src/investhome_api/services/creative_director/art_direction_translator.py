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
    "lifestyle": (
        "sığınak",
        "sanctuary",
        "huzur",
        "calm",
        "sakin",
        "zarif",
        "interior",
        "iç mekan",
        "living",
        "lifestyle",
        "yaşam",
    ),
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
        "lifestyle": "lifestyle / interior experience",
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
    lifestyle: bool = False,
) -> list[dict[str, Any]]:
    """Group related sales messages — one story, not scattered corners."""
    if lifestyle:
        support = _as_list(
            campaign_copy.get("supporting_messages") or strategy.get("supporting_messages")
        )
        callouts = [str(x).strip() for x in support[:3] if str(x).strip()]
        concept_group = {
            "name": "hero_concept",
            "label": "Hero concept cluster",
            "elements": [
                texts.get("headline") or campaign_copy.get("big_idea") or strategy.get("big_idea"),
                texts.get("hero") or campaign_copy.get("hero_message"),
            ],
            "relationship": (
                "Big idea and hero express calm city-center sanctuary — keep proximate, not separated."
            ),
        }
        feature_group = {
            "name": "feature_callouts",
            "label": "Supporting feature callouts",
            "elements": callouts,
            "relationship": (
                "Up to 3 short verified lifestyle features — grouped as callouts, not random corners."
            ),
        }
        action_group = {
            "name": "action",
            "label": "CTA cluster",
            "elements": [texts.get("cta") or "Detayları Keşfet"],
            "relationship": "Real ad CTA — button, pill, outline, or text+arrow — visible and actionable.",
        }
        return [concept_group, feature_group, action_group]

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
    lifestyle: bool = False,
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
    if lifestyle:
        commercial_priority = [
            item
            for item in commercial_priority
            if "price hook" not in item.lower() and "unit opportunity" not in item.lower()
        ]
        if not commercial_priority:
            commercial_priority = [
                "lifestyle / interior experience",
                "creative idea / brand story",
                "call to action",
                "brand presence",
            ]

    info_groups = build_information_groups(
        texts=texts,
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        lifestyle=lifestyle,
    )
    emphasis_strategy = _build_emphasis_strategy(emphasis)
    price_primary = _price_is_primary_hook(commercial_priority) and not lifestyle

    list_price = texts.get("list_price") or str(presentation.get("list") or "$400,000")
    offer_price = texts.get("offer_price") or str(presentation.get("offer") or "$300,000")
    discount_display = texts.get("value_badge") or str(
        _as_dict(presentation.get("discount")).get("display") or "~25%"
    )

    support_callouts = [
        x.strip()
        for x in str(texts.get("supporting_callouts") or "").split("|")
        if x.strip()
    ]

    if lifestyle:
        first_notice = texts.get("headline") or str(campaign_copy.get("big_idea") or "")
        second_notice = (
            texts.get("sales_hook")
            or str(strategy.get("first_2_seconds") or "")
            or texts.get("hero")
            or ""
        )
        visual_hierarchy = [
            f"1 — FIRST GLANCE: {first_notice}",
            f"2 — SECOND READ: {second_notice}",
            f"3 — FEATURES: {'; '.join(support_callouts) if support_callouts else texts.get('supporting', '')}",
            f"4 — ACTION: {texts.get('cta')}",
            f"5 — BRAND: Temple logo (OS-composited, never AI-drawn)",
        ]
        price_hierarchy = {
            "secondary": "",
            "primary": "",
            "advantage": "",
            "dramatization": "No price dramatization — lifestyle interior quality and calm living experience.",
        }
        typography_hierarchy = [
            "Headline: largest editorial — sanctuary / calm city-center living",
            "Hero/sales hook: medium weight supporting the headline",
            "Feature callouts: 3 short lines — varied weight, not uniform",
            "CTA: high-contrast actionable weight",
            "Brand: quiet but visible logo zone",
        ]
        contrast_strategy = (
            "Warm interior palette with navy/ivory type — high contrast for headline and CTA, "
            "not price panels"
        )
        image_text_balance = (
            "Locked living-room interior carries atmosphere; type zones get composed air — "
            "roughly 60% visual / 40% message space, flexible not fixed panels."
        )
        visual_storytelling = (
            str(strategy.get("visual_direction") or campaign_copy.get("visual_direction") or "")
            or "Calm, elegant sanctuary living inside the locked interior render."
        )
    else:
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
        typography_hierarchy = [
            "Headline: largest serif/editorial — Modern. Şık. Tarihi. rhythm",
            "Price primary: bold numeral treatment — dominant over list price",
            "Price secondary: smaller, strikethrough or muted",
            "Eyebrow/supporting: medium sans — unit + launch context",
            "CTA: high-contrast actionable weight",
            "Brand: quiet but visible logo zone",
        ]
        contrast_strategy = (
            "Navy / gold / ivory luxury RE palette — high contrast for price and CTA against interior warmth"
        )
        image_text_balance = (
            "Locked living-room interior carries atmosphere; type and price zones get composed air — "
            "roughly 55–65% visual / 35–45% message space, flexible not fixed panels."
        )
        visual_storytelling = (
            str(strategy.get("visual_direction") or campaign_copy.get("visual_direction") or "")
            or "Historic character meets modern living inside the locked interior render."
        )

    sales_hierarchy = [
        item.replace("price hook / launch offer", "price dramatization")
        for item in commercial_priority
    ]

    cta_prominence = (
        "CTA zone (OS typesets — do NOT draw text): reserve high-contrast actionable area for "
        f"'{texts.get('cta')}' — button/pill air only, no rasterized CTA."
    )

    return ArtDirectionPlan(
        primary_visual_message=first_notice,
        secondary_message=second_notice,
        commercial_priority=commercial_priority,
        visual_hierarchy=visual_hierarchy,
        sales_hierarchy=sales_hierarchy,
        price_hierarchy=price_hierarchy,
        emphasis_strategy=emphasis_strategy,
        typography_hierarchy=typography_hierarchy,
        information_groups=info_groups,
        cta_prominence=cta_prominence,
        badge_callout_opportunity=(
            "Optional feature badges near callout cluster — only if they strengthen lifestyle story."
            if lifestyle
            else f"Optional launch badge for {discount_display} near price cluster — only if it strengthens the offer."
        ),
        contrast_strategy=contrast_strategy,
        negative_space_usage=(
            "Conscious breath around headline, feature callouts, and CTA — premium composition, "
            "not meaningless empty canvas or random decorative gaps."
            if lifestyle
            else "Conscious breath around headline, price cluster, and CTA — premium composition, "
            "not meaningless empty canvas or random decorative gaps."
        ),
        image_text_balance=image_text_balance,
        brand_presence="The Temple project logo zone — upper area, visible air only; OS composites real SVG, never AI-generated",
        visual_storytelling=visual_storytelling,
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

    lifestyle = texts.get("campaign_mode") == "lifestyle" or not str(
        plan.price_hierarchy.get("primary") or ""
    ).strip()

    lines = [
        f"MASTER Instagram {aspect_ratio} feed ad CLEAN BACKGROUND for The Temple — PROJECT MODE edit.",
        f"LANGUAGE atmosphere: {plan.language} campaign (InvestHome OS typesets exact Turkish copy after — GPT draws ZERO text).",
        "",
        "=== GPT IMAGE CLEAN CANVAS LOCK (mandatory — zero tolerance) ===",
        "NO TEXT, NO LETTERS, NO NUMBERS, NO TYPOGRAPHY, NO CAPTIONS, NO LABELS, NO WATERMARKS.",
        "NO LOGOS, NO BRAND MARKS, NO BRAND NAMES, NO MONOGRAMS, NO LOGO-LIKE SYMBOLS.",
        "Output visual composition / atmosphere / background treatment ONLY.",
        "Zone hints below describe hierarchy and contrast air — NOT instructions to paint words or marks.",
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
    ]
    if lifestyle:
        lines.extend(
            [
                "PRICE HIERARCHY:",
                f"  {plan.price_hierarchy.get('dramatization')}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "PRICE HIERARCHY:",
                f"  Secondary (struck/muted): {plan.price_hierarchy.get('secondary')}",
                f"  Primary (dominant): {plan.price_hierarchy.get('primary')}",
                f"  Advantage badge: {plan.price_hierarchy.get('advantage')}",
                f"  Dramatization: {plan.price_hierarchy.get('dramatization')}",
                "",
            ]
        )
    lines.extend(
        [
        "EMPHASIS WORDS (OS varied treatment — compose contrast air only, do NOT typeset):",
        *emphasis_lines,
        "",
        "INFORMATION GROUPING (keep visual clusters together — OS typesets copy, GPT composes air):",
        *group_lines,
        "",
        f"CTA PROMINENCE: {plan.cta_prominence}",
        f"BADGE/CALLOUT: {plan.badge_callout_opportunity}",
        "",
        "TYPOGRAPHY ZONES (OS typesets — compose contrast/air only, do NOT rasterize):",
        *[f"  - {item}" for item in plan.typography_hierarchy],
        "",
        f"CONTRAST STRATEGY: {plan.contrast_strategy}",
        f"NEGATIVE SPACE: {plan.negative_space_usage}",
        f"IMAGE/TEXT BALANCE: {plan.image_text_balance}",
        f"BRAND ZONE (logo air only — OS composites real mark): {plan.brand_presence}",
        f"VISUAL STORYTELLING: {plan.visual_storytelling}",
        f"DECORATION RULE: {plan.decoration_rule}",
        "",
        ]
    )
    if lifestyle:
        lines.extend(
            [
                "WHAT IS BEING SOLD (composition mood — do NOT typeset):",
                f"  The Temple interior lifestyle — calm sanctuary atmosphere around locked interior.",
                "",
                "WHY NOW (mood only — OS typesets):",
                f"  {texts.get('sales_hook')} — {texts.get('eyebrow')}",
                "",
                "FEATURE CALLOUT ZONE (OS typesets — reserve grouped air):",
                f"  {texts.get('supporting')}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "WHAT IS BEING SOLD (composition mood — do NOT typeset):",
                f"  {texts.get('unit')} launch at The Temple — premium editorial atmosphere.",
                "",
                "WHY NOW (mood only — OS typesets):",
                f"  {texts.get('value_badge')} — {texts.get('eyebrow')}",
                "",
                "PRICE ZONE (OS typesets — reserve dramatization air, do NOT paint numbers):",
                f"  {texts.get('offer_price')} (primary) from {texts.get('list_price')} — {texts.get('value_badge')}",
                "",
            ]
        )
    lines.extend(
        [
        "CTA ZONE (OS typesets — reserve actionable contrast air):",
        f"  {texts.get('cta')}",
        "",
        "PROJECT ASSET LOCK — WHAT STAYS REAL:",
        f"  Interior: {interior_meta.get('filename')} (asset {interior_meta.get('asset_id')})",
        "  Preserve room geometry, windows, furniture, materials — do NOT invent another living room.",
        f"  Logo: {logo_meta.get('filename')} (asset {logo_meta.get('asset_id')}) — OS composites real SVG; never redraw or fake.",
        "",
        "WHAT NOT TO INVENT OR RASTERIZE:",
        "  No AI interior, no AI logo, no fake brand marks, no painted text, no extra prices, "
        "no ROI/yield/rent, no landmarks, no map pins, no random sketches, no fixed side-panel or bottom-band template.",
        "",
        "COMPOSITION ZONES (OS typesets — reserve contrast/air, do NOT rasterize copy):",
        f"  Headline zone air for: {texts.get('headline')}",
        f"  Supporting zone air for: {texts.get('supporting')}",
        f"  CTA zone air for: {texts.get('cta')}",
        ]
    )
    if not lifestyle:
        lines.append(f"  Price zone air for: {texts.get('price_hierarchy')} · {texts.get('value_badge')}")
    lines.extend(
        [
        "",
        "ORIGINAL CAMPAIGN BRIEF (context):",
        original_brief.strip(),
        ]
    )
    return "\n".join(lines)


def append_architecture_lock_to_prompt(prompt: str, *, interior_lock: bool = True) -> str:
    """Append standard architecture + clean canvas lock lines for GPT Image edits."""
    lock_lines = [
        "",
        "GPT IMAGE CLEAN CANVAS LOCK (mandatory):",
        "- NO TEXT, NO LETTERS, NO NUMBERS, NO TYPOGRAPHY, NO CAPTIONS, NO LABELS, NO WATERMARKS.",
        "- NO LOGOS, NO BRAND MARKS, NO BRAND NAMES, NO MONOGRAMS, NO LOGO-LIKE SYMBOLS.",
        "- Output visual composition / atmosphere / background treatment ONLY.",
        "",
        "ARCHITECTURE / ASSET LOCK:",
        "- Edit the supplied interior photograph only — graphic atmosphere around it.",
        "- Do NOT rasterize logos, prices, CTAs, headlines, badges, or feature callouts into pixels.",
        "- InvestHome OS Final Composition Layer typesets real copy and the real Temple logo after generation.",
    ]
    if interior_lock:
        lock_lines.insert(
            2,
            "- Preserve interior architecture, furniture layout, windows, and materials exactly.",
        )
    return prompt + "\n".join(lock_lines)
