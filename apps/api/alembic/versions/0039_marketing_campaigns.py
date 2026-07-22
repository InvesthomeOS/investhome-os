"""Marketing campaign management extension tables.

Revision ID: 0039_marketing_campaigns
Revises: 0038_marketing_foundation
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_marketing_campaigns"
down_revision: str | None = "0038_marketing_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaign_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("objectives", sa.Text(), nullable=True),
        sa.Column("messaging", sa.Text(), nullable=True),
        sa.Column("strategies", sa.Text(), nullable=True),
        sa.Column("risks", sa.Text(), nullable=True),
        sa.Column("competitive_context", sa.Text(), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )

    op.create_table(
        "marketing_campaign_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("milestone_type", sa.String(length=30), server_default="other", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="not_started", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("depends_on_ids", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_campaign_milestones_campaign_id", "marketing_campaign_milestones", ["campaign_id"])
    op.create_index("ix_marketing_campaign_milestones_status", "marketing_campaign_milestones", ["status"])

    op.create_table(
        "marketing_campaign_channel_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_currency", sa.String(length=3), nullable=True),
        sa.Column("schedule_json", sa.JSON(), nullable=True),
        sa.Column("tracking_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_campaign_channel_assignments_campaign_id",
        "marketing_campaign_channel_assignments",
        ["campaign_id"],
    )
    op.create_index(
        "ix_marketing_campaign_channel_assignments_channel_id",
        "marketing_campaign_channel_assignments",
        ["channel_id"],
    )

    op.create_table(
        "marketing_campaign_budget_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("planned_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("committed_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("spent_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["budget_id"], ["marketing_budgets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_campaign_budget_allocations_campaign_id",
        "marketing_campaign_budget_allocations",
        ["campaign_id"],
    )

    op.create_table(
        "marketing_campaign_tracking",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("utm_source", sa.String(length=120), nullable=True),
        sa.Column("utm_medium", sa.String(length=120), nullable=True),
        sa.Column("utm_campaign", sa.String(length=120), nullable=True),
        sa.Column("utm_term", sa.String(length=120), nullable=True),
        sa.Column("utm_content", sa.String(length=120), nullable=True),
        sa.Column("tracking_code", sa.String(length=120), nullable=True),
        sa.Column("landing_page_url", sa.String(length=512), nullable=True),
        sa.Column("readiness_status", sa.String(length=20), server_default="not_configured", nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )

    op.create_table(
        "marketing_campaign_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.String(length=80), nullable=False),
        sa.Column("metric_label", sa.String(length=255), nullable=True),
        sa.Column("target_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("period", sa.String(length=40), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_campaign_targets_campaign_id", "marketing_campaign_targets", ["campaign_id"])

    op.create_table(
        "marketing_campaign_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(length=40), nullable=True),
        sa.Column("objective", sa.String(length=40), nullable=True),
        sa.Column("template_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_campaign_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_campaign_saved_views_user_id", "marketing_campaign_saved_views", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_marketing_campaign_saved_views_user_id", table_name="marketing_campaign_saved_views")
    op.drop_table("marketing_campaign_saved_views")
    op.drop_table("marketing_campaign_templates")
    op.drop_index("ix_marketing_campaign_targets_campaign_id", table_name="marketing_campaign_targets")
    op.drop_table("marketing_campaign_targets")
    op.drop_table("marketing_campaign_tracking")
    op.drop_index(
        "ix_marketing_campaign_budget_allocations_campaign_id",
        table_name="marketing_campaign_budget_allocations",
    )
    op.drop_table("marketing_campaign_budget_allocations")
    op.drop_index(
        "ix_marketing_campaign_channel_assignments_channel_id",
        table_name="marketing_campaign_channel_assignments",
    )
    op.drop_index(
        "ix_marketing_campaign_channel_assignments_campaign_id",
        table_name="marketing_campaign_channel_assignments",
    )
    op.drop_table("marketing_campaign_channel_assignments")
    op.drop_index("ix_marketing_campaign_milestones_status", table_name="marketing_campaign_milestones")
    op.drop_index("ix_marketing_campaign_milestones_campaign_id", table_name="marketing_campaign_milestones")
    op.drop_table("marketing_campaign_milestones")
    op.drop_table("marketing_campaign_briefs")
