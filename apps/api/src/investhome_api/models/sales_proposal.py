"""Sales proposal engine models.

Multi-currency architecture (ADR): each proposal carries a single authoritative
``currency``. All ``SalesProposalItem`` rows MUST match that currency — mixed
currency within one proposal is prohibited. Cross-currency deals require separate
proposals per currency.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ProposalStatus(str, enum.Enum):
    DRAFT = "draft"
    INTERNAL_REVIEW = "internal_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


TERMINAL_PROPOSAL_STATUSES = frozenset(
    {
        ProposalStatus.ACCEPTED,
        ProposalStatus.REJECTED,
        ProposalStatus.EXPIRED,
        ProposalStatus.SUPERSEDED,
        ProposalStatus.ARCHIVED,
    }
)

EDITABLE_PROPOSAL_STATUSES = frozenset({ProposalStatus.DRAFT, ProposalStatus.REVISION_REQUESTED})


class ProposalApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ProposalRecipientType(str, enum.Enum):
    PRIMARY = "primary"
    CC = "cc"
    BROKER = "broker"
    ADVISOR = "advisor"
    OTHER = "other"


class ProposalActivityType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    RESTORED = "restored"
    VERSION_CREATED = "version_created"
    STALE_DETECTED = "stale_detected"
    PRICING_REFRESHED = "pricing_refreshed"


class SalesProposal(Base):
    __tablename__ = "sales_proposals"
    __table_args__ = (
        Index("ix_sales_proposals_opportunity_id", "opportunity_id"),
        Index("ix_sales_proposals_status", "status"),
        Index("ix_sales_proposals_proposal_number", "proposal_number", unique=True),
        Index("ix_sales_proposals_party_id", "party_id"),
        Index("ix_sales_proposals_assigned_sales_user_id", "assigned_sales_user_id"),
        Index("ix_sales_proposals_primary_project_id", "primary_project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    proposal_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, native_enum=False, length=30),
        nullable=False,
        default=ProposalStatus.DRAFT,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    primary_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_sales_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class SalesProposalVersion(Base):
    """Immutable snapshot chain — prior versions are never overwritten."""

    __tablename__ = "sales_proposal_versions"
    __table_args__ = (
        UniqueConstraint("proposal_id", "version_number", name="uq_proposal_version_number"),
        Index("ix_sales_proposal_versions_proposal_id", "proposal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_shortlist_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_shortlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pricing_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    terms_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branding_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SalesProposalItem(Base):
    __tablename__ = "sales_proposal_items"
    __table_args__ = (
        Index("ix_sales_proposal_items_version_id", "proposal_version_id"),
        Index("ix_sales_proposal_items_asset_id", "inventory_asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposal_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_price_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_prices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    displayed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    promotional_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_rent: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    selected_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    selected_media: Mapped[list | None] = mapped_column(JSON, nullable=True)
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


class SalesProposalApproval(Base):
    __tablename__ = "sales_proposal_approvals"
    __table_args__ = (Index("ix_sales_proposal_approvals_proposal_id", "proposal_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposal_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision: Mapped[ProposalApprovalDecision] = mapped_column(
        Enum(ProposalApprovalDecision, native_enum=False, length=30),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SalesProposalRecipient(Base):
    __tablename__ = "sales_proposal_recipients"
    __table_args__ = (
        Index("ix_sales_proposal_recipients_proposal_id", "proposal_id"),
        CheckConstraint(
            "recipient_type != 'primary' OR is_primary = true",
            name="ck_proposal_recipient_primary_flag",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    recipient_type: Mapped[ProposalRecipientType] = mapped_column(
        Enum(ProposalRecipientType, native_enum=False, length=20),
        nullable=False,
        default=ProposalRecipientType.PRIMARY,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SalesProposalActivity(Base):
    __tablename__ = "sales_proposal_activities"
    __table_args__ = (Index("ix_sales_proposal_activities_proposal_id", "proposal_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_type: Mapped[ProposalActivityType] = mapped_column(
        Enum(ProposalActivityType, native_enum=False, length=30),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
