"""Add crm_contact_id to sales opportunities.

Revision ID: 0071_sales_opportunity_crm_contact
Revises: 0070_crm_agreements
Create Date: 2026-09-08

Smallest Sales → CRM relationship so historical Bitrix pipeline rows can
reference canonical CrmContact without creating a second person identity.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0071_sales_opportunity_crm_contact"
down_revision: str | None = "0070_crm_agreements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sales_opportunities",
        sa.Column("crm_contact_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_sales_opportunities_crm_contact_id",
        "sales_opportunities",
        ["crm_contact_id"],
    )
    op.create_foreign_key(
        "fk_sales_opportunities_crm_contact_id",
        "sales_opportunities",
        "crm_contacts",
        ["crm_contact_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sales_opportunities_crm_contact_id",
        "sales_opportunities",
        type_="foreignkey",
    )
    op.drop_index("ix_sales_opportunities_crm_contact_id", table_name="sales_opportunities")
    op.drop_column("sales_opportunities", "crm_contact_id")
