"""CRM global search — recent/saved searches, audit, FTS indexes.

Revision ID: 0037_crm_search
Revises: 0036_crm_communications
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_crm_search"
down_revision: str | None = "0036_crm_communications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_recent_searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("entity_types", sa.JSON(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("opened_result_id", sa.Uuid(), nullable=True),
        sa.Column("opened_entity_type", sa.String(length=40), nullable=True),
        sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_crm_recent_searches_user", "crm_recent_searches", ["user_id", "searched_at"])

    op.create_table(
        "crm_saved_searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query", sa.String(length=500), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("entity_types", sa.JSON(), nullable=True),
        sa.Column("sort_json", sa.JSON(), nullable=True),
        sa.Column("grouping", sa.String(length=40), nullable=True),
        sa.Column("visible_fields", sa.JSON(), nullable=True),
        sa.Column("view_mode", sa.String(length=20), nullable=False, server_default=sa.text("'list'")),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default=sa.text("'private'")),
        sa.Column("shared_with", sa.JSON(), nullable=True),
        sa.Column("notification_settings", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_crm_saved_searches_owner", "crm_saved_searches", ["owner_id"])

    op.create_table(
        "crm_search_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_crm_search_audit_user", "crm_search_audit_logs", ["user_id", "created_at"])

    # PostgreSQL full-text search vectors (no-op on SQLite test DB)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('simple',
                    coalesce(display_name, '') || ' ' ||
                    coalesce(first_name, '') || ' ' ||
                    coalesce(last_name, '') || ' ' ||
                    coalesce(primary_email, '') || ' ' ||
                    coalesce(primary_phone, '') || ' ' ||
                    coalesce(organization_name, '') || ' ' ||
                    coalesce(city, '') || ' ' ||
                    coalesce(notes, '')
                )
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_crm_contacts_search_vector ON crm_contacts USING GIN (search_vector)"
        )
        op.execute(
            """
            ALTER TABLE crm_companies ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('simple',
                    coalesce(display_name, '') || ' ' ||
                    coalesce(legal_name, '') || ' ' ||
                    coalesce(trade_name, '') || ' ' ||
                    coalesce(primary_email, '') || ' ' ||
                    coalesce(domain, '') || ' ' ||
                    coalesce(registration_number, '') || ' ' ||
                    coalesce(description, '')
                )
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_crm_companies_search_vector ON crm_companies USING GIN (search_vector)"
        )
        op.execute(
            """
            ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('simple',
                    coalesce(title, '') || ' ' ||
                    coalesce(summary, '') || ' ' ||
                    coalesce(description, '')
                )
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_crm_activities_search_vector ON crm_activities USING GIN (search_vector)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_crm_activities_search_vector")
        op.execute("ALTER TABLE crm_activities DROP COLUMN IF EXISTS search_vector")
        op.execute("DROP INDEX IF EXISTS ix_crm_companies_search_vector")
        op.execute("ALTER TABLE crm_companies DROP COLUMN IF EXISTS search_vector")
        op.execute("DROP INDEX IF EXISTS ix_crm_contacts_search_vector")
        op.execute("ALTER TABLE crm_contacts DROP COLUMN IF EXISTS search_vector")

    op.drop_index("ix_crm_search_audit_user", table_name="crm_search_audit_logs")
    op.drop_table("crm_search_audit_logs")
    op.drop_index("ix_crm_saved_searches_owner", table_name="crm_saved_searches")
    op.drop_table("crm_saved_searches")
    op.drop_index("ix_crm_recent_searches_user", table_name="crm_recent_searches")
    op.drop_table("crm_recent_searches")
