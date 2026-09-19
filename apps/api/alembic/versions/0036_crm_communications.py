"""CRM communications, threads, templates, sequences, and preferences.

Revision ID: 0036_crm_communications
Revises: 0035_crm_activities
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_crm_communications"
down_revision: str | None = "0035_crm_activities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_communication_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=True),
        sa.Column("participant_ids", sa.JSON(), nullable=True),
        sa.Column("related_entity_ids", sa.JSON(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_team_id", sa.Uuid(), nullable=True),
        sa.Column("last_communication_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'open'")),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("follow_up_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_time_seconds", sa.Integer(), nullable=True),
        sa.Column("sentiment", sa.String(length=30), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_comm_threads_status", "crm_communication_threads", ["status"])
    op.create_index("ix_crm_comm_threads_owner", "crm_communication_threads", ["owner_id"])
    op.create_index("ix_crm_comm_threads_assigned", "crm_communication_threads", ["assigned_user_id"])
    op.create_index("ix_crm_comm_threads_last_comm", "crm_communication_threads", ["last_communication_at"])
    op.create_index("ix_crm_comm_threads_archived", "crm_communication_threads", ["archived_at"])

    op.create_table(
        "crm_communications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("preview", sa.String(length=1000), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("sender_entity_type", sa.String(length=40), nullable=True),
        sa.Column("sender_entity_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_entity_type", sa.String(length=40), nullable=True),
        sa.Column("recipient_entity_id", sa.Uuid(), nullable=True),
        sa.Column("recipients", sa.JSON(), nullable=True),
        sa.Column("cc_recipients", sa.JSON(), nullable=True),
        sa.Column("bcc_recipients", sa.JSON(), nullable=True),
        sa.Column("participants", sa.JSON(), nullable=True),
        sa.Column("related_entities", sa.JSON(), nullable=True),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("parent_communication_id", sa.Uuid(), nullable=True),
        sa.Column("external_provider_id", sa.String(length=255), nullable=True),
        sa.Column("provider_thread_id", sa.String(length=255), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default=sa.text("'organization'")),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_team_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("call_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("call_outcome", sa.String(length=50), nullable=True),
        sa.Column("call_direction", sa.String(length=20), nullable=True),
        sa.Column("meeting_url", sa.String(length=1000), nullable=True),
        sa.Column("meeting_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meeting_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["crm_activities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_communication_id"], ["crm_communications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["crm_communication_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_communications_thread", "crm_communications", ["thread_id"])
    op.create_index("ix_crm_communications_channel", "crm_communications", ["channel"])
    op.create_index("ix_crm_communications_status", "crm_communications", ["status"])
    op.create_index("ix_crm_communications_direction", "crm_communications", ["direction"])
    op.create_index("ix_crm_communications_owner", "crm_communications", ["owner_id"])
    op.create_index("ix_crm_communications_scheduled", "crm_communications", ["scheduled_at"])
    op.create_index("ix_crm_communications_sent", "crm_communications", ["sent_at"])
    op.create_index("ix_crm_communications_archived", "crm_communications", ["archived_at"])
    op.create_index(
        "ix_crm_communications_recipient",
        "crm_communications",
        ["recipient_entity_type", "recipient_entity_id"],
    )

    op.create_table(
        "crm_communication_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("communication_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["communication_id"], ["crm_communications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_communication_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_type", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_communication_signatures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=True),
        sa.Column("scope", sa.String(length=30), nullable=False, server_default=sa.text("'personal'")),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_communication_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enrollment_type", sa.String(length=30), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_communication_sequence_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("step_type", sa.String(length=40), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("wait_days", sa.Integer(), nullable=True),
        sa.Column("wait_hours", sa.Integer(), nullable=True),
        sa.Column("condition_json", sa.JSON(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sequence_id"], ["crm_communication_sequences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["crm_communication_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_communication_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_channel", sa.String(length=40), nullable=True),
        sa.Column("allowed_channels", sa.JSON(), nullable=True),
        sa.Column("blocked_channels", sa.JSON(), nullable=True),
        sa.Column("consent_email", sa.Boolean(), nullable=True),
        sa.Column("consent_sms", sa.Boolean(), nullable=True),
        sa.Column("consent_whatsapp", sa.Boolean(), nullable=True),
        sa.Column("consent_phone", sa.Boolean(), nullable=True),
        sa.Column("do_not_contact", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("do_not_contact_reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_comm_prefs_entity",
        "crm_communication_preferences",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "crm_communication_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("communication_id", sa.Uuid(), nullable=True),
        sa.Column("thread_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_comm_audit_comm", "crm_communication_audit_logs", ["communication_id"])
    op.create_index("ix_crm_comm_audit_thread", "crm_communication_audit_logs", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_comm_audit_thread", table_name="crm_communication_audit_logs")
    op.drop_index("ix_crm_comm_audit_comm", table_name="crm_communication_audit_logs")
    op.drop_table("crm_communication_audit_logs")
    op.drop_index("ix_crm_comm_prefs_entity", table_name="crm_communication_preferences")
    op.drop_table("crm_communication_preferences")
    op.drop_table("crm_communication_sequence_steps")
    op.drop_table("crm_communication_sequences")
    op.drop_table("crm_communication_signatures")
    op.drop_table("crm_communication_templates")
    op.drop_table("crm_communication_attachments")
    op.drop_index("ix_crm_communications_recipient", table_name="crm_communications")
    op.drop_index("ix_crm_communications_archived", table_name="crm_communications")
    op.drop_index("ix_crm_communications_sent", table_name="crm_communications")
    op.drop_index("ix_crm_communications_scheduled", table_name="crm_communications")
    op.drop_index("ix_crm_communications_owner", table_name="crm_communications")
    op.drop_index("ix_crm_communications_direction", table_name="crm_communications")
    op.drop_index("ix_crm_communications_status", table_name="crm_communications")
    op.drop_index("ix_crm_communications_channel", table_name="crm_communications")
    op.drop_index("ix_crm_communications_thread", table_name="crm_communications")
    op.drop_table("crm_communications")
    op.drop_index("ix_crm_comm_threads_archived", table_name="crm_communication_threads")
    op.drop_index("ix_crm_comm_threads_last_comm", table_name="crm_communication_threads")
    op.drop_index("ix_crm_comm_threads_assigned", table_name="crm_communication_threads")
    op.drop_index("ix_crm_comm_threads_owner", table_name="crm_communication_threads")
    op.drop_index("ix_crm_comm_threads_status", table_name="crm_communication_threads")
    op.drop_table("crm_communication_threads")
