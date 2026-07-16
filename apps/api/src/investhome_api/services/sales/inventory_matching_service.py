"""Sales inventory matching, preferences, shortlists, and reservation delegation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    Floor,
    InventoryAsset,
    InventorySalesStatus,
    ReservationSource,
)
from investhome_api.models.lead import Lead
from investhome_api.models.lead_qualification import LeadInterestType, LeadInventoryInterest
from investhome_api.models.project import Project
from investhome_api.models.sales import CLOSED_OPPORTUNITY_STAGES, OpportunityInventory, SalesOpportunity
from investhome_api.models.sales_inventory_matching import (
    MatchRejectionReason,
    MatchRelationshipType,
    MatchSource,
    MatchStatus,
    SalesInventoryMatch,
    SalesInventoryPreference,
    SalesInventoryPreferenceAssetType,
    SalesInventoryPreferenceBuilding,
    SalesInventoryPreferenceProject,
    SalesInventoryPreferenceUsageType,
    SalesShortlist,
    SalesShortlistItem,
    ShortlistStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.inventory import reservation_service as reservation_svc
from investhome_api.services.inventory.pricing_service import enrich_asset_pricing_summary
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales.inventory_matching_notifications import (
    notify_shortlisted_unavailable,
)


class InventoryMatchingError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


PREFERENCE_FIELDS = (
    "budget_min",
    "budget_max",
    "currency",
    "bedrooms_min",
    "bedrooms_max",
    "bathrooms_min",
    "bathrooms_max",
    "area_min",
    "area_max",
    "floor_min",
    "floor_max",
    "delivery_date_before",
    "notes",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _validate_context(*, lead_id: UUID | None, opportunity_id: UUID | None) -> None:
    if (lead_id is None) == (opportunity_id is None):
        raise InventoryMatchingError("sales.errors.match_context_required")


def _get_lead_or_raise(db: Session, lead_id: UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None:
        raise InventoryMatchingError("leads.errors.not_found", status_code=404)
    return lead


def _get_opportunity_or_raise(db: Session, opportunity_id: UUID) -> SalesOpportunity:
    opp = db.get(SalesOpportunity, opportunity_id)
    if opp is None or opp.archived_at is not None:
        raise InventoryMatchingError("sales.errors.opportunity_not_found", status_code=404)
    return opp


def _get_asset_or_raise(db: Session, asset_id: UUID) -> InventoryAsset:
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise InventoryMatchingError("sales.errors.inventory_not_found", status_code=404)
    return asset


def _build_inventory_snapshot(db: Session, asset: InventoryAsset, *, user: User) -> dict[str, Any]:
    pricing = enrich_asset_pricing_summary(db, asset, user=user)
    return {
        "availability_status": asset.availability_status.value,
        "reservation_status": asset.reservation_status.value,
        "sales_status": asset.sales_status.value,
        "list_price": pricing.get("list_price"),
        "currency": asset.currency,
        "captured_at": _now().isoformat(),
    }


def _detect_stale(snapshot: dict | None, current: dict[str, Any]) -> tuple[bool, list[str]]:
    if not snapshot:
        return False, []
    stale_fields: list[str] = []
    for field in ("availability_status", "reservation_status", "list_price"):
        if snapshot.get(field) != current.get(field):
            stale_fields.append(field)
    return bool(stale_fields), stale_fields


def _load_preference_relations(db: Session, pref: SalesInventoryPreference) -> dict[str, list]:
    projects = list(
        db.scalars(
            select(SalesInventoryPreferenceProject.project_id).where(
                SalesInventoryPreferenceProject.preference_id == pref.id
            )
        ).all()
    )
    asset_types = list(
        db.scalars(
            select(SalesInventoryPreferenceAssetType.asset_type).where(
                SalesInventoryPreferenceAssetType.preference_id == pref.id
            )
        ).all()
    )
    usage_types = list(
        db.scalars(
            select(SalesInventoryPreferenceUsageType.usage_type).where(
                SalesInventoryPreferenceUsageType.preference_id == pref.id
            )
        ).all()
    )
    buildings = list(
        db.scalars(
            select(SalesInventoryPreferenceBuilding.building_id).where(
                SalesInventoryPreferenceBuilding.preference_id == pref.id
            )
        ).all()
    )
    return {
        "preferred_project_ids": projects,
        "preferred_asset_types": asset_types,
        "preferred_usage_types": usage_types,
        "preferred_building_ids": buildings,
    }


def _preference_response(db: Session, pref: SalesInventoryPreference) -> dict[str, Any]:
    relations = _load_preference_relations(db, pref)
    return {
        "id": pref.id,
        "lead_id": pref.lead_id,
        "opportunity_id": pref.opportunity_id,
        "budget_min": pref.budget_min,
        "budget_max": pref.budget_max,
        "currency": pref.currency,
        "bedrooms_min": pref.bedrooms_min,
        "bedrooms_max": pref.bedrooms_max,
        "bathrooms_min": pref.bathrooms_min,
        "bathrooms_max": pref.bathrooms_max,
        "area_min": pref.area_min,
        "area_max": pref.area_max,
        "floor_min": pref.floor_min,
        "floor_max": pref.floor_max,
        "delivery_date_before": pref.delivery_date_before,
        "notes": pref.notes,
        "created_at": pref.created_at,
        "updated_at": pref.updated_at,
        **relations,
    }


def get_preference(
    db: Session,
    *,
    lead_id: UUID | None = None,
    opportunity_id: UUID | None = None,
) -> SalesInventoryPreference | None:
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)
    if lead_id:
        _get_lead_or_raise(db, lead_id)
        return db.scalar(select(SalesInventoryPreference).where(SalesInventoryPreference.lead_id == lead_id))
    assert opportunity_id is not None
    _get_opportunity_or_raise(db, opportunity_id)
    return db.scalar(
        select(SalesInventoryPreference).where(SalesInventoryPreference.opportunity_id == opportunity_id)
    )


def save_preference(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesInventoryPreference:
    lead_id = data.get("lead_id")
    opportunity_id = data.get("opportunity_id")
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)

    if lead_id:
        _get_lead_or_raise(db, lead_id)
        pref = db.scalar(select(SalesInventoryPreference).where(SalesInventoryPreference.lead_id == lead_id))
    else:
        _get_opportunity_or_raise(db, opportunity_id)
        pref = db.scalar(
            select(SalesInventoryPreference).where(SalesInventoryPreference.opportunity_id == opportunity_id)
        )

    project_ids = data.pop("preferred_project_ids", [])
    asset_types = data.pop("preferred_asset_types", [])
    usage_types = data.pop("preferred_usage_types", [])
    building_ids = data.pop("preferred_building_ids", [])

    before = snapshot_entity(pref, PREFERENCE_FIELDS) if pref else {}
    if pref is None:
        pref = SalesInventoryPreference(
            lead_id=lead_id,
            opportunity_id=opportunity_id,
            created_by_user_id=actor.id,
        )
        db.add(pref)
    for field in PREFERENCE_FIELDS:
        if field in data:
            setattr(pref, field, data[field])
    pref.updated_at = _now()
    db.flush()

    for model, attr, values in (
        (SalesInventoryPreferenceProject, "project_id", project_ids),
        (SalesInventoryPreferenceAssetType, "asset_type", asset_types),
        (SalesInventoryPreferenceUsageType, "usage_type", usage_types),
        (SalesInventoryPreferenceBuilding, "building_id", building_ids),
    ):
        existing_rows = list(db.scalars(select(model).where(model.preference_id == pref.id)).all())
        for row in existing_rows:
            db.delete(row)
        for val in values:
            db.add(model(preference_id=pref.id, **{attr: val}))

    db.flush()

    if before:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.SALES_OPPORTUNITY if opportunity_id else ActivityEntityType.LEAD,
            entity_id=opportunity_id or lead_id,
            description_key="activity.sales.inventory.preference_saved",
            actor=actor,
            before=before,
            after=snapshot_entity(pref, PREFERENCE_FIELDS),
            metadata={"preference_id": str(pref.id)},
            request=request,
        )
    else:
        log_entity_created(
            db,
            entity_type=ActivityEntityType.SALES_OPPORTUNITY if opportunity_id else ActivityEntityType.LEAD,
            entity_id=opportunity_id or lead_id,
            description_key="activity.sales.inventory.preference_saved",
            actor=actor,
            metadata={"preference_id": str(pref.id)},
            request=request,
        )

    return pref


def _apply_search_filters(query, criteria: dict[str, Any], *, user: User):
    if not criteria.get("include_archived"):
        query = query.where(InventoryAsset.archived_at.is_(None))

    if project_id := criteria.get("project_id"):
        query = query.where(InventoryAsset.project_id == project_id)
    if building_id := criteria.get("building_id"):
        query = query.where(InventoryAsset.building_id == building_id)
    if asset_type := criteria.get("asset_type"):
        query = query.where(InventoryAsset.asset_type == asset_type)
    if usage_type := criteria.get("usage_type"):
        query = query.where(InventoryAsset.usage_type == usage_type)
    if availability := criteria.get("availability_status"):
        query = query.where(InventoryAsset.availability_status == availability)
    if criteria.get("sales_status"):
        query = query.where(InventoryAsset.sales_status == criteria["sales_status"])
    else:
        query = query.where(InventoryAsset.sales_status == InventorySalesStatus.AVAILABLE_FOR_SALE)

    if bedrooms_min := criteria.get("bedrooms_min"):
        query = query.where(InventoryAsset.bedrooms >= bedrooms_min)
    if bedrooms_max := criteria.get("bedrooms_max"):
        query = query.where(InventoryAsset.bedrooms <= bedrooms_max)
    if area_min := criteria.get("area_min"):
        query = query.where(InventoryAsset.interior_area_sqft >= area_min)
    if area_max := criteria.get("area_max"):
        query = query.where(InventoryAsset.interior_area_sqft <= area_max)

    if budget_min := criteria.get("budget_min"):
        if not user_has_permission(user, "inventory", "view_price"):
            raise InventoryMatchingError("sales.errors.price_permission_required", status_code=403)
        query = query.where(InventoryAsset.list_price >= budget_min)
    if budget_max := criteria.get("budget_max"):
        if not user_has_permission(user, "inventory", "view_price"):
            raise InventoryMatchingError("sales.errors.price_permission_required", status_code=403)
        query = query.where(InventoryAsset.list_price <= budget_max)

    if search := criteria.get("search"):
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                InventoryAsset.display_id.ilike(pattern),
                InventoryAsset.system_code.ilike(pattern),
            )
        )
    return query


def search_inventory(
    db: Session,
    criteria: dict[str, Any],
    *,
    user: User,
) -> tuple[list[dict[str, Any]], int]:
    if not user_has_permission(user, "inventory", "view"):
        raise InventoryMatchingError("sales.errors.inventory_view_required", status_code=403)

    page = criteria.get("page", 1)
    page_size = criteria.get("page_size", 20)
    lead_id = criteria.get("lead_id")
    opportunity_id = criteria.get("opportunity_id")

    query = select(InventoryAsset)
    query = _apply_search_filters(query, criteria, user=user)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(desc(InventoryAsset.updated_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    assets = list(db.scalars(query).all())

    rejected_ids: set[UUID] = set()
    if criteria.get("exclude_rejected", True) and (lead_id or opportunity_id):
        rejected_q = select(SalesInventoryMatch.inventory_asset_id).where(
            SalesInventoryMatch.status == MatchStatus.REJECTED,
        )
        if lead_id:
            rejected_q = rejected_q.where(SalesInventoryMatch.lead_id == lead_id)
        else:
            rejected_q = rejected_q.where(SalesInventoryMatch.opportunity_id == opportunity_id)
        rejected_ids = set(db.scalars(rejected_q).all())

    existing_matches: dict[UUID, SalesInventoryMatch] = {}
    if lead_id or opportunity_id:
        match_q = select(SalesInventoryMatch).where(SalesInventoryMatch.status != MatchStatus.ARCHIVED)
        if lead_id:
            match_q = match_q.where(SalesInventoryMatch.lead_id == lead_id)
        else:
            match_q = match_q.where(SalesInventoryMatch.opportunity_id == opportunity_id)
        for m in db.scalars(match_q).all():
            existing_matches[m.inventory_asset_id] = m

    items: list[dict[str, Any]] = []
    for asset in assets:
        if asset.id in rejected_ids:
            continue
        pricing = enrich_asset_pricing_summary(db, asset, user=user)
        current = _build_inventory_snapshot(db, asset, user=user)
        existing = existing_matches.get(asset.id)
        is_stale = False
        if existing and existing.inventory_snapshot:
            is_stale, _ = _detect_stale(existing.inventory_snapshot, current)

        items.append(
            {
                "asset_id": asset.id,
                "display_id": asset.display_id,
                "system_code": asset.system_code,
                "project_id": asset.project_id,
                "asset_type": asset.asset_type.value,
                "usage_type": asset.usage_type.value,
                "availability_status": asset.availability_status.value,
                "reservation_status": asset.reservation_status.value,
                "sales_status": asset.sales_status.value,
                "bedrooms": asset.bedrooms,
                "bathrooms": asset.bathrooms,
                "interior_area_sqft": asset.interior_area_sqft,
                "list_price": pricing.get("list_price"),
                "currency": asset.currency,
                "is_stale": is_stale,
                "existing_match_id": existing.id if existing else None,
                "relationship_type": existing.relationship_type if existing else None,
            }
        )

    return items, total


def _sync_opportunity_inventory(
    db: Session,
    opportunity: SalesOpportunity,
    asset: InventoryAsset,
    *,
    relationship_type: MatchRelationshipType,
    is_primary: bool = False,
    is_favorite: bool = False,
    match_reason: str | None = None,
) -> OpportunityInventory:
    link = db.scalar(
        select(OpportunityInventory).where(
            OpportunityInventory.opportunity_id == opportunity.id,
            OpportunityInventory.inventory_asset_id == asset.id,
        )
    )
    if link is None:
        link = OpportunityInventory(
            opportunity_id=opportunity.id,
            inventory_asset_id=asset.id,
            match_reason=match_reason,
            is_favorite=is_favorite or relationship_type == MatchRelationshipType.FAVORITE,
            is_primary=is_primary,
            shortlisted_at=_now() if relationship_type == MatchRelationshipType.SHORTLISTED else None,
        )
        db.add(link)
    else:
        link.is_favorite = is_favorite or relationship_type == MatchRelationshipType.FAVORITE
        link.is_primary = is_primary
        if match_reason:
            link.match_reason = match_reason
        if relationship_type == MatchRelationshipType.SHORTLISTED:
            link.shortlisted_at = _now()
    db.flush()
    return link


def _sync_lead_interest(
    db: Session,
    lead: Lead,
    asset: InventoryAsset,
    *,
    relationship_type: MatchRelationshipType,
    match_reason: str | None = None,
    opportunity_id: UUID | None = None,
) -> LeadInventoryInterest:
    interest_type_map = {
        MatchRelationshipType.MATCHED: LeadInterestType.MATCHED,
        MatchRelationshipType.SHORTLISTED: LeadInterestType.SHORTLISTED,
        MatchRelationshipType.FAVORITE: LeadInterestType.FAVORITE,
        MatchRelationshipType.REJECTED: LeadInterestType.REJECTED,
    }
    interest_type = interest_type_map.get(relationship_type)
    if interest_type is None:
        return None  # type: ignore[return-value]

    existing = db.scalar(
        select(LeadInventoryInterest).where(
            LeadInventoryInterest.lead_id == lead.id,
            LeadInventoryInterest.inventory_asset_id == asset.id,
        )
    )
    if existing is None:
        existing = LeadInventoryInterest(
            lead_id=lead.id,
            inventory_asset_id=asset.id,
            interest_type=interest_type,
            match_reason=match_reason,
            opportunity_id=opportunity_id,
        )
        db.add(existing)
    else:
        existing.interest_type = interest_type
        existing.match_reason = match_reason
        if opportunity_id:
            existing.opportunity_id = opportunity_id
    db.flush()
    return existing


def create_match(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesInventoryMatch:
    lead_id = data.get("lead_id")
    opportunity_id = data.get("opportunity_id")
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)

    asset = _get_asset_or_raise(db, data["inventory_asset_id"])
    relationship_type = data.get("relationship_type", MatchRelationshipType.MATCHED)

    if lead_id:
        _get_lead_or_raise(db, lead_id)
    if opportunity_id:
        _get_opportunity_or_raise(db, opportunity_id)

    existing = db.scalar(
        select(SalesInventoryMatch).where(
            SalesInventoryMatch.inventory_asset_id == asset.id,
            SalesInventoryMatch.lead_id == lead_id if lead_id else SalesInventoryMatch.lead_id.is_(None),
            SalesInventoryMatch.opportunity_id == opportunity_id
            if opportunity_id
            else SalesInventoryMatch.opportunity_id.is_(None),
            SalesInventoryMatch.status != MatchStatus.ARCHIVED,
        )
    )
    if existing and existing.status not in (MatchStatus.REJECTED, MatchStatus.ARCHIVED):
        raise InventoryMatchingError("sales.errors.match_already_exists")
    if existing and existing.status == MatchStatus.REJECTED:
        existing.status = MatchStatus.ACTIVE
        existing.relationship_type = relationship_type
        existing.rejection_reason = None
        existing.inventory_snapshot = _build_inventory_snapshot(db, asset, user=actor)
        existing.updated_at = _now()
        db.flush()
        match = existing
    else:
        snapshot = _build_inventory_snapshot(db, asset, user=actor)
        match = SalesInventoryMatch(
            lead_id=lead_id,
            opportunity_id=opportunity_id,
            inventory_asset_id=asset.id,
            relationship_type=relationship_type,
            match_source=data.get("match_source", MatchSource.MANUAL),
            match_score=data.get("match_score"),
            match_reason=data.get("match_reason"),
            inventory_snapshot=snapshot,
            created_by_user_id=actor.id,
        )
        db.add(match)
        db.flush()

    if opportunity_id:
        opp = _get_opportunity_or_raise(db, opportunity_id)
        _sync_opportunity_inventory(
            db,
            opp,
            asset,
            relationship_type=relationship_type,
            is_favorite=relationship_type == MatchRelationshipType.FAVORITE,
            match_reason=data.get("match_reason"),
        )
    if lead_id:
        lead = _get_lead_or_raise(db, lead_id)
        _sync_lead_interest(
            db,
            lead,
            asset,
            relationship_type=relationship_type,
            match_reason=data.get("match_reason"),
            opportunity_id=opportunity_id,
        )

    entity_id = opportunity_id or lead_id
    entity_type = (
        ActivityEntityType.SALES_OPPORTUNITY if opportunity_id else ActivityEntityType.LEAD
    )
    log_entity_created(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key="activity.sales.inventory.matched",
        actor=actor,
        metadata={
            "match_id": str(match.id),
            "inventory_asset_id": str(asset.id),
            "relationship_type": relationship_type.value,
        },
        request=request,
    )
    return match


def list_matches(
    db: Session,
    *,
    lead_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    relationship_type: MatchRelationshipType | None = None,
    status: MatchStatus | None = None,
    exclude_rejected: bool = False,
    user: User,
) -> list[dict[str, Any]]:
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)
    query = select(SalesInventoryMatch).where(SalesInventoryMatch.archived_at.is_(None))
    if lead_id:
        query = query.where(SalesInventoryMatch.lead_id == lead_id)
    else:
        query = query.where(SalesInventoryMatch.opportunity_id == opportunity_id)
    if relationship_type:
        query = query.where(SalesInventoryMatch.relationship_type == relationship_type)
    if status:
        query = query.where(SalesInventoryMatch.status == status)
    elif exclude_rejected:
        query = query.where(SalesInventoryMatch.status != MatchStatus.REJECTED)

    matches = list(db.scalars(query.order_by(desc(SalesInventoryMatch.updated_at))).all())
    return [_enrich_match(db, m, user=user) for m in matches]


def _enrich_match(db: Session, match: SalesInventoryMatch, *, user: User) -> dict[str, Any]:
    asset = db.get(InventoryAsset, match.inventory_asset_id)
    pricing = enrich_asset_pricing_summary(db, asset, user=user) if asset else {}
    current = _build_inventory_snapshot(db, asset, user=user) if asset else {}
    is_stale, stale_fields = _detect_stale(match.inventory_snapshot, current)

    if is_stale and match.relationship_type == MatchRelationshipType.SHORTLISTED:
        if asset and asset.availability_status != AvailabilityStatus.AVAILABLE:
            notify_shortlisted_unavailable(db, match=match, asset=asset)

    return {
        "id": match.id,
        "lead_id": match.lead_id,
        "opportunity_id": match.opportunity_id,
        "inventory_asset_id": match.inventory_asset_id,
        "relationship_type": match.relationship_type,
        "status": match.status,
        "match_source": match.match_source,
        "match_score": match.match_score,
        "match_reason": match.match_reason,
        "rejection_reason": match.rejection_reason,
        "is_primary": match.is_primary,
        "inventory_snapshot": match.inventory_snapshot,
        "is_stale": is_stale,
        "stale_fields": stale_fields,
        "created_by_user_id": match.created_by_user_id,
        "archived_at": match.archived_at,
        "created_at": match.created_at,
        "updated_at": match.updated_at,
        "asset_display_id": asset.display_id if asset else None,
        "list_price": pricing.get("list_price"),
    }


def reject_match(
    db: Session,
    match: SalesInventoryMatch,
    *,
    rejection_reason: MatchRejectionReason,
    notes: str | None,
    actor: User,
    request: Request | None = None,
) -> SalesInventoryMatch:
    if match.archived_at is not None:
        raise InventoryMatchingError("sales.errors.match_archived")
    match.status = MatchStatus.REJECTED
    match.relationship_type = MatchRelationshipType.REJECTED
    match.rejection_reason = rejection_reason
    if notes:
        match.match_reason = notes
    match.updated_at = _now()
    db.flush()

    if match.lead_id:
        lead = _get_lead_or_raise(db, match.lead_id)
        asset = _get_asset_or_raise(db, match.inventory_asset_id)
        _sync_lead_interest(
            db,
            lead,
            asset,
            relationship_type=MatchRelationshipType.REJECTED,
            match_reason=rejection_reason.value,
            opportunity_id=match.opportunity_id,
        )

    entity_id = match.opportunity_id or match.lead_id
    entity_type = (
        ActivityEntityType.SALES_OPPORTUNITY if match.opportunity_id else ActivityEntityType.LEAD
    )
    log_entity_updated(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key="activity.sales.inventory.rejected",
        actor=actor,
        before={},
        after={"rejection_reason": rejection_reason.value},
        metadata={"match_id": str(match.id)},
        request=request,
    )
    return match


def set_primary_match(
    db: Session,
    match: SalesInventoryMatch,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesInventoryMatch:
    if not match.opportunity_id:
        raise InventoryMatchingError("sales.errors.primary_requires_opportunity")
    if match.status == MatchStatus.REJECTED:
        raise InventoryMatchingError("sales.errors.rejected_cannot_be_primary")

    others = list(
        db.scalars(
            select(SalesInventoryMatch).where(
                SalesInventoryMatch.opportunity_id == match.opportunity_id,
                SalesInventoryMatch.is_primary.is_(True),
                SalesInventoryMatch.id != match.id,
            )
        ).all()
    )
    for other in others:
        other.is_primary = False
        link = db.scalar(
            select(OpportunityInventory).where(
                OpportunityInventory.opportunity_id == match.opportunity_id,
                OpportunityInventory.inventory_asset_id == other.inventory_asset_id,
            )
        )
        if link:
            link.is_primary = False

    match.is_primary = True
    match.relationship_type = MatchRelationshipType.SELECTED
    match.updated_at = _now()
    db.flush()

    opp = _get_opportunity_or_raise(db, match.opportunity_id)
    asset = _get_asset_or_raise(db, match.inventory_asset_id)
    _sync_opportunity_inventory(
        db,
        opp,
        asset,
        relationship_type=MatchRelationshipType.SELECTED,
        is_primary=True,
        match_reason=match.match_reason,
    )

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY,
        entity_id=match.opportunity_id,
        description_key="activity.sales.inventory.primary_selected",
        actor=actor,
        before={},
        after={"inventory_asset_id": str(match.inventory_asset_id)},
        metadata={"match_id": str(match.id)},
        request=request,
    )
    return match


def favorite_match(
    db: Session,
    match: SalesInventoryMatch,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesInventoryMatch:
    match.relationship_type = MatchRelationshipType.FAVORITE
    match.updated_at = _now()
    db.flush()

    if match.opportunity_id:
        opp = _get_opportunity_or_raise(db, match.opportunity_id)
        asset = _get_asset_or_raise(db, match.inventory_asset_id)
        _sync_opportunity_inventory(
            db, opp, asset, relationship_type=MatchRelationshipType.FAVORITE, is_favorite=True
        )
    if match.lead_id:
        lead = _get_lead_or_raise(db, match.lead_id)
        asset = _get_asset_or_raise(db, match.inventory_asset_id)
        _sync_lead_interest(
            db,
            lead,
            asset,
            relationship_type=MatchRelationshipType.FAVORITE,
            opportunity_id=match.opportunity_id,
        )

    entity_id = match.opportunity_id or match.lead_id
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY if match.opportunity_id else ActivityEntityType.LEAD,
        entity_id=entity_id,
        description_key="activity.sales.inventory.favorited",
        actor=actor,
        before={},
        after={"match_id": str(match.id)},
        request=request,
    )
    return match


def archive_match(db: Session, match: SalesInventoryMatch, *, actor: User) -> SalesInventoryMatch:
    match.archived_at = _now()
    match.status = MatchStatus.ARCHIVED
    if match.is_primary:
        match.is_primary = False
    db.flush()
    return match


def create_shortlist(
    db: Session,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> SalesShortlist:
    lead_id = data.get("lead_id")
    opportunity_id = data.get("opportunity_id")
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)
    if lead_id:
        _get_lead_or_raise(db, lead_id)
    if opportunity_id:
        _get_opportunity_or_raise(db, opportunity_id)

    shortlist = SalesShortlist(
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        title=data["title"],
        description=data.get("description"),
        status=data.get("status", ShortlistStatus.DRAFT),
        created_by_user_id=actor.id,
    )
    db.add(shortlist)
    db.flush()

    entity_id = opportunity_id or lead_id
    log_entity_created(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY if opportunity_id else ActivityEntityType.LEAD,
        entity_id=entity_id,
        description_key="activity.sales.shortlist.created",
        actor=actor,
        metadata={"shortlist_id": str(shortlist.id), "title": shortlist.title},
        request=request,
    )
    return shortlist


def list_shortlists(
    db: Session,
    *,
    lead_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    include_archived: bool = False,
    user: User,
) -> list[dict[str, Any]]:
    _validate_context(lead_id=lead_id, opportunity_id=opportunity_id)
    query = select(SalesShortlist)
    if not include_archived:
        query = query.where(SalesShortlist.archived_at.is_(None))
    if lead_id:
        query = query.where(SalesShortlist.lead_id == lead_id)
    else:
        query = query.where(SalesShortlist.opportunity_id == opportunity_id)

    shortlists = list(db.scalars(query.order_by(desc(SalesShortlist.updated_at))).all())
    return [_enrich_shortlist(db, s, user=user) for s in shortlists]


def _enrich_shortlist(db: Session, shortlist: SalesShortlist, *, user: User) -> dict[str, Any]:
    items = list(
        db.scalars(
            select(SalesShortlistItem)
            .where(SalesShortlistItem.shortlist_id == shortlist.id)
            .order_by(SalesShortlistItem.sort_order)
        ).all()
    )
    return {
        "id": shortlist.id,
        "lead_id": shortlist.lead_id,
        "opportunity_id": shortlist.opportunity_id,
        "title": shortlist.title,
        "description": shortlist.description,
        "status": shortlist.status,
        "created_by_user_id": shortlist.created_by_user_id,
        "archived_at": shortlist.archived_at,
        "created_at": shortlist.created_at,
        "updated_at": shortlist.updated_at,
        "items": [_enrich_shortlist_item(db, item, user=user) for item in items],
    }


def _enrich_shortlist_item(db: Session, item: SalesShortlistItem, *, user: User) -> dict[str, Any]:
    asset = db.get(InventoryAsset, item.inventory_asset_id)
    pricing = enrich_asset_pricing_summary(db, asset, user=user) if asset else {}
    current = _build_inventory_snapshot(db, asset, user=user) if asset else {}
    is_stale, stale_fields = _detect_stale(item.inventory_snapshot, current)
    return {
        "id": item.id,
        "shortlist_id": item.shortlist_id,
        "inventory_asset_id": item.inventory_asset_id,
        "sort_order": item.sort_order,
        "notes": item.notes,
        "is_favorite": item.is_favorite,
        "inventory_snapshot": item.inventory_snapshot,
        "is_stale": is_stale,
        "stale_fields": stale_fields,
        "asset_display_id": asset.display_id if asset else None,
        "list_price": pricing.get("list_price"),
        "availability_status": asset.availability_status.value if asset else None,
    }


def add_shortlist_item(
    db: Session,
    shortlist: SalesShortlist,
    *,
    inventory_asset_id: UUID,
    notes: str | None,
    is_favorite: bool,
    actor: User,
    request: Request | None = None,
) -> SalesShortlistItem:
    if shortlist.archived_at is not None:
        raise InventoryMatchingError("sales.errors.shortlist_archived")

    asset = _get_asset_or_raise(db, inventory_asset_id)
    existing = db.scalar(
        select(SalesShortlistItem).where(
            SalesShortlistItem.shortlist_id == shortlist.id,
            SalesShortlistItem.inventory_asset_id == inventory_asset_id,
        )
    )
    if existing:
        raise InventoryMatchingError("sales.errors.shortlist_item_duplicate")

    max_order = db.scalar(
        select(func.coalesce(func.max(SalesShortlistItem.sort_order), -1)).where(
            SalesShortlistItem.shortlist_id == shortlist.id
        )
    )
    snapshot = _build_inventory_snapshot(db, asset, user=actor)
    item = SalesShortlistItem(
        shortlist_id=shortlist.id,
        inventory_asset_id=inventory_asset_id,
        sort_order=(max_order or -1) + 1,
        notes=notes,
        is_favorite=is_favorite,
        inventory_snapshot=snapshot,
    )
    db.add(item)
    db.flush()

    create_match(
        db,
        {
            "lead_id": shortlist.lead_id,
            "opportunity_id": shortlist.opportunity_id,
            "inventory_asset_id": inventory_asset_id,
            "relationship_type": MatchRelationshipType.SHORTLISTED,
            "match_source": MatchSource.MANUAL,
            "match_reason": f"Added to shortlist: {shortlist.title}",
        },
        actor=actor,
        request=request,
    )

    entity_id = shortlist.opportunity_id or shortlist.lead_id
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.SALES_OPPORTUNITY if shortlist.opportunity_id else ActivityEntityType.LEAD,
        entity_id=entity_id,
        description_key="activity.sales.inventory.shortlisted",
        actor=actor,
        before={},
        after={"shortlist_id": str(shortlist.id), "asset_id": str(inventory_asset_id)},
        request=request,
    )
    return item


def reorder_shortlist_items(
    db: Session,
    shortlist: SalesShortlist,
    item_ids: list[UUID],
    *,
    actor: User,
) -> list[SalesShortlistItem]:
    items = {
        item.id: item
        for item in db.scalars(
            select(SalesShortlistItem).where(SalesShortlistItem.shortlist_id == shortlist.id)
        ).all()
    }
    for order, item_id in enumerate(item_ids):
        if item_id not in items:
            raise InventoryMatchingError("sales.errors.shortlist_item_not_found", status_code=404)
        items[item_id].sort_order = order
    db.flush()
    return list(items.values())


def duplicate_shortlist(
    db: Session,
    shortlist: SalesShortlist,
    *,
    actor: User,
    request: Request | None = None,
) -> SalesShortlist:
    new_list = SalesShortlist(
        lead_id=shortlist.lead_id,
        opportunity_id=shortlist.opportunity_id,
        title=f"{shortlist.title} (copy)",
        description=shortlist.description,
        status=ShortlistStatus.DRAFT,
        created_by_user_id=actor.id,
    )
    db.add(new_list)
    db.flush()

    items = list(
        db.scalars(select(SalesShortlistItem).where(SalesShortlistItem.shortlist_id == shortlist.id)).all()
    )
    for item in items:
        db.add(
            SalesShortlistItem(
                shortlist_id=new_list.id,
                inventory_asset_id=item.inventory_asset_id,
                sort_order=item.sort_order,
                notes=item.notes,
                is_favorite=item.is_favorite,
                inventory_snapshot=item.inventory_snapshot,
            )
        )
    db.flush()
    return new_list


def archive_shortlist(db: Session, shortlist: SalesShortlist, *, actor: User) -> SalesShortlist:
    shortlist.archived_at = _now()
    shortlist.status = ShortlistStatus.ARCHIVED
    db.flush()
    return shortlist


def compare_assets(
    db: Session,
    asset_ids: list[UUID],
    *,
    user: User,
) -> list[dict[str, Any]]:
    if len(asset_ids) < 2 or len(asset_ids) > 5:
        raise InventoryMatchingError("sales.errors.compare_asset_count")

    items: list[dict[str, Any]] = []
    for asset_id in asset_ids:
        asset = _get_asset_or_raise(db, asset_id)
        pricing = enrich_asset_pricing_summary(db, asset, user=user)
        project = db.get(Project, asset.project_id)
        building = db.get(Building, asset.building_id) if asset.building_id else None
        floor = db.get(Floor, asset.floor_id) if asset.floor_id else None
        items.append(
            {
                "asset_id": asset.id,
                "display_id": asset.display_id,
                "system_code": asset.system_code,
                "asset_type": asset.asset_type.value,
                "usage_type": asset.usage_type.value,
                "bedrooms": asset.bedrooms,
                "bathrooms": asset.bathrooms,
                "interior_area_sqft": asset.interior_area_sqft,
                "availability_status": asset.availability_status.value,
                "reservation_status": asset.reservation_status.value,
                "sales_status": asset.sales_status.value,
                "list_price": pricing.get("list_price"),
                "currency": asset.currency,
                "project_name": project.project_name if project else None,
                "building_code": building.code if building else None,
                "floor_label": floor.display_name if floor else None,
            }
        )
    return items


def stale_check(
    db: Session,
    asset_ids: list[UUID],
    snapshots: dict[str, dict],
    *,
    user: User,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for asset_id in asset_ids:
        asset = db.get(InventoryAsset, asset_id)
        if asset is None or asset.archived_at is not None:
            continue
        current = _build_inventory_snapshot(db, asset, user=user)
        snapshot = snapshots.get(str(asset_id))
        is_stale, stale_fields = _detect_stale(snapshot, current)
        results.append(
            {
                "asset_id": asset_id,
                "is_stale": is_stale,
                "stale_fields": stale_fields,
                "current": current,
            }
        )
    return results


def create_soft_hold_from_sales(
    db: Session,
    *,
    inventory_asset_id: UUID,
    lead_id: UUID | None,
    opportunity_id: UUID | None,
    notes: str | None,
    deposit_amount: Decimal | None,
    actor: User,
    request: Request | None = None,
):
    asset = _get_asset_or_raise(db, inventory_asset_id)
    if opportunity_id:
        opp = _get_opportunity_or_raise(db, opportunity_id)
        if not lead_id and opp.lead_id:
            lead_id = opp.lead_id

    reservation = reservation_svc.create_soft_hold(
        db,
        asset_id=asset.id,
        investor_id=None,
        lead_id=lead_id,
        actor=actor,
        deposit_amount=deposit_amount,
        notes=notes,
        source=ReservationSource.SALES,
    )

    if opportunity_id:
        create_match(
            db,
            {
                "lead_id": None,
                "opportunity_id": opportunity_id,
                "inventory_asset_id": inventory_asset_id,
                "relationship_type": MatchRelationshipType.SOFT_HOLD,
                "match_reason": "Soft hold initiated from sales",
            },
            actor=actor,
            request=request,
        )

    entity_id = opportunity_id or lead_id
    if entity_id:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.SALES_OPPORTUNITY if opportunity_id else ActivityEntityType.LEAD,
            entity_id=entity_id,
            description_key="activity.sales.soft_hold.initiated",
            actor=actor,
            before={},
            after={"reservation_id": str(reservation.id)},
            request=request,
        )
    return reservation


def request_reservation_from_sales(
    db: Session,
    reservation_id: UUID,
    *,
    notes: str | None,
    deposit_amount: Decimal | None,
    actor: User,
    request: Request | None = None,
):
    from investhome_api.models.inventory import InventoryReservation

    reservation = db.get(InventoryReservation, reservation_id)
    if reservation is None:
        raise InventoryMatchingError("inventory.errors.reservation_not_found", status_code=404)

    updated = reservation_svc.request_reservation(
        db,
        reservation,
        actor=actor,
        notes=notes,
        deposit_amount=deposit_amount,
    )

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.INVENTORY_RESERVATION,
        entity_id=reservation_id,
        description_key="activity.sales.reservation.initiated",
        actor=actor,
        before={},
        after={"status": updated.status.value},
        request=request,
    )
    return updated


def build_matching_executive_summary(db: Session) -> dict[str, int]:
    open_opps = list(
        db.scalars(
            select(SalesOpportunity).where(
                SalesOpportunity.archived_at.is_(None),
                SalesOpportunity.stage.not_in(list(CLOSED_OPPORTUNITY_STAGES)),
            )
        ).all()
    )
    opp_ids = [o.id for o in open_opps]

    without_match = 0
    with_shortlist = 0
    primary_selected = 0
    for opp_id in opp_ids:
        active_matches = db.scalar(
            select(func.count()).select_from(SalesInventoryMatch).where(
                SalesInventoryMatch.opportunity_id == opp_id,
                SalesInventoryMatch.status == MatchStatus.ACTIVE,
            )
        ) or 0
        if active_matches == 0:
            without_match += 1
        shortlist_count = db.scalar(
            select(func.count()).select_from(SalesShortlist).where(
                SalesShortlist.opportunity_id == opp_id,
                SalesShortlist.archived_at.is_(None),
            )
        ) or 0
        if shortlist_count > 0:
            with_shortlist += 1
        primary = db.scalar(
            select(func.count()).select_from(SalesInventoryMatch).where(
                SalesInventoryMatch.opportunity_id == opp_id,
                SalesInventoryMatch.is_primary.is_(True),
            )
        ) or 0
        if primary > 0:
            primary_selected += 1

    shortlisted_unavailable = db.scalar(
        select(func.count()).select_from(SalesInventoryMatch).join(
            InventoryAsset, SalesInventoryMatch.inventory_asset_id == InventoryAsset.id
        ).where(
            SalesInventoryMatch.relationship_type == MatchRelationshipType.SHORTLISTED,
            SalesInventoryMatch.status == MatchStatus.ACTIVE,
            InventoryAsset.availability_status != AvailabilityStatus.AVAILABLE,
        )
    ) or 0

    match_to_reservation = db.scalar(
        select(func.count()).select_from(SalesInventoryMatch).where(
            SalesInventoryMatch.relationship_type.in_(
                [MatchRelationshipType.SOFT_HOLD, MatchRelationshipType.RESERVED]
            ),
            SalesInventoryMatch.status == MatchStatus.ACTIVE,
        )
    ) or 0

    return {
        "opportunities_without_match": without_match,
        "opportunities_with_shortlist": with_shortlist,
        "opportunities_primary_selected": primary_selected,
        "shortlisted_unavailable": shortlisted_unavailable,
        "match_to_reservation_count": match_to_reservation,
    }
