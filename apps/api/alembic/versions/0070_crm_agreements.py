"""CRM agreements table for historical Bitrix Anlaşmalar.

Revision ID: 0070_crm_agreements
Revises: 0037_crm_search
Create Date: 2026-09-03

Additive only. CRM-owned agreements are distinct from Sales opportunities.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0070_crm_agreements"
down_revision: str | None = "0037_crm_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_agreements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("project_group", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="bitrix"),
        sa.Column("source_external_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("agreement_date", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_external_id", name="uq_crm_agreements_source_external_id"),
    )
    op.create_index("ix_crm_agreements_contact_id", "crm_agreements", ["contact_id"])
    op.create_index("ix_crm_agreements_project_id", "crm_agreements", ["project_id"])
    op.create_index("ix_crm_agreements_project_group", "crm_agreements", ["project_group"])
    op.create_index("ix_crm_agreements_status", "crm_agreements", ["status"])


def downgrade() -> None:
    op.drop_index("ix_crm_agreements_status", table_name="crm_agreements")
    op.drop_index("ix_crm_agreements_project_group", table_name="crm_agreements")
    op.drop_index("ix_crm_agreements_project_id", table_name="crm_agreements")
    op.drop_index("ix_crm_agreements_contact_id", table_name="crm_agreements")
    op.drop_table("crm_agreements")
