"""CRM Relationship Engine — polymorphic network between CRM and platform entities."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class CrmRelationshipEntityType(str, enum.Enum):
    CONTACT = "contact"
    COMPANY = "company"
    PROJECT = "project"
    PROPERTY = "property"
    OPPORTUNITY = "opportunity"
    INVESTMENT = "investment"
    TRANSACTION = "transaction"
    VENDOR = "vendor"
    INTERNAL_USER = "internal_user"
    EXTERNAL_ORGANIZATION = "external_organization"
    OTHER = "other"


class CrmRelationshipCategory(str, enum.Enum):
    ORGANIZATIONAL = "organizational"
    COMMERCIAL = "commercial"
    PERSONAL = "personal"
    REFERRAL = "referral"
    INVESTMENT = "investment"
    OPERATIONAL = "operational"
    OTHER = "other"


class CrmRelationshipStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"


class CrmRelationshipStrength(str, enum.Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    STRATEGIC = "strategic"


class CrmRelationshipDirection(str, enum.Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"
    BIDIRECTIONAL = "bidirectional"


class CrmRelationshipAlertType(str, enum.Enum):
    STALE = "stale"
    AT_RISK = "at_risk"
    SCORE_DROP = "score_drop"
    MISSING_FOLLOW_UP = "missing_follow_up"
    CONFLICT = "conflict"
    HIERARCHY_CYCLE = "hierarchy_cycle"
    DUPLICATE = "duplicate"
    OTHER = "other"


class CrmRelationshipAlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CrmDecisionMapRoleType(str, enum.Enum):
    DECISION_MAKER = "decision_maker"
    INFLUENCER = "influencer"
    CHAMPION = "champion"
    GATEKEEPER = "gatekeeper"
    END_USER = "end_user"
    BLOCKER = "blocker"
    OTHER = "other"


class CrmReferralStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONVERTED = "converted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CrmRelationshipReviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class CrmRelationship(Base):
    __tablename__ = "crm_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            "relationship_type",
            name="uq_crm_relationship_endpoints_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_entity_type: Mapped[CrmRelationshipEntityType] = mapped_column(
        Enum(CrmRelationshipEntityType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_entity_type: Mapped[CrmRelationshipEntityType] = mapped_column(
        Enum(CrmRelationshipEntityType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
    reciprocal_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    category: Mapped[CrmRelationshipCategory] = mapped_column(
        Enum(CrmRelationshipCategory, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipCategory.OTHER,
    )
    status: Mapped[CrmRelationshipStatus] = mapped_column(
        Enum(CrmRelationshipStatus, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipStatus.ACTIVE,
    )
    strength: Mapped[CrmRelationshipStrength] = mapped_column(
        Enum(CrmRelationshipStrength, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipStrength.MODERATE,
    )
    direction: Mapped[CrmRelationshipDirection] = mapped_column(
        Enum(CrmRelationshipDirection, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipDirection.OUTBOUND,
    )
    relationship_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    influence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    business_value_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    score_snapshots: Mapped[list[CrmRelationshipScoreSnapshot]] = relationship(
        back_populates="relationship",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list[CrmRelationshipAlert]] = relationship(
        back_populates="relationship",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list[CrmRelationshipReview]] = relationship(
        back_populates="relationship",
        cascade="all, delete-orphan",
    )


class CrmRelationshipTypeConfig(Base):
    __tablename__ = "crm_relationship_type_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    reciprocal_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    category: Mapped[CrmRelationshipCategory] = mapped_column(
        Enum(CrmRelationshipCategory, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipCategory.OTHER,
    )
    is_directional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    reciprocal_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prevents_hierarchy_cycle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CrmRelationshipScoreSnapshot(Base):
    __tablename__ = "crm_relationship_score_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_relationships.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    influence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    business_value_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    relationship: Mapped[CrmRelationship] = relationship(back_populates="score_snapshots")


class CrmRelationshipAlert(Base):
    __tablename__ = "crm_relationship_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crm_relationships.id", ondelete="CASCADE"),
        nullable=True,
    )
    entity_type: Mapped[CrmRelationshipEntityType | None] = mapped_column(
        Enum(CrmRelationshipEntityType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    alert_type: Mapped[CrmRelationshipAlertType] = mapped_column(
        Enum(CrmRelationshipAlertType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CrmRelationshipAlertStatus] = mapped_column(
        Enum(CrmRelationshipAlertStatus, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipAlertStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    relationship: Mapped[CrmRelationship | None] = relationship(back_populates="alerts")


class CrmDecisionMapRole(Base):
    __tablename__ = "crm_decision_map_roles"
    __table_args__ = (
        UniqueConstraint("company_id", "contact_id", "role_type", name="uq_crm_decision_map_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_type: Mapped[CrmDecisionMapRoleType] = mapped_column(
        Enum(CrmDecisionMapRoleType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    influence_level: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CrmReferral(Base):
    __tablename__ = "crm_referrals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    referrer_entity_type: Mapped[CrmRelationshipEntityType] = mapped_column(
        Enum(CrmRelationshipEntityType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    referrer_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    referred_entity_type: Mapped[CrmRelationshipEntityType] = mapped_column(
        Enum(CrmRelationshipEntityType, native_enum=False, length=30, values_callable=_enum_values),
        nullable=False,
    )
    referred_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crm_relationships.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CrmReferralStatus] = mapped_column(
        Enum(CrmReferralStatus, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmReferralStatus.PENDING,
    )
    compensation_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    compensation_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    compensation_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CrmRelationshipReview(Base):
    __tablename__ = "crm_relationship_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_relationships.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[CrmRelationshipReviewStatus] = mapped_column(
        Enum(CrmRelationshipReviewStatus, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        default=CrmRelationshipReviewStatus.SCHEDULED,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scores_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    relationship: Mapped[CrmRelationship] = relationship(back_populates="reviews")


class CrmRelationshipSavedView(Base):
    __tablename__ = "crm_relationship_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
