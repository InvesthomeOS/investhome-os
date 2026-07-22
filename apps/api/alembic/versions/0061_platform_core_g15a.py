"""G15A platform core tables + feature flag targeting columns.

Revision ID: 0061_platform_core_g15a
Revises: 0060_analytics_warehouse_g14
Create Date: 2026-07-20

Non-destructive / additive only. Does not delete operational data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "0061_platform_core_g15a"
down_revision: str | None = "0060_analytics_warehouse_g14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table in insp.get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def upgrade() -> None:
    # Extend feature_flag_overrides (additive)
    if _has_table("feature_flag_overrides"):
        if not _has_column("feature_flag_overrides", "kill_switch"):
            op.add_column(
                "feature_flag_overrides",
                sa.Column("kill_switch", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if not _has_column("feature_flag_overrides", "target_company_ids_json"):
            op.add_column(
                "feature_flag_overrides",
                sa.Column("target_company_ids_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            )
        if not _has_column("feature_flag_overrides", "target_user_ids_json"):
            op.add_column(
                "feature_flag_overrides",
                sa.Column("target_user_ids_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            )
        if not _has_column("feature_flag_overrides", "environment_scope"):
            op.add_column(
                "feature_flag_overrides",
                sa.Column("environment_scope", sa.String(40), nullable=True, server_default="all"),
            )

    if not _has_table("platform_modules"):
        op.create_table(
            "platform_modules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name_en", sa.String(160), nullable=False),
            sa.Column("name_tr", sa.String(160), nullable=False),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("description_tr", sa.Text(), nullable=True),
            sa.Column("lifecycle_status", sa.String(32), nullable=False, server_default="planned"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("env_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("kill_switch", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("depends_on_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("feature_flag_key", sa.String(100), nullable=True),
            sa.Column("route_prefix", sa.String(255), nullable=True),
            sa.Column("admin_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("pilot_phase", sa.String(32), nullable=True),
            sa.Column("block_reason", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("key_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_modules_code", "platform_modules", ["code"], unique=True)
    else:
        if not _has_column("platform_modules", "activated_at"):
            op.add_column("platform_modules", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
        if not _has_column("platform_modules", "key_locked"):
            op.add_column(
                "platform_modules",
                sa.Column("key_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )

    if not _has_table("platform_entitlements"):
        op.create_table(
            "platform_entitlements",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("name_en", sa.String(160), nullable=False),
            sa.Column("name_tr", sa.String(160), nullable=False),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("description_tr", sa.Text(), nullable=True),
            sa.Column("module_code", sa.String(64), nullable=True),
            sa.Column("capability", sa.String(120), nullable=False),
            sa.Column("effect", sa.String(16), nullable=False, server_default="allow"),
            sa.Column("target_roles_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("target_company_ids_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("target_user_ids_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("target_external_types_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_entitlements_code", "platform_entitlements", ["code"], unique=True)
        op.create_index("ix_platform_entitlements_module", "platform_entitlements", ["module_code"])

    if not _has_table("platform_external_user_types"):
        op.create_table(
            "platform_external_user_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(40), nullable=False),
            sa.Column("name_en", sa.String(120), nullable=False),
            sa.Column("name_tr", sa.String(120), nullable=False),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("description_tr", sa.Text(), nullable=True),
            sa.Column("isolation_rules_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("default_scopes_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("can_see_budgets", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_external_user_types_code", "platform_external_user_types", ["code"], unique=True)

    if not _has_table("platform_webhook_subscriptions"):
        op.create_table(
            "platform_webhook_subscriptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("target_url", sa.String(1024), nullable=False),
            sa.Column("secret_hash", sa.String(255), nullable=False),
            sa.Column("secret_prefix", sa.String(16), nullable=False),
            sa.Column("event_types_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if not _has_table("platform_webhook_deliveries"):
        op.create_table(
            "platform_webhook_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "subscription_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_webhook_subscriptions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(120), nullable=False),
            sa.Column("payload_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("signature_header", sa.String(255), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("http_status", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_webhook_deliveries_sub", "platform_webhook_deliveries", ["subscription_id"])

    if not _has_table("platform_integrations"):
        op.create_table(
            "platform_integrations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("name_en", sa.String(160), nullable=False),
            sa.Column("name_tr", sa.String(160), nullable=False),
            sa.Column("category", sa.String(64), nullable=False, server_default="general"),
            sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("description_tr", sa.Text(), nullable=True),
            sa.Column("env_keys_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("docs_url", sa.String(512), nullable=True),
            sa.Column("configured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("block_reason", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_integrations_code", "platform_integrations", ["code"], unique=True)

    if not _has_table("platform_branding_configs"):
        op.create_table(
            "platform_branding_configs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("display_name_en", sa.String(160), nullable=False, server_default="InvestHome"),
            sa.Column("display_name_tr", sa.String(160), nullable=False, server_default="InvestHome"),
            sa.Column("logo_url", sa.String(1024), nullable=True),
            sa.Column("favicon_url", sa.String(1024), nullable=True),
            sa.Column("primary_color", sa.String(32), nullable=True),
            sa.Column("accent_color", sa.String(32), nullable=True),
            sa.Column("secondary_color", sa.String(32), nullable=True),
            sa.Column("support_email", sa.String(255), nullable=True),
            sa.Column("footer_en", sa.Text(), nullable=True),
            sa.Column("footer_tr", sa.Text(), nullable=True),
            sa.Column("allowed_token_keys_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
            sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_branding_configs_code", "platform_branding_configs", ["code"], unique=True)

    if not _has_table("platform_external_access_audits"):
        op.create_table(
            "platform_external_access_audits",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("external_type", sa.String(40), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("resource", sa.String(120), nullable=False),
            sa.Column("resource_id", sa.String(64), nullable=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("outcome", sa.String(32), nullable=False, server_default="allowed"),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_ext_audit_actor", "platform_external_access_audits", ["actor_user_id"])
        op.create_index("ix_platform_ext_audit_type", "platform_external_access_audits", ["external_type"])
        op.create_index("ix_platform_ext_audit_created", "platform_external_access_audits", ["created_at"])


def downgrade() -> None:
    # Non-destructive preference: drop only G15A tables; keep flag columns
    for table in (
        "platform_external_access_audits",
        "platform_webhook_deliveries",
        "platform_webhook_subscriptions",
        "platform_branding_configs",
        "platform_integrations",
        "platform_external_user_types",
        "platform_entitlements",
        "platform_modules",
    ):
        if _has_table(table):
            op.drop_table(table)
