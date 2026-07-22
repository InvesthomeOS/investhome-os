"""CRM company management tables.

Revision ID: 0033_crm_companies
Revises: 0032_crm_contact_management
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_crm_companies"
down_revision: str | None = "0032_crm_contact_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("company_type", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=30), server_default="new", nullable=False),
        sa.Column("registration_number", sa.String(length=80), nullable=True),
        sa.Column("tax_id", sa.String(length=80), nullable=True),
        sa.Column("ein", sa.String(length=80), nullable=True),
        sa.Column("duns_number", sa.String(length=20), nullable=True),
        sa.Column("incorporation_date", sa.Date(), nullable=True),
        sa.Column("incorporation_country", sa.String(length=100), nullable=True),
        sa.Column("incorporation_state", sa.String(length=120), nullable=True),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("secondary_emails", sa.JSON(), nullable=True),
        sa.Column("primary_phone", sa.String(length=50), nullable=True),
        sa.Column("secondary_phones", sa.JSON(), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("annual_revenue", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("relationship_status", sa.String(length=20), server_default="unknown", nullable=False),
        sa.Column("relationship_strength", sa.String(length=20), server_default="moderate", nullable=False),
        sa.Column("relationship_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("parent_company_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("legal_data", sa.JSON(), nullable=True),
        sa.Column("compliance_data", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_company_id"], ["crm_companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_companies_display_name", "crm_companies", ["display_name"])
    op.create_index("ix_crm_companies_legal_name", "crm_companies", ["legal_name"])
    op.create_index("ix_crm_companies_company_type", "crm_companies", ["company_type"])
    op.create_index("ix_crm_companies_status", "crm_companies", ["status"])
    op.create_index("ix_crm_companies_primary_email", "crm_companies", ["primary_email"])
    op.create_index("ix_crm_companies_domain", "crm_companies", ["domain"])
    op.create_index("ix_crm_companies_ein", "crm_companies", ["ein"])
    op.create_index("ix_crm_companies_parent_company_id", "crm_companies", ["parent_company_id"])

    op.create_table(
        "crm_company_type_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("company_type", sa.String(length=40), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "company_type", name="uq_crm_company_type"),
    )

    op.create_table(
        "crm_company_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("address_type", sa.String(length=20), server_default="headquarters", nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state_province", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_company_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="other", nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("relationship_type", sa.String(length=60), nullable=True),
        sa.Column("ownership_percent", sa.Float(), nullable=True),
        sa.Column("signing_authority", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "contact_id", name="uq_crm_company_contact"),
    )

    op.create_table(
        "crm_company_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_company_id", sa.Uuid(), nullable=False),
        sa.Column("target_company_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("is_reciprocal", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("strength", sa.String(length=20), server_default="moderate", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_company_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["crm_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "tag_id", name="uq_crm_company_tag"),
    )

    op.create_table(
        "crm_company_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("columns", sa.JSON(), nullable=True),
        sa.Column("sort_by", sa.String(length=60), nullable=True),
        sa.Column("sort_order", sa.String(length=4), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    profile_tables = [
        "crm_company_financial_profiles",
        "crm_company_investment_profiles",
        "crm_company_brokerage_profiles",
        "crm_company_lender_profiles",
        "crm_company_vendor_profiles",
        "crm_company_law_firm_profiles",
        "crm_company_property_management_profiles",
    ]
    for table in profile_tables:
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("company_id", sa.Uuid(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id"),
        )

    op.add_column("crm_company_financial_profiles", sa.Column("credit_rating", sa.String(length=20), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("annual_revenue", sa.Float(), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("net_worth", sa.Float(), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("total_assets", sa.Float(), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("total_liabilities", sa.Float(), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("fiscal_year_end", sa.String(length=20), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("crm_company_financial_profiles", sa.Column("bank_name", sa.String(length=255), nullable=True))

    op.add_column("crm_company_investment_profiles", sa.Column("aum", sa.Float(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("investment_focus", sa.JSON(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("preferred_asset_classes", sa.JSON(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("preferred_regions", sa.JSON(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("ticket_size_min", sa.Float(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("ticket_size_max", sa.Float(), nullable=True))
    op.add_column("crm_company_investment_profiles", sa.Column("fund_count", sa.Integer(), nullable=True))

    op.add_column("crm_company_brokerage_profiles", sa.Column("license_number", sa.String(length=80), nullable=True))
    op.add_column("crm_company_brokerage_profiles", sa.Column("license_state", sa.String(length=60), nullable=True))
    op.add_column("crm_company_brokerage_profiles", sa.Column("specialization", sa.String(length=120), nullable=True))
    op.add_column("crm_company_brokerage_profiles", sa.Column("market_coverage", sa.JSON(), nullable=True))
    op.add_column("crm_company_brokerage_profiles", sa.Column("agent_count", sa.Integer(), nullable=True))

    op.add_column("crm_company_lender_profiles", sa.Column("lender_type", sa.String(length=60), nullable=True))
    op.add_column("crm_company_lender_profiles", sa.Column("nmls_id", sa.String(length=40), nullable=True))
    op.add_column("crm_company_lender_profiles", sa.Column("loan_types", sa.JSON(), nullable=True))
    op.add_column("crm_company_lender_profiles", sa.Column("max_loan_amount", sa.Float(), nullable=True))
    op.add_column("crm_company_lender_profiles", sa.Column("min_credit_score", sa.Integer(), nullable=True))

    op.add_column("crm_company_vendor_profiles", sa.Column("vendor_category", sa.String(length=120), nullable=True))
    op.add_column("crm_company_vendor_profiles", sa.Column("payment_terms", sa.String(length=60), nullable=True))
    op.add_column("crm_company_vendor_profiles", sa.Column("contract_status", sa.String(length=60), nullable=True))
    op.add_column("crm_company_vendor_profiles", sa.Column("insurance_verified", sa.Boolean(), server_default="false", nullable=False))

    op.add_column("crm_company_law_firm_profiles", sa.Column("bar_number", sa.String(length=60), nullable=True))
    op.add_column("crm_company_law_firm_profiles", sa.Column("practice_areas", sa.JSON(), nullable=True))
    op.add_column("crm_company_law_firm_profiles", sa.Column("attorney_count", sa.Integer(), nullable=True))

    op.add_column("crm_company_property_management_profiles", sa.Column("units_managed", sa.Integer(), nullable=True))
    op.add_column("crm_company_property_management_profiles", sa.Column("property_types", sa.JSON(), nullable=True))
    op.add_column("crm_company_property_management_profiles", sa.Column("service_areas", sa.JSON(), nullable=True))
    op.add_column("crm_company_property_management_profiles", sa.Column("license_number", sa.String(length=80), nullable=True))


def downgrade() -> None:
    for table in reversed([
        "crm_company_property_management_profiles",
        "crm_company_law_firm_profiles",
        "crm_company_vendor_profiles",
        "crm_company_lender_profiles",
        "crm_company_brokerage_profiles",
        "crm_company_investment_profiles",
        "crm_company_financial_profiles",
        "crm_company_saved_views",
        "crm_company_tags",
        "crm_company_relationships",
        "crm_company_contacts",
        "crm_company_addresses",
        "crm_company_type_assignments",
    ]):
        op.drop_table(table)
    op.drop_index("ix_crm_companies_parent_company_id", table_name="crm_companies")
    op.drop_index("ix_crm_companies_ein", table_name="crm_companies")
    op.drop_index("ix_crm_companies_domain", table_name="crm_companies")
    op.drop_index("ix_crm_companies_primary_email", table_name="crm_companies")
    op.drop_index("ix_crm_companies_status", table_name="crm_companies")
    op.drop_index("ix_crm_companies_company_type", table_name="crm_companies")
    op.drop_index("ix_crm_companies_legal_name", table_name="crm_companies")
    op.drop_index("ix_crm_companies_display_name", table_name="crm_companies")
    op.drop_table("crm_companies")
