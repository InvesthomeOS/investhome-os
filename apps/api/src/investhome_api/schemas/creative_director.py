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
    """AI revision of an existing finished-ad (no new campaign)."""

    instruction: str = Field(..., min_length=1, max_length=8000)
    current_final_asset_id: UUID | None = Field(
        default=None,
        description=(
            "Current tip finished-ad for cursor/history. Generation source is always "
            "immutable master_asset_id (not this raster)."
        ),
    )
    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: Literal["1:1", "4:5", "16:9", "9:16"] | None = "4:5"
    format_preset: str | None = Field(default="portrait", max_length=32)


RevisionAction = Literal[
    "replace_text",
    "scale",
    "remove",
    "tone_adjust",
    "preserve",
    "minimum_change",
]
RevisionTarget = Literal[
    "headline",
    "cta",
    "badge",
    "logo",
    "support_message",
    "price",
    "background",
    "layout",
    "style",
    "overall",
]
RevisionConfidence = Literal["high", "medium", "low"]


class RevisionOperation(BaseModel):
    """One structured surgical change — never a verbatim NL dump to the provider."""

    target: RevisionTarget
    action: RevisionAction
    from_value: str | None = Field(default=None, alias="from")
    to_value: str | None = Field(default=None, alias="to")
    scale_factor: float | None = None
    confidence: RevisionConfidence = "medium"
    mode: Literal["exact", "subjective", "ambiguous"] = "exact"
    note: str | None = None

    model_config = {"populate_by_name": True}


class RevisionDiff(BaseModel):
    """Structured Revision Diff produced before any provider call."""

    operations: list[RevisionOperation] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    command_mode: Literal["exact", "subjective", "mixed", "ambiguous"] = "exact"
    max_subjective_ops: int = 3
    quality_lock: dict[str, Any] = Field(default_factory=dict)


class CreativeDirectorCampaignResponse(BaseModel):
    campaign_id: UUID
    project_id: UUID
    brief: dict[str, Any] = Field(default_factory=dict)
    campaign_context: dict[str, Any] = Field(default_factory=dict)


CreativeDirectorProductionMode = Literal["finished_ad", "os_compose"]


class CreativeDirectorGenerateAdRequest(BaseModel):
    """Optional overrides for MASTER ad generation from Campaign Context."""

    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: Literal["1:1", "4:5", "16:9", "9:16"] | None = "4:5"
    format_preset: str | None = Field(default="portrait", max_length=32)
    production_mode: CreativeDirectorProductionMode = "finished_ad"
    skip_gpt_image: bool = False
    background_asset_id: UUID | None = None


class CreativeDirectorRecomposeAdRequest(BaseModel):
    """Regenerate OS layers from an existing GPT Image background — zero provider calls."""

    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: Literal["1:1", "4:5", "16:9", "9:16"] | None = "4:5"
    format_preset: str | None = Field(default="portrait", max_length=32)
    background_asset_id: UUID = Field(..., description="Existing clean GPT Image background asset")


class CreativeDirectorGenerateAdResponse(BaseModel):
    campaign_id: UUID
    project_id: UUID
    language: str
    aspect_ratio: str
    format_preset: str
    production_mode: CreativeDirectorProductionMode = "finished_ad"
    production_brief: dict[str, Any] = Field(default_factory=dict)
    provider_route: dict[str, Any] = Field(default_factory=dict)
    interior_asset_id: UUID
    logo_asset_id: UUID
    final_asset_id: UUID
    final_asset_url: str
    composition_base_asset_id: UUID | None = None
    creative_brief_summary: dict[str, Any] = Field(default_factory=dict)
    final_turkish_texts: dict[str, str] = Field(default_factory=dict)
    claim_guard: dict[str, Any] = Field(default_factory=dict)
    project_asset_lock: dict[str, Any] = Field(default_factory=dict)
    duplication_guard: dict[str, Any] = Field(default_factory=dict)
    provider_call_count: int = 0
    gpt_image_call_count: int = 0
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    gpt_image: dict[str, Any] = Field(default_factory=dict)


class CreativeDirectorReviseAdResponse(CreativeDirectorGenerateAdResponse):
    """Revision response — finished-ad edit with history."""

    revision_brief: dict[str, Any] = Field(default_factory=dict)
    revision_intents: list[str] = Field(default_factory=list)
    revision_diff: dict[str, Any] = Field(default_factory=dict)
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    revision_index: int = 0
    revision_operations: list[dict[str, Any]] = Field(default_factory=list)
    master_asset_id: UUID | None = None
    revision_source_asset_id: UUID | None = None
    quality_guard: dict[str, Any] = Field(default_factory=dict)
    previous_asset_id: UUID | None = None
    campaign_context: dict[str, Any] = Field(default_factory=dict)
