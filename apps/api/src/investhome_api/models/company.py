"""Managed company entities and related records."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from investhome_api.models.branch import Branch

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class CompanyEntityType(str, enum.Enum):
    CORPORATION = "corporation"
    LLC = "llc"
    LP = "lp"
    LLP = "llp"
    HOLDING = "holding"
    TRUST = "trust"
    BRANCH = "branch"
    SUBSIDIARY = "subsidiary"
    JOINT_VENTURE = "joint_venture"
    FOUNDATION = "foundation"
    NON_PROFIT = "non_profit"
    OTHER = "other"


class CompanyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CompanyAddressType(str, enum.Enum):
    REGISTERED = "registered"
    HEAD_OFFICE = "head_office"
    MAILING = "mailing"
    BILLING = "billing"
    WAREHOUSE = "warehouse"
    OTHER = "other"


class CompanyContactRole(str, enum.Enum):
    CEO = "ceo"
    MANAGING_DIRECTOR = "managing_director"
    LEGAL = "legal"
    FINANCE = "finance"
    HR = "hr"
    OPERATIONS = "operations"
    EMERGENCY = "emergency"


class CompanyRelationshipType(str, enum.Enum):
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    BRANCH = "branch"
    PARTNER = "partner"
    JOINT_VENTURE = "joint_venture"
    OTHER = "other"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    logo_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, default=CompanyEntityType.OTHER.value)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=CompanyStatus.DRAFT.value)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    branch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    addresses: Mapped[list[CompanyAddress]] = relationship(back_populates="company", cascade="all, delete-orphan")
    contacts: Mapped[list[CompanyContact]] = relationship(back_populates="company", cascade="all, delete-orphan")
    bank_accounts: Mapped[list[CompanyBankAccount]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    documents: Mapped[list[CompanyDocument]] = relationship(back_populates="company", cascade="all, delete-orphan")
    relationships_from: Mapped[list[CompanyRelationship]] = relationship(
        back_populates="company",
        foreign_keys="CompanyRelationship.company_id",
        cascade="all, delete-orphan",
    )
    branches: Mapped[list["Branch"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class CompanyAddress(Base):
    __tablename__ = "company_addresses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    address_type: Mapped[str] = mapped_column(String(30), nullable=False, default=CompanyAddressType.OTHER.value)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="addresses")


class CompanyContact(Base):
    __tablename__ = "company_contacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default=CompanyContactRole.OPERATIONS.value)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_signatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="contacts")


class CompanyBankAccount(Base):
    __tablename__ = "company_bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(64), nullable=True)
    routing_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="bank_accounts")


class CompanyDocument(Base):
    __tablename__ = "company_documents"
    __table_args__ = (UniqueConstraint("company_id", "document_id", name="uq_company_documents_company_doc"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped[Company] = relationship(back_populates="documents")


class CompanyRelationship(Base):
    __tablename__ = "company_relationships"
    __table_args__ = (
        UniqueConstraint("company_id", "related_company_id", "relationship_type", name="uq_company_relationships"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    related_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CompanyRelationshipType.OTHER.value
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped[Company] = relationship(back_populates="relationships_from", foreign_keys=[company_id])
    related_company: Mapped[Company] = relationship(foreign_keys=[related_company_id])
