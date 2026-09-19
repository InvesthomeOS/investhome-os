"""Sales opportunity domain models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class OpportunityStage(str, enum.Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    INVENTORY_MATCHING = "inventory_matching"
    PROPOSAL_PREPARATION = "proposal_preparation"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    SOFT_HOLD = "soft_hold"
    RESERVATION = "reservation"
    DEPOSIT_PENDING = "deposit_pending"
    CONTRACT = "contract"
    CLOSING_HANDOFF = "closing_handoff"
    WON = "won"
    LOST = "lost"
    DORMANT = "dormant"
    CANCELLED = "cancelled"


CLOSED_OPPORTUNITY_STAGES = frozenset(
    {
        OpportunityStage.WON,
        OpportunityStage.LOST,
        OpportunityStage.DORMANT,
        OpportunityStage.CANCELLED,
    }
)


class OpportunityNextAction(str, enum.Enum):
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SITE_VISIT = "site_visit"
    PROPOSAL = "proposal"
    RESERVATION_FOLLOW_UP = "reservation_follow_up"
    DEPOSIT_FOLLOW_UP = "deposit_follow_up"
    CONTRACT_FOLLOW_UP = "contract_follow_up"
    CLOSING_FOLLOW_UP = "closing_follow_up"


class OpportunityLossReason(str, enum.Enum):
    BUDGET = "budget"
    FINANCING = "financing"
    COMPETITOR = "competitor"
    NO_RESPONSE = "no_response"
    TIMELINE = "timeline"
    LOCATION = "location"
    INVENTORY = "inventory"
    INTERNAL = "internal"
    OTHER = "other"


class OpportunityPartyType(str, enum.Enum):
    LEAD = "lead"
    INVESTOR = "investor"
    CRM_CONTACT = "crm_contact"


class OpportunityPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SalesOpportunity(Base):
    __tablename__ = "sales_opportunities"
    __table_args__ = (
        Index("ix_sales_opportunities_opportunity_code", "opportunity_code", unique=True),
        Index("ix_sales_opportunities_stage", "stage"),
        Index("ix_sales_opportunities_lead_id", "lead_id"),
        Index("ix_sales_opportunities_crm_contact_id", "crm_contact_id"),
        Index("ix_sales_opportunities_party_id", "party_id"),
        Index("ix_sales_opportunities_assigned_sales_user_id", "assigned_sales_user_id"),
        Index("ix_sales_opportunities_reservation_id", "reservation_id"),
        Index("ix_sales_opportunities_archived_at", "archived_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    crm_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    party_type: Mapped[OpportunityPartyType] = mapped_column(
        Enum(OpportunityPartyType, native_enum=False, length=20),
        nullable=False,
    )
    assigned_sales_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[OpportunityStage] = mapped_column(
        Enum(OpportunityStage, native_enum=False, length=50),
        nullable=False,
        default=OpportunityStage.NEW,
    )
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    priority: Mapped[OpportunityPriority] = mapped_column(
        Enum(OpportunityPriority, native_enum=False, length=20),
        nullable=False,
        default=OpportunityPriority.MEDIUM,
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_risks: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    next_action: Mapped[OpportunityNextAction | None] = mapped_column(
        Enum(OpportunityNextAction, native_enum=False, length=50),
        nullable=True,
    )
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    loss_reason: Mapped[OpportunityLossReason | None] = mapped_column(
        Enum(OpportunityLossReason, native_enum=False, length=50),
        nullable=True,
    )
    loss_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dormant_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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


class OpportunityTimeline(Base):
    __tablename__ = "opportunity_timeline"
    __table_args__ = (Index("ix_opportunity_timeline_opportunity_id", "opportunity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    from_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OpportunityInventory(Base):
    __tablename__ = "opportunity_inventory"
    __table_args__ = (
        Index("ix_opportunity_inventory_opportunity_id", "opportunity_id"),
        Index("ix_opportunity_inventory_asset_id", "inventory_asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shortlisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OpportunityProject(Base):
    __tablename__ = "opportunity_projects"
    __table_args__ = (
        Index("ix_opportunity_projects_opportunity_id", "opportunity_id"),
        Index("ix_opportunity_projects_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OpportunityProbabilityHistory(Base):
    __tablename__ = "opportunity_probability_history"
    __table_args__ = (Index("ix_opportunity_probability_history_opportunity_id", "opportunity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_probability: Mapped[int] = mapped_column(Integer, nullable=False)
    new_probability: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
