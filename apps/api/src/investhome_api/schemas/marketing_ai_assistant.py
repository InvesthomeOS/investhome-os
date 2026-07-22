"""Schemas for AI Marketing Assistant — Sprint 8A4."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ASSISTANT_MODES = (
    "marketing_summary",
    "campaign_analysis",
    "content_draft",
    "campaign_brief",
    "audience_suggestion",
    "channel_suggestion",
    "translation",
    "next_actions",
)

CONTENT_DRAFT_TYPES = (
    "social_media_post",
    "instagram_caption",
    "linkedin_post",
    "facebook_post",
    "whatsapp_message",
    "email_draft",
    "blog_outline",
    "short_blog_draft",
    "property_introduction",
    "investor_update",
    "campaign_headline",
    "advertisement_copy",
    "video_script_outline",
    "call_to_action_options",
)

TONES = (
    "professional",
    "informative",
    "premium",
    "investor_focused",
    "sales_focused",
    "friendly",
    "concise",
)

LANGUAGES = ("tr", "en")


class AssistantGenerateRequest(BaseModel):
    mode: str = Field(default="marketing_summary", description="Assistant mode key")
    organization_id: UUID | None = None
    project_id: UUID | None = None
    campaign_id: UUID | None = None
    asset_ids: list[UUID] = Field(default_factory=list, max_length=20)
    audience_id: UUID | None = None
    language: str = "en"
    target_language: str | None = None
    tone: str | None = None
    channel: str | None = None
    content_type: str | None = None
    length: str | None = None
    call_to_action: str | None = None
    source_text: str | None = Field(default=None, max_length=12000)
    adaptation_style: str | None = None
    user_instruction: str | None = Field(default=None, max_length=4000)
    client_request_id: str | None = Field(default=None, max_length=80)
    regenerate_of_id: UUID | None = None


class AssistantDataSource(BaseModel):
    kind: str
    label: str
    entity_id: UUID | str | None = None
    detail: str | None = None


class AssistantActionLink(BaseModel):
    label: str
    href: str
    reason: str | None = None


class AssistantGenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    output_type: str
    status: str
    title: str | None = None
    language: str | None = None
    generated_content: str
    structured_output: dict | None = None
    data_sources: list[AssistantDataSource] | list[dict] = Field(default_factory=list)
    data_warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    safety_blocked: bool = False
    safety_message: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    prompt_key: str | None = None
    prompt_version: str | None = None
    token_usage: dict | None = None
    action_links: list[AssistantActionLink] = Field(default_factory=list)
    data_freshness_at: datetime | None = None
    organization_id: UUID | None = None
    project_id: UUID | None = None
    campaign_id: UUID | None = None
    asset_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AssistantOutputListResponse(BaseModel):
    items: list[AssistantGenerateResponse]
    total: int
    page: int = 1
    page_size: int = 20


class AssistantSaveRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    generated_content: str | None = None
    structured_output: dict | None = None


class AssistantArchiveRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AssistantModeInfo(BaseModel):
    key: str
    prompt_key: str
    label_key: str
    requires_campaign: bool = False
    requires_source_text: bool = False


class AssistantModesResponse(BaseModel):
    modes: list[AssistantModeInfo]
    content_draft_types: list[str]
    tones: list[str]
    languages: list[str]
    provider_available: bool
    provider_name: str | None = None
