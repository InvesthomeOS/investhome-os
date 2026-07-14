"""Create activity_logs table.

Revision ID: 0006_create_activity_logs
Revises: 0005_create_finance
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_create_activity_logs"
down_revision: str | None = "0005_create_finance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("description_key", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"], unique=False)
    op.create_index("ix_activity_logs_entity_type", "activity_logs", ["entity_type"], unique=False)
    op.create_index(
        "ix_activity_logs_entity_id",
        "activity_logs",
        ["entity_id"],
        unique=False,
    )
    op.create_index("ix_activity_logs_event_type", "activity_logs", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_logs_event_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")
