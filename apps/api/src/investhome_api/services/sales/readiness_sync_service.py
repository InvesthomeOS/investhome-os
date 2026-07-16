"""Idempotent synchronization from authoritative domain sources."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.document import Document, DocumentLink, DocumentStatus
from investhome_api.models.finance import FinanceTransaction
from investhome_api.models.inventory import (
    InventoryAsset,
    InventoryReservation,
    ReservationRecordStatus,
)
from investhome_api.models.sales_proposal import ProposalStatus, SalesProposal
from investhome_api.models.sales_readiness import (
    ReadinessRequirementStatus,
    ReadinessRequirementType,
    ReadinessSourceEntityType,
    SalesReadinessCase,
    SalesReadinessRequirement,
)
from investhome_api.services.sales.readiness_config import DOCUMENT_TYPE_TO_REQUIREMENT


def _now() -> datetime:
    return datetime.now(UTC)


def _get_requirement(
    db: Session,
    case_id: UUID,
    req_type: ReadinessRequirementType,
) -> SalesReadinessRequirement | None:
    return db.scalar(
        select(SalesReadinessRequirement).where(
            SalesReadinessRequirement.readiness_case_id == case_id,
            SalesReadinessRequirement.requirement_type == req_type,
        )
    )


def _update_if_changed(
    requirement: SalesReadinessRequirement,
    *,
    new_status: ReadinessRequirementStatus,
    source_event: str,
    source_entity_type: ReadinessSourceEntityType | None = None,
    source_entity_id: UUID | None = None,
    blocked_reason: str | None = None,
) -> bool:
    """Return True if status changed."""
    if requirement.status in {ReadinessRequirementStatus.WAIVED, ReadinessRequirementStatus.NOT_APPLICABLE}:
        return False
    changed = requirement.status != new_status
    requirement.status = new_status
    requirement.last_sync_event = source_event
    if source_entity_type:
        requirement.source_entity_type = source_entity_type
    if source_entity_id:
        requirement.source_entity_id = source_entity_id
    if blocked_reason is not None:
        requirement.blocked_reason = blocked_reason
    elif new_status == ReadinessRequirementStatus.VERIFIED:
        requirement.blocked_reason = None
        requirement.verified_at = _now()
    requirement.updated_at = _now()
    return changed


def sync_reservation(db: Session, case: SalesReadinessCase, *, event: str = "sync.reservation") -> None:
    req = _get_requirement(db, case.id, ReadinessRequirementType.RESERVATION_APPROVED)
    if req is None:
        return
    if case.reservation_id is None:
        _update_if_changed(req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)
        return
    reservation = db.get(InventoryReservation, case.reservation_id)
    if reservation is None:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.MISSING,
            source_event=event,
            blocked_reason="Reservation not found",
        )
        return
    if reservation.status == ReservationRecordStatus.EXPIRED:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.EXPIRED,
            source_event=f"{event}.expired",
            source_entity_type=ReadinessSourceEntityType.INVENTORY_RESERVATION,
            source_entity_id=reservation.id,
            blocked_reason="Reservation expired",
        )
        return
    if reservation.status in {
        ReservationRecordStatus.APPROVED,
        ReservationRecordStatus.DEPOSIT_PENDING,
        ReservationRecordStatus.DEPOSIT_RECEIVED,
        ReservationRecordStatus.CONVERTED,
    }:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.VERIFIED,
            source_event=f"{event}.approved",
            source_entity_type=ReadinessSourceEntityType.INVENTORY_RESERVATION,
            source_entity_id=reservation.id,
        )
    elif reservation.status in {ReservationRecordStatus.PENDING_APPROVAL, ReservationRecordStatus.SOFT_HOLD}:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.PENDING,
            source_event=f"{event}.pending",
            source_entity_type=ReadinessSourceEntityType.INVENTORY_RESERVATION,
            source_entity_id=reservation.id,
        )
    else:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.MISSING,
            source_event=f"{event}.inactive",
            source_entity_type=ReadinessSourceEntityType.INVENTORY_RESERVATION,
            source_entity_id=reservation.id,
        )


def sync_deposit(db: Session, case: SalesReadinessCase, *, event: str = "sync.deposit") -> None:
    due_req = _get_requirement(db, case.id, ReadinessRequirementType.DEPOSIT_DUE)
    recv_req = _get_requirement(db, case.id, ReadinessRequirementType.DEPOSIT_RECEIVED)
    if due_req is None and recv_req is None:
        return
    reservation = db.get(InventoryReservation, case.reservation_id) if case.reservation_id else None
    if reservation is None:
        if due_req:
            _update_if_changed(due_req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)
        if recv_req:
            _update_if_changed(recv_req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)
        return

    if due_req and reservation.deposit_due_at:
        due_req.due_at = reservation.deposit_due_at
        if reservation.deposit_due_at < _now():
            _update_if_changed(
                due_req,
                new_status=ReadinessRequirementStatus.PENDING,
                source_event=f"{event}.overdue",
                blocked_reason="Deposit overdue",
            )
        else:
            _update_if_changed(
                due_req,
                new_status=ReadinessRequirementStatus.VERIFIED,
                source_event=f"{event}.due_set",
            )

    if recv_req:
        if reservation.deposit_received_at:
            txn_id = reservation.finance_transaction_id
            _update_if_changed(
                recv_req,
                new_status=ReadinessRequirementStatus.VERIFIED,
                source_event=f"{event}.received",
                source_entity_type=ReadinessSourceEntityType.FINANCE_TRANSACTION if txn_id else None,
                source_entity_id=txn_id,
            )
        elif reservation.status == ReservationRecordStatus.DEPOSIT_PENDING:
            shortfall = False
            if reservation.deposit_amount and reservation.deposit_amount > 0:
                received = Decimal("0")
                if reservation.finance_transaction_id:
                    txn = db.get(FinanceTransaction, reservation.finance_transaction_id)
                    if txn:
                        received = txn.amount
                if received < reservation.deposit_amount:
                    shortfall = True
            _update_if_changed(
                recv_req,
                new_status=ReadinessRequirementStatus.PENDING,
                source_event=f"{event}.shortfall" if shortfall else f"{event}.pending",
                blocked_reason="Deposit shortfall" if shortfall else None,
            )
        else:
            _update_if_changed(recv_req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)


def sync_proposal(db: Session, case: SalesReadinessCase, *, event: str = "sync.proposal") -> None:
    req = _get_requirement(db, case.id, ReadinessRequirementType.PROPOSAL_ACCEPTED)
    if req is None:
        return
    proposal = db.get(SalesProposal, case.proposal_id) if case.proposal_id else None
    if proposal is None:
        _update_if_changed(req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)
        return
    if proposal.status == ProposalStatus.ACCEPTED:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.VERIFIED,
            source_event=f"{event}.accepted",
            source_entity_type=ReadinessSourceEntityType.SALES_PROPOSAL,
            source_entity_id=proposal.id,
        )
    elif proposal.status in {ProposalStatus.SENT, ProposalStatus.VIEWED, ProposalStatus.APPROVED}:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.PENDING,
            source_event=f"{event}.pending",
            source_entity_type=ReadinessSourceEntityType.SALES_PROPOSAL,
            source_entity_id=proposal.id,
        )
    else:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.MISSING,
            source_event=f"{event}.not_accepted",
            source_entity_type=ReadinessSourceEntityType.SALES_PROPOSAL,
            source_entity_id=proposal.id,
        )


def sync_documents(db: Session, case: SalesReadinessCase, *, event: str = "sync.documents") -> None:
    """Map linked documents to requirement types by document type."""
    if case.opportunity_id is None:
        return
    entity_keys = [("opportunity", case.opportunity_id)]
    if case.lead_id:
        entity_keys.append(("lead", case.lead_id))
    if case.party_id:
        entity_keys.append(("investor", case.party_id))

    doc_by_type: dict[ReadinessRequirementType, Document] = {}
    for entity_type, entity_id in entity_keys:
        links = db.scalars(
            select(DocumentLink).where(
                DocumentLink.entity_type == entity_type,
                DocumentLink.entity_id == entity_id,
            )
        ).all()
        for link in links:
            doc = db.get(Document, link.document_id)
            if doc is None or doc.archived_at is not None:
                continue
            if doc.status == DocumentStatus.ARCHIVED:
                continue
            req_type = DOCUMENT_TYPE_TO_REQUIREMENT.get(doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type))
            if req_type and req_type not in doc_by_type:
                doc_by_type[req_type] = doc

    for req_type, doc in doc_by_type.items():
        req = _get_requirement(db, case.id, req_type)
        if req is None:
            continue
        if req.status in {ReadinessRequirementStatus.WAIVED, ReadinessRequirementStatus.NOT_APPLICABLE}:
            continue
        if doc.status == DocumentStatus.ACTIVE:
            _update_if_changed(
                req,
                new_status=ReadinessRequirementStatus.VERIFIED,
                source_event=f"{event}.verified",
                source_entity_type=ReadinessSourceEntityType.DOCUMENT,
                source_entity_id=doc.id,
            )
        elif doc.status == DocumentStatus.DRAFT:
            _update_if_changed(
                req,
                new_status=ReadinessRequirementStatus.UNDER_REVIEW,
                source_event=f"{event}.under_review",
                source_entity_type=ReadinessSourceEntityType.DOCUMENT,
                source_entity_id=doc.id,
            )
        else:
            _update_if_changed(
                req,
                new_status=ReadinessRequirementStatus.RECEIVED,
                source_event=f"{event}.received",
                source_entity_type=ReadinessSourceEntityType.DOCUMENT,
                source_entity_id=doc.id,
            )


def sync_signature(db: Session, case: SalesReadinessCase, *, event: str = "sync.signature") -> None:
    sig_req = _get_requirement(db, case.id, ReadinessRequirementType.SIGNATURE_COMPLETED)
    if sig_req is None:
        return
    if case.signed_document_id:
        doc = db.get(Document, case.signed_document_id)
        if doc and doc.archived_at is None:
            _update_if_changed(
                sig_req,
                new_status=ReadinessRequirementStatus.VERIFIED,
                source_event=f"{event}.signed",
                source_entity_type=ReadinessSourceEntityType.DOCUMENT,
                source_entity_id=doc.id,
            )
            return
    if case.signature_status == "fully_signed" and case.signed_document_id:
        _update_if_changed(
            sig_req,
            new_status=ReadinessRequirementStatus.VERIFIED,
            source_event=f"{event}.manual_signed",
            source_entity_type=ReadinessSourceEntityType.DOCUMENT,
            source_entity_id=case.signed_document_id,
        )
    elif case.signature_status in {"requested", "partially_signed"}:
        _update_if_changed(sig_req, new_status=ReadinessRequirementStatus.PENDING, source_event=f"{event}.pending")
    else:
        pending_sig = _get_requirement(db, case.id, ReadinessRequirementType.SIGNATURE_REQUIRED)
        if pending_sig and pending_sig.status == ReadinessRequirementStatus.VERIFIED:
            _update_if_changed(sig_req, new_status=ReadinessRequirementStatus.PENDING, source_event=f"{event}.awaiting")


def sync_inventory_conflict(db: Session, case: SalesReadinessCase, *, event: str = "sync.inventory") -> None:
    if case.inventory_asset_id is None:
        return
    asset = db.get(InventoryAsset, case.inventory_asset_id)
    if asset is None or asset.archived_at is not None:
        case.blocker_summary = "Inventory asset archived or unavailable"
        return
    if case.reservation_id:
        active_other = db.scalar(
            select(InventoryReservation).where(
                InventoryReservation.inventory_asset_id == case.inventory_asset_id,
                InventoryReservation.id != case.reservation_id,
                InventoryReservation.status.in_(
                    [
                        ReservationRecordStatus.SOFT_HOLD,
                        ReservationRecordStatus.PENDING_APPROVAL,
                        ReservationRecordStatus.APPROVED,
                        ReservationRecordStatus.DEPOSIT_PENDING,
                    ]
                ),
            )
        )
        if active_other:
            case.blocker_summary = "Inventory reservation conflict detected"


def sync_closing_date(db: Session, case: SalesReadinessCase, *, event: str = "sync.handoff") -> None:
    req = _get_requirement(db, case.id, ReadinessRequirementType.CLOSING_DATE_CONFIRMED)
    if req is None:
        return
    if case.target_closing_handoff_date:
        _update_if_changed(
            req,
            new_status=ReadinessRequirementStatus.VERIFIED,
            source_event=f"{event}.date_set",
        )
    else:
        _update_if_changed(req, new_status=ReadinessRequirementStatus.MISSING, source_event=event)


def sync_case(db: Session, case: SalesReadinessCase, *, event: str = "sync.full") -> SalesReadinessCase:
    """Full idempotent sync — no circular updates to source systems."""
    sync_reservation(db, case, event=f"{event}.reservation")
    sync_deposit(db, case, event=f"{event}.deposit")
    sync_proposal(db, case, event=f"{event}.proposal")
    sync_documents(db, case, event=f"{event}.documents")
    sync_signature(db, case, event=f"{event}.signature")
    sync_inventory_conflict(db, case, event=f"{event}.inventory")
    sync_closing_date(db, case, event=f"{event}.handoff")
    case.updated_at = _now()
    db.flush()
    return case
