"""Verified facts, campaign fact selection, financial safety, missing-fact gating.

Distinguishes VERIFIED PROJECT FACT vs GENERATED MARKETING LANGUAGE.
Campaign-specific figures never become canonical project facts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from investhome_api.services.social_design_engine.campaign_intent import (
    CampaignIntentKind,
    CampaignIntentResult,
    ExplicitFactRequest,
)
from investhome_api.services.social_design_engine.generation import CampaignFact
from investhome_api.services.social_design_engine.project_knowledge import (
    ProjectKnowledgePackage,
    knowledge_has_verified_financial,
)

FactSource = Literal[
    "project_db",
    "retrieved",
    "user_campaign_input",
    "indexed_asset",
    "derived_safe",
]
FactCategory = Literal[
    "identity",
    "location",
    "investment",
    "pricing",
    "rental",
    "development",
    "amenities",
    "neighborhood",
    "architecture",
    "availability",
    "media",
    "other",
]

FINANCIAL_CATEGORIES = frozenset({"investment", "pricing", "rental"})
FINANCIAL_KEYS = frozenset(
    {
        "irr",
        "roi",
        "target_return",
        "yield",
        "rental_income",
        "min_investment",
        "appreciation",
        "profit",
        "financing",
        "duration",
        "projected_irr",
        "projected_roi",
        "equity_required",
        "projected_profit",
    }
)

# Intent → preferred fact categories (ranked)
INTENT_CATEGORY_PRIORITY: dict[CampaignIntentKind, list[FactCategory]] = {
    "investment": ["investment", "pricing", "identity", "location", "architecture"],
    "rental_income": ["rental", "investment", "identity", "amenities"],
    "value_proposition": ["investment", "identity", "location", "architecture", "amenities"],
    "location": ["location", "neighborhood", "identity", "architecture"],
    "neighborhood": ["neighborhood", "location", "identity", "amenities"],
    "lifestyle": ["amenities", "identity", "architecture", "location"],
    "amenities": ["amenities", "identity", "architecture"],
    "architecture": ["architecture", "identity", "location"],
    "launch": ["identity", "architecture", "location", "availability"],
    "availability": ["availability", "identity", "location"],
    "project_awareness": ["identity", "architecture", "location", "amenities"],
    "generic_project_promotion": ["identity", "location", "architecture", "amenities"],
    "construction_progress": ["development", "identity", "architecture"],
}


@dataclass
class VerifiedFact:
    """One grounded fact with provenance. Never invent financial values."""

    fact_id: str
    category: FactCategory
    key: str
    value: str
    display_value: str
    source: FactSource
    source_reference: str
    confidence: float
    verified: bool
    marketing_usefulness: float = 0.5
    recency_score: float = 0.5
    is_financial: bool = False
    is_campaign_scoped: bool = False
    language_safe: bool = True


@dataclass
class MissingFact:
    key: str
    label: str
    category: str
    required: bool
    reason: str
    user_can_provide: bool = True


@dataclass
class CampaignIntelligencePackage:
    """Clean package passed to Marketing Strategy / Copy / Creative Director."""

    campaign_intent: CampaignIntentKind
    campaign_intent_confidence: float
    marketing_objective: str
    project_knowledge: ProjectKnowledgePackage
    verified_campaign_facts: list[VerifiedFact]
    user_campaign_inputs: list[dict[str, Any]]
    missing_relevant_facts: list[MissingFact]
    available_assets: list[dict[str, Any]]
    can_proceed: bool = True
    block_reason: str | None = None
    qa_trace: dict[str, Any] = field(default_factory=dict)
    selected_asset_hint: str | None = None
    angle_hint: str | None = None


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def _fid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _is_financial_key(key: str) -> bool:
    k = _norm(key).replace(" ", "_")
    if k in FINANCIAL_KEYS:
        return True
    return any(
        term in k
        for term in (
            "irr",
            "roi",
            "yield",
            "return",
            "rental",
            "profit",
            "equity",
            "financ",
            "appreciation",
            "investment",
        )
    )


def build_verified_facts_from_knowledge(
    pkg: ProjectKnowledgePackage,
) -> list[VerifiedFact]:
    facts: list[VerifiedFact] = []

    def add(
        *,
        category: FactCategory,
        key: str,
        value: str,
        source: FactSource,
        reference: str,
        confidence: float,
        usefulness: float,
        verified: bool = True,
    ) -> None:
        display = (value or "").strip()
        if not display:
            return
        facts.append(
            VerifiedFact(
                fact_id=_fid("vf"),
                category=category,
                key=key,
                value=display,
                display_value=display,
                source=source,
                source_reference=reference,
                confidence=confidence,
                verified=verified,
                marketing_usefulness=usefulness,
                recency_score=0.7 if source == "project_db" else 0.55,
                is_financial=_is_financial_key(key) or category in FINANCIAL_CATEGORIES,
                is_campaign_scoped=False,
            )
        )

    ident = pkg.project_identity or {}
    if ident.get("project_name"):
        add(
            category="identity",
            key="project_name",
            value=str(ident["project_name"]),
            source="project_db",
            reference="projects.project_name",
            confidence=1.0,
            usefulness=0.95,
        )
    loc = pkg.location or {}
    for key in ("city", "country", "state"):
        if loc.get(key):
            add(
                category="location",
                key=key,
                value=str(loc[key]),
                source="project_db",
                reference=f"projects.{key}",
                confidence=1.0,
                usefulness=0.9 if key == "city" else 0.55,
            )
    # Address is verified but low marketing usefulness (evidence, not the ad)
    if loc.get("address"):
        add(
            category="location",
            key="address",
            value=str(loc["address"]),
            source="project_db",
            reference="projects.address",
            confidence=1.0,
            usefulness=0.15,
        )

    inv = pkg.investment or {}
    for key, usefulness in (
        ("projected_irr", 0.95),
        ("projected_roi", 0.9),
        ("equity_required", 0.85),
        ("projected_profit", 0.7),
    ):
        if inv.get(key):
            add(
                category="investment",
                key=key,
                value=str(inv[key]),
                source="project_db",
                reference=f"projects.{key}",
                confidence=0.95,
                usefulness=usefulness,
            )

    for key, val in (pkg.pricing or {}).items():
        add(
            category="pricing",
            key=str(key),
            value=str(val),
            source="project_db",
            reference=f"projects.{key}",
            confidence=0.9,
            usefulness=0.55,
        )

    if (pkg.neighborhood or {}).get("name"):
        add(
            category="neighborhood",
            key="neighborhood_name",
            value=str(pkg.neighborhood["name"]),
            source="retrieved",
            reference="neighborhood",
            confidence=0.75,
            usefulness=0.9,
        )
    for i, line in enumerate((pkg.neighborhood or {}).get("highlights") or []):
        add(
            category="neighborhood",
            key=f"neighborhood_highlight_{i}",
            value=str(line),
            source="retrieved",
            reference="neighborhood_highlight",
            confidence=0.65,
            usefulness=0.8,
        )
    for i, line in enumerate((pkg.architecture or {}).get("highlights") or []):
        add(
            category="architecture",
            key=f"architecture_highlight_{i}",
            value=str(line),
            source="retrieved",
            reference="architecture_highlight",
            confidence=0.65,
            usefulness=0.85,
        )
    for i, line in enumerate(pkg.amenities or []):
        add(
            category="amenities",
            key=f"amenity_{i}",
            value=str(line),
            source="retrieved",
            reference="amenity",
            confidence=0.6,
            usefulness=0.75,
        )

    # Soft non-financial value lines from evidence
    for ev in pkg.source_evidence or []:
        if ev.source != "retrieved":
            continue
        text = (ev.excerpt or "").strip()
        if not text or re.search(r"\$\s*\d", text) or re.search(r"\d+\s*%", text):
            continue
        if any(f.display_value == text for f in facts):
            continue
        if any(k in _norm(text) for k in ("investment", "investor", "opportunity", "portfolio")):
            add(
                category="investment",
                key="investment_narrative",
                value=text,
                source="retrieved",
                reference=ev.reference,
                confidence=0.55,
                usefulness=0.7,
            )

    return facts


def campaign_inputs_to_verified_facts(campaign_facts: list[CampaignFact]) -> list[VerifiedFact]:
    """User-supplied campaign figures — campaign-scoped, never canonical."""
    out: list[VerifiedFact] = []
    for cf in campaign_facts:
        key = cf.label or "campaign_metric"
        kind = cf.kind
        if kind == "percent":
            cat: FactCategory = "investment"
            key = "campaign_return"
        elif kind == "money":
            cat = "investment"
            key = "campaign_min_investment"
        elif kind == "duration":
            cat = "investment"
            key = "campaign_duration"
        else:
            cat = "other"
        out.append(
            VerifiedFact(
                fact_id=_fid("cf"),
                category=cat,
                key=key,
                value=cf.display,
                display_value=cf.display,
                source="user_campaign_input",
                source_reference="user_prompt",
                confidence=1.0,
                verified=True,
                marketing_usefulness=0.95,
                recency_score=1.0,
                is_financial=True,
                is_campaign_scoped=True,
            )
        )
    return out


def select_facts_for_campaign(
    *,
    all_facts: list[VerifiedFact],
    campaign_intent: CampaignIntentKind,
    limit: int = 8,
    explicit_requests: list[ExplicitFactRequest] | None = None,
) -> list[VerifiedFact]:
    """Rank intent-relevant facts. Do not dump the entire knowledge base."""
    priority = INTENT_CATEGORY_PRIORITY.get(campaign_intent, ["identity", "location"])
    rank_map = {cat: idx for idx, cat in enumerate(priority)}
    explicit_keys = {r.key for r in (explicit_requests or []) if r.required}
    key_aliases = {
        "irr": {"projected_irr", "irr"},
        "roi": {"projected_roi", "roi", "campaign_return"},
        "target_return": {"projected_roi", "campaign_return"},
        "min_investment": {"equity_required", "campaign_min_investment"},
        "profit": {"projected_profit"},
        "duration": {"campaign_duration"},
    }

    scored: list[tuple[float, VerifiedFact]] = []
    for fact in all_facts:
        if fact.key == "address":
            cat_boost = 0.2
        else:
            cat_boost = max(0.0, 1.0 - rank_map.get(fact.category, 9) * 0.12)
        if fact.category not in priority and fact.category != "identity":
            if fact.is_financial and campaign_intent in {
                "location",
                "neighborhood",
                "architecture",
                "lifestyle",
                "amenities",
            }:
                continue
            if cat_boost <= 0 and fact.category not in {"identity"}:
                continue
        score = (
            cat_boost * 3.0
            + fact.confidence * 2.0
            + fact.marketing_usefulness * 2.5
            + fact.recency_score * 1.0
            + (0.5 if fact.verified else 0.0)
            + (0.4 if fact.is_campaign_scoped else 0.0)
        )
        for req_key in explicit_keys:
            aliases = key_aliases.get(req_key, {req_key})
            if fact.key in aliases or req_key in _norm(fact.key):
                score += 5.0
        scored.append((score, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[VerifiedFact] = []
    seen: set[str] = set()
    for _, fact in scored:
        token = _norm(fact.display_value)
        if not token or token in seen:
            continue
        seen.add(token)
        selected.append(fact)
        if len(selected) >= limit:
            break
    return selected


def resolve_missing_facts(
    *,
    intent: CampaignIntentResult,
    knowledge: ProjectKnowledgePackage,
    selected: list[VerifiedFact],
    campaign_facts: list[CampaignFact],
) -> tuple[list[MissingFact], bool, str | None]:
    """Missing facts. Block only when user explicitly requires an unavailable financial fact."""
    missing: list[MissingFact] = []
    user_tokens = " ".join(f.display for f in campaign_facts).lower()
    selected_keys = {_norm(f.key) for f in selected}
    selected_blob = " ".join(f.display_value for f in selected).lower()

    def has_user_or_verified(key: str) -> bool:
        if knowledge_has_verified_financial(knowledge, key):
            return True
        aliases = {
            "irr": ("irr", "projected_irr"),
            "roi": ("roi", "projected_roi", "return"),
            "target_return": ("return", "roi", "getiri", "%"),
            "yield": ("yield", "getiri"),
            "min_investment": ("campaign_min_investment", "equity_required", "$"),
            "duration": ("campaign_duration", "month", "ay"),
            "rental_income": ("rental", "kira"),
            "profit": ("profit", "projected_profit"),
            "appreciation": ("appreciation",),
            "financing": ("financ", "mortgage"),
        }
        for alias in aliases.get(key, (key,)):
            if alias in selected_keys or alias in user_tokens or alias in selected_blob:
                return True
        # Explicit user-supplied percent/money often covers target_return / min_investment
        if key in {"target_return", "roi", "yield"} and any(f.kind == "percent" for f in campaign_facts):
            return True
        if key in {"min_investment"} and any(f.kind == "money" for f in campaign_facts):
            return True
        if key == "duration" and any(f.kind == "duration" for f in campaign_facts):
            return True
        return False

    for req in intent.explicit_fact_requests:
        if has_user_or_verified(req.key):
            continue
        missing.append(
            MissingFact(
                key=req.key,
                label=req.label,
                category="investment",
                required=req.required,
                reason=f"explicitly_requested_but_unavailable:{req.key}",
                user_can_provide=True,
            )
        )

    # Soft missing for investment without metrics — do NOT block
    if intent.campaign_intent in {"investment", "value_proposition", "rental_income"}:
        has_metric = any(f.is_financial and f.is_campaign_scoped for f in selected) or any(
            f.is_financial and f.category == "investment" and f.source == "project_db" for f in selected
        )
        if not has_metric and not any(m.key in {"irr", "roi", "target_return"} for m in missing):
            missing.append(
                MissingFact(
                    key="financial_metrics",
                    label="Campaign financial metrics",
                    category="investment",
                    required=False,
                    reason="investment_without_verified_metrics",
                    user_can_provide=True,
                )
            )

    blocking = [m for m in missing if m.required]
    if blocking:
        keys = ", ".join(m.label for m in blocking)
        return (
            missing,
            False,
            f"missing_required_facts:{keys}. Provide the value(s) in your prompt to continue — nothing was invented.",
        )
    return missing, True, None


def build_campaign_intelligence(
    *,
    intent: CampaignIntentResult,
    knowledge: ProjectKnowledgePackage,
    campaign_facts: list[CampaignFact],
    selected_asset: dict[str, Any] | None = None,
) -> CampaignIntelligencePackage:
    project_facts = build_verified_facts_from_knowledge(knowledge)
    user_facts = campaign_inputs_to_verified_facts(campaign_facts)
    all_facts = project_facts + user_facts
    selected = select_facts_for_campaign(
        all_facts=all_facts,
        campaign_intent=intent.campaign_intent,
        explicit_requests=list(intent.explicit_fact_requests or []),
    )
    missing, can_proceed, block_reason = resolve_missing_facts(
        intent=intent,
        knowledge=knowledge,
        selected=selected,
        campaign_facts=campaign_facts,
    )
    assets = list(knowledge.media_assets or [])[:12]
    qa = {
        "campaign_intent": intent.campaign_intent,
        "intent_confidence": intent.confidence,
        "intent_signals": list(intent.signals),
        "facts_selected": [
            {
                "fact_id": f.fact_id,
                "key": f.key,
                "display": f.display_value,
                "source": f.source,
                "reference": f.source_reference,
                "campaign_scoped": f.is_campaign_scoped,
                "financial": f.is_financial,
            }
            for f in selected
        ],
        "user_supplied": [asdict(f) if hasattr(f, "__dataclass_fields__") else f for f in user_facts],
        "missing_facts": [asdict(m) for m in missing],
        "selected_asset": selected_asset,
        "angle_hint": intent.key_message,
        "can_proceed": can_proceed,
        "populated_knowledge_sections": list(knowledge.populated_sections),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return CampaignIntelligencePackage(
        campaign_intent=intent.campaign_intent,
        campaign_intent_confidence=intent.confidence,
        marketing_objective=intent.marketing_objective,
        project_knowledge=knowledge,
        verified_campaign_facts=selected,
        user_campaign_inputs=[
            {"label": f.label, "display": f.display, "kind": f.kind, "source": "user_supplied"}
            for f in campaign_facts
        ],
        missing_relevant_facts=missing,
        available_assets=assets,
        can_proceed=can_proceed,
        block_reason=block_reason,
        qa_trace=qa,
        selected_asset_hint=str((selected_asset or {}).get("asset_id") or "") or None,
        angle_hint=intent.key_message,
    )


def verified_facts_to_dicts(facts: list[VerifiedFact]) -> list[dict[str, Any]]:
    return [asdict(f) for f in facts]


def missing_facts_to_dicts(facts: list[MissingFact]) -> list[dict[str, Any]]:
    return [asdict(f) for f in facts]


def campaign_intelligence_to_dict(pkg: CampaignIntelligencePackage) -> dict[str, Any]:
    from investhome_api.services.social_design_engine.project_knowledge import project_knowledge_to_dict

    return {
        "campaign_intent": pkg.campaign_intent,
        "campaign_intent_confidence": pkg.campaign_intent_confidence,
        "marketing_objective": pkg.marketing_objective,
        "project_knowledge": project_knowledge_to_dict(pkg.project_knowledge),
        "verified_campaign_facts": verified_facts_to_dicts(pkg.verified_campaign_facts),
        "user_campaign_inputs": list(pkg.user_campaign_inputs),
        "missing_relevant_facts": missing_facts_to_dicts(pkg.missing_relevant_facts),
        "available_assets": list(pkg.available_assets),
        "can_proceed": pkg.can_proceed,
        "block_reason": pkg.block_reason,
        "qa_trace": pkg.qa_trace,
        "selected_asset_hint": pkg.selected_asset_hint,
        "angle_hint": pkg.angle_hint,
    }


def selected_facts_as_strategy_evidence(facts: list[VerifiedFact]) -> list[str]:
    """Human-readable evidence lines for strategist — skip low-usefulness address."""
    out: list[str] = []
    for f in facts:
        if f.key == "address" or f.marketing_usefulness < 0.35:
            continue
        if f.is_financial and f.is_campaign_scoped:
            out.append(f.display_value)
            continue
        if f.is_financial and f.source == "project_db":
            out.append(f.display_value)
            continue
        out.append(f.display_value)
    return out


def financial_metrics_from_verified(
    facts: list[VerifiedFact],
    *,
    language: str,
    instruction: str,
) -> list[Any]:
    """Pass verified financial metrics into Structured Metrics — never invent placeholders."""
    from investhome_api.services.social_design_engine.generation import CampaignFact as CF
    from investhome_api.services.social_design_engine.metrics import campaign_facts_to_structured_metrics

    # Prefer campaign-scoped user inputs
    campaign_like: list[CF] = []
    for f in facts:
        if not f.is_financial:
            continue
        if not (f.is_campaign_scoped or f.source == "project_db"):
            continue
        kind = "other"
        if f.key in {"campaign_return", "projected_irr", "projected_roi"} or "%" in f.display_value:
            kind = "percent"
        elif f.key in {"campaign_min_investment", "equity_required"} or "$" in f.display_value:
            kind = "money"
        elif f.key in {"campaign_duration"} or re.search(r"\b(ay|month)", f.display_value, re.I):
            kind = "duration"
        else:
            continue
        # Only structured metrics for clearly numeric campaign/DB figures
        if kind == "other":
            continue
        # Narrative investment lines are not metrics
        if f.key == "investment_narrative":
            continue
        campaign_like.append(CF(label=f.key, display=f.display_value, kind=kind))
    if not campaign_like:
        return []
    return campaign_facts_to_structured_metrics(
        campaign_like,
        language=language,
        instruction=instruction,
    )


def never_invent_financial_guard(text: str, *, allowed_tokens: list[str]) -> bool:
    """True if text appears to invent a financial claim not in allowed tokens."""
    t = text or ""
    if not re.search(r"(\d+\s*%|\$\s*\d|\birr\b|\broi\b)", t, re.I):
        return False
    allowed = " ".join(allowed_tokens)
    # If every money/percent token in text is allowed, OK
    for m in re.finditer(r"\$\s*[\d,]+(?:\.\d+)?|\d+(?:[.,]\d+)?\s*%", t):
        token = m.group(0).replace(" ", "")
        if token not in allowed and m.group(0) not in allowed:
            return True
    return False
