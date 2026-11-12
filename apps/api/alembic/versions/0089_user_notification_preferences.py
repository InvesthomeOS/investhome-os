"""User notification preferences and delivery dedupe.

Revision ID: 0089_user_notification_preferences
Revises: 0088_inventory_identity_sales_market
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0089_user_notification_preferences"
down_revision: str | None = "0088_inventory_identity_sales_market"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_key", name="uq_user_notification_pref_event"),
    )
    op.create_index(
        "ix_user_notification_preferences_user_id",
        "user_notification_preferences",
        ["user_id"],
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("dedupe_key", sa.String(length=220), nullable=False),
        sa.Column("in_app_status", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("email_status", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_user_id", "dedupe_key", name="uq_notification_delivery_dedupe"),
    )
    op.create_index(
        "ix_notification_deliveries_recipient_user_id",
        "notification_deliveries",
        ["recipient_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_recipient_user_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_index("ix_user_notification_preferences_user_id", table_name="user_notification_preferences")
    op.drop_table("user_notification_preferences")
