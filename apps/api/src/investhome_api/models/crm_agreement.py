"""CRM Agreement — historical Bitrix Anlaşmalar linked to a canonical contact + project group.

Sales opportunities remain in Sales. This table is CRM-only.
"""

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
    JSON,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class CrmAgreementStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CrmAgreement(Base):
    __tablename__ = "crm_agreements"
    __table_args__ = (
        UniqueConstraint("source", "source_external_id", name="uq_crm_agreements_source_external_id"),
        Index("ix_crm_agreements_contact_id", "contact_id"),
        Index("ix_crm_agreements_project_id", "project_id"),
        Index("ix_crm_agreements_project_group", "project_group"),
        Index("ix_crm_agreements_status", "status"),
        Index("ix_crm_agreements_review_required", "review_required"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_group: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="bitrix")
    source_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[CrmAgreementStatus] = mapped_column(
        Enum(CrmAgreementStatus, native_enum=False, length=20),
        nullable=False,
        default=CrmAgreementStatus.UNKNOWN,
    )
    agreement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    unit_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    investment_amount: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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
