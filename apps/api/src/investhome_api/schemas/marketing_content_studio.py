"""Pydantic schemas for marketing content studio."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    code: str | None = None
    description: str | None = None
    content_type: str = "other"
    format: str | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    primary_language: str = "en"
    project_ids: list[str] | None = None
    property_ids: list[str] | None = None
    audience_ids: list[str] | None = None
    campaign_ids: list[str] | None = None
    channel_ids: list[str] | None = None
    tags: list[str] | None = None
    body_json: dict | None = None


class ContentUpdate(BaseModel):
    title: str | None = None
    code: str | None = None
    description: str | None = None
    content_type: str | None = None
    format: str | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    primary_language: str | None = None
    project_ids: list[str] | None = None
    property_ids: list[str] | None = None
    audience_ids: list[str] | None = None
    campaign_ids: list[str] | None = None
    asset_ids: list[str] | None = None
    channel_ids: list[str] | None = None
    scheduled_at: datetime | None = None
    expires_at: datetime | None = None
    tags: list[str] | None = None


class ContentStatusTransition(BaseModel):
    target_status: str


class ContentBriefUpdate(BaseModel):
    objective: str | None = None
    target_audience: str | None = None
    key_messages: str | None = None
    tone_and_voice: str | None = None
    deliverables: str | None = None
    constraints: str | None = None
    success_criteria: str | None = None


class ContentVersionCreate(BaseModel):
    label: str | None = None
    body_json: dict | None = None
    document_id: UUID | None = None
    change_summary: str | None = None


class ContentVariantCreate(BaseModel):
    variant_key: str
    channel_id: UUID | None = None
    channel_category: str | None = None
    title: str | None = None
    body_json: dict | None = None


class ContentTranslationCreate(BaseModel):
    locale: str
    title: str | None = None
    body_json: dict | None = None
    version_id: UUID | None = None


class ContentEntityLink(BaseModel):
    entity_type: str
    entity_id: UUID


class ContentApprovalAction(BaseModel):
    notes: str | None = None
    version_id: UUID | None = None


class PublishingReadinessResponse(BaseModel):
    state: str
    remediation: list[str]
    content_id: str
    status: str


class AssetAiPrepMetadata(BaseModel):
    language: str | None = None
    audience: str | None = None
    market: str | None = None
    property_type: str | None = None
    country: str | None = None
    city: str | None = None
    keywords: list[str] | None = None


class AssetCreateFromDocument(BaseModel):
    document_id: UUID
    name: str | None = None
    title: str | None = None  # alias for name
    asset_type: str = "other"
    description: str | None = None
    tags: list[str] | None = None
    folder: str | None = None
    project_id: UUID | None = None
    campaign_id: UUID | None = None
    notes: str | None = None
    thumbnail_document_id: UUID | None = None
    ai_prep: AssetAiPrepMetadata | None = None
    status: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    title: str | None = None  # alias for name
    description: str | None = None
    asset_type: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    folder: str | None = None
    project_id: UUID | None = None
    campaign_id: UUID | None = None
    notes: str | None = None
    thumbnail_document_id: UUID | None = None
    ai_prep: AssetAiPrepMetadata | None = None


class AssetCampaignLink(BaseModel):
    campaign_id: UUID | None = None


class AssetProjectLink(BaseModel):
    project_id: UUID | None = None


class AssetRightsUpdate(BaseModel):
    license_type: str | None = None
    holder: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    territory: str | None = None
    usage_restrictions: str | None = None
    attribution_required: bool | None = None
    status: str | None = None


class AssetUsageCreate(BaseModel):
    entity_type: str
    entity_id: UUID
    usage_context: str | None = None
    channel_id: UUID | None = None


class BrandProfileCreate(BaseModel):
    name: str
    description: str | None = None
    company_brand_id: UUID | None = None
    colors_json: dict | None = None
    typography_json: dict | None = None
    voice_json: dict | None = None
    guidelines_json: dict | None = None
    logo_asset_ids: list[str] | None = None
    is_default: bool = False


class BrandProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    colors_json: dict | None = None
    typography_json: dict | None = None
    voice_json: dict | None = None
    guidelines_json: dict | None = None
    logo_asset_ids: list[str] | None = None
    status: str | None = None
    is_default: bool | None = None


class TerminologyCreate(BaseModel):
    term: str
    preferred_usage: str | None = None
    avoid_usage: str | None = None
    definition: str | None = None
    category: str | None = None


class ClaimCreate(BaseModel):
    claim_text: str
    category: str | None = None
    evidence_ref: str | None = None
    valid_until: datetime | None = None
    reason: str | None = None
    severity: str = "warning"


class ComplianceCheckRequest(BaseModel):
    content_id: UUID | None = None
    version_id: UUID | None = None
    brand_profile_id: UUID | None = None
    body_text: str = ""


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    template_type: str = "other"
    content_type: str | None = None
    channel_category: str | None = None
    body_template: str | None = None
    body_json: dict | None = None
    document_id: UUID | None = None
    placeholders: list[dict] | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content_type: str | None = None
    channel_category: str | None = None
    status: str | None = None


class TemplatePreviewRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class AIGenerationRequest(BaseModel):
    content_id: UUID | None = None
    version_id: UUID | None = None
    prompt: str
    context_json: dict | None = None


class AIGenerationReview(BaseModel):
    approved: bool


class FieldRegistryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: str
    format: str | None
    channel_category: str | None
    field_key: str
    field_label: str
    field_type: str
    required: bool
    constraints_json: dict | None
    sort_order: int
