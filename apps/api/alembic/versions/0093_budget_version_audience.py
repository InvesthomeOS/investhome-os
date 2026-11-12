"""Separate internal and customer budget versions.

Revision ID: 0093_budget_version_audience
Revises: 0092_inventory_phase_unit_uniqueness

Existing versions become internal. Lines, approvals, and version numbers stay.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0093_budget_version_audience"
down_revision: str | None = "0092_inventory_phase_unit_uniqueness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_budget_versions",
        sa.Column(
            "audience",
            sa.String(length=20),
            nullable=False,
            server_default="internal",
        ),
    )
    op.create_index(
        "ix_project_budget_versions_audience",
        "project_budget_versions",
        ["audience"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_budget_versions_audience", table_name="project_budget_versions")
    op.drop_column("project_budget_versions", "audience")
