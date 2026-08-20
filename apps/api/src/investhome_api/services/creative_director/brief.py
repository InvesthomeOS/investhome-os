"""Creative Director LLM brief — strategy thinking only (no image generation)."""

from __future__ import annotations

import json
import re
from typing import Any

from investhome_api.services.project_assistant.llm_provider import (
    LLMProvider,
    LLMProviderConfigError,
    LLMProviderError,
    get_llm_provider,
)

CREATIVE_BRIEF_MARKER = "CREATIVE_BRIEF_JSON"

# Patterns that make RE ads sound like a generic listing brochure.
CLICHE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bdiscover the elegance\b",
        r"\bprestigious address\b",
        r"\bschedule a viewing\b",
        r"\bschedule a (private )?tour\b",
        r"\breserve a private tour\b",
        r"\bunparalleled luxury\b",
        r"\blucrative investment\b",
        r"\bmost sought[- ]after address\b",
        r"\bgateway to a sophisticated\b",
        r"\bexperience the perfect blend\b",
    )
)

_SYSTEM = """You are a senior advertising Creative Director for real-estate campaigns.
You invent campaign messaging. The user brief is raw material — not copy to polish.
Do NOT write a generic listing ad. Think like a real CD before writing a single line.

────────────────
CREATIVE THINKING (reason first, then write)
────────────────
Silently reason about:
1) commercial goal  2) what is being sold  3) why now
4) strongest sales hook  5) what to see in the first 2 seconds
6) which number truly matters  7) which words to emphasize
8) which project feature creates emotional value
9) supporting message  10) desired user action
Then invent a campaign concept (big idea) and message hierarchy.

────────────────
MESSAGE HIERARCHY (you decide; invent headline/CTA — user need not supply them)
────────────────
Return JSON with:
big_idea, objective, audience, concept, hero_message,
primary_message (ONE dominant message for this single ad),
supporting_messages (array; prefer 1–3 short lines; density by campaign intent),
emphasis (array of words to stress on the visual),
sales_hook, offer, price_presentation (how price should appear — you decide format),
value_proposition, proof_points (array), cta,
emotional_angle, commercial_priority (array ordered),
visual_direction, composition_direction, typography_direction,
color_direction, tone, formats (array),
required_assets (array of descriptions — no invented asset IDs),
required_project_data (array), recommended_outputs (array),
first_2_seconds (what the eye must catch),
thinking_notes (short: goal / hook / number that matters / emotional feature).

ONE AD = ONE PRIMARY MESSAGE. Do not fill every ad with every fact.
Price campaigns may lead with price; location with place; lifestyle with living feel.
Not every field must appear on the final visual — prefer fewer words, stronger ad.
big_idea = campaign platform (memorable, short). hero_message = primary line on creative.

────────────────
CREATIVE SIMPLICITY (quality principle — not a fixed layout)
────────────────
Do not clutter the ad with unnecessary information.
Main sales message + offer + at most 3 supporting messages + a single CTA.
Keep the visual as visible as possible — let the photograph breathe.
Avoid large bottom bands, unnecessary badges, and repeating price messages.
supporting_messages must be ≤3 short lines.

────────────────
PRICE / OFFER
────────────────
If list→launch prices exist in pricing / brief, treat the drop as a SALES HOOK.
Present price creatively (e.g. "$400,000 → $300,000" or "LAUNCH PRICE $300K") — do not hardcode one style.
When using the derived percent, frame ONLY as "approximately N% launch price advantage"
(or "~N% launch price advantage"). NEVER as investment return, ROI, guaranteed profit, or yield.
Do not invent other financial numbers.

────────────────
ANTI-CLICHÉ (hard ban)
────────────────
Never use: "Discover the Elegance…", "Prestigious Address…", "Schedule a Viewing Today…",
"unparalleled luxury", "lucrative investment", "most sought-after address",
"perfect blend of…", "gateway to a sophisticated lifestyle", "Reserve a private tour".
CTA must be campaign-appropriate (e.g. explore details / claim launch price / see Unit X) —
not a viewing-appointment cliché.

────────────────
CREATIVE FREEDOM vs FACTS
────────────────
HIGH FREEDOM: headline, big idea, emphasis, CTA, visual storytelling, tone, composition.
HIGH ACCURACY: price, unit, location, ROI, rent, yield, distance, specs —
only from verified_claims / pricing / user brief. Never invent yields.
PROJECT MODE: real Drive interiors + real project logo only; never invent assets or global brand marks.

LANGUAGE LOCK: When campaign language is Turkish (tr), write ALL user-facing copy
(big_idea, hero_message, supporting_messages, sales_hook, offer, CTA) in Turkish.
Do not mix English slogans/headlines/CTAs into a Turkish campaign.
Return ONLY the JSON object.
"""


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start : end + 1])
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def contains_cliche(text: str | None) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in CLICHE_PATTERNS)


def _local_creative_brief(user_prompt: str) -> str:
    """Deterministic CD brief for mock/local provider — advertising thinking, no clichés."""
    payload: dict[str, Any] = {}
    raw = user_prompt or ""
    start = raw.find("{")
    if start >= 0:
        try:
            payload, _ = json.JSONDecoder().raw_decode(raw, start)
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    pricing = payload.get("pricing") if isinstance(payload.get("pricing"), dict) else {}
    brief = str(payload.get("user_brief") or "")
    name = str(project.get("name") or "Project")
    city = str(project.get("city") or "").strip()
    state = str(project.get("state") or "").strip()
    place = " ".join(p for p in (city, state) if p) or city or "Washington DC"

    unit = None
    units = pricing.get("unit_codes") if isinstance(pricing.get("unit_codes"), list) else []
    if units:
        unit = str(units[0])

    pp = pricing.get("price_presentation") if isinstance(pricing.get("price_presentation"), dict) else {}
    price_copy = str(pp["copy"]) if pp.get("copy") else None
    discount = pricing.get("discount") if isinstance(pricing.get("discount"), dict) else None
    discount_display = str(discount.get("display") or "") if discount else ""

    # Character-led big idea when brief stresses modern / historic / şık.
    brief_l = brief.lower()
    character_led = any(
        k in brief_l for k in ("tarihi", "historic", "modern", "şık", "sik", "karakter")
    )
    if character_led:
        big_idea = "Modern. Şık. Tarihi."
        hero = big_idea
        emphasis = ["Modern", "Şık", "Tarihi", unit or name, "lansman"]
    else:
        big_idea = f"{name} — character that compounds"
        hero = f"{name}: modern life, historic soul"
        emphasis = [name, "modern", "historic", unit or "launch", place]

    sales_hook = f"Unit {unit} launch opportunity" if unit else f"{name} launch opportunity"
    if price_copy:
        sales_hook = f"Unit {unit} launch: {price_copy}" if unit else f"Launch: {price_copy}"

    if discount_display:
        value = f"Approximately {discount_display.lstrip('~')} launch price advantage"
        if discount_display.startswith("~"):
            value = f"{discount_display} launch price advantage"
    else:
        value = f"Distinctive {place} living with a time-bound launch entry"

    offer = price_copy or "Exclusive launch pricing"
    cta = "Detayları İncele" if any(ord(c) > 127 for c in brief) or "proje" in brief_l else "See the details"

    supporting = [
        f"Historic character + modern living at {name}",
        f"{place} — verified neighborhood context" if place else "Verified location context",
    ]
    if unit:
        supporting.insert(0, f"Unit {unit} launch window")

    return json.dumps(
        {
            "big_idea": big_idea,
            "objective": "Unit launch — lifestyle character + honest launch-price advantage",
            "audience": f"Selective buyers and investors seeking character-rich homes in {place}",
            "concept": f"{big_idea} — {name} as modern living inside historic fabric",
            "hero_message": hero,
            "supporting_messages": supporting[:3],
            "emphasis": [w for w in emphasis if w],
            "sales_hook": sales_hook,
            "offer": offer,
            "price_presentation": price_copy or offer,
            "value_proposition": value,
            "proof_points": [
                p
                for p in [
                    "Real project interiors from Drive/Media Library",
                    f"Official {name} brand mark",
                    price_copy,
                    place if place else None,
                ]
                if p
            ],
            "cta": cta,
            "first_2_seconds": (
                f"Real {name} interior + {big_idea}"
                + (f" + {price_copy}" if price_copy else "")
            ),
            "thinking_notes": (
                f"goal=unit launch; sold=Unit {unit or 'residence'} at {name}; "
                f"why_now=launch price; hook=list→launch; number={discount_display or price_copy or 'n/a'}; "
                f"emotion=historic character + modern living; action={cta}"
            ),
            "visual_direction": (
                "Luxury editorial / premium RE campaign. Hero: authentic project interior only. "
                "Quiet light, architectural detail, room for short hierarchy copy. Real logo lockup."
            ),
            "composition_direction": (
                "Editorial balance — negative space for big idea and price strip; "
                "do not cover key architecture. Logo anchored; CTA restrained."
            ),
            "typography_direction": "Expressive display for big idea; restrained supporting; high contrast",
            "color_direction": "Warm stone, deep charcoal, restrained brand accent — no generic purple gradients",
            "tone": "Modern, sharp, historically aware — premium campaign, not listing brochure",
            "formats": ["instagram_feed", "instagram_story", "landing_hero"],
            "required_assets": ["real_interior_photo", "project_logo"],
            "required_project_data": ["unit_identity", "list_and_launch_price", "location"],
            "recommended_outputs": ["social_post", "story", "landing_section"],
            "brief_echo": brief[:200],
        },
        ensure_ascii=False,
    )


def _sanitize_strategy(strategy: dict[str, Any], *, pricing: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    """Light guard against banned listing clichés when the model slips."""
    name = str(project.get("name") or "Project")
    units = pricing.get("unit_codes") if isinstance(pricing.get("unit_codes"), list) else []
    unit = str(units[0]) if units else None
    pp = pricing.get("price_presentation") if isinstance(pricing.get("price_presentation"), dict) else {}
    discount = pricing.get("discount") if isinstance(pricing.get("discount"), dict) else None
    discount_display = str(discount.get("display") or "") if discount else ""

    if contains_cliche(str(strategy.get("hero_message") or "")):
        strategy["hero_message"] = strategy.get("big_idea") or strategy.get("concept") or f"{name}"
    if contains_cliche(str(strategy.get("cta") or "")):
        strategy["cta"] = "Detayları İncele"
    if contains_cliche(str(strategy.get("sales_hook") or "")):
        price_copy = pp.get("copy")
        strategy["sales_hook"] = (
            f"Unit {unit} launch opportunity" if unit else f"{name} launch opportunity"
        )
        if price_copy:
            strategy["sales_hook"] = f"{strategy['sales_hook']}: {price_copy}"
    if contains_cliche(str(strategy.get("value_proposition") or "")) or re.search(
        r"\b(roi|return|guaranteed profit|yield)\b",
        str(strategy.get("value_proposition") or ""),
        re.I,
    ):
        if discount_display:
            strategy["value_proposition"] = f"{discount_display} launch price advantage"
        else:
            strategy["value_proposition"] = f"Launch entry at {name}"

    # Prefer launch-price-advantage framing over bare "% off" / return language.
    for key in ("value_proposition", "offer", "sales_hook", "hero_message"):
        val = strategy.get(key)
        if isinstance(val, str) and discount_display and re.search(r"\d+\s*%\s*off\b", val, re.I):
            strategy[key] = re.sub(
                r"~?\d+(?:\.\d+)?\s*%\s*off\b",
                f"{discount_display} launch price advantage",
                val,
                flags=re.I,
            )
        if isinstance(val, str):
            strategy[key] = re.sub(
                r"\b(\d+(?:\.\d+)?%\s*)(investment\s+return|roi|guaranteed\s+profit)\b",
                r"\1launch price advantage",
                val,
                flags=re.I,
            )

    msgs = strategy.get("supporting_messages") or []
    if isinstance(msgs, list):
        strategy["supporting_messages"] = [
            m for m in msgs if isinstance(m, str) and not contains_cliche(m)
        ][:3]

    if not strategy.get("big_idea"):
        strategy["big_idea"] = strategy.get("concept") or strategy.get("hero_message")

    return strategy


def generate_creative_strategy(
    *,
    user_brief: str,
    project: dict[str, Any],
    research_summary: dict[str, Any],
    pricing: dict[str, Any],
    mode: str,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Ask LLM for CD strategy. Asset IDs / capabilities are filled by orchestration."""
    llm = provider or get_llm_provider()
    payload = {
        "marker": CREATIVE_BRIEF_MARKER,
        "mode": mode,
        "user_brief": user_brief,
        "project": project,
        "research_summary": {
            "selected_interior": research_summary.get("selected_interior"),
            "selected_logo": research_summary.get("selected_logo"),
            "drive_source_count": len(research_summary.get("drive_sources") or []),
            "unit_mentions": research_summary.get("unit_mentions"),
            "warnings": research_summary.get("warnings"),
        },
        "pricing": {
            "unit_codes": pricing.get("unit_codes"),
            "price_presentation": pricing.get("price_presentation"),
            "discount": pricing.get("discount"),
            "claims": pricing.get("claims"),
            "honesty": pricing.get("honesty"),
        },
        "instructions": (
            "Invent the campaign like a senior CD. Decide big_idea, hero, hook, CTA, hierarchy. "
            "Use pricing.discount only as launch price advantage — never as ROI. "
            "No listing clichés. Do not invent prices or asset IDs. "
            f"Respond with {CREATIVE_BRIEF_MARKER} object only."
        ),
    }
    user = f"{CREATIVE_BRIEF_MARKER}\n{json.dumps(payload, ensure_ascii=False)}"
    try:
        # Local provider short-circuit for tests / offline.
        if getattr(llm, "name", "") == "local":
            answer = _local_creative_brief(user)
            meta = {"provider": "local", "model": getattr(llm, "model", "local")}
        else:
            result = llm.generate(system=_SYSTEM, user=user, timeout_seconds=60.0)
            answer = result.answer
            meta = {
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }
        strategy = _extract_json(answer)
    except (LLMProviderConfigError, LLMProviderError) as exc:
        strategy = _extract_json(_local_creative_brief(user))
        meta = {"provider": "fallback_local", "error": str(exc)}

    # Normalize list fields.
    for key in (
        "supporting_messages",
        "emphasis",
        "proof_points",
        "formats",
        "required_assets",
        "required_project_data",
        "recommended_outputs",
    ):
        val = strategy.get(key)
        if val is None:
            strategy[key] = []
        elif isinstance(val, str):
            strategy[key] = [val]
        elif not isinstance(val, list):
            strategy[key] = [str(val)]

    strategy = _sanitize_strategy(strategy, pricing=pricing, project=project)
    strategy["_llm"] = meta
    return strategy


def parse_emphasis_words(brief: str, strategy_emphasis: list[Any]) -> list[str]:
    words = [str(w).strip() for w in (strategy_emphasis or []) if str(w).strip()]
    # Light enrichment from brief tokens if empty.
    if not words:
        for token in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{3,}", brief or ""):
            if token.lower() in {"the", "and", "for", "bir", "ile", "olan"}:
                continue
            words.append(token)
            if len(words) >= 6:
                break
    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        key = w.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out
