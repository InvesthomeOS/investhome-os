"""Merge Alembic heads: company documents + CRM contacts.

Revision ID: 0032_merge_heads
Revises: 0031_crm_contacts, 0031_company_documents
Create Date: 2026-07-16

"""

from collections.abc import Sequence

revision: str = "0032_merge_heads"
down_revision: str | tuple[str, ...] | None = ("0031_crm_contacts", "0031_company_documents")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
