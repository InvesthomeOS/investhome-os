"""Marketing automation foundation — workflows, executions, templates, versions.

Revision ID: 0045_marketing_automation
Revises: 0044_mkt_analytics_fnd
Create Date: 2026-07-16

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0045_marketing_automation"
down_revision: str | None = "0044_mkt_analytics_fnd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEMPLATE_SEED = [
    ("new_lead", "New Lead Welcome", "new_lead", "Automated welcome sequence for new marketing leads.", True),
    ("investor_lead", "Investor Lead Nurture", "investor_lead", "Investor lead qualification and nurture journey.", True),
    ("buyer_lead", "Buyer Lead Follow-up", "buyer_lead", "Follow-up workflow for buyer leads.", True),
    ("broker_lead", "Broker Lead Onboarding", "broker_lead", "Broker lead onboarding and assignment.", True),
    ("reservation_followup", "Reservation Follow-up", "reservation_followup", "Post-reservation follow-up sequence.", False),
    ("meeting_reminder", "Meeting Reminder", "meeting_reminder", "Automated meeting reminder notifications.", False),
    ("event_registration", "Event Registration", "event_registration", "Event registration confirmation journey.", True),
    ("newsletter_journey", "Newsletter Journey", "newsletter_journey", "Newsletter subscription welcome journey.", True),
    ("welcome_journey", "Welcome Journey", "welcome_journey", "General welcome journey for new contacts.", True),
]


def upgrade() -> None:
    op.create_table(
        "marketing_automation_workflows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "pending_approval",
                "approved",
                "active",
                "paused",
                "disabled",
                "archived",
                name="marketing_automation_workflow_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trigger_json", sa.JSON(), nullable=True),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("actions_json", sa.JSON(), nullable=True),
        sa.Column("journey_graph_json", sa.JSON(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("is_journey", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_marketing_automation_workflows_status", "marketing_automation_workflows", ["status"])
    op.create_index("ix_marketing_automation_workflows_owner", "marketing_automation_workflows", ["owner_user_id"])

    op.create_table(
        "marketing_automation_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                "skipped",
                "not_connected",
                name="marketing_automation_execution_status",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("trigger_type", sa.String(length=80), nullable=True),
        sa.Column("trigger_context_json", sa.JSON(), nullable=True),
        sa.Column("actions_executed_json", sa.JSON(), nullable=True),
        sa.Column("actions_skipped_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["marketing_automation_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_automation_executions_workflow", "marketing_automation_executions", ["workflow_id"])
    op.create_index("ix_marketing_automation_executions_status", "marketing_automation_executions", ["status"])

    op.create_table(
        "marketing_automation_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "new_lead",
                "investor_lead",
                "buyer_lead",
                "broker_lead",
                "reservation_followup",
                "meeting_reminder",
                "event_registration",
                "newsletter_journey",
                "welcome_journey",
                "custom",
                name="marketing_automation_template_category",
            ),
            nullable=False,
            server_default="custom",
        ),
        sa.Column("trigger_json", sa.JSON(), nullable=True),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("actions_json", sa.JSON(), nullable=True),
        sa.Column("journey_graph_json", sa.JSON(), nullable=True),
        sa.Column("is_journey", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "marketing_automation_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["marketing_automation_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_automation_versions_workflow", "marketing_automation_versions", ["workflow_id"])

    template_category_enum = sa.Enum(
        "new_lead",
        "investor_lead",
        "buyer_lead",
        "broker_lead",
        "reservation_followup",
        "meeting_reminder",
        "event_registration",
        "newsletter_journey",
        "welcome_journey",
        "custom",
        name="marketing_automation_template_category",
        create_type=False,
    )
    templates = sa.table(
        "marketing_automation_templates",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("category", template_category_enum),
        sa.column("trigger_json", sa.JSON()),
        sa.column("conditions_json", sa.JSON()),
        sa.column("actions_json", sa.JSON()),
        sa.column("journey_graph_json", sa.JSON()),
        sa.column("is_journey", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        templates,
        [
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "code": code,
                "description": desc,
                "category": category,
                "trigger_json": {"type": "lead_created"},
                "conditions_json": [],
                "actions_json": [{"type": "notify_team", "config": {}}],
                "journey_graph_json": {
                    "nodes": [
                        {"id": "trigger-1", "type": "trigger", "label": "Trigger", "x": 100, "y": 80},
                        {"id": "action-1", "type": "action", "label": "Notify Team", "x": 100, "y": 220},
                        {"id": "end-1", "type": "end", "label": "End", "x": 100, "y": 360},
                    ],
                    "edges": [
                        {"id": "e1", "source": "trigger-1", "target": "action-1"},
                        {"id": "e2", "source": "action-1", "target": "end-1"},
                    ],
                }
                if is_journey
                else None,
                "is_journey": is_journey,
                "is_active": True,
            }
            for code, name, category, desc, is_journey in TEMPLATE_SEED
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_automation_versions_workflow", table_name="marketing_automation_versions")
    op.drop_table("marketing_automation_versions")
    op.drop_table("marketing_automation_templates")
    op.drop_index("ix_marketing_automation_executions_status", table_name="marketing_automation_executions")
    op.drop_index("ix_marketing_automation_executions_workflow", table_name="marketing_automation_executions")
    op.drop_table("marketing_automation_executions")
    op.drop_index("ix_marketing_automation_workflows_owner", table_name="marketing_automation_workflows")
    op.drop_index("ix_marketing_automation_workflows_status", table_name="marketing_automation_workflows")
    op.drop_table("marketing_automation_workflows")
    op.execute("DROP TYPE IF EXISTS marketing_automation_template_category")
    op.execute("DROP TYPE IF EXISTS marketing_automation_execution_status")
    op.execute("DROP TYPE IF EXISTS marketing_automation_workflow_status")
