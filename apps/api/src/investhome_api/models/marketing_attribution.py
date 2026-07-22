"""Multi-touch attribution models — touchpoints, journeys, models, rules, allocations, health."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class TouchType(str, enum.Enum):
    AD_CLICK = "ad_click"
    ORGANIC_VISIT = "organic_visit"
    LANDING_PAGE_VIEW = "landing_page_view"
    CTA_CLICK = "cta_click"
    FORM_START = "form_start"
    FORM_SUBMIT = "form_submit"
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    WHATSAPP_CLICK = "whatsapp_click"
    SMS_CLICK = "sms_click"
    PHONE_CALL = "phone_call"
    MEETING = "meeting"
    RESERVATION = "reservation"
    SALE = "sale"
    REFERRAL = "referral"
    BROKER = "broker"
    OFFLINE_EVENT = "offline_event"
    MANUAL_ENTRY = "manual_entry"
    OTHER = "other"


class TouchVerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"
    PARTIAL = "partial"


class JourneyStatus(str, enum.Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    BROKEN = "broken"
    UNKNOWN = "unknown"


class AttributionModelType(str, enum.Enum):
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    POSITION_BASED = "position_based"
    TIME_DECAY = "time_decay"
    DATA_DRIVEN = "data_driven"
    CUSTOM = "custom"
    OFFLINE = "offline"
    MANUAL = "manual"
    UNKNOWN = "unknown"
    PARTIAL = "partial"


class AttributionHealthSeverity(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class AttributionHealthIssueType(str, enum.Enum):
    BROKEN_JOURNEY = "broken_journey"
    MISSING_TOUCH = "missing_touch"
    DUPLICATE_TOUCH = "duplicate_touch"
    UNKNOWN_SOURCE = "unknown_source"
    INCOMPLETE_JOURNEY = "incomplete_journey"
    UNLINKED_TOUCH = "unlinked_touch"


class MarketingTouchpoint(Base):
    __tablename__ = "marketing_touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("crm_contacts.id", ondelete="SET NULL"))
    anonymous_visitor_id: Mapped[str | None] = mapped_column(String(255))
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"))
    channel_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"))
    landing_page_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="SET NULL"))
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="SET NULL"))
    conversion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_conversion_events.id", ondelete="SET NULL")
    )
    crm_timeline_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    sales_lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("leads.id", ondelete="SET NULL"))
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    sale_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    tracking_context_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_tracking_contexts.id", ondelete="SET NULL")
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_form_submissions.id", ondelete="SET NULL")
    )
    lead_context_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_contexts.id", ondelete="SET NULL")
    )
    touch_type: Mapped[TouchType] = mapped_column(
        Enum(TouchType, name="marketing_touch_type"), nullable=False
    )
    touch_order: Mapped[int | None] = mapped_column(Integer)
    touch_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    click_ids_json: Mapped[dict | None] = mapped_column(JSON)
    device_json: Mapped[dict | None] = mapped_column(JSON)
    country: Mapped[str | None] = mapped_column(String(2))
    verification_status: Mapped[TouchVerificationStatus] = mapped_column(
        Enum(TouchVerificationStatus, name="touch_verification_status"),
        default=TouchVerificationStatus.UNKNOWN,
        nullable=False,
    )
    source_entity_type: Mapped[str | None] = mapped_column(String(50))
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_marketing_touchpoints_contact_id", "contact_id"),
        Index("ix_marketing_touchpoints_lead_context_id", "lead_context_id"),
        Index("ix_marketing_touchpoints_touch_timestamp", "touch_timestamp"),
        Index("ix_marketing_touchpoints_tracking_context_id", "tracking_context_id"),
        Index("ix_marketing_touchpoints_source_entity", "source_entity_type", "source_entity_id", unique=True),
    )


class MarketingAttributionJourney(Base):
    __tablename__ = "marketing_attribution_journeys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("crm_contacts.id", ondelete="SET NULL"))
    marketing_lead_context_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_contexts.id", ondelete="SET NULL")
    )
    touchpoint_ids_json: Mapped[list | None] = mapped_column(JSON)
    journey_status: Mapped[JourneyStatus] = mapped_column(
        Enum(JourneyStatus, name="attribution_journey_status"),
        default=JourneyStatus.UNKNOWN,
        nullable=False,
    )
    conversion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_conversion_events.id", ondelete="SET NULL")
    )
    first_touch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_touch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    touch_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_marketing_attribution_journeys_contact_id", "contact_id"),
        Index("ix_marketing_attribution_journeys_lead_context_id", "marketing_lead_context_id"),
        Index("ix_marketing_attribution_journeys_status", "journey_status"),
    )


class MarketingAttributionModel(Base):
    __tablename__ = "marketing_attribution_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[AttributionModelType] = mapped_column(
        Enum(
            AttributionModelType,
            name="attribution_model_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    config_json: Mapped[dict | None] = mapped_column(JSON)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketingAttributionRule(Base):
    __tablename__ = "marketing_attribution_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions_json: Mapped[dict | None] = mapped_column(JSON)
    allocation_json: Mapped[dict | None] = mapped_column(JSON)
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_attribution_models.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketingAttributionAllocation(Base):
    __tablename__ = "marketing_attribution_allocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_attribution_journeys.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_attribution_models.id", ondelete="CASCADE"), nullable=False
    )
    touchpoint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_touchpoints.id", ondelete="CASCADE"), nullable=False
    )
    contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_marketing_attribution_allocations_journey_model", "journey_id", "model_id"),
        Index(
            "ix_marketing_attribution_allocations_unique",
            "journey_id",
            "model_id",
            "touchpoint_id",
            unique=True,
        ),
    )


class MarketingAttributionHealth(Base):
    __tablename__ = "marketing_attribution_health"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    issue_type: Mapped[AttributionHealthIssueType] = mapped_column(
        Enum(AttributionHealthIssueType, name="attribution_health_issue_type"), nullable=False
    )
    severity: Mapped[AttributionHealthSeverity] = mapped_column(
        Enum(AttributionHealthSeverity, name="attribution_health_severity"), nullable=False
    )
    journey_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_attribution_journeys.id", ondelete="CASCADE")
    )
    touchpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_touchpoints.id", ondelete="SET NULL")
    )
    message: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict | None] = mapped_column(JSON)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_marketing_attribution_health_severity", "severity"),
        Index("ix_marketing_attribution_health_journey_id", "journey_id"),
    )
