"""Inventory ownership API routes."""

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
    LEGAL_OWNERSHIP_TYPES,
    InventoryAsset,
    InventoryOwnership,
    OwnershipRecordStatus,
    OwnershipTransferParty,
    OwnershipTransferRequest,
    OwnershipType,
    PENDING_TRANSFER_STATUSES,
    SCHEDULED_TRANSFER_STATUSES,
    TransferRequestStatus,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory_ownership import (
    AssetOwnershipDetailResponse,
    OwnershipApprovalRecordResponse,
    OwnershipDecisionInput,
    OwnershipRecordResponse,
    OwnershipSummaryResponse,
    OwnershipTransferRequestCreate,
    OwnershipTransferRequestListResponse,
    OwnershipTransferRequestResponse,
    OwnershipTransferRequestUpdate,
    TransferPartyInput,
    TransferPartyResponse,
)
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity
from investhome_api.services.inventory.ownership_notifications import (
    notify_finance_reviewers_if_legal,
    notify_stale_conflict,
    notify_transfer_approved,
    notify_transfer_rejected,
    notify_transfer_revision,
    notify_transfer_submitted,
)
from investhome_api.services.inventory.ownership_service import (
    OwnershipError,
    approve_transfer_request,
    build_ownership_snapshot,
    create_transfer_request,
    enrich_ownership_summary,
    get_active_ownership,
    get_ownership_history,
    reject_transfer_request,
    request_transfer_revision,
    review_transfer_request,
    submit_transfer_request,
    sum_active_legal_percentages,
    sum_legal_percentages,
    withdraw_transfer_request,
)
from investhome_api.services.permission_service import user_has_permission

ownership_router = APIRouter(prefix="/inventory/ownership", tags=["inventory-ownership"])
transfers_router = APIRouter(prefix="/inventory/ownership-transfers", tags=["inventory-ownership"])


def _ownership_error(exc: OwnershipError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _log_ownership_activity(
    request: Request,
    db: Session,
    *,
    user: User,
    entity_id: UUID,
    action: ActivityAction,
    description_key: str,
    metadata: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.INVENTORY_OWNERSHIP,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=user,
        metadata=metadata,
        request_context=activity_context_from_request(request),
    )


def _get_asset_or_404(asset_id: UUID, db: Session) -> InventoryAsset:
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory asset not found")
    return asset


def _get_request_or_404(request_id: UUID, db: Session) -> OwnershipTransferRequest:
    request = db.get(OwnershipTransferRequest, request_id)
    if request is None or request.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ownership transfer request not found")
    return request


def _party_info(db: Session, party_id: UUID) -> tuple[str | None, str | None]:
    party = db.get(Investor, party_id)
    if party is None:
        return None, None
    return party.full_name, party.investor_type.value if party.investor_type else None


def _enrich_record(db: Session, record: InventoryOwnership) -> OwnershipRecordResponse:
    name, ptype = _party_info(db, record.party_id)
    return OwnershipRecordResponse(
        id=record.id,
        inventory_asset_id=record.inventory_asset_id,
        party_id=record.party_id,
        party_name=name,
        party_type=ptype,
        ownership_type=record.ownership_type,
        ownership_percentage=record.ownership_percentage,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        status=record.status,
        acquisition_method=record.acquisition_method,
        transfer_reason=record.transfer_reason,
        related_document_id=record.related_document_id,
        related_transaction_id=record.related_transaction_id,
        source=record.source,
        notes=record.notes,
        created_by_user_id=record.created_by_user_id,
        approved_by_user_id=record.approved_by_user_id,
        ownership_transfer_request_id=record.ownership_transfer_request_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _enrich_party(db: Session, party: OwnershipTransferParty) -> TransferPartyResponse:
    name, ptype = _party_info(db, party.party_id)
    return TransferPartyResponse(
        id=party.id,
        party_id=party.party_id,
        party_name=name,
        party_type=ptype,
        ownership_type=party.ownership_type,
        previous_percentage=party.previous_percentage,
        proposed_percentage=party.proposed_percentage,
        role=party.role,
        notes=party.notes,
        created_at=party.created_at,
    )


def _enrich_request(db: Session, request: OwnershipTransferRequest, user: User) -> OwnershipTransferRequestResponse:
    asset = db.get(InventoryAsset, request.inventory_asset_id)
    project = db.get(Project, asset.project_id) if asset else None
    parties = list(
        db.scalars(
            select(OwnershipTransferParty).where(
                OwnershipTransferParty.ownership_transfer_request_id == request.id
            )
        ).all()
    )
    actions: list[str] = []
    if request.status == TransferRequestStatus.DRAFT and (
        request.requested_by_user_id == user.id
        or user_has_permission(user, "inventory", "review_ownership_change")
    ):
        actions.extend(["update", "submit", "withdraw"])
    if request.status in PENDING_TRANSFER_STATUSES:
        if user_has_permission(user, "inventory", "review_ownership_change"):
            actions.append("review")
        if user_has_permission(user, "inventory", "approve_ownership_change"):
            if request.requested_by_user_id != user.id or user_has_permission(
                user, "inventory", "self_approve_ownership_change"
            ):
                actions.append("approve")
        if user_has_permission(user, "inventory", "reject_ownership_change"):
            actions.extend(["reject", "request_revision"])
        if request.requested_by_user_id == user.id:
            actions.append("withdraw")

    legal_active = get_active_ownership(db, request.inventory_asset_id, ownership_types=LEGAL_OWNERSHIP_TYPES)
    return OwnershipTransferRequestResponse(
        id=request.id,
        inventory_asset_id=request.inventory_asset_id,
        asset_display_id=asset.display_id if asset else None,
        project_name=project.project_name if project else None,
        transfer_type=request.transfer_type,
        effective_date=request.effective_date,
        reason=request.reason,
        supporting_document_id=request.supporting_document_id,
        related_transaction_id=request.related_transaction_id,
        requested_by_user_id=request.requested_by_user_id,
        assigned_approver_user_id=request.assigned_approver_user_id,
        status=request.status,
        reviewed_at=request.reviewed_at,
        approved_at=request.approved_at,
        rejected_at=request.rejected_at,
        decision_notes=request.decision_notes,
        parties=[_enrich_party(db, p) for p in parties],
        actions=actions,
        proposed_legal_total=sum_legal_percentages(parties),
        current_legal_total=sum_active_legal_percentages(legal_active),
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _build_party_rows(parties: list[TransferPartyInput]) -> list[OwnershipTransferParty]:
    return [
        OwnershipTransferParty(
            party_id=row.party_id,
            ownership_type=row.ownership_type,
            previous_percentage=row.previous_percentage,
            proposed_percentage=row.proposed_percentage,
            role=row.role,
            notes=row.notes,
        )
        for row in parties
    ]


@ownership_router.get("/by-asset/{asset_id}/current", response_model=list[OwnershipRecordResponse])
def get_current_ownership(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> list[OwnershipRecordResponse]:
    _get_asset_or_404(asset_id, db)
    records = get_active_ownership(db, asset_id)
    result: list[OwnershipRecordResponse] = []
    for record in records:
        if record.ownership_type in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}:
            if not user_has_permission(user, "inventory", "view_beneficial_ownership"):
                continue
        result.append(_enrich_record(db, record))
    return result


@ownership_router.get("/by-asset/{asset_id}/history", response_model=list[OwnershipRecordResponse])
def get_ownership_history_route(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership_history")),
) -> list[OwnershipRecordResponse]:
    _get_asset_or_404(asset_id, db)
    records = get_ownership_history(db, asset_id)
    result: list[OwnershipRecordResponse] = []
    for record in records:
        if record.ownership_type in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}:
            if not user_has_permission(user, "inventory", "view_beneficial_ownership"):
                continue
        result.append(_enrich_record(db, record))
    return result


@ownership_router.get("/by-asset/{asset_id}/detail", response_model=AssetOwnershipDetailResponse)
def get_asset_ownership_detail(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> AssetOwnershipDetailResponse:
    _get_asset_or_404(asset_id, db)
    can_beneficial = user_has_permission(user, "inventory", "view_beneficial_ownership")
    active = get_active_ownership(db, asset_id)
    history = get_ownership_history(db, asset_id) if user_has_permission(user, "inventory", "view_ownership_history") else []

    def filter_records(records: list[InventoryOwnership], types: set[OwnershipType]) -> list[OwnershipRecordResponse]:
        out: list[OwnershipRecordResponse] = []
        for record in records:
            if record.ownership_type not in types:
                continue
            if record.ownership_type in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER} and not can_beneficial:
                continue
            out.append(_enrich_record(db, record))
        return out

    legal_types = LEGAL_OWNERSHIP_TYPES
    other_types = {
        OwnershipType.TRUSTEE,
        OwnershipType.NOMINEE,
        OwnershipType.MANAGER,
        OwnershipType.OTHER,
    }

    pending = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.inventory_asset_id == asset_id,
            OwnershipTransferRequest.status.in_(PENDING_TRANSFER_STATUSES),
            OwnershipTransferRequest.archived_at.is_(None),
        )
    ).all()
    scheduled = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.inventory_asset_id == asset_id,
            OwnershipTransferRequest.status.in_(SCHEDULED_TRANSFER_STATUSES),
            OwnershipTransferRequest.archived_at.is_(None),
        )
    ).all()

    legal_active = [r for r in active if r.ownership_type in legal_types]
    return AssetOwnershipDetailResponse(
        asset_id=asset_id,
        current_legal=filter_records(active, set(legal_types)),
        current_beneficial=filter_records(active, {OwnershipType.BENEFICIAL_OWNER}),
        current_economic=filter_records(active, {OwnershipType.ECONOMIC_OWNER}),
        current_other=filter_records(active, other_types),
        pending_requests=[_enrich_request(db, r, user) for r in pending],
        scheduled_transfers=[_enrich_request(db, r, user) for r in scheduled],
        history=[_enrich_record(db, r) for r in history if can_beneficial or r.ownership_type not in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}],
        legal_total=sum_active_legal_percentages(legal_active),
    )


@ownership_router.get("/by-party/{party_id}", response_model=list[OwnershipRecordResponse])
def get_ownership_by_party(
    party_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> list[OwnershipRecordResponse]:
    records = list(
        db.scalars(
            select(InventoryOwnership).where(
                InventoryOwnership.party_id == party_id,
                InventoryOwnership.status == OwnershipRecordStatus.ACTIVE,
                InventoryOwnership.archived_at.is_(None),
            )
        ).all()
    )
    return [_enrich_record(db, r) for r in records if user_has_permission(user, "inventory", "view_beneficial_ownership") or r.ownership_type not in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}]


@ownership_router.get("/{ownership_id}", response_model=OwnershipRecordResponse)
def get_ownership_detail(
    ownership_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> OwnershipRecordResponse:
    record = db.get(InventoryOwnership, ownership_id)
    if record is None or record.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ownership record not found")
    if record.ownership_type in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}:
        if not user_has_permission(user, "inventory", "view_beneficial_ownership"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="inventory.ownership.errors.beneficial_denied")
    return _enrich_record(db, record)


@ownership_router.get("/summary/by-asset/{asset_id}", response_model=OwnershipSummaryResponse)
def get_ownership_summary(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view")),
) -> OwnershipSummaryResponse:
    asset = _get_asset_or_404(asset_id, db)
    summary = enrich_ownership_summary(db, asset, user=user)
    return OwnershipSummaryResponse(**summary)


@transfers_router.get("", response_model=OwnershipTransferRequestListResponse)
def list_transfer_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
    project_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
    party_id: UUID | None = None,
    status_filter: TransferRequestStatus | None = Query(default=None, alias="status"),
    transfer_type: str | None = None,
    requester_id: UUID | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> OwnershipTransferRequestListResponse:
    query = select(OwnershipTransferRequest).join(
        InventoryAsset, InventoryAsset.id == OwnershipTransferRequest.inventory_asset_id
    )
    if not include_archived:
        query = query.where(OwnershipTransferRequest.archived_at.is_(None))
    if project_id:
        query = query.where(InventoryAsset.project_id == project_id)
    if inventory_asset_id:
        query = query.where(OwnershipTransferRequest.inventory_asset_id == inventory_asset_id)
    if status_filter:
        query = query.where(OwnershipTransferRequest.status == status_filter)
    if transfer_type:
        query = query.where(OwnershipTransferRequest.transfer_type == transfer_type)
    if requester_id:
        query = query.where(OwnershipTransferRequest.requested_by_user_id == requester_id)
    if effective_from:
        query = query.where(OwnershipTransferRequest.effective_date >= effective_from)
    if effective_to:
        query = query.where(OwnershipTransferRequest.effective_date <= effective_to)
    if party_id:
        query = query.join(
            OwnershipTransferParty,
            OwnershipTransferParty.ownership_transfer_request_id == OwnershipTransferRequest.id,
        ).where(OwnershipTransferParty.party_id == party_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_col = getattr(OwnershipTransferRequest, sort_by, OwnershipTransferRequest.created_at)
    order = desc(sort_col) if sort_order == "desc" else asc(sort_col)
    rows = db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return OwnershipTransferRequestListResponse(
        items=[_enrich_request(db, row, user) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, ceil(total / page_size)) if total else 1,
    )


@transfers_router.get("/pending-approvals", response_model=list[OwnershipTransferRequestResponse])
def list_pending_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_ownership_change")),
) -> list[OwnershipTransferRequestResponse]:
    rows = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.status.in_(PENDING_TRANSFER_STATUSES),
            OwnershipTransferRequest.archived_at.is_(None),
        ).order_by(OwnershipTransferRequest.created_at.asc())
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@transfers_router.get("/scheduled", response_model=list[OwnershipTransferRequestResponse])
def list_scheduled_transfers(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> list[OwnershipTransferRequestResponse]:
    rows = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.status.in_(SCHEDULED_TRANSFER_STATUSES),
            OwnershipTransferRequest.archived_at.is_(None),
        ).order_by(OwnershipTransferRequest.effective_date.asc())
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@transfers_router.get("/stale", response_model=list[OwnershipTransferRequestResponse])
def list_stale_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_ownership_change")),
) -> list[OwnershipTransferRequestResponse]:
    rows = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.status == TransferRequestStatus.STALE,
            OwnershipTransferRequest.archived_at.is_(None),
        )
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@transfers_router.get("/by-asset/{asset_id}", response_model=list[OwnershipTransferRequestResponse])
def list_transfers_by_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> list[OwnershipTransferRequestResponse]:
    _get_asset_or_404(asset_id, db)
    rows = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.inventory_asset_id == asset_id,
            OwnershipTransferRequest.archived_at.is_(None),
        ).order_by(OwnershipTransferRequest.created_at.desc())
    ).all()
    return [_enrich_request(db, row, user) for row in rows]


@transfers_router.get("/{request_id}", response_model=OwnershipTransferRequestResponse)
def get_transfer_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership")),
) -> OwnershipTransferRequestResponse:
    return _enrich_request(db, _get_request_or_404(request_id, db), user)


@transfers_router.get("/{request_id}/approvals", response_model=list[OwnershipApprovalRecordResponse])
def list_transfer_approvals(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "view_ownership_history")),
) -> list[OwnershipApprovalRecordResponse]:
    from investhome_api.models.inventory import OwnershipApprovalRecord

    _get_request_or_404(request_id, db)
    rows = db.scalars(
        select(OwnershipApprovalRecord).where(
            OwnershipApprovalRecord.ownership_transfer_request_id == request_id
        )
    ).all()
    return [OwnershipApprovalRecordResponse.model_validate(row) for row in rows]


@transfers_router.post("", response_model=OwnershipTransferRequestResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: OwnershipTransferRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_ownership_change")),
) -> OwnershipTransferRequestResponse:
    try:
        transfer = create_transfer_request(
            db,
            asset_id=payload.inventory_asset_id,
            transfer_type=payload.transfer_type,
            effective_date=payload.effective_date,
            reason=payload.reason,
            parties=_build_party_rows(payload.parties),
            actor=user,
            supporting_document_id=payload.supporting_document_id,
            related_transaction_id=payload.related_transaction_id,
            assigned_approver_user_id=payload.assigned_approver_user_id,
            submit=payload.submit,
        )
        db.commit()
        db.refresh(transfer)
    except OwnershipError as exc:
        db.rollback()
        raise _ownership_error(exc) from exc

    asset = db.get(InventoryAsset, transfer.inventory_asset_id)
    if payload.submit and asset:
        notify_transfer_submitted(db, transfer, display_id=asset.display_id, requester=user)
        notify_finance_reviewers_if_legal(db, transfer, display_id=asset.display_id)
        db.commit()

    _log_ownership_activity(
        request,
        db,
        user=user,
        entity_id=transfer.id,
        action=ActivityAction.CREATED,
        description_key=(
            "activity.inventory.ownership.submitted"
            if payload.submit
            else "activity.inventory.ownership.draft_created"
        ),
        metadata={"asset_id": str(transfer.inventory_asset_id), "transfer_type": transfer.transfer_type.value},
    )
    db.commit()
    return _enrich_request(db, transfer, user)


@transfers_router.patch("/{request_id}", response_model=OwnershipTransferRequestResponse)
def update_transfer(
    request_id: UUID,
    payload: OwnershipTransferRequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_ownership_change")),
) -> OwnershipTransferRequestResponse:
    transfer = _get_request_or_404(request_id, db)
    if transfer.status != TransferRequestStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.ownership.errors.request_not_editable")
    if transfer.requested_by_user_id != user.id and not user_has_permission(user, "inventory", "review_ownership_change"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="inventory.ownership.errors.permission_denied")

    if payload.effective_date is not None:
        transfer.effective_date = payload.effective_date
    if payload.reason is not None:
        transfer.reason = payload.reason
    if payload.supporting_document_id is not None:
        transfer.supporting_document_id = payload.supporting_document_id
    if payload.related_transaction_id is not None:
        transfer.related_transaction_id = payload.related_transaction_id
    if payload.assigned_approver_user_id is not None:
        transfer.assigned_approver_user_id = payload.assigned_approver_user_id
    if payload.parties is not None:
        existing = db.scalars(
            select(OwnershipTransferParty).where(
                OwnershipTransferParty.ownership_transfer_request_id == transfer.id
            )
        ).all()
        for row in existing:
            db.delete(row)
        for row in _build_party_rows(payload.parties):
            row.ownership_transfer_request_id = transfer.id
            db.add(row)
    import json

    transfer.source_ownership_snapshot = json.dumps(build_ownership_snapshot(db, transfer.inventory_asset_id))
    db.commit()
    db.refresh(transfer)
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/submit", response_model=OwnershipTransferRequestResponse)
def submit_transfer(
    request_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_ownership_change")),
) -> OwnershipTransferRequestResponse:
    transfer = _get_request_or_404(request_id, db)
    try:
        submit_transfer_request(db, transfer, actor=user)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        raise _ownership_error(exc) from exc

    asset = db.get(InventoryAsset, transfer.inventory_asset_id)
    if asset:
        notify_transfer_submitted(db, transfer, display_id=asset.display_id, requester=user)
        notify_finance_reviewers_if_legal(db, transfer, display_id=asset.display_id)
        db.commit()

    _log_ownership_activity(
        request,
        db,
        user=user,
        entity_id=transfer.id,
        action=ActivityAction.UPDATED,
        description_key="activity.inventory.ownership.submitted",
    )
    db.commit()
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/review", response_model=OwnershipTransferRequestResponse)
def review_transfer(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_ownership_change")),
) -> OwnershipTransferRequestResponse:
    transfer = _get_request_or_404(request_id, db)
    try:
        review_transfer_request(db, transfer, actor=user)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        if exc.error_key == "inventory.ownership.errors.stale_request":
            asset = db.get(InventoryAsset, transfer.inventory_asset_id)
            if asset:
                notify_stale_conflict(db, transfer, [user], display_id=asset.display_id)
                db.commit()
        raise _ownership_error(exc) from exc
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/approve", response_model=OwnershipTransferRequestResponse)
def approve_transfer(
    request_id: UUID,
    payload: OwnershipDecisionInput,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "approve_ownership_change")),
) -> OwnershipTransferRequestResponse:
    transfer = _get_request_or_404(request_id, db)
    try:
        transfer, _created = approve_transfer_request(db, transfer, actor=user, comments=payload.comments)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        if exc.error_key == "inventory.ownership.errors.stale_request":
            asset = db.get(InventoryAsset, transfer.inventory_asset_id)
            if asset:
                notify_stale_conflict(db, transfer, [user], display_id=asset.display_id)
                db.commit()
        raise _ownership_error(exc) from exc

    asset = db.get(InventoryAsset, transfer.inventory_asset_id)
    requester = db.get(User, transfer.requested_by_user_id)
    if asset and requester:
        scheduled = transfer.status == TransferRequestStatus.APPROVED
        notify_transfer_approved(db, transfer, requester, display_id=asset.display_id, scheduled=scheduled)
        db.commit()

    _log_ownership_activity(
        request,
        db,
        user=user,
        entity_id=transfer.id,
        action=ActivityAction.APPROVED,
        description_key="activity.inventory.ownership.approved",
        metadata={"asset_id": str(transfer.inventory_asset_id)},
    )
    db.commit()
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/reject", response_model=OwnershipTransferRequestResponse)
def reject_transfer(
    request_id: UUID,
    payload: OwnershipDecisionInput,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "reject_ownership_change")),
) -> OwnershipTransferRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.ownership.errors.decision_notes_required")
    transfer = _get_request_or_404(request_id, db)
    try:
        reject_transfer_request(db, transfer, actor=user, decision_notes=payload.decision_notes)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        raise _ownership_error(exc) from exc

    asset = db.get(InventoryAsset, transfer.inventory_asset_id)
    requester = db.get(User, transfer.requested_by_user_id)
    if asset and requester:
        notify_transfer_rejected(db, transfer, requester, display_id=asset.display_id)
        db.commit()

    _log_ownership_activity(
        request,
        db,
        user=user,
        entity_id=transfer.id,
        action=ActivityAction.REJECTED,
        description_key="activity.inventory.ownership.rejected",
    )
    db.commit()
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/request-revision", response_model=OwnershipTransferRequestResponse)
def revision_transfer(
    request_id: UUID,
    payload: OwnershipDecisionInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "review_ownership_change")),
) -> OwnershipTransferRequestResponse:
    if not payload.decision_notes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="inventory.ownership.errors.decision_notes_required")
    transfer = _get_request_or_404(request_id, db)
    try:
        request_transfer_revision(db, transfer, actor=user, decision_notes=payload.decision_notes)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        raise _ownership_error(exc) from exc

    asset = db.get(InventoryAsset, transfer.inventory_asset_id)
    requester = db.get(User, transfer.requested_by_user_id)
    if asset and requester:
        notify_transfer_revision(db, transfer, requester, display_id=asset.display_id)
        db.commit()
    return _enrich_request(db, transfer, user)


@transfers_router.post("/{request_id}/withdraw", response_model=OwnershipTransferRequestResponse)
def withdraw_transfer(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory", "request_ownership_change")),
) -> OwnershipTransferRequestResponse:
    transfer = _get_request_or_404(request_id, db)
    try:
        withdraw_transfer_request(db, transfer, actor=user)
        db.commit()
    except OwnershipError as exc:
        db.rollback()
        raise _ownership_error(exc) from exc
    return _enrich_request(db, transfer, user)
