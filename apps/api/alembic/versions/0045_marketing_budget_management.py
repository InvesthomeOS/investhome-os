"""Marketing budget management — plans, allocations, forecasts, scenarios.

Revision ID: 0045_marketing_budget_management
Revises: 0044_mkt_analytics_fnd
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_marketing_budget_management"
down_revision: str | None = "0044_mkt_analytics_fnd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_budget_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "plan_type",
            sa.Enum("annual", "quarterly", "monthly", name="budget_plan_type"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("quarter", sa.Integer(), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("total_budget", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "pending_approval",
                "approved",
                "locked",
                "active",
                "paused",
                "closed",
                "archived",
                name="budget_plan_status",
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("business_unit_id", sa.Uuid(), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_plans_status", "marketing_budget_plans", ["status"])
    op.create_index("ix_marketing_budget_plans_fiscal_year", "marketing_budget_plans", ["fiscal_year"])
    op.create_index("ix_marketing_budget_plans_plan_type", "marketing_budget_plans", ["plan_type"])

    op.create_table(
        "marketing_budget_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("parent_allocation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "hierarchy_level",
            sa.Enum(
                "organization",
                "business_unit",
                "country",
                "region",
                "project",
                "campaign",
                "channel",
                "creative",
                name="budget_hierarchy_level",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("business_unit_id", sa.Uuid(), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("creative_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_budget_id", sa.Uuid(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("planned_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("allocated_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("committed_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("spent_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legacy_budget_id"], ["marketing_budgets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_allocation_id"], ["marketing_budget_allocations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_allocations_plan_id", "marketing_budget_allocations", ["plan_id"])
    op.create_index("ix_marketing_budget_allocations_campaign_id", "marketing_budget_allocations", ["campaign_id"])
    op.create_index("ix_marketing_budget_allocations_channel_id", "marketing_budget_allocations", ["channel_id"])
    op.create_index("ix_marketing_budget_allocations_hierarchy", "marketing_budget_allocations", ["hierarchy_level"])

    op.create_table(
        "marketing_budget_spend_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("allocation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "record_type",
            sa.Enum("actual", "committed", name="budget_spend_record_type"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("source_ref_type", sa.String(length=40), nullable=True),
        sa.Column("source_ref_id", sa.Uuid(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["allocation_id"], ["marketing_budget_allocations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_spend_records_plan_id", "marketing_budget_spend_records", ["plan_id"])
    op.create_index(
        "ix_marketing_budget_spend_records_allocation_id",
        "marketing_budget_spend_records",
        ["allocation_id"],
    )
    op.create_index(
        "ix_marketing_budget_spend_records_record_type",
        "marketing_budget_spend_records",
        ["record_type"],
    )

    op.create_table(
        "marketing_budget_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=True),
        sa.Column("request_type", sa.String(length=40), nullable=False),
        sa.Column("requested_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "pending", "approved", "rejected", "cancelled", name="budget_request_status"),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["allocation_id"], ["marketing_budget_allocations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_requests_plan_id", "marketing_budget_requests", ["plan_id"])
    op.create_index("ix_marketing_budget_requests_status", "marketing_budget_requests", ["status"])

    op.create_table(
        "marketing_budget_transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("from_allocation_id", sa.Uuid(), nullable=True),
        sa.Column("to_allocation_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "pending", "approved", "rejected", "cancelled", name="budget_transfer_status"),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_allocation_id"], ["marketing_budget_allocations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_allocation_id"], ["marketing_budget_allocations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_transfers_plan_id", "marketing_budget_transfers", ["plan_id"])
    op.create_index("ix_marketing_budget_transfers_status", "marketing_budget_transfers", ["status"])

    op.create_table(
        "marketing_budget_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column(
            "approval_role",
            sa.Enum(
                "marketing_manager",
                "marketing_director",
                "cmo",
                "ceo",
                "finance",
                name="budget_approval_role",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "pending",
                "approved",
                "rejected",
                "returned",
                "cancelled",
                name="budget_approval_status",
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("sequence_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("approver_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budget_approvals_entity", "marketing_budget_approvals", ["entity_type", "entity_id"])
    op.create_index("ix_marketing_budget_approvals_status", "marketing_budget_approvals", ["status"])

    op.create_table(
        "marketing_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metric_type",
            sa.Enum(
                "lead",
                "qualified_lead",
                "meeting",
                "reservation",
                "sales",
                "revenue",
                "spend",
                name="forecast_metric_type",
            ),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("forecast_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("state", sa.String(length=30), server_default="unknown", nullable=False),
        sa.Column("pipeline_connected", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_forecasts_plan_id", "marketing_forecasts", ["plan_id"])
    op.create_index("ix_marketing_forecasts_metric_type", "marketing_forecasts", ["metric_type"])

    op.create_table(
        "marketing_scenario_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "scenario_type",
            sa.Enum("base_case", "optimistic", "conservative", "custom", name="scenario_type"),
            nullable=False,
        ),
        sa.Column("budget_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("spend_target", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("lead_target", sa.Integer(), nullable=True),
        sa.Column("sales_target", sa.Integer(), nullable=True),
        sa.Column("revenue_target", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["marketing_budget_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_scenario_plans_plan_id", "marketing_scenario_plans", ["plan_id"])
    op.create_index("ix_marketing_scenario_plans_scenario_type", "marketing_scenario_plans", ["scenario_type"])


def downgrade() -> None:
    op.drop_index("ix_marketing_scenario_plans_scenario_type", table_name="marketing_scenario_plans")
    op.drop_index("ix_marketing_scenario_plans_plan_id", table_name="marketing_scenario_plans")
    op.drop_table("marketing_scenario_plans")

    op.drop_index("ix_marketing_forecasts_metric_type", table_name="marketing_forecasts")
    op.drop_index("ix_marketing_forecasts_plan_id", table_name="marketing_forecasts")
    op.drop_table("marketing_forecasts")

    op.drop_index("ix_marketing_budget_approvals_status", table_name="marketing_budget_approvals")
    op.drop_index("ix_marketing_budget_approvals_entity", table_name="marketing_budget_approvals")
    op.drop_table("marketing_budget_approvals")

    op.drop_index("ix_marketing_budget_transfers_status", table_name="marketing_budget_transfers")
    op.drop_index("ix_marketing_budget_transfers_plan_id", table_name="marketing_budget_transfers")
    op.drop_table("marketing_budget_transfers")

    op.drop_index("ix_marketing_budget_requests_status", table_name="marketing_budget_requests")
    op.drop_index("ix_marketing_budget_requests_plan_id", table_name="marketing_budget_requests")
    op.drop_table("marketing_budget_requests")

    op.drop_index("ix_marketing_budget_spend_records_record_type", table_name="marketing_budget_spend_records")
    op.drop_index("ix_marketing_budget_spend_records_allocation_id", table_name="marketing_budget_spend_records")
    op.drop_index("ix_marketing_budget_spend_records_plan_id", table_name="marketing_budget_spend_records")
    op.drop_table("marketing_budget_spend_records")

    op.drop_index("ix_marketing_budget_allocations_hierarchy", table_name="marketing_budget_allocations")
    op.drop_index("ix_marketing_budget_allocations_channel_id", table_name="marketing_budget_allocations")
    op.drop_index("ix_marketing_budget_allocations_campaign_id", table_name="marketing_budget_allocations")
    op.drop_index("ix_marketing_budget_allocations_plan_id", table_name="marketing_budget_allocations")
    op.drop_table("marketing_budget_allocations")

    op.drop_index("ix_marketing_budget_plans_plan_type", table_name="marketing_budget_plans")
    op.drop_index("ix_marketing_budget_plans_fiscal_year", table_name="marketing_budget_plans")
    op.drop_index("ix_marketing_budget_plans_status", table_name="marketing_budget_plans")
    op.drop_table("marketing_budget_plans")

    for enum_name in (
        "scenario_type",
        "forecast_metric_type",
        "budget_approval_status",
        "budget_approval_role",
        "budget_transfer_status",
        "budget_request_status",
        "budget_spend_record_type",
        "budget_hierarchy_level",
        "budget_plan_status",
        "budget_plan_type",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
