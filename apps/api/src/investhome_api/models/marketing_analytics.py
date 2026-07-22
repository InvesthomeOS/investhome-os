"""Marketing analytics foundation — metrics registry, layouts, health, executive alerts."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class MetricAggregationType(str, enum.Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    RATE = "rate"
    STATUS = "status"


class DashboardVisibility(str, enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"


class HealthCategoryStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ExecutiveAlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MarketingMetricsRegistry(Base):
    __tablename__ = "marketing_metrics_registry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_entity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aggregation_type: Mapped[MetricAggregationType] = mapped_column(
        Enum(
            MetricAggregationType,
            name="metric_aggregation_type",
            values_callable=_enum_values,
        ),
        default=MetricAggregationType.COUNT,
        nullable=False,
    )
    permission_requirement: Mapped[str | None] = mapped_column(String(80), nullable=True)
    freshness_requirement_minutes: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketingDashboardLayout(Base):
    __tablename__ = "marketing_dashboard_layouts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    visibility: Mapped[DashboardVisibility] = mapped_column(
        Enum(
            DashboardVisibility,
            name="dashboard_visibility",
            values_callable=_enum_values,
        ),
        default=DashboardVisibility.PRIVATE,
        nullable=False,
    )
    widgets_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    dashboard_key: Mapped[str] = mapped_column(String(80), server_default="executive", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_marketing_dashboard_layouts_owner", "owner_user_id"),)


class MarketingDashboardSavedView(Base):
    __tablename__ = "marketing_dashboard_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dashboard_key: Mapped[str] = mapped_column(String(80), server_default="executive", nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    time_filter_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_marketing_dashboard_saved_views_user", "user_id"),)


class MarketingHealthSnapshot(Base):
    __tablename__ = "marketing_health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    overall_status: Mapped[HealthCategoryStatus] = mapped_column(
        Enum(
            HealthCategoryStatus,
            name="health_category_status",
            values_callable=_enum_values,
        ),
        default=HealthCategoryStatus.UNKNOWN,
        nullable=False,
    )
    categories_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_by: Mapped[str] = mapped_column(String(30), server_default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_marketing_health_snapshots_at", "snapshot_at"),)


class MarketingExecutiveAlert(Base):
    __tablename__ = "marketing_executive_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[ExecutiveAlertSeverity] = mapped_column(
        Enum(
            ExecutiveAlertSeverity,
            name="executive_alert_severity",
            values_callable=_enum_values,
        ),
        default=ExecutiveAlertSeverity.INFO,
        nullable=False,
    )
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_marketing_executive_alerts_category", "category"),
        Index("ix_marketing_executive_alerts_resolved", "is_resolved"),
    )
