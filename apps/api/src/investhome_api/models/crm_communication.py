"""CRM Communication — unified communication records, threads, templates, and sequences."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
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


class CrmCommunicationChannel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PHONE = "phone"
    CALL = "call"
    ZOOM = "zoom"
    TEAMS = "teams"
    MEETING = "meeting"
    TASK = "task"
    COMMENT = "comment"
    INTERNAL_MESSAGE = "internal_message"
    NOTE = "note"
    SYSTEM_NOTIFICATION = "system_notification"
    OTHER = "other"


class CrmCommunicationSource(str, enum.Enum):
    BITRIX = "bitrix"
    LIVE_EMAIL = "live_email"
    LIVE_WHATSAPP = "live_whatsapp"
    MANUAL = "manual"


class CrmCommunicationMatchStatus(str, enum.Enum):
    UNMATCHED = "unmatched"
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    IGNORED = "ignored"


class CrmUserCommunicationAccountStatus(str, enum.Enum):
    NOT_CONNECTED = "not_connected"
    PENDING = "pending"
    CONNECTED = "connected"
    ERROR = "error"
    NEEDS_REAUTH = "needs_reauth"
    DISCONNECTED = "disconnected"


class CrmUserCommunicationAccountHealth(str, enum.Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"


class CrmCommunicationDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    SYSTEM = "system"


class CrmCommunicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class CrmCommunicationVisibility(str, enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"
    RESTRICTED = "restricted"


class CrmCommunicationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CrmCommunicationEntityType(str, enum.Enum):
    CONTACT = "contact"
    COMPANY = "company"
    OPPORTUNITY = "opportunity"
    INVESTOR = "investor"
    PROPERTY = "property"
    PROJECT = "project"
    TRANSACTION = "transaction"
    INTERNAL_USER = "internal_user"
    RELATIONSHIP = "relationship"


class CrmThreadStatus(str, enum.Enum):
    OPEN = "open"
    PENDING = "pending"
    SNOOZED = "snoozed"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CrmTemplateType(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL_SCRIPT = "call_script"
    MEETING_AGENDA = "meeting_agenda"
    INTERNAL = "internal"
    FOLLOW_UP = "follow_up"


class CrmSequenceStepType(str, enum.Enum):
    SEND_EMAIL = "send_email"
    SEND_WHATSAPP = "send_whatsapp"
    SEND_SMS = "send_sms"
    CREATE_CALL_TASK = "create_call_task"
    CREATE_FOLLOW_UP = "create_follow_up"
    WAIT = "wait"
    CONDITION = "condition"
    STOP = "stop"


class CrmSequenceEnrollmentType(str, enum.Enum):
    MANUAL = "manual"
    LIST = "list"
    FILTER = "filter"
    OPPORTUNITY = "opportunity"
    EVENT = "event"


class CrmUserCommunicationAccount(Base):
    """Investhome OS user-owned Email / WhatsApp connection — not a CRM contact."""

    __tablename__ = "crm_user_communication_accounts"
    __table_args__ = (
        Index("ix_crm_user_comm_accounts_user", "user_id"),
        Index("ix_crm_user_comm_accounts_channel", "channel_type"),
        Index("ix_crm_user_comm_accounts_status", "status"),
        Index(
            "uq_crm_user_comm_accounts_identity",
            "channel_type",
            "identity",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    identity: Mapped[str] = mapped_column(String(255), nullable=False)
    account_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CrmUserCommunicationAccountStatus.NOT_CONNECTED.value
    )
    health: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CrmUserCommunicationAccountHealth.UNKNOWN.value
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrmCommunicationThread(Base):
    __tablename__ = "crm_communication_threads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    channels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    participant_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    related_entity_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    last_communication_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=CrmCommunicationPriority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=CrmThreadStatus.OPEN.value)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    communications: Mapped[list[CrmCommunication]] = relationship(
        "CrmCommunication", back_populates="thread", lazy="selectin"
    )


class CrmCommunication(Base):
    __tablename__ = "crm_communications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=CrmCommunicationStatus.DRAFT.value)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sender_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    recipient_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recipient_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cc_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    bcc_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    participants: Mapped[list | None] = mapped_column(JSON, nullable=True)
    related_entities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_communication_threads.id", ondelete="SET NULL"), nullable=True
    )
    parent_communication_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_communications.id", ondelete="SET NULL"), nullable=True
    )
    external_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=CrmCommunicationPriority.MEDIUM.value)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CrmCommunicationVisibility.ORGANIZATION.value
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    call_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    call_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    meeting_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meeting_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_activities.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_user_communication_accounts.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False, default=CrmCommunicationSource.MANUAL.value)
    match_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CrmCommunicationMatchStatus.MATCHED.value
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True
    )
    agreement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_agreements.id", ondelete="SET NULL"), nullable=True
    )
    sender_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_identities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conversation_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_matches: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped[CrmCommunicationThread | None] = relationship("CrmCommunicationThread", back_populates="communications")
    attachments: Mapped[list[CrmCommunicationAttachment]] = relationship(
        "CrmCommunicationAttachment", back_populates="communication", lazy="selectin"
    )


class CrmCommunicationAttachment(Base):
    __tablename__ = "crm_communication_attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    communication_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("crm_communications.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    communication: Mapped[CrmCommunication] = relationship("CrmCommunication", back_populates="attachments")


class CrmCommunicationTemplate(Base):
    __tablename__ = "crm_communication_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[list | None] = mapped_column(JSON, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrmCommunicationSignature(Base):
    __tablename__ = "crm_communication_signatures"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="personal")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrmCommunicationSequence(Base):
    __tablename__ = "crm_communication_sequences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrollment_type: Mapped[str] = mapped_column(String(30), nullable=False, default=CrmSequenceEnrollmentType.MANUAL.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list[CrmCommunicationSequenceStep]] = relationship(
        "CrmCommunicationSequenceStep", back_populates="sequence", lazy="selectin", order_by="CrmCommunicationSequenceStep.step_order"
    )


class CrmCommunicationSequenceStep(Base):
    __tablename__ = "crm_communication_sequence_steps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("crm_communication_sequences.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_type: Mapped[str] = mapped_column(String(40), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("crm_communication_templates.id", ondelete="SET NULL"), nullable=True
    )
    wait_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wait_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sequence: Mapped[CrmCommunicationSequence] = relationship("CrmCommunicationSequence", back_populates="steps")


class CrmCommunicationPreference(Base):
    __tablename__ = "crm_communication_preferences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    preferred_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    allowed_channels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blocked_channels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    consent_email: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_sms: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_whatsapp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_phone: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_contact_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class CrmCommunicationAuditLog(Base):
    __tablename__ = "crm_communication_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    communication_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("ix_crm_comm_threads_status", CrmCommunicationThread.status)
Index("ix_crm_comm_threads_owner", CrmCommunicationThread.owner_id)
Index("ix_crm_comm_threads_assigned", CrmCommunicationThread.assigned_user_id)
Index("ix_crm_comm_threads_last_comm", CrmCommunicationThread.last_communication_at)
Index("ix_crm_comm_threads_archived", CrmCommunicationThread.archived_at)

Index("ix_crm_communications_thread", CrmCommunication.thread_id)
Index("ix_crm_communications_channel", CrmCommunication.channel)
Index("ix_crm_communications_status", CrmCommunication.status)
Index("ix_crm_communications_direction", CrmCommunication.direction)
Index("ix_crm_communications_owner", CrmCommunication.owner_id)
Index("ix_crm_communications_scheduled", CrmCommunication.scheduled_at)
Index("ix_crm_communications_sent", CrmCommunication.sent_at)
Index("ix_crm_communications_archived", CrmCommunication.archived_at)
Index("ix_crm_communications_recipient", CrmCommunication.recipient_entity_type, CrmCommunication.recipient_entity_id)
Index("ix_crm_communications_account", CrmCommunication.account_id)
Index("ix_crm_communications_source", CrmCommunication.source)
Index("ix_crm_communications_match_status", CrmCommunication.match_status)
Index("ix_crm_communications_contact", CrmCommunication.contact_id)
Index("ix_crm_communications_content_hash", CrmCommunication.content_hash)
Index("ix_crm_communications_occurred", CrmCommunication.occurred_at)
Index("ix_crm_communications_conversation", CrmCommunication.conversation_key)
Index("ix_crm_comm_attach_document", CrmCommunicationAttachment.document_id)

Index("ix_crm_comm_prefs_entity", CrmCommunicationPreference.entity_type, CrmCommunicationPreference.entity_id)
Index("ix_crm_comm_audit_comm", CrmCommunicationAuditLog.communication_id)
Index("ix_crm_comm_audit_thread", CrmCommunicationAuditLog.thread_id)
