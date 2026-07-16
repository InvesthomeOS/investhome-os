"""Inventory assignment API routes."""

from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.inventory import (
    CHILD_ASSIGNMENT_ASSET_TYPES,
    AssignmentRecordStatus,
    AssignmentRequestStatus,
    AssignmentRequestType,
    InventoryAsset,
    InventoryAssetAssignment,
    InventoryAssetAssignmentRequest,
    PENDING_ASSIGNMENT_STATUSES,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory_assignment import (
    AssetAssignmentDetailResponse,
    AssignmentDecisionInput,
    AssignmentRecordResponse,
    AssignmentRequestCreate,
    AssignmentRequestListResponse,
    AssignmentRequestResponse,
    AssignmentRequestUpdate,
    AssignmentSummaryResponse,
)
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity
from investhome_api.services.inventory.assignment_notifications import (
    notify_assignment_approved,
    notify_assignment_rejected,
    notify_assignment_revision,
    notify_assignment_submitted,
    notify_stale_conflict,
)
from investhome_api.services.inventory.assignment_service import (
    AssignmentError,
    approve_assignment_request,
    create_assignment_request,
    enrich_assignment_summary,
    get_active_assignment,
    get_assignment_history,
    get_parent_accessories,
    reject_assignment_request,
    request_assignment_revision,
    review_assignment_request,
    submit_assignment_request,
    withdraw_assignment_request,
)
from investhome_api.services.permission_service import user_has_permission

assignments_router = APIRouter(prefix="/inventory/assignments", tags=["inventory-assignments"])
requests_router = APIRouter(prefix="/inventory/assignment-requests", tags=["inventory-assignments"])


def _assignment_error(exc: AssignmentError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _get_asset_or_404(asset_id: UUID, db: Session) -> InventoryAsset:
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory asset not found")
    return asset


def _get_request_or_404(request_id: UUID, db: Session) -> InventoryAssetAssignmentRequest:
    request = db.get(InventoryAssetAssignmentRequest, request_id)
    if request is None or request.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment request not found")
    return request


def _enrich_record(db: Session, record: InventoryAssetAssignment) -> AssignmentRecordResponse:
    child = db.get(InventoryAsset, record.child_asset_id)
    parent = db.get(InventoryAsset, record.parent_asset_id)
    return AssignmentRecordResponse(
        id=record.id,
        child_asset_id=record.child_asset_id,
        child_display_id=child.display_id if child else None,
        parent_asset_id=record.parent_asset_id,
        parent_display_id=parent.display_id if parent else None,
        assignment_type=record.assignment_type,
        status=record.status,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        assignment_price=record.assignment_price,
        currency=record.currency,
        supporting_document_id=record.supporting_document_id,
        related_transaction_id=record.related_transaction_id,
        notes=record.notes,
        created_by_user_id=record.created_by_user_id,
        approved_by_user_id=record.approved_by_user_id,
        assignment_request_id=record.assignment_request_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _enrich_request(db: Session, request: InventoryAssetAssignmentRequest, user: User) -> AssignmentRequestResponse:
    child = db.get(InventoryAsset, request.child_asset_id)
    parent = db.get(InventoryAsset, request.parent_asset_id) if request.parent_asset_id else None
    project = db.get(Project, child.project_id) if child else None

    actions: list[str] = []
    if request.status == AssignmentRequestStatus.DRAFT and (
        request.requested_by_user_id == user.id
        or user_has_permission(user, "inventory", "review_assignment")
    ):
        actions.append("submit")
    if request.status in PENDING_ASSIGNMENT_STATUSES:
        if user_has_permission(user, "inventory", "review_assignment"):
            actions.append("review")
        if user_has_permission(user, "inventory", "approve_assignment") and (
            request.requested_by_user_id != user.id
            or user_has_permission(user, "inventory", "self_approve_assignment")
        ):
            actions.append("approve")
        if user_has_permission(user, "inventory", "reject_assignment") and request.requested_by_user_id != user.id:
            actions.append("reject")

    return AssignmentRequestResponse(
        id=request.id,
        child_asset_id=request.child_asset_id,
        child_display_id=child.display_id if child else None,
        parent_asset_id=request.parent_asset_id,
        parent_display_id=parent.display_id if parent else None,
        project_name=project.project_name if project else None,
        request_type=request.request_type,
        assignment_type=request.assignment_type,
        effective_date=request.effective_date,
        reason=request.reason,
        assignment_price=request.assignment_price,
        currency=request.currency,
        supporting_document_id=request.supporting_document_id,
        related_transaction_id=request.related_transaction_id,
        requested_by_user_id=request.requested_by_user_id,
        assigned_approver_user_id=request.assigned_approver_user_id,
        status=request.status,
        reviewed_at=request.reviewed_at,
        approved_at=request.approved_at,
        rejected_at=request.rejected_at,
        decision_notes=request.decision_notes,
        actions=actions,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@assignments_router.get("/summary/by-asset/{asset_id}", response_model=AssignmentSummaryResponse)
def get_assignment_summary(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view")),
) -> AssignmentSummaryResponse:
    asset = _get_asset_or_404(asset_id, db)
    summary = enrich_assignment_summary(db, asset, user=user)
    return AssignmentSummaryResponse(**summary)


@assignments_router.get("/by-child/{child_asset_id}/current", response_model=AssignmentRecordResponse | None)
def get_current_assignment(
    child_asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> AssignmentRecordResponse | None:
    _get_asset_or_404(child_asset_id, db)
    active = get_active_assignment(db, child_asset_id)
    if active is None:
        return None
    return _enrich_record(db, active)


@assignments_router.get("/by-child/{child_asset_id}/history", response_model=list[AssignmentRecordResponse])
def list_assignment_history(
    child_asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment_history")),
) -> list[AssignmentRecordResponse]:
    _get_asset_or_404(child_asset_id, db)
    return [_enrich_record(db, row) for row in get_assignment_history(db, child_asset_id)]


@assignments_router.get("/by-parent/{parent_asset_id}", response_model=list[AssignmentRecordResponse])
def list_parent_accessories(
    parent_asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> list[AssignmentRecordResponse]:
    _get_asset_or_404(parent_asset_id, db)
    return [_enrich_record(db, row) for row in get_parent_accessories(db, parent_asset_id)]


@assignments_router.get("/by-asset/{asset_id}/detail", response_model=AssetAssignmentDetailResponse)
def get_asset_assignment_detail(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> AssetAssignmentDetailResponse:
    asset = _get_asset_or_404(asset_id, db)
    active = get_active_assignment(db, asset_id)
    history = get_assignment_history(db, asset_id) if user_has_permission(user, "inventory", "view_assignment_history") else []

    pending = list(
        db.scalars(
            select(InventoryAssetAssignmentRequest).where(
                InventoryAssetAssignmentRequest.child_asset_id == asset_id,
                InventoryAssetAssignmentRequest.status.in_(PENDING_ASSIGNMENT_STATUSES),
                InventoryAssetAssignmentRequest.archived_at.is_(None),
            )
        ).all()
    )
    scheduled = list(
        db.scalars(
            select(InventoryAssetAssignmentRequest).where(
                InventoryAssetAssignmentRequest.child_asset_id == asset_id,
                InventoryAssetAssignmentRequest.status == AssignmentRequestStatus.APPROVED,
                InventoryAssetAssignmentRequest.archived_at.is_(None),
            )
        ).all()
    )

    accessories = get_parent_accessories(db, asset_id) if asset.asset_type not in CHILD_ASSIGNMENT_ASSET_TYPES else []

    return AssetAssignmentDetailResponse(
        child_asset_id=asset_id,
        current=_enrich_record(db, active) if active else None,
        history=[_enrich_record(db, row) for row in history],
        pending_requests=[_enrich_request(db, row, user) for row in pending],
        scheduled_requests=[_enrich_request(db, row, user) for row in scheduled],
        parent_accessories=[_enrich_record(db, row) for row in accessories],
    )


@assignments_router.get("/unassigned", response_model=list[AssignmentRecordResponse])
def list_unassigned_children(
    project_id: UUID | None = None,
    assignment_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> list[AssignmentRecordResponse]:
    del user
    child_query = select(InventoryAsset).where(
        InventoryAsset.asset_type.in_(CHILD_ASSIGNMENT_ASSET_TYPES),
        InventoryAsset.archived_at.is_(None),
    )
    if project_id:
        child_query = child_query.where(InventoryAsset.project_id == project_id)
    if assignment_type == "parking_for":
        child_query = child_query.where(InventoryAsset.asset_type == "parking_space")
    elif assignment_type == "storage_for":
        child_query = child_query.where(InventoryAsset.asset_type == "storage_unit")

    children = db.scalars(child_query).all()
    assigned_ids = set(
        db.scalars(
            select(InventoryAssetAssignment.child_asset_id).where(
                InventoryAssetAssignment.status == AssignmentRecordStatus.ACTIVE,
            )
        ).all()
    )
    return [
        AssignmentRecordResponse(
            id=child.id,
            child_asset_id=child.id,
            child_display_id=child.display_id,
            parent_asset_id=child.id,
            parent_display_id=None,
            assignment_type="parking_for" if child.asset_type.value == "parking_space" else "storage_for",
            status=AssignmentRecordStatus.ACTIVE,
            effective_from=child.created_at.date(),
            effective_to=None,
            assignment_price=None,
            currency=child.currency,
            supporting_document_id=None,
            related_transaction_id=None,
            notes=None,
            created_by_user_id=None,
            approved_by_user_id=None,
            assignment_request_id=None,
            created_at=child.created_at,
            updated_at=child.updated_at,
        )
        for child in children
        if child.id not in assigned_ids
    ]


@requests_router.get("", response_model=AssignmentRequestListResponse)
def list_assignment_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
    project_id: UUID | None = None,
    child_asset_id: UUID | None = None,
    parent_asset_id: UUID | None = None,
    status_filter: AssignmentRequestStatus | None = Query(default=None, alias="status"),
    request_type: AssignmentRequestType | None = None,
    requester_id: UUID | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> AssignmentRequestListResponse:
    query = select(InventoryAssetAssignmentRequest).join(
        InventoryAsset, InventoryAsset.id == InventoryAssetAssignmentRequest.child_asset_id
    )
    if not include_archived:
        query = query.where(InventoryAssetAssignmentRequest.archived_at.is_(None))
    if project_id:
        query = query.where(InventoryAsset.project_id == project_id)
    if child_asset_id:
        query = query.where(InventoryAssetAssignmentRequest.child_asset_id == child_asset_id)
    if parent_asset_id:
        query = query.where(InventoryAssetAssignmentRequest.parent_asset_id == parent_asset_id)
    if status_filter:
        query = query.where(InventoryAssetAssignmentRequest.status == status_filter)
    if request_type:
        query = query.where(InventoryAssetAssignmentRequest.request_type == request_type)
    if requester_id:
        query = query.where(InventoryAssetAssignmentRequest.requested_by_user_id == requester_id)
    if effective_from:
        query = query.where(InventoryAssetAssignmentRequest.effective_date >= effective_from)
    if effective_to:
        query = query.where(InventoryAssetAssignmentRequest.effective_date <= effective_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_col = getattr(InventoryAssetAssignmentRequest, sort_by, InventoryAssetAssignmentRequest.created_at)
    order = desc(sort_col) if sort_order == "desc" else asc(sort_col)
    rows = db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return AssignmentRequestListResponse(
        items=[_enrich_request(db, row, user) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, ceil(total / page_size)) if total else 0,
    )


@requests_router.get("/pending-approvals", response_model=list[AssignmentRequestResponse])
def list_pending_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_assignment")),
) -> list[AssignmentRequestResponse]:
    rows = db.scalars(
        select(InventoryAssetAssignmentRequest).where(
            InventoryAssetAssignmentRequest.status.in_(PENDING_ASSIGNMENT_STATUSES),
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/scheduled", response_model=list[AssignmentRequestResponse])
def list_scheduled_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> list[AssignmentRequestResponse]:
    rows = db.scalars(
        select(InventoryAssetAssignmentRequest).where(
            InventoryAssetAssignmentRequest.status == AssignmentRequestStatus.APPROVED,
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/stale", response_model=list[AssignmentRequestResponse])
def list_stale_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_assignment")),
) -> list[AssignmentRequestResponse]:
    rows = db.scalars(
        select(InventoryAssetAssignmentRequest).where(
            InventoryAssetAssignmentRequest.status == AssignmentRequestStatus.STALE,
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@requests_router.get("/conflicts", response_model=list[AssignmentRequestResponse])
def list_conflict_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_assignment")),
) -> list[AssignmentRequestResponse]:
    rows = db.scalars(
        select(InventoryAssetAssignmentRequest).where(
            InventoryAssetAssignmentRequest.status.in_(
                {AssignmentRequestStatus.STALE, AssignmentRequestStatus.SUBMITTED, AssignmentRequestStatus.UNDER_REVIEW}
            ),
            InventoryAssetAssignmentRequest.archived_at.is_(None),
        )
    ).all()
    stale_only = [row for row in rows if row.status == AssignmentRequestStatus.STALE]
    return [_enrich_request(db, row, user) for row in stale_only]


@requests_router.get("/{request_id}", response_model=AssignmentRequestResponse)
def get_assignment_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_assignment")),
) -> AssignmentRequestResponse:
    return _enrich_request(db, _get_request_or_404(request_id, db), user)


@requests_router.post("", response_model=AssignmentRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: AssignmentRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "request_assignment")),
) -> AssignmentRequestResponse:
    try:
        created = create_assignment_request(
            db,
            child_asset_id=payload.child_asset_id,
            parent_asset_id=payload.parent_asset_id,
            effective_date=payload.effective_date,
            reason=payload.reason,
            assignment_price=payload.assignment_price,
            currency=payload.currency,
            supporting_document_id=payload.supporting_document_id,
            related_transaction_id=payload.related_transaction_id,
            assigned_approver_user_id=payload.assigned_approver_user_id,
            actor=actor,
            submit=payload.submit,
            request_type=payload.request_type,
        )
        child = db.get(InventoryAsset, created.child_asset_id)
        if payload.submit and child:
            notify_assignment_submitted(db, created, display_id=child.display_id, requester=actor)
        log_activity(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=created.child_asset_id,
            action=ActivityAction.CREATED,
            description_key="activity.inventory.assignment.submitted" if payload.submit else "activity.inventory.assignment.draft_created",
            actor_user=actor,
            request_context=activity_context_from_request(request),
            is_demo=created.is_demo,
        )
        db.commit()
        db.refresh(created)
    except AssignmentError as exc:
        db.rollback()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, created, actor)


@requests_router.post("/{request_id}/submit", response_model=AssignmentRequestResponse)
def submit_request(
    request_id: UUID,
    http_request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "request_assignment")),
) -> AssignmentRequestResponse:
    row = _get_request_or_404(request_id, db)
    try:
        submit_assignment_request(db, row, actor=actor)
        child = db.get(InventoryAsset, row.child_asset_id)
        if child:
            notify_assignment_submitted(db, row, display_id=child.display_id, requester=actor)
        log_activity(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=row.child_asset_id,
            action=ActivityAction.UPDATED,
            description_key="activity.inventory.assignment.submitted",
            actor_user=actor,
            request_context=activity_context_from_request(http_request),
            is_demo=row.is_demo,
        )
        db.commit()
        db.refresh(row)
    except AssignmentError as exc:
        db.rollback()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, row, actor)


@requests_router.post("/{request_id}/review", response_model=AssignmentRequestResponse)
def review_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "review_assignment")),
) -> AssignmentRequestResponse:
    row = _get_request_or_404(request_id, db)
    try:
        review_assignment_request(db, row, actor=actor)
        db.commit()
        db.refresh(row)
    except AssignmentError as exc:
        db.rollback()
        if exc.error_key == "inventory.assignment.errors.stale_request":
            child = db.get(InventoryAsset, row.child_asset_id)
            requester = db.get(User, row.requested_by_user_id)
            if child and requester:
                notify_stale_conflict(db, row, [requester], display_id=child.display_id)
            db.commit()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, row, actor)


@requests_router.post("/{request_id}/approve", response_model=AssignmentRequestResponse)
def approve_request(
    request_id: UUID,
    payload: AssignmentDecisionInput,
    http_request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "approve_assignment")),
) -> AssignmentRequestResponse:
    row = _get_request_or_404(request_id, db)
    requester = db.get(User, row.requested_by_user_id)
    child = db.get(InventoryAsset, row.child_asset_id)
    try:
        updated, _created = approve_assignment_request(db, row, actor=actor, comments=payload.comments)
        scheduled = updated.status == AssignmentRequestStatus.APPROVED
        if requester and child:
            notify_assignment_approved(db, updated, requester, display_id=child.display_id, scheduled=scheduled)
        log_activity(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=updated.child_asset_id,
            action=ActivityAction.APPROVED,
            description_key="activity.inventory.assignment.approved",
            actor_user=actor,
            request_context=activity_context_from_request(http_request),
            is_demo=updated.is_demo,
        )
        db.commit()
        db.refresh(updated)
    except AssignmentError as exc:
        db.rollback()
        if exc.error_key == "inventory.assignment.errors.stale_request" and requester and child:
            notify_stale_conflict(db, row, [requester], display_id=child.display_id)
            db.commit()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, updated, actor)


@requests_router.post("/{request_id}/reject", response_model=AssignmentRequestResponse)
def reject_request(
    request_id: UUID,
    payload: AssignmentDecisionInput,
    http_request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "reject_assignment")),
) -> AssignmentRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.assignment.errors.decision_notes_required")
    row = _get_request_or_404(request_id, db)
    requester = db.get(User, row.requested_by_user_id)
    child = db.get(InventoryAsset, row.child_asset_id)
    try:
        reject_assignment_request(db, row, actor=actor, decision_notes=payload.decision_notes)
        if requester and child:
            notify_assignment_rejected(db, row, requester, display_id=child.display_id)
        log_activity(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=row.child_asset_id,
            action=ActivityAction.REJECTED,
            description_key="activity.inventory.assignment.rejected",
            actor_user=actor,
            request_context=activity_context_from_request(http_request),
            is_demo=row.is_demo,
        )
        db.commit()
        db.refresh(row)
    except AssignmentError as exc:
        db.rollback()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, row, actor)


@requests_router.post("/{request_id}/request-revision", response_model=AssignmentRequestResponse)
def revision_request(
    request_id: UUID,
    payload: AssignmentDecisionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "review_assignment")),
) -> AssignmentRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.assignment.errors.decision_notes_required")
    row = _get_request_or_404(request_id, db)
    requester = db.get(User, row.requested_by_user_id)
    child = db.get(InventoryAsset, row.child_asset_id)
    try:
        request_assignment_revision(db, row, actor=actor, decision_notes=payload.decision_notes)
        if requester and child:
            notify_assignment_revision(db, row, requester, display_id=child.display_id)
        db.commit()
        db.refresh(row)
    except AssignmentError as exc:
        db.rollback()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, row, actor)


@requests_router.post("/{request_id}/withdraw", response_model=AssignmentRequestResponse)
def withdraw_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "request_assignment")),
) -> AssignmentRequestResponse:
    row = _get_request_or_404(request_id, db)
    try:
        withdraw_assignment_request(db, row, actor=actor)
        db.commit()
        db.refresh(row)
    except AssignmentError as exc:
        db.rollback()
        raise _assignment_error(exc) from exc
    return _enrich_request(db, row, actor)
