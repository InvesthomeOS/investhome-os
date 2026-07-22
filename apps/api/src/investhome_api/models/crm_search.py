"""CRM search persistence — recent searches, saved searches, audit."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class CrmRecentSearch(Base):
    __tablename__ = "crm_recent_searches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entity_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_result_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    opened_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CrmSavedSearch(Base):
    __tablename__ = "crm_saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entity_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sort_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    grouping: Mapped[str | None] = mapped_column(String(40), nullable=True)
    visible_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    view_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="list")
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    shared_with: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notification_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmSearchAuditLog(Base):
    __tablename__ = "crm_search_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
