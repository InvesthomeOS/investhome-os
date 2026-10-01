"""Schemas for live communication accounts, ingest, and unmatched queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommunicationAccountCreate(BaseModel):
    user_id: UUID | None = None
    channel_type: str = Field(min_length=3, max_length=40)
    provider: str = Field(min_length=2, max_length=80)
    identity: str = Field(min_length=3, max_length=255)
    account_label: str | None = Field(default=None, max_length=255)
    credentials: dict[str, Any] | None = None


class CommunicationAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    user_name: str | None = None
    channel_type: str
    provider: str
    identity: str
    account_label: str
    status: str
    health: str
    last_sync_at: str | None = None
    last_error: str | None = None
    has_credentials: bool = False
    scopes: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CommunicationAccountListResponse(BaseModel):
    items: list[CommunicationAccountOut]
    request_id: str = ""


class LiveIngestAttachment(BaseModel):
    file_name: str
    mime_type: str | None = None
    file_size: int | None = None
    content_base64: str | None = None
    checksum: str | None = None
    document_id: UUID | None = None


class LiveIngestRequest(BaseModel):
    channel: str
    direction: str = "incoming"
    source: str | None = None
    account_id: UUID | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    raw_source: str | None = None
    sender: str | None = None
    sender_identity: str | None = None
    recipients: list[Any] | None = None
    cc: list[Any] | None = None
    occurred_at: datetime | None = None
    external_provider_id: str | None = None
    conversation_id: str | None = None
    contact_id: UUID | None = None
    agreement_id: UUID | None = None
    rfc_message_id: str | None = None
    attachments: list[LiveIngestAttachment] = Field(default_factory=list)


class UnmatchedCommunicationOut(BaseModel):
    id: UUID
    channel: str
    direction: str
    source: str
    sender: str | None = None
    subject: str | None = None
    preview: str | None = None
    occurred_at: datetime | None = None
    match_status: str
    suggested_matches: list[dict[str, Any]] = Field(default_factory=list)
    account_id: UUID | None = None
    conversation_key: str | None = None


class UnmatchedListResponse(BaseModel):
    items: list[UnmatchedCommunicationOut]
    total: int
    page: int
    page_size: int
    request_id: str = ""


class ConfirmMatchRequest(BaseModel):
    contact_id: UUID
    agreement_id: UUID | None = None


class LiveIngestResponse(BaseModel):
    id: UUID
    created: bool
    match_status: str
    contact_id: UUID | None = None
    duplicate: bool = False
    activity_id: UUID | None = None


class GmailAuthorizeResponse(BaseModel):
    authorize_url: str
    redirect_uri: str
    configured: bool = True


class GmailStatusResponse(BaseModel):
    configured: bool
    redirect_uri: str
    connected_count: int = 0
    pilot_limit: int = 1
    client_reuses_drive_oauth: bool = True


class GmailSyncResponse(BaseModel):
    account_id: str
    ok: bool
    mode: str | None = None
    ingested: int = 0
    skipped: int = 0
    duplicates: int = 0
    error: str | None = None


class CommunicationFeedStats(BaseModel):
    total: int = 0
    email: int = 0
    whatsapp: int = 0
    unmatched: int = 0


class CommunicationFeedItem(BaseModel):
    id: UUID
    source: str
    channel: str
    direction: str
    occurred_at: datetime | None = None
    subject: str | None = None
    preview: str | None = None
    contact_id: UUID | None = None
    contact_name: str | None = None
    agreement_id: UUID | None = None
    project_group: str | None = None
    project_label: str | None = None
    unit_number: str | None = None
    project_unit: str | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    conversation_key: str | None = None
    source_key: str
    activity_id: UUID | None = None


class CommunicationFeedResponse(BaseModel):
    items: list[CommunicationFeedItem]
    total: int
    page: int
    page_size: int
    pages: int
    stats: CommunicationFeedStats
    request_id: str = ""


class CommunicationConversationMessage(BaseModel):
    id: UUID
    title: str
    summary: str | None = None
    actor_name: str | None = None
    created_at: datetime
    activity_type: str = "whatsapp"
    metadata: dict[str, Any] | None = None


class CommunicationConversationResponse(BaseModel):
    contact_id: UUID | None = None
    contact_name: str | None = None
    conversation_key: str | None = None
    messages: list[CommunicationConversationMessage] = Field(default_factory=list)
    request_id: str = ""
