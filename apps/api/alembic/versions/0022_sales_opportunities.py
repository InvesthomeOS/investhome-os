"""Sales opportunities — domain tables and indexes.

Revision ID: 0022_sales_opportunities
Revises: 0021_inventory_assignments
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_sales_opportunities"
down_revision: str | None = "0021_inventory_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_code", sa.String(length=50), nullable=False),
        sa.Column("display_id", sa.String(length=50), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("party_type", sa.String(length=20), nullable=False),
        sa.Column("assigned_sales_user_id", sa.Uuid(), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("probability", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("expected_revenue", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("priority", sa.String(length=20), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("current_risks", sa.JSON(), nullable=True),
        sa.Column("next_action", sa.String(length=50), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("loss_reason", sa.String(length=50), nullable=True),
        sa.Column("loss_notes", sa.Text(), nullable=True),
        sa.Column("dormant_review_date", sa.Date(), nullable=True),
        sa.Column("cancelled_reason", sa.String(length=255), nullable=True),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_sales_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reservation_id"], ["inventory_reservations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_opportunities_opportunity_code", "sales_opportunities", ["opportunity_code"], unique=True)
    op.create_index("ix_sales_opportunities_stage", "sales_opportunities", ["stage"])
    op.create_index("ix_sales_opportunities_lead_id", "sales_opportunities", ["lead_id"])
    op.create_index("ix_sales_opportunities_party_id", "sales_opportunities", ["party_id"])
    op.create_index("ix_sales_opportunities_assigned_sales_user_id", "sales_opportunities", ["assigned_sales_user_id"])
    op.create_index("ix_sales_opportunities_reservation_id", "sales_opportunities", ["reservation_id"])
    op.create_index("ix_sales_opportunities_archived_at", "sales_opportunities", ["archived_at"])

    op.create_table(
        "opportunity_timeline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=True),
        sa.Column("from_probability", sa.Integer(), nullable=True),
        sa.Column("to_probability", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_timeline_opportunity_id", "opportunity_timeline", ["opportunity_id"])

    op.create_table(
        "opportunity_inventory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("match_reason", sa.String(length=255), nullable=True),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("shortlisted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_inventory_opportunity_id", "opportunity_inventory", ["opportunity_id"])
    op.create_index("ix_opportunity_inventory_asset_id", "opportunity_inventory", ["inventory_asset_id"])

    op.create_table(
        "opportunity_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_projects_opportunity_id", "opportunity_projects", ["opportunity_id"])
    op.create_index("ix_opportunity_projects_project_id", "opportunity_projects", ["project_id"])

    op.create_table(
        "opportunity_probability_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("old_probability", sa.Integer(), nullable=False),
        sa.Column("new_probability", sa.Integer(), nullable=False),
        sa.Column("changed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_probability_history_opportunity_id",
        "opportunity_probability_history",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_probability_history_opportunity_id", table_name="opportunity_probability_history")
    op.drop_table("opportunity_probability_history")
    op.drop_index("ix_opportunity_projects_project_id", table_name="opportunity_projects")
    op.drop_index("ix_opportunity_projects_opportunity_id", table_name="opportunity_projects")
    op.drop_table("opportunity_projects")
    op.drop_index("ix_opportunity_inventory_asset_id", table_name="opportunity_inventory")
    op.drop_index("ix_opportunity_inventory_opportunity_id", table_name="opportunity_inventory")
    op.drop_table("opportunity_inventory")
    op.drop_index("ix_opportunity_timeline_opportunity_id", table_name="opportunity_timeline")
    op.drop_table("opportunity_timeline")
    op.drop_index("ix_sales_opportunities_archived_at", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_reservation_id", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_assigned_sales_user_id", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_party_id", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_lead_id", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_stage", table_name="sales_opportunities")
    op.drop_index("ix_sales_opportunities_opportunity_code", table_name="sales_opportunities")
    op.drop_table("sales_opportunities")
