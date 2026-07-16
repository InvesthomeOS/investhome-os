"""Inventory assignment workflow — parking/storage to parent unit links."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.inventory import (
    CHILD_ASSIGNMENT_ASSET_TYPES,
    PARENT_ASSIGNMENT_ASSET_TYPES,
    AssignmentApprovalDecision,
    AssignmentRecordStatus,
    AssignmentRequestStatus,
    AssignmentRequestType,
    AssignmentType,
    InventoryAsset,
    InventoryAssetAssignment,
    InventoryAssetAssignmentApproval,
    InventoryAssetAssignmentEvent,
    InventoryAssetAssignmentRequest,
    InventoryAssetType,
    PENDING_ASSIGNMENT_STATUSES,
)
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.assignment_config import (
    SELF_APPROVE_PERMISSION,
    assignment_type_for_child,
)
from investhome_api.services.permission_service import user_has_permission

TWOPLACES = Decimal("0.01")


class AssignmentError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now(clock: datetime | None = None) -> datetime:
    return clock or datetime.now(UTC)


def _today(clock: datetime | None = None) -> date:
    return _now(clock).date()


def _quantize_price(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(TWOPLACES)


def _lock_asset(db: Session, asset_id: UUID) -> InventoryAsset:
    asset = db.scalar(
        select(InventoryAsset).where(InventoryAsset.id == asset_id).with_for_update()
    )
    if asset is None or asset.archived_at is not None:
        raise AssignmentError("inventory.assignment.errors.asset_not_found", status_code=404)
    return asset


def _append_event(
    db: Session,
    *,
    child_asset_id: UUID,
    event_type: str,
    actor: User | None,
    request_id: UUID | None = None,
    assignment_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> InventoryAssetAssignmentEvent:
    event = InventoryAssetAssignmentEvent(
        child_asset_id=child_asset_id,
        assignment_request_id=request_id,
        inventory_asset_assignment_id=assignment_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.flush()
    return event


def get_active_assignment(db: Session, child_asset_id: UUID) -> InventoryAssetAssignment | None:
    return db.scalar(
        select(InventoryAssetAssignment).where(
            InventoryAssetAssignment.child_asset_id == child_asset_id,
            InventoryAssetAssignment.status == AssignmentRecordStatus.ACTIVE,
            InventoryAssetAssignment.archived_at.is_(None),
        )
    )


def get_assignment_history(db: Session, child_asset_id: UUID) -> list[InventoryAssetAssignment]:
    return list(
        db.scalars(
            select(InventoryAssetAssignment)
            .where(
                InventoryAssetAssignment.child_asset_id == child_asset_id,
                InventoryAssetAssignment.archived_at.is_(None),
            )
            .order_by(InventoryAssetAssignment.effective_from.desc(), InventoryAssetAssignment.created_at.desc())
        ).all()
    )


def get_parent_accessories(db: Session, parent_asset_id: UUID) -> list[InventoryAssetAssignment]:
    return list(
        db.scalars(
            select(InventoryAssetAssignment).where(
                InventoryAssetAssignment.parent_asset_id == parent_asset_id,
                InventoryAssetAssignment.status == AssignmentRecordStatus.ACTIVE,
                InventoryAssetAssignment.archived_at.is_(None),
            )
        ).all()
    )


def build_assignment_snapshot(db: Session, child_asset_id: UUID) -> dict[str, str | None]:
    active = get_active_assignment(db, child_asset_id)
    if active is None:
        return {
            "assignment_id": None,
            "parent_asset_id": None,
            "assignment_type": None,
            "assignment_price": None,
            "currency": None,
        }
    return {
        "assignment_id": str(active.id),
        "parent_asset_id": str(active.parent_asset_id),
        "assignment_type": active.assignment_type.value,
        "assignment_price": str(active.assignment_price) if active.assignment_price is not None else None,
        "currency": active.currency,
    }


def snapshots_match(stored_json: str, current: dict[str, str | None]) -> bool:
    try:
        stored = json.loads(stored_json)
    except json.JSONDecodeError:
        return False
    if not isinstance(stored, dict):
        return False
    keys = ("assignment_id", "parent_asset_id", "assignment_type", "assignment_price", "currency")
    return all(stored.get(k) == current.get(k) for k in keys)


def _validate_child_asset(asset: InventoryAsset) -> None:
    if asset.asset_type not in CHILD_ASSIGNMENT_ASSET_TYPES:
        raise AssignmentError("inventory.assignment.errors.invalid_child_type")


def _validate_parent_asset(asset: InventoryAsset) -> None:
    if asset.asset_type not in PARENT_ASSIGNMENT_ASSET_TYPES:
        raise AssignmentError("inventory.assignment.errors.invalid_parent_type")


def _validate_assignment_pair_db(db: Session, child: InventoryAsset, parent: InventoryAsset) -> None:
    if child.id == parent.id:
        raise AssignmentError("inventory.assignment.errors.self_assignment")
    _validate_child_asset(child)
    _validate_parent_asset(parent)
    if child.project_id != parent.project_id:
        raise AssignmentError("inventory.assignment.errors.project_mismatch")
    parent_as_child = get_active_assignment(db, parent.id)
    if parent_as_child is not None:
        raise AssignmentError("inventory.assignment.errors.circular_assignment")
    child_as_parent = db.scalar(
        select(func.count())
        .select_from(InventoryAssetAssignment)
        .where(
            InventoryAssetAssignment.parent_asset_id == child.id,
            InventoryAssetAssignment.status == AssignmentRecordStatus.ACTIVE,
        )
    )
    if child_as_parent:
        raise AssignmentError("inventory.assignment.errors.circular_assignment")


def _check_stale_request(db: Session, request: InventoryAssetAssignmentRequest) -> None:
    current = build_assignment_snapshot(db, request.child_asset_id)
    if not snapshots_match(request.source_assignment_snapshot, current):
        request.status = AssignmentRequestStatus.STALE
        request.updated_at = _now()
        _append_event(
            db,
            child_asset_id=request.child_asset_id,
            event_type="inventory.assignment.stale_conflict",
            actor=None,
            request_id=request.id,
        )
        raise AssignmentError("inventory.assignment.errors.stale_request", status_code=409)


def _ensure_can_approve(user: User, requester_id: UUID) -> None:
    if not get_settings().auth_enabled:
        return
    if not user_has_permission(user, "inventory", "approve_assignment"):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)
    if requester_id == user.id and not user_has_permission(user, "inventory", SELF_APPROVE_PERMISSION):
        raise AssignmentError("inventory.assignment.errors.self_approval_blocked", status_code=403)


def _infer_request_type(
    db: Session,
    child_asset_id: UUID,
    parent_asset_id: UUID | None,
) -> AssignmentRequestType:
    active = get_active_assignment(db, child_asset_id)
    if parent_asset_id is None:
        if active is None:
            raise AssignmentError("inventory.assignment.errors.not_assigned")
        return AssignmentRequestType.UNASSIGN
    if active is None:
        return AssignmentRequestType.ASSIGN
    if active.parent_asset_id == parent_asset_id:
        raise AssignmentError("inventory.assignment.errors.already_assigned")
    return AssignmentRequestType.REASSIGN


def _close_active_assignment(
    db: Session,
    active: InventoryAssetAssignment,
    *,
    effective_to: date,
) -> None:
    active.status = AssignmentRecordStatus.HISTORICAL
    active.effective_to = effective_to
    active.updated_at = _now()


def _apply_assignment_records(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User | None,
    clock: datetime | None = None,
) -> InventoryAssetAssignment | None:
    _lock_asset(db, request.child_asset_id)
    child = db.get(InventoryAsset, request.child_asset_id)
    assert child is not None

    active = get_active_assignment(db, request.child_asset_id)
    effective = request.effective_date

    if request.request_type in {AssignmentRequestType.REASSIGN, AssignmentRequestType.UNASSIGN}:
        if active is None:
            raise AssignmentError("inventory.assignment.errors.not_assigned")
        close_date = effective - timedelta(days=1) if effective > active.effective_from else effective
        _close_active_assignment(db, active, effective_to=close_date)

    if request.request_type == AssignmentRequestType.UNASSIGN:
        return None

    parent = db.get(InventoryAsset, request.parent_asset_id)
    if parent is None:
        raise AssignmentError("inventory.assignment.errors.parent_not_found", status_code=404)
    _validate_assignment_pair_db(db, child, parent)

    record = InventoryAssetAssignment(
        child_asset_id=request.child_asset_id,
        parent_asset_id=request.parent_asset_id,
        assignment_type=request.assignment_type,
        status=AssignmentRecordStatus.ACTIVE,
        effective_from=effective,
        effective_to=None,
        assignment_price=_quantize_price(request.assignment_price),
        currency=request.currency,
        supporting_document_id=request.supporting_document_id,
        related_transaction_id=request.related_transaction_id,
        notes=request.reason,
        created_by_user_id=actor.id if actor else request.requested_by_user_id,
        approved_by_user_id=actor.id if actor else None,
        assignment_request_id=request.id,
        is_demo=request.is_demo,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        raise AssignmentError("inventory.assignment.errors.active_assignment_exists", status_code=409) from exc
    return record


def mark_competing_requests_stale(
    db: Session,
    child_asset_id: UUID,
    *,
    exclude_request_id: UUID | None = None,
) -> int:
    pending = db.scalars(
        select(InventoryAssetAssignmentRequest).where(
            InventoryAssetAssignmentRequest.child_asset_id == child_asset_id,
            InventoryAssetAssignmentRequest.status.in_(PENDING_ASSIGNMENT_STATUSES),
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    ).all()
    current = build_assignment_snapshot(db, child_asset_id)
    marked = 0
    for competing in pending:
        if exclude_request_id and competing.id == exclude_request_id:
            continue
        if not snapshots_match(competing.source_assignment_snapshot, current):
            competing.status = AssignmentRequestStatus.STALE
            competing.updated_at = _now()
            _append_event(
                db,
                child_asset_id=child_asset_id,
                event_type="inventory.assignment.stale_conflict",
                actor=None,
                request_id=competing.id,
            )
            marked += 1
    return marked


def create_assignment_request(
    db: Session,
    *,
    child_asset_id: UUID,
    parent_asset_id: UUID | None,
    effective_date: date,
    reason: str,
    assignment_price: Decimal | None,
    currency: str,
    supporting_document_id: UUID | None,
    related_transaction_id: UUID | None,
    assigned_approver_user_id: UUID | None,
    actor: User,
    submit: bool = False,
    request_type: AssignmentRequestType | None = None,
) -> InventoryAssetAssignmentRequest:
    child = _lock_asset(db, child_asset_id)
    _validate_child_asset(child)

    inferred = request_type or _infer_request_type(db, child_asset_id, parent_asset_id)

    if inferred != AssignmentRequestType.UNASSIGN:
        if parent_asset_id is None:
            raise AssignmentError("inventory.assignment.errors.parent_required")
        parent = _lock_asset(db, parent_asset_id)
        _validate_assignment_pair_db(db, child, parent)
    elif parent_asset_id is not None:
        raise AssignmentError("inventory.assignment.errors.parent_not_allowed_for_unassign")

    snapshot = build_assignment_snapshot(db, child_asset_id)
    assignment_type = assignment_type_for_child(child.asset_type)

    request = InventoryAssetAssignmentRequest(
        child_asset_id=child_asset_id,
        parent_asset_id=parent_asset_id,
        request_type=inferred,
        assignment_type=assignment_type,
        effective_date=effective_date,
        reason=reason,
        source_assignment_snapshot=json.dumps(snapshot),
        assignment_price=_quantize_price(assignment_price),
        currency=currency.upper(),
        supporting_document_id=supporting_document_id,
        related_transaction_id=related_transaction_id,
        requested_by_user_id=actor.id,
        assigned_approver_user_id=assigned_approver_user_id,
        status=AssignmentRequestStatus.DRAFT,
        is_demo=child.is_demo,
    )
    db.add(request)
    db.flush()

    event_type = (
        "inventory.assignment.requested" if submit else "inventory.assignment.draft_created"
    )
    _append_event(db, child_asset_id=child_asset_id, event_type=event_type, actor=actor, request_id=request.id)

    if submit:
        submit_assignment_request(db, request, actor=actor)

    return request


def submit_assignment_request(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
) -> InventoryAssetAssignmentRequest:
    if request.status != AssignmentRequestStatus.DRAFT:
        raise AssignmentError("inventory.assignment.errors.request_not_submittable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_assignment"
    ):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)

    _check_stale_request(db, request)
    request.status = AssignmentRequestStatus.SUBMITTED
    request.updated_at = _now()
    _append_event(
        db,
        child_asset_id=request.child_asset_id,
        event_type="inventory.assignment.requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def review_assignment_request(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
) -> InventoryAssetAssignmentRequest:
    if request.status not in PENDING_ASSIGNMENT_STATUSES:
        raise AssignmentError("inventory.assignment.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_assignment"):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)

    _check_stale_request(db, request)
    request.status = AssignmentRequestStatus.UNDER_REVIEW
    request.reviewed_at = _now()
    request.updated_at = _now()
    return request


def approve_assignment_request(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
    comments: str | None = None,
    clock: datetime | None = None,
) -> tuple[InventoryAssetAssignmentRequest, InventoryAssetAssignment | None]:
    if request.status == AssignmentRequestStatus.STALE:
        raise AssignmentError("inventory.assignment.errors.stale_request", status_code=409)
    if request.status not in PENDING_ASSIGNMENT_STATUSES:
        raise AssignmentError("inventory.assignment.errors.request_not_approvable")

    _ensure_can_approve(actor, request.requested_by_user_id)
    _check_stale_request(db, request)

    now = _now(clock)
    today = _today(clock)

    db.add(
        InventoryAssetAssignmentApproval(
            assignment_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=AssignmentApprovalDecision.APPROVED,
            comments=comments,
        )
    )

    request.approved_at = now
    request.updated_at = now
    created: InventoryAssetAssignment | None = None

    if request.effective_date > today:
        request.status = AssignmentRequestStatus.APPROVED
        _append_event(
            db,
            child_asset_id=request.child_asset_id,
            event_type="inventory.assignment.scheduled",
            actor=actor,
            request_id=request.id,
            metadata={"effective_date": request.effective_date.isoformat()},
        )
    else:
        created = _apply_assignment_records(db, request, actor=actor, clock=clock)
        request.status = AssignmentRequestStatus.APPLIED
        mark_competing_requests_stale(db, request.child_asset_id, exclude_request_id=request.id)
        event_name = (
            "inventory.assignment.unassigned"
            if request.request_type == AssignmentRequestType.UNASSIGN
            else "inventory.assignment.assigned"
        )
        _append_event(
            db,
            child_asset_id=request.child_asset_id,
            event_type="inventory.assignment.approved",
            actor=actor,
            request_id=request.id,
        )
        _append_event(
            db,
            child_asset_id=request.child_asset_id,
            event_type=event_name,
            actor=actor,
            request_id=request.id,
            assignment_id=created.id if created else None,
        )

    return request, created


def apply_scheduled_assignment(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    clock: datetime | None = None,
) -> InventoryAssetAssignment | None:
    if request.status == AssignmentRequestStatus.APPLIED:
        return None
    if request.status != AssignmentRequestStatus.APPROVED:
        raise AssignmentError("inventory.assignment.errors.request_not_applicable")

    today = _today(clock)
    if request.effective_date > today:
        return None

    current = build_assignment_snapshot(db, request.child_asset_id)
    if not snapshots_match(request.source_assignment_snapshot, current):
        request.status = AssignmentRequestStatus.STALE
        request.updated_at = _now(clock)
        _append_event(
            db,
            child_asset_id=request.child_asset_id,
            event_type="inventory.assignment.stale_conflict",
            actor=None,
            request_id=request.id,
        )
        raise AssignmentError("inventory.assignment.errors.stale_request", status_code=409)

    created = _apply_assignment_records(db, request, actor=None, clock=clock)
    request.status = AssignmentRequestStatus.APPLIED
    request.updated_at = _now(clock)
    mark_competing_requests_stale(db, request.child_asset_id, exclude_request_id=request.id)

    event_name = (
        "inventory.assignment.unassigned"
        if request.request_type == AssignmentRequestType.UNASSIGN
        else "inventory.assignment.assigned"
    )
    _append_event(
        db,
        child_asset_id=request.child_asset_id,
        event_type=event_name,
        actor=None,
        request_id=request.id,
        assignment_id=created.id if created else None,
        metadata={"scheduled": True},
    )
    return created


def reject_assignment_request(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
    decision_notes: str,
) -> InventoryAssetAssignmentRequest:
    if request.status not in PENDING_ASSIGNMENT_STATUSES:
        raise AssignmentError("inventory.assignment.errors.request_not_rejectable")
    if not user_has_permission(actor, "inventory", "reject_assignment"):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)
    if request.requested_by_user_id == actor.id:
        raise AssignmentError("inventory.assignment.errors.self_approval_blocked", status_code=403)

    now = _now()
    request.status = AssignmentRequestStatus.REJECTED
    request.rejected_at = now
    request.decision_notes = decision_notes
    request.updated_at = now

    db.add(
        InventoryAssetAssignmentApproval(
            assignment_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=AssignmentApprovalDecision.REJECTED,
            comments=decision_notes,
        )
    )
    _append_event(
        db,
        child_asset_id=request.child_asset_id,
        event_type="inventory.assignment.rejected",
        actor=actor,
        request_id=request.id,
    )
    return request


def request_assignment_revision(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
    decision_notes: str,
) -> InventoryAssetAssignmentRequest:
    if request.status not in PENDING_ASSIGNMENT_STATUSES:
        raise AssignmentError("inventory.assignment.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_assignment"):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)

    request.status = AssignmentRequestStatus.DRAFT
    request.decision_notes = decision_notes
    request.reviewed_at = _now()
    request.updated_at = _now()

    db.add(
        InventoryAssetAssignmentApproval(
            assignment_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=AssignmentApprovalDecision.REVISION_REQUESTED,
            comments=decision_notes,
        )
    )
    _append_event(
        db,
        child_asset_id=request.child_asset_id,
        event_type="inventory.assignment.revision_requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def withdraw_assignment_request(
    db: Session,
    request: InventoryAssetAssignmentRequest,
    *,
    actor: User,
) -> InventoryAssetAssignmentRequest:
    if request.status not in {
        AssignmentRequestStatus.DRAFT,
        AssignmentRequestStatus.SUBMITTED,
        AssignmentRequestStatus.UNDER_REVIEW,
    }:
        raise AssignmentError("inventory.assignment.errors.request_not_withdrawable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_assignment"
    ):
        raise AssignmentError("inventory.assignment.errors.permission_denied", status_code=403)

    request.status = AssignmentRequestStatus.WITHDRAWN
    request.updated_at = _now()
    _append_event(
        db,
        child_asset_id=request.child_asset_id,
        event_type="inventory.assignment.withdrawn",
        actor=actor,
        request_id=request.id,
    )
    return request


def enrich_assignment_summary(
    db: Session,
    asset: InventoryAsset,
    *,
    user: User | None,
) -> dict[str, Any]:
    if user is None or not user_has_permission(user, "inventory", "view_assignment"):
        return {
            "assigned_to_display_id": None,
            "assigned_to_asset_id": None,
            "assignment_status": "unknown",
            "assignment_type": None,
            "parking_count": 0,
            "storage_count": 0,
            "has_scheduled": False,
            "has_pending": False,
        }

    is_child = asset.asset_type in CHILD_ASSIGNMENT_ASSET_TYPES
    is_parent = asset.asset_type in PARENT_ASSIGNMENT_ASSET_TYPES

    active = get_active_assignment(db, asset.id) if is_child else None
    parent_asset = db.get(InventoryAsset, active.parent_asset_id) if active else None

    parking_count = 0
    storage_count = 0
    if is_parent:
        for row in get_parent_accessories(db, asset.id):
            child = db.get(InventoryAsset, row.child_asset_id)
            if child and child.asset_type == InventoryAssetType.PARKING_SPACE:
                parking_count += 1
            elif child and child.asset_type == InventoryAssetType.STORAGE_UNIT:
                storage_count += 1

    pending = db.scalar(
        select(func.count())
        .select_from(InventoryAssetAssignmentRequest)
        .where(
            InventoryAssetAssignmentRequest.child_asset_id == asset.id,
            InventoryAssetAssignmentRequest.status.in_(PENDING_ASSIGNMENT_STATUSES),
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    )
    scheduled = db.scalar(
        select(func.count())
        .select_from(InventoryAssetAssignmentRequest)
        .where(
            InventoryAssetAssignmentRequest.child_asset_id == asset.id,
            InventoryAssetAssignmentRequest.status == AssignmentRequestStatus.APPROVED,
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    )

    return {
        "assigned_to_display_id": parent_asset.display_id if parent_asset else None,
        "assigned_to_asset_id": str(active.parent_asset_id) if active else None,
        "assignment_status": "assigned" if active else "unassigned",
        "assignment_type": active.assignment_type.value if active else None,
        "parking_count": parking_count,
        "storage_count": storage_count,
        "has_scheduled": bool(scheduled),
        "has_pending": bool(pending),
    }


def list_due_scheduled_assignments(
    db: Session,
    *,
    clock: datetime | None = None,
) -> list[InventoryAssetAssignmentRequest]:
    today = _today(clock)
    return list(
        db.scalars(
            select(InventoryAssetAssignmentRequest).where(
                InventoryAssetAssignmentRequest.status == AssignmentRequestStatus.APPROVED,
                InventoryAssetAssignmentRequest.effective_date <= today,
                InventoryAssetAssignmentRequest.archived_at.is_(None),
            )
        ).all()
    )


def count_unassigned_accessories(db: Session, project_id: UUID | None = None) -> int:
    child_query = select(InventoryAsset.id).where(
        InventoryAsset.asset_type.in_(CHILD_ASSIGNMENT_ASSET_TYPES),
        InventoryAsset.archived_at.is_(None),
    )
    if project_id:
        child_query = child_query.where(InventoryAsset.project_id == project_id)
    child_ids = list(db.scalars(child_query).all())
    if not child_ids:
        return 0

    assigned_ids = set(
        db.scalars(
            select(InventoryAssetAssignment.child_asset_id).where(
                InventoryAssetAssignment.status == AssignmentRecordStatus.ACTIVE,
                InventoryAssetAssignment.child_asset_id.in_(child_ids),
            )
        ).all()
    )
    return sum(1 for cid in child_ids if cid not in assigned_ids)
