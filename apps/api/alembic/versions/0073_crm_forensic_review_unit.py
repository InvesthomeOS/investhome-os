"""Add review_required and agreement unit_number for Bitrix forensic repair.

Revision ID: 0073_crm_forensic_review_unit
Revises: 0072_crm_contact_junk_reason
Create Date: 2026-09-10

Preserve uncertain Bitrix source rows as İnceleme Gerekli and store
agreement unit/apartment numbers as a first-class field.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0073_crm_forensic_review_unit"
down_revision: str | None = "0072_crm_contact_junk_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_contacts",
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_crm_contacts_review_required", "crm_contacts", ["review_required"])
    op.add_column(
        "crm_agreements",
        sa.Column("unit_number", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "crm_agreements",
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_crm_agreements_review_required", "crm_agreements", ["review_required"])


def downgrade() -> None:
    op.drop_index("ix_crm_agreements_review_required", table_name="crm_agreements")
    op.drop_column("crm_agreements", "review_required")
    op.drop_column("crm_agreements", "unit_number")
    op.drop_index("ix_crm_contacts_review_required", table_name="crm_contacts")
    op.drop_column("crm_contacts", "review_required")
