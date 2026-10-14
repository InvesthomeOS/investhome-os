"""Project location profiles, nearby places, and AI summaries.

Revision ID: 0086_project_location_intelligence
Revises: 0085_lead_junk_reason
Create Date: 2026-10-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0086_project_location_intelligence"
down_revision: str | None = "0085_lead_junk_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "project_location_profiles",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("formatted_address", sa.String(length=500), nullable=True),
        sa.Column("neighborhood", sa.String(length=160), nullable=True),
        sa.Column("locality", sa.String(length=160), nullable=True),
        sa.Column("county", sa.String(length=160), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("provider_place_id", sa.String(length=255), nullable=True),
        sa.Column("geocode_status", sa.String(length=20), nullable=False),
        sa.Column("address_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("raw_payload", JSON_TYPE, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_location_profiles_project"),
    )
    op.create_index("ix_project_location_profiles_status", "project_location_profiles", ["geocode_status"])

    op.create_table(
        "project_nearby_places",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_place_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("straight_line_distance_meters", sa.Integer(), nullable=False),
        sa.Column("walking_distance_meters", sa.Integer(), nullable=True),
        sa.Column("walking_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("raw_payload", JSON_TYPE, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "provider",
            "provider_place_id",
            name="uq_project_nearby_places_provider_place",
        ),
    )
    op.create_index("ix_project_nearby_places_project_id", "project_nearby_places", ["project_id"])

    op.create_table(
        "project_location_ai_summaries",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("summary_type", sa.String(length=40), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=80), nullable=True),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "summary_type", name="uq_project_location_ai_summary_type"),
    )


def downgrade() -> None:
    op.drop_table("project_location_ai_summaries")
    op.drop_index("ix_project_nearby_places_project_id", table_name="project_nearby_places")
    op.drop_table("project_nearby_places")
    op.drop_index("ix_project_location_profiles_status", table_name="project_location_profiles")
    op.drop_table("project_location_profiles")
