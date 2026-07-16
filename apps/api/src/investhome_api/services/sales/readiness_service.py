"""Sales readiness case business logic."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.finance import FinanceTransaction
from investhome_api.models.inventory import InventoryAsset, InventoryReservation, ReservationRecordStatus
from investhome_api.models.lead import Lead
from investhome_api.models.sales import (
    OpportunityInventory,
    OpportunityPartyType,
    OpportunityStage,
    SalesOpportunity,
)
from investhome_api.models.sales_proposal import ProposalStatus, SalesProposal
from investhome_api.models.sales_readiness import (
    ACTIVE_READINESS_STATUSES,
    BLOCKING_REQUIREMENT_STATUSES,
    ReadinessCaseStatus,
    ReadinessRequirementStatus,
    SATISFIED_REQUIREMENT_STATUSES,
    SalesReadinessCase,
    SalesReadinessRequirement,
    SalesReadinessStatusHistory,
    TERMINAL_READINESS_STATUSES,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales import readiness_notifications as notify
from investhome_api.services.sales import readiness_sync_service as sync_svc
from investhome_api.services.sales import readiness_template_service as template_svc
from investhome_api.services.sales.opportunity_service import (
    OpportunityError,
    change_stage,
    get_opportunity_or_raise,
)


class ReadinessError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def _generate_case_code(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"RDY-{today}-"
    count = db.scalar(
        select(func.count()).select_from(SalesReadinessCase).where(
            SalesReadinessCase.case_code.like(f"{prefix}%")
        )
    )
    return f"{prefix}{(count or 0) + 1:04d}"


def _append_status_history(
    db: Session,
    case: SalesReadinessCase,
    *,
    previous: ReadinessCaseStatus | None,
    new_status: ReadinessCaseStatus,
    actor: User | None,
    reason: str | None = None,
) -> None:
    db.add(
        SalesReadinessStatusHistory(
            readiness_case_id=case.id,
            previous_status=previous.value if previous else None,
            new_status=new_status.value,
            reason=reason,
            changed_by_user_id=actor.id if actor else None,
            effective_at=_now(),
        )
    )


def _append_timeline_event(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    event_type: str,
    actor: User | None,
    notes: str | None = None,
    metadata: dict | None = None,
) -> None:
    from investhome_api.models.sales import OpportunityTimeline

    db.add(
        OpportunityTimeline(
            opportunity_id=opportunity.id,
            event_type=event_type,
            actor_user_id=actor.id if actor else None,
            notes=notes,
            metadata_json=metadata,
        )
    )


def get_case_or_raise(
    db: Session,
    case_id: UUID,
    *,
    include_archived: bool = False,
) -> SalesReadinessCase:
    case = db.get(SalesReadinessCase, case_id)
    if case is None or (case.archived_at is not None and not include_archived):
        raise ReadinessError("sales.readiness.errors.not_found", status_code=404)
    return case


def _validate_related_entities(db: Session, opportunity: SalesOpportunity) -> None:
    if opportunity.archived_at is not None:
        raise ReadinessError("sales.readiness.errors.opportunity_archived")
    if opportunity.party_id:
        if opportunity.party_type == OpportunityPartyType.LEAD:
            lead = db.get(Lead, opportunity.party_id)
            if lead is None or lead.archived_at is not None:
                raise ReadinessError("sales.readiness.errors.party_archived")


def _check_active_uniqueness(
    db: Session,
    opportunity_id: UUID,
    inventory_asset_id: UUID,
    *,
    exclude_id: UUID | None = None,
) -> None:
    query = select(SalesReadinessCase).where(
        SalesReadinessCase.opportunity_id == opportunity_id,
        SalesReadinessCase.inventory_asset_id == inventory_asset_id,
        SalesReadinessCase.status.in_(ACTIVE_READINESS_STATUSES),
        SalesReadinessCase.archived_at.is_(None),
    )
    if exclude_id:
        query = query.where(SalesReadinessCase.id != exclude_id)
    existing = db.scalar(query)
    if existing:
        raise ReadinessError("sales.readiness.errors.active_case_exists")


def compute_percentage(requirements: list[SalesReadinessRequirement]) -> int:
    mandatory = [r for r in requirements if r.is_mandatory]
    if not mandatory:
        return 100
    satisfied = sum(1 for r in mandatory if r.status in SATISFIED_REQUIREMENT_STATUSES)
    return int(round((satisfied / len(mandatory)) * 100))


def compute_blockers(requirements: list[SalesReadinessRequirement]) -> list[str]:
    blockers: list[str] = []
    for req in requirements:
        if req.is_mandatory and req.status in BLOCKING_REQUIREMENT_STATUSES:
            blockers.append(f"{req.title}: {req.status.value}")
        elif req.blocked_reason:
            blockers.append(f"{req.title}: {req.blocked_reason}")
    return blockers


def derive_case_status(
    case: SalesReadinessCase,
    requirements: list[SalesReadinessRequirement],
    *,
    percentage: int,
) -> ReadinessCaseStatus:
    if case.status in {ReadinessCaseStatus.HANDED_OFF, ReadinessCaseStatus.CANCELLED, ReadinessCaseStatus.ARCHIVED}:
        return case.status
    blockers = compute_blockers(requirements)
    if blockers:
        return ReadinessCaseStatus.BLOCKED
    if case.handoff_requested_at and not case.handoff_approved_at:
        return ReadinessCaseStatus.READY_FOR_CLOSING_HANDOFF
    if case.signature_status in {"requested", "partially_signed"}:
        return ReadinessCaseStatus.SIGNATURE_PENDING
    sig_done = any(
        r.requirement_type.value == "signature_completed" and r.status in SATISFIED_REQUIREMENT_STATUSES
        for r in requirements
    )
    if sig_done or case.signature_status == "fully_signed":
        return ReadinessCaseStatus.CONTRACT_SIGNED
    legal_done = any(
        r.requirement_type.value == "legal_review" and r.status in SATISFIED_REQUIREMENT_STATUSES
        for r in requirements
    )
    if legal_done and percentage >= 70:
        return ReadinessCaseStatus.CONTRACT_PREPARATION
    if percentage >= 60:
        return ReadinessCaseStatus.READY_FOR_CONTRACT
    if percentage > 0:
        return ReadinessCaseStatus.IN_PROGRESS
    return ReadinessCaseStatus.NOT_STARTED


def recalculate_case(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User | None = None,
    sync: bool = True,
) -> SalesReadinessCase:
    if sync:
        sync_svc.sync_case(db, case)
    requirements = list(
        db.scalars(
            select(SalesReadinessRequirement).where(
                SalesReadinessRequirement.readiness_case_id == case.id
            )
        ).all()
    )
    percentage = compute_percentage(requirements)
    blockers = compute_blockers(requirements)
    previous_status = case.status
    case.readiness_percentage = percentage
    case.blocker_summary = "; ".join(blockers[:5]) if blockers else None
    new_status = derive_case_status(case, requirements, percentage=percentage)
    if new_status != previous_status:
        _append_status_history(db, case, previous=previous_status, new_status=new_status, actor=actor)
        case.status = new_status
        if new_status == ReadinessCaseStatus.BLOCKED:
            notify.notify_blocked(db, case, reason=case.blocker_summary)
    case.updated_at = _now()
    db.flush()
    return case


def create_from_opportunity(
    db: Session,
    opportunity_id: UUID,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "create_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    opportunity = get_opportunity_or_raise(db, opportunity_id)
    _validate_related_entities(db, opportunity)

    inventory_asset_id = data.get("inventory_asset_id")
    if inventory_asset_id is None:
        primary = db.scalar(
            select(OpportunityInventory.inventory_asset_id).where(
                OpportunityInventory.opportunity_id == opportunity.id,
                OpportunityInventory.is_primary.is_(True),
            )
        )
        if primary:
            inventory_asset_id = primary
        else:
            inventory_asset_id = db.scalar(
                select(OpportunityInventory.inventory_asset_id)
                .where(OpportunityInventory.opportunity_id == opportunity.id)
                .limit(1)
            )
    if inventory_asset_id is None and opportunity.reservation_id:
        reservation = db.get(InventoryReservation, opportunity.reservation_id)
        if reservation:
            inventory_asset_id = reservation.inventory_asset_id
    if inventory_asset_id is None:
        raise ReadinessError("sales.readiness.errors.inventory_required")
    asset = db.get(InventoryAsset, inventory_asset_id)
    if asset is None or asset.archived_at is not None:
        raise ReadinessError("sales.readiness.errors.inventory_archived")

    _check_active_uniqueness(db, opportunity.id, inventory_asset_id)

    reservation_id = data.get("reservation_id") or opportunity.reservation_id
    proposal_id = data.get("proposal_id")
    if proposal_id is None:
        accepted = db.scalar(
            select(SalesProposal).where(
                SalesProposal.opportunity_id == opportunity.id,
                SalesProposal.status == ProposalStatus.ACCEPTED,
            )
        )
        if accepted:
            proposal_id = accepted.id

    case = SalesReadinessCase(
        case_code=_generate_case_code(db),
        opportunity_id=opportunity.id,
        lead_id=opportunity.lead_id,
        party_id=opportunity.party_id,
        inventory_asset_id=inventory_asset_id,
        reservation_id=reservation_id,
        proposal_id=proposal_id,
        status=ReadinessCaseStatus.NOT_STARTED,
        target_contract_date=data.get("target_contract_date"),
        target_closing_handoff_date=data.get("target_closing_handoff_date"),
        assigned_sales_user_id=data.get("assigned_sales_user_id") or opportunity.assigned_sales_user_id,
        assigned_manager_user_id=data.get("assigned_manager_user_id"),
        assigned_legal_user_id=data.get("assigned_legal_user_id"),
        assigned_finance_user_id=data.get("assigned_finance_user_id"),
        notes=data.get("notes"),
    )
    db.add(case)
    db.flush()

    template = template_svc.resolve_template(
        db,
        project_id=data.get("project_id"),
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type),
        party_type=opportunity.party_type.value,
    )
    template_svc.apply_template_to_case(db, case, template=template)
    recalculate_case(db, case, actor=actor, sync=True)

    log_entity_created(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.created",
        actor=actor,
        metadata={"case_code": case.case_code, "opportunity_id": str(opportunity.id)},
        request=request,
    )
    _append_timeline_event(
        db,
        opportunity,
        event_type="sales.readiness.created",
        actor=actor,
        metadata={"readiness_case_id": str(case.id), "case_code": case.case_code},
    )
    notify.notify_case_assigned(db, case)
    db.flush()
    return case


def update_assignments(
    db: Session,
    case: SalesReadinessCase,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    before = {
        "assigned_sales_user_id": str(case.assigned_sales_user_id) if case.assigned_sales_user_id else None,
        "assigned_legal_user_id": str(case.assigned_legal_user_id) if case.assigned_legal_user_id else None,
        "assigned_finance_user_id": str(case.assigned_finance_user_id) if case.assigned_finance_user_id else None,
    }
    for field in (
        "assigned_sales_user_id",
        "assigned_manager_user_id",
        "assigned_legal_user_id",
        "assigned_finance_user_id",
        "target_contract_date",
        "target_closing_handoff_date",
        "notes",
        "signature_status",
        "signed_document_id",
    ):
        if field in data:
            setattr(case, field, data[field])
    case.updated_at = _now()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.updated",
        actor=actor,
        before=before,
        after={k: str(data.get(k)) if data.get(k) else None for k in before},
        request=request,
    )
    recalculate_case(db, case, actor=actor)
    notify.notify_case_assigned(db, case)
    return case


def archive_case(db: Session, case: SalesReadinessCase, *, actor: User, request: Request | None = None) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    previous = case.status
    case.archived_at = _now()
    case.status = ReadinessCaseStatus.ARCHIVED
    _append_status_history(db, case, previous=previous, new_status=ReadinessCaseStatus.ARCHIVED, actor=actor)
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.archived",
        actor=actor,
        request=request,
    )
    return case


def restore_case(db: Session, case: SalesReadinessCase, *, actor: User, request: Request | None = None) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    case.archived_at = None
    case.status = ReadinessCaseStatus.IN_PROGRESS
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.restored",
        actor=actor,
        request=request,
    )
    return recalculate_case(db, case, actor=actor)


def cancel_case(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "update_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    previous = case.status
    case.status = ReadinessCaseStatus.CANCELLED
    case.notes = (case.notes or "") + (f"\nCancelled: {reason}" if reason else "")
    _append_status_history(db, case, previous=previous, new_status=ReadinessCaseStatus.CANCELLED, actor=actor, reason=reason)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.cancelled",
        actor=actor,
        before={"status": previous.value},
        after={"status": ReadinessCaseStatus.CANCELLED.value},
        request=request,
    )
    return case


def _transition_status(
    db: Session,
    case: SalesReadinessCase,
    new_status: ReadinessCaseStatus,
    *,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> SalesReadinessCase:
    previous = case.status
    case.status = new_status
    _append_status_history(db, case, previous=previous, new_status=new_status, actor=actor, reason=reason)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.status_changed",
        actor=actor,
        before={"status": previous.value},
        after={"status": new_status.value},
        request=request,
    )
    case.updated_at = _now()
    db.flush()
    return case


def mark_ready_for_contract(db: Session, case: SalesReadinessCase, *, actor: User, request: Request | None = None) -> SalesReadinessCase:
    recalculate_case(db, case, actor=actor)
    if case.readiness_percentage < 50:
        raise ReadinessError("sales.readiness.errors.insufficient_readiness")
    return _transition_status(db, case, ReadinessCaseStatus.READY_FOR_CONTRACT, actor=actor, request=request)


def mark_contract_preparation(db: Session, case: SalesReadinessCase, *, actor: User, request: Request | None = None) -> SalesReadinessCase:
    return _transition_status(db, case, ReadinessCaseStatus.CONTRACT_PREPARATION, actor=actor, request=request)


def mark_signature_pending(db: Session, case: SalesReadinessCase, *, actor: User, request: Request | None = None) -> SalesReadinessCase:
    case.signature_status = "requested"
    notify.notify_signature_pending(db, case)
    return _transition_status(db, case, ReadinessCaseStatus.SIGNATURE_PENDING, actor=actor, request=request)


def mark_contract_signed(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User,
    signed_document_id: UUID | None = None,
    request: Request | None = None,
) -> SalesReadinessCase:
    if signed_document_id is None and case.signed_document_id is None:
        raise ReadinessError("sales.readiness.errors.signed_document_required")
    if signed_document_id:
        case.signed_document_id = signed_document_id
    case.signature_status = "fully_signed"
    recalculate_case(db, case, actor=actor)
    case = _transition_status(db, case, ReadinessCaseStatus.CONTRACT_SIGNED, actor=actor, request=request)
    opportunity = db.get(SalesOpportunity, case.opportunity_id)
    if opportunity and opportunity.stage in {
        OpportunityStage.RESERVATION,
        OpportunityStage.DEPOSIT_PENDING,
        OpportunityStage.CONTRACT,
    }:
        try:
            change_stage(db, opportunity, new_stage=OpportunityStage.CONTRACT, actor=actor, request=request)
        except OpportunityError:
            pass
    _append_timeline_event(
        db,
        opportunity,
        event_type="sales.readiness.contract_signed",
        actor=actor,
        metadata={"readiness_case_id": str(case.id)},
    ) if opportunity else None
    return case


def _all_mandatory_satisfied(requirements: list[SalesReadinessRequirement]) -> bool:
    for req in requirements:
        if req.is_mandatory and req.status not in SATISFIED_REQUIREMENT_STATUSES:
            return False
    return True


def request_handoff(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User,
    notes: str | None = None,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "request_handoff"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    recalculate_case(db, case, actor=actor)
    requirements = list(
        db.scalars(
            select(SalesReadinessRequirement).where(
                SalesReadinessRequirement.readiness_case_id == case.id
            )
        ).all()
    )
    if not _all_mandatory_satisfied(requirements):
        raise ReadinessError("sales.readiness.errors.mandatory_incomplete")
    case.handoff_requested_at = _now()
    case.handoff_requested_by_user_id = actor.id
    case.handoff_return_reason = None
    if notes:
        case.notes = (case.notes or "") + f"\nHandoff request: {notes}"
    notify.notify_handoff_requested(db, case)
    _append_timeline_event(
        db,
        db.get(SalesOpportunity, case.opportunity_id),
        event_type="sales.readiness.handoff_requested",
        actor=actor,
        notes=notes,
        metadata={"readiness_case_id": str(case.id)},
    )
    return _transition_status(db, case, ReadinessCaseStatus.READY_FOR_CLOSING_HANDOFF, actor=actor, request=request)


def approve_handoff(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User,
    notes: str | None = None,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "approve_handoff"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    if case.handoff_requested_at is None:
        raise ReadinessError("sales.readiness.errors.handoff_not_requested")
    requirements = list(
        db.scalars(
            select(SalesReadinessRequirement).where(
                SalesReadinessRequirement.readiness_case_id == case.id
            )
        ).all()
    )
    if not _all_mandatory_satisfied(requirements):
        raise ReadinessError("sales.readiness.errors.mandatory_incomplete")
    case.handoff_approved_at = _now()
    case.handoff_approved_by_user_id = actor.id
    opportunity = db.get(SalesOpportunity, case.opportunity_id)
    if opportunity:
        try:
            change_stage(db, opportunity, new_stage=OpportunityStage.CLOSING_HANDOFF, actor=actor, request=request)
        except OpportunityError:
            pass
        _append_timeline_event(
            db,
            opportunity,
            event_type="sales.readiness.handoff_approved",
            actor=actor,
            notes=notes,
            metadata={"readiness_case_id": str(case.id)},
        )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_READINESS,
        entity_id=case.id,
        description_key="activity.sales.readiness.handoff_approved",
        actor=actor,
        before={"status": case.status.value},
        after={"status": ReadinessCaseStatus.HANDED_OFF.value},
        request=request,
    )
    return _transition_status(db, case, ReadinessCaseStatus.HANDED_OFF, actor=actor, request=request)


def return_handoff(
    db: Session,
    case: SalesReadinessCase,
    *,
    actor: User,
    reason: str,
    request: Request | None = None,
) -> SalesReadinessCase:
    if not user_has_permission(actor, "sales", "return_handoff"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    if not reason.strip():
        raise ReadinessError("sales.readiness.errors.return_reason_required")
    case.handoff_return_reason = reason
    case.handoff_requested_at = None
    case.handoff_approved_at = None
    notify.notify_handoff_returned(db, case, reason=reason)
    opportunity = db.get(SalesOpportunity, case.opportunity_id)
    if opportunity:
        _append_timeline_event(
            db,
            opportunity,
            event_type="sales.readiness.handoff_returned",
            actor=actor,
            notes=reason,
            metadata={"readiness_case_id": str(case.id)},
        )
    return _transition_status(db, case, ReadinessCaseStatus.BLOCKED, actor=actor, reason=reason, request=request)


def get_deposit_summary(db: Session, case: SalesReadinessCase, *, user: User) -> dict[str, Any]:
    if not user_has_permission(user, "sales", "view_deposit_status"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    reservation = db.get(InventoryReservation, case.reservation_id) if case.reservation_id else None
    if reservation is None:
        return {
            "reservation_id": None,
            "deposit_amount": None,
            "received_amount": None,
            "remaining_amount": None,
            "currency": None,
            "due_at": None,
            "is_overdue": False,
            "finance_transaction_id": None,
            "status": "no_reservation",
        }
    received = Decimal("0")
    txn_id = reservation.finance_transaction_id
    if txn_id:
        txn = db.get(FinanceTransaction, txn_id)
        if txn:
            received = txn.amount
    required = reservation.deposit_amount or Decimal("0")
    remaining = max(required - received, Decimal("0"))
    is_overdue = bool(
        reservation.deposit_due_at
        and reservation.deposit_due_at < _now()
        and reservation.status == ReservationRecordStatus.DEPOSIT_PENDING
    )
    return {
        "reservation_id": str(reservation.id),
        "deposit_amount": str(required),
        "received_amount": str(received),
        "remaining_amount": str(remaining),
        "currency": reservation.deposit_currency,
        "due_at": reservation.deposit_due_at.isoformat() if reservation.deposit_due_at else None,
        "is_overdue": is_overdue,
        "finance_transaction_id": str(txn_id) if txn_id else None,
        "status": reservation.status.value,
    }


def list_cases(
    db: Session,
    user: User,
    *,
    view: str | None = None,
    opportunity_id: UUID | None = None,
    project_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
    party_id: UUID | None = None,
    assigned_sales_user_id: UUID | None = None,
    assigned_legal_user_id: UUID | None = None,
    assigned_finance_user_id: UUID | None = None,
    status: ReadinessCaseStatus | None = None,
    search: str | None = None,
    include_archived: bool = False,
    offset: int = 0,
    limit: int = 50,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[SalesReadinessCase], int]:
    if not user_has_permission(user, "sales", "view_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    query = select(SalesReadinessCase)
    if not include_archived:
        query = query.where(SalesReadinessCase.archived_at.is_(None))
    if opportunity_id:
        query = query.where(SalesReadinessCase.opportunity_id == opportunity_id)
    if inventory_asset_id:
        query = query.where(SalesReadinessCase.inventory_asset_id == inventory_asset_id)
    if party_id:
        query = query.where(SalesReadinessCase.party_id == party_id)
    if assigned_sales_user_id:
        query = query.where(SalesReadinessCase.assigned_sales_user_id == assigned_sales_user_id)
    if assigned_legal_user_id:
        query = query.where(SalesReadinessCase.assigned_legal_user_id == assigned_legal_user_id)
    if assigned_finance_user_id:
        query = query.where(SalesReadinessCase.assigned_finance_user_id == assigned_finance_user_id)
    if status:
        query = query.where(SalesReadinessCase.status == status)
    if view == "blocked":
        query = query.where(SalesReadinessCase.status == ReadinessCaseStatus.BLOCKED)
    elif view == "in_progress":
        query = query.where(SalesReadinessCase.status == ReadinessCaseStatus.IN_PROGRESS)
    elif view == "deposit_pending":
        query = query.where(
            SalesReadinessCase.status.in_(
                [ReadinessCaseStatus.IN_PROGRESS, ReadinessCaseStatus.BLOCKED, ReadinessCaseStatus.READY_FOR_CONTRACT]
            )
        )
    elif view == "signature_pending":
        query = query.where(SalesReadinessCase.status == ReadinessCaseStatus.SIGNATURE_PENDING)
    elif view == "ready_for_handoff":
        query = query.where(SalesReadinessCase.status == ReadinessCaseStatus.READY_FOR_CLOSING_HANDOFF)
    elif view == "handed_off":
        query = query.where(SalesReadinessCase.status == ReadinessCaseStatus.HANDED_OFF)
    elif view == "archived":
        query = query.where(SalesReadinessCase.archived_at.is_not(None))
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(SalesReadinessCase.case_code.ilike(pattern), SalesReadinessCase.notes.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_col = getattr(SalesReadinessCase, sort_by, SalesReadinessCase.updated_at)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    items = list(db.scalars(query.offset(offset).limit(limit)).all())
    return items, total


def build_dashboard_kpis(db: Session, user: User) -> dict[str, int]:
    if not user_has_permission(user, "sales", "view_readiness"):
        raise ReadinessError("sales.readiness.errors.permission_denied", status_code=403)
    base = select(SalesReadinessCase).where(SalesReadinessCase.archived_at.is_(None))
    active = base.where(SalesReadinessCase.status.in_(ACTIVE_READINESS_STATUSES))
    return {
        "active_cases": db.scalar(select(func.count()).select_from(active.subquery())) or 0,
        "blocked": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.status == ReadinessCaseStatus.BLOCKED).subquery()
            )
        )
        or 0,
        "deposit_pending": db.scalar(
            select(func.count()).select_from(
                base.where(
                    SalesReadinessCase.status.in_(
                        [ReadinessCaseStatus.IN_PROGRESS, ReadinessCaseStatus.BLOCKED]
                    )
                ).subquery()
            )
        )
        or 0,
        "documents_missing": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.blocker_summary.ilike("%document%")).subquery()
            )
        )
        or 0,
        "contract_preparation": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.status == ReadinessCaseStatus.CONTRACT_PREPARATION).subquery()
            )
        )
        or 0,
        "signature_pending": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.status == ReadinessCaseStatus.SIGNATURE_PENDING).subquery()
            )
        )
        or 0,
        "ready_for_handoff": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.status == ReadinessCaseStatus.READY_FOR_CLOSING_HANDOFF).subquery()
            )
        )
        or 0,
        "handed_off_this_month": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.status == ReadinessCaseStatus.HANDED_OFF).subquery()
            )
        )
        or 0,
        "reservation_approved": db.scalar(
            select(func.count()).select_from(
                base.where(SalesReadinessCase.reservation_id.is_not(None)).subquery()
            )
        )
        or 0,
        "deposit_received": 0,
    }


def get_status_history(db: Session, case_id: UUID) -> list[SalesReadinessStatusHistory]:
    return list(
        db.scalars(
            select(SalesReadinessStatusHistory)
            .where(SalesReadinessStatusHistory.readiness_case_id == case_id)
            .order_by(SalesReadinessStatusHistory.effective_at.desc())
        ).all()
    )
