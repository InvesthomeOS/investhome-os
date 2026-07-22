"""Pydantic schemas for marketing channel communications."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadinessCheckItem(BaseModel):
    key: str
    label: str
    passed: bool
    message: str | None = None
    details: dict | None = None


class ReadinessResponse(BaseModel):
    state: str
    ready: bool
    checks: list[ReadinessCheckItem]
    recipients: dict | None = None


class ProviderStatusResponse(BaseModel):
    channel: str
    status: str
    connected: bool
    message: str | None = None
    channel_id: str | None = None
    connection_status: str | None = None


class RecipientCalculationResponse(BaseModel):
    total: int
    eligible: int
    excluded: int
    duplicate_count: int
    exclusions: list[dict]


class PersonalizationPreviewRequest(BaseModel):
    config: dict | None = None
    sample_contact: dict | None = None


class PersonalizationPreviewResponse(BaseModel):
    preview: str
    tokens_used: list[str]
    config: dict | None = None


class OptOutRequest(BaseModel):
    contact_id: UUID | None = None
    company_id: UUID | None = None
    channel: str


class OptOutResponse(BaseModel):
    updated: bool
    channel: str
    consent: str


class FrequencyPolicyCreate(BaseModel):
    name: str
    channel: str
    max_messages_per_day: int | None = None
    max_messages_per_week: int | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None
    config_json: dict | None = None


class FrequencyPolicyResponse(FrequencyPolicyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeliveryEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel: str
    campaign_type: str
    campaign_id: UUID
    contact_id: UUID | None
    event_type: str
    occurred_at: datetime


class DeliveryEventListResponse(BaseModel):
    items: list[DeliveryEventResponse]
    total: int
    page: int
    page_size: int
    pages: int


class IdempotentSendRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    scheduled_at: datetime | None = None


class SendOperationResponse(BaseModel):
    idempotent: bool
    operation_id: str | None = None
    status: str | None = None
    scheduled: bool | None = None
    published: bool | None = None
    sent: bool | None = None


# Social
class SocialAccountCreate(BaseModel):
    network: str
    display_name: str
    handle: str | None = None
    channel_id: UUID | None = None
    capabilities_json: dict | None = None


class SocialAccountResponse(SocialAccountCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    connection_status: str
    is_active: bool
    created_at: datetime


class SocialPostVariantCreate(BaseModel):
    social_account_id: UUID
    network: str
    body_text: str | None = None
    media_refs_json: list | None = None


class SocialPostCreate(BaseModel):
    title: str | None = None
    body_text: str | None = None
    marketing_campaign_id: UUID | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None
    scheduled_at: datetime | None = None
    media_refs_json: list | None = None
    variants: list[SocialPostVariantCreate] = []


class SocialPostUpdate(BaseModel):
    title: str | None = None
    body_text: str | None = None
    scheduled_at: datetime | None = None
    media_refs_json: list | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None


class SocialPostResponse(SocialPostCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    approval_status: str
    readiness_state: str
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SocialPostListResponse(BaseModel):
    items: list[SocialPostResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SocialDashboardResponse(BaseModel):
    total_posts: int
    scheduled_posts: int
    connected_accounts: int
    provider_status: ProviderStatusResponse


class SocialInboxItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    social_account_id: UUID
    network: str
    item_type: str
    author_name: str | None
    body_text: str | None
    status: str
    received_at: datetime | None


# Email
class EmailCampaignCreate(BaseModel):
    name: str
    subject: str | None = None
    preview_text: str | None = None
    audience_id: UUID | None = None
    marketing_campaign_id: UUID | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    unsubscribe_required: bool = True
    unsubscribe_link_present: bool = False
    wizard_step: int | None = 1
    wizard_state_json: dict | None = None


class EmailCampaignUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    preview_text: str | None = None
    audience_id: UUID | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    scheduled_at: datetime | None = None
    unsubscribe_link_present: bool | None = None
    wizard_step: int | None = None
    wizard_state_json: dict | None = None
    personalisation_config_json: dict | None = None


class EmailCampaignResponse(EmailCampaignCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    approval_status: str
    readiness_state: str
    recipient_count: int | None = None
    eligible_recipient_count: int | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EmailCampaignListResponse(BaseModel):
    items: list[EmailCampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int


class EmailDashboardResponse(BaseModel):
    total_campaigns: int
    scheduled_campaigns: int
    provider_status: ProviderStatusResponse


class EmailTemplateCreate(BaseModel):
    name: str
    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None


class EmailTemplateResponse(EmailTemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    created_at: datetime


class EmailSenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    from_email: str
    from_name: str | None
    is_default: bool
    is_active: bool


class EmailDomainCreate(BaseModel):
    domain: str


class EmailDomainResponse(EmailDomainCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    verification_status: str
    dkim_status: str | None
    spf_status: str | None


class EmailSequenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    status: str
    audience_id: UUID | None


class EmailSequenceStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sequence_id: UUID
    step_order: int
    name: str
    delay_hours: int


class EmailTestSendRequest(BaseModel):
    recipient_email: str


# WhatsApp
class WhatsAppCampaignCreate(BaseModel):
    name: str
    audience_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None
    marketing_campaign_id: UUID | None = None


class WhatsAppCampaignUpdate(BaseModel):
    name: str | None = None
    audience_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    scheduled_at: datetime | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None


class WhatsAppCampaignResponse(WhatsAppCampaignCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    approval_status: str
    readiness_state: str
    recipient_count: int | None = None
    eligible_recipient_count: int | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WhatsAppCampaignListResponse(BaseModel):
    items: list[WhatsAppCampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int


class WhatsAppDashboardResponse(BaseModel):
    total_campaigns: int
    provider_status: ProviderStatusResponse


class WhatsAppTemplateCreate(BaseModel):
    name: str
    language: str = "en"
    category: str | None = None
    body_text: str | None = None
    header_text: str | None = None
    footer_text: str | None = None
    placeholders_json: list | None = None
    content_id: UUID | None = None


class WhatsAppTemplateResponse(WhatsAppTemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    created_at: datetime


class WhatsAppSenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    phone_number: str
    connection_status: str
    is_default: bool


class WhatsAppConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    phone_number: str
    status: str
    handoff_status: str | None
    last_message_at: datetime | None


# SMS
class SmsCampaignCreate(BaseModel):
    name: str
    message_body: str | None = None
    audience_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    content_id: UUID | None = None
    content_version_id: UUID | None = None
    marketing_campaign_id: UUID | None = None
    opt_out_required: bool = True
    opt_out_text_present: bool = False


class SmsCampaignUpdate(BaseModel):
    name: str | None = None
    message_body: str | None = None
    audience_id: UUID | None = None
    template_id: UUID | None = None
    sender_profile_id: UUID | None = None
    scheduled_at: datetime | None = None
    opt_out_text_present: bool | None = None


class SmsCampaignResponse(SmsCampaignCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    approval_status: str
    readiness_state: str
    character_count: int | None = None
    segment_count: int | None = None
    recipient_count: int | None = None
    eligible_recipient_count: int | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SmsCampaignListResponse(BaseModel):
    items: list[SmsCampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SmsDashboardResponse(BaseModel):
    total_campaigns: int
    provider_status: ProviderStatusResponse


class SmsTemplateCreate(BaseModel):
    name: str
    body_text: str
    content_id: UUID | None = None


class SmsTemplateResponse(SmsTemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    character_count: int | None
    segment_count: int | None
    is_active: bool
    created_at: datetime


class SmsValidationResponse(BaseModel):
    character_count: int
    segment_count: int


class SmsSenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    sender_id: str
    connection_status: str
    is_default: bool


class SmsTestSendRequest(BaseModel):
    phone_number: str
