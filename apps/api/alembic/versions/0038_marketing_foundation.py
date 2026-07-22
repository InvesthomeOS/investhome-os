"""Marketing workspace foundation tables.

Revision ID: 0038_marketing_foundation
Revises: 0037_crm_search
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_marketing_foundation"
down_revision: str | None = "0037_crm_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.String(length=40), nullable=False),
        sa.Column("campaign_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="normal", nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("project_ids", sa.JSON(), nullable=True),
        sa.Column("property_ids", sa.JSON(), nullable=True),
        sa.Column("audience_ids", sa.JSON(), nullable=True),
        sa.Column("segment_ids", sa.JSON(), nullable=True),
        sa.Column("channel_ids", sa.JSON(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_currency", sa.String(length=3), nullable=True),
        sa.Column("targets_json", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_campaigns_status", "marketing_campaigns", ["status"])
    op.create_index("ix_marketing_campaigns_campaign_type", "marketing_campaigns", ["campaign_type"])
    op.create_index("ix_marketing_campaigns_owner_user_id", "marketing_campaigns", ["owner_user_id"])
    op.create_index("ix_marketing_campaigns_code", "marketing_campaigns", ["code"])
    op.create_index("ix_marketing_campaigns_updated_at", "marketing_campaigns", ["updated_at"])
    op.create_index("ix_marketing_campaigns_archived_at", "marketing_campaigns", ["archived_at"])

    op.create_table(
        "marketing_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="inactive", nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=True),
        sa.Column("connection_status", sa.String(length=30), server_default="not_connected", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_channels_category", "marketing_channels", ["category"])
    op.create_index("ix_marketing_channels_status", "marketing_channels", ["status"])
    op.create_index("ix_marketing_channels_connection_status", "marketing_channels", ["connection_status"])

    op.create_table(
        "marketing_audiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("audience_type", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("estimated_size", sa.Integer(), nullable=True),
        sa.Column("contact_ids", sa.JSON(), nullable=True),
        sa.Column("company_ids", sa.JSON(), nullable=True),
        sa.Column("segment_rules_json", sa.JSON(), nullable=True),
        sa.Column("consent_json", sa.JSON(), nullable=True),
        sa.Column("geo_json", sa.JSON(), nullable=True),
        sa.Column("channel_ids", sa.JSON(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_audiences_audience_type", "marketing_audiences", ["audience_type"])
    op.create_index("ix_marketing_audiences_archived_at", "marketing_audiences", ["archived_at"])

    op.create_table(
        "marketing_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("segment_type", sa.String(length=30), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=True),
        sa.Column("refresh_frequency", sa.String(length=40), nullable=True),
        sa.Column("visibility", sa.String(length=20), server_default="team", nullable=False),
        sa.Column("estimated_size", sa.Integer(), nullable=True),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_segments_segment_type", "marketing_segments", ["segment_type"])
    op.create_index("ix_marketing_segments_archived_at", "marketing_segments", ["archived_at"])

    op.create_table(
        "marketing_lead_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("utm_defaults_json", sa.JSON(), nullable=True),
        sa.Column("tracking_code", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_lead_sources_source_type", "marketing_lead_sources", ["source_type"])
    op.create_index("ix_marketing_lead_sources_tracking_code", "marketing_lead_sources", ["tracking_code"])
    op.create_index("ix_marketing_lead_sources_archived_at", "marketing_lead_sources", ["archived_at"])

    op.create_table(
        "marketing_lead_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("landing_page_id", sa.Uuid(), nullable=True),
        sa.Column("attribution_json", sa.JSON(), nullable=True),
        sa.Column("utm_data_json", sa.JSON(), nullable=True),
        sa.Column("scores_json", sa.JSON(), nullable=True),
        sa.Column("consent_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_lead_contexts_lead_id", "marketing_lead_contexts", ["lead_id"])
    op.create_index("ix_marketing_lead_contexts_contact_id", "marketing_lead_contexts", ["contact_id"])
    op.create_index("ix_marketing_lead_contexts_campaign_id", "marketing_lead_contexts", ["campaign_id"])
    op.create_index("ix_marketing_lead_contexts_source_id", "marketing_lead_contexts", ["source_id"])

    op.create_table(
        "marketing_content_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=30), nullable=False),
        sa.Column("format", sa.String(length=40), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("file_ref", sa.String(length=512), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_content_assets_content_type", "marketing_content_assets", ["content_type"])
    op.create_index("ix_marketing_content_assets_campaign_id", "marketing_content_assets", ["campaign_id"])
    op.create_index("ix_marketing_content_assets_status", "marketing_content_assets", ["status"])

    op.create_table(
        "marketing_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("registration_json", sa.JSON(), nullable=True),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_currency", sa.String(length=3), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_events_event_type", "marketing_events", ["event_type"])
    op.create_index("ix_marketing_events_campaign_id", "marketing_events", ["campaign_id"])
    op.create_index("ix_marketing_events_start_at", "marketing_events", ["start_at"])
    op.create_index("ix_marketing_events_status", "marketing_events", ["status"])

    op.create_table(
        "marketing_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("planned_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("committed_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("spent_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_budgets_campaign_id", "marketing_budgets", ["campaign_id"])
    op.create_index("ix_marketing_budgets_status", "marketing_budgets", ["status"])

    op.create_table(
        "marketing_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("approval_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_approvals_entity", "marketing_approvals", ["entity_type", "entity_id"])
    op.create_index("ix_marketing_approvals_status", "marketing_approvals", ["status"])

    op.create_table(
        "marketing_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_alerts_category", "marketing_alerts", ["category"])
    op.create_index("ix_marketing_alerts_severity", "marketing_alerts", ["severity"])
    op.create_index("ix_marketing_alerts_is_resolved", "marketing_alerts", ["is_resolved"])

    op.create_table(
        "marketing_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recommendation_type", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("confidence_level", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_recommendations_status", "marketing_recommendations", ["status"])
    op.create_index("ix_marketing_recommendations_type", "marketing_recommendations", ["recommendation_type"])


def downgrade() -> None:
    op.drop_index("ix_marketing_recommendations_type", table_name="marketing_recommendations")
    op.drop_index("ix_marketing_recommendations_status", table_name="marketing_recommendations")
    op.drop_table("marketing_recommendations")
    op.drop_index("ix_marketing_alerts_is_resolved", table_name="marketing_alerts")
    op.drop_index("ix_marketing_alerts_severity", table_name="marketing_alerts")
    op.drop_index("ix_marketing_alerts_category", table_name="marketing_alerts")
    op.drop_table("marketing_alerts")
    op.drop_index("ix_marketing_approvals_status", table_name="marketing_approvals")
    op.drop_index("ix_marketing_approvals_entity", table_name="marketing_approvals")
    op.drop_table("marketing_approvals")
    op.drop_index("ix_marketing_budgets_status", table_name="marketing_budgets")
    op.drop_index("ix_marketing_budgets_campaign_id", table_name="marketing_budgets")
    op.drop_table("marketing_budgets")
    op.drop_index("ix_marketing_events_status", table_name="marketing_events")
    op.drop_index("ix_marketing_events_start_at", table_name="marketing_events")
    op.drop_index("ix_marketing_events_campaign_id", table_name="marketing_events")
    op.drop_index("ix_marketing_events_event_type", table_name="marketing_events")
    op.drop_table("marketing_events")
    op.drop_index("ix_marketing_content_assets_status", table_name="marketing_content_assets")
    op.drop_index("ix_marketing_content_assets_campaign_id", table_name="marketing_content_assets")
    op.drop_index("ix_marketing_content_assets_content_type", table_name="marketing_content_assets")
    op.drop_table("marketing_content_assets")
    op.drop_index("ix_marketing_lead_contexts_source_id", table_name="marketing_lead_contexts")
    op.drop_index("ix_marketing_lead_contexts_campaign_id", table_name="marketing_lead_contexts")
    op.drop_index("ix_marketing_lead_contexts_contact_id", table_name="marketing_lead_contexts")
    op.drop_index("ix_marketing_lead_contexts_lead_id", table_name="marketing_lead_contexts")
    op.drop_table("marketing_lead_contexts")
    op.drop_index("ix_marketing_lead_sources_archived_at", table_name="marketing_lead_sources")
    op.drop_index("ix_marketing_lead_sources_tracking_code", table_name="marketing_lead_sources")
    op.drop_index("ix_marketing_lead_sources_source_type", table_name="marketing_lead_sources")
    op.drop_table("marketing_lead_sources")
    op.drop_index("ix_marketing_segments_archived_at", table_name="marketing_segments")
    op.drop_index("ix_marketing_segments_segment_type", table_name="marketing_segments")
    op.drop_table("marketing_segments")
    op.drop_index("ix_marketing_audiences_archived_at", table_name="marketing_audiences")
    op.drop_index("ix_marketing_audiences_audience_type", table_name="marketing_audiences")
    op.drop_table("marketing_audiences")
    op.drop_index("ix_marketing_channels_connection_status", table_name="marketing_channels")
    op.drop_index("ix_marketing_channels_status", table_name="marketing_channels")
    op.drop_index("ix_marketing_channels_category", table_name="marketing_channels")
    op.drop_table("marketing_channels")
    op.drop_index("ix_marketing_campaigns_archived_at", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_updated_at", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_code", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_owner_user_id", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_campaign_type", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_status", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")
