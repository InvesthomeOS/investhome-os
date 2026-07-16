"""Inventory assets foundation — buildings, floors, inventory assets.

Revision ID: 0017_inventory_assets
Revises: 0016_design_studio_sprint2a_seed
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_inventory_assets"
down_revision: str | None = "0016_design_studio_sprint2a_seed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "buildings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("building_type", sa.String(length=50), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "code", name="uq_buildings_project_code"),
    )
    op.create_index("ix_buildings_project_id", "buildings", ["project_id"])

    op.create_table(
        "floors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("floor_number", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("level_code", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_id", "floor_number", name="uq_floors_building_floor_number"),
        sa.UniqueConstraint("building_id", "level_code", name="uq_floors_building_level_code"),
    )
    op.create_index("ix_floors_building_id", "floors", ["building_id"])

    op.create_table(
        "inventory_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("floor_id", sa.Uuid(), nullable=True),
        sa.Column("display_id", sa.String(length=50), nullable=False),
        sa.Column("system_code", sa.String(length=100), nullable=False),
        sa.Column("legal_identifier", sa.String(length=100), nullable=True),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("usage_type", sa.String(length=50), nullable=False),
        sa.Column("unit_subtype", sa.String(length=80), nullable=True),
        sa.Column("bedrooms", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("bathrooms", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("interior_area_sqft", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("exterior_area_sqft", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_area_sqft", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("orientation", sa.String(length=20), nullable=True),
        sa.Column("view_type", sa.String(length=80), nullable=True),
        sa.Column("availability_status", sa.String(length=50), server_default="not_released", nullable=False),
        sa.Column("reservation_status", sa.String(length=50), server_default="none", nullable=False),
        sa.Column("sales_status", sa.String(length=50), server_default="not_for_sale", nullable=False),
        sa.Column("construction_status", sa.String(length=50), server_default="planned", nullable=False),
        sa.Column("closing_status", sa.String(length=50), server_default="not_started", nullable=False),
        sa.Column("leasing_status", sa.String(length=50), server_default="not_applicable", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "display_id", name="uq_inventory_assets_project_display_id"),
    )
    op.create_index("ix_inventory_assets_project_id", "inventory_assets", ["project_id"])
    op.create_index("ix_inventory_assets_building_id", "inventory_assets", ["building_id"])
    op.create_index("ix_inventory_assets_floor_id", "inventory_assets", ["floor_id"])
    op.create_index("ix_inventory_assets_system_code", "inventory_assets", ["system_code"], unique=True)
    op.create_index("ix_inventory_assets_availability_status", "inventory_assets", ["availability_status"])
    op.create_index("ix_inventory_assets_sales_status", "inventory_assets", ["sales_status"])

    op.create_table(
        "inventory_asset_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("status_category", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_status_history_asset_id",
        "inventory_asset_status_history",
        ["inventory_asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_status_history_asset_id", table_name="inventory_asset_status_history")
    op.drop_table("inventory_asset_status_history")
    op.drop_index("ix_inventory_assets_sales_status", table_name="inventory_assets")
    op.drop_index("ix_inventory_assets_availability_status", table_name="inventory_assets")
    op.drop_index("ix_inventory_assets_system_code", table_name="inventory_assets")
    op.drop_index("ix_inventory_assets_floor_id", table_name="inventory_assets")
    op.drop_index("ix_inventory_assets_building_id", table_name="inventory_assets")
    op.drop_index("ix_inventory_assets_project_id", table_name="inventory_assets")
    op.drop_table("inventory_assets")
    op.drop_index("ix_floors_building_id", table_name="floors")
    op.drop_table("floors")
    op.drop_index("ix_buildings_project_id", table_name="buildings")
    op.drop_table("buildings")
