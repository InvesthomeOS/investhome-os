"""Pydantic schemas for CRM communications."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.crm_communication import (
    CrmCommunicationChannel,
    CrmCommunicationDirection,
    CrmCommunicationEntityType,
    CrmCommunicationPriority,
    CrmCommunicationStatus,
    CrmCommunicationVisibility,
    CrmSequenceEnrollmentType,
    CrmSequenceStepType,
    CrmTemplateType,
    CrmThreadStatus,
)


class RecipientSchema(BaseModel):
    entity_type: CrmCommunicationEntityType | None = None
    entity_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    name: str | None = None


class RelatedEntitySchema(BaseModel):
    entity_type: CrmCommunicationEntityType
    entity_id: UUID
    label: str | None = None


class AttachmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    file_name: str
    file_size: int | None = None
    mime_type: str | None = None
    storage_key: str | None = None
    created_at: datetime


class CommunicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel: CrmCommunicationChannel
    direction: CrmCommunicationDirection
    status: CrmCommunicationStatus
    subject: str | None = None
    preview: str | None = None
    thread_id: UUID | None = None
    recipient_entity_type: CrmCommunicationEntityType | None = None
    recipient_entity_id: UUID | None = None
    priority: CrmCommunicationPriority
    visibility: CrmCommunicationVisibility
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    tags: list[str] | None = None
    has_attachments: bool = False
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class CommunicationDetail(CommunicationSummary):
    body: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    sender_entity_type: CrmCommunicationEntityType | None = None
    sender_entity_id: UUID | None = None
    recipients: list[dict[str, Any]] | None = None
    cc_recipients: list[dict[str, Any]] | None = None
    bcc_recipients: list[dict[str, Any]] | None = None
    participants: list[dict[str, Any]] | None = None
    related_entities: list[dict[str, Any]] | None = None
    parent_communication_id: UUID | None = None
    external_provider_id: str | None = None
    provider_thread_id: str | None = None
    delivered_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    replied_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    assigned_team_id: UUID | None = None
    metadata_json: dict[str, Any] | None = None
    call_duration_seconds: int | None = None
    call_outcome: str | None = None
    call_direction: str | None = None
    meeting_url: str | None = None
    meeting_start_at: datetime | None = None
    meeting_end_at: datetime | None = None
    activity_id: UUID | None = None
    attachments: list[AttachmentSchema] = Field(default_factory=list)
    created_by: UUID | None = None
    updated_by: UUID | None = None


class ThreadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    subject: str
    channel: CrmCommunicationChannel
    channels: list[str] | None = None
    unread_count: int
    message_count: int
    priority: CrmCommunicationPriority
    status: CrmThreadStatus
    tags: list[str] | None = None
    follow_up_date: datetime | None = None
    last_communication_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    is_pinned: bool = False
    snoozed_until: datetime | None = None
    preview: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ThreadDetail(ThreadSummary):
    participant_ids: list[str] | None = None
    related_entity_ids: list[dict[str, Any]] | None = None
    response_time_seconds: int | None = None
    sentiment: str | None = None
    communications: list[CommunicationSummary] = Field(default_factory=list)


class CommunicationCreate(BaseModel):
    channel: CrmCommunicationChannel
    direction: CrmCommunicationDirection = CrmCommunicationDirection.OUTBOUND
    status: CrmCommunicationStatus = CrmCommunicationStatus.DRAFT
    subject: str | None = Field(default=None, max_length=500)
    body: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    sender_entity_type: CrmCommunicationEntityType | None = None
    sender_entity_id: UUID | None = None
    recipient_entity_type: CrmCommunicationEntityType | None = None
    recipient_entity_id: UUID | None = None
    recipients: list[RecipientSchema] | None = None
    cc_recipients: list[RecipientSchema] | None = None
    bcc_recipients: list[RecipientSchema] | None = None
    participants: list[dict[str, Any]] | None = None
    related_entities: list[RelatedEntitySchema] | None = None
    thread_id: UUID | None = None
    parent_communication_id: UUID | None = None
    scheduled_at: datetime | None = None
    priority: CrmCommunicationPriority = CrmCommunicationPriority.MEDIUM
    visibility: CrmCommunicationVisibility = CrmCommunicationVisibility.ORGANIZATION
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    tags: list[str] | None = None
    metadata_json: dict[str, Any] | None = None
    call_duration_seconds: int | None = None
    call_outcome: str | None = None
    call_direction: str | None = None
    meeting_url: str | None = Field(default=None, max_length=1000)
    meeting_start_at: datetime | None = None
    meeting_end_at: datetime | None = None


class CommunicationUpdate(BaseModel):
    subject: str | None = Field(default=None, max_length=500)
    body: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    status: CrmCommunicationStatus | None = None
    recipients: list[RecipientSchema] | None = None
    cc_recipients: list[RecipientSchema] | None = None
    bcc_recipients: list[RecipientSchema] | None = None
    scheduled_at: datetime | None = None
    priority: CrmCommunicationPriority | None = None
    visibility: CrmCommunicationVisibility | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    tags: list[str] | None = None
    metadata_json: dict[str, Any] | None = None
    call_duration_seconds: int | None = None
    call_outcome: str | None = None
    meeting_url: str | None = None
    meeting_start_at: datetime | None = None
    meeting_end_at: datetime | None = None


class ThreadAssignRequest(BaseModel):
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None


class ThreadFollowUpRequest(BaseModel):
    follow_up_date: datetime | None = None


class ThreadSnoozeRequest(BaseModel):
    snoozed_until: datetime


class CommunicationListResponse(BaseModel):
    items: list[CommunicationSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class ThreadListResponse(BaseModel):
    items: list[ThreadSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class CommunicationMutationResponse(BaseModel):
    communication: CommunicationDetail
    warnings: list[str] = Field(default_factory=list)


class ThreadMutationResponse(BaseModel):
    thread: ThreadDetail
    warnings: list[str] = Field(default_factory=list)


class TemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    template_type: CrmTemplateType
    subject: str | None = None
    channel: CrmCommunicationChannel | None = None
    is_shared: bool
    is_active: bool
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class TemplateDetail(TemplateSummary):
    body: str
    body_html: str | None = None
    variables: list[str] | None = None
    owner_id: UUID | None = None
    team_id: UUID | None = None
    created_by: UUID | None = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    template_type: CrmTemplateType
    subject: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1)
    body_html: str | None = None
    variables: list[str] | None = None
    channel: CrmCommunicationChannel | None = None
    is_shared: bool = False
    tags: list[str] | None = None


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    subject: str | None = None
    body: str | None = None
    body_html: str | None = None
    variables: list[str] | None = None
    is_shared: bool | None = None
    is_active: bool | None = None
    tags: list[str] | None = None


class TemplateListResponse(BaseModel):
    items: list[TemplateSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class SignatureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    channel: CrmCommunicationChannel | None = None
    scope: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SignatureDetail(SignatureSummary):
    body_html: str
    body_text: str | None = None
    owner_id: UUID | None = None
    team_id: UUID | None = None
    department_id: UUID | None = None


class SignatureCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    channel: CrmCommunicationChannel | None = None
    scope: str = "personal"
    is_default: bool = False


class SignatureUpdate(BaseModel):
    name: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class SignatureListResponse(BaseModel):
    items: list[SignatureSummary]
    request_id: str = ""


class SequenceStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    step_order: int
    step_type: CrmSequenceStepType
    template_id: UUID | None = None
    wait_days: int | None = None
    wait_hours: int | None = None
    condition_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None


class SequenceStepInput(BaseModel):
    step_order: int = 0
    step_type: CrmSequenceStepType
    template_id: UUID | None = None
    wait_days: int | None = None
    wait_hours: int | None = None
    condition_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None


class SequenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None = None
    enrollment_type: CrmSequenceEnrollmentType
    is_active: bool
    step_count: int = 0
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class SequenceDetail(SequenceSummary):
    steps: list[SequenceStepSchema] = Field(default_factory=list)
    owner_id: UUID | None = None
    created_by: UUID | None = None


class SequenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    enrollment_type: CrmSequenceEnrollmentType = CrmSequenceEnrollmentType.MANUAL
    tags: list[str] | None = None
    steps: list[SequenceStepInput] = Field(default_factory=list)


class SequenceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enrollment_type: CrmSequenceEnrollmentType | None = None
    is_active: bool | None = None
    tags: list[str] | None = None
    steps: list[SequenceStepInput] | None = None


class SequenceListResponse(BaseModel):
    items: list[SequenceSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class PreferenceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entity_type: CrmCommunicationEntityType
    entity_id: UUID
    preferred_channel: CrmCommunicationChannel | None = None
    allowed_channels: list[str] | None = None
    blocked_channels: list[str] | None = None
    consent_email: bool | None = None
    consent_sms: bool | None = None
    consent_whatsapp: bool | None = None
    consent_phone: bool | None = None
    do_not_contact: bool
    do_not_contact_reason: str | None = None
    metadata_json: dict[str, Any] | None = None
    updated_at: datetime


class PreferenceUpsert(BaseModel):
    preferred_channel: CrmCommunicationChannel | None = None
    allowed_channels: list[str] | None = None
    blocked_channels: list[str] | None = None
    consent_email: bool | None = None
    consent_sms: bool | None = None
    consent_whatsapp: bool | None = None
    consent_phone: bool | None = None
    do_not_contact: bool | None = None
    do_not_contact_reason: str | None = None
    metadata_json: dict[str, Any] | None = None


class ProviderStatusSchema(BaseModel):
    provider: str
    channel: CrmCommunicationChannel
    status: str
    message: str | None = None
    last_sync_at: datetime | None = None


class ProviderStatusListResponse(BaseModel):
    items: list[ProviderStatusSchema]
    request_id: str = ""


class AnalyticsMetricSchema(BaseModel):
    key: str
    label: str
    value: float | int | None = None
    unavailable: bool = False
    unavailable_reason: str | None = None


class AnalyticsDashboardResponse(BaseModel):
    metrics: list[AnalyticsMetricSchema]
    period_start: datetime | None = None
    period_end: datetime | None = None
    request_id: str = ""


class ConsentWarning(BaseModel):
    code: str
    message: str
    entity_type: CrmCommunicationEntityType | None = None
    entity_id: UUID | None = None
