"""Project phases and optional unit phase link.

Revision ID: 0090_project_phases
Revises: 0089_user_notification_preferences

Does not rewrite existing unit identifiers or agreement unit text.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0090_project_phases"
down_revision: str | None = "0089_user_notification_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_phases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_phases_project_name"),
    )
    op.create_index("ix_project_phases_project_id", "project_phases", ["project_id"])
    op.add_column("inventory_assets", sa.Column("phase_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_inventory_assets_phase_id",
        "inventory_assets",
        "project_phases",
        ["phase_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "uq_inventory_assets_project_building_display",
        "inventory_assets",
        type_="unique",
    )
    op.execute(
        """
        ALTER TABLE inventory_assets
        ADD CONSTRAINT uq_inventory_assets_project_building_phase_display
        UNIQUE NULLS NOT DISTINCT (project_id, building_id, phase_id, display_id)
        """
    )
    op.add_column("crm_agreements", sa.Column("phase_id", sa.Uuid(), nullable=True))
    op.add_column("crm_agreements", sa.Column("inventory_asset_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_crm_agreements_phase_id",
        "crm_agreements",
        "project_phases",
        ["phase_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_crm_agreements_inventory_asset_id",
        "crm_agreements",
        "inventory_assets",
        ["inventory_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_crm_agreements_inventory_asset_id", "crm_agreements", type_="foreignkey")
    op.drop_constraint("fk_crm_agreements_phase_id", "crm_agreements", type_="foreignkey")
    op.drop_column("crm_agreements", "inventory_asset_id")
    op.drop_column("crm_agreements", "phase_id")
    op.execute(
        "ALTER TABLE inventory_assets DROP CONSTRAINT IF EXISTS uq_inventory_assets_project_building_phase_display"
    )
    op.create_unique_constraint(
        "uq_inventory_assets_project_building_display",
        "inventory_assets",
        ["project_id", "building_id", "display_id"],
    )
    op.drop_constraint("fk_inventory_assets_phase_id", "inventory_assets", type_="foreignkey")
    op.drop_column("inventory_assets", "phase_id")
    op.drop_index("ix_project_phases_project_id", table_name="project_phases")
    op.drop_table("project_phases")
