"""Sales contract readiness domain models."""

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
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ReadinessCaseStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    READY_FOR_CONTRACT = "ready_for_contract"
    CONTRACT_PREPARATION = "contract_preparation"
    SIGNATURE_PENDING = "signature_pending"
    CONTRACT_SIGNED = "contract_signed"
    READY_FOR_CLOSING_HANDOFF = "ready_for_closing_handoff"
    HANDED_OFF = "handed_off"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


TERMINAL_READINESS_STATUSES = frozenset(
    {
        ReadinessCaseStatus.HANDED_OFF,
        ReadinessCaseStatus.CANCELLED,
        ReadinessCaseStatus.ARCHIVED,
    }
)

ACTIVE_READINESS_STATUSES = frozenset(
    {
        ReadinessCaseStatus.NOT_STARTED,
        ReadinessCaseStatus.IN_PROGRESS,
        ReadinessCaseStatus.BLOCKED,
        ReadinessCaseStatus.READY_FOR_CONTRACT,
        ReadinessCaseStatus.CONTRACT_PREPARATION,
        ReadinessCaseStatus.SIGNATURE_PENDING,
        ReadinessCaseStatus.CONTRACT_SIGNED,
        ReadinessCaseStatus.READY_FOR_CLOSING_HANDOFF,
    }
)


class ReadinessRequirementType(str, enum.Enum):
    RESERVATION_APPROVED = "reservation_approved"
    DEPOSIT_DUE = "deposit_due"
    DEPOSIT_RECEIVED = "deposit_received"
    PARTY_IDENTITY = "party_identity"
    PARTY_ORGANIZATION_DOCUMENTS = "party_organization_documents"
    KYC_DOCUMENT = "kyc_document"
    PROOF_OF_FUNDS = "proof_of_funds"
    FINANCING_CONFIRMATION = "financing_confirmation"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PURCHASE_AGREEMENT = "purchase_agreement"
    SUBSCRIPTION_AGREEMENT = "subscription_agreement"
    OPERATING_AGREEMENT = "operating_agreement"
    DISCLOSURE = "disclosure"
    PAYMENT_SCHEDULE = "payment_schedule"
    TAX_FORM = "tax_form"
    LEGAL_REVIEW = "legal_review"
    SIGNATURE_REQUIRED = "signature_required"
    SIGNATURE_COMPLETED = "signature_completed"
    CLOSING_DATE_CONFIRMED = "closing_date_confirmed"
    OTHER = "other"


class ReadinessRequirementStatus(str, enum.Enum):
    MISSING = "missing"
    PENDING = "pending"
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    WAIVED = "waived"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"


BLOCKING_REQUIREMENT_STATUSES = frozenset(
    {
        ReadinessRequirementStatus.MISSING,
        ReadinessRequirementStatus.REJECTED,
        ReadinessRequirementStatus.EXPIRED,
    }
)

SATISFIED_REQUIREMENT_STATUSES = frozenset(
    {
        ReadinessRequirementStatus.VERIFIED,
        ReadinessRequirementStatus.WAIVED,
        ReadinessRequirementStatus.NOT_APPLICABLE,
    }
)


class ReadinessTemplateGroup(str, enum.Enum):
    RESERVATION = "reservation"
    DEPOSIT = "deposit"
    PARTY = "party"
    DOCUMENTS = "documents"
    CONTRACT = "contract"
    HANDOFF = "handoff"


class ReadinessSourceEntityType(str, enum.Enum):
    INVENTORY_RESERVATION = "inventory_reservation"
    FINANCE_TRANSACTION = "finance_transaction"
    SALES_PROPOSAL = "sales_proposal"
    DOCUMENT = "document"
    LEAD = "lead"
    INVESTOR = "investor"
    INVENTORY_ASSET = "inventory_asset"
    OPPORTUNITY = "opportunity"
    OTHER = "other"


class SalesReadinessCase(Base):
    __tablename__ = "sales_readiness_cases"
    __table_args__ = (
        Index("ix_sales_readiness_cases_opportunity_id", "opportunity_id"),
        Index("ix_sales_readiness_cases_status", "status"),
        Index("ix_sales_readiness_cases_inventory_asset_id", "inventory_asset_id"),
        Index("ix_sales_readiness_cases_assigned_sales_user_id", "assigned_sales_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
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
    inventory_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("sales_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ReadinessCaseStatus] = mapped_column(
        Enum(ReadinessCaseStatus, native_enum=False, length=40),
        nullable=False,
        default=ReadinessCaseStatus.NOT_STARTED,
    )
    readiness_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_contract_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_closing_handoff_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_sales_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_legal_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_finance_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    blocker_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    handoff_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff_requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    handoff_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff_approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    handoff_return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    signed_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
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


class SalesReadinessRequirement(Base):
    __tablename__ = "sales_readiness_requirements"
    __table_args__ = (
        Index("ix_sales_readiness_requirements_case_id", "readiness_case_id"),
        Index("ix_sales_readiness_requirements_type", "requirement_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    readiness_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_readiness_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirement_type: Mapped[ReadinessRequirementType] = mapped_column(
        Enum(ReadinessRequirementType, native_enum=False, length=50),
        nullable=False,
    )
    template_group: Mapped[ReadinessTemplateGroup | None] = mapped_column(
        Enum(ReadinessTemplateGroup, native_enum=False, length=30),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReadinessRequirementStatus] = mapped_column(
        Enum(ReadinessRequirementStatus, native_enum=False, length=30),
        nullable=False,
        default=ReadinessRequirementStatus.MISSING,
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_entity_type: Mapped[ReadinessSourceEntityType | None] = mapped_column(
        Enum(ReadinessSourceEntityType, native_enum=False, length=40),
        nullable=True,
    )
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    waiver_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    waiver_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    waiver_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_event: Mapped[str | None] = mapped_column(String(80), nullable=True)
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


class SalesReadinessStatusHistory(Base):
    __tablename__ = "sales_readiness_status_history"
    __table_args__ = (Index("ix_sales_readiness_status_history_case_id", "readiness_case_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    readiness_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_readiness_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SalesReadinessTemplate(Base):
    __tablename__ = "sales_readiness_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    buyer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    party_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sale_structure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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


class SalesReadinessTemplateItem(Base):
    __tablename__ = "sales_readiness_template_items"
    __table_args__ = (Index("ix_sales_readiness_template_items_template_id", "template_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sales_readiness_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_group: Mapped[ReadinessTemplateGroup] = mapped_column(
        Enum(ReadinessTemplateGroup, native_enum=False, length=30),
        nullable=False,
    )
    requirement_type: Mapped[ReadinessRequirementType] = mapped_column(
        Enum(ReadinessRequirementType, native_enum=False, length=50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
