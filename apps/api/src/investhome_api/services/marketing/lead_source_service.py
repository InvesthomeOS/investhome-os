"""Marketing lead source management — hierarchy, mappings, normalization."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    LeadSourceMapping,
    LeadSourceNormalization,
    MarketingLeadContext,
    MarketingLeadSource,
    MarketingLeadSourceType,
)
from investhome_api.models.user_auth import User


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


def _get_source_or_404(db: Session, source_id: UUID) -> MarketingLeadSource:
    source = db.get(MarketingLeadSource, source_id)
    if source is None or source.archived_at is not None:
        raise HTTPException(status_code=404, detail="Lead source not found")
    return source


def list_lead_sources(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    source_type: str | None = None,
    parent_id: UUID | None = None,
) -> tuple[list[MarketingLeadSource], int]:
    query = select(MarketingLeadSource).where(MarketingLeadSource.archived_at.is_(None))
    if search:
        query = query.where(MarketingLeadSource.name.ilike(f"%{search}%"))
    if source_type:
        query = query.where(MarketingLeadSource.source_type == MarketingLeadSourceType(source_type))
    if parent_id:
        query = query.where(MarketingLeadSource.parent_id == parent_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingLeadSource.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_lead_source_summary(db: Session) -> dict:
    total = db.scalar(select(func.count()).where(MarketingLeadSource.archived_at.is_(None))) or 0
    active = db.scalar(
        select(func.count()).where(
            MarketingLeadSource.archived_at.is_(None),
            MarketingLeadSource.is_active.is_(True),
        )
    ) or 0
    return {"total": total, "active": active}


def get_source_hierarchy(db: Session) -> list[dict]:
    sources = db.scalars(
        select(MarketingLeadSource).where(MarketingLeadSource.archived_at.is_(None)).order_by(MarketingLeadSource.name)
    ).all()
    by_parent: dict[str | None, list] = {}
    for s in sources:
        key = str(s.parent_id) if s.parent_id else None
        by_parent.setdefault(key, []).append(s)

    def _build_tree(parent_key: str | None) -> list[dict]:
        nodes = []
        for s in by_parent.get(parent_key, []):
            nodes.append(
                {
                    "id": str(s.id),
                    "name": s.name,
                    "source_type": s.source_type.value,
                    "tracking_code": s.tracking_code,
                    "children": _build_tree(str(s.id)),
                }
            )
        return nodes

    return _build_tree(None)


def validate_source_hierarchy(db: Session, source_id: UUID, parent_id: UUID | None) -> None:
    if parent_id is None:
        return
    if parent_id == source_id:
        raise HTTPException(status_code=400, detail="Source cannot be its own parent")
    visited: set[str] = set()
    current = parent_id
    while current:
        if str(current) == str(source_id):
            raise HTTPException(status_code=400, detail="Circular hierarchy detected")
        if str(current) in visited:
            raise HTTPException(status_code=400, detail="Circular hierarchy detected")
        visited.add(str(current))
        parent = db.get(MarketingLeadSource, current)
        current = parent.parent_id if parent else None


def create_lead_source(db: Session, user: User, payload: dict) -> MarketingLeadSource:
    parent_id = payload.get("parent_id")
    if parent_id:
        parent = db.get(MarketingLeadSource, UUID(str(parent_id)))
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent source not found")
    name = payload["name"]
    source = MarketingLeadSource(
        name=name,
        normalized_name=_normalize_name(name),
        parent_id=UUID(str(parent_id)) if parent_id else None,
        source_type=MarketingLeadSourceType(payload["source_type"]),
        channel_id=payload.get("channel_id"),
        utm_defaults_json=payload.get("utm_defaults_json"),
        tracking_code=payload.get("tracking_code"),
        description=payload.get("description"),
        created_by_user_id=user.id,
    )
    db.add(source)
    db.flush()
    source.tracking_readiness = _assess_tracking_readiness(source)
    return source


def update_lead_source(db: Session, source_id: UUID, user: User, payload: dict) -> MarketingLeadSource:
    source = _get_source_or_404(db, source_id)
    if "parent_id" in payload:
        parent_id = payload["parent_id"]
        if parent_id:
            validate_source_hierarchy(db, source_id, UUID(str(parent_id)))
        source.parent_id = UUID(str(parent_id)) if parent_id else None
    if "name" in payload:
        source.name = payload["name"]
        source.normalized_name = _normalize_name(payload["name"])
    for key in ("channel_id", "utm_defaults_json", "tracking_code", "description", "is_active"):
        if key in payload:
            setattr(source, key, payload[key])
    if "source_type" in payload:
        source.source_type = MarketingLeadSourceType(payload["source_type"])
    source.updated_by_user_id = user.id
    source.tracking_readiness = _assess_tracking_readiness(source)
    return source


def _assess_tracking_readiness(source: MarketingLeadSource) -> str:
    if not source.tracking_code and not source.utm_defaults_json:
        return "not_configured"
    if source.tracking_code and source.utm_defaults_json:
        return "ready"
    return "incomplete"


def get_source_mappings(db: Session, source_id: UUID) -> list[LeadSourceMapping]:
    _get_source_or_404(db, source_id)
    return list(db.scalars(select(LeadSourceMapping).where(LeadSourceMapping.source_id == source_id)).all())


def create_source_mapping(db: Session, source_id: UUID, payload: dict) -> LeadSourceMapping:
    _get_source_or_404(db, source_id)
    mapping = LeadSourceMapping(
        source_id=source_id,
        provider=payload.get("provider"),
        external_key=payload["external_key"],
        mapping_json=payload.get("mapping_json"),
    )
    db.add(mapping)
    db.flush()
    return mapping


def normalize_source_value(db: Session, source_id: UUID, raw_value: str) -> dict:
    _get_source_or_404(db, source_id)
    existing = db.scalar(
        select(LeadSourceNormalization).where(
            LeadSourceNormalization.source_id == source_id,
            LeadSourceNormalization.raw_value == raw_value,
        )
    )
    if existing:
        return {"raw_value": raw_value, "normalized_value": existing.normalized_value, "from_cache": True}
    normalized = _normalize_name(raw_value)
    record = LeadSourceNormalization(
        source_id=source_id,
        raw_value=raw_value,
        normalized_value=normalized,
    )
    db.add(record)
    db.flush()
    return {"raw_value": raw_value, "normalized_value": normalized, "from_cache": False}


def get_source_leads(db: Session, source_id: UUID, *, page: int = 1, page_size: int = 25) -> tuple[list, int]:
    _get_source_or_404(db, source_id)
    query = select(MarketingLeadContext).where(MarketingLeadContext.source_id == source_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def archive_lead_source(db: Session, source_id: UUID) -> MarketingLeadSource:
    source = _get_source_or_404(db, source_id)
    source.archived_at = datetime.now(tz=UTC)
    source.is_active = False
    return source
