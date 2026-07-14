from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.schemas.lead import LeadCreate, LeadListResponse, LeadResponse, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])


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
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    query = select(Lead)

    if not include_archived:
        query = query.where(Lead.archived_at.is_(None))

    if status_filter is not None:
        query = query.where(Lead.status == status_filter)

    if source:
        query = query.where(Lead.source == source)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Lead.full_name.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.phone.ilike(pattern),
                Lead.interested_project.ilike(pattern),
            )
        )

    query = query.order_by(Lead.updated_at.desc())
    leads = db.scalars(query).all()

    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=len(leads),
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: UUID, db: Session = Depends(get_db)) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)
    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> LeadResponse:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    for field, value in updates.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", response_model=LeadResponse)
def archive_lead(lead_id: UUID, db: Session = Depends(get_db)) -> LeadResponse:
    lead = _get_lead_or_404(lead_id, db)

    if lead.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead is already archived")

    lead.archived_at = datetime.now(UTC)
    lead.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)
