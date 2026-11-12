"""Optional project, phase, and unit links on leads.

Revision ID: 0091_lead_phase_links
Revises: 0090_project_phases

Does not copy phase names onto leads and does not rewrite agreements.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0091_lead_phase_links"
down_revision: str | None = "0090_project_phases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column("leads", sa.Column("phase_id", sa.Uuid(), nullable=True))
    op.add_column("leads", sa.Column("inventory_asset_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_leads_project_id", "leads", "projects", ["project_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(
        "fk_leads_phase_id", "leads", "project_phases", ["phase_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_leads_inventory_asset_id",
        "leads",
        "inventory_assets",
        ["inventory_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_leads_project_id", "leads", ["project_id"])
    op.create_index("ix_leads_phase_id", "leads", ["phase_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_phase_id", table_name="leads")
    op.drop_index("ix_leads_project_id", table_name="leads")
    op.drop_constraint("fk_leads_inventory_asset_id", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_phase_id", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_project_id", "leads", type_="foreignkey")
    op.drop_column("leads", "inventory_asset_id")
    op.drop_column("leads", "phase_id")
    op.drop_column("leads", "project_id")
