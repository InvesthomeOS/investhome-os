"""Work items — tasks, meetings, follow-ups.

Revision ID: 0026_work_items
Revises: 0025_sales_proposals
Create Date: 2026-07-16

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0026_work_items"
down_revision: str | None = "0025_sales_proposals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("work_item_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'open'"), nullable=False),
        sa.Column("priority", sa.String(length=20), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_entity_type", sa.String(length=30), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=True),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("next_action_type", sa.String(length=50), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("legacy_lead_follow_up_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_items_due_at", "work_items", ["due_at"])
    op.create_index("ix_work_items_assigned_user_id", "work_items", ["assigned_user_id"])
    op.create_index("ix_work_items_opportunity_id", "work_items", ["opportunity_id"])
    op.create_index("ix_work_items_lead_id", "work_items", ["lead_id"])
    op.create_index("ix_work_items_status", "work_items", ["status"])
    op.create_index(
        "ix_work_items_active_assigned_due",
        "work_items",
        ["assigned_user_id", "due_at", "archived_at"],
    )
    op.create_index(
        "ix_work_items_active_partial",
        "work_items",
        ["assigned_user_id", "due_at"],
        postgresql_where=sa.text(
            "archived_at IS NULL AND status NOT IN ('completed', 'cancelled', 'archived')"
        ),
    )

    op.create_table(
        "meeting_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_type", sa.String(length=20), server_default=sa.text("'video'"), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("meeting_url", sa.String(length=500), nullable=True),
        sa.Column("agenda", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("decision_summary", sa.Text(), nullable=True),
        sa.Column("next_steps", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_item_id"),
    )
    op.create_index("ix_meeting_records_work_item_id", "meeting_records", ["work_item_id"], unique=True)

    op.create_table(
        "follow_up_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column("follow_up_type", sa.String(length=50), nullable=False),
        sa.Column("contact_method", sa.String(length=20), server_default=sa.text("'call'"), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=True),
        sa.Column("response_status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_item_id"),
    )
    op.create_index("ix_follow_up_records_work_item_id", "follow_up_records", ["work_item_id"], unique=True)

    op.create_table(
        "work_item_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("participant_role", sa.String(length=20), server_default=sa.text("'attendee'"), nullable=False),
        sa.Column("attendance_status", sa.String(length=20), server_default=sa.text("'invited'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_item_participants_work_item_id", "work_item_participants", ["work_item_id"])

    op.create_table(
        "work_item_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_item_status_history_work_item_id", "work_item_status_history", ["work_item_id"])

    conn = op.get_bind()
    follow_ups = conn.execute(
        sa.text(
            """
            SELECT id, lead_id, follow_up_type, due_at, completed_at,
                   assigned_user_id, notes, status, created_at, updated_at
            FROM lead_follow_ups
            """
        )
    ).fetchall()

    type_map = {
        "call": "call",
        "email": "follow_up",
        "meeting": "meeting",
        "whatsapp": "follow_up",
        "site_visit": "site_visit",
        "other": "other",
    }
    status_map = {
        "pending": "open",
        "completed": "completed",
        "cancelled": "cancelled",
        "overdue": "open",
    }

    for row in follow_ups:
        conn.execute(
            sa.text(
                """
                INSERT INTO work_items (
                    id, title, work_item_type, status, priority,
                    assigned_user_id, due_at, completed_at, lead_id,
                    related_entity_type, related_entity_id, description,
                    legacy_lead_follow_up_id, created_at, updated_at
                ) VALUES (
                    :id, :title, :work_item_type, :status, 'medium',
                    :assigned_user_id, :due_at, :completed_at, :lead_id,
                    'lead', :lead_id, :notes,
                    :legacy_id, :created_at, :updated_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "title": f"Lead follow-up ({row.follow_up_type})",
                "work_item_type": type_map.get(row.follow_up_type, "follow_up"),
                "status": status_map.get(row.status, "open"),
                "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
                "due_at": row.due_at,
                "completed_at": row.completed_at,
                "lead_id": str(row.lead_id),
                "notes": row.notes,
                "legacy_id": str(row.id),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_work_item_status_history_work_item_id", table_name="work_item_status_history")
    op.drop_table("work_item_status_history")
    op.drop_index("ix_work_item_participants_work_item_id", table_name="work_item_participants")
    op.drop_table("work_item_participants")
    op.drop_index("ix_follow_up_records_work_item_id", table_name="follow_up_records")
    op.drop_table("follow_up_records")
    op.drop_index("ix_meeting_records_work_item_id", table_name="meeting_records")
    op.drop_table("meeting_records")
    op.drop_index("ix_work_items_active_partial", table_name="work_items")
    op.drop_index("ix_work_items_active_assigned_due", table_name="work_items")
    op.drop_index("ix_work_items_status", table_name="work_items")
    op.drop_index("ix_work_items_lead_id", table_name="work_items")
    op.drop_index("ix_work_items_opportunity_id", table_name="work_items")
    op.drop_index("ix_work_items_assigned_user_id", table_name="work_items")
    op.drop_index("ix_work_items_due_at", table_name="work_items")
    op.drop_table("work_items")
