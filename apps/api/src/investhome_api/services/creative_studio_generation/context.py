"""Assemble structured Creative Studio generation context from project RAG."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.ai_index import AiDocument, AiDocumentStatus
from investhome_api.models.project import Project
from investhome_api.schemas.creative_studio_generation import (
    CreativeStudioBrandContext,
    CreativeStudioCitation,
    CreativeStudioGenerationContext,
    CreativeStudioProjectIdentity,
    CreativeStudioSelectedAsset,
)
from investhome_api.services.ai_search.hybrid_search import SearchHit
from investhome_api.services.project_assistant.prompt_builder import evidence_from_hits

# Real Drive brand folder — never invent brand rules when this is absent.
BRAND_CATEGORY = "01_BRAND"

# Patterns that must never enter generation context (demo / stock media).
_FORBIDDEN_MEDIA_RE = re.compile(
    r"(unsplash\.com|images\.unsplash|picsum\.photos|placehold\.co|placeholder\.com|"
    r"loremflickr|via\.placeholder|dummyimage\.com)",
    re.IGNORECASE,
)
_FORBIDDEN_KEYS = frozenset(
    {
        "unsplash",
        "mock_image",
        "mock_images",
        "demo_image",
        "demo_images",
        "stock_image",
        "stock_images",
        "placeholder_image",
        "placeholder_images",
    }
)


def sanitize_builder_context(raw: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Strip mock/Unsplash/stock media from optional builder_context.

    Returns (cleaned_context_or_None, warnings).
    """
    if not raw:
        return None, []
    warnings: list[str] = []
    cleaned = _sanitize_value(raw, warnings)
    if not isinstance(cleaned, dict):
        return None, warnings
    return cleaned, warnings


def _sanitize_value(value: Any, warnings: list[str]) -> Any:
    if isinstance(value, str):
        if _FORBIDDEN_MEDIA_RE.search(value):
            warnings.append("stripped_forbidden_media_url_from_builder_context")
            return None
        return value
    if isinstance(value, list):
        out = []
        for item in value:
            sanitized = _sanitize_value(item, warnings)
            if sanitized is not None:
                out.append(sanitized)
        return out
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_l = str(key).lower()
            if key_l in _FORBIDDEN_KEYS or "unsplash" in key_l:
                warnings.append(f"stripped_forbidden_builder_context_key:{key}")
                continue
            sanitized = _sanitize_value(item, warnings)
            if sanitized is not None:
                out[str(key)] = sanitized
        return out
    return value


def project_identity_from_model(project: Project) -> CreativeStudioProjectIdentity:
    return CreativeStudioProjectIdentity(
        project_id=project.id,
        project_code=project.project_code,
        project_name=project.project_name,
        project_type=getattr(project.project_type, "value", None) or str(project.project_type or ""),
        project_status=getattr(project.project_status, "value", None)
        or str(project.project_status or ""),
        city=project.city,
        country=project.country,
    )


def verified_facts_from_project(project: Project) -> list[str]:
    """Non-hallucinated identity facts from the Project row only."""
    facts: list[str] = [
        f"project_name={project.project_name}",
        f"project_code={project.project_code}",
    ]
    if project.city:
        facts.append(f"city={project.city}")
    if project.country:
        facts.append(f"country={project.country}")
    if project.address:
        facts.append(f"address={project.address}")
    if project.total_units is not None:
        facts.append(f"total_units={project.total_units}")
    ptype = getattr(project.project_type, "value", None) or project.project_type
    if ptype:
        facts.append(f"project_type={ptype}")
    pstatus = getattr(project.project_status, "value", None) or project.project_status
    if pstatus:
        facts.append(f"project_status={pstatus}")
    return facts


def citations_from_hits(hits: list[SearchHit]) -> list[CreativeStudioCitation]:
    out: list[CreativeStudioCitation] = []
    for hit in hits:
        out.append(
            CreativeStudioCitation(
                asset_id=hit.asset_id,
                document_id=hit.document_id,
                document_name=hit.file or "untitled",
                chunk_id=hit.chunk_id,
                chunk_reference=f"chunk:{hit.chunk_order}",
                chunk_order=hit.chunk_order,
                project_id=hit.project_id,
                score=float(hit.score or 0.0),
                excerpt=(hit.chunk_text or "")[:280] or None,
                category=hit.category,
            )
        )
    return out


def load_brand_context(db: Session, *, project_id: UUID) -> CreativeStudioBrandContext:
    """
    Brand context only from real indexed AI documents in brand category / filenames.

    Never invents cosmetic brand rules or demo brand profiles.
    """
    docs = list(
        db.scalars(
            select(AiDocument).where(
                AiDocument.project_id == project_id,
                AiDocument.is_active.is_(True),
                AiDocument.index_status == AiDocumentStatus.READY.value,
            )
        ).all()
    )
    brand_docs: list[AiDocument] = []
    for doc in docs:
        cat = (doc.category or "").strip()
        title = (doc.title or "").lower()
        if cat == BRAND_CATEGORY or "brand" in cat.lower() or "brand" in title:
            text = (doc.extracted_text or doc.summary or "").strip()
            if text:
                brand_docs.append(doc)

    if not brand_docs:
        return CreativeStudioBrandContext(
            available=False,
            reason="brand_context_unavailable",
            excerpts=[],
            document_ids=[],
            source_categories=[],
        )

    excerpts: list[str] = []
    doc_ids: list[UUID] = []
    cats: list[str] = []
    for doc in brand_docs[:5]:
        text = (doc.extracted_text or doc.summary or "").strip()
        excerpts.append(text[:600])
        doc_ids.append(doc.id)
        if doc.category and doc.category not in cats:
            cats.append(doc.category)

    return CreativeStudioBrandContext(
        available=True,
        reason=None,
        excerpts=excerpts,
        document_ids=doc_ids,
        source_categories=cats,
    )


def build_generation_context(
    *,
    project: Project,
    builder_type: str,
    language: str | None,
    hits: list[SearchHit],
    selected_assets: list[CreativeStudioSelectedAsset],
    brand_context: CreativeStudioBrandContext,
    extra_warnings: list[str] | None = None,
) -> CreativeStudioGenerationContext:
    warnings = list(extra_warnings or [])
    if not hits:
        warnings.append("insufficient_retrieved_content")
    if not brand_context.available:
        warnings.append("brand_context_unavailable")

    evidence = evidence_from_hits(hits)
    # Hard isolation check — never leak other projects into context
    for row in evidence:
        if str(row.get("project_id")) != str(project.id):
            raise ValueError("cross_project_evidence_leak")

    citations = citations_from_hits(hits)
    for cit in citations:
        if cit.project_id != project.id:
            raise ValueError("cross_project_citation_leak")

    return CreativeStudioGenerationContext(
        project_identity=project_identity_from_model(project),
        verified_facts=verified_facts_from_project(project),
        retrieved_content=evidence,
        selected_assets=selected_assets,
        citations=citations,
        brand_context=brand_context,
        builder_type=builder_type,
        language=language,
        warnings=warnings,
    )


def assert_context_has_no_forbidden_media(context: CreativeStudioGenerationContext) -> None:
    """Defense-in-depth: generation context must never contain Unsplash/mock media URLs."""
    blob = context.model_dump_json()
    if _FORBIDDEN_MEDIA_RE.search(blob):
        raise ValueError("forbidden_media_in_generation_context")
