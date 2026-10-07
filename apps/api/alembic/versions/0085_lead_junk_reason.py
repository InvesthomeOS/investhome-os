"""Add filterable junk_reason on CRM leads.

Revision ID: 0085_lead_junk_reason
Revises: 0084_lead_investment_budget_currency
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0085_lead_junk_reason"
down_revision: str | None = "0084_lead_investment_budget_currency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("junk_reason", sa.String(length=40), nullable=True))
    op.add_column("leads", sa.Column("junk_reason_detail", sa.String(length=500), nullable=True))
    op.add_column("leads", sa.Column("junked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_leads_junk_reason", "leads", ["junk_reason"])


def downgrade() -> None:
    op.drop_index("ix_leads_junk_reason", table_name="leads")
    op.drop_column("leads", "junked_at")
    op.drop_column("leads", "junk_reason_detail")
    op.drop_column("leads", "junk_reason")
