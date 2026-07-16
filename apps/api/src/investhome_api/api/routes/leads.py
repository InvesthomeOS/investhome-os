from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.lead_qualification import LeadQualification, QualificationStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.lead import LeadCreate, LeadListResponse, LeadResponse, LeadUpdate
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity

router = APIRouter(prefix="/leads", tags=["leads"])

LEAD_ACTIVITY_FIELDS = [
    "full_name",
    "email",
    "phone",
    "country",
    "source",
    "status",
    "assigned_to",
    "estimated_budget",
    "interested_project",
    "notes",
]


def _get_lead_or_404(lead_id: UUID, db: Session, *, include_archived: bool = False) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or (lead.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.get("", response_model=LeadListResponse)
def list_leads(
    search: str | None = Query(default=None, max_length=255),
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    source: str | None = Query(default=None, max_length=100),
    qualification_status: QualificationStatus | None = Query(default=None),
    preferred_market: str | None = Query(default=None, max_length=100),
    lead_score_min: int | None = Query(default=None, ge=0, le=100),
    lead_score_max: int | None = Query(default=None, ge=0, le=100),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("leads", "view")),
) -> LeadListResponse:
    query = select(Lead)

    if not include_archived:
        query = query.where(Lead.archived_at.is_(None))

    if status_filter is not None:
        query = query.where(Lead.status == status_filter)

    if source:
        query = query.where(Lead.source == source)

    if preferred_market:
        query = query.where(Lead.preferred_market == preferred_market)

    if lead_score_min is not None:
        query = query.where(Lead.cached_lead_score >= lead_score_min)

    if lead_score_max is not None:
        query = query.where(Lead.cached_lead_score <= lead_score_max)

    if qualification_status is not None:
        query = query.join(LeadQualification, LeadQualification.lead_id == Lead.id).where(
            LeadQualification.qualification_status == qualification_status
        )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Lead.full_name.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.phone.ilike(pattern),
                Lead.interested_project.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.preferred_market.ilike(pattern),
            )
        )

    query = query.order_by(Lead.updated_at.desc())
    leads = db.scalars(query).all()

    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=len(leads),
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("leads", "view")),
) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)
    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("leads", "create")),
) -> LeadResponse:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.flush()
    log_entity_created(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key="activity.lead.created",
        actor=actor,
        metadata={"name": lead.full_name, "status": lead.status.value},
        request=request,
        is_demo=lead.is_demo,
    )
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("leads", "update")),
) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    before = snapshot_entity(lead, LEAD_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key="activity.lead.updated",
        actor=actor,
        before=before,
        after=snapshot_entity(lead, LEAD_ACTIVITY_FIELDS),
        metadata={"name": lead.full_name},
        request=request,
        is_demo=lead.is_demo,
    )
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", response_model=LeadResponse)
def archive_lead(
    lead_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("leads", "archive")),
) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)

    if lead.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead is already archived")

    lead.archived_at = datetime.now(UTC)
    lead.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key="activity.lead.archived",
        actor=actor,
        metadata={"name": lead.full_name},
        request=request,
        is_demo=lead.is_demo,
    )
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)
