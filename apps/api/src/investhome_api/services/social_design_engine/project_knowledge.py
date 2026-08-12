"""Project Knowledge Package — assembled from existing project DB + RAG + assets.

Not a second knowledge system. Only populates fields that have supporting evidence.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from investhome_api.models.project import Project
from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.social_design_engine.ops import looks_like_rag_or_debug_copy


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return folded.strip().lower()


def _dec_str(value: Decimal | float | int | None) -> str | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.4f}".rstrip("0").rstrip(".")


def _money_display(value: Decimal | float | int | None, currency: str = "USD") -> str | None:
    raw = _dec_str(value)
    if raw is None:
        return None
    try:
        n = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if abs(n) >= 1000:
        grouped = f"{int(round(n)):,}"
    else:
        grouped = raw
    if (currency or "USD").upper() == "USD":
        return f"${grouped}"
    return f"{grouped} {currency}"


def _pct_display(value: Decimal | float | int | None) -> str | None:
    """Project DB stores ROI/IRR as fractions or percent — normalize carefully."""
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    # Heuristic: values <= 1 treated as fractions (0.14 → 14%)
    if 0 < abs(n) <= 1:
        n = n * 100
    if float(n).is_integer():
        return f"{int(n)}%"
    return f"{n:.2f}".rstrip("0").rstrip(".") + "%"


@dataclass
class SourceEvidence:
    source: str
    reference: str
    excerpt: str = ""


@dataclass
class ProjectKnowledgePackage:
    """Structured project knowledge for campaign planning. Sparse by design."""

    project_identity: dict[str, Any] = field(default_factory=dict)
    location: dict[str, Any] = field(default_factory=dict)
    investment: dict[str, Any] = field(default_factory=dict)
    pricing: dict[str, Any] = field(default_factory=dict)
    rental: dict[str, Any] = field(default_factory=dict)
    development: dict[str, Any] = field(default_factory=dict)
    amenities: list[str] = field(default_factory=list)
    neighborhood: dict[str, Any] = field(default_factory=dict)
    architecture: dict[str, Any] = field(default_factory=dict)
    availability: dict[str, Any] = field(default_factory=dict)
    media_assets: list[dict[str, Any]] = field(default_factory=list)
    source_evidence: list[SourceEvidence] = field(default_factory=list)
    populated_sections: list[str] = field(default_factory=list)


def _add_evidence(
    evidence: list[SourceEvidence],
    *,
    source: str,
    reference: str,
    excerpt: str = "",
) -> None:
    token = f"{source}:{reference}:{excerpt[:40]}"
    if any(f"{e.source}:{e.reference}:{e.excerpt[:40]}" == token for e in evidence):
        return
    evidence.append(SourceEvidence(source=source, reference=reference, excerpt=excerpt[:180]))


def _sentences_from_retrieved(
    retrieved: list[Any],
    *,
    terms: tuple[str, ...],
    limit: int = 4,
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in retrieved:
        if not isinstance(row, dict):
            continue
        name = str(row.get("document_name") or "").lower()
        if "metadata.json" in name or name.endswith(".json"):
            continue
        text = str(row.get("text") or row.get("excerpt") or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        sn = _norm(text)
        if terms and not any(term in sn for term in terms):
            continue
        sentence = text.split(".")[0].strip()
        if len(sentence) < 12:
            continue
        out.append((sentence[:220], name or "retrieved"))
        if len(out) >= limit:
            break
    return out


def build_project_knowledge_package(
    *,
    project: Project,
    context: CreativeStudioGenerationContext,
    media_candidates: list[SocialDesignMediaCandidate] | None = None,
) -> ProjectKnowledgePackage:
    """Assemble knowledge only from Project row + grounded retrieval + assets."""
    pkg = ProjectKnowledgePackage()
    evidence: list[SourceEvidence] = []
    retrieved = list(context.retrieved_content or [])

    # --- Identity (always from Project DB) ---
    identity = {
        "project_id": str(project.id),
        "project_name": project.project_name,
        "project_code": project.project_code,
    }
    if project.project_type is not None:
        identity["project_type"] = getattr(project.project_type, "value", None) or str(project.project_type)
    if project.project_status is not None:
        identity["project_status"] = getattr(project.project_status, "value", None) or str(
            project.project_status
        )
    pkg.project_identity = identity
    pkg.populated_sections.append("project_identity")
    _add_evidence(evidence, source="project_db", reference="projects.project_name", excerpt=project.project_name)

    # --- Location ---
    location: dict[str, Any] = {}
    for key, attr in (
        ("city", "city"),
        ("state", "state"),
        ("country", "country"),
        ("address", "address"),
        ("postal_code", "postal_code"),
    ):
        val = getattr(project, attr, None)
        if val:
            location[key] = val
            _add_evidence(evidence, source="project_db", reference=f"projects.{attr}", excerpt=str(val))
    if location:
        pkg.location = location
        pkg.populated_sections.append("location")

    # --- Investment (ONLY verified Project financial fields — never invent) ---
    investment: dict[str, Any] = {}
    currency = (project.currency or "USD").upper()
    irr = _pct_display(project.projected_irr)
    roi = _pct_display(project.projected_roi)
    if irr:
        investment["projected_irr"] = irr
        investment["projected_irr_raw"] = _dec_str(project.projected_irr)
        _add_evidence(evidence, source="project_db", reference="projects.projected_irr", excerpt=irr)
    if roi:
        investment["projected_roi"] = roi
        investment["projected_roi_raw"] = _dec_str(project.projected_roi)
        _add_evidence(evidence, source="project_db", reference="projects.projected_roi", excerpt=roi)
    equity = _money_display(project.equity_required, currency)
    if equity:
        investment["equity_required"] = equity
        _add_evidence(evidence, source="project_db", reference="projects.equity_required", excerpt=equity)
    profit = _money_display(project.projected_profit, currency)
    if profit:
        investment["projected_profit"] = profit
        _add_evidence(evidence, source="project_db", reference="projects.projected_profit", excerpt=profit)
    if investment:
        pkg.investment = investment
        pkg.populated_sections.append("investment")

    # --- Pricing ---
    pricing: dict[str, Any] = {}
    for key, attr in (
        ("acquisition_price", "acquisition_price"),
        ("current_project_value", "current_project_value"),
        ("projected_sale_value", "projected_sale_value"),
        ("total_development_cost", "total_development_cost"),
    ):
        disp = _money_display(getattr(project, attr, None), currency)
        if disp:
            pricing[key] = disp
            _add_evidence(evidence, source="project_db", reference=f"projects.{attr}", excerpt=disp)
    if pricing:
        pkg.pricing = pricing
        pkg.populated_sections.append("pricing")

    # --- Development ---
    development: dict[str, Any] = {}
    if project.total_units is not None:
        development["total_units"] = project.total_units
    if project.completion_percentage is not None:
        development["completion_percentage"] = _dec_str(project.completion_percentage)
    if project.development_stage is not None:
        development["development_stage"] = getattr(project.development_stage, "value", None) or str(
            project.development_stage
        )
    if project.target_completion_date is not None:
        development["target_completion_date"] = project.target_completion_date.isoformat()
    if development:
        pkg.development = development
        pkg.populated_sections.append("development")
        _add_evidence(evidence, source="project_db", reference="projects.development", excerpt=str(development)[:120])

    # --- Neighborhood / architecture / amenities from RAG (only when grounded) ---
    from investhome_api.services.social_design_engine.marketing_strategist import extract_neighborhood

    neighborhood_name = extract_neighborhood(
        retrieved,
        city=project.city or "",
        project_name=project.project_name or "",
    )
    neighborhood: dict[str, Any] = {}
    if neighborhood_name:
        neighborhood["name"] = neighborhood_name
        _add_evidence(evidence, source="retrieved", reference="neighborhood", excerpt=neighborhood_name)
    loc_lines = _sentences_from_retrieved(
        retrieved,
        terms=("location", "neighborhood", "district", "corridor", "washington", "central", "metro"),
    )
    if loc_lines:
        neighborhood["highlights"] = [s for s, _ in loc_lines]
        for sent, doc in loc_lines:
            _add_evidence(evidence, source="retrieved", reference=doc, excerpt=sent)
    if neighborhood:
        pkg.neighborhood = neighborhood
        pkg.populated_sections.append("neighborhood")

    arch_lines = _sentences_from_retrieved(
        retrieved,
        terms=("architecture", "architectural", "facade", "façade", "material", "craft", "design language"),
    )
    if arch_lines:
        pkg.architecture = {"highlights": [s for s, _ in arch_lines]}
        pkg.populated_sections.append("architecture")
        for sent, doc in arch_lines:
            _add_evidence(evidence, source="retrieved", reference=doc, excerpt=sent)

    amenity_lines = _sentences_from_retrieved(
        retrieved,
        terms=("amenity", "amenities", "spa", "pool", "rooftop", "lobby", "fitness"),
    )
    if amenity_lines:
        pkg.amenities = [s for s, _ in amenity_lines]
        pkg.populated_sections.append("amenities")
        for sent, doc in amenity_lines:
            _add_evidence(evidence, source="retrieved", reference=doc, excerpt=sent)

    # Soft value proposition prose (non-financial) from marketing docs
    value_lines = _sentences_from_retrieved(
        retrieved,
        terms=("investment", "investor", "opportunity", "value", "equity", "portfolio"),
        limit=3,
    )
    # Only attach as evidence — financial numbers stay in investment section
    for sent, doc in value_lines:
        if re.search(r"\d+\s*%", sent) or re.search(r"\$\s*\d", sent):
            # Financial claims from RAG are NOT auto-promoted to verified investment facts.
            _add_evidence(evidence, source="retrieved_unverified_financial", reference=doc, excerpt=sent)
        else:
            _add_evidence(evidence, source="retrieved", reference=doc, excerpt=sent)

    # Availability — only if units known
    if project.total_units is not None or project.residential_units is not None:
        avail: dict[str, Any] = {}
        if project.total_units is not None:
            avail["total_units"] = project.total_units
        if project.residential_units is not None:
            avail["residential_units"] = project.residential_units
        pkg.availability = avail
        pkg.populated_sections.append("availability")

    # Media assets (IDs + semantic hints only)
    media: list[dict[str, Any]] = []
    for cand in media_candidates or []:
        media.append(
            {
                "asset_id": str(cand.asset_id),
                "filename": cand.filename,
                "folder_category": cand.folder_category,
                "tags": list(cand.tags or []),
                "score": cand.score,
            }
        )
    if media:
        pkg.media_assets = media[:24]
        pkg.populated_sections.append("media_assets")

    pkg.source_evidence = evidence[:40]
    if evidence:
        pkg.populated_sections.append("source_evidence")

    # Dedup populated sections
    pkg.populated_sections = list(dict.fromkeys(pkg.populated_sections))
    return pkg


def project_knowledge_to_dict(pkg: ProjectKnowledgePackage) -> dict[str, Any]:
    data = asdict(pkg)
    return data


def knowledge_has_verified_financial(pkg: ProjectKnowledgePackage, key: str) -> bool:
    inv = pkg.investment or {}
    mapping = {
        "irr": "projected_irr",
        "roi": "projected_roi",
        "profit": "projected_profit",
        "min_investment": "equity_required",
        "target_return": "projected_roi",
        "yield": "projected_roi",
    }
    field = mapping.get(key)
    if not field:
        return False
    return bool(inv.get(field))
