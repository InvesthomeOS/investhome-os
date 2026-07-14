"""Notification API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.notification import (
    NotificationPriority,
    NotificationSource,
    NotificationStatus,
    NotificationType,
)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: NotificationType
    priority: NotificationPriority
    title_key: str
    message_key: str
    metadata: dict[str, object] | None = Field(default=None, validation_alias="metadata_json")
    related_entity_type: str | None
    related_entity_id: UUID | None
    recipient_user_id: UUID
    created_by: UUID | None
    source: NotificationSource
    status: NotificationStatus
    read_at: datetime | None
    dismissed_at: datetime | None
    expires_at: datetime | None
    is_demo: bool
    created_at: datetime
    link_module: str | None = None
    link_query: dict[str, str] | None = None
    related_label: str | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    pages: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int
    highest_priority: NotificationPriority | None = None


class NotificationSummaryResponse(BaseModel):
    critical: int
    high: int
    medium: int
    unread: int


class NotificationMarkReadResponse(BaseModel):
    updated: int
