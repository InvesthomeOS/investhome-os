"""Primary campaign attribution per lead — Sprint 8A3 single-touch model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class MarketingAttributionSource(str, enum.Enum):
    MANUAL = "manual"
    UTM = "utm"
    IMPORT = "import"
    CRM = "crm"
    REFERRAL = "referral"
    OTHER = "other"


class MarketingLeadAttribution(Base):
    """One primary campaign attribution per canonical Sales lead."""

    __tablename__ = "marketing_lead_attributions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    attribution_source: Mapped[MarketingAttributionSource] = mapped_column(
        String(20), nullable=False, default=MarketingAttributionSource.OTHER
    )
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_touch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attribution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_mkt_lead_attrib_lead_id", "lead_id"),
        Index("ix_mkt_lead_attrib_campaign_id", "campaign_id"),
        Index("ix_mkt_lead_attrib_company_id", "company_id"),
        Index("ix_mkt_lead_attrib_created_at", "created_at"),
        Index("ix_mkt_lead_attrib_converted_at", "converted_at"),
        Index("ix_mkt_lead_attrib_utm_source", "utm_source"),
    )


class MarketingLeadAttributionAudit(Base):
    __tablename__ = "marketing_lead_attribution_audit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_attributions.id", ondelete="SET NULL"), nullable=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    previous_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    new_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_mkt_lead_attrib_audit_lead_id", "lead_id"),)
