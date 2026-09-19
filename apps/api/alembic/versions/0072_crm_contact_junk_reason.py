"""Add filterable junk_reason on CRM contacts.

Revision ID: 0072_crm_contact_junk_reason
Revises: 0071_sales_opportunity_crm_contact
Create Date: 2026-09-09

First-class Junk Sebebi field so contacts can be filtered by the original
Bitrix reason without inferring or rewriting the source value.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0072_crm_contact_junk_reason"
down_revision: str | None = "0071_sales_opportunity_crm_contact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_contacts",
        sa.Column("junk_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "crm_contacts",
        sa.Column("junked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_crm_contacts_junk_reason", "crm_contacts", ["junk_reason"])


def downgrade() -> None:
    op.drop_index("ix_crm_contacts_junk_reason", table_name="crm_contacts")
    op.drop_column("crm_contacts", "junked_at")
    op.drop_column("crm_contacts", "junk_reason")
