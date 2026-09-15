"""Add REIT investment_amount on CRM agreements.

Revision ID: 0074_crm_agreement_investment_amount
Revises: 0073_crm_forensic_review_unit
Create Date: 2026-09-14

Store the exact Bitrix Gelir value as a first-class field. REIT is an
investment participation record, not a unit sale.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0074_crm_agreement_investment_amount"
down_revision: str | None = "0073_crm_forensic_review_unit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_agreements",
        sa.Column("investment_amount", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_agreements", "investment_amount")
