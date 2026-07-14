"""Global search API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchHighlight(BaseModel):
    field: str
    snippet: str


class SearchResultItem(BaseModel):
    entity_type: str
    entity_id: UUID
    title: str
    subtitle: str | None = None
    preview: str | None = None
    module: str
    link_query: dict[str, str] = Field(default_factory=dict)
    status: str | None = None
    assigned_to: str | None = None
    created_at: datetime | None = None
    score: float = 0.0
    highlights: list[SearchHighlight] = Field(default_factory=list)


class SearchGroup(BaseModel):
    entity_type: str
    label_key: str
    items: list[SearchResultItem]
    total: int


class SearchResponse(BaseModel):
    query: str
    groups: list[SearchGroup]
    total: int
    took_ms: int
