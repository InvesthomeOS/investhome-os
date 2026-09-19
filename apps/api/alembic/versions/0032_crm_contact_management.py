"""CRM contact management extensions.

Revision ID: 0032_crm_contact_management
Revises: 0031_crm_contacts
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_crm_contact_management"
down_revision: str | None = "0031_crm_contacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crm_contacts", sa.Column("job_title", sa.String(length=120), nullable=True))
    op.add_column("crm_contacts", sa.Column("department", sa.String(length=120), nullable=True))
    op.add_column("crm_contacts", sa.Column("linkedin_url", sa.String(length=500), nullable=True))
    op.add_column("crm_contacts", sa.Column("whatsapp", sa.String(length=50), nullable=True))
    op.add_column("crm_contacts", sa.Column("website", sa.String(length=500), nullable=True))
    op.add_column("crm_contacts", sa.Column("address_line1", sa.String(length=255), nullable=True))
    op.add_column("crm_contacts", sa.Column("address_line2", sa.String(length=255), nullable=True))
    op.add_column("crm_contacts", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("crm_contacts", sa.Column("state_province", sa.String(length=120), nullable=True))
    op.add_column("crm_contacts", sa.Column("postal_code", sa.String(length=30), nullable=True))
    op.add_column("crm_contacts", sa.Column("country", sa.String(length=100), nullable=True))
    op.add_column(
        "crm_contacts",
        sa.Column("lifecycle_stage", sa.String(length=30), server_default="new", nullable=False),
    )
    op.add_column(
        "crm_contacts",
        sa.Column("relationship_status", sa.String(length=20), server_default="unknown", nullable=False),
    )
    op.add_column(
        "crm_contacts",
        sa.Column("relationship_strength", sa.String(length=20), server_default="moderate", nullable=False),
    )
    op.add_column(
        "crm_contacts",
        sa.Column("priority", sa.String(length=20), server_default="normal", nullable=False),
    )
    op.add_column("crm_contacts", sa.Column("source", sa.String(length=120), nullable=True))
    op.add_column("crm_contacts", sa.Column("referred_by_contact_id", sa.Uuid(), nullable=True))
    op.add_column("crm_contacts", sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_contacts", sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "crm_contacts",
        sa.Column("relationship_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "crm_contacts",
        sa.Column("engagement_score", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("crm_contacts", sa.Column("compliance_data", sa.JSON(), nullable=True))
    op.add_column("crm_contacts", sa.Column("communication_prefs", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_crm_contacts_referred_by",
        "crm_contacts",
        "crm_contacts",
        ["referred_by_contact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_crm_contacts_lifecycle_stage", "crm_contacts", ["lifecycle_stage"])
    op.create_index("ix_crm_contacts_priority", "crm_contacts", ["priority"])
    op.create_index("ix_crm_contacts_primary_email", "crm_contacts", ["primary_email"])
    op.create_index("ix_crm_contacts_primary_phone", "crm_contacts", ["primary_phone"])
    op.create_index("ix_crm_contacts_next_follow_up_at", "crm_contacts", ["next_follow_up_at"])

    op.create_table(
        "crm_contact_type_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("contact_type", sa.String(length=40), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", "contact_type", name="uq_crm_contact_type"),
    )
    op.create_index("ix_crm_contact_type_assignments_contact_id", "crm_contact_type_assignments", ["contact_id"])

    op.create_table(
        "crm_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "crm_contact_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["crm_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", "tag_id", name="uq_crm_contact_tag"),
    )

    op.create_table(
        "crm_contact_investment_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("investor_type", sa.String(length=60), nullable=True),
        sa.Column("accreditation_status", sa.String(length=60), nullable=True),
        sa.Column("risk_profile", sa.String(length=60), nullable=True),
        sa.Column("investment_capacity_min", sa.Float(), nullable=True),
        sa.Column("investment_capacity_max", sa.Float(), nullable=True),
        sa.Column("preferred_asset_classes", sa.JSON(), nullable=True),
        sa.Column("preferred_regions", sa.JSON(), nullable=True),
        sa.Column("investment_timeline", sa.String(length=60), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id"),
    )

    op.create_table(
        "crm_contact_buyer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("preferred_locations", sa.JSON(), nullable=True),
        sa.Column("property_types", sa.JSON(), nullable=True),
        sa.Column("bedroom_min", sa.Integer(), nullable=True),
        sa.Column("financing_status", sa.String(length=60), nullable=True),
        sa.Column("purchase_timeline", sa.String(length=60), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id"),
    )

    op.create_table(
        "crm_contact_broker_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("license_number", sa.String(length=80), nullable=True),
        sa.Column("brokerage_name", sa.String(length=255), nullable=True),
        sa.Column("specialization", sa.String(length=120), nullable=True),
        sa.Column("service_areas", sa.JSON(), nullable=True),
        sa.Column("commission_structure", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id"),
    )

    op.create_table(
        "crm_contact_vendor_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_category", sa.String(length=80), nullable=True),
        sa.Column("service_scope", sa.String(length=255), nullable=True),
        sa.Column("contract_status", sa.String(length=60), nullable=True),
        sa.Column("payment_terms", sa.String(length=120), nullable=True),
        sa.Column("insurance_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id"),
    )

    op.create_table(
        "crm_contact_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("sort_by", sa.String(length=40), nullable=True),
        sa.Column("sort_dir", sa.String(length=4), nullable=True),
        sa.Column("columns_json", sa.JSON(), nullable=True),
        sa.Column("density", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_contact_merge_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("survivor_contact_id", sa.Uuid(), nullable=True),
        sa.Column("merged_contact_id", sa.Uuid(), nullable=False),
        sa.Column("merged_snapshot", sa.JSON(), nullable=True),
        sa.Column("merged_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["merged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["survivor_contact_id"], ["crm_contacts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_contact_duplicate_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id_a", sa.Uuid(), nullable=False),
        sa.Column("contact_id_b", sa.Uuid(), nullable=False),
        sa.Column("match_reason", sa.String(length=60), nullable=False),
        sa.Column("match_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id_a"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id_b"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("crm_contact_duplicate_candidates")
    op.drop_table("crm_contact_merge_history")
    op.drop_table("crm_contact_saved_views")
    op.drop_table("crm_contact_vendor_profiles")
    op.drop_table("crm_contact_broker_profiles")
    op.drop_table("crm_contact_buyer_profiles")
    op.drop_table("crm_contact_investment_profiles")
    op.drop_table("crm_contact_tags")
    op.drop_table("crm_tags")
    op.drop_index("ix_crm_contact_type_assignments_contact_id", table_name="crm_contact_type_assignments")
    op.drop_table("crm_contact_type_assignments")
    op.drop_index("ix_crm_contacts_next_follow_up_at", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_primary_phone", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_primary_email", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_priority", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_lifecycle_stage", table_name="crm_contacts")
    op.drop_constraint("fk_crm_contacts_referred_by", "crm_contacts", type_="foreignkey")
    for col in (
        "communication_prefs",
        "compliance_data",
        "engagement_score",
        "relationship_score",
        "next_follow_up_at",
        "last_contact_at",
        "referred_by_contact_id",
        "source",
        "priority",
        "relationship_strength",
        "relationship_status",
        "lifecycle_stage",
        "country",
        "postal_code",
        "state_province",
        "city",
        "address_line2",
        "address_line1",
        "website",
        "whatsapp",
        "linkedin_url",
        "department",
        "job_title",
    ):
        op.drop_column("crm_contacts", col)
