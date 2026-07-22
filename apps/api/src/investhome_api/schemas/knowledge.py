"""Knowledge Hub Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProviderCapabilityStatus(BaseModel):
    """Honest status for optional providers (OCR / vector / malware)."""

    provider: str
    available: bool
    reason: str | None = None
    required_env: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)


class KnowledgeMetricValue(BaseModel):
    value: int | float | None = None
    available: bool = True
    reason: str | None = None
    drilldown: str | None = None


class KnowledgeOverviewResponse(BaseModel):
    total_documents: KnowledgeMetricValue
    recent_uploads: KnowledgeMetricValue
    awaiting_review: KnowledgeMetricValue
    expiring_soon: KnowledgeMetricValue
    failed_jobs: KnowledgeMetricValue
    unlinked: KnowledgeMetricValue
    duplicate_candidates: KnowledgeMetricValue
    storage_used_bytes: KnowledgeMetricValue
    collections: KnowledgeMetricValue
    indexing_status: ProviderCapabilityStatus
    ocr_status: ProviderCapabilityStatus
    ai_status: ProviderCapabilityStatus
    malware_scan_status: ProviderCapabilityStatus
    vector_search_status: ProviderCapabilityStatus


class KnowledgeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name_en: str
    name_tr: str
    description: str | None
    sort_order: int
    is_active: bool
    is_system: bool


class KnowledgeCategoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name_en: str = Field(min_length=1, max_length=200)
    name_tr: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sort_order: int = 0


class KnowledgeCategoryUpdate(BaseModel):
    name_en: str | None = Field(default=None, max_length=200)
    name_tr: str | None = Field(default=None, max_length=200)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class KnowledgeCollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    collection_type: str
    smart_rules_json: str | None
    owner_user_id: UUID | None
    is_shared: bool
    document_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeCollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    collection_type: str = "manual"
    smart_rules: dict[str, Any] | None = None
    is_shared: bool = True


class KnowledgeCollectionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    smart_rules: dict[str, Any] | None = None
    is_shared: bool | None = None


class KnowledgeCollectionItemCreate(BaseModel):
    document_id: UUID


class KnowledgeReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_title: str | None = None
    reason: str
    status: str
    priority: str
    details: str | None
    confidence_score: str | None
    assigned_to_user_id: UUID | None
    resolved_by_user_id: UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeReviewResolveRequest(BaseModel):
    status: str = Field(description="resolved | dismissed")
    resolution_notes: str | None = None


class KnowledgeRetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    category_code: str | None
    retention_days: int | None
    action_on_expiry: str
    is_active: bool
    legal_hold_capable: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeRetentionPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_code: str | None = None
    retention_days: int | None = Field(default=None, ge=1)
    action_on_expiry: str = "notify"
    legal_hold_capable: bool = False


class KnowledgeAiSearchHit(BaseModel):
    document_id: UUID
    title: str
    snippet: str
    citation: str | None = None
    page: int | None = None
    score: float | None = None
    source: str = "keyword"
    ai_summary: str | None = None


class KnowledgeAiSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeAiSearchHit]
    provider: ProviderCapabilityStatus
    note: str | None = None


class KnowledgeAiSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)


class KnowledgeSettingsResponse(BaseModel):
    auto_enqueue_review_on_low_confidence: bool = True
    expiration_alert_days: int = 30
    enable_duplicate_detection: bool = True
    vector_indexing_enabled: bool = False
    malware_scanning_enabled: bool = False
    providers: dict[str, ProviderCapabilityStatus] = Field(default_factory=dict)
    placeholders: dict[str, str] = Field(default_factory=dict)


class KnowledgeSettingsUpdate(BaseModel):
    auto_enqueue_review_on_low_confidence: bool | None = None
    expiration_alert_days: int | None = Field(default=None, ge=1, le=365)
    enable_duplicate_detection: bool | None = None


class KnowledgePipelineStage(BaseModel):
    stage: str
    label: str
    count: int
    status: str  # healthy | attention | unavailable


class KnowledgePipelineStatusResponse(BaseModel):
    stages: list[KnowledgePipelineStage]
    automation_hook: str = "/automation"
    note: str | None = None


class KnowledgeFoundationPlaceholder(BaseModel):
    feature: str
    status: str
    description: str
    required_env: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)
