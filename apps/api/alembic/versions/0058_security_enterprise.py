"""Security & enterprise admin foundation — Product Polish P11.

Revision ID: 0058_security_enterprise
Revises: 0057_bi_saved_reports
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0058_security_enterprise"
down_revision: str | None = "0057_bi_saved_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if _has_table("users"):
        if not _has_column("users", "mfa_enabled"):
            op.add_column(
                "users",
                sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
            )
        if not _has_column("users", "mfa_method"):
            op.add_column("users", sa.Column("mfa_method", sa.String(32), nullable=True))
        if not _has_column("users", "mfa_enforced_at"):
            op.add_column(
                "users",
                sa.Column("mfa_enforced_at", sa.DateTime(timezone=True), nullable=True),
            )

    if not _has_table("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_jti", sa.String(64), nullable=False, unique=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(512), nullable=True),
            sa.Column("device_label", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoke_reason", sa.String(100), nullable=True),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_token_jti", "auth_sessions", ["token_jti"], unique=True)

    if not _has_table("platform_api_keys"):
        op.create_table(
            "platform_api_keys",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "created_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("key_prefix", sa.String(16), nullable=False),
            sa.Column("key_hash", sa.String(255), nullable=False),
            sa.Column("scopes_json", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_platform_api_keys_prefix", "platform_api_keys", ["key_prefix"])

    if not _has_table("temporary_permission_grants"):
        op.create_table(
            "temporary_permission_grants",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "granted_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("resource", sa.String(50), nullable=False),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("reason", sa.String(500), nullable=True),
            sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_temp_perm_grants_user_id", "temporary_permission_grants", ["user_id"])

    if not _has_table("feature_flag_overrides"):
        op.create_table(
            "feature_flag_overrides",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("flag_key", sa.String(100), nullable=False, unique=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("rollout_percent", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("target_roles_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column(
                "updated_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if not _has_table("security_incidents"):
        op.create_table(
            "security_incidents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("severity", sa.String(40), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(40), nullable=False, server_default="open"),
            sa.Column("category", sa.String(80), nullable=False, server_default="security"),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column(
                "reported_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "assignee_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for table in (
        "security_incidents",
        "feature_flag_overrides",
        "temporary_permission_grants",
        "platform_api_keys",
        "auth_sessions",
    ):
        if _has_table(table):
            op.drop_table(table)
    if _has_table("users"):
        for col in ("mfa_enforced_at", "mfa_method", "mfa_enabled"):
            if _has_column("users", col):
                op.drop_column("users", col)
