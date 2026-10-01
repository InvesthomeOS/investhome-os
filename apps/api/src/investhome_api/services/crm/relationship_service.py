"""CRM Relationship CRUD and business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.project import Project
from investhome_api.models.crm_relationship import (
    CrmDecisionMapRole,
    CrmReferral,
    CrmRelationship,
    CrmRelationshipAlert,
    CrmRelationshipAlertStatus,
    CrmRelationshipAlertType,
    CrmRelationshipCategory,
    CrmRelationshipDirection,
    CrmRelationshipEntityType,
    CrmRelationshipReview,
    CrmRelationshipSavedView,
    CrmRelationshipStatus,
    CrmRelationshipStrength,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_relationships import (
    CrmDecisionMapRoleCreate,
    CrmDecisionMapRoleResponse,
    CrmDecisionMapResponse,
    CrmEntityRef,
    CrmReferralCreate,
    CrmReferralResponse,
    CrmRelationshipAlertResponse,
    CrmRelationshipBulkActionRequest,
    CrmRelationshipBulkActionResponse,
    CrmRelationshipCounts,
    CrmRelationshipCreate,
    CrmRelationshipDetail,
    CrmRelationshipDuplicateCandidate,
    CrmRelationshipIntelligenceDashboard,
    CrmRelationshipListResponse,
    CrmRelationshipRecommendation,
    CrmRelationshipReviewCreate,
    CrmRelationshipReviewResponse,
    CrmRelationshipSavedViewCreate,
    CrmRelationshipSavedViewResponse,
    CrmRelationshipSummary,
    CrmRelationshipUpdate,
)
from investhome_api.services.crm.reciprocal_mapping_service import (
    prevents_hierarchy_cycle,
    resolve_category,
    resolve_reciprocal_type,
    seed_type_configs,
)
from investhome_api.services.crm.relationship_score_service import (
    calculate_relationship_scores,
    apply_scores_to_relationship,
)
from investhome_api.services.permission_service import user_has_permission

CRM_RELATIONSHIP_ACTIVITY_FIELDS = [
    "relationship_type",
    "category",
    "status",
    "strength",
    "is_confidential",
    "source_entity_type",
    "target_entity_type",
]


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _resolve_display_name(
    db: Session,
    entity_type: CrmRelationshipEntityType,
    entity_id: UUID,
) -> str | None:
    if entity_type == CrmRelationshipEntityType.CONTACT:
        contact = db.get(CrmContact, entity_id)
        return contact.display_name if contact else None
    if entity_type == CrmRelationshipEntityType.COMPANY:
        company = db.get(CrmCompany, entity_id)
        return company.display_name if company else None
    if entity_type == CrmRelationshipEntityType.PROJECT:
        project = db.get(Project, entity_id)
        return project.project_name if project else None
    return None


def relationship_pair_kind(rel: CrmRelationship) -> str:
    source = rel.source_entity_type
    target = rel.target_entity_type
    types = {source, target}
    if types == {CrmRelationshipEntityType.CONTACT, CrmRelationshipEntityType.COMPANY}:
        return "contact_company"
    if types == {CrmRelationshipEntityType.CONTACT, CrmRelationshipEntityType.PROJECT}:
        return "contact_project"
    if source == CrmRelationshipEntityType.CONTACT and target == CrmRelationshipEntityType.CONTACT:
        return "contact_contact"
    if types == {CrmRelationshipEntityType.COMPANY, CrmRelationshipEntityType.PROJECT}:
        return "company_project"
    if source == CrmRelationshipEntityType.COMPANY and target == CrmRelationshipEntityType.COMPANY:
        return "company_company"
    return "other"


def _pair_kind_clause(pair_kind: str):
    contact = CrmRelationshipEntityType.CONTACT
    company = CrmRelationshipEntityType.COMPANY
    project = CrmRelationshipEntityType.PROJECT
    if pair_kind == "contact_company":
        return or_(
            (CrmRelationship.source_entity_type == contact) & (CrmRelationship.target_entity_type == company),
            (CrmRelationship.source_entity_type == company) & (CrmRelationship.target_entity_type == contact),
        )
    if pair_kind == "contact_project":
        return or_(
            (CrmRelationship.source_entity_type == contact) & (CrmRelationship.target_entity_type == project),
            (CrmRelationship.source_entity_type == project) & (CrmRelationship.target_entity_type == contact),
        )
    if pair_kind == "contact_contact":
        return (CrmRelationship.source_entity_type == contact) & (CrmRelationship.target_entity_type == contact)
    if pair_kind == "company_project":
        return or_(
            (CrmRelationship.source_entity_type == company) & (CrmRelationship.target_entity_type == project),
            (CrmRelationship.source_entity_type == project) & (CrmRelationship.target_entity_type == company),
        )
    if pair_kind == "company_company":
        return (CrmRelationship.source_entity_type == company) & (CrmRelationship.target_entity_type == company)
    return None


def _project_ids_for_group(db: Session, project_group: str) -> list[UUID]:
    return list(
        db.scalars(
            select(CrmAgreement.project_id).where(
                CrmAgreement.project_group == project_group,
                CrmAgreement.project_id.is_not(None),
            ).distinct()
        ).all()
    )


def _linked_project(db: Session, rel: CrmRelationship) -> tuple[UUID | None, str | None]:
    if rel.source_entity_type == CrmRelationshipEntityType.PROJECT:
        project = db.get(Project, rel.source_entity_id)
        return rel.source_entity_id, project.project_name if project else None
    if rel.target_entity_type == CrmRelationshipEntityType.PROJECT:
        project = db.get(Project, rel.target_entity_id)
        return rel.target_entity_id, project.project_name if project else None
    return None, None


def _linked_agreement(db: Session, rel: CrmRelationship) -> tuple[UUID | None, str | None]:
    contact_id = None
    project_id = None
    if rel.source_entity_type == CrmRelationshipEntityType.CONTACT:
        contact_id = rel.source_entity_id
    elif rel.target_entity_type == CrmRelationshipEntityType.CONTACT:
        contact_id = rel.target_entity_id
    if rel.source_entity_type == CrmRelationshipEntityType.PROJECT:
        project_id = rel.source_entity_id
    elif rel.target_entity_type == CrmRelationshipEntityType.PROJECT:
        project_id = rel.target_entity_id
    if not contact_id or not project_id:
        return None, None
    agreements = list(
        db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.contact_id == contact_id,
                CrmAgreement.project_id == project_id,
            )
        ).all()
    )
    if len(agreements) != 1:
        return None, None
    agreement = agreements[0]
    label = agreement.unit_number or agreement.project_group
    return agreement.id, label


def serialize_relationship_summary(db: Session, rel: CrmRelationship) -> CrmRelationshipSummary:
    reciprocal_label = None
    if rel.reciprocal_type:
        from investhome_api.services.crm.reciprocal_mapping_service import get_reciprocal_display_label
        reciprocal_label = get_reciprocal_display_label(db, rel.relationship_type)

    owner_name = None
    if rel.owner_user_id:
        owner = db.get(User, rel.owner_user_id)
        owner_name = owner.full_name if owner else None

    linked_project_id, linked_project_label = _linked_project(db, rel)
    linked_agreement_id, linked_agreement_label = _linked_agreement(db, rel)

    return CrmRelationshipSummary(
        id=rel.id,
        source_entity_type=rel.source_entity_type.value,
        source_entity_id=rel.source_entity_id,
        target_entity_type=rel.target_entity_type.value,
        target_entity_id=rel.target_entity_id,
        source_display_name=_resolve_display_name(db, rel.source_entity_type, rel.source_entity_id),
        target_display_name=_resolve_display_name(db, rel.target_entity_type, rel.target_entity_id),
        relationship_type=rel.relationship_type,
        reciprocal_type=rel.reciprocal_type,
        reciprocal_label=reciprocal_label,
        category=rel.category.value,
        status=rel.status.value,
        strength=rel.strength.value,
        direction=rel.direction.value,
        relationship_score=rel.relationship_score,
        engagement_score=rel.engagement_score,
        influence_score=rel.influence_score,
        trust_score=rel.trust_score,
        business_value_score=rel.business_value_score,
        risk_score=rel.risk_score,
        is_confidential=rel.is_confidential,
        is_verified=rel.is_verified,
        owner_user_id=rel.owner_user_id,
        owner_name=owner_name,
        last_interaction_at=rel.last_interaction_at,
        notes=rel.notes,
        pair_kind=relationship_pair_kind(rel),
        linked_project_id=linked_project_id,
        linked_project_label=linked_project_label,
        linked_agreement_id=linked_agreement_id,
        linked_agreement_label=linked_agreement_label,
        archived_at=rel.archived_at,
        created_at=rel.created_at,
        updated_at=rel.updated_at,
    )


def serialize_relationship_detail(db: Session, rel: CrmRelationship) -> CrmRelationshipDetail:
    summary = serialize_relationship_summary(db, rel)
    return CrmRelationshipDetail(
        **summary.model_dump(),
        metadata_json=rel.metadata_json,
        started_at=rel.started_at,
        ended_at=rel.ended_at,
    )


def strip_confidential_fields(rel: CrmRelationshipDetail, can_view: bool) -> CrmRelationshipDetail:
    if can_view or not rel.is_confidential:
        return rel
    return rel.model_copy(update={"notes": None, "metadata_json": None})


def strip_referral_compensation(referral: CrmReferralResponse, can_view: bool) -> CrmReferralResponse:
    if can_view:
        return referral
    return referral.model_copy(
        update={
            "compensation_amount": None,
            "compensation_currency": None,
            "compensation_status": None,
        }
    )


def get_relationship_or_404(db: Session, relationship_id: UUID) -> CrmRelationship:
    rel = db.get(CrmRelationship, relationship_id)
    if not rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
    return rel


def _validate_endpoints(payload: CrmRelationshipCreate) -> None:
    if (
        payload.source_entity_type == payload.target_entity_type
        and payload.source_entity_id == payload.target_entity_id
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Self-relationship not allowed")


def _check_hierarchy_cycle(
    db: Session,
    source_type: CrmRelationshipEntityType,
    source_id: UUID,
    target_type: CrmRelationshipEntityType,
    target_id: UUID,
    relationship_type: str,
) -> None:
    if not prevents_hierarchy_cycle(db, relationship_type):
        return
    if source_type != target_type:
        return

    visited: set[tuple[str, UUID]] = set()
    stack = [(target_type, target_id)]

    while stack:
        current_type, current_id = stack.pop()
        key = (current_type.value, current_id)
        if key in visited:
            continue
        visited.add(key)
        if current_type == source_type and current_id == source_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Hierarchy cycle detected",
            )
        rels = db.scalars(
            select(CrmRelationship).where(
                CrmRelationship.archived_at.is_(None),
                CrmRelationship.relationship_type.in_(["parent", "subsidiary"]),
                or_(
                    (CrmRelationship.source_entity_type == current_type)
                    & (CrmRelationship.source_entity_id == current_id),
                    (CrmRelationship.target_entity_type == current_type)
                    & (CrmRelationship.target_entity_id == current_id),
                ),
            )
        ).all()
        for rel in rels:
            if rel.source_entity_id == current_id and rel.source_entity_type == current_type:
                stack.append((rel.target_entity_type, rel.target_entity_id))
            else:
                stack.append((rel.source_entity_type, rel.source_entity_id))


def find_duplicate_candidates(
    db: Session,
    payload: CrmRelationshipCreate,
) -> list[CrmRelationshipDuplicateCandidate]:
    existing = db.scalars(
        select(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.source_entity_type == CrmRelationshipEntityType(payload.source_entity_type.value),
            CrmRelationship.source_entity_id == payload.source_entity_id,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType(payload.target_entity_type.value),
            CrmRelationship.target_entity_id == payload.target_entity_id,
            CrmRelationship.relationship_type == payload.relationship_type,
        )
    ).all()
    return [
        CrmRelationshipDuplicateCandidate(
            existing_id=rel.id,
            relationship_type=rel.relationship_type,
            source_entity_type=rel.source_entity_type.value,
            source_entity_id=rel.source_entity_id,
            target_entity_type=rel.target_entity_type.value,
            target_entity_id=rel.target_entity_id,
            match_score=1.0,
        )
        for rel in existing
    ]


def create_relationship(db: Session, payload: CrmRelationshipCreate, user: User | None) -> CrmRelationship:
    seed_type_configs(db)
    _validate_endpoints(payload)
    duplicates = find_duplicate_candidates(db, payload)
    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate relationship exists",
        )

    reciprocal_type, _ = resolve_reciprocal_type(db, payload.relationship_type)
    if payload.category is not None:
        category_value = payload.category.value if hasattr(payload.category, "value") else payload.category
        category = CrmRelationshipCategory(category_value)
    else:
        category = resolve_category(db, payload.relationship_type)

    _check_hierarchy_cycle(
        db,
        CrmRelationshipEntityType(payload.source_entity_type.value),
        payload.source_entity_id,
        CrmRelationshipEntityType(payload.target_entity_type.value),
        payload.target_entity_id,
        payload.relationship_type,
    )

    status_value = payload.status.value if hasattr(payload.status, "value") else payload.status
    strength_value = payload.strength.value if hasattr(payload.strength, "value") else payload.strength
    direction_value = payload.direction.value if hasattr(payload.direction, "value") else payload.direction

    rel = CrmRelationship(
        source_entity_type=CrmRelationshipEntityType(payload.source_entity_type.value),
        source_entity_id=payload.source_entity_id,
        target_entity_type=CrmRelationshipEntityType(payload.target_entity_type.value),
        target_entity_id=payload.target_entity_id,
        relationship_type=payload.relationship_type,
        reciprocal_type=reciprocal_type,
        category=category,
        status=CrmRelationshipStatus(status_value),
        strength=CrmRelationshipStrength(strength_value),
        direction=CrmRelationshipDirection(direction_value),
        is_confidential=payload.is_confidential,
        is_verified=payload.is_verified,
        notes=payload.notes,
        metadata_json=payload.metadata_json,
        started_at=payload.started_at,
        owner_user_id=payload.owner_user_id or (user.id if user else None),
    )
    db.add(rel)
    db.flush()

    breakdown = calculate_relationship_scores(db, rel)
    apply_scores_to_relationship(db, rel, breakdown)
    return rel


def update_relationship(
    db: Session,
    rel: CrmRelationship,
    payload: CrmRelationshipUpdate,
) -> CrmRelationship:
    data = payload.model_dump(exclude_unset=True)
    if "relationship_type" in data:
        reciprocal_type, _ = resolve_reciprocal_type(db, data["relationship_type"])
        rel.reciprocal_type = reciprocal_type
        rel.category = resolve_category(db, data["relationship_type"])
        _check_hierarchy_cycle(
            db,
            rel.source_entity_type,
            rel.source_entity_id,
            rel.target_entity_type,
            rel.target_entity_id,
            data["relationship_type"],
        )
    for key, value in data.items():
        if hasattr(value, "value"):
            value = value.value
        setattr(rel, key, value)

    breakdown = calculate_relationship_scores(db, rel)
    apply_scores_to_relationship(db, rel, breakdown)
    return rel


def list_relationships(
    db: Session,
    *,
    search: str | None = None,
    status_filter: str | None = None,
    category: str | None = None,
    relationship_type: str | None = None,
    pair_kind: str | None = None,
    owner_user_id: UUID | None = None,
    project_group: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    include_archived: bool = False,
    include_confidential: bool = True,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> CrmRelationshipListResponse:
    query = select(CrmRelationship)
    if not include_archived:
        query = query.where(CrmRelationship.archived_at.is_(None))
    if not include_confidential:
        query = query.where(CrmRelationship.is_confidential.is_(False))
    if status_filter:
        query = query.where(CrmRelationship.status == status_filter)
    if category:
        query = query.where(CrmRelationship.category == category)
    if relationship_type:
        query = query.where(CrmRelationship.relationship_type == relationship_type)
    pair_clause = _pair_kind_clause(pair_kind) if pair_kind else None
    if pair_clause is not None:
        query = query.where(pair_clause)
    if owner_user_id:
        query = query.where(CrmRelationship.owner_user_id == owner_user_id)
    if project_group:
        project_ids = _project_ids_for_group(db, project_group)
        query = query.where(
            or_(
                (CrmRelationship.source_entity_type == CrmRelationshipEntityType.PROJECT)
                & CrmRelationship.source_entity_id.in_(project_ids),
                (CrmRelationship.target_entity_type == CrmRelationshipEntityType.PROJECT)
                & CrmRelationship.target_entity_id.in_(project_ids),
            )
        )
    if entity_type and entity_id:
        et = CrmRelationshipEntityType(entity_type)
        query = query.where(
            or_(
                (CrmRelationship.source_entity_type == et) & (CrmRelationship.source_entity_id == entity_id),
                (CrmRelationship.target_entity_type == et) & (CrmRelationship.target_entity_id == entity_id),
            )
        )
    if search:
        like = f"%{search.strip()}%"
        contact_ids = select(CrmContact.id).where(CrmContact.display_name.ilike(like))
        company_ids = select(CrmCompany.id).where(
            or_(CrmCompany.display_name.ilike(like), CrmCompany.legal_name.ilike(like))
        )
        project_ids = select(Project.id).where(
            or_(Project.project_name.ilike(like), Project.project_code.ilike(like))
        )
        query = query.where(
            or_(
                CrmRelationship.relationship_type.ilike(like),
                CrmRelationship.notes.ilike(like),
                (CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT)
                & CrmRelationship.source_entity_id.in_(contact_ids),
                (CrmRelationship.target_entity_type == CrmRelationshipEntityType.CONTACT)
                & CrmRelationship.target_entity_id.in_(contact_ids),
                (CrmRelationship.source_entity_type == CrmRelationshipEntityType.COMPANY)
                & CrmRelationship.source_entity_id.in_(company_ids),
                (CrmRelationship.target_entity_type == CrmRelationshipEntityType.COMPANY)
                & CrmRelationship.target_entity_id.in_(company_ids),
                (CrmRelationship.source_entity_type == CrmRelationshipEntityType.PROJECT)
                & CrmRelationship.source_entity_id.in_(project_ids),
                (CrmRelationship.target_entity_type == CrmRelationshipEntityType.PROJECT)
                & CrmRelationship.target_entity_id.in_(project_ids),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_col = getattr(CrmRelationship, sort_by, CrmRelationship.updated_at)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = [serialize_relationship_summary(db, rel) for rel in db.scalars(query).all()]
    return CrmRelationshipListResponse(items=items, total=total, page=page, page_size=page_size)


def relationship_workspace_counts(db: Session, *, include_archived: bool = False) -> CrmRelationshipCounts:
    query = select(CrmRelationship)
    if not include_archived:
        query = query.where(CrmRelationship.archived_at.is_(None))
    counts = CrmRelationshipCounts()
    for rel in db.scalars(query).all():
        counts.total += 1
        kind = relationship_pair_kind(rel)
        if kind == "contact_company":
            counts.contact_company += 1
        elif kind == "contact_project":
            counts.contact_project += 1
        elif kind == "contact_contact":
            counts.contact_contact += 1
        elif kind == "company_project":
            counts.company_project += 1
        elif kind == "company_company":
            counts.company_company += 1
    return counts


def archive_relationship(db: Session, rel: CrmRelationship) -> CrmRelationship:
    rel.archived_at = datetime.now(UTC)
    rel.status = CrmRelationshipStatus.ARCHIVED
    return rel


def restore_relationship(db: Session, rel: CrmRelationship) -> CrmRelationship:
    rel.archived_at = None
    rel.status = CrmRelationshipStatus.ACTIVE
    return rel


def delete_relationship(db: Session, rel: CrmRelationship) -> None:
    db.delete(rel)


def bulk_action(db: Session, request: CrmRelationshipBulkActionRequest) -> CrmRelationshipBulkActionResponse:
    updated = 0
    failed = 0
    for rel_id in request.relationship_ids:
        rel = db.get(CrmRelationship, rel_id)
        if not rel:
            failed += 1
            continue
        if request.action == "archive":
            archive_relationship(db, rel)
        elif request.action == "restore":
            restore_relationship(db, rel)
        elif request.action == "update" and request.payload:
            update_relationship(db, rel, CrmRelationshipUpdate(**request.payload))
        else:
            failed += 1
            continue
        updated += 1
    return CrmRelationshipBulkActionResponse(updated=updated, failed=failed)


def export_relationships_csv(db: Session, include_confidential: bool = False) -> str:
    result = list_relationships(
        db,
        include_archived=False,
        include_confidential=include_confidential,
        page=1,
        page_size=10000,
    )
    lines = [
        "id,source_type,source_id,target_type,target_id,relationship_type,category,status,strength,score"
    ]
    for item in result.items:
        lines.append(
            f"{item.id},{item.source_entity_type},{item.source_entity_id},"
            f"{item.target_entity_type},{item.target_entity_id},{item.relationship_type},"
            f"{item.category},{item.status},{item.strength},{item.relationship_score}"
        )
    return "\n".join(lines)


def list_alerts(db: Session, *, status_filter: str | None = None) -> list[CrmRelationshipAlertResponse]:
    query = select(CrmRelationshipAlert)
    if status_filter:
        query = query.where(CrmRelationshipAlert.status == status_filter)
    query = query.order_by(CrmRelationshipAlert.created_at.desc()).limit(100)
    return [
        CrmRelationshipAlertResponse(
            id=a.id,
            relationship_id=a.relationship_id,
            entity_type=a.entity_type.value if a.entity_type else None,
            entity_id=a.entity_id,
            alert_type=a.alert_type.value,
            severity=a.severity,
            message=a.message,
            status=a.status.value,
            created_at=a.created_at,
            resolved_at=a.resolved_at,
        )
        for a in db.scalars(query).all()
    ]


def update_alert_status(db: Session, alert_id: UUID, new_status: str) -> CrmRelationshipAlertResponse:
    alert = db.get(CrmRelationshipAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = CrmRelationshipAlertStatus(new_status)
    if new_status in ("resolved", "dismissed"):
        alert.resolved_at = datetime.now(UTC)
    return CrmRelationshipAlertResponse(
        id=alert.id,
        relationship_id=alert.relationship_id,
        entity_type=alert.entity_type.value if alert.entity_type else None,
        entity_id=alert.entity_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity,
        message=alert.message,
        status=alert.status.value,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )


def get_recommendations(db: Session) -> list[CrmRelationshipRecommendation]:
    recs: list[CrmRelationshipRecommendation] = []
    stale_rels = db.scalars(
        select(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.engagement_score < 40,
        ).order_by(CrmRelationship.engagement_score.asc()).limit(5)
    ).all()
    for rel in stale_rels:
        recs.append(
            CrmRelationshipRecommendation(
                id=f"stale-{rel.id}",
                title="Re-engage stale relationship",
                description=f"Low engagement score ({rel.engagement_score}) for {rel.relationship_type} link",
                priority="medium",
                relationship_id=rel.id,
                reason=f"engagement_score={rel.engagement_score} below threshold 40",
            )
        )
    at_risk = db.scalars(
        select(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.risk_score > 60,
        ).order_by(CrmRelationship.risk_score.desc()).limit(5)
    ).all()
    for rel in at_risk:
        recs.append(
            CrmRelationshipRecommendation(
                id=f"risk-{rel.id}",
                title="Address at-risk relationship",
                description=f"High risk score ({rel.risk_score}) detected",
                priority="high",
                relationship_id=rel.id,
                reason=f"risk_score={rel.risk_score} above threshold 60",
            )
        )
    return recs


def build_intelligence_dashboard(db: Session) -> CrmRelationshipIntelligenceDashboard:
    total = db.scalar(
        select(func.count()).select_from(CrmRelationship).where(CrmRelationship.archived_at.is_(None))
    ) or 0
    if total == 0:
        return CrmRelationshipIntelligenceDashboard()

    active = db.scalar(
        select(func.count()).select_from(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.status == CrmRelationshipStatus.ACTIVE,
        )
    ) or 0
    avg_score = db.scalar(
        select(func.avg(CrmRelationship.relationship_score)).where(CrmRelationship.archived_at.is_(None))
    ) or 0.0
    at_risk = db.scalar(
        select(func.count()).select_from(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.risk_score > 60,
        )
    ) or 0
    stale = db.scalar(
        select(func.count()).select_from(CrmRelationship).where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.engagement_score < 40,
        )
    ) or 0
    open_alerts = db.scalar(
        select(func.count()).select_from(CrmRelationshipAlert).where(
            CrmRelationshipAlert.status == CrmRelationshipAlertStatus.OPEN,
        )
    ) or 0

    top_influencers: list[CrmEntityRef] = []
    top_rels = db.scalars(
        select(CrmRelationship).where(CrmRelationship.archived_at.is_(None))
        .order_by(CrmRelationship.influence_score.desc()).limit(5)
    ).all()
    seen: set[str] = set()
    for rel in top_rels:
        for et, eid in (
            (rel.source_entity_type, rel.source_entity_id),
            (rel.target_entity_type, rel.target_entity_id),
        ):
            key = f"{et.value}:{eid}"
            if key in seen:
                continue
            seen.add(key)
            top_influencers.append(
                CrmEntityRef(
                    entity_type=et.value,
                    entity_id=eid,
                    display_name=_resolve_display_name(db, et, eid),
                )
            )

    score_distribution = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    all_rels = db.scalars(
        select(CrmRelationship.relationship_score).where(CrmRelationship.archived_at.is_(None))
    ).all()
    for score in all_rels:
        if score <= 25:
            score_distribution["0-25"] += 1
        elif score <= 50:
            score_distribution["26-50"] += 1
        elif score <= 75:
            score_distribution["51-75"] += 1
        else:
            score_distribution["76-100"] += 1

    category_breakdown: dict[str, int] = {}
    cat_rows = db.execute(
        select(CrmRelationship.category, func.count())
        .where(CrmRelationship.archived_at.is_(None))
        .group_by(CrmRelationship.category)
    ).all()
    for cat, count in cat_rows:
        category_breakdown[cat.value if hasattr(cat, "value") else str(cat)] = count

    return CrmRelationshipIntelligenceDashboard(
        total_relationships=total,
        active_relationships=active,
        average_score=round(float(avg_score), 1),
        at_risk_count=at_risk,
        stale_count=stale,
        top_influencers=top_influencers[:5],
        score_distribution=score_distribution,
        category_breakdown=category_breakdown,
        open_alerts=open_alerts,
    )


def get_decision_map(db: Session, company_id: UUID) -> CrmDecisionMapResponse:
    roles = db.scalars(
        select(CrmDecisionMapRole).where(CrmDecisionMapRole.company_id == company_id)
    ).all()
    return CrmDecisionMapResponse(
        company_id=company_id,
        roles=[
            CrmDecisionMapRoleResponse(
                id=r.id,
                company_id=r.company_id,
                contact_id=r.contact_id,
                contact_display_name=_resolve_display_name(
                    db, CrmRelationshipEntityType.CONTACT, r.contact_id
                ),
                role_type=_enum_value(r.role_type),
                influence_level=r.influence_level,
                notes=r.notes,
            )
            for r in roles
        ],
    )


def upsert_decision_map_role(
    db: Session,
    company_id: UUID,
    payload: CrmDecisionMapRoleCreate,
) -> CrmDecisionMapRoleResponse:
    existing = db.scalar(
        select(CrmDecisionMapRole).where(
            CrmDecisionMapRole.company_id == company_id,
            CrmDecisionMapRole.contact_id == payload.contact_id,
            CrmDecisionMapRole.role_type == payload.role_type,
        )
    )
    if existing:
        existing.influence_level = payload.influence_level
        existing.notes = payload.notes
        role = existing
    else:
        role = CrmDecisionMapRole(
            company_id=company_id,
            contact_id=payload.contact_id,
            role_type=payload.role_type,
            influence_level=payload.influence_level,
            notes=payload.notes,
        )
        db.add(role)
    db.flush()
    return CrmDecisionMapRoleResponse(
        id=role.id,
        company_id=role.company_id,
        contact_id=role.contact_id,
        contact_display_name=_resolve_display_name(
            db, CrmRelationshipEntityType.CONTACT, role.contact_id
        ),
        role_type=_enum_value(role.role_type),
        influence_level=role.influence_level,
        notes=role.notes,
    )


def create_referral(db: Session, payload: CrmReferralCreate) -> CrmReferral:
    referral = CrmReferral(
        referrer_entity_type=CrmRelationshipEntityType(payload.referrer_entity_type.value),
        referrer_entity_id=payload.referrer_entity_id,
        referred_entity_type=CrmRelationshipEntityType(payload.referred_entity_type.value),
        referred_entity_id=payload.referred_entity_id,
        relationship_id=payload.relationship_id,
        status=payload.status.value,
        compensation_amount=payload.compensation_amount,
        compensation_currency=payload.compensation_currency,
        compensation_status=payload.compensation_status,
        notes=payload.notes,
    )
    db.add(referral)
    db.flush()
    return referral


def serialize_referral(db: Session, referral: CrmReferral) -> CrmReferralResponse:
    return CrmReferralResponse(
        id=referral.id,
        referrer_entity_type=referral.referrer_entity_type.value,
        referrer_entity_id=referral.referrer_entity_id,
        referred_entity_type=referral.referred_entity_type.value,
        referred_entity_id=referral.referred_entity_id,
        referrer_display_name=_resolve_display_name(
            db, referral.referrer_entity_type, referral.referrer_entity_id
        ),
        referred_display_name=_resolve_display_name(
            db, referral.referred_entity_type, referral.referred_entity_id
        ),
        relationship_id=referral.relationship_id,
        status=referral.status.value,
        compensation_amount=referral.compensation_amount,
        compensation_currency=referral.compensation_currency,
        compensation_status=referral.compensation_status,
        notes=referral.notes,
        created_at=referral.created_at,
        updated_at=referral.updated_at,
    )


def list_referrals(db: Session) -> list[CrmReferralResponse]:
    referrals = db.scalars(select(CrmReferral).order_by(CrmReferral.created_at.desc()).limit(100)).all()
    return [serialize_referral(db, r) for r in referrals]


def create_review(db: Session, payload: CrmRelationshipReviewCreate) -> CrmRelationshipReview:
    review = CrmRelationshipReview(
        relationship_id=payload.relationship_id,
        review_date=payload.review_date,
        status=payload.status.value,
        notes=payload.notes,
    )
    db.add(review)
    db.flush()
    return review


def list_reviews(db: Session, relationship_id: UUID | None = None) -> list[CrmRelationshipReviewResponse]:
    query = select(CrmRelationshipReview)
    if relationship_id:
        query = query.where(CrmRelationshipReview.relationship_id == relationship_id)
    query = query.order_by(CrmRelationshipReview.review_date.desc()).limit(50)
    return [
        CrmRelationshipReviewResponse(
            id=r.id,
            relationship_id=r.relationship_id,
            reviewer_user_id=r.reviewer_user_id,
            review_date=r.review_date,
            status=r.status.value,
            notes=r.notes,
            scores_snapshot=r.scores_snapshot,
            created_at=r.created_at,
        )
        for r in db.scalars(query).all()
    ]


def list_saved_views(db: Session, user_id: UUID) -> list[CrmRelationshipSavedViewResponse]:
    views = db.scalars(
        select(CrmRelationshipSavedView).where(CrmRelationshipSavedView.user_id == user_id)
    ).all()
    return [
        CrmRelationshipSavedViewResponse(id=v.id, name=v.name, filters=v.filters, is_default=v.is_default)
        for v in views
    ]


def create_saved_view(
    db: Session,
    user_id: UUID,
    payload: CrmRelationshipSavedViewCreate,
) -> CrmRelationshipSavedViewResponse:
    if payload.is_default:
        existing_defaults = db.scalars(
            select(CrmRelationshipSavedView).where(
                CrmRelationshipSavedView.user_id == user_id,
                CrmRelationshipSavedView.is_default.is_(True),
            )
        ).all()
        for view in existing_defaults:
            view.is_default = False
    view = CrmRelationshipSavedView(
        user_id=user_id,
        name=payload.name,
        filters=payload.filters,
        is_default=payload.is_default,
    )
    db.add(view)
    db.flush()
    return CrmRelationshipSavedViewResponse(
        id=view.id, name=view.name, filters=view.filters, is_default=view.is_default
    )


def can_view_confidential(user: User | None) -> bool:
    if not user:
        return False
    return user_has_permission(user, "crm", "view_relationship_confidential")


def can_view_referral_compensation(user: User | None) -> bool:
    if not user:
        return False
    return user_has_permission(user, "crm", "view_referral_compensation")
