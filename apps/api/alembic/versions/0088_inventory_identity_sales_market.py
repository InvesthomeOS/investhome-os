"""Building-level unit identity and sales market allocation.

Revision ID: 0088_inventory_identity_sales_market
Revises: 0087_password_reset_tokens
Create Date: 2026-11-03

PostgreSQL 16 (compose image postgres:16-alpine) supports UNIQUE NULLS NOT
DISTINCT, added in PostgreSQL 15. That keeps a null building_id from
allowing duplicate display_id values in the same project.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0088_inventory_identity_sales_market"
down_revision: str | None = "0087_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_inventory_assets_project_display_id",
        "inventory_assets",
        type_="unique",
    )
    op.execute(
        """
        ALTER TABLE inventory_assets
        ADD CONSTRAINT uq_inventory_assets_project_building_display
        UNIQUE NULLS NOT DISTINCT (project_id, building_id, display_id)
        """
    )
    op.add_column(
        "inventory_assets",
        sa.Column("sales_market", sa.String(length=20), nullable=True),
    )
    op.create_index(
        "ix_inventory_assets_sales_market",
        "inventory_assets",
        ["sales_market"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_assets_sales_market", table_name="inventory_assets")
    op.drop_column("inventory_assets", "sales_market")
    op.drop_constraint(
        "uq_inventory_assets_project_building_display",
        "inventory_assets",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_inventory_assets_project_display_id",
        "inventory_assets",
        ["project_id", "display_id"],
    )
