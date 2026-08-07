"""Vector storage abstraction — local JSON today; pgvector/Qdrant/etc. later."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import Settings, get_settings
from investhome_api.models.ai_search import AiEmbedding


@dataclass(frozen=True)
class VectorHit:
    chunk_id: UUID
    embedding_id: UUID
    score: float
    model: str


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / (na * nb))


class VectorStore(ABC):
    """Backend-agnostic vector index. Implementations must never mutate Drive."""

    name: str

    @abstractmethod
    def upsert(
        self,
        db: Session,
        *,
        chunk_id: UUID,
        provider: str,
        model: str,
        dimensions: int,
        vector: list[float],
        checksum: str,
    ) -> AiEmbedding:
        """Insert or replace embedding for (chunk_id, model). Skip if checksum matches."""

    @abstractmethod
    def delete_for_chunks(self, db: Session, chunk_ids: list[UUID]) -> int:
        """Remove embeddings for deleted chunks. Returns count removed."""

    @abstractmethod
    def search(
        self,
        db: Session,
        *,
        query_vector: list[float],
        model: str,
        chunk_ids: list[UUID] | None = None,
        limit: int = 50,
    ) -> list[VectorHit]:
        """Nearest-neighbor style search over stored vectors (filtered by chunk_ids when set)."""


class LocalJsonVectorStore(VectorStore):
    """Stores vectors in ``ai_embeddings.vector`` JSON; cosine scan in-process.

    Suitable for local/dev, SQLite tests, and moderate corpora. Production can
    swap to PgVectorStore / Qdrant / Pinecone / Weaviate without changing callers.
    """

    name = "local"

    def upsert(
        self,
        db: Session,
        *,
        chunk_id: UUID,
        provider: str,
        model: str,
        dimensions: int,
        vector: list[float],
        checksum: str,
    ) -> AiEmbedding:
        existing = db.scalar(
            select(AiEmbedding).where(
                AiEmbedding.chunk_id == chunk_id,
                AiEmbedding.model == model,
            )
        )
        if existing is not None and existing.checksum == checksum:
            return existing
        if existing is not None:
            existing.provider = provider
            existing.dimensions = dimensions
            existing.vector = list(vector)
            existing.checksum = checksum
            db.flush()
            return existing
        row = AiEmbedding(
            chunk_id=chunk_id,
            provider=provider,
            model=model,
            dimensions=dimensions,
            vector=list(vector),
            checksum=checksum,
        )
        db.add(row)
        db.flush()
        return row

    def delete_for_chunks(self, db: Session, chunk_ids: list[UUID]) -> int:
        if not chunk_ids:
            return 0
        rows = list(
            db.scalars(select(AiEmbedding).where(AiEmbedding.chunk_id.in_(chunk_ids))).all()
        )
        for row in rows:
            db.delete(row)
        db.flush()
        return len(rows)

    def search(
        self,
        db: Session,
        *,
        query_vector: list[float],
        model: str,
        chunk_ids: list[UUID] | None = None,
        limit: int = 50,
    ) -> list[VectorHit]:
        query = select(AiEmbedding).where(AiEmbedding.model == model)
        if chunk_ids is not None:
            if not chunk_ids:
                return []
            query = query.where(AiEmbedding.chunk_id.in_(chunk_ids))
        rows = list(db.scalars(query).all())
        scored: list[VectorHit] = []
        for row in rows:
            vec = row.vector if isinstance(row.vector, list) else []
            score = cosine_similarity(query_vector, [float(v) for v in vec])
            scored.append(
                VectorHit(
                    chunk_id=row.chunk_id,
                    embedding_id=row.id,
                    score=score,
                    model=row.model,
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[: max(1, limit)]


class PgVectorStore(LocalJsonVectorStore):
    """Placeholder production path — currently delegates to JSON cosine scan.

    When ``pgvector`` is installed and a VECTOR column migration is applied,
    override ``search`` to use ``<=>`` / ``<->`` operators. Interface is stable.
    """

    name = "pgvector"


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    backend = (settings.vector_store_backend or "local").strip().lower()
    if backend in {"pgvector", "postgres"}:
        return PgVectorStore()
    # qdrant / pinecone / weaviate reserved — fall back to local until wired
    return LocalJsonVectorStore()
