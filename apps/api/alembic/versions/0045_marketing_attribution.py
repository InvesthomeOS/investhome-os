"""Multi-touch attribution engine — migration 0045.

Revision ID: 0045_marketing_attribution
Revises: 0044_mkt_analytics_fnd
Create Date: 2026-07-16

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0045_marketing_attribution"
down_revision: str | None = "0044_mkt_analytics_fnd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_MODELS = [
    ("First Touch", "first_touch", True),
    ("Last Touch", "last_touch", False),
    ("Linear", "linear", False),
    ("Position Based", "position_based", False),
    ("Time Decay", "time_decay", False),
    ("Data Driven", "data_driven", False),
]


def upgrade() -> None:
    op.create_table(
        "marketing_touchpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("anonymous_visitor_id", sa.String(length=255), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("landing_page_id", sa.Uuid(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("conversion_event_id", sa.Uuid(), nullable=True),
        sa.Column("crm_timeline_event_id", sa.Uuid(), nullable=True),
        sa.Column("sales_lead_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("sale_id", sa.Uuid(), nullable=True),
        sa.Column("tracking_context_id", sa.Uuid(), nullable=True),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("lead_context_id", sa.Uuid(), nullable=True),
        sa.Column(
            "touch_type",
            sa.Enum(
                "ad_click", "organic_visit", "landing_page_view", "cta_click", "form_start",
                "form_submit", "email_open", "email_click", "whatsapp_click", "sms_click",
                "phone_call", "meeting", "reservation", "sale", "referral", "broker",
                "offline_event", "manual_entry", "other",
                name="marketing_touch_type",
            ),
            nullable=False,
        ),
        sa.Column("touch_order", sa.Integer(), nullable=True),
        sa.Column("touch_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_term", sa.String(length=255), nullable=True),
        sa.Column("utm_content", sa.String(length=255), nullable=True),
        sa.Column("click_ids_json", sa.JSON(), nullable=True),
        sa.Column("device_json", sa.JSON(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column(
            "verification_status",
            sa.Enum("verified", "unverified", "unknown", "partial", name="touch_verification_status"),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("source_entity_type", sa.String(length=50), nullable=True),
        sa.Column("source_entity_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversion_event_id"], ["marketing_conversion_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_context_id"], ["marketing_lead_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sales_lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["marketing_form_submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tracking_context_id"], ["marketing_tracking_contexts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_touchpoints_contact_id", "marketing_touchpoints", ["contact_id"])
    op.create_index("ix_marketing_touchpoints_lead_context_id", "marketing_touchpoints", ["lead_context_id"])
    op.create_index("ix_marketing_touchpoints_touch_timestamp", "marketing_touchpoints", ["touch_timestamp"])
    op.create_index("ix_marketing_touchpoints_tracking_context_id", "marketing_touchpoints", ["tracking_context_id"])
    op.create_index(
        "ix_marketing_touchpoints_source_entity",
        "marketing_touchpoints",
        ["source_entity_type", "source_entity_id"],
        unique=True,
    )

    op.create_table(
        "marketing_attribution_journeys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("marketing_lead_context_id", sa.Uuid(), nullable=True),
        sa.Column("touchpoint_ids_json", sa.JSON(), nullable=True),
        sa.Column(
            "journey_status",
            sa.Enum("complete", "incomplete", "broken", "unknown", name="attribution_journey_status"),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("conversion_event_id", sa.Uuid(), nullable=True),
        sa.Column("first_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("touch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversion_event_id"], ["marketing_conversion_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marketing_lead_context_id"], ["marketing_lead_contexts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_attribution_journeys_contact_id", "marketing_attribution_journeys", ["contact_id"])
    op.create_index(
        "ix_marketing_attribution_journeys_lead_context_id",
        "marketing_attribution_journeys",
        ["marketing_lead_context_id"],
    )
    op.create_index("ix_marketing_attribution_journeys_status", "marketing_attribution_journeys", ["journey_status"])

    op.create_table(
        "marketing_attribution_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "model_type",
            sa.Enum(
                "first_touch", "last_touch", "linear", "position_based", "time_decay",
                "data_driven", "custom", "offline", "manual", "unknown", "partial",
                name="attribution_model_type",
            ),
            nullable=False,
        ),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_attribution_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("allocation_json", sa.JSON(), nullable=True),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["marketing_attribution_models.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_attribution_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journey_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("touchpoint_id", sa.Uuid(), nullable=False),
        sa.Column("contribution_pct", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["journey_id"], ["marketing_attribution_journeys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["marketing_attribution_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["touchpoint_id"], ["marketing_touchpoints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_attribution_allocations_journey_model",
        "marketing_attribution_allocations",
        ["journey_id", "model_id"],
    )
    op.create_index(
        "ix_marketing_attribution_allocations_unique",
        "marketing_attribution_allocations",
        ["journey_id", "model_id", "touchpoint_id"],
        unique=True,
    )

    op.create_table(
        "marketing_attribution_health",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "issue_type",
            sa.Enum(
                "broken_journey", "missing_touch", "duplicate_touch", "unknown_source",
                "incomplete_journey", "unlinked_touch",
                name="attribution_health_issue_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("healthy", "warning", "critical", name="attribution_health_severity"),
            nullable=False,
        ),
        sa.Column("journey_id", sa.Uuid(), nullable=True),
        sa.Column("touchpoint_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["journey_id"], ["marketing_attribution_journeys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["touchpoint_id"], ["marketing_touchpoints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_attribution_health_severity", "marketing_attribution_health", ["severity"])
    op.create_index("ix_marketing_attribution_health_journey_id", "marketing_attribution_health", ["journey_id"])

    attribution_model_enum = sa.Enum(
        "first_touch",
        "last_touch",
        "linear",
        "position_based",
        "time_decay",
        "data_driven",
        "custom",
        "offline",
        "manual",
        "unknown",
        "partial",
        name="attribution_model_type",
        create_type=False,
    )
    models_table = sa.table(
        "marketing_attribution_models",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("model_type", attribution_model_enum),
        sa.column("is_default", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        models_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "model_type": model_type,
                "is_default": is_default,
                "is_active": True,
            }
            for name, model_type, is_default in DEFAULT_MODELS
        ],
    )


def downgrade() -> None:
    op.drop_table("marketing_attribution_health")
    op.drop_table("marketing_attribution_allocations")
    op.drop_table("marketing_attribution_rules")
    op.drop_table("marketing_attribution_models")
    op.drop_table("marketing_attribution_journeys")
    op.drop_table("marketing_touchpoints")
    op.execute("DROP TYPE IF EXISTS attribution_health_severity")
    op.execute("DROP TYPE IF EXISTS attribution_health_issue_type")
    op.execute("DROP TYPE IF EXISTS attribution_model_type")
    op.execute("DROP TYPE IF EXISTS attribution_journey_status")
    op.execute("DROP TYPE IF EXISTS touch_verification_status")
    op.execute("DROP TYPE IF EXISTS marketing_touch_type")
