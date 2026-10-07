"""Add currency for lead estimated / investment budget.

Revision ID: 0084_lead_investment_budget_currency
Revises: 0083_user_invitations
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0084_lead_investment_budget_currency"
down_revision: str | None = "0083_user_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("estimated_budget_currency", sa.String(length=3), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "estimated_budget_currency")
