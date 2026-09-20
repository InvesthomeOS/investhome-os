"""Add purchase-level Hemen Kira flag.

Revision ID: 0076_crm_agreement_hemen_kira
Revises: 0075_crm_agreement_participants
Create Date: 2026-09-19

Operational lease-immediately flag. Default false. No backfill.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0076_crm_agreement_hemen_kira"
down_revision: str | None = "0075_crm_agreement_participants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_agreements",
        sa.Column("hemen_kira", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("crm_agreements", "hemen_kira")
