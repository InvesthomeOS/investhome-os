"""CRM activity timeline, tasks, notes, and follow-ups.

Revision ID: 0035_crm_activities
Revises: 0034_crm_relationships
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_crm_activities"
down_revision: str | None = "0034_crm_relationships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=40), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(), nullable=True),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("activity_category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("task_status", sa.String(length=30), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_team_id", sa.Uuid(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("meeting_url", sa.String(length=1000), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("follow_up_reason", sa.String(length=40), nullable=True),
        sa.Column("recurrence_frequency", sa.String(length=20), nullable=True),
        sa.Column("recurrence_rule", sa.String(length=500), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_activities_entity", "crm_activities", ["entity_type", "entity_id"])
    op.create_index("ix_crm_activities_type", "crm_activities", ["activity_type"])
    op.create_index("ix_crm_activities_status", "crm_activities", ["status"])
    op.create_index("ix_crm_activities_due_date", "crm_activities", ["due_date"])
    op.create_index("ix_crm_activities_start_date", "crm_activities", ["start_date"])
    op.create_index("ix_crm_activities_owner", "crm_activities", ["owner_id"])
    op.create_index("ix_crm_activities_assigned", "crm_activities", ["assigned_user_id"])
    op.create_index("ix_crm_activities_created_at", "crm_activities", ["created_at"])
    op.create_index("ix_crm_activities_archived", "crm_activities", ["archived_at"])

    op.create_table(
        "crm_activity_entity_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_activity_entity_links_entity",
        "crm_activity_entity_links",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "crm_activity_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", sa.JSON(), nullable=True),
        sa.Column("reactions", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["crm_activity_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_activity_checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_by", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_activity_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_url", sa.String(length=2000), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_activity_reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offset_minutes", sa.Integer(), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_follow_up_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("trigger_activity_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_status", sa.String(length=30), nullable=True),
        sa.Column("follow_up_reason", sa.String(length=40), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default=sa.text("7")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_activity_saved_filters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("filter_logic", sa.String(length=10), nullable=False, server_default=sa.text("'and'")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.bulk_insert(
        sa.table(
            "crm_follow_up_rules",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("trigger_activity_type", sa.String()),
            sa.column("trigger_status", sa.String()),
            sa.column("follow_up_reason", sa.String()),
            sa.column("delay_days", sa.Integer()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "name": "Meeting completed follow-up",
                "trigger_activity_type": "meeting",
                "trigger_status": "completed",
                "follow_up_reason": "relationship_review",
                "delay_days": 7,
                "is_active": True,
            },
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "name": "Proposal sent follow-up",
                "trigger_activity_type": "proposal_sent",
                "trigger_status": "completed",
                "follow_up_reason": "opportunity",
                "delay_days": 3,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("crm_activity_saved_filters")
    op.drop_table("crm_follow_up_rules")
    op.drop_table("crm_activity_reminders")
    op.drop_table("crm_activity_attachments")
    op.drop_table("crm_activity_checklist_items")
    op.drop_table("crm_activity_comments")
    op.drop_index("ix_crm_activity_entity_links_entity", table_name="crm_activity_entity_links")
    op.drop_table("crm_activity_entity_links")
    op.drop_index("ix_crm_activities_archived", table_name="crm_activities")
    op.drop_index("ix_crm_activities_created_at", table_name="crm_activities")
    op.drop_index("ix_crm_activities_assigned", table_name="crm_activities")
    op.drop_index("ix_crm_activities_owner", table_name="crm_activities")
    op.drop_index("ix_crm_activities_start_date", table_name="crm_activities")
    op.drop_index("ix_crm_activities_due_date", table_name="crm_activities")
    op.drop_index("ix_crm_activities_status", table_name="crm_activities")
    op.drop_index("ix_crm_activities_type", table_name="crm_activities")
    op.drop_index("ix_crm_activities_entity", table_name="crm_activities")
    op.drop_table("crm_activities")
