"""CRM activity API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.crm_activity import (
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
    CrmFollowUpReason,
    CrmRecurrenceFrequency,
    CrmReminderChannel,
    CrmTaskStatus,
)


class CrmActivityEntityLinkSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: CrmActivityEntityType
    entity_id: UUID
    is_primary: bool = False


class CrmActivityChecklistItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    sort_order: int = 0
    is_completed: bool = False
    completed_by: UUID | None = None
    completed_at: datetime | None = None


class CrmActivityChecklistItemInput(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    sort_order: int = 0
    is_completed: bool = False


class CrmActivityAttachmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    file_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    document_id: UUID | None = None
    created_at: datetime


class CrmActivityAttachmentInput(BaseModel):
    file_name: str = Field(min_length=1, max_length=500)
    file_url: str | None = Field(default=None, max_length=2000)
    mime_type: str | None = Field(default=None, max_length=120)
    file_size_bytes: int | None = None
    document_id: UUID | None = None


class CrmActivityReminderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: CrmReminderChannel
    remind_at: datetime
    offset_minutes: int | None = None
    is_sent: bool = False


class CrmActivityReminderInput(BaseModel):
    channel: CrmReminderChannel = CrmReminderChannel.IN_APP
    remind_at: datetime
    offset_minutes: int | None = None


class CrmActivityCommentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None = None
    body: str
    mentions: list[str] | None = None
    reactions: dict[str, list[str]] | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CrmActivityCommentInput(BaseModel):
    body: str = Field(min_length=1)
    parent_id: UUID | None = None
    mentions: list[str] | None = None


class CrmActivitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: CrmActivityEntityType
    entity_id: UUID
    related_entity_type: CrmActivityEntityType | None = None
    related_entity_id: UUID | None = None
    activity_type: CrmActivityType
    activity_category: CrmActivityCategory
    title: str
    summary: str | None = None
    status: CrmActivityStatus
    task_status: CrmTaskStatus | None = None
    priority: CrmActivityPriority
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    reminder_date: datetime | None = None
    timezone: str | None = None
    location: str | None = None
    meeting_url: str | None = None
    tags: list[str] | None = None
    visibility: CrmActivityVisibility
    is_pinned: bool = False
    is_favorite: bool = False
    follow_up_reason: CrmFollowUpReason | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    archived_at: datetime | None = None
    has_attachments: bool = False
    comment_count: int = 0
    entity_name: str | None = None
    assigned_user_name: str | None = None
    owner_name: str | None = None
    created_by_name: str | None = None
    related_entity_name: str | None = None


class CrmActivityDetail(CrmActivitySummary):
    description: str | None = None
    outcome: str | None = None
    duration_minutes: int | None = None
    estimated_duration_minutes: int | None = None
    actual_duration_minutes: int | None = None
    recurrence_frequency: CrmRecurrenceFrequency | None = None
    recurrence_rule: str | None = None
    metadata_json: dict[str, object] | None = None
    entity_links: list[CrmActivityEntityLinkSchema] = Field(default_factory=list)
    checklist_items: list[CrmActivityChecklistItemSchema] = Field(default_factory=list)
    attachments: list[CrmActivityAttachmentSchema] = Field(default_factory=list)
    reminders: list[CrmActivityReminderSchema] = Field(default_factory=list)
    comments: list[CrmActivityCommentSchema] = Field(default_factory=list)


class CrmActivityCreate(BaseModel):
    entity_type: CrmActivityEntityType
    entity_id: UUID
    related_entity_type: CrmActivityEntityType | None = None
    related_entity_id: UUID | None = None
    activity_type: CrmActivityType
    activity_category: CrmActivityCategory | None = None
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    outcome: str | None = None
    status: CrmActivityStatus = CrmActivityStatus.PLANNED
    task_status: CrmTaskStatus | None = None
    priority: CrmActivityPriority = CrmActivityPriority.MEDIUM
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration_minutes: int | None = None
    due_date: datetime | None = None
    reminder_date: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=500)
    meeting_url: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    visibility: CrmActivityVisibility = CrmActivityVisibility.ORGANIZATION
    follow_up_reason: CrmFollowUpReason | None = None
    recurrence_frequency: CrmRecurrenceFrequency | None = None
    recurrence_rule: str | None = Field(default=None, max_length=500)
    estimated_duration_minutes: int | None = None
    metadata_json: dict[str, object] | None = None
    entity_links: list[CrmActivityEntityLinkSchema] | None = None
    checklist_items: list[CrmActivityChecklistItemInput] | None = None
    attachments: list[CrmActivityAttachmentInput] | None = None
    reminders: list[CrmActivityReminderInput] | None = None


class CrmActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    outcome: str | None = None
    status: CrmActivityStatus | None = None
    task_status: CrmTaskStatus | None = None
    priority: CrmActivityPriority | None = None
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None
    assigned_team_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration_minutes: int | None = None
    due_date: datetime | None = None
    reminder_date: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=500)
    meeting_url: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    visibility: CrmActivityVisibility | None = None
    follow_up_reason: CrmFollowUpReason | None = None
    recurrence_frequency: CrmRecurrenceFrequency | None = None
    recurrence_rule: str | None = Field(default=None, max_length=500)
    estimated_duration_minutes: int | None = None
    actual_duration_minutes: int | None = None
    metadata_json: dict[str, object] | None = None
    is_pinned: bool | None = None
    is_favorite: bool | None = None


class CrmActivityListResponse(BaseModel):
    items: list[CrmActivitySummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class CrmActivityMutationResponse(BaseModel):
    activity: CrmActivityDetail


class CrmTimelineEntry(BaseModel):
    id: str
    source: str
    activity_type: str
    title: str
    summary: str | None = None
    status: str | None = None
    priority: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    actor_name: str | None = None
    created_at: datetime
    is_system_event: bool = False
    metadata_json: dict[str, object] | None = None


class CrmTimelineResponse(BaseModel):
    items: list[CrmTimelineEntry]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class CrmActivityBulkUpdateRequest(BaseModel):
    activity_ids: list[UUID] = Field(min_length=1)
    assigned_user_id: UUID | None = None
    status: CrmActivityStatus | None = None
    priority: CrmActivityPriority | None = None
    archive: bool | None = None
    restore: bool | None = None


class CrmActivityBulkUpdateResponse(BaseModel):
    updated: int


class CrmFollowUpCreate(BaseModel):
    entity_type: CrmActivityEntityType
    entity_id: UUID
    reason: CrmFollowUpReason
    title: str | None = Field(default=None, max_length=500)
    due_date: datetime
    reminder_date: datetime | None = None
    notes: str | None = None
    owner_id: UUID | None = None
    assigned_user_id: UUID | None = None


class CrmFollowUpSummary(CrmActivitySummary):
    pass


class CrmFollowUpListResponse(BaseModel):
    items: list[CrmFollowUpSummary]
    page: int
    page_size: int
    total: int
    pages: int


class CrmCalendarEvent(BaseModel):
    id: UUID
    title: str
    activity_type: CrmActivityType
    status: CrmActivityStatus
    start_date: datetime | None = None
    end_date: datetime | None = None
    due_date: datetime | None = None
    all_day: bool = False
    entity_type: CrmActivityEntityType
    entity_id: UUID
    assigned_user_id: UUID | None = None
    color: str | None = None
    entity_name: str | None = None
    assigned_user_name: str | None = None


class CrmCalendarResponse(BaseModel):
    events: list[CrmCalendarEvent]
    start: datetime
    end: datetime


class CrmActivitySavedFilterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    filters_json: dict[str, object]
    filter_logic: str = Field(default="and", pattern="^(and|or)$")
    is_shared: bool = False


class CrmActivitySavedFilterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    filters_json: dict[str, object]
    filter_logic: str
    is_shared: bool
    created_at: datetime


class CrmActivityDashboardWidgets(BaseModel):
    todays_tasks: list[CrmActivitySummary]
    overdue_tasks: list[CrmActivitySummary]
    upcoming_meetings: list[CrmActivitySummary]
    follow_ups_due: list[CrmActivitySummary]
    recent_notes: list[CrmActivitySummary]
    recent_activities: list[CrmActivitySummary]
    missed_activities: list[CrmActivitySummary]
