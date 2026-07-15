"""Visual Design Studio API schemas — Sprint 2 extensions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.design_studio import DesignStatus, DesignType, FurnitureType


class DesignParameters(BaseModel):
    mode: str = Field(description="basic_overlay or room_regions")
    palette: str = "default"
    regions: list[dict[str, Any]] = Field(default_factory=list)
    backgroundColor: str | None = None
    selected_style_preset_id: UUID | None = None
    selected_material_package_id: UUID | None = None
    color_overlays: list[dict[str, Any]] = Field(default_factory=list)
    furniture_items: list[str] = Field(default_factory=list)
    furniture_placements: list[dict[str, Any]] = Field(default_factory=list)
    furniture_positions: dict[str, dict[str, float]] = Field(default_factory=dict)
    furniture_rotations: dict[str, float] = Field(default_factory=dict)
    furniture_dimensions: dict[str, dict[str, float]] = Field(default_factory=dict)
    editor_metadata: dict[str, Any] = Field(default_factory=dict)


class DesignVersionCreate(BaseModel):
    design_parameters: DesignParameters
    source_geometry_version: str | None = None


class DesignVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_project_id: UUID
    version_number: int
    source_geometry_version: str | None
    design_parameters: dict[str, Any] | None
    output_location: str | None
    thumbnail_location: str | None
    created_by_user_id: UUID | None
    created_by_name: str | None = None
    created_at: datetime


class DesignProjectCreate(BaseModel):
    project_id: UUID
    document_id: UUID
    document_version_id: UUID | None = None
    drawing_analysis_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    design_type: DesignType = DesignType.COLORED_FLOOR_PLAN


class DesignProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    design_type: DesignType | None = None
    status: DesignStatus | None = None


class DesignProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    document_id: UUID
    document_version_id: UUID
    drawing_analysis_id: UUID | None
    title: str
    description: str | None
    design_type: DesignType
    status: DesignStatus
    source_geometry_version: str | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    review_comment: str | None = None
    review_submitted_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    project_name: str | None = None
    document_title: str | None = None
    created_by_name: str | None = None
    reviewed_by_name: str | None = None
    current_version_number: int | None = None
    version_count: int = 0


class DesignProjectListResponse(BaseModel):
    items: list[DesignProjectResponse]
    total: int


class DesignVersionListResponse(BaseModel):
    items: list[DesignVersionResponse]
    total: int


class DesignSourceRegion(BaseModel):
    id: str
    label: str | None
    element_type: str
    has_geometry: bool


class DesignSourceRegionsResponse(BaseModel):
    mode: str
    regions: list[DesignSourceRegion]


class DesignStatusAction(BaseModel):
    comment: str | None = None


class CompatibleSourceDocument(BaseModel):
    id: UUID
    title: str
    document_type: str
    document_version_id: UUID
    drawing_analysis_id: UUID | None
    preview_status: str | None
    has_room_regions: bool


class CompatibleSourceDocumentsResponse(BaseModel):
    items: list[CompatibleSourceDocument]
    total: int


# --- Style Presets ---


class StylePresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=60)
    description: str | None = None
    color_palette: dict[str, Any] | None = None
    material_preferences: dict[str, Any] | None = None
    furniture_preferences: dict[str, Any] | None = None


class StylePresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    color_palette: dict[str, Any] | None = None
    material_preferences: dict[str, Any] | None = None
    furniture_preferences: dict[str, Any] | None = None


class StylePresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    color_palette: dict[str, Any] | None
    material_preferences: dict[str, Any] | None
    furniture_preferences: dict[str, Any] | None
    is_system_preset: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class StylePresetListResponse(BaseModel):
    items: list[StylePresetResponse]
    total: int


# --- Material Packages ---


class MaterialPackageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    flooring: str | None = None
    wall_finish: str | None = None
    ceiling_finish: str | None = None
    cabinetry: str | None = None
    countertop: str | None = None
    backsplash: str | None = None
    bathroom_finish: str | None = None
    metal_finish: str | None = None
    door_finish: str | None = None
    color_palette: dict[str, Any] | None = None
    reference_document_ids: list[str] | None = None


class MaterialPackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    flooring: str | None = None
    wall_finish: str | None = None
    ceiling_finish: str | None = None
    cabinetry: str | None = None
    countertop: str | None = None
    backsplash: str | None = None
    bathroom_finish: str | None = None
    metal_finish: str | None = None
    door_finish: str | None = None
    color_palette: dict[str, Any] | None = None
    reference_document_ids: list[str] | None = None


class MaterialPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    flooring: str | None
    wall_finish: str | None
    ceiling_finish: str | None
    cabinetry: str | None
    countertop: str | None
    backsplash: str | None
    bathroom_finish: str | None
    metal_finish: str | None
    door_finish: str | None
    color_palette: dict[str, Any] | None
    reference_document_ids: list | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class MaterialPackageListResponse(BaseModel):
    items: list[MaterialPackageResponse]
    total: int


class ApplyMaterialPackageRequest(BaseModel):
    material_package_id: UUID
    design_parameters: DesignParameters | None = None


# --- Furniture Catalog ---


class FurnitureItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=60)
    room_type: str | None = None
    furniture_type: FurnitureType
    width: float | None = None
    depth: float | None = None
    height: float | None = None
    measurement_unit: str = "cm"
    default_rotation: float = 0.0
    icon_or_preview: str | None = None
    metadata: dict[str, Any] | None = None


class FurnitureItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    room_type: str | None = None
    furniture_type: FurnitureType | None = None
    width: float | None = None
    depth: float | None = None
    height: float | None = None
    measurement_unit: str | None = None
    default_rotation: float | None = None
    icon_or_preview: str | None = None
    metadata: dict[str, Any] | None = None


class FurnitureItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    code: str
    room_type: str | None
    furniture_type: FurnitureType
    width: float | None
    depth: float | None
    height: float | None
    measurement_unit: str
    default_rotation: float
    icon_or_preview: str | None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")
    is_system_item: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class FurnitureItemListResponse(BaseModel):
    items: list[FurnitureItemResponse]
    total: int


# --- Version Comparison ---


class VersionCompareRequest(BaseModel):
    version_a_id: UUID
    version_b_id: UUID


class VersionCompareDiff(BaseModel):
    style_preset_changed: bool
    style_preset_a: str | None = None
    style_preset_b: str | None = None
    material_package_changed: bool
    material_package_a: str | None = None
    material_package_b: str | None = None
    furniture_count_a: int = 0
    furniture_count_b: int = 0
    furniture_added: list[str] = Field(default_factory=list)
    furniture_removed: list[str] = Field(default_factory=list)
    furniture_moved: list[str] = Field(default_factory=list)
    colors_changed: bool = False
    color_diff_summary: str | None = None


class VersionCompareResponse(BaseModel):
    version_a: DesignVersionResponse
    version_b: DesignVersionResponse
    design_status: DesignStatus
    diff: VersionCompareDiff
    comparison_note: str = "Metadata comparison only — not pixel-perfect visual diff."
