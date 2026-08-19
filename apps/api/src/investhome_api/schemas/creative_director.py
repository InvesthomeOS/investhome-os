"""Schemas for Creative Director campaign brief + context."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreativeDirectorCampaignRequest(BaseModel):
    project_id: UUID
    brief: str = Field(..., min_length=1, max_length=12000)
    mode: Literal["project", "general"] = "project"
    language: str | None = Field(default=None, max_length=16)
    # Test/report helper: force video capability into required list to prove missing reporting.
    include_video_capability: bool = False


class CreativeDirectorReviseRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=8000)


class CreativeDirectorCampaignResponse(BaseModel):
    campaign_id: UUID
    project_id: UUID
    brief: dict[str, Any] = Field(default_factory=dict)
    campaign_context: dict[str, Any] = Field(default_factory=dict)


class CreativeDirectorGenerateAdRequest(BaseModel):
    """Optional overrides for MASTER ad generation from Campaign Context."""

    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: Literal["1:1", "4:5", "16:9", "9:16"] | None = "4:5"
    format_preset: str | None = Field(default="portrait", max_length=32)


class CreativeDirectorGenerateAdResponse(BaseModel):
    campaign_id: UUID
    project_id: UUID
    language: str
    aspect_ratio: str
    format_preset: str
    interior_asset_id: UUID
    logo_asset_id: UUID
    final_asset_id: UUID
    final_asset_url: str
    composition_base_asset_id: UUID | None = None
    creative_brief_summary: dict[str, Any] = Field(default_factory=dict)
    final_turkish_texts: dict[str, str] = Field(default_factory=dict)
    claim_guard: dict[str, Any] = Field(default_factory=dict)
    project_asset_lock: dict[str, Any] = Field(default_factory=dict)
    provider_call_count: int = 0
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    gpt_image: dict[str, Any] = Field(default_factory=dict)
