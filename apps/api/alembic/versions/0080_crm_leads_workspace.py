"""CRM lead workspace columns for campaign, convert, and ingest.

Revision ID: 0080_crm_leads_workspace
Revises: 0079_crm_tags_lifecycle
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0080_crm_leads_workspace"
down_revision: str | None = "0079_crm_tags_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("campaign", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("provider", sa.String(length=40), nullable=True))
    op.add_column(
        "leads",
        sa.Column("ingest_status", sa.String(length=20), nullable=False, server_default="ok"),
    )
    op.add_column("leads", sa.Column("converted_contact_id", sa.Uuid(), nullable=True))
    op.add_column("leads", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_leads_converted_contact_id",
        "leads",
        "crm_contacts",
        ["converted_contact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_leads_ingest_status", "leads", ["ingest_status"])
    op.create_index("ix_leads_converted_contact_id", "leads", ["converted_contact_id"])
    op.create_index("ix_leads_campaign", "leads", ["campaign"])


def downgrade() -> None:
    op.drop_index("ix_leads_campaign", table_name="leads")
    op.drop_index("ix_leads_converted_contact_id", table_name="leads")
    op.drop_index("ix_leads_ingest_status", table_name="leads")
    op.drop_constraint("fk_leads_converted_contact_id", "leads", type_="foreignkey")
    op.drop_column("leads", "metadata_json")
    op.drop_column("leads", "converted_contact_id")
    op.drop_column("leads", "ingest_status")
    op.drop_column("leads", "provider")
    op.drop_column("leads", "campaign")
