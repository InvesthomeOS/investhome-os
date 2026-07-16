"""Sales proposal business logic and workflow enforcement."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.inventory import (
    InventoryAsset,
    InventoryAssetPrice,
    PriceStatus,
    PriceType,
    ReservationStatus,
)
from investhome_api.models.sales import OpportunityStage, SalesOpportunity
from investhome_api.models.sales_inventory_matching import SalesShortlist, SalesShortlistItem
from investhome_api.models.sales_proposal import (
    EDITABLE_PROPOSAL_STATUSES,
    ProposalActivityType,
    ProposalApprovalDecision,
    ProposalRecipientType,
    ProposalStatus,
    SalesProposal,
    SalesProposalActivity,
    SalesProposalApproval,
    SalesProposalItem,
    SalesProposalRecipient,
    SalesProposalVersion,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales import opportunity_service as opp_svc
from investhome_api.services.sales import proposal_notifications as notify
from investhome_api.services.sales.proposal_number_service import generate_proposal_number

PROPOSAL_ACTIVITY_FIELDS = (
    "title",
    "status",
    "currency",
    "valid_until",
    "primary_project_id",
    "assigned_sales_user_id",
    "notes",
)


class ProposalError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def _append_activity(
    db: Session,
    proposal: SalesProposal,
    activity_type: ProposalActivityType,
    *,
    actor: User | None = None,
    metadata: dict[str, Any] | None = None,
) -> SalesProposalActivity:
    entry = SalesProposalActivity(
        proposal_id=proposal.id,
        activity_type=activity_type,
        actor_user_id=actor.id if actor else None,
        metadata_json=metadata,
    )
    db.add(entry)
    db.flush()
    return entry


def get_proposal_or_raise(
    db: Session,
    proposal_id: UUID,
    *,
    include_archived: bool = False,
) -> SalesProposal:
    proposal = db.get(SalesProposal, proposal_id)
    if proposal is None or (proposal.archived_at is not None and not include_archived):
        raise ProposalError("sales.proposal.errors.not_found", status_code=404)
    return proposal


def _get_version_or_raise(db: Session, version_id: UUID) -> SalesProposalVersion:
    version = db.get(SalesProposalVersion, version_id)
    if version is None:
        raise ProposalError("sales.proposal.errors.version_not_found", status_code=404)
    return version


def _get_opportunity_or_raise(db: Session, opportunity_id: UUID) -> SalesOpportunity:
    return opp_svc.get_opportunity_or_raise(db, opportunity_id)


def _ensure_editable(proposal: SalesProposal) -> None:
    if proposal.status not in EDITABLE_PROPOSAL_STATUSES:
        raise ProposalError("sales.proposal.errors.not_editable")


def _ensure_version_mutable(version: SalesProposalVersion) -> None:
    if version.is_approved:
        raise ProposalError("sales.proposal.errors.version_immutable")


def _get_current_version(db: Session, proposal: SalesProposal) -> SalesProposalVersion | None:
    if proposal.current_version_id:
        return db.get(SalesProposalVersion, proposal.current_version_id)
    return db.scalar(
        select(SalesProposalVersion)
        .where(SalesProposalVersion.proposal_id == proposal.id)
        .order_by(SalesProposalVersion.version_number.desc())
        .limit(1)
    )


def _resolve_active_price(
    db: Session,
    asset_id: UUID,
    currency: str,
    *,
    approved_price_id: UUID | None = None,
) -> InventoryAssetPrice:
    if approved_price_id:
        price = db.get(InventoryAssetPrice, approved_price_id)
        if (
            price is None
            or price.inventory_asset_id != asset_id
            or price.status != PriceStatus.ACTIVE
            or price.archived_at is not None
        ):
            raise ProposalError("sales.proposal.errors.invalid_approved_price")
        return price

    price = db.scalar(
        select(InventoryAssetPrice).where(
            InventoryAssetPrice.inventory_asset_id == asset_id,
            InventoryAssetPrice.price_type == PriceType.LIST,
            InventoryAssetPrice.currency == currency,
            InventoryAssetPrice.status == PriceStatus.ACTIVE,
            InventoryAssetPrice.archived_at.is_(None),
        )
    )
    if price is None:
        raise ProposalError("sales.proposal.errors.no_approved_price")
    return price


def _validate_item_currency(proposal: SalesProposal, currency: str) -> None:
    if currency != proposal.currency:
        raise ProposalError("sales.proposal.errors.currency_mismatch")


def _sync_opportunity_on_sent(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    opportunity = db.get(SalesOpportunity, proposal.opportunity_id)
    if opportunity is None or opportunity.archived_at is not None:
        return
    if opportunity.stage in {
        OpportunityStage.PROPOSAL_PREPARATION,
        OpportunityStage.INVENTORY_MATCHING,
        OpportunityStage.MEETING_COMPLETED,
        OpportunityStage.NEGOTIATION,
        OpportunityStage.QUALIFIED,
        OpportunityStage.MEETING_SCHEDULED,
        OpportunityStage.NEW,
    }:
        try:
            opp_svc.change_stage(
                db,
                opportunity,
                new_stage=OpportunityStage.PROPOSAL_SENT,
                actor=actor,
                request=request,
                notes=f"Auto-sync from proposal {proposal.proposal_number}",
            )
        except opp_svc.OpportunityError:
            pass


def create_proposal(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    opportunity = _get_opportunity_or_raise(db, data["opportunity_id"])
    currency = data.get("currency") or opportunity.currency or "USD"

    proposal_number = generate_proposal_number(
        db,
        project_id=data.get("primary_project_id"),
    )

    proposal = SalesProposal(
        opportunity_id=opportunity.id,
        lead_id=data.get("lead_id") or opportunity.lead_id,
        party_id=data.get("party_id") or opportunity.party_id,
        title=data["title"],
        proposal_number=proposal_number,
        status=ProposalStatus.DRAFT,
        currency=currency,
        valid_until=data.get("valid_until"),
        primary_project_id=data.get("primary_project_id"),
        created_by_user_id=actor.id,
        assigned_sales_user_id=data.get("assigned_sales_user_id") or opportunity.assigned_sales_user_id,
        notes=data.get("notes"),
    )
    db.add(proposal)
    db.flush()

    version = SalesProposalVersion(
        proposal_id=proposal.id,
        version_number=1,
        content_snapshot=data.get("content_snapshot") or {},
        pricing_snapshot={},
        terms_snapshot=data.get("terms_snapshot") or {},
        branding_snapshot=data.get("branding_snapshot"),
        created_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    proposal.current_version_id = version.id

    if data.get("recipient_email"):
        db.add(
            SalesProposalRecipient(
                proposal_id=proposal.id,
                party_id=proposal.party_id,
                recipient_type=ProposalRecipientType.PRIMARY,
                is_primary=True,
                email_snapshot=data["recipient_email"],
                language=data.get("language", "en"),
            )
        )

    _append_activity(db, proposal, ProposalActivityType.CREATED, actor=actor)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.created",
        actor=actor,
        metadata={"proposal_number": proposal.proposal_number},
        request=request,
    )
    return proposal


def update_proposal(
    db: Session,
    proposal: SalesProposal,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    _ensure_editable(proposal)
    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)

    for field in ("title", "valid_until", "primary_project_id", "assigned_sales_user_id", "notes"):
        if field in data and data[field] is not None:
            setattr(proposal, field, data[field])

    if "content_snapshot" in data or "terms_snapshot" in data or "branding_snapshot" in data:
        version = _get_current_version(db, proposal)
        if version:
            _ensure_version_mutable(version)
            if "content_snapshot" in data:
                version.content_snapshot = data["content_snapshot"]
            if "terms_snapshot" in data:
                version.terms_snapshot = data["terms_snapshot"]
            if "branding_snapshot" in data:
                version.branding_snapshot = data["branding_snapshot"]

    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.UPDATED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.updated",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    return proposal


def list_proposals(
    db: Session,
    *,
    status: ProposalStatus | None = None,
    opportunity_id: UUID | None = None,
    party_id: UUID | None = None,
    primary_project_id: UUID | None = None,
    assigned_sales_user_id: UUID | None = None,
    valid_until_before: date | None = None,
    valid_until_after: date | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    include_archived: bool = False,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SalesProposal], int]:
    query = select(SalesProposal)
    if not include_archived:
        query = query.where(SalesProposal.archived_at.is_(None))
    if status:
        query = query.where(SalesProposal.status == status)
    if opportunity_id:
        query = query.where(SalesProposal.opportunity_id == opportunity_id)
    if party_id:
        query = query.where(SalesProposal.party_id == party_id)
    if primary_project_id:
        query = query.where(SalesProposal.primary_project_id == primary_project_id)
    if assigned_sales_user_id:
        query = query.where(SalesProposal.assigned_sales_user_id == assigned_sales_user_id)
    if valid_until_before:
        query = query.where(SalesProposal.valid_until <= valid_until_before)
    if valid_until_after:
        query = query.where(SalesProposal.valid_until >= valid_until_after)
    if created_after:
        query = query.where(SalesProposal.created_at >= created_after)
    if created_before:
        query = query.where(SalesProposal.created_at <= created_before)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                SalesProposal.title.ilike(pattern),
                SalesProposal.proposal_number.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(SalesProposal.updated_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return items, total


def archive_proposal(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    proposal.archived_at = _now()
    proposal.status = ProposalStatus.ARCHIVED
    db.flush()
    _append_activity(db, proposal, ProposalActivityType.ARCHIVED, actor=actor)
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.archived",
        actor=actor,
        request=request,
    )
    return proposal


def restore_proposal(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    proposal.archived_at = None
    if proposal.status == ProposalStatus.ARCHIVED:
        proposal.status = ProposalStatus.DRAFT
    db.flush()
    _append_activity(db, proposal, ProposalActivityType.RESTORED, actor=actor)
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.restored",
        actor=actor,
        request=request,
    )
    return proposal


def submit_proposal(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status not in {ProposalStatus.DRAFT, ProposalStatus.REVISION_REQUESTED}:
        raise ProposalError("sales.proposal.errors.invalid_submit_status")

    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")

    items = db.scalars(
        select(SalesProposalItem).where(SalesProposalItem.proposal_version_id == version.id)
    ).all()
    if not items:
        raise ProposalError("sales.proposal.errors.no_items")

    stale = check_stale(db, proposal)
    if stale.get("has_stale"):
        raise ProposalError("sales.proposal.errors.stale_on_submit")

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.INTERNAL_REVIEW
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.SUBMITTED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.submitted",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    notify.notify_review_required(db, proposal)
    return proposal


def review_proposal(
    db: Session,
    proposal: SalesProposal,
    *,
    decision: ProposalApprovalDecision,
    comments: str | None,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status != ProposalStatus.INTERNAL_REVIEW:
        raise ProposalError("sales.proposal.errors.not_in_review")

    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")

    db.add(
        SalesProposalApproval(
            proposal_id=proposal.id,
            proposal_version_id=version.id,
            reviewer_user_id=actor.id,
            decision=decision,
            comments=comments,
        )
    )

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)

    if decision == ProposalApprovalDecision.APPROVED:
        version.is_approved = True
        version.approved_at = _now()
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_by_user_id = actor.id
        proposal.approved_at = _now()
        activity = ProposalActivityType.APPROVED
        desc = "activity.sales.proposal.approved"
        notify.notify_approved(db, proposal)
        notify.notify_ready_to_send(db, proposal)
    elif decision == ProposalApprovalDecision.REJECTED:
        proposal.status = ProposalStatus.REJECTED
        proposal.rejected_at = _now()
        activity = ProposalActivityType.REJECTED
        desc = "activity.sales.proposal.rejected"
        notify.notify_rejected(db, proposal)
    else:
        proposal.status = ProposalStatus.REVISION_REQUESTED
        activity = ProposalActivityType.REVISION_REQUESTED
        desc = "activity.sales.proposal.revision_requested"
        notify.notify_revision_requested(db, proposal)

    proposal.updated_at = _now()
    db.flush()
    _append_activity(db, proposal, activity, actor=actor, metadata={"comments": comments})
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key=desc,
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        metadata={"comments": comments},
        request=request,
    )
    return proposal


def mark_sent(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status != ProposalStatus.APPROVED:
        raise ProposalError("sales.proposal.errors.send_requires_approved")

    version = _get_current_version(db, proposal)
    if version is None or not version.is_approved:
        raise ProposalError("sales.proposal.errors.send_requires_approved_version")

    stale = check_stale(db, proposal)
    if stale.get("has_stale"):
        raise ProposalError("sales.proposal.errors.stale_on_send")

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.SENT
    proposal.sent_at = _now()
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.SENT, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.sent",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    _sync_opportunity_on_sent(db, proposal, actor=actor, request=request)
    return proposal


def mark_viewed(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status not in {ProposalStatus.SENT, ProposalStatus.VIEWED}:
        raise ProposalError("sales.proposal.errors.invalid_viewed_status")

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.VIEWED
    proposal.viewed_at = _now()
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.VIEWED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.viewed",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    notify.notify_viewed(db, proposal)
    return proposal


def mark_accepted(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status == ProposalStatus.EXPIRED:
        raise ProposalError("sales.proposal.errors.expired_requires_renewal")
    if proposal.status not in {ProposalStatus.SENT, ProposalStatus.VIEWED, ProposalStatus.APPROVED}:
        raise ProposalError("sales.proposal.errors.invalid_accept_status")

    if proposal.valid_until and proposal.valid_until < date.today():
        proposal.status = ProposalStatus.EXPIRED
        proposal.expired_at = _now()
        db.flush()
        raise ProposalError("sales.proposal.errors.expired")

    stale = check_stale(db, proposal)
    if stale.get("has_stale"):
        raise ProposalError("sales.proposal.errors.stale_on_accept")

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.ACCEPTED
    proposal.accepted_at = _now()
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.ACCEPTED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.accepted",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    notify.notify_accepted(db, proposal)
    return proposal


def mark_rejected(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposal:
    if proposal.status not in {ProposalStatus.SENT, ProposalStatus.VIEWED}:
        raise ProposalError("sales.proposal.errors.invalid_reject_status")

    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.REJECTED
    proposal.rejected_at = _now()
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.DECLINED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.declined",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    return proposal


def mark_expired(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User | None = None,
    request: Request | None = None,
) -> SalesProposal:
    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.EXPIRED
    proposal.expired_at = _now()
    proposal.updated_at = _now()
    db.flush()

    _append_activity(db, proposal, ProposalActivityType.EXPIRED, actor=actor)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.expired",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    notify.notify_expired(db, proposal)
    return proposal


def create_version_from_current(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposalVersion:
    if proposal.status not in {
        ProposalStatus.APPROVED,
        ProposalStatus.SENT,
        ProposalStatus.VIEWED,
        ProposalStatus.REVISION_REQUESTED,
    }:
        raise ProposalError("sales.proposal.errors.cannot_create_version")

    current = _get_current_version(db, proposal)
    if current is None:
        raise ProposalError("sales.proposal.errors.no_version")

    max_version = db.scalar(
        select(func.max(SalesProposalVersion.version_number)).where(
            SalesProposalVersion.proposal_id == proposal.id
        )
    ) or 0

    new_version = SalesProposalVersion(
        proposal_id=proposal.id,
        version_number=max_version + 1,
        source_shortlist_id=current.source_shortlist_id,
        content_snapshot=dict(current.content_snapshot or {}),
        pricing_snapshot=dict(current.pricing_snapshot or {}),
        terms_snapshot=dict(current.terms_snapshot or {}),
        branding_snapshot=dict(current.branding_snapshot or {}) if current.branding_snapshot else None,
        created_by_user_id=actor.id,
    )
    db.add(new_version)
    db.flush()

    for item in db.scalars(
        select(SalesProposalItem).where(SalesProposalItem.proposal_version_id == current.id)
    ).all():
        db.add(
            SalesProposalItem(
                proposal_version_id=new_version.id,
                inventory_asset_id=item.inventory_asset_id,
                sort_order=item.sort_order,
                item_title=item.item_title,
                approved_price_id=item.approved_price_id,
                displayed_amount=item.displayed_amount,
                currency=item.currency,
                promotional_terms=item.promotional_terms,
                payment_terms=item.payment_terms,
                estimated_rent=item.estimated_rent,
                selected_documents=item.selected_documents,
                selected_media=item.selected_media,
                notes=item.notes,
            )
        )

    proposal.current_version_id = new_version.id
    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    proposal.status = ProposalStatus.DRAFT
    proposal.approved_by_user_id = None
    proposal.approved_at = None
    proposal.sent_at = None
    proposal.viewed_at = None
    proposal.updated_at = _now()
    db.flush()

    _append_activity(
        db,
        proposal,
        ProposalActivityType.VERSION_CREATED,
        actor=actor,
        metadata={"version_number": new_version.version_number},
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.version_created",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        metadata={"version_number": new_version.version_number},
        request=request,
    )
    return new_version


def import_from_shortlist(
    db: Session,
    proposal: SalesProposal,
    shortlist_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposalVersion:
    _ensure_editable(proposal)
    shortlist = db.get(SalesShortlist, shortlist_id)
    if shortlist is None or shortlist.archived_at is not None:
        raise ProposalError("sales.proposal.errors.shortlist_not_found", status_code=404)

    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")
    _ensure_version_mutable(version)

    version.source_shortlist_id = shortlist_id
    db.execute(
        SalesProposalItem.__table__.delete().where(
            SalesProposalItem.proposal_version_id == version.id
        )
    )

    items = db.scalars(
        select(SalesShortlistItem)
        .where(SalesShortlistItem.shortlist_id == shortlist_id)
        .order_by(SalesShortlistItem.sort_order)
    ).all()

    for idx, sl_item in enumerate(items):
        asset = db.get(InventoryAsset, sl_item.inventory_asset_id)
        if asset is None or asset.archived_at is not None:
            continue
        price = _resolve_active_price(db, asset.id, proposal.currency)
        title = asset.display_id
        if sl_item.inventory_snapshot and sl_item.inventory_snapshot.get("display_id"):
            title = sl_item.inventory_snapshot["display_id"]

        db.add(
            SalesProposalItem(
                proposal_version_id=version.id,
                inventory_asset_id=asset.id,
                sort_order=idx,
                item_title=title,
                approved_price_id=price.id,
                displayed_amount=price.amount,
                currency=price.currency,
                notes=sl_item.notes,
            )
        )

    db.flush()
    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.imported_shortlist",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        metadata={"shortlist_id": str(shortlist_id)},
        request=request,
    )
    return version


def add_item(
    db: Session,
    proposal: SalesProposal,
    data: dict[str, Any],
    *,
    actor: User,
) -> SalesProposalItem:
    _ensure_editable(proposal)
    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")
    _ensure_version_mutable(version)

    asset_id = data["inventory_asset_id"]
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise ProposalError("sales.proposal.errors.asset_not_found", status_code=404)

    price = _resolve_active_price(
        db,
        asset_id,
        proposal.currency,
        approved_price_id=data.get("approved_price_id"),
    )
    _validate_item_currency(proposal, price.currency)

    max_order = db.scalar(
        select(func.max(SalesProposalItem.sort_order)).where(
            SalesProposalItem.proposal_version_id == version.id
        )
    ) or -1

    item = SalesProposalItem(
        proposal_version_id=version.id,
        inventory_asset_id=asset_id,
        sort_order=data.get("sort_order", max_order + 1),
        item_title=data.get("item_title") or asset.display_id,
        approved_price_id=price.id,
        displayed_amount=data["displayed_amount"] if data.get("displayed_amount") is not None else price.amount,
        currency=price.currency,
        promotional_terms=data.get("promotional_terms"),
        payment_terms=data.get("payment_terms"),
        estimated_rent=data.get("estimated_rent"),
        selected_documents=data.get("selected_documents"),
        selected_media=data.get("selected_media"),
        notes=data.get("notes"),
    )
    db.add(item)
    db.flush()
    return item


def remove_item(db: Session, proposal: SalesProposal, item_id: UUID, *, actor: User) -> None:
    _ensure_editable(proposal)
    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")
    _ensure_version_mutable(version)

    item = db.get(SalesProposalItem, item_id)
    if item is None or item.proposal_version_id != version.id:
        raise ProposalError("sales.proposal.errors.item_not_found", status_code=404)
    db.delete(item)
    db.flush()


def reorder_items(
    db: Session,
    proposal: SalesProposal,
    item_orders: list[dict[str, Any]],
    *,
    actor: User,
) -> list[SalesProposalItem]:
    _ensure_editable(proposal)
    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")
    _ensure_version_mutable(version)

    for entry in item_orders:
        item = db.get(SalesProposalItem, entry["item_id"])
        if item and item.proposal_version_id == version.id:
            item.sort_order = entry["sort_order"]
    db.flush()
    return list(
        db.scalars(
            select(SalesProposalItem)
            .where(SalesProposalItem.proposal_version_id == version.id)
            .order_by(SalesProposalItem.sort_order)
        ).all()
    )


def update_item(
    db: Session,
    proposal: SalesProposal,
    item_id: UUID,
    data: dict[str, Any],
    *,
    actor: User,
) -> SalesProposalItem:
    _ensure_editable(proposal)
    version = _get_current_version(db, proposal)
    if version is None:
        raise ProposalError("sales.proposal.errors.no_version")
    _ensure_version_mutable(version)

    item = db.get(SalesProposalItem, item_id)
    if item is None or item.proposal_version_id != version.id:
        raise ProposalError("sales.proposal.errors.item_not_found", status_code=404)

    if "approved_price_id" in data and data["approved_price_id"]:
        price = _resolve_active_price(
            db,
            item.inventory_asset_id,
            proposal.currency,
            approved_price_id=data["approved_price_id"],
        )
        item.approved_price_id = price.id
        item.displayed_amount = price.amount
        item.currency = price.currency

    for field in (
        "item_title",
        "displayed_amount",
        "promotional_terms",
        "payment_terms",
        "estimated_rent",
        "selected_documents",
        "selected_media",
        "notes",
        "sort_order",
    ):
        if field in data and data[field] is not None:
            setattr(item, field, data[field])

    _validate_item_currency(proposal, item.currency)
    db.flush()
    return item


def refresh_stale_pricing(
    db: Session,
    proposal: SalesProposal,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesProposalVersion:
    new_version = create_version_from_current(db, proposal, actor=actor, request=request)
    version = new_version

    for item in db.scalars(
        select(SalesProposalItem).where(SalesProposalItem.proposal_version_id == version.id)
    ).all():
        price = _resolve_active_price(db, item.inventory_asset_id, proposal.currency)
        item.approved_price_id = price.id
        item.displayed_amount = price.amount
        item.currency = price.currency

    db.flush()
    _append_activity(db, proposal, ProposalActivityType.PRICING_REFRESHED, actor=actor)
    before = snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_PROPOSAL,
        entity_id=proposal.id,
        description_key="activity.sales.proposal.pricing_refreshed",
        actor=actor,
        before=before,
        after=snapshot_entity(proposal, PROPOSAL_ACTIVITY_FIELDS),
        request=request,
    )
    return version


def check_stale(db: Session, proposal: SalesProposal) -> dict[str, Any]:
    version = _get_current_version(db, proposal)
    if version is None:
        return {"has_stale": False, "items": []}

    stale_items: list[dict[str, Any]] = []
    for item in db.scalars(
        select(SalesProposalItem).where(SalesProposalItem.proposal_version_id == version.id)
    ).all():
        price = db.get(InventoryAssetPrice, item.approved_price_id)
        asset = db.get(InventoryAsset, item.inventory_asset_id)
        is_stale = False
        stale_fields: list[str] = []

        if price is None or price.status != PriceStatus.ACTIVE or price.archived_at is not None:
            is_stale = True
            stale_fields.append("price_inactive")
        elif price.amount != item.displayed_amount:
            is_stale = True
            stale_fields.append("price_changed")

        if asset is None or asset.archived_at is not None:
            is_stale = True
            stale_fields.append("asset_archived")
        elif asset.reservation_status not in {ReservationStatus.NONE, None}:
            is_stale = True
            stale_fields.append("availability_changed")

        if is_stale:
            stale_items.append(
                {
                    "item_id": str(item.id),
                    "asset_id": str(item.inventory_asset_id),
                    "stale_fields": stale_fields,
                }
            )

    has_stale = len(stale_items) > 0
    if has_stale:
        _append_activity(
            db,
            proposal,
            ProposalActivityType.STALE_DETECTED,
            metadata={"stale_count": len(stale_items)},
        )
    return {"has_stale": has_stale, "items": stale_items}


def add_recipient(
    db: Session,
    proposal: SalesProposal,
    data: dict[str, Any],
    *,
    actor: User,
) -> SalesProposalRecipient:
    recipient = SalesProposalRecipient(
        proposal_id=proposal.id,
        party_id=data.get("party_id") or proposal.party_id,
        recipient_type=data.get("recipient_type", ProposalRecipientType.CC),
        is_primary=False,
        email_snapshot=data.get("email_snapshot"),
        language=data.get("language", "en"),
    )
    db.add(recipient)
    db.flush()
    return recipient


def remove_recipient(db: Session, proposal: SalesProposal, recipient_id: UUID) -> None:
    recipient = db.get(SalesProposalRecipient, recipient_id)
    if recipient is None or recipient.proposal_id != proposal.id:
        raise ProposalError("sales.proposal.errors.recipient_not_found", status_code=404)
    if recipient.is_primary:
        raise ProposalError("sales.proposal.errors.cannot_remove_primary")
    db.delete(recipient)
    db.flush()


def set_primary_recipient(
    db: Session,
    proposal: SalesProposal,
    recipient_id: UUID,
    *,
    actor: User,
) -> SalesProposalRecipient:
    recipient = db.get(SalesProposalRecipient, recipient_id)
    if recipient is None or recipient.proposal_id != proposal.id:
        raise ProposalError("sales.proposal.errors.recipient_not_found", status_code=404)

    for r in db.scalars(
        select(SalesProposalRecipient).where(SalesProposalRecipient.proposal_id == proposal.id)
    ).all():
        r.is_primary = False
        r.recipient_type = ProposalRecipientType.CC if r.id != recipient_id else ProposalRecipientType.PRIMARY

    recipient.is_primary = True
    recipient.recipient_type = ProposalRecipientType.PRIMARY
    db.flush()
    return recipient


def list_versions(db: Session, proposal_id: UUID) -> list[SalesProposalVersion]:
    return list(
        db.scalars(
            select(SalesProposalVersion)
            .where(SalesProposalVersion.proposal_id == proposal_id)
            .order_by(SalesProposalVersion.version_number.desc())
        ).all()
    )


def get_version_items(db: Session, version_id: UUID) -> list[SalesProposalItem]:
    return list(
        db.scalars(
            select(SalesProposalItem)
            .where(SalesProposalItem.proposal_version_id == version_id)
            .order_by(SalesProposalItem.sort_order)
        ).all()
    )


def get_recipients(db: Session, proposal_id: UUID) -> list[SalesProposalRecipient]:
    return list(
        db.scalars(
            select(SalesProposalRecipient).where(SalesProposalRecipient.proposal_id == proposal_id)
        ).all()
    )


def get_activities(db: Session, proposal_id: UUID) -> list[SalesProposalActivity]:
    return list(
        db.scalars(
            select(SalesProposalActivity)
            .where(SalesProposalActivity.proposal_id == proposal_id)
            .order_by(SalesProposalActivity.created_at.desc())
        ).all()
    )


def get_approvals(db: Session, proposal_id: UUID) -> list[SalesProposalApproval]:
    return list(
        db.scalars(
            select(SalesProposalApproval)
            .where(SalesProposalApproval.proposal_id == proposal_id)
            .order_by(SalesProposalApproval.created_at.desc())
        ).all()
    )


def mask_item_amounts(items: list[SalesProposalItem], user: User | None) -> list[SalesProposalItem]:
    if user and user_has_permission(user, "sales", "view_sensitive_proposal_price"):
        return items
    for item in items:
        item.displayed_amount = Decimal("0")
    return items


def build_executive_summary(db: Session) -> dict[str, Any]:
    today = date.today()
    expiring_cutoff = today + timedelta(days=7)

    by_status: dict[str, int] = {}
    for status in ProposalStatus:
        count = db.scalar(
            select(func.count())
            .select_from(SalesProposal)
            .where(
                SalesProposal.status == status,
                SalesProposal.archived_at.is_(None),
            )
        )
        by_status[status.value] = count or 0

    value_by_currency: dict[str, str] = {}
    for row in db.execute(
        select(SalesProposal.currency, func.sum(SalesProposalItem.displayed_amount))
        .join(
            SalesProposalVersion,
            SalesProposalVersion.id == SalesProposal.current_version_id,
        )
        .join(
            SalesProposalItem,
            SalesProposalItem.proposal_version_id == SalesProposalVersion.id,
        )
        .where(
            SalesProposal.status.in_(
                [
                    ProposalStatus.SENT,
                    ProposalStatus.VIEWED,
                    ProposalStatus.ACCEPTED,
                ]
            ),
            SalesProposal.archived_at.is_(None),
        )
        .group_by(SalesProposal.currency)
    ).all():
        value_by_currency[row[0]] = str(row[1] or 0)

    expiring_soon = db.scalar(
        select(func.count())
        .select_from(SalesProposal)
        .where(
            SalesProposal.valid_until.isnot(None),
            SalesProposal.valid_until <= expiring_cutoff,
            SalesProposal.valid_until >= today,
            SalesProposal.status.in_(
                [ProposalStatus.APPROVED, ProposalStatus.SENT, ProposalStatus.VIEWED]
            ),
            SalesProposal.archived_at.is_(None),
        )
    ) or 0

    return {
        "by_status": by_status,
        "value_by_currency": value_by_currency,
        "expiring_soon": expiring_soon,
        "pending_review": by_status.get(ProposalStatus.INTERNAL_REVIEW.value, 0),
    }
