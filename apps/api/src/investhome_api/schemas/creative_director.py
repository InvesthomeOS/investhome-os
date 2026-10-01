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
    selected_element_id: str | None = Field(
        default=None,
        max_length=128,
        description="SMB selected layer id — strongest target for vague commands.",
    )


RevisionAction = Literal[
    "replace_text",
    "scale",
    "resize",
    "remove",
    "delete",
    "tone_adjust",
    "preserve",
    "minimum_change",
    "translate",
    "set_position",
    "align",
    "set_font_size",
    "set_color",
    "hide",
    "set_geometry",
    "improve_readability",
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
    "subheadline",
    "eyebrow",
    "top_small_description",
    "primary_headline",
    "left_feature_texts",
    "feature_text",
]
RevisionConfidence = Literal["high", "medium", "low"]
RevisionPriority = Literal[
    "exact_numeric",
    "relational_geometric",
    "percentage",
    "relative_nl",
    "subjective",
    "ambiguous",
]


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
    priority: RevisionPriority | None = "exact_numeric"
    dx: float | None = None
    dy: float | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    font_size: float | None = None
    color: str | None = None
    align_edge: str | None = None
    reference_element: str | None = None
    element_id: str | None = None
    element_ids: list[str] | None = None
    value: float | None = None
    semantic_target: str | None = None

    model_config = {"populate_by_name": True}


class RevisionDiff(BaseModel):
    """Structured Revision Diff produced before any provider call."""

    operations: list[RevisionOperation] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    command_mode: Literal["exact", "subjective", "mixed", "ambiguous"] = "exact"
    max_subjective_ops: int = 3
    quality_lock: dict[str, Any] = Field(default_factory=dict)
    strict_preserve: bool = False
    selected_element_id: str | None = None
    geometry_operations: list[dict[str, Any]] = Field(default_factory=list)
    requested_changes: list[dict[str, Any]] = Field(default_factory=list)


class CreativeDirectorCampaignResponse(BaseModel):
    campaign_id: UUID
    project_id: UUID
    brief: dict[str, Any] = Field(default_factory=dict)
    campaign_context: dict[str, Any] = Field(default_factory=dict)


CreativeDirectorProductionMode = Literal[
    "finished_ad",
    "os_compose",
    "editable_finished_ad",
    "golden_native_v1",
]
RevisionRoute = Literal[
    "LAYER_ONLY",
    "MICRO_EDIT",
    "CREATIVE_RECOMPOSE",
    "IMAGE_REQUIRED",
    "VISUAL_REPLACE_ONLY",
    "PRICE_EDIT_ONLY",
    "BOUNDED_LOCAL_RECOMPOSITION",
]


class DesignSpecElement(BaseModel):
    """One editable overlay (or locked background) in a Design Spec."""

    id: str
    type: Literal[
        "image",
        "logo",
        "text",
        "badge",
        "cta",
        "shape",
        "rectangle",
        "line",
        "divider",
        "gradient",
        "overlay",
        "icon",
    ]
    role: str | None = None
    content: str | None = None
    asset_id: str | None = None
    locked: bool = False
    editable: bool = True
    lock_aspect_ratio: bool | None = None
    claim_sensitive: bool | None = None
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    z_index: int = 0
    opacity: float | None = 1.0
    typography: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    treatment: dict[str, Any] | None = None


class DesignSpec(BaseModel):
    """Structured editable finished-ad layout — OS renders; does not invent creative."""

    version: int = 2
    mode: Literal["editable_finished_ad"] = "editable_finished_ad"
    canvas: dict[str, Any] = Field(default_factory=dict)
    language: str = "tr"
    campaign_intent: str | None = None
    composition_plan: dict[str, Any] | None = None
    composition: dict[str, Any] | None = None
    background: dict[str, Any] | None = None
    master_background_asset_id: str
    logo_asset_id: str
    finished_ad_raster_asset_id: str | None = None
    locked_background: bool = True
    elements: list[dict[str, Any]] = Field(default_factory=list)


class CreativeDirectorGenerateAdRequest(BaseModel):
    """Optional overrides for MASTER ad generation from Campaign Context."""

    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: Literal["1:1", "4:5", "16:9", "9:16"] | None = "4:5"
    format_preset: str | None = Field(default="portrait", max_length=32)
    production_mode: CreativeDirectorProductionMode = "finished_ad"
    skip_gpt_image: bool = False
    background_asset_id: UUID | None = None
    workflow: Literal["phase5"] | None = None
    user_request: str | None = Field(default=None, max_length=12000)


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
    architecture_truth_guard: dict[str, Any] = Field(default_factory=dict)
    duplication_guard: dict[str, Any] = Field(default_factory=dict)
    provider_call_count: int = 0
    gpt_image_call_count: int = 0
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    gpt_image: dict[str, Any] = Field(default_factory=dict)
    # Optional/legacy editable finished-ad layered design (NOT production default)
    design_spec: dict[str, Any] | None = None
    master_background_asset_id: UUID | None = None
    finished_ad_raster_asset_id: UUID | None = None
    editable_layers: list[dict[str, Any]] = Field(default_factory=list)
    # Immutable golden master (alias of master_asset_id)
    master_asset_id: UUID | None = None
    master_finished_ad_asset_id: UUID | None = None
    quality_guard: dict[str, Any] = Field(default_factory=dict)
    structured_design_data: dict[str, Any] | None = None
    master_creative: dict[str, Any] | None = None


class CreativeDirectorReviseAdResponse(CreativeDirectorGenerateAdResponse):
    """Revision response — finished-ad edit with history."""

    revision_brief: dict[str, Any] = Field(default_factory=dict)
    revision_intents: list[str] = Field(default_factory=list)
    revision_diff: dict[str, Any] = Field(default_factory=dict)
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    revision_index: int = 0
    revision_operations: list[dict[str, Any]] = Field(default_factory=list)
    revision_source_asset_id: UUID | None = None
    previous_asset_id: UUID | None = None
    campaign_context: dict[str, Any] = Field(default_factory=dict)
    revision_route: RevisionRoute | None = None
    user_feedback: str | None = None
    change_diff_validation: dict[str, Any] = Field(default_factory=dict)
    interpreted_plan: dict[str, Any] = Field(default_factory=dict)
    execution_validation: dict[str, Any] = Field(default_factory=dict)
