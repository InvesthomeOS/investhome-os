"""Sales opportunity business logic."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.inventory import InventoryAsset, InventoryReservation
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project
from investhome_api.models.sales import (
    CLOSED_OPPORTUNITY_STAGES,
    OpportunityInventory,
    OpportunityNextAction,
    OpportunityPartyType,
    OpportunityProbabilityHistory,
    OpportunityProject,
    OpportunityStage,
    OpportunityTimeline,
    SalesOpportunity,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.schemas.sales_opportunity import SalesOpportunityResponse
from investhome_api.services.crm.identity import displayable_phone
from investhome_api.services.sales.config import (
    ALLOWED_STAGE_TRANSITIONS,
    CONTRACT_PATH_STAGES,
    OPPORTUNITY_ACTIVITY_FIELDS,
)


class OpportunityError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def _validate_party(db: Session, party_id: UUID, party_type: OpportunityPartyType) -> None:
    if party_type == OpportunityPartyType.LEAD:
        lead = db.get(Lead, party_id)
        if lead is None or lead.archived_at is not None:
            raise OpportunityError("sales.errors.party_not_found", status_code=404)
        return
    if party_type == OpportunityPartyType.CRM_CONTACT:
        contact = db.get(CrmContact, party_id)
        if contact is None:
            raise OpportunityError("sales.errors.party_not_found", status_code=404)
        return
    investor = db.get(Investor, party_id)
    if investor is None or investor.archived_at is not None:
        raise OpportunityError("sales.errors.party_not_found", status_code=404)


def _party_contact(db: Session, opportunity: SalesOpportunity) -> CrmContact | None:
    if opportunity.party_type == OpportunityPartyType.CRM_CONTACT:
        return db.get(CrmContact, opportunity.crm_contact_id or opportunity.party_id)
    if opportunity.crm_contact_id:
        return db.get(CrmContact, opportunity.crm_contact_id)
    return None


def _party_label(db: Session, opportunity: SalesOpportunity) -> str:
    if opportunity.party_type == OpportunityPartyType.LEAD:
        lead = db.get(Lead, opportunity.party_id)
        return lead.full_name if lead else str(opportunity.party_id)
    contact = _party_contact(db, opportunity)
    if contact is not None:
        return contact.display_name
    if opportunity.party_type == OpportunityPartyType.CRM_CONTACT:
        return str(opportunity.crm_contact_id or opportunity.party_id)
    investor = db.get(Investor, opportunity.party_id)
    return investor.full_name if investor else str(opportunity.party_id)


def serialize_opportunity(db: Session, opportunity: SalesOpportunity) -> SalesOpportunityResponse:
    payload = SalesOpportunityResponse.model_validate(opportunity)
    contact = _party_contact(db, opportunity)
    owner_name = None
    if contact and contact.owner_user_id:
        owner = db.get(User, contact.owner_user_id)
        owner_name = owner.full_name if owner else None
    return payload.model_copy(
        update={
            "party_label": _party_label(db, opportunity),
            "contact_phone": displayable_phone(contact.primary_phone) if contact else None,
            "contact_email": contact.primary_email if contact else None,
            "contact_owner_name": owner_name,
            "contact_last_activity_at": (contact.last_contact_at if contact else None)
            or opportunity.last_contact_at,
            "contact_next_follow_up_at": contact.next_follow_up_at if contact else None,
        }
    )


def _generate_opportunity_code(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"OPP-{today}-"
    count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.opportunity_code.like(f"{prefix}%")
        )
    )
    return f"{prefix}{(count or 0) + 1:04d}"


def _append_timeline(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    event_type: str,
    actor: User | None,
    from_stage: str | None = None,
    to_stage: str | None = None,
    from_probability: int | None = None,
    to_probability: int | None = None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> OpportunityTimeline:
    entry = OpportunityTimeline(
        opportunity_id=opportunity.id,
        event_type=event_type,
        from_stage=from_stage,
        to_stage=to_stage,
        from_probability=from_probability,
        to_probability=to_probability,
        actor_user_id=actor.id if actor else None,
        notes=notes,
        metadata_json=metadata,
    )
    db.add(entry)
    db.flush()
    return entry


def _validate_open_follow_up(opportunity: SalesOpportunity) -> None:
    if opportunity.stage in CLOSED_OPPORTUNITY_STAGES:
        return
    if opportunity.next_action is None or opportunity.next_action_date is None:
        raise OpportunityError("sales.errors.next_action_required")


def _validate_stage_requirements(
    opportunity: SalesOpportunity,
    new_stage: OpportunityStage,
    *,
    from_stage: OpportunityStage,
) -> None:
    if new_stage == OpportunityStage.WON:
        has_reservation = opportunity.reservation_id is not None
        from_contract_path = from_stage in CONTRACT_PATH_STAGES
        if not has_reservation and not from_contract_path:
            raise OpportunityError("sales.errors.won_requires_reservation_or_contract_path")
    if new_stage == OpportunityStage.LOST and opportunity.loss_reason is None:
        raise OpportunityError("sales.errors.loss_reason_required")
    if new_stage == OpportunityStage.DORMANT and opportunity.dormant_review_date is None:
        raise OpportunityError("sales.errors.dormant_review_date_required")
    if new_stage == OpportunityStage.CANCELLED and not opportunity.cancelled_reason:
        raise OpportunityError("sales.errors.cancelled_reason_required")


def get_opportunity_or_raise(
    db: Session,
    opportunity_id: UUID,
    *,
    include_archived: bool = False,
) -> SalesOpportunity:
    opportunity = db.get(SalesOpportunity, opportunity_id)
    if opportunity is None or (opportunity.archived_at is not None and not include_archived):
        raise OpportunityError("sales.errors.not_found", status_code=404)
    return opportunity


def create_opportunity(
    db: Session,
    *,
    data: dict[str, Any],
    actor: User,
    request: Request | None = None,
) -> SalesOpportunity:
    party_id = data["party_id"]
    party_type = data["party_type"]
    _validate_party(db, party_id, party_type)

    lead_id = data.get("lead_id")
    if lead_id is not None:
        lead = db.get(Lead, lead_id)
        if lead is None or lead.archived_at is not None:
            raise OpportunityError("sales.errors.lead_not_found", status_code=404)

    assigned_user_id = data.get("assigned_sales_user_id")
    if assigned_user_id is not None:
        user = db.get(User, assigned_user_id)
        if user is None:
            raise OpportunityError("sales.errors.user_not_found", status_code=404)

    reservation_id = data.get("reservation_id")
    if reservation_id is not None:
        reservation = db.get(InventoryReservation, reservation_id)
        if reservation is None:
            raise OpportunityError("sales.errors.reservation_not_found", status_code=404)

    crm_contact_id = data.get("crm_contact_id")
    if party_type == OpportunityPartyType.CRM_CONTACT:
        crm_contact_id = crm_contact_id or party_id
        contact = db.get(CrmContact, crm_contact_id)
        if contact is None:
            raise OpportunityError("sales.errors.party_not_found", status_code=404)

    opportunity = SalesOpportunity(
        opportunity_code=data.get("opportunity_code") or _generate_opportunity_code(db),
        display_id=data.get("display_id"),
        lead_id=lead_id,
        crm_contact_id=crm_contact_id,
        party_id=party_id,
        party_type=party_type,
        assigned_sales_user_id=assigned_user_id,
        stage=data.get("stage", OpportunityStage.NEW),
        probability=data.get("probability", 0),
        expected_close_date=data.get("expected_close_date"),
        expected_revenue=data.get("expected_revenue"),
        currency=data.get("currency", "USD"),
        priority=data.get("priority"),
        source=data.get("source"),
        current_risks=data.get("current_risks"),
        next_action=data.get("next_action"),
        next_action_date=data.get("next_action_date"),
        last_contact_at=data.get("last_contact_at"),
        notes=data.get("notes"),
        reservation_id=reservation_id,
        is_demo=data.get("is_demo", False),
        created_by_id=actor.id,
    )
    _validate_open_follow_up(opportunity)

    db.add(opportunity)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.opportunity.created",
        actor=actor,
        to_stage=opportunity.stage.value,
        metadata={"opportunity_code": opportunity.opportunity_code},
    )

    log_entity_created(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.created",
        actor=actor,
        metadata={
            "opportunity_code": opportunity.opportunity_code,
            "party": _party_label(db, opportunity),
            "stage": opportunity.stage.value,
        },
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def update_opportunity(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    updates: dict[str, Any],
    actor: User,
    request: Request | None = None,
) -> SalesOpportunity:
    if not updates:
        raise OpportunityError("sales.errors.no_updates", status_code=400)

    if "party_id" in updates or "party_type" in updates:
        party_id = updates.get("party_id", opportunity.party_id)
        party_type = updates.get("party_type", opportunity.party_type)
        _validate_party(db, party_id, party_type)

    if "assigned_sales_user_id" in updates and updates["assigned_sales_user_id"] is not None:
        user = db.get(User, updates["assigned_sales_user_id"])
        if user is None:
            raise OpportunityError("sales.errors.user_not_found", status_code=404)

    if "reservation_id" in updates and updates["reservation_id"] is not None:
        reservation = db.get(InventoryReservation, updates["reservation_id"])
        if reservation is None:
            raise OpportunityError("sales.errors.reservation_not_found", status_code=404)

    before = snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(opportunity, field, value)
    opportunity.updated_at = _now()

    _validate_open_follow_up(opportunity)

    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.updated",
        actor=actor,
        before=before,
        after=snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS),
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def change_stage(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    new_stage: OpportunityStage,
    actor: User,
    request: Request | None = None,
    notes: str | None = None,
    loss_reason: Any = None,
    loss_notes: str | None = None,
    dormant_review_date: date | None = None,
    cancelled_reason: str | None = None,
) -> SalesOpportunity:
    current = opportunity.stage
    if new_stage == current:
        raise OpportunityError("sales.errors.stage_unchanged")

    allowed = ALLOWED_STAGE_TRANSITIONS.get(current, frozenset())
    if new_stage not in allowed:
        raise OpportunityError("sales.errors.invalid_stage_transition")

    if loss_reason is not None:
        opportunity.loss_reason = loss_reason
    if loss_notes is not None:
        opportunity.loss_notes = loss_notes
    if dormant_review_date is not None:
        opportunity.dormant_review_date = dormant_review_date
    if cancelled_reason is not None:
        opportunity.cancelled_reason = cancelled_reason

    _validate_stage_requirements(opportunity, new_stage, from_stage=current)

    before = snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS)
    opportunity.stage = new_stage
    opportunity.updated_at = _now()
    db.flush()

    event_type = "sales.won" if new_stage == OpportunityStage.WON else (
        "sales.lost" if new_stage == OpportunityStage.LOST else "sales.stage.changed"
    )
    _append_timeline(
        db,
        opportunity,
        event_type=event_type,
        actor=actor,
        from_stage=current.value,
        to_stage=new_stage.value,
        notes=notes,
        metadata={"opportunity_code": opportunity.opportunity_code},
    )

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.stage_changed",
        actor=actor,
        before=before,
        after=snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS),
        metadata={
            "opportunity_code": opportunity.opportunity_code,
            "from_stage": current.value,
            "to_stage": new_stage.value,
        },
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def change_probability(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    new_probability: int,
    actor: User,
    reason: str | None = None,
    request: Request | None = None,
) -> SalesOpportunity:
    if new_probability < 0 or new_probability > 100:
        raise OpportunityError("sales.errors.invalid_probability")
    if new_probability == opportunity.probability:
        raise OpportunityError("sales.errors.probability_unchanged")

    old = opportunity.probability
    before = snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS)
    opportunity.probability = new_probability
    opportunity.updated_at = _now()

    history = OpportunityProbabilityHistory(
        opportunity_id=opportunity.id,
        old_probability=old,
        new_probability=new_probability,
        changed_by_id=actor.id,
        reason=reason,
    )
    db.add(history)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.probability.changed",
        actor=actor,
        from_probability=old,
        to_probability=new_probability,
        notes=reason,
    )

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.probability_changed",
        actor=actor,
        before=before,
        after=snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS),
        metadata={
            "opportunity_code": opportunity.opportunity_code,
            "old_probability": old,
            "new_probability": new_probability,
        },
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def update_next_action(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    next_action: OpportunityNextAction,
    next_action_date: date,
    actor: User,
    request: Request | None = None,
) -> SalesOpportunity:
    before = snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS)
    opportunity.next_action = next_action
    opportunity.next_action_date = next_action_date
    opportunity.updated_at = _now()
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.next_action.changed",
        actor=actor,
        metadata={
            "next_action": next_action.value,
            "next_action_date": next_action_date.isoformat(),
        },
    )

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.next_action_changed",
        actor=actor,
        before=before,
        after=snapshot_entity(opportunity, OPPORTUNITY_ACTIVITY_FIELDS),
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def link_inventory(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    inventory_asset_id: UUID,
    actor: User,
    match_reason: str | None = None,
    is_favorite: bool = False,
    notes: str | None = None,
    request: Request | None = None,
) -> OpportunityInventory:
    asset = db.get(InventoryAsset, inventory_asset_id)
    if asset is None or asset.archived_at is not None:
        raise OpportunityError("sales.errors.inventory_not_found", status_code=404)

    existing = db.scalar(
        select(OpportunityInventory).where(
            OpportunityInventory.opportunity_id == opportunity.id,
            OpportunityInventory.inventory_asset_id == inventory_asset_id,
        )
    )
    if existing is not None:
        raise OpportunityError("sales.errors.inventory_already_linked")

    link = OpportunityInventory(
        opportunity_id=opportunity.id,
        inventory_asset_id=inventory_asset_id,
        match_reason=match_reason,
        is_favorite=is_favorite,
        shortlisted_at=_now() if is_favorite else None,
        notes=notes,
    )
    db.add(link)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.inventory.linked",
        actor=actor,
        metadata={"inventory_asset_id": str(inventory_asset_id)},
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.inventory_linked",
        actor=actor,
        before={},
        after={"inventory_asset_id": str(inventory_asset_id)},
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return link


def unlink_inventory(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    inventory_asset_id: UUID,
    actor: User,
    request: Request | None = None,
) -> None:
    link = db.scalar(
        select(OpportunityInventory).where(
            OpportunityInventory.opportunity_id == opportunity.id,
            OpportunityInventory.inventory_asset_id == inventory_asset_id,
        )
    )
    if link is None:
        raise OpportunityError("sales.errors.inventory_not_linked", status_code=404)
    db.delete(link)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.inventory.unlinked",
        actor=actor,
        metadata={"inventory_asset_id": str(inventory_asset_id)},
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.inventory_unlinked",
        actor=actor,
        before={"inventory_asset_id": str(inventory_asset_id)},
        after={},
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )


def link_project(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    project_id: UUID,
    actor: User,
    request: Request | None = None,
) -> OpportunityProject:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise OpportunityError("sales.errors.project_not_found", status_code=404)

    existing = db.scalar(
        select(OpportunityProject).where(
            OpportunityProject.opportunity_id == opportunity.id,
            OpportunityProject.project_id == project_id,
        )
    )
    if existing is not None:
        raise OpportunityError("sales.errors.project_already_linked")

    link = OpportunityProject(opportunity_id=opportunity.id, project_id=project_id)
    db.add(link)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.project.linked",
        actor=actor,
        metadata={"project_id": str(project_id)},
    )
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.project_linked",
        actor=actor,
        before={},
        after={"project_id": str(project_id)},
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return link


def unlink_project(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    project_id: UUID,
    actor: User,
    request: Request | None = None,
) -> None:
    link = db.scalar(
        select(OpportunityProject).where(
            OpportunityProject.opportunity_id == opportunity.id,
            OpportunityProject.project_id == project_id,
        )
    )
    if link is None:
        raise OpportunityError("sales.errors.project_not_linked", status_code=404)
    db.delete(link)
    db.flush()

    _append_timeline(
        db,
        opportunity,
        event_type="sales.project.unlinked",
        actor=actor,
        metadata={"project_id": str(project_id)},
    )


def archive_opportunity(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesOpportunity:
    if opportunity.archived_at is not None:
        raise OpportunityError("sales.errors.already_archived")
    opportunity.archived_at = _now()
    opportunity.updated_at = _now()
    db.flush()

    _append_timeline(db, opportunity, event_type="sales.archived", actor=actor)
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.archived",
        actor=actor,
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def restore_opportunity(
    db: Session,
    opportunity: SalesOpportunity,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesOpportunity:
    if opportunity.archived_at is None:
        raise OpportunityError("sales.errors.not_archived")
    opportunity.archived_at = None
    opportunity.updated_at = _now()
    db.flush()

    _append_timeline(db, opportunity, event_type="sales.restored", actor=actor)
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=opportunity.id,
        description_key="activity.sales_opportunity.restored",
        actor=actor,
        metadata={"opportunity_code": opportunity.opportunity_code},
        request=request,
        is_demo=opportunity.is_demo,
    )
    return opportunity


def list_opportunities(
    db: Session,
    *,
    search: str | None = None,
    stage: OpportunityStage | None = None,
    assigned_sales_user_id: UUID | None = None,
    party_id: UUID | None = None,
    lead_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SalesOpportunity], int]:
    query = select(SalesOpportunity)
    count_query = select(func.count()).select_from(SalesOpportunity)

    if not include_archived:
        query = query.where(SalesOpportunity.archived_at.is_(None))
        count_query = count_query.where(SalesOpportunity.archived_at.is_(None))

    if stage is not None:
        query = query.where(SalesOpportunity.stage == stage)
        count_query = count_query.where(SalesOpportunity.stage == stage)

    if assigned_sales_user_id is not None:
        query = query.where(SalesOpportunity.assigned_sales_user_id == assigned_sales_user_id)
        count_query = count_query.where(SalesOpportunity.assigned_sales_user_id == assigned_sales_user_id)

    if party_id is not None:
        query = query.where(SalesOpportunity.party_id == party_id)
        count_query = count_query.where(SalesOpportunity.party_id == party_id)

    if lead_id is not None:
        query = query.where(SalesOpportunity.lead_id == lead_id)
        count_query = count_query.where(SalesOpportunity.lead_id == lead_id)

    if search:
        pattern = f"%{search.strip()}%"
        contact_ids = select(CrmContact.id).where(
            or_(
                CrmContact.display_name.ilike(pattern),
                CrmContact.primary_email.ilike(pattern),
                CrmContact.primary_phone.ilike(pattern),
            )
        )
        query = query.where(
            or_(
                SalesOpportunity.opportunity_code.ilike(pattern),
                SalesOpportunity.display_id.ilike(pattern),
                SalesOpportunity.notes.ilike(pattern),
                SalesOpportunity.crm_contact_id.in_(contact_ids),
            )
        )
        count_query = count_query.where(
            or_(
                SalesOpportunity.opportunity_code.ilike(pattern),
                SalesOpportunity.display_id.ilike(pattern),
                SalesOpportunity.notes.ilike(pattern),
                SalesOpportunity.crm_contact_id.in_(contact_ids),
            )
        )

    sort_column = getattr(SalesOpportunity, sort_by, SalesOpportunity.updated_at)
    order = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
    query = query.order_by(order).offset(offset).limit(limit)

    total = db.scalar(count_query) or 0
    items = list(db.scalars(query).all())
    return items, total


def get_timeline(db: Session, opportunity_id: UUID) -> list[OpportunityTimeline]:
    return list(
        db.scalars(
            select(OpportunityTimeline)
            .where(OpportunityTimeline.opportunity_id == opportunity_id)
            .order_by(OpportunityTimeline.created_at.desc())
        ).all()
    )


def build_pipeline_summary(db: Session, *, include_archived: bool = False) -> dict[str, Any]:
    query = select(SalesOpportunity.stage, func.count()).group_by(SalesOpportunity.stage)
    if not include_archived:
        query = query.where(SalesOpportunity.archived_at.is_(None))
    rows = db.execute(query).all()
    stages = {stage.value: count for stage, count in rows}
    total = sum(stages.values())
    return {"stages": stages, "total": total}


def build_dashboard_metrics(db: Session) -> dict[str, Any]:
    today = date.today()
    open_stages = [s for s in OpportunityStage if s not in CLOSED_OPPORTUNITY_STAGES]
    open_count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
        )
    ) or 0

    pipeline_value = db.scalar(
        select(func.coalesce(func.sum(SalesOpportunity.expected_revenue), 0)).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
        )
    ) or Decimal("0")

    won_count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage == OpportunityStage.WON,
        )
    ) or 0

    lost_count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage == OpportunityStage.LOST,
        )
    ) or 0

    no_follow_up = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            or_(
                SalesOpportunity.next_action.is_(None),
                SalesOpportunity.next_action_date.is_(None),
                SalesOpportunity.next_action_date < today,
            ),
        )
    ) or 0

    dormant_count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage == OpportunityStage.DORMANT,
        )
    ) or 0

    closing_cutoff = today + timedelta(days=30)
    closing_soon = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            SalesOpportunity.expected_close_date.is_not(None),
            SalesOpportunity.expected_close_date >= today,
            SalesOpportunity.expected_close_date <= closing_cutoff,
        )
    ) or 0

    return {
        "open_opportunities": open_count,
        "pipeline_value": str(pipeline_value),
        "won_count": won_count,
        "lost_count": lost_count,
        "no_follow_up": no_follow_up,
        "dormant_count": dormant_count,
        "expected_closings_30d": closing_soon,
    }


def build_executive_summary(db: Session) -> dict[str, Any]:
    today = date.today()
    open_stages = [s for s in OpportunityStage if s not in CLOSED_OPPORTUNITY_STAGES]

    pipeline_value = db.scalar(
        select(func.coalesce(func.sum(SalesOpportunity.expected_revenue), 0)).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
        )
    ) or Decimal("0")

    weighted_value = db.scalar(
        select(
            func.coalesce(
                func.sum(SalesOpportunity.expected_revenue * SalesOpportunity.probability / 100),
                0,
            )
        ).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            SalesOpportunity.expected_revenue.is_not(None),
        )
    ) or Decimal("0")

    high_risk = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            SalesOpportunity.probability < 30,
        )
    ) or 0

    no_follow_up = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            or_(
                SalesOpportunity.next_action.is_(None),
                SalesOpportunity.next_action_date.is_(None),
                SalesOpportunity.next_action_date < today,
            ),
        )
    ) or 0

    dormant = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage == OpportunityStage.DORMANT,
        )
    ) or 0

    closing_cutoff = today + timedelta(days=30)
    expected_closings = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.in_(open_stages),
            SalesOpportunity.expected_close_date.is_not(None),
            SalesOpportunity.expected_close_date >= today,
            SalesOpportunity.expected_close_date <= closing_cutoff,
        )
    ) or 0

    return {
        "pipeline_value": str(pipeline_value),
        "weighted_pipeline_value": str(weighted_value),
        "high_risk_count": high_risk,
        "no_follow_up_count": no_follow_up,
        "dormant_count": dormant,
        "expected_closings_30d": expected_closings,
    }
