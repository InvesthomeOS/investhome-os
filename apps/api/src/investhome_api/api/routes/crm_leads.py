"""CRM leads workspace routes — prefix /crm/leads. Does not replace /leads."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_leads import (
    CrmLeadBoardCardsResponse,
    CrmLeadBoardResponse,
    CrmLeadConvertRequest,
    CrmLeadConvertResponse,
    CrmLeadCreate,
    CrmLeadDetail,
    CrmLeadIngestRequest,
    CrmLeadListResponse,
    CrmLeadStageUpdate,
    CrmLeadUpdate,
)
from investhome_api.services.crm.activity_service import ActivityValidationError
from investhome_api.services.crm.crm_lead_service import (
    LEAD_CARD_PAGE_SIZE,
    LEAD_LIST_PAGE_SIZE,
    LeadConflictError,
    LeadNotFoundError,
    LeadValidationError,
    convert_crm_lead,
    create_crm_lead,
    get_crm_lead,
    ingest_crm_lead,
    lead_board,
    lead_board_cards,
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


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Lead bulunamadı",
    )


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _lead_validation_http(exc: LeadValidationError) -> HTTPException:
    fallback = status.HTTP_400_BAD_REQUEST
    status_code = getattr(exc, "status_code", fallback) or fallback
    code = getattr(exc, "code", None)
    return HTTPException(status_code=status_code, detail=code or str(exc))


def _lead_query(
    *,
    search: str | None,
    stage: str | None,
    source: str | None,
    project: str | None,
    owner_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
    ingest_status: str | None,
    junk_reason: str | None,
    surface: str | None,
) -> dict[str, object]:
    return {
        "search": search,
        "stage": stage,
        "source": source,
        "project": project,
        "owner_id": owner_id,
        "date_from": date_from,
        "date_to": date_to,
        "ingest_status": ingest_status,
        "junk_reason": junk_reason,
        "surface": surface,
    }


@router.get("", response_model=CrmLeadListResponse)
def list_leads_workspace(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    search: Annotated[str | None, Query(max_length=255)] = None,
    stage: Annotated[str | None, Query(max_length=40)] = None,
    source: Annotated[str | None, Query(max_length=100)] = None,
    project: Annotated[str | None, Query(max_length=255)] = None,
    owner_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    ingest_status: Annotated[str | None, Query(max_length=20)] = None,
    junk_reason: Annotated[str | None, Query(max_length=40)] = None,
    surface: Annotated[str | None, Query(max_length=40)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = LEAD_LIST_PAGE_SIZE,
) -> CrmLeadListResponse:
    del user
    return list_crm_leads(
        db,
        page=page,
        page_size=page_size,
        **_lead_query(
            search=search,
            stage=stage,
            source=source,
            project=project,
            owner_id=owner_id,
            date_from=date_from,
            date_to=date_to,
            ingest_status=ingest_status,
            junk_reason=junk_reason,
            surface=surface,
        ),
    )


@router.get("/board/cards", response_model=CrmLeadBoardCardsResponse)
def lead_board_cards_route(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    stage: Annotated[str, Query(min_length=1, max_length=40)],
    search: Annotated[str | None, Query(max_length=255)] = None,
    source: Annotated[str | None, Query(max_length=100)] = None,
    project: Annotated[str | None, Query(max_length=255)] = None,
    owner_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    ingest_status: Annotated[str | None, Query(max_length=20)] = None,
    junk_reason: Annotated[str | None, Query(max_length=40)] = None,
    surface: Annotated[str | None, Query(max_length=40)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = LEAD_CARD_PAGE_SIZE,
) -> CrmLeadBoardCardsResponse:
    del user
    payload = lead_board_cards(
        db,
        stage=stage,
        page=page,
        page_size=page_size,
        search=search,
        source=source,
        project=project,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
        ingest_status=ingest_status,
        junk_reason=junk_reason,
        surface=surface,
    )
    return CrmLeadBoardCardsResponse(**payload)


@router.get("/board", response_model=CrmLeadBoardResponse)
def lead_board_route(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    search: Annotated[str | None, Query(max_length=255)] = None,
    stage: Annotated[str | None, Query(max_length=40)] = None,
    source: Annotated[str | None, Query(max_length=100)] = None,
    project: Annotated[str | None, Query(max_length=255)] = None,
    owner_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    ingest_status: Annotated[str | None, Query(max_length=20)] = None,
    junk_reason: Annotated[str | None, Query(max_length=40)] = None,
    surface: Annotated[str | None, Query(max_length=40)] = None,
    page_size: Annotated[int, Query(ge=1, le=50)] = LEAD_CARD_PAGE_SIZE,
) -> CrmLeadBoardResponse:
    del user
    payload = lead_board(
        db,
        page_size=page_size,
        **_lead_query(
            search=search,
            stage=stage,
            source=source,
            project=project,
            owner_id=owner_id,
            date_from=date_from,
            date_to=date_to,
            ingest_status=ingest_status,
            junk_reason=junk_reason,
            surface=surface,
        ),
    )
    return CrmLeadBoardResponse(**payload)


@router.post("/ingest", response_model=CrmLeadDetail, status_code=status.HTTP_201_CREATED)
def ingest_lead_workspace(
    payload: CrmLeadIngestRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "create"))],
) -> CrmLeadDetail:
    """Store a future Meta/Google/website lead. Providers are not connected."""
    try:
        lead = ingest_crm_lead(db, payload, actor=user)
        db.commit()
        return lead
    except LeadValidationError as exc:
        db.rollback()
        raise _lead_validation_http(exc) from exc


@router.get("/{lead_id}", response_model=CrmLeadDetail)
def get_lead_workspace(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
) -> CrmLeadDetail:
    del user
    try:
        return get_crm_lead(db, lead_id)
    except LeadNotFoundError as exc:
        raise _not_found() from exc


@router.post("", response_model=CrmLeadDetail, status_code=status.HTTP_201_CREATED)
def create_lead_workspace(
    payload: CrmLeadCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "create"))],
    confirm: Annotated[bool, Query()] = False,
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
        raise _lead_validation_http(exc) from exc


@router.patch("/{lead_id}", response_model=CrmLeadDetail)
def update_lead_workspace(
    lead_id: UUID,
    payload: CrmLeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
) -> CrmLeadDetail:
    try:
        lead = update_crm_lead(db, lead_id, payload, actor=user)
        db.commit()
        return lead
    except LeadNotFoundError as exc:
        db.rollback()
        raise _not_found() from exc
    except LeadValidationError as exc:
        db.rollback()
        raise _lead_validation_http(exc) from exc
    except ActivityValidationError as exc:
        db.rollback()
        raise _bad_request(str(exc)) from exc


@router.post("/{lead_id}/stage", response_model=CrmLeadDetail)
def move_lead_stage(
    lead_id: UUID,
    payload: CrmLeadStageUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
) -> CrmLeadDetail:
    try:
        lead = move_crm_lead_stage(
            db,
            lead_id,
            payload.stage,
            actor=user,
            junk_reason=payload.junk_reason,
            junk_reason_detail=payload.junk_reason_detail,
        )
        db.commit()
        return lead
    except LeadNotFoundError as exc:
        db.rollback()
        raise _not_found() from exc
    except LeadValidationError as exc:
        db.rollback()
        raise _lead_validation_http(exc) from exc
    except ActivityValidationError as exc:
        db.rollback()
        raise _bad_request(str(exc)) from exc


@router.post("/{lead_id}/convert", response_model=CrmLeadConvertResponse)
def convert_lead_workspace(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
    payload: CrmLeadConvertRequest | None = None,
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
        raise _not_found() from exc
    except LeadConflictError as exc:
        db.rollback()
        return _conflict(exc)
    except LeadValidationError as exc:
        db.rollback()
        raise _lead_validation_http(exc) from exc
    except ValueError as exc:
        db.rollback()
        raise _bad_request(str(exc)) from exc
