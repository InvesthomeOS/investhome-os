"""Create expanded activity_logs audit schema.

Revision ID: 0008_expand_activity_logs
Revises: 0007_create_auth
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_expand_activity_logs"
down_revision: str | None = "0007_create_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_activity_logs_event_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("description_key", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("previous_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
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
    op.create_index("ix_activity_logs_actor_user_id", "activity_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_activity_logs_entity_type", "activity_logs", ["entity_type"], unique=False)
    op.create_index("ix_activity_logs_entity_id", "activity_logs", ["entity_id"], unique=False)
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"], unique=False)
    op.create_index(
        "ix_activity_logs_entity_type_entity_id",
        "activity_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_activity_logs_entity_type_entity_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_actor_user_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")

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
    op.create_index("ix_activity_logs_entity_id", "activity_logs", ["entity_id"], unique=False)
    op.create_index("ix_activity_logs_event_type", "activity_logs", ["event_type"], unique=False)
