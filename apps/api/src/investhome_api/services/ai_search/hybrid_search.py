"""Hybrid semantic + keyword search over AI Document chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.ai_index import AiDocument, AiDocumentStatus
from investhome_api.models.ai_search import AiChunk
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSyncStatus,
)
from investhome_api.services.ai_search.providers import get_embedding_provider
from investhome_api.services.ai_search.vector_store import get_vector_store

_TOKEN_RE = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜäöüÄÖÜ0-9]{2,}")

# Ranking weights (must stay documented for acceptance)
W_SEMANTIC = 0.45
W_KEYWORD = 0.30
W_PROJECT = 0.15
W_ACTIVITY = 0.10


@dataclass(frozen=True)
class SearchHit:
    asset_id: UUID | None
    document_id: UUID
    chunk_id: UUID
    chunk_order: int
    chunk_text: str
    score: float
    semantic_score: float
    keyword_score: float
    summary: str | None
    source: str
    file: str
    project_id: UUID
    category: str | None
    builders: list[str] | None


class ProjectScopeError(ValueError):
    """Raised when project filter mode is missing or unsafe."""


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def keyword_score(query: str, text: str) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    t_tokens = _tokenize(text)
    if not t_tokens:
        return 0.0
    overlap = len(q_tokens & t_tokens)
    # Jaccard-ish with slight boost for denser query coverage
    coverage = overlap / len(q_tokens)
    jaccard = overlap / len(q_tokens | t_tokens)
    return float(0.7 * coverage + 0.3 * jaccard)


def _activity_score(asset: CreativeStudioMediaAsset | None, now: datetime) -> float:
    if asset is None:
        return 0.35
    ts = asset.updated_at or asset.created_at
    if ts is None:
        return 0.35
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
    # Recent assets score higher; flat after ~180 days
    return float(max(0.05, 1.0 - min(age_days, 180.0) / 180.0))


def _project_relevance(
    doc_project_id: UUID,
    *,
    preferred_project_id: UUID | None,
    project_ids: set[UUID],
) -> float:
    if preferred_project_id and doc_project_id == preferred_project_id:
        return 1.0
    if doc_project_id in project_ids:
        return 0.85
    return 0.0


def resolve_project_filter(
    *,
    project_scope: str,
    project_id: UUID | None,
    project_ids: list[UUID] | None,
) -> tuple[str, list[UUID] | None]:
    """
    Mandatory project filter.

    Returns (mode, allowed_project_ids). ``None`` list means global (explicit only).
    """
    mode = (project_scope or "single").strip().lower()
    if mode == "single":
        if project_id is None:
            raise ProjectScopeError("project_id is required when project_scope=single")
        return "single", [project_id]
    if mode == "multi":
        ids = list(project_ids or [])
        if project_id is not None and project_id not in ids:
            ids.append(project_id)
        if not ids:
            raise ProjectScopeError("project_ids is required when project_scope=multi")
        return "multi", ids
    if mode == "global":
        # Explicit opt-in — never accidental cross-tenant
        return "global", None
    raise ProjectScopeError(f"invalid project_scope: {project_scope}")


def hybrid_search(
    db: Session,
    *,
    query: str,
    project_scope: str = "single",
    project_id: UUID | None = None,
    project_ids: list[UUID] | None = None,
    limit: int = 10,
    category: str | None = None,
    builder: str | None = None,
) -> list[SearchHit]:
    """
    Semantic + keyword hybrid ranking.

    Excludes inactive / non-ready / missing Drive assets from normal results.
    Never returns raw embedding vectors.
    """
    q = (query or "").strip()
    if not q:
        return []

    mode, allowed = resolve_project_filter(
        project_scope=project_scope,
        project_id=project_id,
        project_ids=project_ids,
    )
    limit = max(1, min(int(limit or 10), 100))

    doc_query = select(AiDocument).where(
        AiDocument.is_active.is_(True),
        AiDocument.index_status == AiDocumentStatus.READY.value,
    )
    if allowed is not None:
        doc_query = doc_query.where(AiDocument.project_id.in_(allowed))
    if category:
        doc_query = doc_query.where(AiDocument.category == category.strip())

    documents = list(db.scalars(doc_query).all())
    if builder:
        needle = builder.strip().lower()
        documents = [
            d
            for d in documents
            if d.builders
            and any(needle in str(b).lower() for b in d.builders)
        ]

    # Exclude missing Drive-linked assets
    eligible_docs: list[AiDocument] = []
    asset_map: dict[UUID, CreativeStudioMediaAsset] = {}
    for doc in documents:
        if doc.asset_id is None:
            eligible_docs.append(doc)
            continue
        asset = db.get(CreativeStudioMediaAsset, doc.asset_id)
        if asset is None:
            continue
        if asset.archived_at is not None:
            continue
        if asset.sync_status == MediaAssetSyncStatus.MISSING.value:
            continue
        asset_map[asset.id] = asset
        eligible_docs.append(doc)

    if not eligible_docs:
        return []

    doc_ids = [d.id for d in eligible_docs]
    doc_by_id = {d.id: d for d in eligible_docs}
    chunks = list(
        db.scalars(select(AiChunk).where(AiChunk.document_id.in_(doc_ids))).all()
    )
    if not chunks:
        return []

    chunk_by_id = {c.id: c for c in chunks}
    chunk_ids = list(chunk_by_id.keys())

    provider = get_embedding_provider()
    store = get_vector_store()
    query_vec = provider.embed([q]).vectors[0]
    semantic_hits = store.search(
        db,
        query_vector=query_vec,
        model=provider.model,
        chunk_ids=chunk_ids,
        limit=max(limit * 5, 50),
    )
    semantic_by_chunk = {h.chunk_id: max(0.0, h.score) for h in semantic_hits}

    # Also score keyword across all eligible chunks (coverage)
    now = datetime.now(UTC)
    allowed_set = set(allowed or [])
    preferred = project_id if mode == "single" else (project_id or (allowed[0] if allowed else None))

    ranked: list[SearchHit] = []
    for chunk in chunks:
        doc = doc_by_id.get(chunk.document_id)
        if doc is None:
            continue
        sem = semantic_by_chunk.get(chunk.id, 0.0)
        # Soft keyword floor even when not in top semantic
        kw = keyword_score(q, chunk.text)
        if sem <= 0.0 and kw <= 0.0:
            continue
        asset = asset_map.get(doc.asset_id) if doc.asset_id else None
        proj = _project_relevance(
            doc.project_id,
            preferred_project_id=preferred,
            project_ids=allowed_set if allowed is not None else {doc.project_id},
        )
        act = _activity_score(asset, now)
        score = (
            W_SEMANTIC * sem
            + W_KEYWORD * kw
            + W_PROJECT * proj
            + W_ACTIVITY * act
        )
        source = "drive" if doc.drive_file_id else ("asset" if doc.asset_id else "ai_document")
        ranked.append(
            SearchHit(
                asset_id=doc.asset_id,
                document_id=doc.id,
                chunk_id=chunk.id,
                chunk_order=chunk.chunk_order,
                chunk_text=chunk.text,
                score=round(score, 6),
                semantic_score=round(sem, 6),
                keyword_score=round(kw, 6),
                summary=doc.summary,
                source=source,
                file=doc.title or "",
                project_id=doc.project_id,
                category=doc.category,
                builders=list(doc.builders) if doc.builders else None,
            )
        )

    ranked.sort(key=lambda h: h.score, reverse=True)

    # Deduplicate by document — keep best chunk per document for cleaner results
    seen_docs: set[UUID] = set()
    unique: list[SearchHit] = []
    for hit in ranked:
        if hit.document_id in seen_docs:
            continue
        seen_docs.add(hit.document_id)
        unique.append(hit)
        if len(unique) >= limit:
            break
    return unique
