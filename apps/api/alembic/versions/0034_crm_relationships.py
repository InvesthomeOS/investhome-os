"""CRM relationship engine tables.

Revision ID: 0034_crm_relationships
Revises: 0033_crm_companies
Create Date: 2026-07-16
"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0034_crm_relationships"
down_revision: str | None = "0033_crm_companies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TYPE_CONFIGS = [
    ("parent", "subsidiary", "organizational", True, "Parent", "Subsidiary", True),
    ("subsidiary", "parent", "organizational", True, "Subsidiary", "Parent", True),
    ("referred_by", "referred_to", "referral", True, "Referred By", "Referred To", False),
    ("referred_to", "referred_by", "referral", True, "Referred To", "Referred By", False),
    ("partner", "partner", "commercial", False, "Partner", "Partner", False),
    ("client", "vendor", "commercial", True, "Client", "Vendor", False),
    ("vendor", "client", "commercial", True, "Vendor", "Client", False),
    ("investor", "investee", "investment", True, "Investor", "Investee", False),
    ("investee", "investor", "investment", True, "Investee", "Investor", False),
    ("affiliate", "affiliate", "organizational", False, "Affiliate", "Affiliate", False),
    ("competitor", "competitor", "commercial", False, "Competitor", "Competitor", False),
    ("colleague", "colleague", "personal", False, "Colleague", "Colleague", False),
    ("advisor", "advisee", "operational", True, "Advisor", "Advisee", False),
    ("advisee", "advisor", "operational", True, "Advisee", "Advisor", False),
    ("employs", "employed_by", "organizational", True, "Employs", "Employed By", False),
    ("employed_by", "employs", "organizational", True, "Employed By", "Employs", False),
    ("other", "other", "other", False, "Other", "Other", False),
]


def upgrade() -> None:
    op.create_table(
        "crm_relationship_type_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=60), nullable=False),
        sa.Column("reciprocal_type", sa.String(length=60), nullable=True),
        sa.Column("category", sa.String(length=30), server_default="other", nullable=False),
        sa.Column("is_directional", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("reciprocal_label", sa.String(length=120), nullable=True),
        sa.Column("prevents_hierarchy_cycle", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relationship_type"),
    )

    op.create_table(
        "crm_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_entity_type", sa.String(length=30), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), nullable=False),
        sa.Column("target_entity_type", sa.String(length=30), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=60), nullable=False),
        sa.Column("reciprocal_type", sa.String(length=60), nullable=True),
        sa.Column("category", sa.String(length=30), server_default="other", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("strength", sa.String(length=20), server_default="moderate", nullable=False),
        sa.Column("direction", sa.String(length=20), server_default="outbound", nullable=False),
        sa.Column("relationship_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("engagement_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("influence_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("trust_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("business_value_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_confidential", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            "relationship_type",
            name="uq_crm_relationship_endpoints_type",
        ),
    )
    op.create_index("ix_crm_relationships_source", "crm_relationships", ["source_entity_type", "source_entity_id"])
    op.create_index("ix_crm_relationships_target", "crm_relationships", ["target_entity_type", "target_entity_id"])
    op.create_index("ix_crm_relationships_type", "crm_relationships", ["relationship_type"])
    op.create_index("ix_crm_relationships_status", "crm_relationships", ["status"])

    op.create_table(
        "crm_relationship_score_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("engagement_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("influence_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("trust_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("business_value_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("factors", sa.JSON(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["crm_relationships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_relationship_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("alert_type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["relationship_id"], ["crm_relationships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_decision_map_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("role_type", sa.String(length=30), nullable=False),
        sa.Column("influence_level", sa.Integer(), server_default="50", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["crm_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "contact_id", "role_type", name="uq_crm_decision_map_role"),
    )

    op.create_table(
        "crm_referrals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referrer_entity_type", sa.String(length=30), nullable=False),
        sa.Column("referrer_entity_id", sa.Uuid(), nullable=False),
        sa.Column("referred_entity_type", sa.String(length=30), nullable=False),
        sa.Column("referred_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("compensation_amount", sa.Float(), nullable=True),
        sa.Column("compensation_currency", sa.String(length=3), nullable=True),
        sa.Column("compensation_status", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["crm_relationships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_relationship_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("scores_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["crm_relationships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_relationship_saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    config_table = sa.table(
        "crm_relationship_type_configs",
        sa.column("id", sa.Uuid()),
        sa.column("relationship_type", sa.String()),
        sa.column("reciprocal_type", sa.String()),
        sa.column("category", sa.String()),
        sa.column("is_directional", sa.Boolean()),
        sa.column("label", sa.String()),
        sa.column("reciprocal_label", sa.String()),
        sa.column("prevents_hierarchy_cycle", sa.Boolean()),
    )
    op.bulk_insert(
        config_table,
        [
            {
                "id": uuid.uuid4(),
                "relationship_type": row[0],
                "reciprocal_type": row[1],
                "category": row[2],
                "is_directional": row[3],
                "label": row[4],
                "reciprocal_label": row[5],
                "prevents_hierarchy_cycle": row[6],
            }
            for row in TYPE_CONFIGS
        ],
    )


def downgrade() -> None:
    op.drop_table("crm_relationship_saved_views")
    op.drop_table("crm_relationship_reviews")
    op.drop_table("crm_referrals")
    op.drop_table("crm_decision_map_roles")
    op.drop_table("crm_relationship_alerts")
    op.drop_table("crm_relationship_score_snapshots")
    op.drop_index("ix_crm_relationships_status", table_name="crm_relationships")
    op.drop_index("ix_crm_relationships_type", table_name="crm_relationships")
    op.drop_index("ix_crm_relationships_target", table_name="crm_relationships")
    op.drop_index("ix_crm_relationships_source", table_name="crm_relationships")
    op.drop_table("crm_relationships")
    op.drop_table("crm_relationship_type_configs")
