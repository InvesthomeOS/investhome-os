"""Creative Director campaign context — durable shared source for later builders."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class CreativeDirectorCampaign(Base):
    """Persisted Campaign Context for Creative Director / AI Orchestrator."""

    __tablename__ = "creative_director_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    linked_project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="project")
    original_brief: Mapped[str] = mapped_column(Text, nullable=False)
    # Full structured context: strategy, claims, assets, capabilities, history.
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_creative_director_campaigns_linked_project_id", "linked_project_id"),
        Index("ix_creative_director_campaigns_created_by_user_id", "created_by_user_id"),
        Index("ix_creative_director_campaigns_status", "status"),
        Index("ix_creative_director_campaigns_created_at", "created_at"),
    )
