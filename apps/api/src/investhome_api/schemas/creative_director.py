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
