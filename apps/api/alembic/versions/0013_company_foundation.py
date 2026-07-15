"""Company foundation tables.

Revision ID: 0013_company_foundation
Revises: 0012_drawing_intelligence
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_company_foundation"
down_revision: str | None = "0012_drawing_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("short_name", sa.String(length=80), nullable=True),
        sa.Column("company_code", sa.String(length=50), nullable=False),
        sa.Column("slogan", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("primary_phone", sa.String(length=50), nullable=True),
        sa.Column("tax_id", sa.String(length=100), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("state_or_region", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("default_language", sa.String(length=5), server_default="tr", nullable=False),
        sa.Column("default_timezone", sa.String(length=64), server_default="Europe/Istanbul", nullable=False),
        sa.Column("default_currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("default_measurement_system", sa.String(length=20), server_default="imperial", nullable=False),
        sa.Column("default_area_unit", sa.String(length=20), server_default="square_feet", nullable=False),
        sa.Column("default_date_format", sa.String(length=30), server_default="DD/MM/YYYY", nullable=False),
        sa.Column("default_number_format", sa.String(length=30), server_default="1.234,56", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_code"),
    )

    op.create_table(
        "offices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("office_name", sa.String(length=255), nullable=False),
        sa.Column("office_code", sa.String(length=50), nullable=False),
        sa.Column("office_type", sa.String(length=30), server_default="other", nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("state_or_region", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("default_currency", sa.String(length=3), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "office_code", name="uq_offices_company_code"),
    )
    op.create_index("ix_offices_company_id", "offices", ["company_id"])

    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("brand_name", sa.String(length=255), nullable=False),
        sa.Column("brand_code", sa.String(length=50), nullable=False),
        sa.Column("legal_display_name", sa.String(length=255), nullable=True),
        sa.Column("slogan", sa.String(length=500), nullable=True),
        sa.Column("brand_description", sa.Text(), nullable=True),
        sa.Column("logo_primary_document_id", sa.Uuid(), nullable=True),
        sa.Column("logo_secondary_document_id", sa.Uuid(), nullable=True),
        sa.Column("logo_monochrome_document_id", sa.Uuid(), nullable=True),
        sa.Column("favicon_document_id", sa.Uuid(), nullable=True),
        sa.Column("primary_color", sa.String(length=20), nullable=True),
        sa.Column("secondary_color", sa.String(length=20), nullable=True),
        sa.Column("accent_color", sa.String(length=20), nullable=True),
        sa.Column("background_color", sa.String(length=20), nullable=True),
        sa.Column("surface_color", sa.String(length=20), nullable=True),
        sa.Column("text_primary_color", sa.String(length=20), nullable=True),
        sa.Column("text_secondary_color", sa.String(length=20), nullable=True),
        sa.Column("success_color", sa.String(length=20), nullable=True),
        sa.Column("warning_color", sa.String(length=20), nullable=True),
        sa.Column("error_color", sa.String(length=20), nullable=True),
        sa.Column("font_heading", sa.String(length=120), nullable=True),
        sa.Column("font_body", sa.String(length=120), nullable=True),
        sa.Column("font_monospace", sa.String(length=120), nullable=True),
        sa.Column("border_radius_style", sa.String(length=30), nullable=True),
        sa.Column("standard_disclaimer_tr", sa.Text(), nullable=True),
        sa.Column("standard_disclaimer_en", sa.Text(), nullable=True),
        sa.Column("email_footer_tr", sa.Text(), nullable=True),
        sa.Column("email_footer_en", sa.Text(), nullable=True),
        sa.Column("social_links", sa.JSON(), nullable=True),
        sa.Column("contact_information", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["logo_primary_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["logo_secondary_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["logo_monochrome_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["favicon_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "brand_code", name="uq_brands_company_code"),
    )
    op.create_index("ix_brand_profiles_company_id", "brand_profiles", ["company_id"])

    op.create_table(
        "brand_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_profile_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=True),
        sa.Column("usage_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["brand_profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_assets_brand_profile_id", "brand_assets", ["brand_profile_id"])

    op.create_table(
        "system_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("preference_key", sa.String(length=120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("preference_key"),
    )
    op.create_index("ix_system_preferences_category", "system_preferences", ["category"])

    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manager_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_departments_company_code"),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manager_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "code", name="uq_teams_department_code"),
    )

    op.create_table(
        "user_departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "department_id", name="uq_user_departments"),
    )

    op.create_table(
        "user_teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "team_id", name="uq_user_teams"),
    )


def downgrade() -> None:
    op.drop_table("user_teams")
    op.drop_table("user_departments")
    op.drop_table("teams")
    op.drop_table("departments")
    op.drop_index("ix_system_preferences_category", table_name="system_preferences")
    op.drop_table("system_preferences")
    op.drop_index("ix_brand_assets_brand_profile_id", table_name="brand_assets")
    op.drop_table("brand_assets")
    op.drop_index("ix_brand_profiles_company_id", table_name="brand_profiles")
    op.drop_table("brand_profiles")
    op.drop_index("ix_offices_company_id", table_name="offices")
    op.drop_table("offices")
    op.drop_table("company_profiles")
