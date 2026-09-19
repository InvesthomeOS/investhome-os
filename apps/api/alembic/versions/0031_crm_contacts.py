"""CRM contacts table.

Revision ID: 0031_crm_contacts
Revises: 0027_sales_readiness
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_crm_contacts"
down_revision: str | None = "0027_sales_readiness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_type", sa.String(length=40), nullable=False),
        sa.Column("record_kind", sa.String(length=20), server_default="person", nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=True),
        sa.Column("organization_name", sa.String(length=255), nullable=True),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("secondary_emails", sa.JSON(), nullable=True),
        sa.Column("primary_phone", sa.String(length=50), nullable=True),
        sa.Column("secondary_phones", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("investor_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["investor_id"], ["investors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_contacts_contact_type", "crm_contacts", ["contact_type"])
    op.create_index("ix_crm_contacts_status", "crm_contacts", ["status"])
    op.create_index("ix_crm_contacts_owner_user_id", "crm_contacts", ["owner_user_id"])
    op.create_index("ix_crm_contacts_company_id", "crm_contacts", ["company_id"])
    op.create_index("ix_crm_contacts_lead_id", "crm_contacts", ["lead_id"])
    op.create_index("ix_crm_contacts_investor_id", "crm_contacts", ["investor_id"])
    op.create_index("ix_crm_contacts_updated_at", "crm_contacts", ["updated_at"])
    op.create_index("ix_crm_contacts_archived_at", "crm_contacts", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_crm_contacts_archived_at", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_updated_at", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_investor_id", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_lead_id", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_company_id", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_owner_user_id", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_status", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_contact_type", table_name="crm_contacts")
    op.drop_table("crm_contacts")
