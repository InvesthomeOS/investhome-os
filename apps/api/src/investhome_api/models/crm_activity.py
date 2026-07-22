"""CRM Activity — unified operational memory for contacts, companies, and relationships."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class CrmActivityEntityType(str, enum.Enum):
    CONTACT = "contact"
    COMPANY = "company"
    OPPORTUNITY = "opportunity"
    INVESTOR = "investor"
    PROPERTY = "property"
    PROJECT = "project"
    TRANSACTION = "transaction"
    INVESTMENT = "investment"
    VENDOR = "vendor"
    INTERNAL_USER = "internal_user"
    RELATIONSHIP = "relationship"


class CrmActivityType(str, enum.Enum):
    NOTE = "note"
    PHONE_CALL = "phone_call"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    MEETING = "meeting"
    ZOOM_MEETING = "zoom_meeting"
    TEAMS_MEETING = "teams_meeting"
    SITE_VISIT = "site_visit"
    PROPERTY_TOUR = "property_tour"
    INVESTOR_MEETING = "investor_meeting"
    CONSTRUCTION_MEETING = "construction_meeting"
    INSPECTION = "inspection"
    DOCUMENT_SENT = "document_sent"
    DOCUMENT_RECEIVED = "document_received"
    PROPOSAL_SENT = "proposal_sent"
    PROPOSAL_RECEIVED = "proposal_received"
    RESERVATION = "reservation"
    CONTRACT_SIGNED = "contract_signed"
    CLOSING = "closing"
    PAYMENT = "payment"
    TASK = "task"
    REMINDER = "reminder"
    FOLLOW_UP = "follow_up"
    INTERNAL_DISCUSSION = "internal_discussion"
    COMMENT = "comment"
    SYSTEM_EVENT = "system_event"
    AUTOMATION_EVENT = "automation_event"
    OTHER = "other"


class CrmActivityCategory(str, enum.Enum):
    COMMUNICATION = "communication"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"
    DOCUMENT = "document"
    TRANSACTION = "transaction"
    FOLLOW_UP = "follow_up"
    SYSTEM = "system"
    OTHER = "other"


class CrmActivityStatus(str, enum.Enum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"
    DEFERRED = "deferred"
    ARCHIVED = "archived"


class CrmTaskStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class CrmActivityPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CrmActivityVisibility(str, enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"
    RESTRICTED = "restricted"


class CrmFollowUpReason(str, enum.Enum):
    INVESTOR = "investor"
    BROKER = "broker"
    LENDER = "lender"
    PROPERTY = "property"
    OPPORTUNITY = "opportunity"
    RELATIONSHIP_REVIEW = "relationship_review"
    CONTRACT = "contract"
    PAYMENT = "payment"
    INSPECTION = "inspection"
    CUSTOM = "custom"


class CrmCallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CrmCallOutcome(str, enum.Enum):
    NO_ANSWER = "no_answer"
    LEFT_VOICEMAIL = "left_voicemail"
    CONNECTED = "connected"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    CLOSED = "closed"


class CrmReminderChannel(str, enum.Enum):
    NOTIFICATION = "notification"
    EMAIL = "email"
    IN_APP = "in_app"


class CrmRecurrenceFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class CrmActivity(Base):
    __tablename__ = "crm_activities"
    __table_args__ = (
        Index("ix_crm_activities_entity", "entity_type", "entity_id"),
        Index("ix_crm_activities_type", "activity_type"),
        Index("ix_crm_activities_status", "status"),
        Index("ix_crm_activities_due_date", "due_date"),
        Index("ix_crm_activities_start_date", "start_date"),
        Index("ix_crm_activities_owner", "owner_id"),
        Index("ix_crm_activities_assigned", "assigned_user_id"),
        Index("ix_crm_activities_created_at", "created_at"),
        Index("ix_crm_activities_archived", "archived_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[CrmActivityEntityType] = mapped_column(
        Enum(CrmActivityEntityType, native_enum=False, length=40),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    related_entity_type: Mapped[CrmActivityEntityType | None] = mapped_column(
        Enum(CrmActivityEntityType, native_enum=False, length=40),
        nullable=True,
    )
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    activity_type: Mapped[CrmActivityType] = mapped_column(
        Enum(CrmActivityType, native_enum=False, length=50),
        nullable=False,
    )
    activity_category: Mapped[CrmActivityCategory] = mapped_column(
        Enum(CrmActivityCategory, native_enum=False, length=30),
        nullable=False,
        default=CrmActivityCategory.OTHER,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CrmActivityStatus] = mapped_column(
        Enum(CrmActivityStatus, native_enum=False, length=30),
        nullable=False,
        default=CrmActivityStatus.PLANNED,
    )
    task_status: Mapped[CrmTaskStatus | None] = mapped_column(
        Enum(CrmTaskStatus, native_enum=False, length=30),
        nullable=True,
    )
    priority: Mapped[CrmActivityPriority] = mapped_column(
        Enum(CrmActivityPriority, native_enum=False, length=20),
        nullable=False,
        default=CrmActivityPriority.MEDIUM,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    visibility: Mapped[CrmActivityVisibility] = mapped_column(
        Enum(CrmActivityVisibility, native_enum=False, length=20),
        nullable=False,
        default=CrmActivityVisibility.ORGANIZATION,
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    follow_up_reason: Mapped[CrmFollowUpReason | None] = mapped_column(
        Enum(CrmFollowUpReason, native_enum=False, length=40),
        nullable=True,
    )
    recurrence_frequency: Mapped[CrmRecurrenceFrequency | None] = mapped_column(
        Enum(CrmRecurrenceFrequency, native_enum=False, length=20),
        nullable=True,
    )
    recurrence_rule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entity_links: Mapped[list[CrmActivityEntityLink]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list[CrmActivityComment]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    checklist_items: Mapped[list[CrmActivityChecklistItem]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list[CrmActivityAttachment]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[list[CrmActivityReminder]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )


class CrmActivityEntityLink(Base):
    __tablename__ = "crm_activity_entity_links"
    __table_args__ = (
        Index("ix_crm_activity_entity_links_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[CrmActivityEntityType] = mapped_column(
        Enum(CrmActivityEntityType, native_enum=False, length=40),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    activity: Mapped[CrmActivity] = relationship(back_populates="entity_links")


class CrmActivityComment(Base):
    __tablename__ = "crm_activity_comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("crm_activity_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    reactions: Mapped[dict[str, list[str]] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped[CrmActivity] = relationship(back_populates="comments")


class CrmActivityChecklistItem(Base):
    __tablename__ = "crm_activity_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped[CrmActivity] = relationship(back_populates="checklist_items")


class CrmActivityAttachment(Base):
    __tablename__ = "crm_activity_attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    activity: Mapped[CrmActivity] = relationship(back_populates="attachments")


class CrmActivityReminder(Base):
    __tablename__ = "crm_activity_reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[CrmReminderChannel] = mapped_column(
        Enum(CrmReminderChannel, native_enum=False, length=20),
        nullable=False,
        default=CrmReminderChannel.IN_APP,
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped[CrmActivity] = relationship(back_populates="reminders")


class CrmFollowUpRule(Base):
    __tablename__ = "crm_follow_up_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger_activity_type: Mapped[CrmActivityType] = mapped_column(
        Enum(CrmActivityType, native_enum=False, length=50),
        nullable=False,
    )
    trigger_status: Mapped[CrmActivityStatus | None] = mapped_column(
        Enum(CrmActivityStatus, native_enum=False, length=30),
        nullable=True,
    )
    follow_up_reason: Mapped[CrmFollowUpReason] = mapped_column(
        Enum(CrmFollowUpReason, native_enum=False, length=40),
        nullable=False,
    )
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CrmActivitySavedFilter(Base):
    __tablename__ = "crm_activity_saved_filters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    filters_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    filter_logic: Mapped[str] = mapped_column(String(10), nullable=False, default="and")
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
