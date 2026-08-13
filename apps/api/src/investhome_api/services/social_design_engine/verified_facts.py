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
from investhome_api.services.social_design_engine.fact_governance import (
    CampaignContext,
    ConflictStatus,
    DerivationType,
    MarketingStatus,
    Visibility,
    apply_conflicts_and_eligibility,
    blocked_financial_tokens,
    claim_family_for_key,
    extract_financial_tokens,
    is_financial_claim_key,
    is_marketing_eligible,
)
from investhome_api.services.social_design_engine.generation import CampaignFact
from investhome_api.services.social_design_engine.project_knowledge import (
    ProjectKnowledgePackage,
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
        "leverage",
        "ltv",
        "loan_to_cost",
        "projected_value",
        "expected_exit",
        "distributions",
        "cash_flow",
        "investment_period",
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
    """One grounded fact with provenance. Never invent financial values.

    Legacy unknown financial facts default CONSERVATIVELY: not marketing-eligible.
    """

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
    visibility: Visibility = "unknown"
    marketing_status: MarketingStatus = "requires_review"
    derivation_type: DerivationType = "extracted"
    effective_date: str | None = None
    campaign_scope: str | None = None
    conflict_status: ConflictStatus = "none"


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
    """Clean package passed to Marketing Strategy / Copy / Creative Director.

    TWO packages: project_knowledge (reasoning) and marketing_safe_facts (public claims).
    """

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
    marketing_safe_facts: list[VerifiedFact] = field(default_factory=list)
    claim_eligibility_trace: list[dict[str, Any]] = field(default_factory=list)


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def _fid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _is_financial_key(key: str) -> bool:
    k = _norm(key).replace(" ", "_")
    if k in {"investment_narrative", "neighborhood_name"} or k.startswith(
        ("neighborhood_highlight", "architecture_highlight", "amenity_")
    ):
        return False
    if k in FINANCIAL_KEYS:
        return True
    return is_financial_claim_key(key)


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
        visibility: Visibility | None = None,
        marketing_status: MarketingStatus | None = None,
        derivation_type: DerivationType | None = None,
    ) -> None:
        display = (value or "").strip()
        if not display:
            return
        financial = _is_financial_key(key) or (
            category in FINANCIAL_CATEGORIES and key != "investment_narrative"
        )
        # Conservative legacy defaults: financial knowledge is NOT marketing-approved.
        if financial:
            vis: Visibility = visibility or ("internal" if source == "project_db" else "unknown")
            mstatus: MarketingStatus = marketing_status or "requires_review"
            deriv: DerivationType = derivation_type or (
                "canonical" if source == "project_db" else "extracted"
            )
        else:
            vis = visibility or ("public" if source == "project_db" and key != "address" else "public")
            if key == "address":
                vis = visibility or "internal"
            mstatus = marketing_status or "approved"
            deriv = derivation_type or ("canonical" if source == "project_db" else "extracted")
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
                is_financial=financial,
                is_campaign_scoped=False,
                visibility=vis,
                marketing_status=mstatus,
                derivation_type=deriv,
                effective_date=None,
                campaign_scope=None,
                conflict_status="none",
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
                visibility="public",
                marketing_status="approved",
                derivation_type="extracted",
            )

    # RAG / doc financial numbers: considered for the trace, NEVER auto-approved.
    _ingest_extracted_financials(facts, pkg)

    # Explicit marketing approval only when an authoritative project record says so.
    _apply_explicit_project_approvals(facts, pkg)
    return facts


def _infer_extracted_key(excerpt: str) -> str:
    t = _norm(excerpt)
    if any(k in t for k in ("irr",)):
        return "irr"
    if any(k in t for k in ("hedef getiri", "target return", "roi", "getiri")):
        return "target_return"
    if any(k in t for k in ("yield",)):
        return "yield"
    if any(k in t for k in ("min", "asgari", "equity", "minimum")):
        return "min_investment"
    if any(k in t for k in ("kira", "rental")):
        return "rental_income"
    if any(k in t for k in ("profit", "kar", "kâr")):
        return "profit"
    if any(k in t for k in ("ltv", "leverage", "financ")):
        return "financing"
    if any(k in t for k in ("ay", "month", "süre", "sure", "period")):
        return "duration"
    return "extracted_financial"


def _ingest_extracted_financials(facts: list[VerifiedFact], pkg: ProjectKnowledgePackage) -> None:
    seen = {_norm(f.display_value) for f in facts}
    for ev in pkg.source_evidence or []:
        text = (ev.excerpt or "").strip()
        if not text:
            continue
        tokens = extract_financial_tokens(text)
        if not tokens:
            continue
        for token in tokens:
            if _norm(token) in seen:
                continue
            seen.add(_norm(token))
            key = _infer_extracted_key(text)
            facts.append(
                VerifiedFact(
                    fact_id=_fid("xf"),
                    category="investment",
                    key=key,
                    value=token,
                    display_value=token,
                    source="retrieved",
                    source_reference=ev.reference or "retrieved",
                    confidence=0.45,
                    verified=False,
                    marketing_usefulness=0.2,
                    recency_score=0.4,
                    is_financial=True,
                    is_campaign_scoped=False,
                    visibility="unknown",
                    marketing_status="requires_review",
                    derivation_type="extracted",
                    conflict_status="none",
                )
            )


def _apply_explicit_project_approvals(facts: list[VerifiedFact], pkg: ProjectKnowledgePackage) -> None:
    """Honor ONLY explicit marketing-approval flags on the knowledge record.

    Never infer approval from the mere presence of a financial field.
    """
    inv = pkg.investment or {}
    pricing = pkg.pricing or {}
    approved_keys: set[str] = set()
    for bucket in (inv, pricing):
        for raw_key, raw_val in bucket.items():
            key = str(raw_key)
            if key.endswith("_marketing_status") and str(raw_val).strip().lower() == "approved":
                approved_keys.add(key[: -len("_marketing_status")])
            if key.endswith("_marketing_approved") and raw_val in {True, "true", "approved", 1, "1"}:
                approved_keys.add(key[: -len("_marketing_approved")])
    if not approved_keys:
        return
    aliases = {
        "projected_irr": {"projected_irr", "irr"},
        "projected_roi": {"projected_roi", "roi", "target_return"},
        "equity_required": {"equity_required", "min_investment"},
        "projected_profit": {"projected_profit", "profit"},
    }
    allowed = set(approved_keys)
    for src, dests in aliases.items():
        if src in approved_keys:
            allowed.update(dests)
    for fact in facts:
        if not fact.is_financial:
            continue
        if fact.derivation_type != "canonical":
            continue
        if fact.key in allowed:
            fact.marketing_status = "approved"
            fact.visibility = "public"


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
                visibility="public",
                marketing_status="campaign_only",
                derivation_type="user_supplied",
                effective_date=datetime.now(UTC).isoformat(),
                campaign_scope="current",
                conflict_status="none",
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


def _eligible_covers_request(key: str, eligible: list[VerifiedFact], campaign_facts: list[CampaignFact]) -> bool:
    """True when a MARKETING-ELIGIBLE fact (or current campaign input) covers the request.

    Project-knowledge existence is not sufficient.
    """
    aliases = {
        "irr": {"irr", "projected_irr"},
        "roi": {"roi", "projected_roi", "campaign_return", "target_return"},
        "target_return": {"target_return", "projected_roi", "campaign_return", "roi"},
        "yield": {"yield", "campaign_return"},
        "min_investment": {"min_investment", "campaign_min_investment", "equity_required"},
        "duration": {"duration", "campaign_duration", "investment_period"},
        "rental_income": {"rental_income", "rental"},
        "profit": {"profit", "projected_profit"},
        "appreciation": {"appreciation"},
        "financing": {"financing", "leverage", "ltv"},
    }
    wanted = aliases.get(key, {key})
    family = claim_family_for_key(key)
    for fact in eligible:
        if not fact.is_financial:
            continue
        if fact.key in wanted or key in _norm(fact.key):
            return True
        if family and claim_family_for_key(fact.key) == family and fact.is_campaign_scoped:
            return True
    if key in {"target_return", "roi", "yield"} and any(f.kind == "percent" for f in campaign_facts):
        return True
    if key == "irr" and any(f.kind == "percent" for f in campaign_facts):
        return True
    if key in {"min_investment"} and any(f.kind == "money" for f in campaign_facts):
        return True
    if key == "duration" and any(f.kind == "duration" for f in campaign_facts):
        return True
    return False


def resolve_missing_facts(
    *,
    intent: CampaignIntentResult,
    knowledge: ProjectKnowledgePackage,
    selected: list[VerifiedFact],
    campaign_facts: list[CampaignFact],
    eligible_facts: list[VerifiedFact] | None = None,
) -> tuple[list[MissingFact], bool, str | None]:
    """Missing facts. Block only when user explicitly requires an unavailable eligible claim."""
    _ = knowledge
    missing: list[MissingFact] = []
    pool = list(eligible_facts if eligible_facts is not None else selected)

    def has_eligible(key: str) -> bool:
        return _eligible_covers_request(key, pool, campaign_facts)

    for req in intent.explicit_fact_requests:
        if has_eligible(req.key):
            continue
        missing.append(
            MissingFact(
                key=req.key,
                label=req.label,
                category="investment",
                required=req.required,
                reason=f"explicitly_requested_but_not_marketing_approved:{req.key}",
                user_can_provide=True,
            )
        )

    # Soft missing for investment without eligible metrics — do NOT block
    if intent.campaign_intent in {"investment", "value_proposition", "rental_income"}:
        has_metric = any(
            f.is_financial and is_marketing_eligible(f).eligible for f in pool if f.is_financial
        )
        if not has_metric and not any(m.key in {"irr", "roi", "target_return"} for m in missing):
            missing.append(
                MissingFact(
                    key="financial_metrics",
                    label="Campaign financial metrics",
                    category="investment",
                    required=False,
                    reason="investment_without_marketing_approved_metrics",
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
    campaign_ctx = CampaignContext(
        campaign_intent=intent.campaign_intent,
        current_campaign_id="current",
        user_supplied_keys=frozenset(f.key for f in user_facts),
    )
    marketing_safe, eligibility_trace, conflicts = apply_conflicts_and_eligibility(
        all_facts,
        campaign_ctx,
    )
    # Public campaign facts come ONLY from the marketing-safe package.
    selected = select_facts_for_campaign(
        all_facts=marketing_safe,
        campaign_intent=intent.campaign_intent,
        explicit_requests=list(intent.explicit_fact_requests or []),
    )
    missing, can_proceed, block_reason = resolve_missing_facts(
        intent=intent,
        knowledge=knowledge,
        selected=selected,
        campaign_facts=campaign_facts,
        eligible_facts=marketing_safe,
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
                "marketing_status": f.marketing_status,
                "derivation_type": f.derivation_type,
                "visibility": f.visibility,
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
        "claim_eligibility_trace": eligibility_trace,
        "financial_conflicts": {
            family: [
                {
                    "key": getattr(f, "key", None),
                    "display": getattr(f, "display_value", None),
                    "source": getattr(f, "source", None),
                    "marketing_status": getattr(f, "marketing_status", None),
                }
                for f in group
            ]
            for family, group in conflicts.items()
        },
        "blocked_financial_tokens": blocked_financial_tokens(all_facts, campaign_ctx),
        "marketing_safe_count": len(marketing_safe),
        "packages": {
            "project_knowledge": True,
            "marketing_safe_facts": True,
        },
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
        marketing_safe_facts=marketing_safe,
        claim_eligibility_trace=eligibility_trace,
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
        "marketing_safe_facts": verified_facts_to_dicts(pkg.marketing_safe_facts),
        "user_campaign_inputs": list(pkg.user_campaign_inputs),
        "missing_relevant_facts": missing_facts_to_dicts(pkg.missing_relevant_facts),
        "available_assets": list(pkg.available_assets),
        "can_proceed": pkg.can_proceed,
        "block_reason": pkg.block_reason,
        "qa_trace": pkg.qa_trace,
        "claim_eligibility_trace": list(pkg.claim_eligibility_trace),
        "selected_asset_hint": pkg.selected_asset_hint,
        "angle_hint": pkg.angle_hint,
    }


def selected_facts_as_strategy_evidence(facts: list[VerifiedFact]) -> list[str]:
    """Public-safe evidence for strategist. Financials only if marketing-eligible."""
    out: list[str] = []
    for f in facts:
        if f.key == "address" or f.marketing_usefulness < 0.35:
            continue
        if f.is_financial and not is_marketing_eligible(f).eligible:
            continue
        if f.is_financial and f.is_campaign_scoped:
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
    """Structured Metrics may only consume marketing-eligible facts + campaign inputs.

    MUST NOT independently query raw project/RAG financial data.
    """
    from investhome_api.services.social_design_engine.generation import CampaignFact as CF
    from investhome_api.services.social_design_engine.metrics import campaign_facts_to_structured_metrics

    campaign_like: list[CF] = []
    for f in facts:
        if not f.is_financial:
            continue
        if f.key == "investment_narrative":
            continue
        if not is_marketing_eligible(f).eligible:
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
