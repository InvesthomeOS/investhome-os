"""Sales contract readiness — cases, requirements, templates.

Revision ID: 0027_sales_readiness
Revises: 0026_work_items
Create Date: 2026-07-16

"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0027_sales_readiness"
down_revision: str | None = "0026_work_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ITEMS = [
    ("reservation", "reservation_approved", "Reservation approved", True, 10),
    ("deposit", "deposit_due", "Deposit due date confirmed", True, 20),
    ("deposit", "deposit_received", "Deposit received", True, 30),
    ("party", "party_identity", "Party identity confirmed", True, 40),
    ("party", "party_organization_documents", "Organization documents", False, 50),
    ("documents", "proof_of_funds", "Proof of funds", True, 60),
    ("documents", "kyc_document", "KYC document", False, 70),
    ("contract", "proposal_accepted", "Proposal accepted", True, 80),
    ("documents", "purchase_agreement", "Purchase agreement", True, 90),
    ("documents", "payment_schedule", "Payment schedule", True, 100),
    ("contract", "legal_review", "Legal review complete", True, 110),
    ("contract", "signature_required", "Signature requested", True, 120),
    ("contract", "signature_completed", "Signature completed", True, 130),
    ("handoff", "closing_date_confirmed", "Target closing date confirmed", True, 140),
]


def upgrade() -> None:
    op.create_table(
        "sales_readiness_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("asset_type", sa.String(length=50), nullable=True),
        sa.Column("buyer_type", sa.String(length=50), nullable=True),
        sa.Column("party_type", sa.String(length=50), nullable=True),
        sa.Column("sale_structure", sa.String(length=50), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "sales_readiness_template_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("template_group", sa.String(length=30), nullable=False),
        sa.Column("requirement_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["sales_readiness_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sales_readiness_template_items_template_id",
        "sales_readiness_template_items",
        ["template_id"],
    )

    op.create_table(
        "sales_readiness_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_code", sa.String(length=40), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=True),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default=sa.text("'not_started'"), nullable=False),
        sa.Column("readiness_percentage", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("target_contract_date", sa.Date(), nullable=True),
        sa.Column("target_closing_handoff_date", sa.Date(), nullable=True),
        sa.Column("assigned_sales_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_manager_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_legal_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_finance_user_id", sa.Uuid(), nullable=True),
        sa.Column("blocker_summary", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("handoff_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handoff_requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("handoff_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handoff_approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("handoff_return_reason", sa.Text(), nullable=True),
        sa.Column("signature_status", sa.String(length=30), nullable=True),
        sa.Column("signed_document_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_finance_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_legal_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_manager_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_sales_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reservation_id"], ["inventory_reservations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_code"),
    )
    op.create_index("ix_sales_readiness_cases_opportunity_id", "sales_readiness_cases", ["opportunity_id"])
    op.create_index("ix_sales_readiness_cases_status", "sales_readiness_cases", ["status"])
    op.create_index("ix_sales_readiness_cases_inventory_asset_id", "sales_readiness_cases", ["inventory_asset_id"])
    op.create_index("ix_sales_readiness_cases_assigned_sales_user_id", "sales_readiness_cases", ["assigned_sales_user_id"])

    op.create_table(
        "sales_readiness_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("readiness_case_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_type", sa.String(length=50), nullable=False),
        sa.Column("template_group", sa.String(length=30), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'missing'"), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source_entity_type", sa.String(length=40), nullable=True),
        sa.Column("source_entity_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("waiver_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("waiver_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_sync_event", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["readiness_case_id"], ["sales_readiness_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_readiness_requirements_case_id", "sales_readiness_requirements", ["readiness_case_id"])
    op.create_index("ix_sales_readiness_requirements_type", "sales_readiness_requirements", ["requirement_type"])

    op.create_table(
        "sales_readiness_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("readiness_case_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=True),
        sa.Column("new_status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["readiness_case_id"], ["sales_readiness_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sales_readiness_status_history_case_id",
        "sales_readiness_status_history",
        ["readiness_case_id"],
    )

    template_id = uuid.uuid4()
    op.execute(
        sa.text(
            """
            INSERT INTO sales_readiness_templates (id, code, name, description, is_default, is_active)
            VALUES (:id, 'default', 'Default Contract Readiness',
                    'Standard reservation → deposit → contract → handoff checklist', true, true)
            """
        ).bindparams(id=template_id)
    )
    for group, req_type, title, mandatory, sort_order in DEFAULT_ITEMS:
        op.execute(
            sa.text(
                """
                INSERT INTO sales_readiness_template_items
                    (id, template_id, template_group, requirement_type, title, is_mandatory, sort_order)
                VALUES (:id, :template_id, :group, :req_type, :title, :mandatory, :sort_order)
                """
            ).bindparams(
                id=uuid.uuid4(),
                template_id=template_id,
                group=group,
                req_type=req_type,
                title=title,
                mandatory=mandatory,
                sort_order=sort_order,
            )
        )


def downgrade() -> None:
    op.drop_index("ix_sales_readiness_status_history_case_id", table_name="sales_readiness_status_history")
    op.drop_table("sales_readiness_status_history")
    op.drop_index("ix_sales_readiness_requirements_type", table_name="sales_readiness_requirements")
    op.drop_index("ix_sales_readiness_requirements_case_id", table_name="sales_readiness_requirements")
    op.drop_table("sales_readiness_requirements")
    op.drop_index("ix_sales_readiness_cases_assigned_sales_user_id", table_name="sales_readiness_cases")
    op.drop_index("ix_sales_readiness_cases_inventory_asset_id", table_name="sales_readiness_cases")
    op.drop_index("ix_sales_readiness_cases_status", table_name="sales_readiness_cases")
    op.drop_index("ix_sales_readiness_cases_opportunity_id", table_name="sales_readiness_cases")
    op.drop_table("sales_readiness_cases")
    op.drop_index("ix_sales_readiness_template_items_template_id", table_name="sales_readiness_template_items")
    op.drop_table("sales_readiness_template_items")
    op.drop_table("sales_readiness_templates")
