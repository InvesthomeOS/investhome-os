"""Marketing content studio, assets, brand center, templates.

Revision ID: 0041_marketing_content_studio
Revises: 0040_mkt_audiences_seg
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_marketing_content_studio"
down_revision: str | None = "0040_mkt_audiences_seg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_contents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=30), nullable=False),
        sa.Column("format", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="idea", nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("primary_language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("project_ids", sa.JSON(), nullable=True),
        sa.Column("property_ids", sa.JSON(), nullable=True),
        sa.Column("audience_ids", sa.JSON(), nullable=True),
        sa.Column("campaign_ids", sa.JSON(), nullable=True),
        sa.Column("asset_ids", sa.JSON(), nullable=True),
        sa.Column("channel_ids", sa.JSON(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_marketing_contents_status", "marketing_contents", ["status"])
    op.create_index("ix_marketing_contents_content_type", "marketing_contents", ["content_type"])
    op.create_index("ix_marketing_contents_owner_user_id", "marketing_contents", ["owner_user_id"])
    op.create_index("ix_marketing_contents_scheduled_at", "marketing_contents", ["scheduled_at"])
    op.create_index("ix_marketing_contents_archived_at", "marketing_contents", ["archived_at"])

    op.create_table(
        "marketing_content_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("key_messages", sa.Text(), nullable=True),
        sa.Column("tone_and_voice", sa.Text(), nullable=True),
        sa.Column("deliverables", sa.Text(), nullable=True),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id"),
    )

    op.create_table(
        "marketing_content_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("body_json", sa.JSON(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_content_versions_content_id", "marketing_content_versions", ["content_id"])

    op.create_table(
        "marketing_content_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("channel_category", sa.String(length=30), nullable=True),
        sa.Column("variant_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body_json", sa.JSON(), nullable=True),
        sa.Column("validation_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_content_variants_content_id", "marketing_content_variants", ["content_id"])

    op.create_table(
        "marketing_content_translations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body_json", sa.JSON(), nullable=True),
        sa.Column("is_outdated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_content_translations_content_id", "marketing_content_translations", ["content_id"])

    op.create_table(
        "marketing_content_type_field_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=30), nullable=False),
        sa.Column("format", sa.String(length=40), nullable=True),
        sa.Column("channel_category", sa.String(length=30), nullable=True),
        sa.Column("field_key", sa.String(length=80), nullable=False),
        sa.Column("field_label", sa.String(length=120), nullable=False),
        sa.Column("field_type", sa.String(length=30), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mkt_content_type_registry_type", "marketing_content_type_field_registry", ["content_type"])

    op.create_table(
        "marketing_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("file_ref", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("rights_status", sa.String(length=30), server_default="unknown", nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_assets_asset_type", "marketing_assets", ["asset_type"])
    op.create_index("ix_marketing_assets_rights_status", "marketing_assets", ["rights_status"])
    op.create_index("ix_marketing_assets_status", "marketing_assets", ["status"])

    op.create_table(
        "marketing_asset_rights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("license_type", sa.String(length=40), nullable=True),
        sa.Column("holder", sa.String(length=255), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("territory", sa.String(length=120), nullable=True),
        sa.Column("usage_restrictions", sa.Text(), nullable=True),
        sa.Column("attribution_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="unknown", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["marketing_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )

    op.create_table(
        "marketing_asset_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("usage_context", sa.String(length=80), nullable=True),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["marketing_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["marketing_channels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_asset_usage_asset_id", "marketing_asset_usage_records", ["asset_id"])
    op.create_index("ix_marketing_asset_usage_entity", "marketing_asset_usage_records", ["entity_type", "entity_id"])

    op.create_table(
        "marketing_brand_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("company_brand_id", sa.Uuid(), nullable=True),
        sa.Column("colors_json", sa.JSON(), nullable=True),
        sa.Column("typography_json", sa.JSON(), nullable=True),
        sa.Column("voice_json", sa.JSON(), nullable=True),
        sa.Column("guidelines_json", sa.JSON(), nullable=True),
        sa.Column("logo_asset_ids", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_brand_id"], ["brand_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_brand_terminology",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=False),
        sa.Column("term", sa.String(length=120), nullable=False),
        sa.Column("preferred_usage", sa.String(length=255), nullable=True),
        sa.Column("avoid_usage", sa.String(length=255), nullable=True),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["marketing_brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_brand_terminology_profile", "marketing_brand_terminology", ["brand_profile_id"])

    op.create_table(
        "marketing_approved_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("evidence_ref", sa.String(length=255), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["marketing_brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_prohibited_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), server_default="warning", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["marketing_brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_brand_compliance_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("violations_json", sa.JSON(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("checked_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["marketing_brand_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(length=40), nullable=False),
        sa.Column("content_type", sa.String(length=30), nullable=True),
        sa.Column("channel_category", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_templates_template_type", "marketing_templates", ["template_type"])
    op.create_index("ix_marketing_templates_status", "marketing_templates", ["status"])

    op.create_table(
        "marketing_template_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=True),
        sa.Column("body_json", sa.JSON(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_template_versions_template_id", "marketing_template_versions", ["template_id"])

    op.create_table(
        "marketing_template_placeholders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("placeholder_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("placeholder_type", sa.String(length=30), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("validation_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["marketing_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_template_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_template_placeholders_template_id", "marketing_template_placeholders", ["template_id"])

    op.create_table(
        "marketing_ai_content_generation_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=True),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending_review", nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["marketing_contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_id"], ["marketing_content_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "marketing_approvals",
        sa.Column("version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_marketing_approvals_version_id",
        "marketing_approvals",
        "marketing_content_versions",
        ["version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_marketing_approvals_version_id", "marketing_approvals", type_="foreignkey")
    op.drop_column("marketing_approvals", "version_id")
    op.drop_table("marketing_ai_content_generation_records")
    op.drop_index("ix_marketing_template_placeholders_template_id", table_name="marketing_template_placeholders")
    op.drop_table("marketing_template_placeholders")
    op.drop_index("ix_marketing_template_versions_template_id", table_name="marketing_template_versions")
    op.drop_table("marketing_template_versions")
    op.drop_index("ix_marketing_templates_status", table_name="marketing_templates")
    op.drop_index("ix_marketing_templates_template_type", table_name="marketing_templates")
    op.drop_table("marketing_templates")
    op.drop_table("marketing_brand_compliance_results")
    op.drop_table("marketing_prohibited_claims")
    op.drop_table("marketing_approved_claims")
    op.drop_index("ix_marketing_brand_terminology_profile", table_name="marketing_brand_terminology")
    op.drop_table("marketing_brand_terminology")
    op.drop_table("marketing_brand_profiles")
    op.drop_index("ix_marketing_asset_usage_entity", table_name="marketing_asset_usage_records")
    op.drop_index("ix_marketing_asset_usage_asset_id", table_name="marketing_asset_usage_records")
    op.drop_table("marketing_asset_usage_records")
    op.drop_table("marketing_asset_rights")
    op.drop_index("ix_marketing_assets_status", table_name="marketing_assets")
    op.drop_index("ix_marketing_assets_rights_status", table_name="marketing_assets")
    op.drop_index("ix_marketing_assets_asset_type", table_name="marketing_assets")
    op.drop_table("marketing_assets")
    op.drop_index("ix_mkt_content_type_registry_type", table_name="marketing_content_type_field_registry")
    op.drop_table("marketing_content_type_field_registry")
    op.drop_index("ix_marketing_content_translations_content_id", table_name="marketing_content_translations")
    op.drop_table("marketing_content_translations")
    op.drop_index("ix_marketing_content_variants_content_id", table_name="marketing_content_variants")
    op.drop_table("marketing_content_variants")
    op.drop_index("ix_marketing_content_versions_content_id", table_name="marketing_content_versions")
    op.drop_table("marketing_content_versions")
    op.drop_table("marketing_content_briefs")
    op.drop_index("ix_marketing_contents_archived_at", table_name="marketing_contents")
    op.drop_index("ix_marketing_contents_scheduled_at", table_name="marketing_contents")
    op.drop_index("ix_marketing_contents_owner_user_id", table_name="marketing_contents")
    op.drop_index("ix_marketing_contents_content_type", table_name="marketing_contents")
    op.drop_index("ix_marketing_contents_status", table_name="marketing_contents")
    op.drop_table("marketing_contents")
