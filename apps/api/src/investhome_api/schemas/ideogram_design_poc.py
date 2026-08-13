"""Schemas for the Ideogram External Design AI proof of concept."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from investhome_api.schemas.social_design_engine import SocialDesignDraftState

IdeogramVariant = Literal["A", "B", "C"]
IdeogramAspectRatio = Literal["1:1"]


class IdeogramProviderStatusResponse(BaseModel):
    available: bool
    configured: bool
    enabled: bool
    provider: str = "ideogram"
    model: str
    remix_endpoint: str
    generate_endpoint: str
    reason: str | None = None


class IdeogramDesignRequest(BaseModel):
    linked_project_id: UUID
    instruction: str = Field(..., min_length=1, max_length=8000)
    aspect_ratio: IdeogramAspectRatio = "1:1"
    count: int = Field(default=3, ge=1, le=3)
    language: str | None = Field(default=None, max_length=16)
    selected_asset_ids: list[UUID] = Field(default_factory=list)
    draft: SocialDesignDraftState = Field(default_factory=SocialDesignDraftState)
    builder_context: dict[str, Any] | None = None
    regenerate_variant: IdeogramVariant | None = None
    session_id: str | None = Field(default=None, max_length=80)


class IdeogramOutput(BaseModel):
    variant: IdeogramVariant
    art_direction: str
    remote_url: str | None = None
    local_asset_id: UUID
    local_asset_url: str
    provider: str = "ideogram"
    provider_generation_id: str | None = None
    original_remote_url: str | None = None
    seed: int | None = None
    resolution: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdeogramSourceImage(BaseModel):
    asset_id: UUID
    filename: str
    content_type: str | None = None
    folder_category: str | None = None
    tags: list[str] = Field(default_factory=list)


class IdeogramDesignResponse(BaseModel):
    provider: str = "ideogram"
    model: str
    endpoint: str
    session_id: str
    linked_project_id: UUID
    campaign_context_id: str | None = None
    generation_context_id: str
    aspect_ratio: IdeogramAspectRatio = "1:1"
    source_image: IdeogramSourceImage
    brief: dict[str, Any] = Field(default_factory=dict)
    outputs: list[IdeogramOutput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider_call_count: int = 0
    latency_ms: int = 0
