"""Lead qualification, scoring, inventory interest, and follow-up models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class InvestmentObjective(str, enum.Enum):
    RENTAL_INCOME = "rental_income"
    CAPITAL_APPRECIATION = "capital_appreciation"
    PERSONAL_USE = "personal_use"
    DIVERSIFICATION = "diversification"
    CITIZENSHIP = "citizenship"
    DEVELOPMENT = "development"
    OTHER = "other"


class CashOrFinancing(str, enum.Enum):
    CASH = "cash"
    MORTGAGE = "mortgage"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class PurchaseTimeline(str, enum.Enum):
    IMMEDIATE = "immediate"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    TWELVE_PLUS = "12_plus"
    UNKNOWN = "unknown"


class RiskTolerance(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualificationStatus(str, enum.Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    QUALIFIED = "qualified"
    REQUIRES_MORE_INFORMATION = "requires_more_information"
    UNQUALIFIED = "unqualified"


class LeadInterestType(str, enum.Enum):
    MATCHED = "matched"
    SHORTLISTED = "shortlisted"
    FAVORITE = "favorite"
    REJECTED = "rejected"


class FollowUpType(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    WHATSAPP = "whatsapp"
    SITE_VISIT = "site_visit"
    OTHER = "other"


class FollowUpStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class LeadQualification(Base):
    """One active qualification record per lead (human-reviewed checklist)."""

    __tablename__ = "lead_qualifications"
    __table_args__ = (Index("ix_lead_qualifications_lead_id", "lead_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    investment_objective: Mapped[InvestmentObjective | None] = mapped_column(
        Enum(InvestmentObjective, native_enum=False, length=50),
        nullable=True,
    )
    investment_capacity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    cash_or_financing: Mapped[CashOrFinancing | None] = mapped_column(
        Enum(CashOrFinancing, native_enum=False, length=20),
        nullable=True,
    )
    expected_purchase_timeline: Mapped[PurchaseTimeline | None] = mapped_column(
        Enum(PurchaseTimeline, native_enum=False, length=20),
        nullable=True,
    )
    preferred_markets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preferred_projects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preferred_property_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    bedrooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bedrooms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    area_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_rental_yield: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    expected_roi: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    risk_tolerance: Mapped[RiskTolerance | None] = mapped_column(
        Enum(RiskTolerance, native_enum=False, length=20),
        nullable=True,
    )
    decision_makers: Mapped[str | None] = mapped_column(Text, nullable=True)
    accredited_investor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    required_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_concerns: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualification_status: Mapped[QualificationStatus] = mapped_column(
        Enum(QualificationStatus, native_enum=False, length=50),
        nullable=False,
        default=QualificationStatus.NEW,
    )
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qualified_by_id: Mapped[uuid.UUID | None] = mapped_column(
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


class LeadScore(Base):
    __tablename__ = "lead_scores"
    __table_args__ = (Index("ix_lead_scores_lead_id", "lead_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    computed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class LeadScoreComponent(Base):
    __tablename__ = "lead_score_components"
    __table_args__ = (Index("ix_lead_score_components_lead_score_id", "lead_score_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_score_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lead_scores.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_key: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("1.0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class LeadInventoryInterest(Base):
    __tablename__ = "lead_inventory_interests"
    __table_args__ = (
        Index("ix_lead_inventory_interests_lead_id", "lead_id"),
        Index("ix_lead_inventory_interests_asset_id", "inventory_asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    interest_type: Mapped[LeadInterestType] = mapped_column(
        Enum(LeadInterestType, native_enum=False, length=20),
        nullable=False,
    )
    match_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="SET NULL"),
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


class LeadFollowUp(Base):
    """Lightweight follow-up until Task/Calendar domain ships (5B4+).

    Calendar integration is NOT implemented — due_at is stored locally only.
    """

    __tablename__ = "lead_follow_ups"
    __table_args__ = (Index("ix_lead_follow_ups_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    follow_up_type: Mapped[FollowUpType] = mapped_column(
        Enum(FollowUpType, native_enum=False, length=20),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, native_enum=False, length=20),
        nullable=False,
        default=FollowUpStatus.PENDING,
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


class LeadTimeline(Base):
    """Domain timeline for lead qualification/score/assignment events."""

    __tablename__ = "lead_timeline"
    __table_args__ = (Index("ix_lead_timeline_lead_id", "lead_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
