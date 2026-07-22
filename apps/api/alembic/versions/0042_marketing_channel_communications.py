"""Marketing channel communications — social, email, WhatsApp, SMS.

Revision ID: 0042_mkt_channel_comms
Revises: 0041_marketing_content_studio
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_mkt_channel_comms"
down_revision: str | None = "0041_marketing_content_studio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_frequency_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("max_messages_per_day", sa.Integer(), nullable=True),
        sa.Column("max_messages_per_week", sa.Integer(), nullable=True),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_frequency_policies_channel", "marketing_frequency_policies", ["channel"])

    op.create_table(
        "marketing_email_sending_domains",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("verification_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("dkim_status", sa.String(length=30), nullable=True),
        sa.Column("spf_status", sa.String(length=30), nullable=True),
        sa.Column("dmarc_status", sa.String(length=30), nullable=True),
        sa.Column("dns_records_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )

    op.create_table(
        "marketing_email_sender_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("reply_to", sa.String(length=255), nullable=True),
        sa.Column("domain_id", sa.Uuid(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["marketing_email_sending_domains.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_email_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("content_version_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_email_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("audience_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_email_sequence_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("delay_hours", sa.Integer(), server_default="0", nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sequence_id"], ["marketing_email_sequences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_email_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_email_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("approval_status", sa.String(length=30), server_default="not_required", nullable=False),
        sa.Column("readiness_state", sa.String(length=30), server_default="not_calculated", nullable=False),
        sa.Column("marketing_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("audience_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("content_version_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("personalisation_config_json", sa.JSON(), nullable=True),
        sa.Column("frequency_policy_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_count", sa.Integer(), nullable=True),
        sa.Column("eligible_recipient_count", sa.Integer(), nullable=True),
        sa.Column("readiness_checks_json", sa.JSON(), nullable=True),
        sa.Column("last_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("material_change_hash", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("preview_text", sa.String(length=500), nullable=True),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("sender_profile_id", sa.Uuid(), nullable=True),
        sa.Column("sequence_id", sa.Uuid(), nullable=True),
        sa.Column("unsubscribe_required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("unsubscribe_link_present", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("wizard_step", sa.Integer(), nullable=True),
        sa.Column("wizard_state_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["frequency_policy_id"], ["marketing_frequency_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marketing_campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_profile_id"], ["marketing_email_sender_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sequence_id"], ["marketing_email_sequences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_email_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_email_campaigns_status", "marketing_email_campaigns", ["status"])

    op.create_table(
        "marketing_whatsapp_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("header_text", sa.String(length=255), nullable=True),
        sa.Column("footer_text", sa.String(length=255), nullable=True),
        sa.Column("placeholders_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("external_template_id", sa.String(length=255), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_whatsapp_sender_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("connection_status", sa.String(length=40), server_default="not_connected", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_whatsapp_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("approval_status", sa.String(length=30), server_default="not_required", nullable=False),
        sa.Column("readiness_state", sa.String(length=30), server_default="not_calculated", nullable=False),
        sa.Column("marketing_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("audience_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("content_version_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("personalisation_config_json", sa.JSON(), nullable=True),
        sa.Column("frequency_policy_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_count", sa.Integer(), nullable=True),
        sa.Column("eligible_recipient_count", sa.Integer(), nullable=True),
        sa.Column("readiness_checks_json", sa.JSON(), nullable=True),
        sa.Column("last_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("material_change_hash", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("sender_profile_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["frequency_policy_id"], ["marketing_frequency_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marketing_campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_profile_id"], ["marketing_whatsapp_sender_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_whatsapp_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_whatsapp_campaigns_status", "marketing_whatsapp_campaigns", ["status"])

    op.create_table(
        "marketing_whatsapp_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_profile_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("phone_number", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("handoff_status", sa.String(length=30), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("messages_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_profile_id"], ["marketing_whatsapp_sender_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_sms_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("segment_count", sa.Integer(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_sms_sender_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sender_id", sa.String(length=30), nullable=False),
        sa.Column("connection_status", sa.String(length=40), server_default="not_connected", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_sms_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("approval_status", sa.String(length=30), server_default="not_required", nullable=False),
        sa.Column("readiness_state", sa.String(length=30), server_default="not_calculated", nullable=False),
        sa.Column("marketing_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("audience_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("content_version_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("personalisation_config_json", sa.JSON(), nullable=True),
        sa.Column("frequency_policy_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_count", sa.Integer(), nullable=True),
        sa.Column("eligible_recipient_count", sa.Integer(), nullable=True),
        sa.Column("readiness_checks_json", sa.JSON(), nullable=True),
        sa.Column("last_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("material_change_hash", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("sender_profile_id", sa.Uuid(), nullable=True),
        sa.Column("opt_out_required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("opt_out_text_present", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("segment_count", sa.Integer(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["frequency_policy_id"], ["marketing_frequency_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marketing_campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_profile_id"], ["marketing_sms_sender_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_sms_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_sms_campaigns_status", "marketing_sms_campaigns", ["status"])

    op.create_table(
        "marketing_social_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("network", sa.String(length=30), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("connection_status", sa.String(length=40), server_default="not_connected", nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        sa.Column("capabilities_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_social_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("approval_status", sa.String(length=30), server_default="not_required", nullable=False),
        sa.Column("readiness_state", sa.String(length=30), server_default="not_calculated", nullable=False),
        sa.Column("marketing_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("content_version_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("media_refs_json", sa.JSON(), nullable=True),
        sa.Column("readiness_checks_json", sa.JSON(), nullable=True),
        sa.Column("last_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("material_change_hash", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marketing_campaign_id"], ["marketing_campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_social_posts_status", "marketing_social_posts", ["status"])

    op.create_table(
        "marketing_social_post_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("social_account_id", sa.Uuid(), nullable=False),
        sa.Column("network", sa.String(length=30), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("media_refs_json", sa.JSON(), nullable=True),
        sa.Column("validation_json", sa.JSON(), nullable=True),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("publish_status", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["marketing_social_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["social_account_id"], ["marketing_social_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_social_inbox_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("social_account_id", sa.Uuid(), nullable=False),
        sa.Column("network", sa.String(length=30), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("handoff_status", sa.String(length=30), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["social_account_id"], ["marketing_social_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_channel_delivery_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("campaign_type", sa.String(length=30), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_channel_delivery_events_campaign",
        "marketing_channel_delivery_events",
        ["campaign_type", "campaign_id"],
    )
    op.create_index("ix_marketing_channel_delivery_events_channel", "marketing_channel_delivery_events", ["channel"])

    op.create_table(
        "marketing_channel_send_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_marketing_channel_send_operations_resource",
        "marketing_channel_send_operations",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_table("marketing_channel_send_operations")
    op.drop_table("marketing_channel_delivery_events")
    op.drop_table("marketing_social_inbox_items")
    op.drop_table("marketing_social_post_variants")
    op.drop_index("ix_marketing_social_posts_status", table_name="marketing_social_posts")
    op.drop_table("marketing_social_posts")
    op.drop_table("marketing_social_accounts")
    op.drop_index("ix_marketing_sms_campaigns_status", table_name="marketing_sms_campaigns")
    op.drop_table("marketing_sms_campaigns")
    op.drop_table("marketing_sms_sender_profiles")
    op.drop_table("marketing_sms_templates")
    op.drop_table("marketing_whatsapp_conversations")
    op.drop_index("ix_marketing_whatsapp_campaigns_status", table_name="marketing_whatsapp_campaigns")
    op.drop_table("marketing_whatsapp_campaigns")
    op.drop_table("marketing_whatsapp_sender_profiles")
    op.drop_table("marketing_whatsapp_templates")
    op.drop_index("ix_marketing_email_campaigns_status", table_name="marketing_email_campaigns")
    op.drop_table("marketing_email_campaigns")
    op.drop_table("marketing_email_sequence_steps")
    op.drop_table("marketing_email_sequences")
    op.drop_table("marketing_email_templates")
    op.drop_table("marketing_email_sender_profiles")
    op.drop_table("marketing_email_sending_domains")
    op.drop_index("ix_marketing_frequency_policies_channel", table_name="marketing_frequency_policies")
    op.drop_table("marketing_frequency_policies")
