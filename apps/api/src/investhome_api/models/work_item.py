"""Shared work item domain — tasks, meetings, follow-ups."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class WorkItemType(str, enum.Enum):
    TASK = "task"
    CALL = "call"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    SITE_VISIT = "site_visit"
    DOCUMENT_REQUEST = "document_request"
    PROPOSAL_FOLLOW_UP = "proposal_follow_up"
    RESERVATION_FOLLOW_UP = "reservation_follow_up"
    DEPOSIT_FOLLOW_UP = "deposit_follow_up"
    CONTRACT_FOLLOW_UP = "contract_follow_up"
    CLOSING_FOLLOW_UP = "closing_follow_up"
    OTHER = "other"


class WorkItemStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"
    ARCHIVED = "archived"


ACTIVE_WORK_ITEM_STATUSES = frozenset(
    {
        WorkItemStatus.OPEN,
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.WAITING,
        WorkItemStatus.BLOCKED,
        WorkItemStatus.OVERDUE,
    }
)

TERMINAL_WORK_ITEM_STATUSES = frozenset(
    {
        WorkItemStatus.COMPLETED,
        WorkItemStatus.CANCELLED,
        WorkItemStatus.ARCHIVED,
    }
)


class WorkItemPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RelatedEntityType(str, enum.Enum):
    LEAD = "lead"
    OPPORTUNITY = "opportunity"
    PARTY = "party"
    PROJECT = "project"
    INVENTORY_ASSET = "inventory_asset"
    PROPOSAL = "proposal"
    RESERVATION = "reservation"


class MeetingType(str, enum.Enum):
    IN_PERSON = "in_person"
    VIDEO = "video"
    PHONE = "phone"
    SITE = "site"
    OTHER = "other"


class ContactMethod(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    IN_PERSON = "in_person"
    OTHER = "other"


class FollowUpOutcome(str, enum.Enum):
    CONNECTED = "connected"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    SCHEDULED = "scheduled"
    NOT_INTERESTED = "not_interested"
    OTHER = "other"


class ResponseStatus(str, enum.Enum):
    PENDING = "pending"
    RESPONDED = "responded"
    NO_RESPONSE = "no_response"
    DECLINED = "declined"


class ParticipantRole(str, enum.Enum):
    ORGANIZER = "organizer"
    ATTENDEE = "attendee"
    OPTIONAL = "optional"
    LEAD = "lead"
    INVESTOR = "investor"
    INTERNAL = "internal"


class AttendanceStatus(str, enum.Enum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class WorkItem(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        Index("ix_work_items_due_at", "due_at"),
        Index("ix_work_items_assigned_user_id", "assigned_user_id"),
        Index("ix_work_items_opportunity_id", "opportunity_id"),
        Index("ix_work_items_lead_id", "lead_id"),
        Index("ix_work_items_status", "status"),
        Index("ix_work_items_active_assigned_due", "assigned_user_id", "due_at", "archived_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_item_type: Mapped[WorkItemType] = mapped_column(
        Enum(WorkItemType, native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[WorkItemStatus] = mapped_column(
        Enum(WorkItemStatus, native_enum=False, length=30),
        nullable=False,
        default=WorkItemStatus.OPEN,
    )
    priority: Mapped[WorkItemPriority] = mapped_column(
        Enum(WorkItemPriority, native_enum=False, length=20),
        nullable=False,
        default=WorkItemPriority.MEDIUM,
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    related_entity_type: Mapped[RelatedEntityType | None] = mapped_column(
        Enum(RelatedEntityType, native_enum=False, length=30),
        nullable=True,
    )
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    inventory_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legacy_lead_follow_up_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MeetingRecord(Base):
    __tablename__ = "meeting_records"
    __table_args__ = (Index("ix_meeting_records_work_item_id", "work_item_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    meeting_type: Mapped[MeetingType] = mapped_column(
        Enum(MeetingType, native_enum=False, length=20),
        nullable=False,
        default=MeetingType.VIDEO,
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FollowUpRecord(Base):
    __tablename__ = "follow_up_records"
    __table_args__ = (Index("ix_follow_up_records_work_item_id", "work_item_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    follow_up_type: Mapped[WorkItemType] = mapped_column(
        Enum(WorkItemType, native_enum=False, length=50),
        nullable=False,
    )
    contact_method: Mapped[ContactMethod] = mapped_column(
        Enum(ContactMethod, native_enum=False, length=20),
        nullable=False,
        default=ContactMethod.CALL,
    )
    outcome: Mapped[FollowUpOutcome | None] = mapped_column(
        Enum(FollowUpOutcome, native_enum=False, length=30),
        nullable=True,
    )
    response_status: Mapped[ResponseStatus] = mapped_column(
        Enum(ResponseStatus, native_enum=False, length=20),
        nullable=False,
        default=ResponseStatus.PENDING,
    )
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class WorkItemParticipant(Base):
    __tablename__ = "work_item_participants"
    __table_args__ = (Index("ix_work_item_participants_work_item_id", "work_item_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole, native_enum=False, length=20),
        nullable=False,
        default=ParticipantRole.ATTENDEE,
    )
    attendance_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, native_enum=False, length=20),
        nullable=False,
        default=AttendanceStatus.INVITED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WorkItemStatusHistory(Base):
    __tablename__ = "work_item_status_history"
    __table_args__ = (Index("ix_work_item_status_history_work_item_id", "work_item_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
