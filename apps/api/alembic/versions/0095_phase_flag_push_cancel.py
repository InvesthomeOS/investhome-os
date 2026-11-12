"""Project phase flag, browser push subscriptions, agreement cancellation.

Revision ID: 0095_phase_flag_push_cancel
Revises: 0094_funding_contracted_profit

Not applied by this change. Existing rows stay phase-less until a user
marks the project as phased. Cancellation columns preserve the agreement.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0095_phase_flag_push_cancel"
down_revision: str | None = "0094_funding_contracted_profit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("uses_phases", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "user_push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(length=1000), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "endpoint", name="uq_user_push_subscription_endpoint"),
    )
    op.create_index("ix_user_push_subscriptions_user_id", "user_push_subscriptions", ["user_id"])
    op.add_column("crm_agreements", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_agreements", sa.Column("cancellation_reason", sa.String(length=255), nullable=True))
    op.add_column("crm_agreements", sa.Column("cancellation_note", sa.String(length=2000), nullable=True))
    op.add_column("crm_agreements", sa.Column("cancelled_by", sa.Uuid(), nullable=True))
    op.add_column("crm_agreements", sa.Column("pipeline_return_stage", sa.String(length=40), nullable=True))
    op.add_column("crm_agreements", sa.Column("pipeline_returned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_crm_agreements_cancelled_by_users",
        "crm_agreements",
        "users",
        ["cancelled_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_crm_agreements_cancelled_by_users", "crm_agreements", type_="foreignkey")
    op.drop_column("crm_agreements", "pipeline_returned_at")
    op.drop_column("crm_agreements", "pipeline_return_stage")
    op.drop_column("crm_agreements", "cancelled_by")
    op.drop_column("crm_agreements", "cancellation_note")
    op.drop_column("crm_agreements", "cancellation_reason")
    op.drop_column("crm_agreements", "cancelled_at")
    op.drop_index("ix_user_push_subscriptions_user_id", table_name="user_push_subscriptions")
    op.drop_table("user_push_subscriptions")
    op.drop_column("projects", "uses_phases")
