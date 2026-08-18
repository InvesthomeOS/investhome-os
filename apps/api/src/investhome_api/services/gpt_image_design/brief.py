"""Creative brief for GPT Image — Claim Guard facts + architecture lock. No invented claims."""

from __future__ import annotations

from typing import Any

from investhome_api.services.project_assistant.llm_provider import (
    LLMProviderConfigError,
    LLMProviderError,
    get_llm_provider,
)
from investhome_api.services.social_design_engine.copy_director import CopyDirection
from investhome_api.services.social_design_engine.creative_director import CreativeConcept
from investhome_api.services.social_design_engine.fact_governance import (
    extract_financial_tokens,
    strip_ineligible_financial_claims,
    text_contains_ineligible_financial,
)
from investhome_api.services.social_design_engine.generation import CampaignFact, GenerationIntent
from investhome_api.services.social_design_engine.marketing_strategist import MarketingStrategy
from investhome_api.services.social_design_engine.verified_facts import CampaignIntelligencePackage

_KNOWN_CANONICAL_LEAKS = ("19.5%", "27.8%", "$1450K", "$1,450K", "$1.45M", "1450K")

ARCHITECTURE_LOCK = [
    "The FIRST input image is the actual product for sale — a real project render/photograph.",
    "Do NOT change building architecture, facade, massing, materials, or silhouette.",
    "Do NOT add, remove, or relocate windows, doors, balconies, or floors.",
    "Do NOT redesign, restyle, or replace the building with a different property.",
    "Do NOT invent a skyline, landmark, or neighborhood that contradicts verified location facts.",
    "You MAY: composition, crop, typography, graphic design, info panels, map/location graphics, lines/markers, background expansion, city/location context that matches verified facts, brand lockups from supplied logo files.",
    "Use only real logo files supplied as extra input images. NEVER generate, redraw, or fake a logo.",
    "Do not invent price, rent, ROI, IRR, yield, or distance figures.",
]


def _safe_facts(intel: CampaignIntelligencePackage) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for fact in intel.marketing_safe_facts:
        value = (fact.display_value or fact.value or "").strip()
        if not value:
            continue
        rows.append(
            {
                "key": fact.key,
                "label": fact.key.replace("_", " "),
                "value": value,
                "financial": "yes" if fact.is_financial else "no",
            }
        )
    return rows


def _user_campaign_facts(facts: list[CampaignFact]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for fact in facts:
        display = (fact.display or "").strip()
        if not display:
            continue
        out.append({"label": fact.label, "value": display, "kind": fact.kind})
    return out


def _allowed_financial_tokens(
    campaign_facts: list[CampaignFact],
    intel: CampaignIntelligencePackage,
) -> list[str]:
    tokens: list[str] = []
    for fact in campaign_facts:
        if fact.display and fact.display not in tokens:
            tokens.append(fact.display)
        for extra in extract_financial_tokens(fact.display):
            if extra not in tokens:
                tokens.append(extra)
    for vf in intel.marketing_safe_facts:
        if not vf.is_financial:
            continue
        value = (vf.display_value or vf.value or "").strip()
        if value and value not in tokens:
            tokens.append(value)
        for extra in extract_financial_tokens(value):
            if extra not in tokens:
                tokens.append(extra)
    return tokens


def _blocked_tokens(intel: CampaignIntelligencePackage, allowed: list[str]) -> list[str]:
    blocked: list[str] = []
    qa = intel.qa_trace or {}
    for token in qa.get("blocked_financial_tokens") or []:
        text = str(token).strip()
        if text and text not in blocked:
            blocked.append(text)
    for row in intel.claim_eligibility_trace or []:
        if not isinstance(row, dict):
            continue
        if row.get("is_financial") and not row.get("eligible"):
            token = str(row.get("fact") or row.get("value") or "").strip()
            if token and token not in blocked:
                blocked.append(token)
    for leak in _KNOWN_CANONICAL_LEAKS:
        if leak not in allowed and leak not in blocked:
            blocked.append(leak)
    return blocked


def _sanitize(text: str, *, allowed: list[str], blocked: list[str]) -> str:
    cleaned = strip_ineligible_financial_claims(
        text or "",
        allowed_tokens=allowed,
        blocked_tokens=blocked,
    )
    if text_contains_ineligible_financial(cleaned, allowed_tokens=allowed, blocked_tokens=blocked):
        return strip_ineligible_financial_claims(
            cleaned,
            allowed_tokens=allowed,
            blocked_tokens=blocked,
        )
    return cleaned


def build_shared_brief(
    *,
    project_name: str,
    instruction: str,
    intent: GenerationIntent,
    strategy: MarketingStrategy,
    copy_direction: CopyDirection,
    creative: CreativeConcept,
    campaign_facts: list[CampaignFact],
    intel: CampaignIntelligencePackage,
    source_filename: str,
    language: str | None,
    format_label: str,
    resolution: str,
    extra_image_roles: list[str],
    logo_notes: list[str],
    design_reference_names: list[str],
) -> dict[str, Any]:
    allowed = _allowed_financial_tokens(campaign_facts, intel)
    blocked = _blocked_tokens(intel, allowed)
    pkg = copy_direction.package
    visible_copy = {
        "eyebrow": _sanitize(pkg.eyebrow, allowed=allowed, blocked=blocked),
        "headline": _sanitize(pkg.headline, allowed=allowed, blocked=blocked),
        "supporting": _sanitize(pkg.supporting_copy, allowed=allowed, blocked=blocked),
        "cta": _sanitize(pkg.cta, allowed=allowed, blocked=blocked),
    }
    message = _sanitize(strategy.single_minded_message, allowed=allowed, blocked=blocked)
    evidence = [
        _sanitize(item, allowed=allowed, blocked=blocked)
        for item in strategy.supporting_evidence
        if item
    ]
    evidence = [item for item in evidence if item]
    return {
        "project": project_name,
        "objective": strategy.objective or intent.marketing_objective,
        "audience": strategy.audience or intent.audience,
        "language": language or intent.language or "en",
        "campaign_angle": strategy.campaign_angle,
        "tone": strategy.tone or pkg.tone or creative.tone,
        "single_minded_message": message,
        "supporting_evidence": evidence,
        "marketing_safe_facts": _safe_facts(intel),
        "user_campaign_facts": _user_campaign_facts(campaign_facts),
        "allowed_financial_tokens": allowed,
        "blocked_financial_tokens": blocked,
        "visible_copy": visible_copy,
        "composition": {
            "format": format_label,
            "resolution": resolution,
            "family": creative.composition_family or creative.composition_strategy,
            "safe_text_zone": creative.safe_text_zone,
        },
        "architecture_lock": list(ARCHITECTURE_LOCK),
        "brand_restraint": [
            "Do not invent financial figures, distances, landmarks, or amenities.",
            "Do not replace the supplied building photograph with a different building.",
            "Use only supplied real logo files — no fake logos, watermarks, or stock people.",
            "Only render eligible marketing-safe facts and current-campaign user facts.",
        ],
        "source_image": source_filename,
        "extra_image_roles": extra_image_roles,
        "logo_notes": logo_notes,
        "design_references": design_reference_names,
        "user_instruction": instruction.strip(),
        "excluded_facts": list(strategy.excluded_facts or []),
    }


def render_project_edit_prompt(shared: dict[str, Any]) -> str:
    facts_lines = []
    for row in shared.get("user_campaign_facts") or []:
        facts_lines.append(f"- {row.get('label')}: {row.get('value')}")
    for row in shared.get("marketing_safe_facts") or []:
        facts_lines.append(f"- {row.get('label')}: {row.get('value')}")
    if not facts_lines:
        facts_lines.append("- None. Do not invent any figures.")
    allowed = shared.get("allowed_financial_tokens") or []
    blocked = shared.get("blocked_financial_tokens") or []
    copy = shared.get("visible_copy") or {}
    evidence = shared.get("supporting_evidence") or []
    composition = shared.get("composition") or {}
    extra_roles = shared.get("extra_image_roles") or []
    logo_notes = shared.get("logo_notes") or []
    references = shared.get("design_references") or []
    lines = [
        "Create a finished flattened premium Instagram social advertisement by EDITING the supplied project photograph.",
        f"PROJECT: {shared.get('project') or 'Project'}",
        f"OBJECTIVE: {shared.get('objective')}",
        f"AUDIENCE: {shared.get('audience')}",
        f"LANGUAGE: {shared.get('language')}",
        f"TONE: {shared.get('tone')}",
        f"CAMPAIGN ANGLE: {shared.get('campaign_angle')}",
        f"SINGLE-MINDED MESSAGE: {shared.get('single_minded_message')}",
        "MARKETING-SAFE FACTS (authoritative — Financial Claim Guard; do not invent):",
        *facts_lines,
        f"PERMITTED FINANCIAL TOKENS ONLY: {', '.join(allowed) if allowed else 'none'}",
        f"FORBIDDEN FINANCIAL TOKENS: {', '.join(blocked) if blocked else 'none'}",
        "VISIBLE COPY (render exactly, do not rewrite numbers):",
        f"- Eyebrow: {copy.get('eyebrow') or ''}",
        f"- Headline: {copy.get('headline') or ''}",
        f"- Supporting: {copy.get('supporting') or ''}",
        f"- CTA: {copy.get('cta') or ''}",
        f"FORMAT: {composition.get('format') or 'Instagram 4:5'} at {composition.get('resolution') or '1088x1360'}.",
        f"SOURCE IMAGE (input 1 — the product for sale): {shared.get('source_image')}.",
        "Preserve this building exactly. Graphic design around it; do not redesign architecture.",
        f"EXTRA INPUT IMAGES (real logo files only): {', '.join(extra_roles) if extra_roles else 'none — do not invent logos'}.",
        "ARCHITECTURE LOCK:",
        *[f"- {item}" for item in (shared.get('architecture_lock') or ARCHITECTURE_LOCK)],
        "BRAND RESTRAINT:",
        *[f"- {item}" for item in (shared.get('brand_restraint') or [])],
        "USER BRIEF:",
        str(shared.get("user_instruction") or ""),
    ]
    if logo_notes:
        lines.insert(-2, "LOGO FILE NOTES:")
        for note in logo_notes:
            lines.insert(-2, f"- {note}")
    if references:
        lines.insert(
            -2,
            "DESIGN REFERENCES (context only — do not photocopy layouts or substitute a different building): "
            + ", ".join(str(name) for name in references),
        )
    if evidence:
        lines.insert(11, "SUPPORTING EVIDENCE (non-financial unless listed as permitted):")
        for item in evidence[:6]:
            lines.insert(12, f"- {item}")
    prompt = "\n".join(lines)
    return strip_ineligible_financial_claims(
        prompt,
        allowed_tokens=list(allowed),
        blocked_tokens=list(blocked),
    )


def render_general_prompt(*, instruction: str, language: str | None) -> str:
    lang = (language or "en").strip() or "en"
    return "\n".join(
        [
            "Create a finished flattened premium Investhome branded social advertisement (text-to-image).",
            "BRAND: Investhome (Washington DC real-estate investment). Apply Investhome brand tastefully.",
            "Do not invent a specific for-sale building, project name, price, rent, ROI, IRR, or distance.",
            "Do not generate fake logos. If no real logo file is supplied, keep brand treatment typographic.",
            f"LANGUAGE: {lang}",
            "USER BRIEF:",
            instruction.strip(),
        ]
    )


def refine_prompt_with_llm(prompt: str, *, allowed: list[str], blocked: list[str]) -> str:
    """Optional chat refine via existing AI_API_KEY LLMProvider. Local provider is skipped."""
    try:
        provider = get_llm_provider()
    except LLMProviderConfigError:
        return prompt
    if provider.name not in {"openai", "azure_openai"}:
        return prompt
    system = (
        "You write prompts for OpenAI GPT Image edits. Keep the architecture lock intact. "
        "Never invent financial figures, distances, or logos. Return only the image prompt."
    )
    user = (
        "Rewrite the following as a tight GPT Image edit prompt. Preserve every Claim Guard "
        "fact token and the architecture-preservation rules. Do not add numbers.\n\n"
        + prompt
    )
    try:
        result = provider.generate(system=system, user=user, timeout_seconds=45.0)
    except LLMProviderError:
        return prompt
    refined = (result.answer or "").strip()
    if not refined or len(refined) < 80:
        return prompt
    return strip_ineligible_financial_claims(
        refined,
        allowed_tokens=list(allowed),
        blocked_tokens=list(blocked),
    )
