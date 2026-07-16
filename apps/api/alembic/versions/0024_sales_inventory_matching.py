"""Sales inventory matching, preferences, and shortlists.

Revision ID: 0024_sales_inventory_matching
Revises: 0023_lead_qualification
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_sales_inventory_matching"
down_revision: str | None = "0023_lead_qualification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunity_inventory",
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.create_table(
        "sales_inventory_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("budget_min", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("budget_max", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("bedrooms_min", sa.Integer(), nullable=True),
        sa.Column("bedrooms_max", sa.Integer(), nullable=True),
        sa.Column("bathrooms_min", sa.Integer(), nullable=True),
        sa.Column("bathrooms_max", sa.Integer(), nullable=True),
        sa.Column("area_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("area_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("floor_min", sa.Integer(), nullable=True),
        sa.Column("floor_max", sa.Integer(), nullable=True),
        sa.Column("delivery_date_before", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_inventory_preferences_lead_xor_opportunity",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_inventory_preferences_lead_id", "sales_inventory_preferences", ["lead_id"], unique=True)
    op.create_index(
        "ix_sales_inventory_preferences_opportunity_id",
        "sales_inventory_preferences",
        ["opportunity_id"],
        unique=True,
    )

    op.create_table(
        "sales_inventory_preference_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["preference_id"], ["sales_inventory_preferences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preference_id", "project_id", name="uq_pref_project"),
    )

    op.create_table(
        "sales_inventory_preference_asset_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["preference_id"], ["sales_inventory_preferences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preference_id", "asset_type", name="uq_pref_asset_type"),
    )

    op.create_table(
        "sales_inventory_preference_usage_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("usage_type", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["preference_id"], ["sales_inventory_preferences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preference_id", "usage_type", name="uq_pref_usage_type"),
    )

    op.create_table(
        "sales_inventory_preference_buildings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("preference_id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preference_id"], ["sales_inventory_preferences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preference_id", "building_id", name="uq_pref_building"),
    )

    op.create_table(
        "sales_inventory_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("match_source", sa.String(length=20), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_reason", sa.String(length=255), nullable=True),
        sa.Column("rejection_reason", sa.String(length=30), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("inventory_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_inventory_matches_lead_xor_opportunity",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_inventory_matches_lead_id", "sales_inventory_matches", ["lead_id"])
    op.create_index("ix_sales_inventory_matches_opportunity_id", "sales_inventory_matches", ["opportunity_id"])
    op.create_index("ix_sales_inventory_matches_asset_id", "sales_inventory_matches", ["inventory_asset_id"])
    op.create_index("ix_sales_inventory_matches_status", "sales_inventory_matches", ["status"])

    op.create_table(
        "sales_shortlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(lead_id IS NOT NULL AND opportunity_id IS NULL) OR "
            "(lead_id IS NULL AND opportunity_id IS NOT NULL)",
            name="ck_sales_shortlists_lead_xor_opportunity",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_shortlists_lead_id", "sales_shortlists", ["lead_id"])
    op.create_index("ix_sales_shortlists_opportunity_id", "sales_shortlists", ["opportunity_id"])

    op.create_table(
        "sales_shortlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shortlist_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("inventory_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shortlist_id"], ["sales_shortlists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shortlist_id", "inventory_asset_id", name="uq_shortlist_asset"),
    )
    op.create_index("ix_sales_shortlist_items_shortlist_id", "sales_shortlist_items", ["shortlist_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_shortlist_items_shortlist_id", table_name="sales_shortlist_items")
    op.drop_table("sales_shortlist_items")
    op.drop_index("ix_sales_shortlists_opportunity_id", table_name="sales_shortlists")
    op.drop_index("ix_sales_shortlists_lead_id", table_name="sales_shortlists")
    op.drop_table("sales_shortlists")
    op.drop_index("ix_sales_inventory_matches_status", table_name="sales_inventory_matches")
    op.drop_index("ix_sales_inventory_matches_asset_id", table_name="sales_inventory_matches")
    op.drop_index("ix_sales_inventory_matches_opportunity_id", table_name="sales_inventory_matches")
    op.drop_index("ix_sales_inventory_matches_lead_id", table_name="sales_inventory_matches")
    op.drop_table("sales_inventory_matches")
    op.drop_table("sales_inventory_preference_buildings")
    op.drop_table("sales_inventory_preference_usage_types")
    op.drop_table("sales_inventory_preference_asset_types")
    op.drop_table("sales_inventory_preference_projects")
    op.drop_index("ix_sales_inventory_preferences_opportunity_id", table_name="sales_inventory_preferences")
    op.drop_index("ix_sales_inventory_preferences_lead_id", table_name="sales_inventory_preferences")
    op.drop_table("sales_inventory_preferences")
    op.drop_column("opportunity_inventory", "is_primary")
