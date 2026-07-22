"""Project budget foundation — versions, lines, categories, cost codes, revisions.

Revision ID: 0049_project_budget_foundation
Revises: 0048_projects_foundation
Create Date: 2026-07-19

Strategy (Option B):
- Preserve legacy ``project_budgets`` unchanged for finance workspace / dashboard.
- Add normalized version/line/category/cost-code/revision tables.
- Seed system categories and a minimal internal cost-code set.
- Backfill one APPROVED current version per project that already has legacy rows,
  with lines mapped from those rows (``legacy_project_budget_id`` retained).

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "0049_project_budget_foundation"
down_revision: str | None = "0048_projects_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_CATEGORY_MAP = {
    "acquisition": "ACQ",
    "design": "SOFT",
    "architecture": "SOFT",
    "engineering": "SOFT",
    "permitting": "SOFT",
    "legal": "SOFT",
    "financing": "FIN",
    "construction": "HARD",
    "marketing": "MKT",
    "sales": "SALES",
    "leasing": "LEASE",
    "operations": "OPS",
    "contingency": "CONT",
    "taxes": "TAX",
    "insurance": "INS",
    "other": "OTHER",
}

SYSTEM_CATEGORIES = [
    ("LAND", "Land", "land", 10),
    ("ACQ", "Acquisition", "acquisition", 20),
    ("HARD", "Hard Costs", "hard_cost", 30),
    ("SOFT", "Soft Costs", "soft_cost", 40),
    ("FIN", "Financing", "financing", 50),
    ("MKT", "Marketing", "marketing", 60),
    ("SALES", "Sales", "sales", 70),
    ("LEASE", "Leasing", "leasing", 80),
    ("OPS", "Operating", "operating", 90),
    ("CONT", "Contingency", "contingency", 100),
    ("TAX", "Tax", "tax", 110),
    ("INS", "Insurance", "insurance", 120),
    ("PROF", "Professional Fees", "professional_fees", 130),
    ("DEVFEE", "Developer Fee", "developer_fee", 140),
    ("OTHER", "Other", "other", 150),
]

SYSTEM_COST_CODES = [
    ("01-000", "General Requirements", "HARD", 10),
    ("02-000", "Existing Conditions", "HARD", 20),
    ("03-000", "Concrete", "HARD", 30),
    ("04-000", "Masonry", "HARD", 40),
    ("05-000", "Metals", "HARD", 50),
    ("06-000", "Wood and Plastics", "HARD", 60),
    ("07-000", "Thermal and Moisture Protection", "HARD", 70),
    ("08-000", "Openings", "HARD", 80),
    ("09-000", "Finishes", "HARD", 90),
    ("21-000", "Fire Suppression", "HARD", 100),
    ("22-000", "Plumbing", "HARD", 110),
    ("23-000", "HVAC", "HARD", 120),
    ("26-000", "Electrical", "HARD", 130),
    ("31-000", "Earthwork", "HARD", 140),
    ("32-000", "Exterior Improvements", "HARD", 150),
    ("A-100", "Architecture", "SOFT", 160),
    ("E-100", "Engineering", "SOFT", 170),
    ("L-100", "Legal", "SOFT", 180),
    ("P-100", "Permits", "SOFT", 190),
    ("C-100", "Contingency Allowance", "CONT", 200),
]


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("project_budget_categories"):
        op.create_table(
            "project_budget_categories",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category_type", sa.String(length=50), nullable=False),
            sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("project_budget_categories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("company_id", "code", name="uq_project_budget_categories_company_code"),
        )
        op.create_index("ix_project_budget_categories_company_id", "project_budget_categories", ["company_id"])
        op.create_index("ix_project_budget_categories_parent_id", "project_budget_categories", ["parent_id"])
        op.create_index("ix_project_budget_categories_category_type", "project_budget_categories", ["category_type"])

    if not _has_table("project_cost_codes"):
        op.create_table(
            "project_cost_codes",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category_id", sa.Uuid(), sa.ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("company_id", "code", name="uq_project_cost_codes_company_code"),
        )
        op.create_index("ix_project_cost_codes_company_id", "project_cost_codes", ["company_id"])
        op.create_index("ix_project_cost_codes_category_id", "project_cost_codes", ["category_id"])
        op.create_index("ix_project_cost_codes_parent_id", "project_cost_codes", ["parent_id"])

    if not _has_table("project_budget_versions"):
        op.create_table(
            "project_budget_versions",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("project_id", "version_number", name="uq_project_budget_versions_project_version"),
        )
        op.create_index("ix_project_budget_versions_project_id", "project_budget_versions", ["project_id"])
        op.create_index("ix_project_budget_versions_status", "project_budget_versions", ["status"])
        op.create_index("ix_project_budget_versions_is_current", "project_budget_versions", ["is_current"])
        op.create_index("ix_project_budget_versions_company_id", "project_budget_versions", ["company_id"])

    if not _has_table("project_budget_lines"):
        op.create_table(
            "project_budget_lines",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("budget_version_id", sa.Uuid(), sa.ForeignKey("project_budget_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category_id", sa.Uuid(), sa.ForeignKey("project_budget_categories.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("cost_code_id", sa.Uuid(), sa.ForeignKey("project_cost_codes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("parent_line_id", sa.Uuid(), sa.ForeignKey("project_budget_lines.id", ondelete="SET NULL"), nullable=True),
            sa.Column("legacy_project_budget_id", sa.Uuid(), sa.ForeignKey("project_budgets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("line_number", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit", sa.String(length=50), nullable=True),
            sa.Column("unit_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("original_budget", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("approved_revisions", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("current_budget", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("committed_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("actual_cost", sa.Numeric(18, 2), nullable=True),
            sa.Column("forecast_to_complete", sa.Numeric(18, 2), nullable=True),
            sa.Column("forecast_at_completion", sa.Numeric(18, 2), nullable=True),
            sa.Column("variance", sa.Numeric(18, 2), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_summary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint(
                "budget_version_id", "line_number", name="uq_project_budget_lines_version_line_number"
            ),
        )
        op.create_index("ix_project_budget_lines_project_id", "project_budget_lines", ["project_id"])
        op.create_index("ix_project_budget_lines_budget_version_id", "project_budget_lines", ["budget_version_id"])
        op.create_index("ix_project_budget_lines_category_id", "project_budget_lines", ["category_id"])
        op.create_index("ix_project_budget_lines_cost_code_id", "project_budget_lines", ["cost_code_id"])
        op.create_index("ix_project_budget_lines_parent_line_id", "project_budget_lines", ["parent_line_id"])

    if not _has_table("project_budget_revisions"):
        op.create_table(
            "project_budget_revisions",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("budget_version_id", sa.Uuid(), sa.ForeignKey("project_budget_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("revision_number", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "budget_version_id",
                "revision_number",
                name="uq_project_budget_revisions_version_number",
            ),
        )
        op.create_index("ix_project_budget_revisions_project_id", "project_budget_revisions", ["project_id"])
        op.create_index(
            "ix_project_budget_revisions_budget_version_id", "project_budget_revisions", ["budget_version_id"]
        )
        op.create_index("ix_project_budget_revisions_status", "project_budget_revisions", ["status"])

    if not _has_table("project_budget_revision_lines"):
        op.create_table(
            "project_budget_revision_lines",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("revision_id", sa.Uuid(), sa.ForeignKey("project_budget_revisions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("budget_line_id", sa.Uuid(), sa.ForeignKey("project_budget_lines.id", ondelete="CASCADE"), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index(
            "ix_project_budget_revision_lines_revision_id", "project_budget_revision_lines", ["revision_id"]
        )
        op.create_index(
            "ix_project_budget_revision_lines_budget_line_id",
            "project_budget_revision_lines",
            ["budget_line_id"],
        )

    _seed_system_taxonomy()
    _backfill_from_legacy()


def _seed_system_taxonomy() -> None:
    bind = op.get_bind()
    existing = bind.execute(
        text("SELECT code FROM project_budget_categories WHERE company_id IS NULL AND is_system = true")
    ).fetchall()
    if existing:
        return

    category_ids: dict[str, str] = {}
    for code, name, category_type, sort_order in SYSTEM_CATEGORIES:
        cat_id = str(uuid.uuid4())
        category_ids[code] = cat_id
        bind.execute(
            text(
                """
                INSERT INTO project_budget_categories
                (id, company_id, code, name, description, category_type, parent_id,
                 sort_order, is_active, is_system, created_at, updated_at)
                VALUES
                (:id, NULL, :code, :name, NULL, :category_type, NULL,
                 :sort_order, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": cat_id,
                "code": code,
                "name": name,
                "category_type": category_type,
                "sort_order": sort_order,
            },
        )

    for code, name, category_code, sort_order in SYSTEM_COST_CODES:
        bind.execute(
            text(
                """
                INSERT INTO project_cost_codes
                (id, company_id, code, name, description, category_id, parent_id,
                 level, is_active, is_system, sort_order, created_at, updated_at)
                VALUES
                (:id, NULL, :code, :name, NULL, :category_id, NULL,
                 1, true, true, :sort_order, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "code": code,
                "name": name,
                "category_id": category_ids[category_code],
                "sort_order": sort_order,
            },
        )


def _backfill_from_legacy() -> None:
    bind = op.get_bind()
    if not _has_table("project_budgets"):
        return

    already = bind.execute(text("SELECT COUNT(*) FROM project_budget_versions")).scalar()
    if already and int(already) > 0:
        return

    category_rows = bind.execute(
        text("SELECT id, code FROM project_budget_categories WHERE company_id IS NULL")
    ).fetchall()
    category_by_code = {row[1]: row[0] for row in category_rows}
    default_category = category_by_code.get("OTHER")
    if default_category is None:
        return

    project_ids = bind.execute(text("SELECT DISTINCT project_id FROM project_budgets")).fetchall()
    for (project_id,) in project_ids:
        project = bind.execute(
            text("SELECT currency, company_id, project_name FROM projects WHERE id = :id"),
            {"id": project_id},
        ).fetchone()
        if project is None:
            continue
        currency, company_id, project_name = project
        version_id = str(uuid.uuid4())
        bind.execute(
            text(
                """
                INSERT INTO project_budget_versions
                (id, company_id, project_id, name, version_number, status, description,
                 currency, effective_date, approved_at, is_current, created_at, updated_at)
                VALUES
                (:id, :company_id, :project_id, :name, 1, 'approved',
                 'Backfilled from legacy project_budgets',
                 :currency, CURRENT_DATE, CURRENT_TIMESTAMP, true,
                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": version_id,
                "company_id": company_id,
                "project_id": project_id,
                "name": f"{project_name or 'Project'} — Legacy Budget v1",
                "currency": currency or "USD",
            },
        )

        legacy_rows = bind.execute(
            text(
                """
                SELECT id, budget_name, category, original_budget, revised_budget,
                       committed_amount, paid_amount, forecast_amount, currency, notes
                FROM project_budgets
                WHERE project_id = :project_id
                ORDER BY created_at ASC
                """
            ),
            {"project_id": project_id},
        ).fetchall()

        for index, row in enumerate(legacy_rows, start=1):
            (
                legacy_id,
                budget_name,
                category,
                original_budget,
                revised_budget,
                committed_amount,
                paid_amount,
                forecast_amount,
                row_currency,
                notes,
            ) = row
            cat_code = LEGACY_CATEGORY_MAP.get(str(category), "OTHER")
            category_id = category_by_code.get(cat_code, default_category)
            original = Decimal(str(original_budget or 0))
            revised = Decimal(str(revised_budget)) if revised_budget is not None else original
            approved_revisions = revised - original
            current = revised
            bind.execute(
                text(
                    """
                    INSERT INTO project_budget_lines
                    (id, company_id, project_id, budget_version_id, category_id, cost_code_id,
                     parent_line_id, legacy_project_budget_id, line_number, name, description,
                     original_budget, approved_revisions, current_budget, committed_cost,
                     actual_cost, forecast_at_completion, currency, notes, sort_order,
                     is_summary, is_active, created_at, updated_at)
                    VALUES
                    (:id, :company_id, :project_id, :budget_version_id, :category_id, NULL,
                     NULL, :legacy_id, :line_number, :name, NULL,
                     :original_budget, :approved_revisions, :current_budget, :committed_cost,
                     :actual_cost, :forecast_at_completion, :currency, :notes, :sort_order,
                     false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "company_id": company_id,
                    "project_id": project_id,
                    "budget_version_id": version_id,
                    "category_id": category_id,
                    "legacy_id": legacy_id,
                    "line_number": f"{index:04d}",
                    "name": budget_name,
                    "original_budget": original,
                    "approved_revisions": approved_revisions,
                    "current_budget": current,
                    "committed_cost": committed_amount,
                    "actual_cost": paid_amount,
                    "forecast_at_completion": forecast_amount,
                    "currency": row_currency or currency or "USD",
                    "notes": notes,
                    "sort_order": index,
                },
            )


def downgrade() -> None:
    for table in (
        "project_budget_revision_lines",
        "project_budget_revisions",
        "project_budget_lines",
        "project_budget_versions",
        "project_cost_codes",
        "project_budget_categories",
    ):
        if _has_table(table):
            op.drop_table(table)
