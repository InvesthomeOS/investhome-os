"""CRM leads workspace routes — prefix /crm/leads. Does not replace /leads."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_leads import (
    CrmLeadConvertRequest,
    CrmLeadConvertResponse,
    CrmLeadCreate,
    CrmLeadDetail,
    CrmLeadIngestRequest,
    CrmLeadListResponse,
    CrmLeadStageUpdate,
    CrmLeadUpdate,
)
from investhome_api.services.crm.crm_lead_service import (
    LeadConflictError,
    LeadNotFoundError,
    LeadValidationError,
    convert_crm_lead,
    create_crm_lead,
    get_crm_lead,
    ingest_crm_lead,
    list_crm_leads,
    move_crm_lead_stage,
    update_crm_lead,
)

router = APIRouter(prefix="/crm/leads", tags=["crm-leads"])


def _conflict(exc: LeadConflictError) -> JSONResponse:
    body = exc.body.model_dump(mode="json")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "detail": body["message"],
            "error": {"code": body["code"], "message": body["message"]},
            "matches": body["matches"],
        },
    )


@router.get("", response_model=CrmLeadListResponse)
def list_leads_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
    search: str | None = Query(default=None, max_length=255),
    stage: str | None = Query(default=None, max_length=40),
    source: str | None = Query(default=None, max_length=100),
    project: str | None = Query(default=None, max_length=255),
    owner_id: UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    ingest_status: str | None = Query(default=None, max_length=20),
) -> CrmLeadListResponse:
    del user
    return list_crm_leads(
        db,
        search=search,
        stage=stage,
        source=source,
        project=project,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
        ingest_status=ingest_status,
    )


@router.post("/ingest", response_model=CrmLeadDetail, status_code=status.HTTP_201_CREATED)
def ingest_lead_workspace(
    payload: CrmLeadIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmLeadDetail:
    """Store a future Meta/Google/website lead. Providers are not connected."""
    try:
        lead = ingest_crm_lead(db, payload, actor=user)
        db.commit()
        return lead
    except LeadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{lead_id}", response_model=CrmLeadDetail)
def get_lead_workspace(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmLeadDetail:
    del user
    try:
        return get_crm_lead(db, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı") from exc


@router.post("", response_model=CrmLeadDetail, status_code=status.HTTP_201_CREATED)
def create_lead_workspace(
    payload: CrmLeadCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
    confirm: bool = Query(default=False),
) -> CrmLeadDetail | JSONResponse:
    try:
        lead = create_crm_lead(db, payload, actor=user, confirm=confirm)
        db.commit()
        return lead
    except LeadConflictError as exc:
        db.rollback()
        return _conflict(exc)
    except LeadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{lead_id}", response_model=CrmLeadDetail)
def update_lead_workspace(
    lead_id: UUID,
    payload: CrmLeadUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmLeadDetail:
    try:
        lead = update_crm_lead(db, lead_id, payload, actor=user)
        db.commit()
        return lead
    except LeadNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı") from exc
    except LeadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{lead_id}/stage", response_model=CrmLeadDetail)
def move_lead_stage(
    lead_id: UUID,
    payload: CrmLeadStageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmLeadDetail:
    try:
        lead = move_crm_lead_stage(db, lead_id, payload.stage, actor=user)
        db.commit()
        return lead
    except LeadNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı") from exc
    except LeadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{lead_id}/convert", response_model=CrmLeadConvertResponse)
def convert_lead_workspace(
    lead_id: UUID,
    payload: CrmLeadConvertRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmLeadConvertResponse | JSONResponse:
    body = payload or CrmLeadConvertRequest()
    try:
        result = convert_crm_lead(
            db,
            lead_id,
            actor=user,
            confirm_existing_person_id=body.confirm_existing_person_id,
        )
        db.commit()
        return result
    except LeadNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı") from exc
    except LeadConflictError as exc:
        db.rollback()
        return _conflict(exc)
    except LeadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
