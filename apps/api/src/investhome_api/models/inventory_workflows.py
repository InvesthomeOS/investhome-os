"""Ownership and assignment workflow models (Sprint 4B5 / 4B6)."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class TransferType(str, enum.Enum):
    INITIAL_OWNERSHIP = "initial_ownership"
    FULL_TRANSFER = "full_transfer"
    PARTIAL_TRANSFER = "partial_transfer"
    PERCENTAGE_CHANGE = "percentage_change"
    OWNER_ADDITION = "owner_addition"
    OWNER_REMOVAL = "owner_removal"
    OWNERSHIP_TYPE_CHANGE = "ownership_type_change"
    CORRECTION = "correction"
    OTHER = "other"


class TransferRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    STALE = "stale"
    WITHDRAWN = "withdrawn"


PENDING_TRANSFER_STATUSES = frozenset(
    {
        TransferRequestStatus.SUBMITTED,
        TransferRequestStatus.UNDER_REVIEW,
    }
)

SCHEDULED_TRANSFER_STATUSES = frozenset({TransferRequestStatus.APPROVED})


class OwnershipRecordStatus(str, enum.Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"


class OwnershipType(str, enum.Enum):
    LEGAL_OWNER = "legal_owner"
    BENEFICIAL_OWNER = "beneficial_owner"
    ECONOMIC_OWNER = "economic_owner"
    JOINT_OWNER = "joint_owner"
    TRUSTEE = "trustee"
    NOMINEE = "nominee"
    MANAGER = "manager"
    OTHER = "other"


LEGAL_OWNERSHIP_TYPES = frozenset({OwnershipType.LEGAL_OWNER, OwnershipType.JOINT_OWNER})


class AcquisitionMethod(str, enum.Enum):
    PURCHASE = "purchase"
    TRANSFER = "transfer"
    CORRECTION = "correction"
    INHERITANCE = "inheritance"
    GIFT = "gift"
    OTHER = "other"


class OwnershipSource(str, enum.Enum):
    TRANSFER = "transfer"
    CORRECTION = "correction"
    INITIAL = "initial"
    IMPORT = "import"
    OTHER = "other"


class TransferPartyRole(str, enum.Enum):
    CONTINUING_OWNER = "continuing_owner"
    INCOMING_OWNER = "incoming_owner"
    OUTGOING_OWNER = "outgoing_owner"


class OwnershipApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class OwnershipTransferRequest(Base):
    __tablename__ = "ownership_transfer_requests"
    __table_args__ = (
        Index("ix_ownership_transfer_requests_asset_id", "inventory_asset_id"),
        Index("ix_ownership_transfer_requests_status", "status"),
        Index("ix_ownership_transfer_requests_requester", "requested_by_user_id"),
        Index("ix_ownership_transfer_requests_effective_date", "effective_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    transfer_type: Mapped[TransferType] = mapped_column(
        Enum(TransferType, native_enum=False, length=50),
        nullable=False,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_ownership_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    assigned_approver_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[TransferRequestStatus] = mapped_column(
        Enum(TransferRequestStatus, native_enum=False, length=50),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryOwnership(Base):
    __tablename__ = "inventory_ownership"
    __table_args__ = (
        Index("ix_inventory_ownership_asset_id", "inventory_asset_id"),
        Index("ix_inventory_ownership_party_id", "party_id"),
        Index("ix_inventory_ownership_status", "status"),
        Index("ix_inventory_ownership_type", "ownership_type"),
        Index(
            "uq_inventory_ownership_active_party_type",
            "inventory_asset_id",
            "party_id",
            "ownership_type",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("investors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ownership_type: Mapped[OwnershipType] = mapped_column(
        Enum(OwnershipType, native_enum=False, length=50),
        nullable=False,
    )
    ownership_percentage: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[OwnershipRecordStatus] = mapped_column(
        Enum(OwnershipRecordStatus, native_enum=False, length=50),
        nullable=False,
    )
    acquisition_method: Mapped[AcquisitionMethod] = mapped_column(
        Enum(AcquisitionMethod, native_enum=False, length=50),
        nullable=False,
    )
    transfer_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[OwnershipSource] = mapped_column(
        Enum(OwnershipSource, native_enum=False, length=50),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ownership_transfer_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ownership_transfer_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    correction_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_ownership.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OwnershipTransferParty(Base):
    __tablename__ = "ownership_transfer_parties"
    __table_args__ = (Index("ix_ownership_transfer_parties_request_id", "ownership_transfer_request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ownership_transfer_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ownership_transfer_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("investors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ownership_type: Mapped[OwnershipType] = mapped_column(
        Enum(OwnershipType, native_enum=False, length=50),
        nullable=False,
    )
    previous_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    proposed_percentage: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    role: Mapped[TransferPartyRole] = mapped_column(
        Enum(TransferPartyRole, native_enum=False, length=50),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class OwnershipApprovalRecord(Base):
    __tablename__ = "ownership_approval_records"
    __table_args__ = (Index("ix_ownership_approval_records_request_id", "ownership_transfer_request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ownership_transfer_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ownership_transfer_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[OwnershipApprovalDecision] = mapped_column(
        Enum(OwnershipApprovalDecision, native_enum=False, length=50),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InventoryOwnershipEvent(Base):
    __tablename__ = "inventory_ownership_events"
    __table_args__ = (
        Index("ix_inventory_ownership_events_asset_id", "inventory_asset_id"),
        Index("ix_inventory_ownership_events_request_id", "ownership_transfer_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inventory_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    ownership_transfer_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ownership_transfer_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    inventory_ownership_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_ownership.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AssignmentType(str, enum.Enum):
    PARKING_FOR = "parking_for"
    STORAGE_FOR = "storage_for"


class AssignmentRecordStatus(str, enum.Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"


class AssignmentRequestType(str, enum.Enum):
    ASSIGN = "assign"
    REASSIGN = "reassign"
    UNASSIGN = "unassign"


class AssignmentRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    STALE = "stale"
    WITHDRAWN = "withdrawn"


PENDING_ASSIGNMENT_STATUSES = frozenset(
    {
        AssignmentRequestStatus.SUBMITTED,
        AssignmentRequestStatus.UNDER_REVIEW,
    }
)


class AssignmentApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class InventoryAssetAssignmentRequest(Base):
    __tablename__ = "inventory_asset_assignment_requests"
    __table_args__ = (
        Index("ix_assignment_requests_child_asset_id", "child_asset_id"),
        Index("ix_assignment_requests_parent_asset_id", "parent_asset_id"),
        Index("ix_assignment_requests_status", "status"),
        Index("ix_assignment_requests_requester", "requested_by_user_id"),
        Index("ix_assignment_requests_effective_date", "effective_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=True,
    )
    request_type: Mapped[AssignmentRequestType] = mapped_column(
        Enum(AssignmentRequestType, native_enum=False, length=50),
        nullable=False,
    )
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, native_enum=False, length=50),
        nullable=False,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_assignment_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    assignment_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    supporting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    assigned_approver_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[AssignmentRequestStatus] = mapped_column(
        Enum(AssignmentRequestStatus, native_enum=False, length=50),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryAssetAssignment(Base):
    __tablename__ = "inventory_asset_assignments"
    __table_args__ = (
        Index("ix_inventory_asset_assignments_child", "child_asset_id"),
        Index("ix_inventory_asset_assignments_parent", "parent_asset_id"),
        Index("ix_inventory_asset_assignments_status", "status"),
        Index(
            "uq_inventory_assignment_active_child",
            "child_asset_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[AssignmentRecordStatus] = mapped_column(
        Enum(AssignmentRecordStatus, native_enum=False, length=50),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    assignment_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    supporting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    assignment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_assignment_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
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
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryAssetAssignmentApproval(Base):
    __tablename__ = "inventory_asset_assignment_approvals"
    __table_args__ = (Index("ix_assignment_approval_records_request_id", "assignment_request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assignment_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_assignment_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[AssignmentApprovalDecision] = mapped_column(
        Enum(AssignmentApprovalDecision, native_enum=False, length=50),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InventoryAssetAssignmentEvent(Base):
    __tablename__ = "inventory_asset_assignment_events"
    __table_args__ = (
        Index("ix_inventory_assignment_events_child", "child_asset_id"),
        Index("ix_inventory_assignment_events_request_id", "assignment_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inventory_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_assignment_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    inventory_asset_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("inventory_asset_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
