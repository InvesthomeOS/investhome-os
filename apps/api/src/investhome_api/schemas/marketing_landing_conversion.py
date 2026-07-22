"""Pydantic schemas for marketing landing pages, forms, and conversion."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Landing Pages ---


class LandingPageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    campaign_id: UUID | None = None
    form_id: UUID | None = None
    project_id: UUID | None = None
    property_id: UUID | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class LandingPageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    campaign_id: UUID | None = None
    form_id: UUID | None = None
    project_id: UUID | None = None
    property_id: UUID | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    tracking_config_json: dict | None = None
    consent_config_json: dict | None = None


class LandingPageSectionCreate(BaseModel):
    section_type: str
    sort_order: int = 0
    config_json: dict | None = None
    is_visible: bool = True

    @field_validator("section_type")
    @classmethod
    def validate_section_type(cls, v: str) -> str:
        allowed = {
            "hero", "lead_form", "project_summary", "property_summary",
            "features", "testimonials", "cta", "gallery", "video", "faq", "footer",
        }
        if v not in allowed:
            raise ValueError(f"Invalid section type: {v}")
        return v


class LandingPageSectionUpdate(BaseModel):
    sort_order: int | None = None
    config_json: dict | None = None
    is_visible: bool | None = None


class LandingPageSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    landing_page_id: UUID
    section_type: str
    sort_order: int
    config_json: dict | None
    is_visible: bool


class LandingPageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: str
    campaign_id: UUID | None
    form_id: UUID | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LandingPageDetail(LandingPageSummary):
    project_id: UUID | None
    property_id: UUID | None
    meta_title: str | None
    meta_description: str | None
    tracking_config_json: dict | None
    consent_config_json: dict | None
    approval_status: str | None
    published_version_id: UUID | None
    sections: list[LandingPageSectionResponse] = []


class LandingPageListResponse(BaseModel):
    items: list[LandingPageSummary]
    total: int
    page: int
    page_size: int
    pages: int


class LandingPageReadinessResponse(BaseModel):
    landing_page_id: UUID
    ready: bool
    blockers: list[str]
    warnings: list[str] = []


class LandingPageStatusTransition(BaseModel):
    target_status: str
    idempotency_key: str | None = None


class LandingPageDomainCreate(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    path_prefix: str | None = None
    is_primary: bool = False


class LandingPageDomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    landing_page_id: UUID
    domain: str
    path_prefix: str | None
    is_primary: bool
    verification_status: str


class LandingPageVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    landing_page_id: UUID
    version_number: int
    created_at: datetime


class SectionRegistryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_type: str
    label: str
    config_schema_json: dict | None
    allowed_public_fields_json: list | None


class PublicDataFieldItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    field_key: str
    label: str
    data_type: str


# --- Forms ---


class FormCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    campaign_id: UUID | None = None
    source_id: UUID | None = None


class FormUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    campaign_id: UUID | None = None
    source_id: UUID | None = None
    consent_config_json: dict | None = None
    routing_config_json: dict | None = None
    notification_config_json: dict | None = None
    spam_config_json: dict | None = None


class FormFieldCreate(BaseModel):
    field_key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    field_type: str
    label: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    required: bool = False
    config_json: dict | None = None
    validation_json: dict | None = None
    is_visible: bool = True


class FormFieldUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    required: bool | None = None
    config_json: dict | None = None
    validation_json: dict | None = None
    is_visible: bool | None = None


class FormFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    form_id: UUID
    field_key: str
    field_type: str
    label: str
    sort_order: int
    required: bool
    config_json: dict | None
    validation_json: dict | None
    is_visible: bool


class FormLogicGroupCreate(BaseModel):
    target_field_id: UUID
    operator: str = "and"
    action: str = "show"
    conditions_json: list[dict]
    sort_order: int = 0


class FormLogicGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    form_id: UUID
    target_field_id: UUID
    operator: str
    action: str
    conditions_json: list | None
    sort_order: int


class FormSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: str
    campaign_id: UUID | None
    source_id: UUID | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FormDetail(FormSummary):
    consent_config_json: dict | None
    routing_config_json: dict | None
    notification_config_json: dict | None
    spam_config_json: dict | None
    published_version_id: UUID | None
    fields: list[FormFieldResponse] = []
    logic_groups: list[FormLogicGroupResponse] = []


class FormListResponse(BaseModel):
    items: list[FormSummary]
    total: int
    page: int
    page_size: int
    pages: int


class FormFieldRegistryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_type: str
    label: str
    config_schema_json: dict | None
    validation_schema_json: dict | None


class FormReadinessResponse(BaseModel):
    form_id: UUID
    ready: bool
    blockers: list[str]


# --- Submissions ---


class TrackingPayload(BaseModel):
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    referrer: str | None = None
    landing_url: str | None = None
    session_id: str | None = None


class ConsentPayload(BaseModel):
    consent_email: bool | None = None
    consent_sms: bool | None = None
    consent_whatsapp: bool | None = None
    consent_phone: bool | None = None


class PublicFormSubmit(BaseModel):
    values: dict[str, str | bool | None]
    tracking: TrackingPayload | None = None
    consent: ConsentPayload | None = None
    landing_page_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=255)


class SubmissionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    form_id: UUID
    landing_page_id: UUID | None
    status: str
    contact_id: UUID | None
    lead_context_id: UUID | None
    created_at: datetime


class SubmissionDetail(SubmissionSummary):
    normalized_values_json: dict | None
    tracking_context_id: UUID | None
    consent_evidence_id: UUID | None
    duplicate_of_submission_id: UUID | None
    pipeline_errors_json: list | None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionSummary]
    total: int
    page: int
    page_size: int
    pages: int


class SubmissionReviewAction(BaseModel):
    action: str = Field(pattern=r"^(approve|reject)$")
    reason: str | None = None


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: UUID
    review_type: str
    status: str
    reason: str | None
    created_at: datetime


# --- Lead Capture ---


class LeadRoutingRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    priority: int = 0
    is_active: bool = True
    is_fallback: bool = False
    conditions_json: dict | None = None
    action_json: dict | None = None
    form_id: UUID | None = None
    source_id: UUID | None = None


class LeadRoutingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    priority: int
    is_active: bool
    is_fallback: bool
    conditions_json: dict | None
    action_json: dict | None
    form_id: UUID | None
    source_id: UUID | None


class HandoffSLAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    target_minutes: int
    is_default: bool
    is_active: bool


class SalesHandoffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_context_id: UUID
    submission_id: UUID | None
    sales_lead_id: UUID | None
    status: str
    due_at: datetime | None
    blockers_json: list | None


class LeadCaptureDashboard(BaseModel):
    pending_review: int
    pending_verification: int
    duplicates_detected: int
    ready_for_handoff: int
    provider_status: str = "not_connected"


# --- Conversions & Tracking ---


class ConversionEventCreate(BaseModel):
    event_type: str
    submission_id: UUID | None = None
    lead_context_id: UUID | None = None
    landing_page_id: UUID | None = None
    form_id: UUID | None = None
    value_json: dict | None = None


class ConversionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    submission_id: UUID | None
    lead_context_id: UUID | None
    created_at: datetime


class ConversionAnalyticsShell(BaseModel):
    connected: bool = False
    message: str = "Analytics provider not connected"
    metrics: dict | None = None


class AttributionShell(BaseModel):
    connected: bool = False
    message: str = "Attribution data not available"
    summary: dict | None = None


# --- Webhooks ---


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=500)
    event_types_json: list[str] | None = None
    form_id: UUID | None = None
    is_active: bool = True


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    event_types_json: list | None
    is_active: bool
    form_id: UUID | None


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    webhook_id: UUID
    event_type: str
    status: str
    response_code: int | None
    created_at: datetime


class ProviderStatusResponse(BaseModel):
    provider: str
    connected: bool
    status: str
    message: str | None = None
