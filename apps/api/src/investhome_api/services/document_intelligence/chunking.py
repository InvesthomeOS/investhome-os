"""Document chunking for search and Q&A readiness."""

from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from investhome_api.models.document_intelligence import DocumentChunk
from investhome_api.services.document_intelligence.types import TextSegment


MAX_CHUNK_CHARS = 3000


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_chunks_from_segments(
    segments: list[TextSegment],
) -> list[tuple[str, str, int]]:
    """Return list of (content, source_reference, token_count)."""
    chunks: list[tuple[str, str, int]] = []
    buffer = ""
    buffer_ref = ""
    for segment in segments:
        ref = segment.source.label()
        piece = segment.text.strip()
        if not piece:
            continue
        candidate = f"{buffer}\n\n{piece}".strip() if buffer else piece
        if len(candidate) > MAX_CHUNK_CHARS and buffer:
            chunks.append((buffer, buffer_ref, estimate_tokens(buffer)))
            buffer = piece
            buffer_ref = ref
        else:
            buffer = candidate
            buffer_ref = ref if not buffer_ref else f"{buffer_ref}; {ref}"
    if buffer:
        chunks.append((buffer, buffer_ref, estimate_tokens(buffer)))
    return chunks


def persist_chunks(
    db: Session,
    *,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    analysis_id: uuid.UUID,
    segments: list[TextSegment],
) -> list[DocumentChunk]:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_version_id == version_id))
    db.flush()
    built = build_chunks_from_segments(segments)
    saved: list[DocumentChunk] = []
    for index, (content, ref, tokens) in enumerate(built):
        chunk = DocumentChunk(
            document_id=document_id,
            document_version_id=version_id,
            analysis_id=analysis_id,
            chunk_index=index,
            content=content,
            source_reference=ref,
            token_count=tokens,
        )
        db.add(chunk)
        saved.append(chunk)
    db.flush()
    return saved
