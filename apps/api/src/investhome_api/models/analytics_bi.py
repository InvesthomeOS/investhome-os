"""Business Intelligence persistence — saved reports and alert thresholds (P9)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from investhome_api.db.base import Base


class BiSavedReport(Base):
    __tablename__ = "bi_saved_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(40), nullable=False, server_default="executive")
    chart_type: Mapped[str] = mapped_column(String(40), nullable=False, server_default="kpi")
    metric_keys_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    layout_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_bi_saved_reports_owner", "owner_user_id"),
        Index("ix_bi_saved_reports_domain", "domain"),
    )


class BiAlertThreshold(Base):
    """Threshold config that feeds the existing Alert Center — does not duplicate alerts."""

    __tablename__ = "bi_alert_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)  # gt|gte|lt|lte|eq
    threshold_value: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default="warning")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("metric_key", "name", name="uq_bi_alert_thresholds_metric_name"),
        Index("ix_bi_alert_thresholds_metric", "metric_key"),
    )
