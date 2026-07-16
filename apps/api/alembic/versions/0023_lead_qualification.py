"""Lead qualification, scoring, inventory interest, and follow-ups.

Revision ID: 0023_lead_qualification
Revises: 0022_sales_opportunities
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_lead_qualification"
down_revision: str | None = "0022_sales_opportunities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("assigned_manager_id", sa.Uuid(), nullable=True))
    op.add_column("leads", sa.Column("company", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("preferred_market", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("cached_lead_score", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_leads_assigned_manager_id",
        "leads",
        "users",
        ["assigned_manager_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_leads_assigned_manager_id", "leads", ["assigned_manager_id"])
    op.create_index("ix_leads_preferred_market", "leads", ["preferred_market"])
    op.create_index("ix_leads_cached_lead_score", "leads", ["cached_lead_score"])

    op.create_table(
        "lead_qualifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("investment_objective", sa.String(length=50), nullable=True),
        sa.Column("investment_capacity", sa.String(length=100), nullable=True),
        sa.Column("budget_min", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("budget_max", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("preferred_currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("cash_or_financing", sa.String(length=20), nullable=True),
        sa.Column("expected_purchase_timeline", sa.String(length=20), nullable=True),
        sa.Column("preferred_markets", sa.JSON(), nullable=True),
        sa.Column("preferred_projects", sa.JSON(), nullable=True),
        sa.Column("preferred_property_types", sa.JSON(), nullable=True),
        sa.Column("bedrooms_min", sa.Integer(), nullable=True),
        sa.Column("bedrooms_max", sa.Integer(), nullable=True),
        sa.Column("bathrooms_min", sa.Integer(), nullable=True),
        sa.Column("bathrooms_max", sa.Integer(), nullable=True),
        sa.Column("area_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("area_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("target_rental_yield", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("expected_roi", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("risk_tolerance", sa.String(length=20), nullable=True),
        sa.Column("decision_makers", sa.Text(), nullable=True),
        sa.Column("accredited_investor", sa.Boolean(), nullable=True),
        sa.Column("required_documents", sa.JSON(), nullable=True),
        sa.Column("current_concerns", sa.Text(), nullable=True),
        sa.Column("sales_notes", sa.Text(), nullable=True),
        sa.Column("qualification_status", sa.String(length=50), server_default=sa.text("'new'"), nullable=False),
        sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qualified_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["qualified_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_qualifications_lead_id", "lead_qualifications", ["lead_id"], unique=True)

    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("total_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("computed_by_id", sa.Uuid(), nullable=True),
        sa.Column("is_manual_override", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["computed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_scores_lead_id", "lead_scores", ["lead_id"], unique=True)

    op.create_table(
        "lead_score_components",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_score_id", sa.Uuid(), nullable=False),
        sa.Column("component_key", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("weight", sa.Numeric(precision=5, scale=2), server_default=sa.text("1.0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_score_id"], ["lead_scores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_score_components_lead_score_id", "lead_score_components", ["lead_score_id"])

    op.create_table(
        "lead_inventory_interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("interest_type", sa.String(length=20), nullable=False),
        sa.Column("match_reason", sa.String(length=255), nullable=True),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_inventory_interests_lead_id", "lead_inventory_interests", ["lead_id"])
    op.create_index("ix_lead_inventory_interests_asset_id", "lead_inventory_interests", ["inventory_asset_id"])

    op.create_table(
        "lead_follow_ups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("follow_up_type", sa.String(length=20), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_follow_ups_lead_id", "lead_follow_ups", ["lead_id"])

    op.create_table(
        "lead_timeline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_timeline_lead_id", "lead_timeline", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_timeline_lead_id", table_name="lead_timeline")
    op.drop_table("lead_timeline")
    op.drop_index("ix_lead_follow_ups_lead_id", table_name="lead_follow_ups")
    op.drop_table("lead_follow_ups")
    op.drop_index("ix_lead_inventory_interests_asset_id", table_name="lead_inventory_interests")
    op.drop_index("ix_lead_inventory_interests_lead_id", table_name="lead_inventory_interests")
    op.drop_table("lead_inventory_interests")
    op.drop_index("ix_lead_score_components_lead_score_id", table_name="lead_score_components")
    op.drop_table("lead_score_components")
    op.drop_index("ix_lead_scores_lead_id", table_name="lead_scores")
    op.drop_table("lead_scores")
    op.drop_index("ix_lead_qualifications_lead_id", table_name="lead_qualifications")
    op.drop_table("lead_qualifications")
    op.drop_index("ix_leads_cached_lead_score", table_name="leads")
    op.drop_index("ix_leads_preferred_market", table_name="leads")
    op.drop_index("ix_leads_assigned_manager_id", table_name="leads")
    op.drop_constraint("fk_leads_assigned_manager_id", "leads", type_="foreignkey")
    op.drop_column("leads", "cached_lead_score")
    op.drop_column("leads", "preferred_market")
    op.drop_column("leads", "company")
    op.drop_column("leads", "assigned_manager_id")
