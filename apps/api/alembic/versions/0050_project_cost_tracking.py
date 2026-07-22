"""Project cost tracking — vendors, commitments, bills, payments, retainage.

Revision ID: 0050_project_cost_tracking
Revises: 0049_project_budget_foundation
Create Date: 2026-07-19

Additive only. No destructive changes. No invented vendor backfill.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0050_project_cost_tracking"
down_revision: str | None = "0049_project_budget_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("vendors"):
        op.create_table(
            "vendors",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("legal_name", sa.String(length=255), nullable=True),
            sa.Column("vendor_code", sa.String(length=50), nullable=False),
            sa.Column("tax_id_last4", sa.String(length=4), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("vendor_type", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("payment_terms", sa.String(length=100), nullable=True),
            sa.Column("default_currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("insurance_expiration_date", sa.Date(), nullable=True),
            sa.Column("license_number", sa.String(length=100), nullable=True),
            sa.Column("license_expiration_date", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("company_id", "vendor_code", name="uq_vendors_company_code"),
        )
        op.create_index("ix_vendors_company_id", "vendors", ["company_id"])
        op.create_index("ix_vendors_status", "vendors", ["status"])
        op.create_index("ix_vendors_name", "vendors", ["name"])

    if not _has_table("project_vendors"):
        op.create_table(
            "project_vendors",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("role", sa.String(length=100), nullable=False, server_default="vendor"),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("primary_contact_id", sa.Uuid(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "project_id", "vendor_id", "role", name="uq_project_vendors_project_vendor_role"
            ),
        )
        op.create_index("ix_project_vendors_project_id", "project_vendors", ["project_id"])
        op.create_index("ix_project_vendors_vendor_id", "project_vendors", ["vendor_id"])
        op.create_index("ix_project_vendors_company_id", "project_vendors", ["company_id"])
        op.create_index("ix_project_vendors_status", "project_vendors", ["status"])

    if not _has_table("project_commitments"):
        op.create_table(
            "project_commitments",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "budget_version_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_versions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("commitment_number", sa.String(length=50), nullable=False),
            sa.Column("commitment_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("original_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("approved_change_orders", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("current_committed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("invoiced_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("retained_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("remaining_commitment", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("executed_date", sa.Date(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("payment_terms", sa.String(length=100), nullable=True),
            sa.Column("retainage_percentage", sa.Numeric(8, 4), nullable=True),
            sa.Column("billing_contact_id", sa.Uuid(), nullable=True),
            sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("budget_override_reason", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint(
                "project_id", "commitment_number", name="uq_project_commitments_project_number"
            ),
        )
        op.create_index("ix_project_commitments_project_id", "project_commitments", ["project_id"])
        op.create_index("ix_project_commitments_vendor_id", "project_commitments", ["vendor_id"])
        op.create_index("ix_project_commitments_company_id", "project_commitments", ["company_id"])
        op.create_index("ix_project_commitments_status", "project_commitments", ["status"])
        op.create_index(
            "ix_project_commitments_budget_version_id", "project_commitments", ["budget_version_id"]
        )
        op.create_index(
            "ix_project_commitments_commitment_type", "project_commitments", ["commitment_type"]
        )

    if not _has_table("project_commitment_lines"):
        op.create_table(
            "project_commitment_lines",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "commitment_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "budget_line_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_lines.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "category_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_categories.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "cost_code_id",
                sa.Uuid(),
                sa.ForeignKey("project_cost_codes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("line_number", sa.String(length=50), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit", sa.String(length=50), nullable=True),
            sa.Column("unit_price", sa.Numeric(18, 2), nullable=True),
            sa.Column("original_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("approved_change_orders", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("current_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("invoiced_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("retained_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("remaining_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint(
                "commitment_id",
                "line_number",
                name="uq_project_commitment_lines_commitment_line_number",
            ),
        )
        op.create_index("ix_project_commitment_lines_project_id", "project_commitment_lines", ["project_id"])
        op.create_index(
            "ix_project_commitment_lines_commitment_id", "project_commitment_lines", ["commitment_id"]
        )
        op.create_index(
            "ix_project_commitment_lines_budget_line_id", "project_commitment_lines", ["budget_line_id"]
        )
        op.create_index(
            "ix_project_commitment_lines_category_id", "project_commitment_lines", ["category_id"]
        )
        op.create_index(
            "ix_project_commitment_lines_cost_code_id", "project_commitment_lines", ["cost_code_id"]
        )

    if not _has_table("project_commitment_change_orders"):
        op.create_table(
            "project_commitment_change_orders",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "commitment_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("change_order_number", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("requested_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("approved_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "commitment_id",
                "change_order_number",
                name="uq_project_commitment_cos_commitment_number",
            ),
        )
        op.create_index(
            "ix_project_commitment_cos_project_id", "project_commitment_change_orders", ["project_id"]
        )
        op.create_index(
            "ix_project_commitment_cos_commitment_id",
            "project_commitment_change_orders",
            ["commitment_id"],
        )
        op.create_index(
            "ix_project_commitment_cos_status", "project_commitment_change_orders", ["status"]
        )

    if not _has_table("project_commitment_change_order_lines"):
        op.create_table(
            "project_commitment_change_order_lines",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column(
                "change_order_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitment_change_orders.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "commitment_line_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitment_lines.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "budget_line_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_lines.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index(
            "ix_project_commitment_co_lines_change_order_id",
            "project_commitment_change_order_lines",
            ["change_order_id"],
        )
        op.create_index(
            "ix_project_commitment_co_lines_commitment_line_id",
            "project_commitment_change_order_lines",
            ["commitment_line_id"],
        )
        op.create_index(
            "ix_project_commitment_co_lines_budget_line_id",
            "project_commitment_change_order_lines",
            ["budget_line_id"],
        )

    if not _has_table("project_vendor_bills"):
        op.create_table(
            "project_vendor_bills",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "commitment_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitments.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("bill_number", sa.String(length=50), nullable=False),
            sa.Column("vendor_invoice_number", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("invoice_date", sa.Date(), nullable=False),
            sa.Column("received_date", sa.Date(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("billing_period_start", sa.Date(), nullable=True),
            sa.Column("billing_period_end", sa.Date(), nullable=True),
            sa.Column("subtotal", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("retainage_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("approved_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("balance_due", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("payment_terms", sa.String(length=100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("posted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("voided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("project_id", "bill_number", name="uq_project_vendor_bills_project_number"),
            sa.UniqueConstraint(
                "vendor_id", "vendor_invoice_number", name="uq_project_vendor_bills_vendor_invoice"
            ),
        )
        op.create_index("ix_project_vendor_bills_project_id", "project_vendor_bills", ["project_id"])
        op.create_index("ix_project_vendor_bills_vendor_id", "project_vendor_bills", ["vendor_id"])
        op.create_index(
            "ix_project_vendor_bills_commitment_id", "project_vendor_bills", ["commitment_id"]
        )
        op.create_index("ix_project_vendor_bills_company_id", "project_vendor_bills", ["company_id"])
        op.create_index("ix_project_vendor_bills_status", "project_vendor_bills", ["status"])
        op.create_index("ix_project_vendor_bills_due_date", "project_vendor_bills", ["due_date"])
        op.create_index("ix_project_vendor_bills_invoice_date", "project_vendor_bills", ["invoice_date"])

    if not _has_table("project_vendor_bill_lines"):
        op.create_table(
            "project_vendor_bill_lines",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "vendor_bill_id",
                sa.Uuid(),
                sa.ForeignKey("project_vendor_bills.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "commitment_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitments.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "commitment_line_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitment_lines.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "budget_line_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_lines.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "category_id",
                sa.Uuid(),
                sa.ForeignKey("project_budget_categories.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "cost_code_id",
                sa.Uuid(),
                sa.ForeignKey("project_cost_codes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("line_number", sa.String(length=50), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
            sa.Column("unit", sa.String(length=50), nullable=True),
            sa.Column("unit_price", sa.Numeric(18, 2), nullable=True),
            sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("retainage_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("previously_billed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("current_billed_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("stored_materials_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint(
                "vendor_bill_id",
                "line_number",
                name="uq_project_vendor_bill_lines_bill_line_number",
            ),
        )
        op.create_index(
            "ix_project_vendor_bill_lines_project_id", "project_vendor_bill_lines", ["project_id"]
        )
        op.create_index(
            "ix_project_vendor_bill_lines_vendor_bill_id",
            "project_vendor_bill_lines",
            ["vendor_bill_id"],
        )
        op.create_index(
            "ix_project_vendor_bill_lines_commitment_id",
            "project_vendor_bill_lines",
            ["commitment_id"],
        )
        op.create_index(
            "ix_project_vendor_bill_lines_commitment_line_id",
            "project_vendor_bill_lines",
            ["commitment_line_id"],
        )
        op.create_index(
            "ix_project_vendor_bill_lines_budget_line_id",
            "project_vendor_bill_lines",
            ["budget_line_id"],
        )
        op.create_index(
            "ix_project_vendor_bill_lines_category_id", "project_vendor_bill_lines", ["category_id"]
        )
        op.create_index(
            "ix_project_vendor_bill_lines_cost_code_id", "project_vendor_bill_lines", ["cost_code_id"]
        )

    if not _has_table("project_payments"):
        op.create_table(
            "project_payments",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("payment_number", sa.String(length=50), nullable=False),
            sa.Column("payment_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("payment_method", sa.String(length=30), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("reference_number", sa.String(length=100), nullable=True),
            sa.Column("memo", sa.Text(), nullable=True),
            sa.Column("source_account_id", sa.Uuid(), nullable=True),
            sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("posted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("voided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("project_id", "payment_number", name="uq_project_payments_project_number"),
        )
        op.create_index("ix_project_payments_project_id", "project_payments", ["project_id"])
        op.create_index("ix_project_payments_vendor_id", "project_payments", ["vendor_id"])
        op.create_index("ix_project_payments_company_id", "project_payments", ["company_id"])
        op.create_index("ix_project_payments_status", "project_payments", ["status"])
        op.create_index("ix_project_payments_payment_date", "project_payments", ["payment_date"])

    if not _has_table("project_payment_allocations"):
        op.create_table(
            "project_payment_allocations",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column(
                "payment_id",
                sa.Uuid(),
                sa.ForeignKey("project_payments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "vendor_bill_id",
                sa.Uuid(),
                sa.ForeignKey("project_vendor_bills.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("allocated_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("retainage_release_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index(
            "ix_project_payment_allocations_payment_id", "project_payment_allocations", ["payment_id"]
        )
        op.create_index(
            "ix_project_payment_allocations_vendor_bill_id",
            "project_payment_allocations",
            ["vendor_bill_id"],
        )
        op.create_index(
            "ix_project_payment_allocations_project_id", "project_payment_allocations", ["project_id"]
        )
        op.create_index(
            "ix_project_payment_allocations_company_id", "project_payment_allocations", ["company_id"]
        )

    if not _has_table("project_retainage_releases"):
        op.create_table(
            "project_retainage_releases",
            sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
            sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("vendor_id", sa.Uuid(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "commitment_id",
                sa.Uuid(),
                sa.ForeignKey("project_commitments.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "vendor_bill_id",
                sa.Uuid(),
                sa.ForeignKey("project_vendor_bills.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("release_number", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("release_date", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("posted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("voided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "project_id", "release_number", name="uq_project_retainage_releases_project_number"
            ),
        )
        op.create_index(
            "ix_project_retainage_releases_project_id", "project_retainage_releases", ["project_id"]
        )
        op.create_index(
            "ix_project_retainage_releases_vendor_id", "project_retainage_releases", ["vendor_id"]
        )
        op.create_index(
            "ix_project_retainage_releases_commitment_id",
            "project_retainage_releases",
            ["commitment_id"],
        )
        op.create_index(
            "ix_project_retainage_releases_vendor_bill_id",
            "project_retainage_releases",
            ["vendor_bill_id"],
        )
        op.create_index(
            "ix_project_retainage_releases_status", "project_retainage_releases", ["status"]
        )


def downgrade() -> None:
    for table in (
        "project_retainage_releases",
        "project_payment_allocations",
        "project_payments",
        "project_vendor_bill_lines",
        "project_vendor_bills",
        "project_commitment_change_order_lines",
        "project_commitment_change_orders",
        "project_commitment_lines",
        "project_commitments",
        "project_vendors",
        "vendors",
    ):
        if _has_table(table):
            op.drop_table(table)
