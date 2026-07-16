"""Inventory ownership workflow — centralized immutable ownership and transfers."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.inventory import (
    LEGAL_OWNERSHIP_TYPES,
    AcquisitionMethod,
    InventoryAsset,
    InventoryOwnership,
    InventoryOwnershipEvent,
    OwnershipApprovalDecision,
    OwnershipApprovalRecord,
    OwnershipRecordStatus,
    OwnershipSource,
    OwnershipTransferParty,
    OwnershipTransferRequest,
    OwnershipType,
    PENDING_TRANSFER_STATUSES,
    SCHEDULED_TRANSFER_STATUSES,
    TransferPartyRole,
    TransferRequestStatus,
    TransferType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.ownership_config import (
    REQUIRE_DOCUMENT_FOR_LEGAL_CHANGES,
    SELF_APPROVE_PERMISSION,
    is_legal_ownership_type,
    transfer_affects_legal,
)
from investhome_api.services.permission_service import user_has_permission

FOURPLACES = Decimal("0.0001")
TWOPLACES = Decimal("0.01")


class OwnershipError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now(clock: datetime | None = None) -> datetime:
    return clock or datetime.now(UTC)


def _today(clock: datetime | None = None) -> date:
    return (_now(clock)).date()


def _quantize_pct(value: Decimal) -> Decimal:
    return value.quantize(FOURPLACES, rounding=ROUND_HALF_UP)


def _validate_percentage(value: Decimal) -> None:
    pct = _quantize_pct(value)
    if pct <= 0 or pct > Decimal("100"):
        raise OwnershipError("inventory.ownership.errors.invalid_percentage")


def _lock_asset(db: Session, asset_id: UUID) -> InventoryAsset:
    asset = db.scalar(
        select(InventoryAsset).where(InventoryAsset.id == asset_id).with_for_update()
    )
    if asset is None or asset.archived_at is not None:
        raise OwnershipError("inventory.ownership.errors.asset_not_found", status_code=404)
    return asset


def _validate_party(db: Session, party_id: UUID) -> Investor:
    party = db.get(Investor, party_id)
    if party is None or party.archived_at is not None:
        raise OwnershipError("inventory.ownership.errors.party_not_found", status_code=404)
    return party


def _append_event(
    db: Session,
    *,
    asset_id: UUID,
    event_type: str,
    actor: User | None,
    request_id: UUID | None = None,
    ownership_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> InventoryOwnershipEvent:
    event = InventoryOwnershipEvent(
        inventory_asset_id=asset_id,
        ownership_transfer_request_id=request_id,
        inventory_ownership_id=ownership_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.flush()
    return event


def get_active_ownership(
    db: Session,
    asset_id: UUID,
    *,
    ownership_types: frozenset[OwnershipType] | None = None,
) -> list[InventoryOwnership]:
    query = select(InventoryOwnership).where(
        InventoryOwnership.inventory_asset_id == asset_id,
        InventoryOwnership.status == OwnershipRecordStatus.ACTIVE,
        InventoryOwnership.archived_at.is_(None),
    )
    if ownership_types is not None:
        query = query.where(InventoryOwnership.ownership_type.in_(ownership_types))
    return list(db.scalars(query.order_by(InventoryOwnership.effective_from.desc())).all())


def get_ownership_history(db: Session, asset_id: UUID) -> list[InventoryOwnership]:
    return list(
        db.scalars(
            select(InventoryOwnership)
            .where(
                InventoryOwnership.inventory_asset_id == asset_id,
                InventoryOwnership.archived_at.is_(None),
            )
            .order_by(InventoryOwnership.effective_from.desc(), InventoryOwnership.created_at.desc())
        ).all()
    )


def build_ownership_snapshot(db: Session, asset_id: UUID) -> list[dict[str, str]]:
    records = get_active_ownership(db, asset_id)
    snapshot = [
        {
            "id": str(record.id),
            "party_id": str(record.party_id),
            "ownership_type": record.ownership_type.value,
            "percentage": str(record.ownership_percentage),
        }
        for record in records
    ]
    snapshot.sort(key=lambda row: (row["ownership_type"], row["party_id"]))
    return snapshot


def _snapshot_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row["party_id"], row["ownership_type"], row["percentage"])


def snapshots_match(stored_json: str, current: list[dict[str, str]]) -> bool:
    try:
        stored = json.loads(stored_json)
    except json.JSONDecodeError:
        return False
    if not isinstance(stored, list):
        return False
    stored_keys = sorted(_snapshot_key(row) for row in stored)
    current_keys = sorted(_snapshot_key(row) for row in current)
    return stored_keys == current_keys


def sum_legal_percentages(records: list[OwnershipTransferParty]) -> Decimal:
    total = Decimal("0")
    for record in records:
        if record.role == TransferPartyRole.OUTGOING_OWNER:
            continue
        if is_legal_ownership_type(record.ownership_type):
            total += record.proposed_percentage
    return _quantize_pct(total)


def sum_active_legal_percentages(records: list[InventoryOwnership]) -> Decimal:
    total = Decimal("0")
    for record in records:
        if record.ownership_type in LEGAL_OWNERSHIP_TYPES:
            total += record.ownership_percentage
    return _quantize_pct(total)


def validate_proposed_legal_total(
    parties: list[OwnershipTransferParty],
    *,
    allow_incomplete: bool = False,
    allow_disputed: bool = False,
) -> None:
    legal_parties = [p for p in parties if is_legal_ownership_type(p.ownership_type) and p.role != TransferPartyRole.OUTGOING_OWNER]
    if not legal_parties:
        return
    total = sum_legal_percentages(parties)
    if total == Decimal("100"):
        return
    if allow_disputed and total != Decimal("100"):
        return
    if allow_incomplete and total < Decimal("100"):
        return
    raise OwnershipError("inventory.ownership.errors.legal_total_invalid")


def _check_stale_request(db: Session, request: OwnershipTransferRequest) -> None:
    current = build_ownership_snapshot(db, request.inventory_asset_id)
    if not snapshots_match(request.source_ownership_snapshot, current):
        request.status = TransferRequestStatus.STALE
        request.updated_at = _now()
        raise OwnershipError("inventory.ownership.errors.stale_request", status_code=409)


def mark_competing_requests_stale(
    db: Session,
    asset_id: UUID,
    *,
    exclude_request_id: UUID | None = None,
) -> int:
    pending = db.scalars(
        select(OwnershipTransferRequest).where(
            OwnershipTransferRequest.inventory_asset_id == asset_id,
            OwnershipTransferRequest.status.in_(PENDING_TRANSFER_STATUSES | SCHEDULED_TRANSFER_STATUSES),
            OwnershipTransferRequest.archived_at.is_(None),
        )
    ).all()
    current = build_ownership_snapshot(db, asset_id)
    marked = 0
    for request in pending:
        if exclude_request_id and request.id == exclude_request_id:
            continue
        if not snapshots_match(request.source_ownership_snapshot, current):
            request.status = TransferRequestStatus.STALE
            request.updated_at = _now()
            _append_event(
                db,
                asset_id=asset_id,
                event_type="inventory.ownership.stale_conflict",
                actor=None,
                request_id=request.id,
            )
            marked += 1
    return marked


def _ensure_can_view_ownership(user: User, ownership_type: OwnershipType) -> None:
    if not user_has_permission(user, "inventory", "view_ownership"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)
    if ownership_type in {OwnershipType.BENEFICIAL_OWNER, OwnershipType.ECONOMIC_OWNER}:
        if not user_has_permission(user, "inventory", "view_beneficial_ownership"):
            raise OwnershipError("inventory.ownership.errors.beneficial_denied", status_code=403)


def _ensure_can_request(user: User) -> None:
    if not user_has_permission(user, "inventory", "request_ownership_change"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)


def _ensure_can_approve(user: User, requester_id: UUID) -> None:
    if not get_settings().auth_enabled:
        return
    if not user_has_permission(user, "inventory", "approve_ownership_change"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)
    if requester_id == user.id and not user_has_permission(user, "inventory", SELF_APPROVE_PERMISSION):
        raise OwnershipError("inventory.ownership.errors.self_approval_blocked", status_code=403)


def _ensure_document_for_legal(
    request: OwnershipTransferRequest,
    parties: list[OwnershipTransferParty],
) -> None:
    if not REQUIRE_DOCUMENT_FOR_LEGAL_CHANGES:
        return
    if request.transfer_type == TransferType.INITIAL_OWNERSHIP:
        return
    if not transfer_affects_legal(request.transfer_type):
        return
    has_legal_change = any(
        is_legal_ownership_type(p.ownership_type)
        and (p.role != TransferPartyRole.CONTINUING_OWNER or p.previous_percentage != p.proposed_percentage)
        for p in parties
    )
    if has_legal_change and request.supporting_document_id is None:
        raise OwnershipError("inventory.ownership.errors.document_required")


def _acquisition_method_for_transfer(transfer_type: TransferType) -> AcquisitionMethod:
    if transfer_type == TransferType.INITIAL_OWNERSHIP:
        return AcquisitionMethod.PURCHASE
    if transfer_type == TransferType.CORRECTION:
        return AcquisitionMethod.CORRECTION
    return AcquisitionMethod.TRANSFER


def _ownership_types_in_transfer(parties: list[OwnershipTransferParty]) -> set[OwnershipType]:
    return {party.ownership_type for party in parties}


def _close_active_records(
    db: Session,
    asset_id: UUID,
    effective_to: date,
    ownership_types: set[OwnershipType],
) -> list[InventoryOwnership]:
    closed: list[InventoryOwnership] = []
    active = get_active_ownership(db, asset_id, ownership_types=frozenset(ownership_types))
    for record in active:
        record.status = OwnershipRecordStatus.HISTORICAL
        record.effective_to = effective_to
        record.updated_at = _now()
        closed.append(record)
    return closed


def _apply_transfer_records(
    db: Session,
    request: OwnershipTransferRequest,
    parties: list[OwnershipTransferParty],
    *,
    actor: User | None,
) -> list[InventoryOwnership]:
    asset = _lock_asset(db, request.inventory_asset_id)
    affected_types = _ownership_types_in_transfer(parties)
    has_legal = any(is_legal_ownership_type(t) for t in affected_types)

    if request.transfer_type != TransferType.INITIAL_OWNERSHIP:
        _close_active_records(db, asset.id, request.effective_date, affected_types)

    created: list[InventoryOwnership] = []
    acquisition = _acquisition_method_for_transfer(request.transfer_type)
    source = OwnershipSource.CORRECTION if request.transfer_type == TransferType.CORRECTION else OwnershipSource.TRANSFER

    for party_row in parties:
        if party_row.role == TransferPartyRole.OUTGOING_OWNER:
            continue
        if party_row.proposed_percentage <= 0:
            continue
        _validate_party(db, party_row.party_id)
        _validate_percentage(party_row.proposed_percentage)

        record = InventoryOwnership(
            inventory_asset_id=asset.id,
            party_id=party_row.party_id,
            ownership_type=party_row.ownership_type,
            ownership_percentage=_quantize_pct(party_row.proposed_percentage),
            effective_from=request.effective_date,
            effective_to=None,
            status=OwnershipRecordStatus.ACTIVE,
            acquisition_method=acquisition,
            transfer_reason=request.reason,
            related_document_id=request.supporting_document_id,
            related_transaction_id=request.related_transaction_id,
            source=source,
            notes=party_row.notes,
            created_by_user_id=request.requested_by_user_id,
            approved_by_user_id=actor.id if actor else None,
            ownership_transfer_request_id=request.id,
            is_demo=asset.is_demo,
        )
        db.add(record)
        created.append(record)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise OwnershipError("inventory.ownership.errors.duplicate_active_owner", status_code=409) from exc

    if has_legal:
        legal_total = sum_active_legal_percentages(get_active_ownership(db, asset.id))
        if legal_total != Decimal("100"):
            raise OwnershipError("inventory.ownership.errors.legal_total_invalid")

    return created


def create_transfer_request(
    db: Session,
    *,
    asset_id: UUID,
    transfer_type: TransferType,
    effective_date: date,
    reason: str,
    parties: list[OwnershipTransferParty],
    actor: User,
    supporting_document_id: UUID | None = None,
    related_transaction_id: UUID | None = None,
    assigned_approver_user_id: UUID | None = None,
    submit: bool = False,
) -> OwnershipTransferRequest:
    _ensure_can_request(actor)
    asset = _lock_asset(db, asset_id)
    snapshot = build_ownership_snapshot(db, asset_id)

    if transfer_type == TransferType.INITIAL_OWNERSHIP and snapshot:
        raise OwnershipError("inventory.ownership.errors.initial_ownership_exists")

    for party_row in parties:
        _validate_party(db, party_row.party_id)
        _validate_percentage(party_row.proposed_percentage)

    validate_proposed_legal_total(parties)

    request = OwnershipTransferRequest(
        inventory_asset_id=asset_id,
        transfer_type=transfer_type,
        effective_date=effective_date,
        reason=reason,
        source_ownership_snapshot=json.dumps(snapshot),
        supporting_document_id=supporting_document_id,
        related_transaction_id=related_transaction_id,
        requested_by_user_id=actor.id,
        assigned_approver_user_id=assigned_approver_user_id,
        status=TransferRequestStatus.DRAFT,
        is_demo=asset.is_demo,
    )
    db.add(request)
    db.flush()

    for party_row in parties:
        party_row.ownership_transfer_request_id = request.id
        db.add(party_row)

    _ensure_document_for_legal(request, parties)

    event_type = (
        "inventory.ownership.change_requested"
        if submit
        else "inventory.ownership.initialized"
    )
    _append_event(db, asset_id=asset_id, event_type=event_type, actor=actor, request_id=request.id)

    if submit:
        submit_transfer_request(db, request, actor=actor)

    return request


def submit_transfer_request(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
) -> OwnershipTransferRequest:
    if request.status != TransferRequestStatus.DRAFT:
        raise OwnershipError("inventory.ownership.errors.request_not_submittable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_ownership_change"
    ):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)

    parties = list(
        db.scalars(
            select(OwnershipTransferParty).where(
                OwnershipTransferParty.ownership_transfer_request_id == request.id
            )
        ).all()
    )
    validate_proposed_legal_total(parties)
    _ensure_document_for_legal(request, parties)
    _check_stale_request(db, request)

    request.status = TransferRequestStatus.SUBMITTED
    request.updated_at = _now()
    _append_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.ownership.change_requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def review_transfer_request(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
) -> OwnershipTransferRequest:
    if request.status not in PENDING_TRANSFER_STATUSES:
        raise OwnershipError("inventory.ownership.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_ownership_change"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)

    _check_stale_request(db, request)
    request.status = TransferRequestStatus.UNDER_REVIEW
    request.reviewed_at = _now()
    request.updated_at = _now()
    return request


def approve_transfer_request(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
    comments: str | None = None,
    clock: datetime | None = None,
) -> tuple[OwnershipTransferRequest, list[InventoryOwnership]]:
    if request.status == TransferRequestStatus.STALE:
        raise OwnershipError("inventory.ownership.errors.stale_request", status_code=409)
    if request.status not in PENDING_TRANSFER_STATUSES:
        raise OwnershipError("inventory.ownership.errors.request_not_approvable")

    _ensure_can_approve(actor, request.requested_by_user_id)
    _check_stale_request(db, request)

    parties = list(
        db.scalars(
            select(OwnershipTransferParty).where(
                OwnershipTransferParty.ownership_transfer_request_id == request.id
            )
        ).all()
    )
    validate_proposed_legal_total(parties)
    _ensure_document_for_legal(request, parties)

    now = _now(clock)
    today = _today(clock)

    db.add(
        OwnershipApprovalRecord(
            ownership_transfer_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=OwnershipApprovalDecision.APPROVED,
            comments=comments,
        )
    )

    request.approved_at = now
    request.updated_at = now

    created: list[InventoryOwnership] = []

    if request.effective_date > today:
        request.status = TransferRequestStatus.APPROVED
        _append_event(
            db,
            asset_id=request.inventory_asset_id,
            event_type="inventory.ownership.transfer_scheduled",
            actor=actor,
            request_id=request.id,
            metadata={"effective_date": request.effective_date.isoformat()},
        )
    else:
        created = _apply_transfer_records(db, request, parties, actor=actor)
        request.status = TransferRequestStatus.APPLIED
        mark_competing_requests_stale(db, request.inventory_asset_id, exclude_request_id=request.id)
        event_name = (
            "inventory.ownership.corrected"
            if request.transfer_type == TransferType.CORRECTION
            else "inventory.ownership.transferred"
        )
        _append_event(
            db,
            asset_id=request.inventory_asset_id,
            event_type="inventory.ownership.approved",
            actor=actor,
            request_id=request.id,
        )
        _append_event(
            db,
            asset_id=request.inventory_asset_id,
            event_type=event_name,
            actor=actor,
            request_id=request.id,
            metadata={"records_created": len(created)},
        )

    return request, created


def apply_scheduled_transfer(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    clock: datetime | None = None,
) -> list[InventoryOwnership]:
    """Apply an approved future-dated transfer. Idempotent."""
    if request.status == TransferRequestStatus.APPLIED:
        return []
    if request.status != TransferRequestStatus.APPROVED:
        raise OwnershipError("inventory.ownership.errors.request_not_applicable")

    today = _today(clock)
    if request.effective_date > today:
        return []

    current = build_ownership_snapshot(db, request.inventory_asset_id)
    if not snapshots_match(request.source_ownership_snapshot, current):
        request.status = TransferRequestStatus.STALE
        request.updated_at = _now(clock)
        _append_event(
            db,
            asset_id=request.inventory_asset_id,
            event_type="inventory.ownership.stale_conflict",
            actor=None,
            request_id=request.id,
        )
        raise OwnershipError("inventory.ownership.errors.stale_request", status_code=409)

    parties = list(
        db.scalars(
            select(OwnershipTransferParty).where(
                OwnershipTransferParty.ownership_transfer_request_id == request.id
            )
        ).all()
    )

    created = _apply_transfer_records(db, request, parties, actor=None)
    request.status = TransferRequestStatus.APPLIED
    request.updated_at = _now(clock)
    mark_competing_requests_stale(db, request.inventory_asset_id, exclude_request_id=request.id)

    _append_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.ownership.transferred",
        actor=None,
        request_id=request.id,
        metadata={"scheduled": True, "records_created": len(created)},
    )
    return created


def reject_transfer_request(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
    decision_notes: str,
) -> OwnershipTransferRequest:
    if request.status not in PENDING_TRANSFER_STATUSES:
        raise OwnershipError("inventory.ownership.errors.request_not_rejectable")
    if not user_has_permission(actor, "inventory", "reject_ownership_change"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)
    if get_settings().auth_enabled and request.requested_by_user_id == actor.id:
        raise OwnershipError("inventory.ownership.errors.self_approval_blocked", status_code=403)

    now = _now()
    request.status = TransferRequestStatus.REJECTED
    request.rejected_at = now
    request.decision_notes = decision_notes
    request.updated_at = now

    db.add(
        OwnershipApprovalRecord(
            ownership_transfer_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=OwnershipApprovalDecision.REJECTED,
            comments=decision_notes,
        )
    )
    _append_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.ownership.rejected",
        actor=actor,
        request_id=request.id,
    )
    return request


def request_transfer_revision(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
    decision_notes: str,
) -> OwnershipTransferRequest:
    if request.status not in PENDING_TRANSFER_STATUSES:
        raise OwnershipError("inventory.ownership.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_ownership_change"):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)

    request.status = TransferRequestStatus.DRAFT
    request.decision_notes = decision_notes
    request.reviewed_at = _now()
    request.updated_at = _now()

    db.add(
        OwnershipApprovalRecord(
            ownership_transfer_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=OwnershipApprovalDecision.REVISION_REQUESTED,
            comments=decision_notes,
        )
    )
    _append_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.ownership.revision_requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def withdraw_transfer_request(
    db: Session,
    request: OwnershipTransferRequest,
    *,
    actor: User,
) -> OwnershipTransferRequest:
    if request.status not in {
        TransferRequestStatus.DRAFT,
        TransferRequestStatus.SUBMITTED,
        TransferRequestStatus.UNDER_REVIEW,
    }:
        raise OwnershipError("inventory.ownership.errors.request_not_withdrawable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_ownership_change"
    ):
        raise OwnershipError("inventory.ownership.errors.permission_denied", status_code=403)

    request.status = TransferRequestStatus.WITHDRAWN
    request.updated_at = _now()
    _append_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.ownership.withdrawn",
        actor=actor,
        request_id=request.id,
    )
    return request


def enrich_ownership_summary(
    db: Session,
    asset: InventoryAsset,
    *,
    user: User | None,
) -> dict[str, Any]:
    if user is None or not user_has_permission(user, "inventory", "view_ownership"):
        return {
            "primary_legal_owner": None,
            "owner_count": 0,
            "ownership_status": "unknown",
        }

    legal = get_active_ownership(
        db, asset.id, ownership_types=LEGAL_OWNERSHIP_TYPES
    )
    primary = None
    if legal:
        primary_record = max(legal, key=lambda r: r.ownership_percentage)
        party = db.get(Investor, primary_record.party_id)
        primary = party.full_name if party else None

    total = sum_active_legal_percentages(legal)
    if not legal:
        status = "none"
    elif total == Decimal("100"):
        status = "complete"
    elif any(r.status == OwnershipRecordStatus.DISPUTED for r in legal):
        status = "disputed"
    else:
        status = "incomplete"

    return {
        "primary_legal_owner": primary,
        "owner_count": len(legal),
        "ownership_status": status,
    }


def list_due_scheduled_transfers(db: Session, *, clock: datetime | None = None) -> list[OwnershipTransferRequest]:
    today = _today(clock)
    return list(
        db.scalars(
            select(OwnershipTransferRequest).where(
                OwnershipTransferRequest.status == TransferRequestStatus.APPROVED,
                OwnershipTransferRequest.effective_date <= today,
                OwnershipTransferRequest.archived_at.is_(None),
            )
        ).all()
    )
