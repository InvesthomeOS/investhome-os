"""Project cost tracking — vendors, commitments, bills, payments, retainage (Sprint 10A4B).

Actual cost recognition rule (documented):
  Actual cost = sum of posted vendor bill line ``net_amount + tax_amount``.
  Draft / in-review / approved-but-unposted bills do not create actual cost.

Committed cost recognition rule:
  Committed cost = sum of commitment ``current_committed_amount`` for statuses
  APPROVED, EXECUTED, ACTIVE, COMPLETED.

Do not double-count legacy ``ProjectBudget.paid_amount`` with normalized actuals.
"""

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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class VendorType(str, enum.Enum):
    GENERAL_CONTRACTOR = "general_contractor"
    SUBCONTRACTOR = "subcontractor"
    SUPPLIER = "supplier"
    CONSULTANT = "consultant"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    ATTORNEY = "attorney"
    BROKER = "broker"
    INSURANCE = "insurance"
    LENDER = "lender"
    UTILITY = "utility"
    GOVERNMENT = "government"
    OTHER = "other"


class VendorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_HOLD = "on_hold"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class ProjectVendorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ProjectCommitmentType(str, enum.Enum):
    CONTRACT = "contract"
    PURCHASE_ORDER = "purchase_order"
    SUBCONTRACT = "subcontract"
    PROFESSIONAL_SERVICES = "professional_services"
    CONSULTING_AGREEMENT = "consulting_agreement"
    LETTER_OF_INTENT = "letter_of_intent"
    OTHER = "other"


class ProjectCommitmentStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    EXECUTED = "executed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ChangeOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VendorBillStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"
    ARCHIVED = "archived"


class ProjectPaymentStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    VOID = "void"


class ProjectPaymentMethod(str, enum.Enum):
    ACH = "ach"
    WIRE = "wire"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INTERNAL_TRANSFER = "internal_transfer"
    OTHER = "other"


class RetainageReleaseStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    POSTED = "posted"
    REJECTED = "rejected"
    VOID = "void"


COMMITTED_COST_STATUSES = frozenset(
    {
        ProjectCommitmentStatus.APPROVED,
        ProjectCommitmentStatus.EXECUTED,
        ProjectCommitmentStatus.ACTIVE,
        ProjectCommitmentStatus.COMPLETED,
    }
)

POSTED_BILL_STATUSES = frozenset(
    {
        VendorBillStatus.POSTED,
        VendorBillStatus.PARTIALLY_PAID,
        VendorBillStatus.PAID,
    }
)


class Vendor(Base):
    """Company-scoped vendor master (finance AP — not CRM vendor profiles)."""

    __tablename__ = "vendors"
    __table_args__ = (
        UniqueConstraint("company_id", "vendor_code", name="uq_vendors_company_code"),
        Index("ix_vendors_company_id", "company_id"),
        Index("ix_vendors_status", "status"),
        Index("ix_vendors_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_code: Mapped[str] = mapped_column(String(50), nullable=False)
    tax_id_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_type: Mapped[VendorType] = mapped_column(
        Enum(VendorType, native_enum=False, length=50),
        nullable=False,
        default=VendorType.OTHER,
    )
    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus, native_enum=False, length=30),
        nullable=False,
        default=VendorStatus.ACTIVE,
    )
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    insurance_expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectVendor(Base):
    __tablename__ = "project_vendors"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "vendor_id", "role", name="uq_project_vendors_project_vendor_role"
        ),
        Index("ix_project_vendors_project_id", "project_id"),
        Index("ix_project_vendors_vendor_id", "vendor_id"),
        Index("ix_project_vendors_company_id", "company_id"),
        Index("ix_project_vendors_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="vendor")
    status: Mapped[ProjectVendorStatus] = mapped_column(
        Enum(ProjectVendorStatus, native_enum=False, length=30),
        nullable=False,
        default=ProjectVendorStatus.ACTIVE,
    )
    primary_contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectCommitment(Base):
    __tablename__ = "project_commitments"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "commitment_number", name="uq_project_commitments_project_number"
        ),
        Index("ix_project_commitments_project_id", "project_id"),
        Index("ix_project_commitments_vendor_id", "vendor_id"),
        Index("ix_project_commitments_company_id", "company_id"),
        Index("ix_project_commitments_status", "status"),
        Index("ix_project_commitments_budget_version_id", "budget_version_id"),
        Index("ix_project_commitments_commitment_type", "commitment_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    budget_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_budget_versions.id", ondelete="SET NULL"), nullable=True
    )
    commitment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    commitment_type: Mapped[ProjectCommitmentType] = mapped_column(
        Enum(ProjectCommitmentType, native_enum=False, length=50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectCommitmentStatus] = mapped_column(
        Enum(ProjectCommitmentStatus, native_enum=False, length=30),
        nullable=False,
        default=ProjectCommitmentStatus.DRAFT,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_change_orders: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    current_committed_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    invoiced_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retained_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    remaining_commitment: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    executed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retainage_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    billing_contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    budget_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectCommitmentLine(Base):
    __tablename__ = "project_commitment_lines"
    __table_args__ = (
        UniqueConstraint(
            "commitment_id",
            "line_number",
            name="uq_project_commitment_lines_commitment_line_number",
        ),
        Index("ix_project_commitment_lines_project_id", "project_id"),
        Index("ix_project_commitment_lines_commitment_id", "commitment_id"),
        Index("ix_project_commitment_lines_budget_line_id", "budget_line_id"),
        Index("ix_project_commitment_lines_category_id", "category_id"),
        Index("ix_project_commitment_lines_cost_code_id", "cost_code_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_commitments.id", ondelete="CASCADE"), nullable=False
    )
    budget_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_lines.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    cost_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True
    )
    line_number: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_change_orders: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    invoiced_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retained_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectCommitmentChangeOrder(Base):
    __tablename__ = "project_commitment_change_orders"
    __table_args__ = (
        UniqueConstraint(
            "commitment_id",
            "change_order_number",
            name="uq_project_commitment_cos_commitment_number",
        ),
        Index("ix_project_commitment_cos_project_id", "project_id"),
        Index("ix_project_commitment_cos_commitment_id", "commitment_id"),
        Index("ix_project_commitment_cos_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_commitments.id", ondelete="CASCADE"), nullable=False
    )
    change_order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ChangeOrderStatus] = mapped_column(
        Enum(ChangeOrderStatus, native_enum=False, length=30),
        nullable=False,
        default=ChangeOrderStatus.DRAFT,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectCommitmentChangeOrderLine(Base):
    __tablename__ = "project_commitment_change_order_lines"
    __table_args__ = (
        Index("ix_project_commitment_co_lines_change_order_id", "change_order_id"),
        Index("ix_project_commitment_co_lines_commitment_line_id", "commitment_line_id"),
        Index("ix_project_commitment_co_lines_budget_line_id", "budget_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    change_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_commitment_change_orders.id", ondelete="CASCADE"), nullable=False
    )
    commitment_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_commitment_lines.id", ondelete="CASCADE"), nullable=False
    )
    budget_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_lines.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProjectVendorBill(Base):
    """Vendor bill (AP invoice). Totals are recalculated centrally from lines.

    Bill formulas:
      subtotal = sum(line.gross_amount)
      retainage_amount = sum(line.retainage_amount)
      tax_amount = sum(line.tax_amount)
      total_amount = subtotal + tax_amount
      approved_amount = total_amount - retainage_amount
      balance_due = approved_amount - paid_amount
    """

    __tablename__ = "project_vendor_bills"
    __table_args__ = (
        UniqueConstraint("project_id", "bill_number", name="uq_project_vendor_bills_project_number"),
        UniqueConstraint(
            "vendor_id",
            "vendor_invoice_number",
            name="uq_project_vendor_bills_vendor_invoice",
        ),
        Index("ix_project_vendor_bills_project_id", "project_id"),
        Index("ix_project_vendor_bills_vendor_id", "vendor_id"),
        Index("ix_project_vendor_bills_commitment_id", "commitment_id"),
        Index("ix_project_vendor_bills_company_id", "company_id"),
        Index("ix_project_vendor_bills_status", "status"),
        Index("ix_project_vendor_bills_due_date", "due_date"),
        Index("ix_project_vendor_bills_invoice_date", "invoice_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_commitments.id", ondelete="SET NULL"), nullable=True
    )
    bill_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[VendorBillStatus] = mapped_column(
        Enum(VendorBillStatus, native_enum=False, length=30),
        nullable=False,
        default=VendorBillStatus.DRAFT,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retainage_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    approved_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    balance_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectVendorBillLine(Base):
    """Bill line. Recognized actual cost (when bill is posted): net_amount + tax_amount."""

    __tablename__ = "project_vendor_bill_lines"
    __table_args__ = (
        UniqueConstraint(
            "vendor_bill_id",
            "line_number",
            name="uq_project_vendor_bill_lines_bill_line_number",
        ),
        Index("ix_project_vendor_bill_lines_project_id", "project_id"),
        Index("ix_project_vendor_bill_lines_vendor_bill_id", "vendor_bill_id"),
        Index("ix_project_vendor_bill_lines_commitment_id", "commitment_id"),
        Index("ix_project_vendor_bill_lines_commitment_line_id", "commitment_line_id"),
        Index("ix_project_vendor_bill_lines_budget_line_id", "budget_line_id"),
        Index("ix_project_vendor_bill_lines_category_id", "category_id"),
        Index("ix_project_vendor_bill_lines_cost_code_id", "cost_code_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_vendor_bills.id", ondelete="CASCADE"), nullable=False
    )
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_commitments.id", ondelete="SET NULL"), nullable=True
    )
    commitment_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_commitment_lines.id", ondelete="SET NULL"), nullable=True
    )
    budget_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_lines.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    cost_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True
    )
    line_number: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    retainage_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    previously_billed_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    current_billed_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    stored_materials_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectPayment(Base):
    __tablename__ = "project_payments"
    __table_args__ = (
        UniqueConstraint("project_id", "payment_number", name="uq_project_payments_project_number"),
        Index("ix_project_payments_project_id", "project_id"),
        Index("ix_project_payments_vendor_id", "vendor_id"),
        Index("ix_project_payments_company_id", "company_id"),
        Index("ix_project_payments_status", "status"),
        Index("ix_project_payments_payment_date", "payment_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ProjectPaymentStatus] = mapped_column(
        Enum(ProjectPaymentStatus, native_enum=False, length=30),
        nullable=False,
        default=ProjectPaymentStatus.DRAFT,
    )
    payment_method: Mapped[ProjectPaymentMethod] = mapped_column(
        Enum(ProjectPaymentMethod, native_enum=False, length=30),
        nullable=False,
        default=ProjectPaymentMethod.OTHER,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectPaymentAllocation(Base):
    __tablename__ = "project_payment_allocations"
    __table_args__ = (
        Index("ix_project_payment_allocations_payment_id", "payment_id"),
        Index("ix_project_payment_allocations_vendor_bill_id", "vendor_bill_id"),
        Index("ix_project_payment_allocations_project_id", "project_id"),
        Index("ix_project_payment_allocations_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_payments.id", ondelete="CASCADE"), nullable=False
    )
    vendor_bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_vendor_bills.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    retainage_release_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ProjectRetainageRelease(Base):
    __tablename__ = "project_retainage_releases"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "release_number", name="uq_project_retainage_releases_project_number"
        ),
        Index("ix_project_retainage_releases_project_id", "project_id"),
        Index("ix_project_retainage_releases_vendor_id", "vendor_id"),
        Index("ix_project_retainage_releases_commitment_id", "commitment_id"),
        Index("ix_project_retainage_releases_vendor_bill_id", "vendor_bill_id"),
        Index("ix_project_retainage_releases_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False
    )
    commitment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_commitments.id", ondelete="RESTRICT"), nullable=False
    )
    vendor_bill_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_vendor_bills.id", ondelete="SET NULL"), nullable=True
    )
    release_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[RetainageReleaseStatus] = mapped_column(
        Enum(RetainageReleaseStatus, native_enum=False, length=30),
        nullable=False,
        default=RetainageReleaseStatus.DRAFT,
    )
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
