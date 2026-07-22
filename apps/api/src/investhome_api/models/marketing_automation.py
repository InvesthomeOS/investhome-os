"""Marketing automation workflow, execution, template, and version models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from investhome_api.db.base import Base


class MarketingAutomationWorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"
    ARCHIVED = "archived"


class MarketingAutomationTriggerType(str, enum.Enum):
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_QUALIFIED = "lead_qualified"
    CRM_CONTACT_CREATED = "crm_contact_created"
    CRM_CONTACT_UPDATED = "crm_contact_updated"
    LANDING_PAGE_VIEWED = "landing_page_viewed"
    CTA_CLICKED = "cta_clicked"
    FORM_STARTED = "form_started"
    FORM_SUBMITTED = "form_submitted"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    WHATSAPP_CLICKED = "whatsapp_clicked"
    SMS_CLICKED = "sms_clicked"
    MEETING_BOOKED = "meeting_booked"
    RESERVATION_CREATED = "reservation_created"
    SALE_CREATED = "sale_created"
    CAMPAIGN_STARTED = "campaign_started"
    CAMPAIGN_FINISHED = "campaign_finished"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"


class MarketingAutomationConditionOperator(str, enum.Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    COUNTRY = "country"
    LANGUAGE = "language"
    CAMPAIGN = "campaign"
    PROJECT = "project"
    PROPERTY = "property"
    AUDIENCE = "audience"
    SEGMENT = "segment"
    LEAD_SCORE = "lead_score"
    BUDGET = "budget"
    REVENUE = "revenue"
    RESERVATION = "reservation"
    SALE = "sale"


class MarketingAutomationActionType(str, enum.Enum):
    CREATE_TASK = "create_task"
    ASSIGN_OWNER = "assign_owner"
    ASSIGN_TEAM = "assign_team"
    SEND_EMAIL = "send_email"
    SEND_WHATSAPP = "send_whatsapp"
    SEND_SMS = "send_sms"
    CREATE_CRM_ACTIVITY = "create_crm_activity"
    CREATE_CRM_NOTE = "create_crm_note"
    CREATE_TIMELINE_EVENT = "create_timeline_event"
    MOVE_AUDIENCE = "move_audience"
    MOVE_SEGMENT = "move_segment"
    START_CAMPAIGN = "start_campaign"
    STOP_CAMPAIGN = "stop_campaign"
    WAIT = "wait"
    BRANCH = "branch"
    CALL_WEBHOOK = "call_webhook"
    UPDATE_LEAD_CONTEXT = "update_lead_context"
    NOTIFY_USER = "notify_user"
    NOTIFY_TEAM = "notify_team"


class MarketingAutomationDelayUnit(str, enum.Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    BUSINESS_DAYS = "business_days"
    SPECIFIC_DATE = "specific_date"


class MarketingAutomationExecutionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_CONNECTED = "not_connected"


class MarketingAutomationTemplateCategory(str, enum.Enum):
    NEW_LEAD = "new_lead"
    INVESTOR_LEAD = "investor_lead"
    BUYER_LEAD = "buyer_lead"
    BROKER_LEAD = "broker_lead"
    RESERVATION_FOLLOWUP = "reservation_followup"
    MEETING_REMINDER = "meeting_reminder"
    EVENT_REGISTRATION = "event_registration"
    NEWSLETTER_JOURNEY = "newsletter_journey"
    WELCOME_JOURNEY = "welcome_journey"
    CUSTOM = "custom"


class MarketingAutomationWorkflow(Base):
    __tablename__ = "marketing_automation_workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MarketingAutomationWorkflowStatus] = mapped_column(
        Enum(
            MarketingAutomationWorkflowStatus,
            native_enum=False,
            length=40,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=MarketingAutomationWorkflowStatus.DRAFT,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger_json: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    conditions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    actions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    journey_graph_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_journey: Mapped[bool] = mapped_column(nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    executions: Mapped[list[MarketingAutomationExecution]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    versions: Mapped[list[MarketingAutomationVersion]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class MarketingAutomationExecution(Base):
    __tablename__ = "marketing_automation_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("marketing_automation_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MarketingAutomationExecutionStatus] = mapped_column(
        Enum(MarketingAutomationExecutionStatus, native_enum=False, length=40),
        nullable=False,
        default=MarketingAutomationExecutionStatus.QUEUED,
    )
    trigger_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trigger_context_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    actions_executed_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    actions_skipped_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workflow: Mapped[MarketingAutomationWorkflow] = relationship(back_populates="executions")


class MarketingAutomationTemplate(Base):
    __tablename__ = "marketing_automation_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[MarketingAutomationTemplateCategory] = mapped_column(
        Enum(MarketingAutomationTemplateCategory, native_enum=False, length=40),
        nullable=False,
        default=MarketingAutomationTemplateCategory.CUSTOM,
    )
    trigger_json: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    conditions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    actions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    journey_graph_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    is_journey: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class MarketingAutomationVersion(Base):
    __tablename__ = "marketing_automation_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("marketing_automation_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workflow: Mapped[MarketingAutomationWorkflow] = relationship(back_populates="versions")
