"""Schemas for AI Project Assistant (RAG)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ProjectAssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    project_id: UUID | None = None
    project_ids: list[UUID] | None = None
    project_scope: str = Field(
        default="single",
        description="single | multi | global — global requires explicit mode",
    )
    conversation_id: UUID | None = None


class ProjectAssistantCitation(BaseModel):
    asset_id: UUID | None = None
    document_id: UUID
    document_name: str
    chunk_id: UUID
    chunk_reference: str
    chunk_order: int
    project_id: UUID
    score: float
    excerpt: str | None = None


class ProjectAssistantAssetRef(BaseModel):
    asset_id: UUID
    document_name: str
    project_id: UUID


class ProjectAssistantDocumentRef(BaseModel):
    document_id: UUID
    document_name: str
    project_id: UUID
    asset_id: UUID | None = None


class ProjectAssistantResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[ProjectAssistantCitation]
    assets: list[ProjectAssistantAssetRef]
    documents: list[ProjectAssistantDocumentRef]
    projects: list[UUID]
    search_time_ms: int
    latency_ms: int
    conversation_id: UUID
    provider: str
    model: str
    grounded: bool
