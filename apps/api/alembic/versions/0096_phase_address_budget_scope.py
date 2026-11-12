"""Phase address and phase-scoped budget and funding rows.

Revision ID: 0096_phase_address_budget_scope
Revises: 0095_phase_flag_push_cancel

Not applied by this change. Existing budget versions and funding
commitments stay project-level (phase_id NULL). Existing phase rows
keep a null address. Version numbers stay unique per project.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0096_phase_address_budget_scope"
down_revision: str | None = "0095_phase_flag_push_cancel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("project_phases", sa.Column("address_line", sa.String(length=255), nullable=True))
    op.add_column("project_phases", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("project_phases", sa.Column("region", sa.String(length=80), nullable=True))
    op.add_column("project_phases", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("project_budget_versions", sa.Column("phase_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_project_budget_versions_phase_id",
        "project_budget_versions",
        ["phase_id"],
    )
    op.create_foreign_key(
        "fk_project_budget_versions_phase_id",
        "project_budget_versions",
        "project_phases",
        ["phase_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("funding_commitments", sa.Column("phase_id", sa.Uuid(), nullable=True))
    op.create_index("ix_funding_commitments_phase_id", "funding_commitments", ["phase_id"])
    op.create_foreign_key(
        "fk_funding_commitments_phase_id",
        "funding_commitments",
        "project_phases",
        ["phase_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_funding_commitments_phase_id", "funding_commitments", type_="foreignkey")
    op.drop_index("ix_funding_commitments_phase_id", table_name="funding_commitments")
    op.drop_column("funding_commitments", "phase_id")
    op.drop_constraint(
        "fk_project_budget_versions_phase_id", "project_budget_versions", type_="foreignkey"
    )
    op.drop_index("ix_project_budget_versions_phase_id", table_name="project_budget_versions")
    op.drop_column("project_budget_versions", "phase_id")
    op.drop_column("project_phases", "postal_code")
    op.drop_column("project_phases", "region")
    op.drop_column("project_phases", "city")
    op.drop_column("project_phases", "address_line")
