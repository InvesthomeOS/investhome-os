"""Live communication accounts, matching, and dedupe foundation.

Revision ID: 0078_live_communication_foundation
Revises: 0077_document_link_hidden_from_view
Create Date: 2026-09-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0078_live_communication_foundation"
down_revision: str | None = "0077_document_link_hidden_from_view"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_user_communication_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel_type", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("identity", sa.String(length=255), nullable=False),
        sa.Column("account_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="not_connected"),
        sa.Column("health", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_user_comm_accounts_user", "crm_user_communication_accounts", ["user_id"])
    op.create_index("ix_crm_user_comm_accounts_channel", "crm_user_communication_accounts", ["channel_type"])
    op.create_index("ix_crm_user_comm_accounts_status", "crm_user_communication_accounts", ["status"])
    op.create_index(
        "uq_crm_user_comm_accounts_identity",
        "crm_user_communication_accounts",
        ["channel_type", "identity"],
        unique=True,
    )

    op.add_column("crm_communications", sa.Column("account_id", sa.Uuid(), nullable=True))
    op.add_column(
        "crm_communications",
        sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"),
    )
    op.add_column(
        "crm_communications",
        sa.Column("match_status", sa.String(length=20), nullable=False, server_default="matched"),
    )
    op.add_column("crm_communications", sa.Column("contact_id", sa.Uuid(), nullable=True))
    op.add_column("crm_communications", sa.Column("agreement_id", sa.Uuid(), nullable=True))
    op.add_column("crm_communications", sa.Column("sender_identity", sa.String(length=255), nullable=True))
    op.add_column("crm_communications", sa.Column("recipient_identities", sa.JSON(), nullable=True))
    op.add_column("crm_communications", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_communications", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("crm_communications", sa.Column("conversation_key", sa.String(length=255), nullable=True))
    op.add_column("crm_communications", sa.Column("raw_source", sa.Text(), nullable=True))
    op.add_column("crm_communications", sa.Column("suggested_matches", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_crm_communications_account_id",
        "crm_communications",
        "crm_user_communication_accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_crm_communications_contact_id",
        "crm_communications",
        "crm_contacts",
        ["contact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_crm_communications_agreement_id",
        "crm_communications",
        "crm_agreements",
        ["agreement_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_crm_communications_account", "crm_communications", ["account_id"])
    op.create_index("ix_crm_communications_source", "crm_communications", ["source"])
    op.create_index("ix_crm_communications_match_status", "crm_communications", ["match_status"])
    op.create_index("ix_crm_communications_contact", "crm_communications", ["contact_id"])
    op.create_index("ix_crm_communications_content_hash", "crm_communications", ["content_hash"])
    op.create_index("ix_crm_communications_occurred", "crm_communications", ["occurred_at"])
    op.create_index("ix_crm_communications_conversation", "crm_communications", ["conversation_key"])
    op.create_index(
        "uq_crm_comm_provider_message",
        "crm_communications",
        ["source", "external_provider_id"],
        unique=True,
        postgresql_where=sa.text("external_provider_id IS NOT NULL"),
    )

    op.add_column("crm_communication_attachments", sa.Column("document_id", sa.Uuid(), nullable=True))
    op.add_column("crm_communication_attachments", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_crm_comm_attach_document_id",
        "crm_communication_attachments",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_crm_comm_attach_document", "crm_communication_attachments", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_comm_attach_document", table_name="crm_communication_attachments")
    op.drop_constraint("fk_crm_comm_attach_document_id", "crm_communication_attachments", type_="foreignkey")
    op.drop_column("crm_communication_attachments", "checksum")
    op.drop_column("crm_communication_attachments", "document_id")
    op.drop_index("uq_crm_comm_provider_message", table_name="crm_communications")
    op.drop_index("ix_crm_communications_conversation", table_name="crm_communications")
    op.drop_index("ix_crm_communications_occurred", table_name="crm_communications")
    op.drop_index("ix_crm_communications_content_hash", table_name="crm_communications")
    op.drop_index("ix_crm_communications_contact", table_name="crm_communications")
    op.drop_index("ix_crm_communications_match_status", table_name="crm_communications")
    op.drop_index("ix_crm_communications_source", table_name="crm_communications")
    op.drop_index("ix_crm_communications_account", table_name="crm_communications")
    op.drop_constraint("fk_crm_communications_agreement_id", "crm_communications", type_="foreignkey")
    op.drop_constraint("fk_crm_communications_contact_id", "crm_communications", type_="foreignkey")
    op.drop_constraint("fk_crm_communications_account_id", "crm_communications", type_="foreignkey")
    op.drop_column("crm_communications", "suggested_matches")
    op.drop_column("crm_communications", "raw_source")
    op.drop_column("crm_communications", "conversation_key")
    op.drop_column("crm_communications", "content_hash")
    op.drop_column("crm_communications", "occurred_at")
    op.drop_column("crm_communications", "recipient_identities")
    op.drop_column("crm_communications", "sender_identity")
    op.drop_column("crm_communications", "agreement_id")
    op.drop_column("crm_communications", "contact_id")
    op.drop_column("crm_communications", "match_status")
    op.drop_column("crm_communications", "source")
    op.drop_column("crm_communications", "account_id")
    op.drop_index("uq_crm_user_comm_accounts_identity", table_name="crm_user_communication_accounts")
    op.drop_index("ix_crm_user_comm_accounts_status", table_name="crm_user_communication_accounts")
    op.drop_index("ix_crm_user_comm_accounts_channel", table_name="crm_user_communication_accounts")
    op.drop_index("ix_crm_user_comm_accounts_user", table_name="crm_user_communication_accounts")
    op.drop_table("crm_user_communication_accounts")
