"""CRM identity match review routes — prefix /crm/matches."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_matches import CrmMatchDecisionRequest, CrmMatchDetail, CrmMatchListResponse
from investhome_api.services.crm.crm_match_service import (
    MatchNotFoundError,
    MatchValidationError,
    decide_crm_match,
    get_crm_match,
    list_crm_matches,
    refresh_crm_matches,
)

router = APIRouter(prefix="/crm/matches", tags=["crm-matches"])


@router.get("", response_model=CrmMatchListResponse)
def list_matches_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
    search: str | None = Query(default=None, max_length=255),
    match_type: str | None = Query(default=None, max_length=40),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    source: str | None = Query(default=None, max_length=80),
) -> CrmMatchListResponse:
    del user
    result = list_crm_matches(
        db,
        search=search,
        match_type=match_type,
        status=status_filter,
        source=source,
    )
    db.commit()
    return result


@router.post("/refresh", response_model=CrmMatchListResponse)
def refresh_matches_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmMatchListResponse:
    del user
    refresh_crm_matches(db)
    result = list_crm_matches(db, refresh=False)
    db.commit()
    return result


@router.get("/{match_id}", response_model=CrmMatchDetail)
def get_match_workspace(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmMatchDetail:
    del user
    try:
        return get_crm_match(db, match_id)
    except MatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eşleşme bulunamadı") from exc


@router.post("/{match_id}/decision", response_model=CrmMatchDetail)
def decide_match_workspace(
    match_id: UUID,
    payload: CrmMatchDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmMatchDetail:
    try:
        result = decide_crm_match(db, match_id, payload, actor=user)
        db.commit()
        return result
    except MatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eşleşme bulunamadı") from exc
    except MatchValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
