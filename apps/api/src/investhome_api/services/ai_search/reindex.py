"""Incremental chunk + embedding reindex for AI Documents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.ai_index import AiDocument, AiDocumentStatus
from investhome_api.models.ai_search import AiChunk, AiEmbedding
from investhome_api.services.ai_search.chunking import (
    CHUNK_MAX_CHARS,
    CHUNK_MIN_CHARS,
    build_chunks,
)
from investhome_api.services.ai_search.providers import EmbeddingProvider, get_embedding_provider
from investhome_api.services.ai_search.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def sync_document_chunks(
    db: Session,
    document: AiDocument,
    *,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> list[AiChunk]:
    """Upsert chunks for a document; delete removed orders. Returns current chunks."""
    settings = get_settings()
    min_c = min_chars if min_chars is not None else settings.ai_search_chunk_min_chars
    max_c = max_chars if max_chars is not None else settings.ai_search_chunk_max_chars
    min_c = min_c or CHUNK_MIN_CHARS
    max_c = max_c or CHUNK_MAX_CHARS

    text = document.extracted_text or ""
    drafts = build_chunks(text, min_chars=min_c, max_chars=max_c)
    existing = {
        c.chunk_order: c
        for c in db.scalars(
            select(AiChunk).where(AiChunk.document_id == document.id)
        ).all()
    }
    keep_orders: set[int] = set()
    result: list[AiChunk] = []

    for draft in drafts:
        keep_orders.add(draft.chunk_order)
        row = existing.get(draft.chunk_order)
        if row is not None and row.checksum == draft.checksum and row.text == draft.text:
            result.append(row)
            continue
        if row is not None:
            row.text = draft.text
            row.checksum = draft.checksum
            row.updated_at = _utcnow()
            result.append(row)
        else:
            row = AiChunk(
                id=uuid4(),
                document_id=document.id,
                chunk_order=draft.chunk_order,
                text=draft.text,
                checksum=draft.checksum,
            )
            db.add(row)
            result.append(row)

    # Remove stale chunk orders (+ embeddings)
    stale_ids = [row.id for order, row in existing.items() if order not in keep_orders]
    if stale_ids:
        store = get_vector_store()
        store.delete_for_chunks(db, stale_ids)
        for order, row in existing.items():
            if order not in keep_orders:
                db.delete(row)

    db.flush()
    return result


def embed_new_or_changed_chunks(
    db: Session,
    chunks: list[AiChunk],
    *,
    provider: EmbeddingProvider | None = None,
    store: VectorStore | None = None,
    batch_size: int | None = None,
) -> dict[str, int]:
    """Embed only chunks missing an embedding or with changed checksum. No duplicates."""
    provider = provider or get_embedding_provider()
    store = store or get_vector_store()
    settings = get_settings()
    batch = batch_size or settings.embedding_batch_size or 32

    stats = {"embedded": 0, "skipped": 0, "batches": 0}
    if not chunks:
        return stats

    model = provider.model
    pending: list[AiChunk] = []
    for chunk in chunks:
        existing = db.scalar(
            select(AiEmbedding).where(
                AiEmbedding.chunk_id == chunk.id,
                AiEmbedding.model == model,
            )
        )
        if existing is not None and existing.checksum == chunk.checksum:
            stats["skipped"] += 1
            continue
        pending.append(chunk)

    for i in range(0, len(pending), batch):
        group = pending[i : i + batch]
        result = provider.embed([c.text for c in group])
        stats["batches"] += 1
        for chunk, vector in zip(group, result.vectors, strict=True):
            store.upsert(
                db,
                chunk_id=chunk.id,
                provider=result.provider,
                model=result.model,
                dimensions=result.dimensions,
                vector=vector,
                checksum=chunk.checksum,
            )
            stats["embedded"] += 1
    db.flush()
    return stats


def remove_document_vectors(db: Session, document_id: UUID) -> int:
    """Delete all chunks (and embeddings) for a document."""
    chunks = list(db.scalars(select(AiChunk).where(AiChunk.document_id == document_id)).all())
    if not chunks:
        return 0
    store = get_vector_store()
    store.delete_for_chunks(db, [c.id for c in chunks])
    count = len(chunks)
    for chunk in chunks:
        db.delete(chunk)
    db.flush()
    return count


def reindex_document(
    db: Session,
    document_id: UUID,
    *,
    provider: EmbeddingProvider | None = None,
    store: VectorStore | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Full incremental reindex for one AI document (chunks + embeddings)."""
    doc = db.get(AiDocument, document_id)
    if doc is None:
        return {"ok": False, "reason": "not_found"}

    if (
        not doc.is_active
        or doc.index_status != AiDocumentStatus.READY.value
        or not (doc.extracted_text or "").strip()
    ):
        removed = remove_document_vectors(db, document_id)
        return {"ok": True, "removed": removed, "reason": "inactive_or_empty"}

    chunks = sync_document_chunks(db, doc)
    if force:
        # Force re-embed: clear checksum match by deleting embeddings for this model
        emb_provider = provider or get_embedding_provider()
        for chunk in chunks:
            existing = db.scalar(
                select(AiEmbedding).where(
                    AiEmbedding.chunk_id == chunk.id,
                    AiEmbedding.model == emb_provider.model,
                )
            )
            if existing is not None:
                db.delete(existing)
        db.flush()

    embed_stats = embed_new_or_changed_chunks(
        db, chunks, provider=provider, store=store
    )
    return {
        "ok": True,
        "document_id": str(document_id),
        "chunks": len(chunks),
        **embed_stats,
    }


def reindex_after_ai_document_update(db: Session, document: AiDocument) -> None:
    """Additive hook after AI Index pipeline updates a document."""
    try:
        if (
            document.is_active
            and document.index_status == AiDocumentStatus.READY.value
            and (document.extracted_text or "").strip()
        ):
            reindex_document(db, document.id)
        else:
            remove_document_vectors(db, document.id)
    except Exception:  # noqa: BLE001
        logger.warning(
            "ai_search_reindex_hook_failed",
            extra={"document_id": str(document.id)},
            exc_info=True,
        )


def reindex_project_vectors(
    db: Session,
    project_id: UUID,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Reindex all ready AI documents for a project."""
    docs = list(
        db.scalars(
            select(AiDocument).where(
                AiDocument.project_id == project_id,
                AiDocument.is_active.is_(True),
                AiDocument.index_status == AiDocumentStatus.READY.value,
            )
        ).all()
    )
    stats = {"documents": 0, "chunks": 0, "embedded": 0, "skipped": 0, "errors": 0}
    provider = get_embedding_provider()
    store = get_vector_store()
    for doc in docs:
        try:
            result = reindex_document(
                db, doc.id, provider=provider, store=store, force=force
            )
            if result.get("ok"):
                stats["documents"] += 1
                stats["chunks"] += int(result.get("chunks") or 0)
                stats["embedded"] += int(result.get("embedded") or 0)
                stats["skipped"] += int(result.get("skipped") or 0)
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
            logger.warning("ai_search_project_reindex_failed", exc_info=True)
    return stats
