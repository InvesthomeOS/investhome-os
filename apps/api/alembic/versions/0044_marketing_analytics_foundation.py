"""Marketing analytics foundation — metrics registry, layouts, health snapshots.

Revision ID: 0044_mkt_analytics_fnd
Revises: 0043_mkt_landing_conv
Create Date: 2026-07-16

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0044_mkt_analytics_fnd"
down_revision: str | None = "0043_mkt_landing_conv"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

METRICS_SEED = [
    ("marketing_leads", "Marketing Leads", "marketing_lead_contexts", "count", "view_leads", 60),
    ("qualified_leads", "Qualified Leads", "marketing_lead_contexts", "count", "view_leads", 60),
    ("sales_handoffs", "Sales Handoffs", "marketing_sales_handoffs", "count", "view_leads", 60),
    ("meetings", "Meetings", None, "status", "view_leads", None),
    ("reservations", "Reservations", None, "status", "view_leads", None),
    ("sales", "Sales", None, "status", "view_leads", None),
    ("revenue", "Revenue", None, "status", "view_spend", None),
    ("conversion_rate", "Conversion Rate", None, "rate", "export_analytics", 60),
    ("marketing_health", "Marketing Health", None, "status", "view_dashboard", 30),
    ("tracking_health", "Tracking Health", None, "status", "view_attribution", 30),
    ("attribution_health", "Attribution Health", None, "status", "view_attribution", 30),
    ("data_freshness", "Data Freshness", None, "status", "view_dashboard", 15),
]


def upgrade() -> None:
    op.create_table(
        "marketing_metrics_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("source_entity", sa.String(length=80), nullable=True),
        sa.Column(
            "aggregation_type",
            sa.Enum("count", "sum", "avg", "rate", "status", name="metric_aggregation_type"),
            nullable=False,
        ),
        sa.Column("permission_requirement", sa.String(length=80), nullable=True),
        sa.Column("freshness_requirement_minutes", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_key"),
    )

    op.create_table(
        "marketing_dashboard_layouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column(
            "visibility",
            sa.Enum("private", "team", "organization", name="dashboard_visibility"),
            server_default="private",
            nullable=False,
        ),
        sa.Column("widgets_json", sa.JSON(), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("dashboard_key", sa.String(length=80), server_default="executive", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_dashboard_layouts_owner", "marketing_dashboard_layouts", ["owner_user_id"])

    op.create_table(
        "marketing_dashboard_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dashboard_key", sa.String(length=80), server_default="executive", nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("time_filter_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_dashboard_saved_views_user", "marketing_dashboard_saved_views", ["user_id"])

    op.create_table(
        "marketing_health_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "overall_status",
            sa.Enum("healthy", "warning", "critical", "unknown", name="health_category_status"),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("categories_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("computed_by", sa.String(length=30), server_default="system", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_health_snapshots_at", "marketing_health_snapshots", ["snapshot_at"])

    op.create_table(
        "marketing_executive_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "critical", name="executive_alert_severity"),
            server_default="info",
            nullable=False,
        ),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_executive_alerts_category", "marketing_executive_alerts", ["category"])
    op.create_index("ix_marketing_executive_alerts_resolved", "marketing_executive_alerts", ["is_resolved"])

    metric_agg_enum = sa.Enum(
        "count", "sum", "avg", "rate", "status", name="metric_aggregation_type", create_type=False
    )
    metrics_table = sa.table(
        "marketing_metrics_registry",
        sa.column("id", sa.Uuid()),
        sa.column("metric_key", sa.String()),
        sa.column("label", sa.String()),
        sa.column("source_entity", sa.String()),
        sa.column("aggregation_type", metric_agg_enum),
        sa.column("permission_requirement", sa.String()),
        sa.column("freshness_requirement_minutes", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        metrics_table,
        [
            {
                "id": uuid.uuid4(),
                "metric_key": key,
                "label": label,
                "source_entity": entity,
                "aggregation_type": agg,
                "permission_requirement": perm,
                "freshness_requirement_minutes": fresh,
                "is_active": True,
            }
            for key, label, entity, agg, perm, fresh in METRICS_SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("marketing_executive_alerts")
    op.drop_table("marketing_health_snapshots")
    op.drop_table("marketing_dashboard_saved_views")
    op.drop_table("marketing_dashboard_layouts")
    op.drop_table("marketing_metrics_registry")
    op.execute("DROP TYPE IF EXISTS executive_alert_severity")
    op.execute("DROP TYPE IF EXISTS health_category_status")
    op.execute("DROP TYPE IF EXISTS dashboard_visibility")
    op.execute("DROP TYPE IF EXISTS metric_aggregation_type")
