"""Work item API schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.work_item import (
    AttendanceStatus,
    ContactMethod,
    FollowUpOutcome,
    MeetingType,
    ParticipantRole,
    RelatedEntityType,
    ResponseStatus,
    WorkItemPriority,
    WorkItemStatus,
    WorkItemType,
)


class WorkItemParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    party_id: UUID | None
    user_id: UUID | None
    participant_role: ParticipantRole
    attendance_status: AttendanceStatus
    created_at: datetime


class MeetingRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_item_id: UUID
    meeting_type: MeetingType
    location: str | None
    meeting_url: str | None
    agenda: str | None
    notes: str | None
    outcome: str | None
    decision_summary: str | None
    next_steps: str | None
    started_at: datetime | None
    ended_at: datetime | None


class FollowUpRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_item_id: UUID
    follow_up_type: WorkItemType
    contact_method: ContactMethod
    outcome: FollowUpOutcome | None
    response_status: ResponseStatus
    next_follow_up_at: datetime | None
    notes: str | None


class WorkItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    work_item_type: WorkItemType
    status: WorkItemStatus
    effective_status: WorkItemStatus | None = None
    priority: WorkItemPriority
    assigned_user_id: UUID | None
    created_by_user_id: UUID | None
    due_at: datetime | None
    start_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    reminder_at: datetime | None
    related_entity_type: RelatedEntityType | None
    related_entity_id: UUID | None
    project_id: UUID | None
    lead_id: UUID | None
    opportunity_id: UUID | None
    party_id: UUID | None
    inventory_asset_id: UUID | None
    proposal_id: UUID | None
    outcome: str | None
    next_action_type: str | None
    next_action_date: date | None
    is_private: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    meeting: MeetingRecordResponse | None = None
    follow_up: FollowUpRecordResponse | None = None
    participants: list[WorkItemParticipantResponse] = Field(default_factory=list)


class WorkItemListResponse(BaseModel):
    items: list[WorkItemResponse]
    total: int
    offset: int
    limit: int


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    work_item_type: WorkItemType = WorkItemType.TASK
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    assigned_user_id: UUID | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    reminder_at: datetime | None = None
    related_entity_type: RelatedEntityType | None = None
    related_entity_id: UUID | None = None
    project_id: UUID | None = None
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    party_id: UUID | None = None
    inventory_asset_id: UUID | None = None
    proposal_id: UUID | None = None
    is_private: bool = False


class WorkItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    work_item_type: WorkItemType | None = None
    priority: WorkItemPriority | None = None
    assigned_user_id: UUID | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    reminder_at: datetime | None = None
    outcome: str | None = None
    is_private: bool | None = None
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    party_id: UUID | None = None
    project_id: UUID | None = None
    inventory_asset_id: UUID | None = None
    proposal_id: UUID | None = None


class StatusChangeRequest(BaseModel):
    status: WorkItemStatus
    reason: str | None = None


class RescheduleRequest(BaseModel):
    due_at: datetime


class CompleteWorkItemRequest(BaseModel):
    outcome: str | None = None
    next_follow_up: dict | None = None


class MeetingCreate(WorkItemCreate):
    meeting_type: MeetingType = MeetingType.VIDEO
    location: str | None = None
    meeting_url: str | None = None
    agenda: str | None = None
    participants: list[dict] | None = None


class MeetingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    assigned_user_id: UUID | None = None
    meeting_type: MeetingType | None = None
    location: str | None = None
    meeting_url: str | None = None
    agenda: str | None = None
    notes: str | None = None
    outcome: str | None = None
    decision_summary: str | None = None
    next_steps: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class MeetingCompleteRequest(MeetingUpdate):
    next_follow_up: dict | None = None


class FollowUpCreate(WorkItemCreate):
    contact_method: ContactMethod = ContactMethod.CALL
    notes: str | None = None


class FollowUpCompleteRequest(BaseModel):
    outcome: FollowUpOutcome | None = None
    response_status: ResponseStatus | None = None
    notes: str | None = None
    next_follow_up: dict | None = None


class WorkDashboardKpisResponse(BaseModel):
    today_count: int
    overdue_count: int
    meetings_today_count: int
    blocked_count: int
    waiting_count: int
    my_work_count: int
    no_next_action_count: int


class CalendarEventResponse(BaseModel):
    id: UUID
    title: str
    work_item_type: WorkItemType
    status: WorkItemStatus
    start_at: datetime | None
    due_at: datetime | None
    assigned_user_id: UUID | None
    is_private: bool
