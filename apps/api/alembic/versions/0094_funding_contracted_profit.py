"""Store investor contracted profit on the existing commitment.

Revision ID: 0094_funding_contracted_profit
Revises: 0093_budget_version_audience

The amount uses the commitment currency. Null means it was not entered.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0094_funding_contracted_profit"
down_revision: str | None = "0093_budget_version_audience"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "funding_commitments",
        sa.Column("contracted_profit", sa.Numeric(precision=16, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("funding_commitments", "contracted_profit")
