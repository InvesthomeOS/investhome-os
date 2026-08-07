"""Schemas for AI semantic / hybrid search (no raw vectors)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AiSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    project_id: UUID | None = None
    project_ids: list[UUID] | None = None
    project_scope: str = Field(
        default="single",
        description="single | multi | global — global requires explicit mode",
    )
    limit: int = Field(default=10, ge=1, le=100)
    category: str | None = None
    builder: str | None = None


class AiSearchResultItem(BaseModel):
    asset_id: UUID | None = None
    document_id: UUID
    chunk_id: UUID
    chunk: str
    chunk_order: int
    score: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    summary: str | None = None
    source: str
    file: str
    project_id: UUID
    category: str | None = None
    builders: list[str] | None = None


class AiSearchResponse(BaseModel):
    query: str
    project_scope: str
    total: int
    items: list[AiSearchResultItem]
