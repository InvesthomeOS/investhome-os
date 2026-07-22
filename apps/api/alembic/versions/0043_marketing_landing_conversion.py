"""Marketing landing pages, forms, submissions, and conversion infrastructure.

Revision ID: 0043_mkt_landing_conv
Revises: 0042_mkt_channel_comms
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043_mkt_landing_conv"
down_revision: str | None = "0042_mkt_channel_comms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_form_field_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("config_schema_json", sa.JSON(), nullable=True),
        sa.Column("validation_schema_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_type"),
    )
    op.create_table(
        "marketing_landing_page_section_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("section_type", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("config_schema_json", sa.JSON(), nullable=True),
        sa.Column("allowed_public_fields_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("section_type"),
    )
    op.create_table(
        "marketing_public_data_field_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=30), server_default="string", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_public_data_field_entity_key",
        "marketing_public_data_field_registry",
        ["entity_type", "field_key"],
        unique=True,
    )
    op.create_table(
        "marketing_handoff_slas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_forms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("consent_config_json", sa.JSON(), nullable=True),
        sa.Column("routing_config_json", sa.JSON(), nullable=True),
        sa.Column("notification_config_json", sa.JSON(), nullable=True),
        sa.Column("spam_config_json", sa.JSON(), nullable=True),
        sa.Column("published_version_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_marketing_forms_slug", "marketing_forms", ["slug"])
    op.create_table(
        "marketing_landing_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("tracking_config_json", sa.JSON(), nullable=True),
        sa.Column("consent_config_json", sa.JSON(), nullable=True),
        sa.Column("approval_status", sa.String(length=30), nullable=True),
        sa.Column("published_version_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_marketing_landing_pages_slug", "marketing_landing_pages", ["slug"])
    op.create_table(
        "marketing_form_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("field_type", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("validation_json", sa.JSON(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_form_fields_form_key", "marketing_form_fields", ["form_id", "field_key"], unique=True)
    op.create_table(
        "marketing_form_logic_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("target_field_id", sa.Uuid(), nullable=False),
        sa.Column("operator", sa.String(length=10), server_default="and", nullable=False),
        sa.Column("action", sa.String(length=30), server_default="show", nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_field_id"], ["marketing_form_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_form_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_landing_page_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=False),
        sa.Column("section_type", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_landing_page_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_landing_page_domains",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("path_prefix", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verification_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("dns_records_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_landing_page_experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("traffic_split_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_landing_page_experiment_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("weight_percent", sa.Integer(), server_default="50", nullable=False),
        sa.Column("is_control", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["marketing_landing_page_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_landing_page_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_tracking_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_term", sa.String(length=255), nullable=True),
        sa.Column("utm_content", sa.String(length=255), nullable=True),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column("landing_url", sa.String(length=500), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_consent_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("consent_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("marketing_eligible", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("evidence_source", sa.String(length=50), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_form_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("landing_page_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="received", nullable=False),
        sa.Column("raw_values_reference", sa.String(length=500), nullable=True),
        sa.Column("normalized_values_json", sa.JSON(), nullable=True),
        sa.Column("tracking_context_id", sa.Uuid(), nullable=True),
        sa.Column("consent_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("lead_context_id", sa.Uuid(), nullable=True),
        sa.Column("duplicate_of_submission_id", sa.Uuid(), nullable=True),
        sa.Column("pipeline_errors_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["consent_evidence_id"], ["marketing_consent_evidence.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_context_id"], ["marketing_lead_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tracking_context_id"], ["marketing_tracking_contexts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_form_submissions_idempotency_key", "marketing_form_submissions", ["idempotency_key"])
    op.create_index(
        "ix_marketing_form_submissions_form_idempotency",
        "marketing_form_submissions",
        ["form_id", "idempotency_key"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_consent_evidence_submission",
        "marketing_consent_evidence",
        "marketing_form_submissions",
        ["submission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "marketing_conversion_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("lead_context_id", sa.Uuid(), nullable=True),
        sa.Column("landing_page_id", sa.Uuid(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("tracking_context_id", sa.Uuid(), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["landing_page_id"], ["marketing_landing_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_context_id"], ["marketing_lead_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["marketing_form_submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tracking_context_id"], ["marketing_tracking_contexts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_lead_routing_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_fallback", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("action_json", sa.JSON(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_sales_handoffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_context_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("sales_lead_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("sla_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blockers_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_context_id"], ["marketing_lead_contexts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sla_id"], ["marketing_handoff_slas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["marketing_form_submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_submission_review_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("review_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["marketing_form_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("event_types_json", sa.JSON(), nullable=True),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["marketing_forms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "marketing_webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["webhook_id"], ["marketing_webhooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_lead_context_form",
        "marketing_lead_contexts",
        "marketing_forms",
        ["form_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_lead_context_landing_page",
        "marketing_lead_contexts",
        "marketing_landing_pages",
        ["landing_page_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_lead_context_landing_page", "marketing_lead_contexts", type_="foreignkey")
    op.drop_constraint("fk_lead_context_form", "marketing_lead_contexts", type_="foreignkey")
    op.drop_table("marketing_webhook_deliveries")
    op.drop_table("marketing_webhooks")
    op.drop_table("marketing_submission_review_items")
    op.drop_table("marketing_sales_handoffs")
    op.drop_table("marketing_lead_routing_rules")
    op.drop_table("marketing_conversion_events")
    op.drop_constraint("fk_consent_evidence_submission", "marketing_consent_evidence", type_="foreignkey")
    op.drop_table("marketing_form_submissions")
    op.drop_table("marketing_consent_evidence")
    op.drop_table("marketing_tracking_contexts")
    op.drop_table("marketing_landing_page_experiment_variants")
    op.drop_table("marketing_landing_page_experiments")
    op.drop_table("marketing_landing_page_domains")
    op.drop_table("marketing_landing_page_versions")
    op.drop_table("marketing_landing_page_sections")
    op.drop_table("marketing_form_versions")
    op.drop_table("marketing_form_logic_groups")
    op.drop_table("marketing_form_fields")
    op.drop_table("marketing_landing_pages")
    op.drop_table("marketing_forms")
    op.drop_table("marketing_handoff_slas")
    op.drop_index("ix_public_data_field_entity_key", table_name="marketing_public_data_field_registry")
    op.drop_table("marketing_public_data_field_registry")
    op.drop_table("marketing_landing_page_section_registry")
    op.drop_table("marketing_form_field_registry")
