"""Hide CRM documents from a surface without deleting files.

Revision ID: 0077_document_link_hidden_from_view
Revises: 0076_crm_agreement_hemen_kira
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0077_document_link_hidden_from_view"
down_revision: str | None = "0076_crm_agreement_hemen_kira"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_links",
        sa.Column("hidden_from_view", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("document_links", "hidden_from_view")
