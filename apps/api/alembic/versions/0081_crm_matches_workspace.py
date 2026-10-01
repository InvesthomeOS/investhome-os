"""CRM matches review columns on duplicate candidates.

Revision ID: 0081_crm_matches_workspace
Revises: 0080_crm_leads_workspace
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0081_crm_matches_workspace"
down_revision: str | None = "0080_crm_leads_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("match_kind", sa.String(length=20), nullable=False, server_default="possible"),
    )
    op.add_column("crm_contact_duplicate_candidates", sa.Column("source", sa.String(length=80), nullable=True))
    op.add_column("crm_contact_duplicate_candidates", sa.Column("evidence_json", sa.JSON(), nullable=True))
    op.add_column("crm_contact_duplicate_candidates", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("protected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("protected_reason", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("merge_queued", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("crm_contact_duplicate_candidates", sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_contact_duplicate_candidates",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_foreign_key(
        "fk_crm_dup_candidates_reviewed_by",
        "crm_contact_duplicate_candidates",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        DELETE FROM crm_contact_duplicate_candidates a
        USING crm_contact_duplicate_candidates b
        WHERE a.contact_id_a = b.contact_id_a
          AND a.contact_id_b = b.contact_id_b
          AND a.id > b.id
        """
    )
    op.execute(
        """
        UPDATE crm_contact_duplicate_candidates
        SET contact_id_a = contact_id_b, contact_id_b = contact_id_a
        WHERE contact_id_a > contact_id_b
        """
    )
    op.create_index(
        "ix_crm_dup_candidates_status",
        "crm_contact_duplicate_candidates",
        ["status"],
    )
    op.create_unique_constraint(
        "uq_crm_dup_candidates_pair",
        "crm_contact_duplicate_candidates",
        ["contact_id_a", "contact_id_b"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_crm_dup_candidates_pair", "crm_contact_duplicate_candidates", type_="unique")
    op.drop_index("ix_crm_dup_candidates_status", table_name="crm_contact_duplicate_candidates")
    op.drop_constraint("fk_crm_dup_candidates_reviewed_by", "crm_contact_duplicate_candidates", type_="foreignkey")
    op.drop_column("crm_contact_duplicate_candidates", "updated_at")
    op.drop_column("crm_contact_duplicate_candidates", "reviewed_at")
    op.drop_column("crm_contact_duplicate_candidates", "reviewed_by_user_id")
    op.drop_column("crm_contact_duplicate_candidates", "merge_queued")
    op.drop_column("crm_contact_duplicate_candidates", "protected_reason")
    op.drop_column("crm_contact_duplicate_candidates", "protected")
    op.drop_column("crm_contact_duplicate_candidates", "review_notes")
    op.drop_column("crm_contact_duplicate_candidates", "evidence_json")
    op.drop_column("crm_contact_duplicate_candidates", "source")
    op.drop_column("crm_contact_duplicate_candidates", "match_kind")
