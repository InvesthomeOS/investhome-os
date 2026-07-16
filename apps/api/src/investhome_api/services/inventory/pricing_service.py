"""Inventory pricing workflow — centralized versioned pricing and approval."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.inventory import (
    PENDING_PRICE_REQUEST_STATUSES,
    InventoryAsset,
    InventoryAssetPrice,
    InventoryPriceEvent,
    PriceApprovalDecision,
    PriceApprovalRecord,
    PriceChangeRequest,
    PriceRequestStatus,
    PriceSource,
    PriceStatus,
    PriceType,
    SENSITIVE_PRICE_TYPES,
)
from investhome_api.models.user_auth import User
from investhome_api.services.inventory.pricing_config import (
    ApprovalRuleContext,
    requires_approval,
    requires_sensitive_approve,
)
from investhome_api.services.permission_service import user_has_permission

TWOPLACES = Decimal("0.01")
PCTPLACES = Decimal("0.01")


class PricingError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now(clock: datetime | None = None) -> datetime:
    return clock or datetime.now(UTC)


def compute_change(
    current: Decimal | None,
    proposed: Decimal,
) -> tuple[Decimal, Decimal | None]:
    base = current or Decimal("0")
    change_amount = (proposed - base).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if current is not None and current != 0:
        change_pct = ((change_amount / current) * 100).quantize(PCTPLACES, rounding=ROUND_HALF_UP)
    else:
        change_pct = None
    return change_amount, change_pct


def _lock_asset(db: Session, asset_id: UUID) -> InventoryAsset:
    asset = db.scalar(
        select(InventoryAsset).where(InventoryAsset.id == asset_id).with_for_update()
    )
    if asset is None or asset.archived_at is not None:
        raise PricingError("inventory.pricing.errors.asset_not_found", status_code=404)
    return asset


def get_active_price(
    db: Session,
    asset_id: UUID,
    price_type: PriceType,
    currency: str,
) -> InventoryAssetPrice | None:
    return db.scalar(
        select(InventoryAssetPrice).where(
            InventoryAssetPrice.inventory_asset_id == asset_id,
            InventoryAssetPrice.price_type == price_type,
            InventoryAssetPrice.currency == currency,
            InventoryAssetPrice.status == PriceStatus.ACTIVE,
            InventoryAssetPrice.archived_at.is_(None),
        )
    )


def _validate_effective_dates(effective_from: date, effective_to: date | None) -> None:
    if effective_to is not None and effective_to < effective_from:
        raise PricingError("inventory.pricing.errors.invalid_effective_dates")


def _append_price_event(
    db: Session,
    *,
    asset_id: UUID,
    event_type: str,
    actor: User | None,
    request_id: UUID | None = None,
    price_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> InventoryPriceEvent:
    event = InventoryPriceEvent(
        inventory_asset_id=asset_id,
        price_change_request_id=request_id,
        inventory_asset_price_id=price_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.flush()
    return event


def _refresh_asset_price_cache(asset: InventoryAsset, price: InventoryAssetPrice) -> None:
    if price.price_type == PriceType.LIST and price.status == PriceStatus.ACTIVE:
        asset.list_price = price.amount
    elif price.price_type == PriceType.PROMOTIONAL and price.status == PriceStatus.ACTIVE:
        asset.promotional_price = price.amount


def _supersede_active_price(
    db: Session,
    active: InventoryAssetPrice,
    *,
    effective_to: date,
) -> None:
    active.status = PriceStatus.SUPERSEDED
    active.effective_to = effective_to
    active.updated_at = _now()


def _role_codes(user: User) -> frozenset[str]:
    return frozenset(role.code for role in user.roles)


def _ensure_can_view_price(user: User, price_type: PriceType) -> None:
    if not user_has_permission(user, "inventory", "view_price"):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)
    if price_type in SENSITIVE_PRICE_TYPES and not user_has_permission(
        user, "inventory", "view_sensitive_price"
    ):
        raise PricingError("inventory.pricing.errors.sensitive_price_denied", status_code=403)


def _ensure_can_approve(user: User, price_type: PriceType, requester_id: UUID) -> None:
    if not user_has_permission(user, "inventory", "approve_price"):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)
    if requires_sensitive_approve(price_type) and not user_has_permission(
        user, "inventory", "view_sensitive_price"
    ):
        raise PricingError("inventory.pricing.errors.sensitive_approve_denied", status_code=403)
    if requester_id == user.id:
        if get_settings().auth_enabled and not user_has_permission(
            user, "inventory", "self_approve_price"
        ):
            raise PricingError("inventory.pricing.errors.self_approval_blocked", status_code=403)


def _check_stale_request(db: Session, request: PriceChangeRequest) -> None:
    current = get_active_price(
        db,
        request.inventory_asset_id,
        request.price_type,
        request.currency,
    )
    current_id = current.id if current else None
    if current_id != request.current_price_id:
        raise PricingError("inventory.pricing.errors.stale_request", status_code=409)


def create_initial_price(
    db: Session,
    *,
    asset_id: UUID,
    price_type: PriceType,
    amount: Decimal,
    currency: str,
    effective_from: date,
    effective_to: date | None,
    reason: str | None,
    actor: User,
    source: PriceSource = PriceSource.INITIAL,
) -> InventoryAssetPrice:
    asset = _lock_asset(db, asset_id)
    _validate_effective_dates(effective_from, effective_to)

    if currency != asset.currency:
        raise PricingError("inventory.pricing.errors.currency_mismatch")

    existing = get_active_price(db, asset.id, price_type, currency)
    if existing is not None:
        raise PricingError("inventory.pricing.errors.active_price_exists", status_code=409)

    price = InventoryAssetPrice(
        inventory_asset_id=asset.id,
        price_type=price_type,
        amount=amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP),
        currency=currency,
        effective_from=effective_from,
        effective_to=effective_to,
        status=PriceStatus.ACTIVE,
        reason=reason,
        source=source,
        created_by_user_id=actor.id,
        is_demo=asset.is_demo,
    )
    db.add(price)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise PricingError("inventory.pricing.errors.overlap_active_price", status_code=409) from exc

    _refresh_asset_price_cache(asset, price)
    _append_price_event(
        db,
        asset_id=asset.id,
        event_type="inventory.price.initialized",
        actor=actor,
        price_id=price.id,
        metadata={"price_type": price_type.value, "amount": str(amount), "currency": currency},
    )
    return price


def archive_draft_price(
    db: Session,
    price: InventoryAssetPrice,
    *,
    actor: User,
) -> InventoryAssetPrice:
    if price.status not in {PriceStatus.DRAFT, PriceStatus.REJECTED}:
        raise PricingError("inventory.pricing.errors.cannot_archive_price")
    price.status = PriceStatus.ARCHIVED
    price.archived_at = _now()
    price.updated_at = _now()
    _append_price_event(
        db,
        asset_id=price.inventory_asset_id,
        event_type="inventory.price.archived",
        actor=actor,
        price_id=price.id,
    )
    return price


def create_price_request(
    db: Session,
    *,
    asset_id: UUID,
    price_type: PriceType,
    proposed_amount: Decimal,
    currency: str,
    effective_from: date,
    effective_to: date | None,
    reason: str,
    supporting_document_id: UUID | None,
    assigned_approver_user_id: UUID | None,
    actor: User,
    submit: bool = False,
) -> PriceChangeRequest:
    asset = _lock_asset(db, asset_id)
    _validate_effective_dates(effective_from, effective_to)

    if currency != asset.currency:
        raise PricingError("inventory.pricing.errors.currency_mismatch")

    active = get_active_price(db, asset.id, price_type, currency)
    current_amount = active.amount if active else None
    change_amount, change_pct = compute_change(current_amount, proposed_amount)

    ctx = ApprovalRuleContext(
        price_type=price_type,
        project_id=asset.project_id,
        current_amount=current_amount,
        proposed_amount=proposed_amount,
        change_percentage=change_pct,
        requester_role_codes=_role_codes(actor),
    )
    if requires_approval(ctx) and not submit:
        status = PriceRequestStatus.DRAFT
    elif requires_approval(ctx):
        status = PriceRequestStatus.SUBMITTED
    else:
        status = PriceRequestStatus.DRAFT

    request = PriceChangeRequest(
        inventory_asset_id=asset.id,
        price_type=price_type,
        current_price_id=active.id if active else None,
        current_amount=current_amount,
        proposed_amount=proposed_amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP),
        currency=currency,
        change_amount=change_amount,
        change_percentage=change_pct,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=reason,
        supporting_document_id=supporting_document_id,
        requested_by_user_id=actor.id,
        assigned_approver_user_id=assigned_approver_user_id,
        status=status,
        is_demo=asset.is_demo,
    )
    db.add(request)
    db.flush()

    event_key = (
        "inventory.price.change_requested"
        if status != PriceRequestStatus.DRAFT
        else "inventory.price.draft_created"
    )
    _append_price_event(
        db,
        asset_id=asset.id,
        event_type=event_key,
        actor=actor,
        request_id=request.id,
        metadata={
            "price_type": price_type.value,
            "proposed_amount": str(proposed_amount),
            "change_percentage": str(change_pct) if change_pct is not None else None,
        },
    )
    return request


def update_draft_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
    proposed_amount: Decimal | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    reason: str | None = None,
    supporting_document_id: UUID | None = None,
    assigned_approver_user_id: UUID | None = None,
    clear_assigned_approver: bool = False,
) -> PriceChangeRequest:
    if request.status != PriceRequestStatus.DRAFT:
        raise PricingError("inventory.pricing.errors.request_not_editable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_price_change"
    ):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)

    asset = _lock_asset(db, request.inventory_asset_id)
    active = get_active_price(db, asset.id, request.price_type, request.currency)
    request.current_price_id = active.id if active else None
    request.current_amount = active.amount if active else None

    if proposed_amount is not None:
        request.proposed_amount = proposed_amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if effective_from is not None:
        request.effective_from = effective_from
    if effective_to is not None:
        request.effective_to = effective_to
    if reason is not None:
        request.reason = reason
    if supporting_document_id is not None:
        request.supporting_document_id = supporting_document_id
    if clear_assigned_approver:
        request.assigned_approver_user_id = None
    elif assigned_approver_user_id is not None:
        request.assigned_approver_user_id = assigned_approver_user_id

    _validate_effective_dates(request.effective_from, request.effective_to)
    change_amount, change_pct = compute_change(request.current_amount, request.proposed_amount)
    request.change_amount = change_amount
    request.change_percentage = change_pct
    request.updated_at = _now()
    return request


def submit_price_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
) -> PriceChangeRequest:
    if request.status != PriceRequestStatus.DRAFT:
        raise PricingError("inventory.pricing.errors.request_not_submittable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "request_price_change"
    ):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)

    _lock_asset(db, request.inventory_asset_id)
    _check_stale_request(db, request)

    request.status = PriceRequestStatus.SUBMITTED
    request.updated_at = _now()
    _append_price_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.price.change_requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def review_price_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
) -> PriceChangeRequest:
    if request.status not in {PriceRequestStatus.SUBMITTED, PriceRequestStatus.UNDER_REVIEW}:
        raise PricingError("inventory.pricing.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_price_change"):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)

    _check_stale_request(db, request)
    request.status = PriceRequestStatus.UNDER_REVIEW
    request.reviewed_at = _now()
    request.updated_at = _now()
    return request


def _apply_approved_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
    comments: str | None,
) -> InventoryAssetPrice:
    asset = _lock_asset(db, request.inventory_asset_id)
    _check_stale_request(db, request)

    active = get_active_price(db, asset.id, request.price_type, request.currency)
    if active is not None:
        _supersede_active_price(db, active, effective_to=request.effective_from)

    new_price = InventoryAssetPrice(
        inventory_asset_id=asset.id,
        price_type=request.price_type,
        amount=request.proposed_amount,
        currency=request.currency,
        effective_from=request.effective_from,
        effective_to=request.effective_to,
        status=PriceStatus.ACTIVE,
        reason=request.reason,
        source=PriceSource.MANUAL_REQUEST,
        approved_request_id=request.id,
        created_by_user_id=actor.id,
        is_demo=asset.is_demo,
    )
    db.add(new_price)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise PricingError("inventory.pricing.errors.overlap_active_price", status_code=409) from exc

    _refresh_asset_price_cache(asset, new_price)

    now = _now()
    request.status = PriceRequestStatus.APPLIED
    request.approved_at = now
    request.updated_at = now

    record = PriceApprovalRecord(
        price_change_request_id=request.id,
        reviewer_user_id=actor.id,
        decision=PriceApprovalDecision.APPROVED,
        comments=comments,
    )
    db.add(record)
    db.flush()

    _append_price_event(
        db,
        asset_id=asset.id,
        event_type="inventory.price.approved",
        actor=actor,
        request_id=request.id,
        price_id=new_price.id,
    )
    _append_price_event(
        db,
        asset_id=asset.id,
        event_type="inventory.price.activated",
        actor=actor,
        request_id=request.id,
        price_id=new_price.id,
        metadata={"amount": str(new_price.amount), "price_type": request.price_type.value},
    )
    return new_price


def approve_price_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
    comments: str | None = None,
) -> tuple[PriceChangeRequest, InventoryAssetPrice]:
    if request.status not in PENDING_PRICE_REQUEST_STATUSES:
        raise PricingError("inventory.pricing.errors.request_not_approvable")

    _ensure_can_approve(actor, request.price_type, request.requested_by_user_id)
    new_price = _apply_approved_request(db, request, actor=actor, comments=comments)
    return request, new_price


def reject_price_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
    decision_notes: str,
) -> PriceChangeRequest:
    if request.status not in PENDING_PRICE_REQUEST_STATUSES:
        raise PricingError("inventory.pricing.errors.request_not_rejectable")
    if not user_has_permission(actor, "inventory", "reject_price"):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)
    if request.requested_by_user_id == actor.id and get_settings().auth_enabled:
        raise PricingError("inventory.pricing.errors.self_approval_blocked", status_code=403)

    now = _now()
    request.status = PriceRequestStatus.REJECTED
    request.rejected_at = now
    request.decision_notes = decision_notes
    request.updated_at = now

    db.add(
        PriceApprovalRecord(
            price_change_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=PriceApprovalDecision.REJECTED,
            comments=decision_notes,
        )
    )
    _append_price_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.price.rejected",
        actor=actor,
        request_id=request.id,
        metadata={"reason": decision_notes},
    )
    return request


def request_price_revision(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
    decision_notes: str,
) -> PriceChangeRequest:
    if request.status not in PENDING_PRICE_REQUEST_STATUSES:
        raise PricingError("inventory.pricing.errors.request_not_reviewable")
    if not user_has_permission(actor, "inventory", "review_price_change"):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)

    request.status = PriceRequestStatus.DRAFT
    request.decision_notes = decision_notes
    request.reviewed_at = _now()
    request.updated_at = _now()

    db.add(
        PriceApprovalRecord(
            price_change_request_id=request.id,
            reviewer_user_id=actor.id,
            decision=PriceApprovalDecision.REVISION_REQUESTED,
            comments=decision_notes,
        )
    )
    _append_price_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.price.revision_requested",
        actor=actor,
        request_id=request.id,
    )
    return request


def withdraw_price_request(
    db: Session,
    request: PriceChangeRequest,
    *,
    actor: User,
) -> PriceChangeRequest:
    if request.status not in {PriceRequestStatus.DRAFT, PriceRequestStatus.SUBMITTED, PriceRequestStatus.UNDER_REVIEW}:
        raise PricingError("inventory.pricing.errors.request_not_withdrawable")
    if request.requested_by_user_id != actor.id and not user_has_permission(
        actor, "inventory", "review_price_change"
    ):
        raise PricingError("inventory.pricing.errors.permission_denied", status_code=403)

    request.status = PriceRequestStatus.WITHDRAWN
    request.updated_at = _now()
    _append_price_event(
        db,
        asset_id=request.inventory_asset_id,
        event_type="inventory.price.withdrawn",
        actor=actor,
        request_id=request.id,
    )
    return request


def list_prices_for_asset(db: Session, asset_id: UUID) -> list[InventoryAssetPrice]:
    return list(
        db.scalars(
            select(InventoryAssetPrice)
            .where(
                InventoryAssetPrice.inventory_asset_id == asset_id,
                InventoryAssetPrice.archived_at.is_(None),
            )
            .order_by(InventoryAssetPrice.effective_from.desc(), InventoryAssetPrice.created_at.desc())
        ).all()
    )


def list_current_prices(db: Session, asset_id: UUID) -> list[InventoryAssetPrice]:
    return list(
        db.scalars(
            select(InventoryAssetPrice).where(
                InventoryAssetPrice.inventory_asset_id == asset_id,
                InventoryAssetPrice.status == PriceStatus.ACTIVE,
                InventoryAssetPrice.archived_at.is_(None),
            )
        ).all()
    )


def list_price_history(db: Session, asset_id: UUID) -> list[InventoryAssetPrice]:
    return list(
        db.scalars(
            select(InventoryAssetPrice)
            .where(
                InventoryAssetPrice.inventory_asset_id == asset_id,
                InventoryAssetPrice.status.in_(
                    [
                        PriceStatus.ACTIVE,
                        PriceStatus.SUPERSEDED,
                        PriceStatus.EXPIRED,
                    ]
                ),
            )
            .order_by(InventoryAssetPrice.effective_from.desc(), InventoryAssetPrice.created_at.desc())
        ).all()
    )


def list_approval_records(db: Session, request_id: UUID) -> list[PriceApprovalRecord]:
    return list(
        db.scalars(
            select(PriceApprovalRecord)
            .where(PriceApprovalRecord.price_change_request_id == request_id)
            .order_by(PriceApprovalRecord.created_at.desc())
        ).all()
    )


def count_pending_requests_for_asset(db: Session, asset_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(PriceChangeRequest)
            .where(
                PriceChangeRequest.inventory_asset_id == asset_id,
                PriceChangeRequest.status.in_(PENDING_PRICE_REQUEST_STATUSES),
                PriceChangeRequest.archived_at.is_(None),
            )
        )
        or 0
    )


def enrich_asset_pricing_summary(
    db: Session,
    asset: InventoryAsset,
    *,
    user: User,
) -> dict[str, Any]:
    can_view = user_has_permission(user, "inventory", "view_price")
    can_sensitive = user_has_permission(user, "inventory", "view_sensitive_price")
    if not can_view:
        return {
            "list_price": None,
            "promotional_price": None,
            "contracted_price": None,
            "currency": asset.currency,
            "pending_price_requests": 0,
        }

    list_price = asset.list_price
    promo_price = asset.promotional_price
    contracted_price = None

    if can_sensitive:
        contracted = get_active_price(db, asset.id, PriceType.CONTRACTED, asset.currency)
        contracted_price = contracted.amount if contracted else None

    pending = count_pending_requests_for_asset(db, asset.id)

    return {
        "list_price": str(list_price) if list_price is not None else None,
        "promotional_price": str(promo_price) if promo_price is not None else None,
        "contracted_price": str(contracted_price) if contracted_price is not None else None,
        "currency": asset.currency,
        "pending_price_requests": pending,
    }


def mask_amount_for_user(user: User, price_type: PriceType, amount: Decimal | None) -> str | None:
    if amount is None:
        return None
    if price_type in SENSITIVE_PRICE_TYPES and not user_has_permission(
        user, "inventory", "view_sensitive_price"
    ):
        return None
    if not user_has_permission(user, "inventory", "view_price"):
        return None
    return str(amount)
