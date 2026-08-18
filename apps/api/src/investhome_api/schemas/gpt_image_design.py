"""Schemas for GPT Image Social Media Builder visual engine."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from investhome_api.schemas.social_design_engine import SocialDesignDraftState

GptImageProvider = Literal["gpt-image", "openai-image"]
GptImageCampaignMode = Literal["project", "general"]
GptImageAspectRatio = Literal["1:1", "4:5", "16:9", "9:16"]


class GptImageProviderStatusResponse(BaseModel):
    available: bool
    configured: bool
    enabled: bool
    provider: str = "gpt-image"
    model: str
    edits_endpoint: str
    generate_endpoint: str
    reason: str | None = None


class GptImageDesignRequest(BaseModel):
    linked_project_id: UUID | None = None
    instruction: str = Field(..., min_length=1, max_length=8000)
    design_provider: GptImageProvider = "gpt-image"
    campaign_mode: GptImageCampaignMode = "project"
    aspect_ratio: GptImageAspectRatio | None = None
    format_preset: str | None = Field(default=None, max_length=32)
    language: str | None = Field(default=None, max_length=16)
    selected_asset_ids: list[UUID] = Field(default_factory=list)
    draft: SocialDesignDraftState = Field(default_factory=SocialDesignDraftState)
    builder_context: dict[str, Any] | None = None
    session_id: str | None = Field(default=None, max_length=80)


class GptImageOutput(BaseModel):
    local_asset_id: UUID
    local_asset_url: str
    provider: str = "gpt-image"
    provider_generation_id: str | None = None
    resolution: str | None = None
    canvas_width: int | None = None
    canvas_height: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    # SMB editable layers (Native Art Director element shape). Optional for general mode.
    layers: list[dict[str, Any]] = Field(default_factory=list)
    composition_base_asset_id: UUID | None = None
    composition_warnings: list[str] = Field(default_factory=list)


class GptImageSourceImage(BaseModel):
    asset_id: UUID
    filename: str
    content_type: str | None = None
    folder_category: str | None = None
    tags: list[str] = Field(default_factory=list)
    role: str = "source"


class GptImageDesignResponse(BaseModel):
    provider: str = "gpt-image"
    model: str
    endpoint: str
    campaign_mode: GptImageCampaignMode
    session_id: str
    linked_project_id: UUID | None = None
    campaign_context_id: str | None = None
    generation_context_id: str
    aspect_ratio: str
    format_preset: str
    source_image: GptImageSourceImage | None = None
    extra_images: list[GptImageSourceImage] = Field(default_factory=list)
    brief: dict[str, Any] = Field(default_factory=dict)
    outputs: list[GptImageOutput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider_call_count: int = 0
    latency_ms: int = 0
