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

_SYSTEM = """You are the Creative Director for a real-estate marketing system.
Interpret the user brief like a senior CD. Decide campaign strategy from the brief,
verified project facts, and available real assets — not from fixed layout templates.

Return ONLY a JSON object with these keys:
objective, audience, concept, hero_message, supporting_messages (array),
emphasis (array of words to stress), sales_hook, offer, value_proposition,
proof_points (array), cta, visual_direction, composition_direction,
typography_direction, color_direction, tone, formats (array),
required_assets (array of descriptions), required_project_data (array),
recommended_outputs (array).

Rules:
- Do NOT invent financial numbers. Use only numbers present in verified_claims / user brief.
- Do NOT invent asset IDs. Assets are selected separately.
- Do NOT propose AI-generated interiors when mode is project and a real interior is locked.
- High creativity for concept/messaging; high fact accuracy for claims; protect project assets.
- Language may follow the brief (Turkish/English mix OK); keep hero/CTA campaign-ready.
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


def _local_creative_brief(user_prompt: str) -> str:
    """Deterministic CD brief for mock/local provider — no fabricated finance."""
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
    unit = None
    units = pricing.get("unit_codes") if isinstance(pricing.get("unit_codes"), list) else []
    if units:
        unit = str(units[0])

    price_copy = None
    pp = pricing.get("price_presentation") if isinstance(pricing.get("price_presentation"), dict) else {}
    if pp.get("copy"):
        price_copy = str(pp["copy"])
    discount = pricing.get("discount") if isinstance(pricing.get("discount"), dict) else None

    hero = f"{name}: where modern living meets historic character"
    if unit:
        hero = f"Unit {unit} at {name} — modern elegance, historic soul"
    sales_hook = "A rare launch opportunity in a landmark address"
    if price_copy:
        sales_hook = f"Launch pricing: {price_copy}"
    value = (
        f"Live and invest in {city or 'a premier district'} with architectural character "
        f"and a time-bound launch offer."
    )
    if discount and discount.get("display"):
        value = (
            f"Secure Unit {unit or 'your residence'} at {discount['display']} off list — "
            f"distinguished living and a measured investment entry in {city or 'Washington DC'}."
        )
    offer = price_copy or "Exclusive launch pricing"
    cta = "Reserve a private tour"
    supporting = [
        f"Real interiors from {name} — not AI fiction",
        "Historic character meets contemporary refinement",
        f"{city} living with investment clarity" if city else "Distinguished urban living",
    ]
    return json.dumps(
        {
            "objective": "Unit launch campaign — lifestyle + investment",
            "audience": "Discerning Washington DC residents and investors seeking character-rich homes",
            "concept": f"The Landmark Residence — {name} as modern life inside historic character",
            "hero_message": hero,
            "supporting_messages": supporting,
            "emphasis": ["Unit", unit or name, "launch", "historic", "modern", city or "DC"],
            "sales_hook": sales_hook,
            "offer": offer,
            "value_proposition": value,
            "proof_points": [
                p
                for p in [
                    f"Real project interiors from Drive/Media Library",
                    f"Official {name} brand mark",
                    price_copy,
                    "Washington DC address" if city else None,
                ]
                if p
            ],
            "cta": cta,
            "visual_direction": (
                "Hero: authentic project interior photography. Soft premium lighting, "
                "quiet luxury, architectural detail in frame. Real logo lockup — never drawn."
            ),
            "composition_direction": (
                "Editorial balance — room for hero copy and price strip without covering faces "
                "or key architecture. Logo anchored, CTA clear."
            ),
            "typography_direction": "Refined sans for headlines; restrained supporting type; high contrast",
            "color_direction": "Warm neutrals, stone, deep charcoal, restrained metallic accent from brand",
            "tone": "Modern, sophisticated, historically aware, investment-confident",
            "formats": ["instagram_feed", "instagram_story", "landing_hero"],
            "required_assets": ["real_interior_photo", "project_logo"],
            "required_project_data": ["unit_identity", "list_and_launch_price", "location"],
            "recommended_outputs": ["social_post", "story", "landing_section"],
            "brief_echo": brief[:200],
        },
        ensure_ascii=False,
    )


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
            "Decide campaign creative strategy. Do not invent prices or asset IDs. "
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
