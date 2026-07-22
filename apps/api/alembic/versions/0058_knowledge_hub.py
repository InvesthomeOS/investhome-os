"""Knowledge Hub foundation — collections, categories, review, retention.

Revision ID: 0058_knowledge_hub
Revises: 0057_bi_saved_reports
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0058_knowledge_hub"
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
    if not _has_table("knowledge_categories"):
        op.create_table(
            "knowledge_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("name_en", sa.String(200), nullable=False),
            sa.Column("name_tr", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("code", name="uq_knowledge_categories_code"),
        )
        op.create_index("ix_knowledge_categories_active", "knowledge_categories", ["is_active"])

    if not _has_table("knowledge_collections"):
        op.create_table(
            "knowledge_collections",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("collection_type", sa.String(30), nullable=False, server_default="manual"),
            sa.Column("smart_rules_json", sa.Text(), nullable=True),
            sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("ix_knowledge_collections_type", "knowledge_collections", ["collection_type"])
        op.create_index("ix_knowledge_collections_owner", "knowledge_collections", ["owner_user_id"])

    if not _has_table("knowledge_collection_items"):
        op.create_table(
            "knowledge_collection_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "collection_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "document_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("added_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "collection_id",
                "document_id",
                name="uq_knowledge_collection_document",
            ),
        )
        op.create_index(
            "ix_knowledge_collection_items_collection",
            "knowledge_collection_items",
            ["collection_id"],
        )
        op.create_index(
            "ix_knowledge_collection_items_document",
            "knowledge_collection_items",
            ["document_id"],
        )

    if not _has_table("knowledge_review_items"):
        op.create_table(
            "knowledge_review_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "document_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("reason", sa.String(60), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.String(20), nullable=True),
            sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("ix_knowledge_review_status", "knowledge_review_items", ["status"])
        op.create_index("ix_knowledge_review_reason", "knowledge_review_items", ["reason"])
        op.create_index("ix_knowledge_review_document", "knowledge_review_items", ["document_id"])

    if not _has_table("knowledge_retention_policies"):
        op.create_table(
            "knowledge_retention_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category_code", sa.String(80), nullable=True),
            sa.Column("retention_days", sa.Integer(), nullable=True),
            sa.Column("action_on_expiry", sa.String(40), nullable=False, server_default="notify"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("legal_hold_capable", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    if not _has_table("knowledge_settings"):
        op.create_table(
            "knowledge_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("key", sa.String(120), nullable=False),
            sa.Column("value_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("key", name="uq_knowledge_settings_key"),
        )

    # Additive document flags for Knowledge Hub lifecycle (never overwrite originals)
    if _has_table("documents"):
        if not _has_column("documents", "review_status"):
            op.add_column(
                "documents",
                sa.Column("review_status", sa.String(30), nullable=True),
            )
        if not _has_column("documents", "legal_hold"):
            op.add_column(
                "documents",
                sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default="false"),
            )
        if not _has_column("documents", "publish_to_website"):
            op.add_column(
                "documents",
                sa.Column(
                    "publish_to_website",
                    sa.Boolean(),
                    nullable=False,
                    server_default="false",
                ),
            )
        if not _has_column("documents", "malware_scan_status"):
            op.add_column(
                "documents",
                sa.Column("malware_scan_status", sa.String(40), nullable=True),
            )
        if not _has_column("documents", "category_code"):
            op.add_column(
                "documents",
                sa.Column("category_code", sa.String(80), nullable=True),
            )
            op.create_index("ix_documents_category_code", "documents", ["category_code"])


def downgrade() -> None:
    if _has_table("documents"):
        for col, idx in (
            ("category_code", "ix_documents_category_code"),
            ("malware_scan_status", None),
            ("publish_to_website", None),
            ("legal_hold", None),
            ("review_status", None),
        ):
            if _has_column("documents", col):
                if idx:
                    op.drop_index(idx, table_name="documents")
                op.drop_column("documents", col)

    for table in (
        "knowledge_settings",
        "knowledge_retention_policies",
        "knowledge_review_items",
        "knowledge_collection_items",
        "knowledge_collections",
        "knowledge_categories",
    ):
        if _has_table(table):
            op.drop_table(table)
