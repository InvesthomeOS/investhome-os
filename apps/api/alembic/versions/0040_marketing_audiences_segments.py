"""Marketing audience, segment, lead source extension tables.

Revision ID: 0040_mkt_audiences_seg
Revises: 0039_marketing_campaigns
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_mkt_audiences_seg"
down_revision: str | None = "0039_marketing_campaigns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("marketing_audiences", sa.Column("mode", sa.String(length=30), server_default="static", nullable=False))
    op.add_column("marketing_audiences", sa.Column("status", sa.String(length=20), server_default="draft", nullable=False))
    op.add_column("marketing_audiences", sa.Column("calculated_size", sa.Integer(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("segment_ids", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("inclusion_refs_json", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("exclusion_refs_json", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("consent_requirements_json", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("channel_eligibility_json", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("refresh_policy_json", sa.JSON(), nullable=True))
    op.add_column("marketing_audiences", sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("marketing_audiences", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("marketing_audiences", sa.Column("updated_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_audiences_updated_by_user_id",
        "marketing_audiences",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_marketing_audiences_mode", "marketing_audiences", ["mode"])
    op.create_index("ix_marketing_audiences_status", "marketing_audiences", ["status"])

    op.add_column("marketing_segments", sa.Column("calculated_size", sa.Integer(), nullable=True))
    op.add_column(
        "marketing_segments",
        sa.Column("calculation_status", sa.String(length=20), server_default="not_calculated", nullable=False),
    )
    op.add_column("marketing_segments", sa.Column("current_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("marketing_segments", sa.Column("depends_on_segment_ids", sa.JSON(), nullable=True))
    op.add_column("marketing_segments", sa.Column("updated_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_segments_updated_by_user_id",
        "marketing_segments",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_marketing_segments_calculation_status", "marketing_segments", ["calculation_status"])

    op.add_column("marketing_lead_contexts", sa.Column("marketing_status", sa.String(length=40), nullable=True))
    op.add_column("marketing_lead_contexts", sa.Column("verification_status", sa.String(length=40), nullable=True))
    op.add_column(
        "marketing_lead_contexts",
        sa.Column("handoff_status", sa.String(length=20), server_default="not_ready", nullable=False),
    )
    op.add_column("marketing_lead_contexts", sa.Column("suppression_json", sa.JSON(), nullable=True))
    op.create_index("ix_marketing_lead_contexts_handoff_status", "marketing_lead_contexts", ["handoff_status"])

    op.add_column("marketing_lead_sources", sa.Column("normalized_name", sa.String(length=255), nullable=True))
    op.add_column("marketing_lead_sources", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.add_column("marketing_lead_sources", sa.Column("tracking_readiness", sa.String(length=30), nullable=True))
    op.add_column("marketing_lead_sources", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("marketing_lead_sources", sa.Column("updated_by_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_marketing_lead_sources_parent_id",
        "marketing_lead_sources",
        "marketing_lead_sources",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_marketing_lead_sources_updated_by_user_id",
        "marketing_lead_sources",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_marketing_lead_sources_parent_id", "marketing_lead_sources", ["parent_id"])

    op.create_table(
        "marketing_audience_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audience_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("is_included", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("inclusion_source", sa.String(length=20), nullable=True),
        sa.Column("exclusion_reason", sa.String(length=20), nullable=True),
        sa.Column("eligibility_json", sa.JSON(), nullable=True),
        sa.Column("explainability_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_audience_memberships_audience_id", "marketing_audience_memberships", ["audience_id"])
    op.create_index("ix_marketing_audience_memberships_contact_id", "marketing_audience_memberships", ["contact_id"])
    op.create_index("ix_marketing_audience_memberships_company_id", "marketing_audience_memberships", ["company_id"])

    op.create_table(
        "marketing_audience_consent_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audience_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audience_id"], ["marketing_audiences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_segment_rule_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("parent_group_id", sa.Uuid(), nullable=True),
        sa.Column("operator", sa.String(length=10), server_default="and", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_group_id"], ["marketing_segment_rule_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["marketing_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_segment_rule_groups_segment_id", "marketing_segment_rule_groups", ["segment_id"])

    op.create_table(
        "marketing_segment_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=40), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("negate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["marketing_segment_rule_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_segment_rules_group_id", "marketing_segment_rules", ["group_id"])

    op.create_table(
        "marketing_segment_calculation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["marketing_segments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_segment_calculation_runs_segment_id", "marketing_segment_calculation_runs", ["segment_id"])

    op.create_table(
        "marketing_segment_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rules_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["segment_id"], ["marketing_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_segment_versions_segment_id", "marketing_segment_versions", ["segment_id"])

    op.create_table(
        "marketing_lead_source_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("mapping_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_lead_source_mappings_source_id", "marketing_lead_source_mappings", ["source_id"])

    op.create_table(
        "marketing_lead_source_normalizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("raw_value", sa.String(length=512), nullable=False),
        sa.Column("normalized_value", sa.String(length=512), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["marketing_lead_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_lead_source_normalizations_source_id",
        "marketing_lead_source_normalizations",
        ["source_id"],
    )

    op.create_table(
        "marketing_audience_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "marketing_segment_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("marketing_segment_saved_views")
    op.drop_table("marketing_audience_saved_views")
    op.drop_index("ix_marketing_lead_source_normalizations_source_id", table_name="marketing_lead_source_normalizations")
    op.drop_table("marketing_lead_source_normalizations")
    op.drop_index("ix_marketing_lead_source_mappings_source_id", table_name="marketing_lead_source_mappings")
    op.drop_table("marketing_lead_source_mappings")
    op.drop_index("ix_marketing_segment_versions_segment_id", table_name="marketing_segment_versions")
    op.drop_table("marketing_segment_versions")
    op.drop_index("ix_marketing_segment_calculation_runs_segment_id", table_name="marketing_segment_calculation_runs")
    op.drop_table("marketing_segment_calculation_runs")
    op.drop_index("ix_marketing_segment_rules_group_id", table_name="marketing_segment_rules")
    op.drop_table("marketing_segment_rules")
    op.drop_index("ix_marketing_segment_rule_groups_segment_id", table_name="marketing_segment_rule_groups")
    op.drop_table("marketing_segment_rule_groups")
    op.drop_table("marketing_audience_consent_requirements")
    op.drop_index("ix_marketing_audience_memberships_company_id", table_name="marketing_audience_memberships")
    op.drop_index("ix_marketing_audience_memberships_contact_id", table_name="marketing_audience_memberships")
    op.drop_index("ix_marketing_audience_memberships_audience_id", table_name="marketing_audience_memberships")
    op.drop_table("marketing_audience_memberships")

    op.drop_index("ix_marketing_lead_sources_parent_id", table_name="marketing_lead_sources")
    op.drop_constraint("fk_marketing_lead_sources_updated_by_user_id", "marketing_lead_sources", type_="foreignkey")
    op.drop_constraint("fk_marketing_lead_sources_parent_id", "marketing_lead_sources", type_="foreignkey")
    op.drop_column("marketing_lead_sources", "updated_by_user_id")
    op.drop_column("marketing_lead_sources", "is_active")
    op.drop_column("marketing_lead_sources", "tracking_readiness")
    op.drop_column("marketing_lead_sources", "parent_id")
    op.drop_column("marketing_lead_sources", "normalized_name")

    op.drop_index("ix_marketing_lead_contexts_handoff_status", table_name="marketing_lead_contexts")
    op.drop_column("marketing_lead_contexts", "suppression_json")
    op.drop_column("marketing_lead_contexts", "handoff_status")
    op.drop_column("marketing_lead_contexts", "verification_status")
    op.drop_column("marketing_lead_contexts", "marketing_status")

    op.drop_index("ix_marketing_segments_calculation_status", table_name="marketing_segments")
    op.drop_constraint("fk_marketing_segments_updated_by_user_id", "marketing_segments", type_="foreignkey")
    op.drop_column("marketing_segments", "updated_by_user_id")
    op.drop_column("marketing_segments", "depends_on_segment_ids")
    op.drop_column("marketing_segments", "current_version")
    op.drop_column("marketing_segments", "calculation_status")
    op.drop_column("marketing_segments", "calculated_size")

    op.drop_index("ix_marketing_audiences_status", table_name="marketing_audiences")
    op.drop_index("ix_marketing_audiences_mode", table_name="marketing_audiences")
    op.drop_constraint("fk_marketing_audiences_updated_by_user_id", "marketing_audiences", type_="foreignkey")
    op.drop_column("marketing_audiences", "updated_by_user_id")
    op.drop_column("marketing_audiences", "version")
    op.drop_column("marketing_audiences", "last_refreshed_at")
    op.drop_column("marketing_audiences", "refresh_policy_json")
    op.drop_column("marketing_audiences", "channel_eligibility_json")
    op.drop_column("marketing_audiences", "consent_requirements_json")
    op.drop_column("marketing_audiences", "exclusion_refs_json")
    op.drop_column("marketing_audiences", "inclusion_refs_json")
    op.drop_column("marketing_audiences", "segment_ids")
    op.drop_column("marketing_audiences", "calculated_size")
    op.drop_column("marketing_audiences", "status")
    op.drop_column("marketing_audiences", "mode")
