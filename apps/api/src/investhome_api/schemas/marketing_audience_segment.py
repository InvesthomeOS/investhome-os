"""Pydantic schemas for marketing audiences, segments, leads, and sources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SegmentRuleSchema(BaseModel):
    field_key: str = Field(min_length=1, max_length=80)
    operator: str = Field(min_length=1, max_length=40)
    value: dict | str | int | float | bool | list | None = None
    negate: bool = False


class SegmentRuleGroupSchema(BaseModel):
    operator: str = Field(default="and", pattern="^(and|or|not)$")
    sort_order: int = 0
    rules: list[SegmentRuleSchema | dict] = Field(default_factory=list)
    groups: list["SegmentRuleGroupSchema"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_depth(self) -> SegmentRuleGroupSchema:
        def _depth(g: SegmentRuleGroupSchema, level: int) -> int:
            if level > 5:
                raise ValueError("Rule group depth exceeds maximum of 5")
            max_d = level
            for nested in g.groups:
                max_d = max(max_d, _depth(nested, level + 1))
            return max_d

        _depth(self, 1)
        if len(self.rules) > 20:
            raise ValueError("Rules per group exceeds maximum of 20")
        return self


SegmentRuleGroupSchema.model_rebuild()


class AudienceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    audience_type: str
    mode: str = "static"
    source: str | None = None
    contact_ids: list[str] | None = None
    company_ids: list[str] | None = None
    segment_ids: list[str] | None = None
    inclusion_refs_json: dict | None = None
    exclusion_refs_json: dict | None = None
    consent_json: dict | None = None
    consent_requirements_json: dict | None = None
    channel_eligibility_json: dict | None = None
    geo_json: dict | None = None
    refresh_policy_json: dict | None = None
    channel_ids: list[str] | None = None
    language: str | None = None


class AudienceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    audience_type: str | None = None
    mode: str | None = None
    source: str | None = None
    contact_ids: list[str] | None = None
    company_ids: list[str] | None = None
    segment_ids: list[str] | None = None
    inclusion_refs_json: dict | None = None
    exclusion_refs_json: dict | None = None
    consent_json: dict | None = None
    consent_requirements_json: dict | None = None
    channel_eligibility_json: dict | None = None
    geo_json: dict | None = None
    refresh_policy_json: dict | None = None
    channel_ids: list[str] | None = None
    language: str | None = None


class AudienceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    audience_type: str
    mode: str
    status: str
    source: str | None
    estimated_size: int | None
    calculated_size: int | None
    language: str | None
    last_refreshed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AudienceDetail(AudienceSummary):
    description: str | None
    contact_ids: list | None
    company_ids: list | None
    segment_ids: list | None
    consent_requirements_json: dict | None
    channel_eligibility_json: dict | None
    geo_json: dict | None
    refresh_policy_json: dict | None
    version: int


class AudienceMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audience_id: UUID
    contact_id: UUID | None
    company_id: UUID | None
    is_included: bool
    inclusion_source: str | None
    exclusion_reason: str | None
    eligibility_json: dict | None
    explainability_json: dict | None


class AudienceMemberAdd(BaseModel):
    contact_id: UUID | None = None
    company_id: UUID | None = None

    @model_validator(mode="after")
    def require_entity(self) -> AudienceMemberAdd:
        if not self.contact_id and not self.company_id:
            raise ValueError("contact_id or company_id required")
        return self


class AudienceSummaryStats(BaseModel):
    active: int
    draft: int
    total: int


class AudienceReadinessResponse(BaseModel):
    audience_id: str
    state: str
    blockers: list[str]
    member_count: int | None
    consent_check: dict


class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    segment_type: str
    rules_json: dict | None = None
    rule_groups: list[SegmentRuleGroupSchema] | None = None
    refresh_frequency: str | None = None
    visibility: str = "team"
    depends_on_segment_ids: list[str] | None = None


class SegmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    segment_type: str | None = None
    rules_json: dict | None = None
    rule_groups: list[SegmentRuleGroupSchema] | None = None
    refresh_frequency: str | None = None
    visibility: str | None = None
    depends_on_segment_ids: list[str] | None = None


class SegmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    segment_type: str
    visibility: str
    estimated_size: int | None
    calculated_size: int | None
    calculation_status: str
    current_version: int
    last_refreshed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SegmentDetail(SegmentSummary):
    description: str | None
    rules_json: dict | None
    depends_on_segment_ids: list | None
    refresh_frequency: str | None


class SegmentPreviewResponse(BaseModel):
    segment_id: str
    state: str
    estimated_count: int | None
    sample_members: list
    rule_explanation: str
    warnings: list[str]


class SegmentSummaryStats(BaseModel):
    total: int
    calculated: int
    not_calculated: int


class SegmentFieldRegistryResponse(BaseModel):
    fields: list[dict]


class MarketingLeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    contact_id: UUID | None
    company_id: UUID | None
    campaign_id: UUID | None
    source_id: UUID | None
    channel_id: UUID | None
    utm_data_json: dict | None
    marketing_status: str | None
    verification_status: str | None
    handoff_status: str
    created_at: datetime


class MarketingLeadDetailResponse(BaseModel):
    id: UUID
    lead_id: UUID | None
    contact_id: UUID | None
    company_id: UUID | None
    campaign_id: UUID | None
    source_id: UUID | None
    attribution_json: dict | None
    utm_data_json: dict | None
    scores_json: dict | None
    consent_status: dict[str, str | None]
    marketing_status: str | None
    verification_status: str | None
    handoff_status: str


class HandoffReadinessResponse(BaseModel):
    context_id: str
    ready: bool
    blockers: list[str]
    consent_status: dict[str, str | None]


class HandoffResponse(BaseModel):
    context_id: str
    lead_id: str
    linked_existing: bool


class MarketingLeadSummaryStats(BaseModel):
    total: int
    ready_for_handoff: int
    blocked: int


class LeadSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str
    parent_id: UUID | None = None
    channel_id: UUID | None = None
    utm_defaults_json: dict | None = None
    tracking_code: str | None = None
    description: str | None = None


class LeadSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    parent_id: UUID | None = None
    channel_id: UUID | None = None
    utm_defaults_json: dict | None = None
    tracking_code: str | None = None
    description: str | None = None
    is_active: bool | None = None


class LeadSourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    normalized_name: str | None
    parent_id: UUID | None
    source_type: str
    channel_id: UUID | None
    tracking_code: str | None
    tracking_readiness: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LeadSourceDetail(LeadSourceSummary):
    description: str | None
    utm_defaults_json: dict | None


class LeadSourceMappingCreate(BaseModel):
    provider: str | None = None
    external_key: str = Field(min_length=1, max_length=255)
    mapping_json: dict | None = None


class LeadSourceMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    provider: str | None
    external_key: str
    mapping_json: dict | None
    is_active: bool


class NormalizationRequest(BaseModel):
    raw_value: str = Field(min_length=1, max_length=512)


class NormalizationResponse(BaseModel):
    raw_value: str
    normalized_value: str
    from_cache: bool


class SavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filters_json: dict | None = None
    is_default: bool = False
    is_shared: bool = False


class PaginatedResponse(BaseModel):
    items: list
    page: int
    page_size: int
    total: int
    pages: int
