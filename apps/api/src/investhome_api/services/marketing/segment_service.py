"""Marketing segment management — rules, preview, calculation, dependencies."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    MarketingSegment,
    MarketingSegmentType,
    SegmentCalculationRun,
    SegmentCalculationStatus,
    SegmentRule,
    SegmentRuleGroup,
    SegmentSavedView,
    SegmentVersion,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.segment_field_registry import (
    MAX_RULE_DEPTH,
    MAX_RULES_PER_GROUP,
    get_field_definition,
    validate_rule_operator,
)


def _get_segment_or_404(db: Session, segment_id: UUID) -> MarketingSegment:
    segment = db.get(MarketingSegment, segment_id)
    if segment is None or segment.archived_at is not None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


def list_segments(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    segment_type: str | None = None,
    calculation_status: str | None = None,
) -> tuple[list[MarketingSegment], int]:
    query = select(MarketingSegment).where(MarketingSegment.archived_at.is_(None))
    if search:
        query = query.where(MarketingSegment.name.ilike(f"%{search}%"))
    if segment_type:
        query = query.where(MarketingSegment.segment_type == MarketingSegmentType(segment_type))
    if calculation_status:
        query = query.where(MarketingSegment.calculation_status == SegmentCalculationStatus(calculation_status))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingSegment.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_segment_summary(db: Session) -> dict:
    total = db.scalar(select(func.count()).where(MarketingSegment.archived_at.is_(None))) or 0
    calculated = db.scalar(
        select(func.count()).where(
            MarketingSegment.archived_at.is_(None),
            MarketingSegment.calculation_status == SegmentCalculationStatus.COMPLETED,
        )
    ) or 0
    pending = db.scalar(
        select(func.count()).where(
            MarketingSegment.archived_at.is_(None),
            MarketingSegment.calculation_status.in_(
                [SegmentCalculationStatus.NOT_CALCULATED, SegmentCalculationStatus.PENDING]
            ),
        )
    ) or 0
    return {"total": total, "calculated": calculated, "not_calculated": pending}


def create_segment(db: Session, user: User, payload: dict) -> MarketingSegment:
    segment = MarketingSegment(
        name=payload["name"],
        description=payload.get("description"),
        segment_type=MarketingSegmentType(payload["segment_type"]),
        rules_json=payload.get("rules_json"),
        refresh_frequency=payload.get("refresh_frequency"),
        visibility=payload.get("visibility", "team"),
        depends_on_segment_ids=payload.get("depends_on_segment_ids"),
        created_by_user_id=user.id,
        calculation_status=SegmentCalculationStatus.NOT_CALCULATED,
    )
    db.add(segment)
    db.flush()
    if payload.get("rule_groups"):
        _save_rule_groups(db, segment.id, payload["rule_groups"], version=1)
    return segment


def update_segment(db: Session, segment_id: UUID, user: User, payload: dict) -> MarketingSegment:
    segment = _get_segment_or_404(db, segment_id)
    for key in ("name", "description", "rules_json", "refresh_frequency", "visibility", "depends_on_segment_ids"):
        if key in payload:
            setattr(segment, key, payload[key])
    if "segment_type" in payload:
        segment.segment_type = MarketingSegmentType(payload["segment_type"])
    segment.updated_by_user_id = user.id
    if payload.get("rule_groups") is not None:
        validate_segment_dependencies(db, segment_id, payload.get("depends_on_segment_ids") or [])
        segment.current_version += 1
        _save_rule_groups(db, segment_id, payload["rule_groups"], version=segment.current_version)
        segment.calculation_status = SegmentCalculationStatus.NOT_CALCULATED
        db.add(
            SegmentVersion(
                segment_id=segment_id,
                version=segment.current_version,
                rules_snapshot_json={"rule_groups": payload["rule_groups"]},
                created_by_user_id=user.id,
            )
        )
    return segment


def _save_rule_groups(db: Session, segment_id: UUID, rule_groups: list[dict], version: int) -> None:
    """Persist normalized rule groups — replaces existing for version."""
    existing_groups = db.scalars(
        select(SegmentRuleGroup).where(SegmentRuleGroup.segment_id == segment_id, SegmentRuleGroup.version == version)
    ).all()
    for g in existing_groups:
        db.delete(g)
    db.flush()

    def _create_group(group_data: dict, parent_id: UUID | None, depth: int) -> None:
        if depth > MAX_RULE_DEPTH:
            raise HTTPException(status_code=400, detail=f"Rule depth exceeds maximum of {MAX_RULE_DEPTH}")
        rules = group_data.get("rules", [])
        if len(rules) > MAX_RULES_PER_GROUP:
            raise HTTPException(status_code=400, detail=f"Rules per group exceeds maximum of {MAX_RULES_PER_GROUP}")
        group = SegmentRuleGroup(
            segment_id=segment_id,
            parent_group_id=parent_id,
            operator=group_data.get("operator", "and"),
            sort_order=group_data.get("sort_order", 0),
            version=version,
        )
        db.add(group)
        db.flush()
        for idx, rule_data in enumerate(rules):
            field_key = rule_data.get("field_key", "")
            operator = rule_data.get("operator", "")
            if not get_field_definition(field_key):
                raise HTTPException(status_code=400, detail=f"Unknown field: {field_key}")
            if not validate_rule_operator(field_key, operator):
                raise HTTPException(status_code=400, detail=f"Invalid operator '{operator}' for field '{field_key}'")
            db.add(
                SegmentRule(
                    group_id=group.id,
                    field_key=field_key,
                    operator=operator,
                    value_json=rule_data.get("value"),
                    negate=rule_data.get("negate", False),
                    sort_order=idx,
                )
            )
        for nested in group_data.get("groups", []):
            _create_group(nested, group.id, depth + 1)

    for g in rule_groups:
        _create_group(g, None, 1)


def get_segment_rules(db: Session, segment_id: UUID) -> list[dict]:
    _get_segment_or_404(db, segment_id)
    segment = db.get(MarketingSegment, segment_id)
    version = segment.current_version if segment else 1
    groups = db.scalars(
        select(SegmentRuleGroup).where(
            SegmentRuleGroup.segment_id == segment_id,
            SegmentRuleGroup.version == version,
            SegmentRuleGroup.parent_group_id.is_(None),
        )
    ).all()
    return [_serialize_rule_group(db, g) for g in groups]


def _serialize_rule_group(db: Session, group: SegmentRuleGroup) -> dict:
    rules = db.scalars(select(SegmentRule).where(SegmentRule.group_id == group.id).order_by(SegmentRule.sort_order)).all()
    nested = db.scalars(
        select(SegmentRuleGroup).where(SegmentRuleGroup.parent_group_id == group.id).order_by(SegmentRuleGroup.sort_order)
    ).all()
    return {
        "id": str(group.id),
        "operator": group.operator,
        "rules": [
            {
                "id": str(r.id),
                "field_key": r.field_key,
                "operator": r.operator,
                "value": r.value_json,
                "negate": r.negate,
            }
            for r in rules
        ],
        "groups": [_serialize_rule_group(db, ng) for ng in nested],
    }


def validate_segment_dependencies(db: Session, segment_id: UUID, depends_on: list) -> None:
    """Block circular segment dependencies."""
    visited: set[str] = set()
    path: set[str] = set()

    def _check(current_id: str) -> None:
        if current_id in path:
            raise HTTPException(status_code=400, detail="Circular segment dependency detected")
        if current_id in visited:
            return
        visited.add(current_id)
        path.add(current_id)
        seg = db.get(MarketingSegment, UUID(current_id))
        if seg and seg.depends_on_segment_ids:
            for dep_id in seg.depends_on_segment_ids:
                _check(str(dep_id))
        path.remove(current_id)

    _check(str(segment_id))
    for dep_id in depends_on:
        if str(dep_id) == str(segment_id):
            raise HTTPException(status_code=400, detail="Segment cannot depend on itself")
        _check(str(dep_id))


def preview_segment(db: Session, segment_id: UUID) -> dict:
    segment = _get_segment_or_404(db, segment_id)
    if segment.calculation_status == SegmentCalculationStatus.NOT_CALCULATED:
        return {
            "segment_id": str(segment_id),
            "state": "not_calculated",
            "estimated_count": None,
            "sample_members": [],
            "rule_explanation": _build_rule_explanation(db, segment_id),
            "warnings": ["Segment has not been calculated — count unavailable"],
        }
    latest_run = db.scalar(
        select(SegmentCalculationRun)
        .where(SegmentCalculationRun.segment_id == segment_id)
        .order_by(SegmentCalculationRun.created_at.desc())
    )
    return {
        "segment_id": str(segment_id),
        "state": "ready" if latest_run and latest_run.status == SegmentCalculationStatus.COMPLETED else "not_calculated",
        "estimated_count": latest_run.member_count if latest_run else segment.calculated_size,
        "sample_members": [],
        "rule_explanation": _build_rule_explanation(db, segment_id),
        "warnings": latest_run.warnings_json if latest_run else [],
    }


def _build_rule_explanation(db: Session, segment_id: UUID) -> str:
    rules = get_segment_rules(db, segment_id)
    if not rules:
        return "No rules defined"
    parts = []
    for group in rules:
        parts.append(f"({group['operator'].upper()} group with {len(group['rules'])} rules)")
    return "; ".join(parts)


def calculate_segment(db: Session, segment_id: UUID, user: User) -> SegmentCalculationRun:
    """Server-side calculation only — never evaluates arbitrary code."""
    segment = _get_segment_or_404(db, segment_id)
    validate_segment_dependencies(db, segment_id, segment.depends_on_segment_ids or [])
    run = SegmentCalculationRun(
        segment_id=segment_id,
        status=SegmentCalculationStatus.RUNNING,
        version=segment.current_version,
        started_at=datetime.now(tz=UTC),
        triggered_by_user_id=user.id,
        warnings_json=[],
    )
    db.add(run)
    segment.calculation_status = SegmentCalculationStatus.RUNNING
    db.flush()

    # Honest calculation: count explicit rules only — no fabricated scores
    rules = get_segment_rules(db, segment_id)
    warnings: list[str] = []
    if not rules:
        warnings.append("No rules defined — member count is zero")
        member_count = 0
    else:
        member_count = None
        warnings.append("Full dynamic calculation requires CRM data provider — count unavailable until provider connected")

    run.status = SegmentCalculationStatus.COMPLETED if member_count is not None else SegmentCalculationStatus.FAILED
    run.member_count = member_count
    run.warnings_json = warnings
    run.completed_at = datetime.now(tz=UTC)
    segment.calculation_status = run.status
    if member_count is not None:
        segment.calculated_size = member_count
    segment.last_refreshed_at = datetime.now(tz=UTC)
    return run


def refresh_segment(db: Session, segment_id: UUID, user: User) -> MarketingSegment:
    segment = _get_segment_or_404(db, segment_id)
    calculate_segment(db, segment_id, user)
    return segment


def list_segment_versions(db: Session, segment_id: UUID) -> list[SegmentVersion]:
    _get_segment_or_404(db, segment_id)
    return list(
        db.scalars(
            select(SegmentVersion)
            .where(SegmentVersion.segment_id == segment_id)
            .order_by(SegmentVersion.version.desc())
        ).all()
    )


def list_saved_views(db: Session, user_id: UUID) -> list[SegmentSavedView]:
    return list(
        db.scalars(
            select(SegmentSavedView).where(
                or_(SegmentSavedView.user_id == user_id, SegmentSavedView.is_shared.is_(True))
            )
        ).all()
    )
