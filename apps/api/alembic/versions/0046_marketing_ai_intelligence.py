"""Marketing AI intelligence foundation.

Revision ID: 0046_marketing_ai_intelligence
Revises: 0045_merge_marketing_heads
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_marketing_ai_intelligence"
down_revision: str | None = "0045_merge_marketing_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_ai_insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "campaign",
                "country",
                "project",
                "channel",
                "creative",
                "landing_page",
                "form",
                "revenue",
                "audience",
                "budget",
                "automation",
                "general",
                name="ai_insight_category",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "critical", name="ai_insight_severity"),
            server_default="info",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level"),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_ai_insights_category_active", "marketing_ai_insights", ["category", "is_active"])

    op.create_table(
        "marketing_ai_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "recommendation_type",
            sa.Enum(
                "increase_budget",
                "decrease_budget",
                "pause_campaign",
                "scale_campaign",
                "duplicate_campaign",
                "refresh_creative",
                "improve_landing_page",
                "improve_form",
                "fix_tracking",
                "reallocate_budget",
                "call_lead",
                "assign_sales",
                "send_email",
                "send_whatsapp",
                "other",
                name="ai_recommendation_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level", create_type=False),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("requires_evidence", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_ai_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "framework",
            sa.Enum(
                "lead_scoring",
                "predictive_revenue",
                "campaign_optimization",
                "creative_intelligence",
                "audience_intelligence",
                "budget_optimization",
                "next_best_action",
                name="ai_prediction_framework",
            ),
            nullable=False,
        ),
        sa.Column("prediction_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level", create_type=False),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("confidence_pct", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_ai_predictions_framework_key",
        "marketing_ai_predictions",
        ["framework", "prediction_key"],
    )

    op.create_table(
        "marketing_ai_anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "anomaly_type",
            sa.Enum(
                "traffic_drop",
                "lead_drop",
                "conversion_drop",
                "ctr_drop",
                "duplicate_spike",
                "spam_spike",
                "tracking_failure",
                "revenue_drop",
                name="ai_anomaly_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level", create_type=False),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "critical", name="ai_insight_severity", create_type=False),
            server_default="warning",
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_ai_briefings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "period",
            sa.Enum("daily", "weekly", "monthly", "quarterly", "board", name="ai_briefing_period"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level", create_type=False),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("sections_json", sa.JSON(), nullable=True),
        sa.Column("generated_for_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_ai_copilot_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=80), nullable=True),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column(
            "confidence",
            sa.Enum("unknown", "low", "medium", "high", name="ai_confidence_level", create_type=False),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_ai_copilot_queries_user_created",
        "marketing_ai_copilot_queries",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_ai_copilot_queries_user_created", table_name="marketing_ai_copilot_queries")
    op.drop_table("marketing_ai_copilot_queries")
    op.drop_table("marketing_ai_briefings")
    op.drop_table("marketing_ai_anomalies")
    op.drop_index("ix_marketing_ai_predictions_framework_key", table_name="marketing_ai_predictions")
    op.drop_table("marketing_ai_predictions")
    op.drop_table("marketing_ai_recommendations")
    op.drop_index("ix_marketing_ai_insights_category_active", table_name="marketing_ai_insights")
    op.drop_table("marketing_ai_insights")
    op.execute("DROP TYPE IF EXISTS ai_briefing_period")
    op.execute("DROP TYPE IF EXISTS ai_anomaly_type")
    op.execute("DROP TYPE IF EXISTS ai_prediction_framework")
    op.execute("DROP TYPE IF EXISTS ai_recommendation_type")
    op.execute("DROP TYPE IF EXISTS ai_confidence_level")
    op.execute("DROP TYPE IF EXISTS ai_insight_severity")
    op.execute("DROP TYPE IF EXISTS ai_insight_category")
