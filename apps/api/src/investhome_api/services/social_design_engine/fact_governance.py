"""Marketing-approved fact governance and financial claim guard.

PROJECT KNOWLEDGE → FACT CLASSIFICATION → CLAIM ELIGIBILITY → public output.

A fact existing in RAG / project DB / spreadsheets is NOT a public marketing claim.
Financial numbers become public only when (A) the user supplied them in the current
campaign or (B) they are canonical AND explicitly marketing-approved.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Visibility = Literal["public", "internal", "restricted", "unknown"]
MarketingStatus = Literal["approved", "not_approved", "requires_review", "campaign_only"]
DerivationType = Literal[
    "canonical",
    "user_supplied",
    "calculated",
    "inferred",
    "historical",
    "extracted",
]
ConflictStatus = Literal["none", "conflicting", "blocked_family"]

FINANCIAL_CLAIM_FAMILIES: dict[str, frozenset[str]] = {
    "return": frozenset(
        {
            "return",
            "target_return",
            "roi",
            "irr",
            "yield",
            "appreciation",
            "projected_irr",
            "projected_roi",
            "campaign_return",
            "getiri",
        }
    ),
    "min_investment": frozenset(
        {
            "min_investment",
            "minimum_investment",
            "equity_required",
            "campaign_min_investment",
            "entry_ticket",
        }
    ),
    "investment_period": frozenset(
        {
            "duration",
            "investment_period",
            "campaign_duration",
            "hold_period",
        }
    ),
    "rental_income": frozenset({"rental_income", "rental", "kira"}),
    "profit": frozenset({"profit", "projected_profit"}),
    "financing": frozenset(
        {
            "financing",
            "leverage",
            "ltv",
            "loan_to_cost",
            "loan_to_value",
            "debt",
            "mortgage",
        }
    ),
    "projected_value": frozenset(
        {
            "projected_value",
            "projected_sale_value",
            "expected_exit",
            "current_project_value",
            "acquisition_price",
            "total_development_cost",
        }
    ),
    "cash_flow": frozenset({"cash_flow", "distributions", "distribution"}),
}

FINANCIAL_CLAIM_KEY_TERMS = frozenset().union(*FINANCIAL_CLAIM_FAMILIES.values())

_FINANCIAL_TEXT_TERMS = (
    "irr",
    "roi",
    "yield",
    "return",
    "getiri",
    "rental",
    "profit",
    "equity",
    "financ",
    "leverage",
    "ltv",
    "appreciation",
    "investment",
    "yatirim",
    "cash flow",
    "distribution",
)

_NUMERIC_CLAIM_RE = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?\s*[kmb]?\b|\$\s*\d+(?:\.\d+)?\s*(?:k|m|mn|million)\b"
    r"|\d+(?:[.,]\d+)?\s*%|%\s*\d+(?:[.,]\d+)?",
    re.I,
)


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def normalize_claim_value(value: str) -> str:
    """Normalize a financial display token for conflict comparison."""
    raw = (value or "").strip().lower().replace(" ", "")
    raw = raw.replace(",", "")
    raw = raw.replace("mn", "m").replace("million", "m")
    m = re.search(r"(\d+(?:\.\d+)?)(%)?", raw)
    if not m:
        return raw
    num = m.group(1)
    try:
        n = float(num)
        if n.is_integer():
            num = str(int(n))
        else:
            num = f"{n:.4f}".rstrip("0").rstrip(".")
    except ValueError:
        pass
    if "%" in raw or (m.group(2) == "%"):
        return f"{num}%"
    if "$" in raw or "k" in raw or raw.endswith("m"):
        factor = 1
        if raw.endswith("k") or "k" in raw[1:]:
            factor = 1_000
        elif raw.endswith("m"):
            factor = 1_000_000
        try:
            return str(int(float(num) * factor))
        except ValueError:
            return raw
    return num


def claim_family_for_key(key: str) -> str | None:
    k = _norm(key).replace(" ", "_")
    for family, keys in FINANCIAL_CLAIM_FAMILIES.items():
        if k in keys:
            return family
        if any(alias in k or k in alias for alias in keys if len(alias) >= 3):
            if k in keys or any(k == alias or k.startswith(alias) or alias.startswith(k) for alias in keys):
                return family
    for family, keys in FINANCIAL_CLAIM_FAMILIES.items():
        if any(alias in k for alias in keys if len(alias) >= 4):
            return family
    return None


def is_financial_claim_key(key: str) -> bool:
    k = _norm(key).replace(" ", "_")
    if k in FINANCIAL_CLAIM_KEY_TERMS:
        return True
    if claim_family_for_key(key):
        return True
    return any(term in k for term in _FINANCIAL_TEXT_TERMS)


def text_has_financial_claim(text: str) -> bool:
    t = text or ""
    if _NUMERIC_CLAIM_RE.search(t):
        return True
    tn = _norm(t)
    return any(term in tn for term in ("irr", "roi", "ltv", "yield", "hedef getiri"))


def extract_financial_tokens(text: str) -> list[str]:
    return [m.group(0).strip() for m in _NUMERIC_CLAIM_RE.finditer(text or "")]


@dataclass
class CampaignContext:
    """Current-campaign eligibility context. Never writes into canonical project data."""

    campaign_intent: str = "generic_project_promotion"
    current_campaign_id: str | None = None
    user_supplied_keys: frozenset[str] = field(default_factory=frozenset)
    explicitly_approved_keys: frozenset[str] = field(default_factory=frozenset)
    explicitly_approved_fact_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass
class EligibilityDecision:
    eligible: bool
    reason: str
    source: str
    status: str
    conflict_status: ConflictStatus = "none"
    claim_family: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _explicitly_approved(fact: Any, campaign_context: CampaignContext) -> bool:
    """True only when an authoritative record explicitly marks marketing approval.

    Existence in project DB / RAG is not approval.
    """
    status = getattr(fact, "marketing_status", None)
    fact_id = str(getattr(fact, "fact_id", "") or "")
    key = str(getattr(fact, "key", "") or "")
    if fact_id and fact_id in campaign_context.explicitly_approved_fact_ids:
        return True
    if key and key in campaign_context.explicitly_approved_keys:
        return True
    return status == "approved"


def is_marketing_eligible(fact: Any, campaign_context: CampaignContext | None = None) -> EligibilityDecision:
    """ONE centralized eligibility check. All downstream consumers must use this.

    Financial claims are eligible ONLY if:
      (A) user supplied in the CURRENT campaign, or
      (B) canonical AND explicitly marketing-approved.
    Verified / RAG / spreadsheet / doc is not enough.
    """
    ctx = campaign_context or CampaignContext()
    source = str(getattr(fact, "source", "") or "unknown")
    status = str(getattr(fact, "marketing_status", "") or "unknown")
    derivation = str(getattr(fact, "derivation_type", "") or "unknown")
    key = str(getattr(fact, "key", "") or "")
    if hasattr(fact, "is_financial"):
        is_financial = bool(fact.is_financial)
    else:
        is_financial = is_financial_claim_key(key)
    conflict = str(getattr(fact, "conflict_status", "none") or "none")
    family = claim_family_for_key(key) if is_financial else None
    visibility = str(getattr(fact, "visibility", "unknown") or "unknown")

    if conflict in {"conflicting", "blocked_family"}:
        return EligibilityDecision(
            eligible=False,
            reason="conflicting_values",
            source=source,
            status=status,
            conflict_status=conflict,  # type: ignore[arg-type]
            claim_family=family,
        )

    if not is_financial:
        if visibility == "restricted":
            return EligibilityDecision(
                eligible=False,
                reason="restricted_visibility",
                source=source,
                status=status or "not_approved",
            )
        # Non-financial verified facts continue with visibility/confidence.
        return EligibilityDecision(
            eligible=True,
            reason="non_financial_visibility_ok",
            source=source,
            status=status or "approved",
        )

    # (A) user supplied in CURRENT campaign — campaign_only, never canonical.
    if (
        derivation == "user_supplied"
        and status == "campaign_only"
        and bool(getattr(fact, "is_campaign_scoped", False))
        and source == "user_campaign_input"
    ):
        return EligibilityDecision(
            eligible=True,
            reason="user_supplied_current_campaign",
            source=source,
            status="campaign_only",
            claim_family=family,
        )

    # (B) canonical AND explicitly marketing-approved.
    if derivation == "canonical" and _explicitly_approved(fact, ctx):
        if visibility == "restricted":
            return EligibilityDecision(
                eligible=False,
                reason="approved_but_restricted",
                source=source,
                status="approved",
                claim_family=family,
            )
        return EligibilityDecision(
            eligible=True,
            reason="canonical_marketing_approved",
            source=source,
            status="approved",
            claim_family=family,
        )

    if status == "requires_review":
        return EligibilityDecision(
            eligible=False,
            reason="requires_marketing_review",
            source=source,
            status="requires_review",
            claim_family=family,
        )
    if status == "not_approved":
        return EligibilityDecision(
            eligible=False,
            reason="not_marketing_approved",
            source=source,
            status="not_approved",
            claim_family=family,
        )
    if derivation in {"extracted", "inferred", "historical", "calculated"}:
        return EligibilityDecision(
            eligible=False,
            reason="derived_or_extracted_not_approved",
            source=source,
            status=status or "requires_review",
            claim_family=family,
        )
    if source in {"retrieved", "indexed_asset"}:
        return EligibilityDecision(
            eligible=False,
            reason="retrieved_not_marketing_approved",
            source=source,
            status=status or "requires_review",
            claim_family=family,
        )
    # Canonical / project_db financial without explicit approval.
    return EligibilityDecision(
        eligible=False,
        reason="verified_is_not_marketing_approved",
        source=source,
        status=status or "requires_review",
        claim_family=family,
    )


# Public alias matching the brief's centralized name.
isMarketingEligible = is_marketing_eligible


def detect_financial_conflicts(
    facts: list[Any],
    campaign_context: CampaignContext | None = None,
) -> dict[str, list[Any]]:
    """If a claim family has more than one distinct eligible-or-approvable value, block all.

    Do not guess which return / min-investment figure is 'the' one.
    User-supplied campaign values are authoritative for this campaign and are not
    blocked by unapproved RAG/DB siblings; conflicts among eligible values block both.
    """
    by_family: dict[str, list[Any]] = {}
    for fact in facts:
        if not bool(getattr(fact, "is_financial", False)):
            continue
        family = claim_family_for_key(str(getattr(fact, "key", "") or ""))
        if not family:
            continue
        by_family.setdefault(family, []).append(fact)

    conflicts: dict[str, list[Any]] = {}
    for family, group in by_family.items():
        # Conflict among values that would otherwise be eligible (A or B).
        would_be: list[Any] = []
        for fact in group:
            prior = getattr(fact, "conflict_status", "none")
            if prior in {"conflicting", "blocked_family"}:
                continue
            # Peek eligibility without conflict short-circuit by using a copy of status.
            decision = is_marketing_eligible(fact, campaign_context)
            if decision.eligible:
                would_be.append(fact)
        values = {normalize_claim_value(str(getattr(f, "display_value", "") or getattr(f, "value", "") or "")) for f in would_be}
        values.discard("")
        if len(values) > 1:
            conflicts[family] = list(would_be)
            for fact in would_be:
                fact.conflict_status = "conflicting"
            # Also mark other considered facts in the family for the trace.
            for fact in group:
                if getattr(fact, "conflict_status", "none") == "none":
                    fact.conflict_status = "blocked_family"
        elif len(values) == 0 and len({normalize_claim_value(str(getattr(f, "display_value", "") or "")) for f in group} - {""}) > 1:
            # Multiple unapproved values exist — do not pick one; record family conflict.
            conflicts[family] = list(group)
            for fact in group:
                fact.conflict_status = "blocked_family"
    return conflicts


def apply_conflicts_and_eligibility(
    facts: list[Any],
    campaign_context: CampaignContext | None = None,
) -> tuple[list[Any], list[dict[str, Any]], dict[str, list[Any]]]:
    """Run conflict detection then eligibility. Returns (safe_facts, trace, conflicts)."""
    ctx = campaign_context or CampaignContext()
    conflicts = detect_financial_conflicts(facts, ctx)
    safe: list[Any] = []
    trace: list[dict[str, Any]] = []
    for fact in facts:
        decision = is_marketing_eligible(fact, ctx)
        row = {
            "fact_id": getattr(fact, "fact_id", None),
            "fact": getattr(fact, "display_value", None) or getattr(fact, "value", None),
            "key": getattr(fact, "key", None),
            "source": decision.source,
            "source_reference": getattr(fact, "source_reference", None),
            "marketing_status": getattr(fact, "marketing_status", None),
            "derivation_type": getattr(fact, "derivation_type", None),
            "visibility": getattr(fact, "visibility", None),
            "eligible": decision.eligible,
            "eligibility": decision.reason,
            "rejection_reason": None if decision.eligible else decision.reason,
            "conflict_status": decision.conflict_status,
            "claim_family": decision.claim_family,
            "is_financial": bool(getattr(fact, "is_financial", False)),
            "campaign_scoped": bool(getattr(fact, "is_campaign_scoped", False)),
        }
        trace.append(row)
        if decision.eligible:
            safe.append(fact)
    return safe, trace, conflicts


def allowed_financial_tokens(facts: list[Any], campaign_context: CampaignContext | None = None) -> list[str]:
    ctx = campaign_context or CampaignContext()
    out: list[str] = []
    for fact in facts:
        if not bool(getattr(fact, "is_financial", False)):
            continue
        if not is_marketing_eligible(fact, ctx).eligible:
            continue
        for attr in ("display_value", "value"):
            token = str(getattr(fact, attr, "") or "").strip()
            if token and token not in out:
                out.append(token)
    return out


def blocked_financial_tokens(facts: list[Any], campaign_context: CampaignContext | None = None) -> list[str]:
    ctx = campaign_context or CampaignContext()
    out: list[str] = []
    for fact in facts:
        if not bool(getattr(fact, "is_financial", False)):
            continue
        if is_marketing_eligible(fact, ctx).eligible:
            continue
        for attr in ("display_value", "value"):
            token = str(getattr(fact, attr, "") or "").strip()
            if token and token not in out:
                out.append(token)
        for extra in extract_financial_tokens(str(getattr(fact, "display_value", "") or "")):
            if extra not in out:
                out.append(extra)
    return out


def text_contains_ineligible_financial(
    text: str,
    *,
    allowed_tokens: list[str],
    blocked_tokens: list[str] | None = None,
) -> bool:
    """True when copy/metrics text asserts a financial number that is not eligible."""
    t = text or ""
    if not t:
        return False
    allowed_blob = " ".join(allowed_tokens)
    for token in blocked_tokens or []:
        if token and token in t:
            if token not in allowed_blob and token.replace(" ", "") not in allowed_blob.replace(" ", ""):
                return True
    for m in _NUMERIC_CLAIM_RE.finditer(t):
        tok = m.group(0)
        compact = tok.replace(" ", "")
        if any(tok in a or compact in a.replace(" ", "") for a in allowed_tokens):
            continue
        return True
    return False


def strip_ineligible_financial_claims(
    text: str,
    *,
    allowed_tokens: list[str],
    blocked_tokens: list[str] | None = None,
) -> str:
    """Remove ineligible financial tokens from public copy. Do not invent replacements."""
    out = text or ""
    if not out:
        return out
    for token in blocked_tokens or []:
        if token and token in out:
            if not any(token in a for a in allowed_tokens):
                out = out.replace(token, "")
    for m in list(_NUMERIC_CLAIM_RE.finditer(out)):
        tok = m.group(0)
        compact = tok.replace(" ", "")
        if any(tok in a or compact in a.replace(" ", "") for a in allowed_tokens):
            continue
        out = out.replace(tok, "")
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip(" ,.;·-")


def retrieved_text_is_public_safe(
    text: str,
    *,
    allowed_tokens: list[str],
) -> bool:
    """Retrieved prose may inform reasoning; public copy may not assert ineligible numbers."""
    if not text_has_financial_claim(text):
        return True
    return not text_contains_ineligible_financial(text, allowed_tokens=allowed_tokens)
