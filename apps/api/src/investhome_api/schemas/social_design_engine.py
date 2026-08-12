"""Schemas for Social Media Builder AI Design Engine (Phase 1)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from investhome_api.schemas.creative_studio_generation import (
    CreativeStudioBrandContext,
    CreativeStudioCitation,
)

DesignMode = Literal["create", "edit"]

DESIGN_OP_TYPES: frozenset[str] = frozenset(
    {
        "CREATE_POST",
        "SET_FORMAT",
        "ADD_TEXT",
        "UPDATE_TEXT",
        "DELETE_ELEMENT",
        "ADD_IMAGE",
        "REPLACE_IMAGE",
        "ADD_CTA",
        "UPDATE_CTA",
        "ADD_METRIC_GROUP",
        "UPDATE_METRIC_GROUP",
        "MOVE_ELEMENT",
        "RESIZE_ELEMENT",
        "ALIGN_ELEMENT",
        "UPDATE_STYLE",
        "SET_BACKGROUND",
        "SET_Z_INDEX",
        "APPLY_LAYOUT_INTENT",
    }
)


class SocialDesignOp(BaseModel):
    """Strict P0 design operation — LLM proposes; server validates + applies."""

    op: str = Field(..., min_length=1, max_length=40)
    linked_project_id: UUID
    post_id: str = Field(..., min_length=1, max_length=120)
    element_id: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class SocialDesignMediaCandidate(BaseModel):
    asset_id: UUID
    filename: str
    content_type: str | None = None
    folder_id: UUID | None = None
    folder_category: str | None = None
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0
    linked_project_id: UUID


class SocialDesignDraftState(BaseModel):
    """Current SMB canvas state sent for create/edit planning."""

    posts: list[dict[str, Any]] = Field(default_factory=list)
    selected_post_id: str | None = None


class SocialDesignRequest(BaseModel):
    linked_project_id: UUID
    instruction: str = Field(..., min_length=1, max_length=8000)
    mode: DesignMode = "create"
    draft: SocialDesignDraftState = Field(default_factory=SocialDesignDraftState)
    selected_asset_ids: list[UUID] = Field(default_factory=list)
    language: str | None = Field(default=None, max_length=16)
    builder_context: dict[str, Any] | None = None


class SocialDesignRejectedOp(BaseModel):
    op: dict[str, Any]
    reason: str


class SocialDesignGenerationMeta(BaseModel):
    """Generation metadata — never written into design text elements."""

    citations: list[CreativeStudioCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    grounded: bool = False
    retrieval_confidence: float = 0.0
    asset_ids_used: list[UUID] = Field(default_factory=list)
    provider: str
    model: str
    brand_context: CreativeStudioBrandContext
    brand_context_status: str
    search_time_ms: int = 0
    latency_ms: int = 0
    mode: DesignMode
    planner: str = "llm"
    # Edit-intent audit (never rendered on canvas)
    intents: list[str] = Field(default_factory=list)
    intent_targets: list[str] = Field(default_factory=list)
    applied_intents: list[str] = Field(default_factory=list)
    rejected_reasons: list[str] = Field(default_factory=list)
    copy_protected: bool = False
    generated_by: str | None = None
    project_id: UUID | None = None
    user_prompt: str | None = None
    generation_intent: dict[str, Any] | None = None
    source_document_ids: list[UUID] = Field(default_factory=list)
    selected_asset_ids: list[UUID] = Field(default_factory=list)
    generated_at: str | None = None
    content_package: dict[str, Any] | None = None
    design_plan: dict[str, Any] | None = None
    campaign_facts: list[dict[str, Any]] = Field(default_factory=list)
    structured_metrics: list[dict[str, Any]] = Field(default_factory=list)
    metric_group: dict[str, Any] | None = None
    creative_concept: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    marketing_strategy: dict[str, Any] | None = None
    copy_quality: dict[str, Any] | None = None
    headline_candidates: list[dict[str, Any]] = Field(default_factory=list)


class SocialDesignResponse(BaseModel):
    linked_project_id: UUID
    mode: DesignMode
    ops: list[SocialDesignOp] = Field(default_factory=list)
    rejected_ops: list[SocialDesignRejectedOp] = Field(default_factory=list)
    posts: list[dict[str, Any]] = Field(default_factory=list)
    selected_post_id: str | None = None
    media_candidates: list[SocialDesignMediaCandidate] = Field(default_factory=list)
    meta: SocialDesignGenerationMeta
    generated_content: str = ""
