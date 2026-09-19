"""CRM agreement participants for joint purchases.

Revision ID: 0075_crm_agreement_participants
Revises: 0074_crm_agreement_investment_amount
Create Date: 2026-09-18

Many-to-many owners on a single agreement. Does not split agreements.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0075_crm_agreement_participants"
down_revision: str | None = "0074_crm_agreement_investment_amount"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_agreement_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agreement_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="owner"),
        sa.Column("ownership_pct", sa.Numeric(7, 2), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="bitrix_live"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agreement_id"], ["crm_agreements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agreement_id", "contact_id", name="uq_crm_agreement_participants_agreement_contact"),
    )
    op.create_index("ix_crm_agreement_participants_agreement_id", "crm_agreement_participants", ["agreement_id"])
    op.create_index("ix_crm_agreement_participants_contact_id", "crm_agreement_participants", ["contact_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_agreement_participants_contact_id", table_name="crm_agreement_participants")
    op.drop_index("ix_crm_agreement_participants_agreement_id", table_name="crm_agreement_participants")
    op.drop_table("crm_agreement_participants")
