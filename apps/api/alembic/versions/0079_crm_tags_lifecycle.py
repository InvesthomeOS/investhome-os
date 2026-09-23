"""CRM tag description, status, audit events, and assignment timestamps.

Revision ID: 0079_crm_tags_lifecycle
Revises: 0078_live_communication_foundation
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0079_crm_tags_lifecycle"
down_revision: str | None = "0078_live_communication_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_tags", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "crm_tags",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "crm_tags",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("crm_tags", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.add_column("crm_tags", sa.Column("updated_by", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_crm_tags_created_by", "crm_tags", "users", ["created_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_crm_tags_updated_by", "crm_tags", "users", ["updated_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_crm_tags_status", "crm_tags", ["status"])

    op.add_column(
        "crm_contact_tags",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("crm_contact_tags", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_crm_contact_tags_created_by",
        "crm_contact_tags",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "crm_tag_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["crm_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_tag_events_tag_id", "crm_tag_events", ["tag_id"])
    op.create_index("ix_crm_tag_events_created_at", "crm_tag_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_crm_tag_events_created_at", table_name="crm_tag_events")
    op.drop_index("ix_crm_tag_events_tag_id", table_name="crm_tag_events")
    op.drop_table("crm_tag_events")
    op.drop_constraint("fk_crm_contact_tags_created_by", "crm_contact_tags", type_="foreignkey")
    op.drop_column("crm_contact_tags", "created_by")
    op.drop_column("crm_contact_tags", "created_at")
    op.drop_index("ix_crm_tags_status", table_name="crm_tags")
    op.drop_constraint("fk_crm_tags_updated_by", "crm_tags", type_="foreignkey")
    op.drop_constraint("fk_crm_tags_created_by", "crm_tags", type_="foreignkey")
    op.drop_column("crm_tags", "updated_by")
    op.drop_column("crm_tags", "created_by")
    op.drop_column("crm_tags", "updated_at")
    op.drop_column("crm_tags", "status")
    op.drop_column("crm_tags", "description")
