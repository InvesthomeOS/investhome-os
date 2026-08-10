"""Schemas for Creative Studio shared AI generation (Phase 1 foundation)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Align with CreativeStudioDocumentType values — shared across all builders.
CREATIVE_STUDIO_BUILDER_TYPES: frozenset[str] = frozenset(
    {
        "website",
        "landing",
        "blog",
        "email",
        "social",
        "ads",
        "proposal",
        "presentation",
        "brochure",
        "video",
        "image",
        "architectural",
    }
)


class CreativeStudioGenerateRequest(BaseModel):
    """Shared generation request — one API for every Creative Studio builder."""

    linked_project_id: UUID = Field(
        ...,
        description="Mandatory CRM / OS project id. Generation is project-scoped only.",
    )
    builder_type: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="Builder / document type (e.g. blog, email, social, proposal).",
    )
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User generation instruction.",
    )
    selected_asset_ids: list[UUID] = Field(
        default_factory=list,
        description="Media Library asset ids that must belong to linked_project_id.",
    )
    language: str | None = Field(
        default=None,
        max_length=16,
        description="Optional output language hint (e.g. en, tr).",
    )
    builder_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional builder-specific structured context (no mock/Unsplash media).",
    )


class CreativeStudioCitation(BaseModel):
    asset_id: UUID | None = None
    document_id: UUID
    document_name: str
    chunk_id: UUID
    chunk_reference: str
    chunk_order: int
    project_id: UUID
    score: float
    excerpt: str | None = None
    category: str | None = None


class CreativeStudioSelectedAsset(BaseModel):
    asset_id: UUID
    filename: str
    project_id: UUID
    folder_category: str | None = None
    content_type: str | None = None


class CreativeStudioBrandContext(BaseModel):
    """Brand rules only when real indexed brand documents exist for the project."""

    available: bool
    reason: str | None = None
    excerpts: list[str] = Field(default_factory=list)
    document_ids: list[UUID] = Field(default_factory=list)
    source_categories: list[str] = Field(default_factory=list)


class CreativeStudioProjectIdentity(BaseModel):
    project_id: UUID
    project_code: str
    project_name: str
    project_type: str | None = None
    project_status: str | None = None
    city: str | None = None
    country: str | None = None


class CreativeStudioGenerationContext(BaseModel):
    """Structured context assembled before LLM generation — never includes mock/Unsplash."""

    project_identity: CreativeStudioProjectIdentity
    verified_facts: list[str]
    retrieved_content: list[dict[str, Any]]
    selected_assets: list[CreativeStudioSelectedAsset]
    citations: list[CreativeStudioCitation]
    brand_context: CreativeStudioBrandContext
    builder_type: str
    language: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CreativeStudioGenerateResponse(BaseModel):
    generated_content: str
    project_id: UUID
    builder_type: str
    asset_ids_used: list[UUID]
    citations: list[CreativeStudioCitation]
    retrieval_confidence: float
    warnings: list[str] = Field(default_factory=list)
    brand_context: CreativeStudioBrandContext
    grounded: bool
    provider: str
    model: str
    search_time_ms: int
    latency_ms: int
    context: CreativeStudioGenerationContext | None = None
