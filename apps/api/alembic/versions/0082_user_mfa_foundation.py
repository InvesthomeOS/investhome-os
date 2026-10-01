"""MFA storage foundation: user_mfa + hashed recovery codes.

Revision ID: 0082_user_mfa_foundation
Revises: 0081_crm_matches_workspace
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0082_user_mfa_foundation"
down_revision: str | None = "0081_crm_matches_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_mfa",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("totp_secret_ciphertext", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("enrollment_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrollment_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_user_mfa_user_id", "user_mfa", ["user_id"], unique=True)

    op.create_table(
        "user_mfa_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_mfa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_mfa.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_user_mfa_recovery_codes_user_mfa_id",
        "user_mfa_recovery_codes",
        ["user_mfa_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_mfa_recovery_codes_user_mfa_id", table_name="user_mfa_recovery_codes")
    op.drop_table("user_mfa_recovery_codes")
    op.drop_index("ix_user_mfa_user_id", table_name="user_mfa")
    op.drop_table("user_mfa")
