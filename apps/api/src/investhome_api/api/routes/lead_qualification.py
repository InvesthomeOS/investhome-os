"""Lead qualification, scoring, and follow-up API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.inventory import InventoryReservation
from investhome_api.models.lead import Lead
from investhome_api.models.lead_qualification import LeadQualification, LeadScoreComponent, QualificationStatus
from investhome_api.models.sales import SalesOpportunity
from investhome_api.models.user_auth import User
from investhome_api.schemas.lead_qualification import (
    LeadDetailSummaryResponse,
    LeadFollowUpCreate,
    LeadFollowUpResponse,
    LeadInventoryInterestCreate,
    LeadInventoryInterestResponse,
    LeadQualificationExecutiveSummary,
    LeadQualificationResponse,
    LeadQualificationUpdate,
    LeadScoreRecalculate,
    LeadScoreResponse,
    LeadScoreComponentResponse,
    LeadTimelineResponse,
    LeadTimelineEntry,
    QualificationStatusChange,
)
from investhome_api.services.leads import lead_score_service as score_svc
from investhome_api.services.leads import qualification_service as qual_svc

router = APIRouter(prefix="/leads", tags=["lead-qualification"])


def _handle_error(exc: qual_svc.QualificationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _score_response(db: Session, lead_id: UUID) -> LeadScoreResponse | None:
    score = score_svc.get_lead_score(db, lead_id)
    if score is None:
        return None
    components = list(
        db.scalars(
            select(LeadScoreComponent).where(LeadScoreComponent.lead_score_id == score.id)
        ).all()
    )
    return LeadScoreResponse(
        id=score.id,
        lead_id=score.lead_id,
        total_score=score.total_score,
        computed_at=score.computed_at,
        computed_by_id=score.computed_by_id,
        is_manual_override=score.is_manual_override,
        components=[LeadScoreComponentResponse.model_validate(c) for c in components],
    )


@router.get("/executive/qualification-summary", response_model=LeadQualificationExecutiveSummary)
def get_qualification_executive_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("executive", "view")),
) -> LeadQualificationExecutiveSummary:
    return LeadQualificationExecutiveSummary(**qual_svc.build_executive_qualification_summary(db))


@router.get("/{lead_id}/summary", response_model=LeadDetailSummaryResponse)
def get_lead_detail_summary(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> LeadDetailSummaryResponse:
    try:
        qual_svc._get_lead_or_raise(db, lead_id)
    except qual_svc.QualificationError as exc:
        raise _handle_error(exc) from exc

    qual = qual_svc.get_qualification(db, lead_id)
    score = score_svc.get_lead_score(db, lead_id)
    opp_count = db.scalar(
        select(func.count()).select_from(SalesOpportunity).where(SalesOpportunity.lead_id == lead_id)
    ) or 0
    resv_count = db.scalar(
        select(func.count()).select_from(InventoryReservation).where(InventoryReservation.lead_id == lead_id)
    ) or 0
    interests = qual_svc.list_inventory_interests(db, lead_id)
    follow_ups = qual_svc.list_follow_ups(db, lead_id)
    pending = sum(1 for f in follow_ups if f.status.value == "pending")

    return LeadDetailSummaryResponse(
        lead_id=lead_id,
        opportunity_count=opp_count,
        reservation_count=resv_count,
        inventory_interest_count=len(interests),
        follow_up_count=len(follow_ups),
        pending_follow_up_count=pending,
        lead_score=score.total_score if score else None,
        qualification_status=qual.qualification_status if qual else None,
    )


@router.get("/{lead_id}/qualification", response_model=LeadQualificationResponse)
def get_lead_qualification(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> LeadQualificationResponse:
    try:
        qual = qual_svc.get_or_create_qualification(db, lead_id)
        db.commit()
        db.refresh(qual)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadQualificationResponse.model_validate(qual)


@router.patch("/{lead_id}/qualification", response_model=LeadQualificationResponse)
def update_lead_qualification(
    lead_id: UUID,
    payload: LeadQualificationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "qualify_lead")),
) -> LeadQualificationResponse:
    try:
        qual = qual_svc.update_qualification(
            db,
            lead_id,
            payload.model_dump(exclude_unset=True),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(qual)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadQualificationResponse.model_validate(qual)


@router.post("/{lead_id}/qualification/status", response_model=LeadQualificationResponse)
def change_qualification_status(
    lead_id: UUID,
    payload: QualificationStatusChange,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "qualify_lead")),
) -> LeadQualificationResponse:
    try:
        qual = qual_svc.change_qualification_status(
            db,
            lead_id,
            payload.status,
            actor=actor,
            notes=payload.notes,
            request=request,
        )
        db.commit()
        db.refresh(qual)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadQualificationResponse.model_validate(qual)


@router.get("/{lead_id}/score", response_model=LeadScoreResponse | None)
def get_lead_score(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> LeadScoreResponse | None:
    try:
        return _score_response(db, lead_id)
    except qual_svc.QualificationError as exc:
        raise _handle_error(exc) from exc


@router.post("/{lead_id}/score/recalculate", response_model=LeadScoreResponse)
def recalculate_lead_score(
    lead_id: UUID,
    payload: LeadScoreRecalculate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "score_lead")),
) -> LeadScoreResponse:
    try:
        score, _ = score_svc.recalculate_lead_score(
            db,
            lead_id,
            actor=actor,
            manual_override=payload.manual_override,
            request=request,
        )
        db.commit()
        db.refresh(score)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    result = _score_response(db, lead_id)
    assert result is not None
    return result


@router.get("/{lead_id}/timeline", response_model=LeadTimelineResponse)
def get_lead_timeline(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> LeadTimelineResponse:
    try:
        items = qual_svc.build_lead_timeline(db, lead_id)
    except qual_svc.QualificationError as exc:
        raise _handle_error(exc) from exc
    return LeadTimelineResponse(items=[LeadTimelineEntry(**item) for item in items])


@router.get("/{lead_id}/inventory-interests", response_model=list[LeadInventoryInterestResponse])
def list_lead_inventory_interests(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> list[LeadInventoryInterestResponse]:
    try:
        items = qual_svc.list_inventory_interests(db, lead_id)
    except qual_svc.QualificationError as exc:
        raise _handle_error(exc) from exc
    return [LeadInventoryInterestResponse.model_validate(i) for i in items]


@router.post(
    "/{lead_id}/inventory-interests",
    response_model=LeadInventoryInterestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lead_inventory_interest(
    lead_id: UUID,
    payload: LeadInventoryInterestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update_lead")),
) -> LeadInventoryInterestResponse:
    try:
        interest = qual_svc.add_inventory_interest(
            db,
            lead_id,
            payload.model_dump(),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(interest)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadInventoryInterestResponse.model_validate(interest)


@router.delete("/{lead_id}/inventory-interests/{interest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead_inventory_interest(
    lead_id: UUID,
    interest_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "update_lead")),
) -> None:
    try:
        qual_svc.remove_inventory_interest(db, lead_id, interest_id)
        db.commit()
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.get("/{lead_id}/follow-ups", response_model=list[LeadFollowUpResponse])
def list_lead_follow_ups(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_lead")),
) -> list[LeadFollowUpResponse]:
    try:
        items = qual_svc.list_follow_ups(db, lead_id)
    except qual_svc.QualificationError as exc:
        raise _handle_error(exc) from exc
    return [LeadFollowUpResponse.model_validate(i) for i in items]


@router.post(
    "/{lead_id}/follow-ups",
    response_model=LeadFollowUpResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lead_follow_up(
    lead_id: UUID,
    payload: LeadFollowUpCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update_lead")),
) -> LeadFollowUpResponse:
    try:
        follow_up = qual_svc.create_follow_up(
            db,
            lead_id,
            payload.model_dump(),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(follow_up)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadFollowUpResponse.model_validate(follow_up)


@router.patch("/{lead_id}/follow-ups/{follow_up_id}/complete", response_model=LeadFollowUpResponse)
def complete_lead_follow_up(
    lead_id: UUID,
    follow_up_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update_lead")),
) -> LeadFollowUpResponse:
    try:
        follow_up = qual_svc.complete_follow_up(
            db,
            lead_id,
            follow_up_id,
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(follow_up)
    except qual_svc.QualificationError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return LeadFollowUpResponse.model_validate(follow_up)
