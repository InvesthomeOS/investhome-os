"""Sales proposal API routes."""

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.sales_proposal import ProposalStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.sales_proposal import (
    ProposalExecutiveSummaryResponse,
    ProposalHtmlResponse,
    ProposalReviewRequest,
    SalesProposalActivityResponse,
    SalesProposalApprovalResponse,
    SalesProposalCreate,
    SalesProposalDetailResponse,
    SalesProposalItemCreate,
    SalesProposalItemReorderEntry,
    SalesProposalItemResponse,
    SalesProposalItemUpdate,
    SalesProposalListResponse,
    SalesProposalRecipientCreate,
    SalesProposalRecipientResponse,
    SalesProposalResponse,
    SalesProposalUpdate,
    SalesProposalVersionResponse,
    ShortlistImportRequest,
    StaleCheckResponse,
)
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.sales import proposal_output_service as output_svc
from investhome_api.services.sales import proposal_service as svc

router = APIRouter(prefix="/sales/proposals", tags=["sales-proposals"])


def _handle_error(exc: svc.ProposalError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _build_detail(
    db: Session,
    proposal,
    *,
    user: User,
) -> SalesProposalDetailResponse:
    version = svc._get_current_version(db, proposal)
    items = svc.get_version_items(db, version.id) if version else []
    items = svc.mask_item_amounts(items, user)
    stale = svc.check_stale(db, proposal)
    return SalesProposalDetailResponse(
        **SalesProposalResponse.model_validate(proposal).model_dump(),
        current_version=SalesProposalVersionResponse.model_validate(version) if version else None,
        items=[SalesProposalItemResponse.model_validate(i) for i in items],
        recipients=[SalesProposalRecipientResponse.model_validate(r) for r in svc.get_recipients(db, proposal.id)],
        stale_check=stale,
    )


@router.get("", response_model=SalesProposalListResponse)
def list_proposals(
    search: str | None = Query(default=None, max_length=255),
    status: ProposalStatus | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    party_id: UUID | None = Query(default=None),
    primary_project_id: UUID | None = Query(default=None),
    assigned_sales_user_id: UUID | None = Query(default=None),
    valid_until_before: date | None = Query(default=None),
    valid_until_after: date | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> SalesProposalListResponse:
    items, total = svc.list_proposals(
        db,
        search=search,
        status=status,
        opportunity_id=opportunity_id,
        party_id=party_id,
        primary_project_id=primary_project_id,
        assigned_sales_user_id=assigned_sales_user_id,
        valid_until_before=valid_until_before,
        valid_until_after=valid_until_after,
        created_after=created_after,
        created_before=created_before,
        include_archived=include_archived,
        offset=offset,
        limit=limit,
    )
    return SalesProposalListResponse(
        items=[SalesProposalResponse.model_validate(p) for p in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/executive-summary", response_model=ProposalExecutiveSummaryResponse)
def executive_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_pipeline")),
) -> ProposalExecutiveSummaryResponse:
    return ProposalExecutiveSummaryResponse(**svc.build_executive_summary(db))


@router.get("/{proposal_id}", response_model=SalesProposalDetailResponse)
def get_proposal(
    proposal_id: UUID,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id, include_archived=include_archived)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return _build_detail(db, proposal, user=user)


@router.post("", response_model=SalesProposalDetailResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(
    body: SalesProposalCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "create_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.create_proposal(db, body.model_dump(), actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.patch("/{proposal_id}", response_model=SalesProposalDetailResponse)
def update_proposal(
    proposal_id: UUID,
    body: SalesProposalUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.update_proposal(
            db,
            proposal,
            body.model_dump(exclude_unset=True),
            actor=user,
            request=request,
        )
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.delete("/{proposal_id}", response_model=SalesProposalResponse)
def archive_proposal(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "archive_proposal")),
) -> SalesProposalResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.archive_proposal(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return SalesProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/restore", response_model=SalesProposalResponse)
def restore_proposal(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id, include_archived=True)
        proposal = svc.restore_proposal(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return SalesProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/submit", response_model=SalesProposalDetailResponse)
def submit_proposal(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "submit_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.submit_proposal(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/review", response_model=SalesProposalDetailResponse)
def review_proposal(
    proposal_id: UUID,
    body: ProposalReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "review_proposal")),
) -> SalesProposalDetailResponse:
    perm = "approve_proposal" if body.decision.value == "approved" else "reject_proposal"
    if body.decision.value == "revision_requested":
        perm = "review_proposal"
    if not user_has_permission(user, "sales", perm):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.review_proposal(
            db,
            proposal,
            decision=body.decision,
            comments=body.comments,
            actor=user,
            request=request,
        )
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/mark-sent", response_model=SalesProposalDetailResponse)
def mark_sent(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "mark_proposal_sent")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.mark_sent(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/mark-viewed", response_model=SalesProposalDetailResponse)
def mark_viewed(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "mark_proposal_viewed")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.mark_viewed(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/mark-accepted", response_model=SalesProposalDetailResponse)
def mark_accepted(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "mark_proposal_accepted")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.mark_accepted(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/mark-rejected", response_model=SalesProposalDetailResponse)
def mark_rejected(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.mark_rejected(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/mark-expired", response_model=SalesProposalDetailResponse)
def mark_expired(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        proposal = svc.mark_expired(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/versions", response_model=SalesProposalVersionResponse)
def create_version(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalVersionResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        version = svc.create_version_from_current(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(version)
    return SalesProposalVersionResponse.model_validate(version)


@router.get("/{proposal_id}/versions", response_model=list[SalesProposalVersionResponse])
def list_versions(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> list[SalesProposalVersionResponse]:
    try:
        svc.get_proposal_or_raise(db, proposal_id)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    versions = svc.list_versions(db, proposal_id)
    return [SalesProposalVersionResponse.model_validate(v) for v in versions]


@router.get("/{proposal_id}/versions/{version_id}", response_model=SalesProposalVersionResponse)
def get_version(
    proposal_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> SalesProposalVersionResponse:
    try:
        svc.get_proposal_or_raise(db, proposal_id)
        version = svc._get_version_or_raise(db, version_id)
        if version.proposal_id != proposal_id:
            raise svc.ProposalError("sales.proposal.errors.version_not_found", status_code=404)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return SalesProposalVersionResponse.model_validate(version)


@router.post("/{proposal_id}/import-shortlist", response_model=SalesProposalDetailResponse)
def import_shortlist(
    proposal_id: UUID,
    body: ShortlistImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        svc.import_from_shortlist(db, proposal, body.shortlist_id, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.post("/{proposal_id}/items", response_model=SalesProposalItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    proposal_id: UUID,
    body: SalesProposalItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalItemResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        item = svc.add_item(db, proposal, body.model_dump(), actor=user)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(item)
    return SalesProposalItemResponse.model_validate(item)


@router.patch("/{proposal_id}/items/{item_id}", response_model=SalesProposalItemResponse)
def update_item(
    proposal_id: UUID,
    item_id: UUID,
    body: SalesProposalItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalItemResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        item = svc.update_item(
            db,
            proposal,
            item_id,
            body.model_dump(exclude_unset=True),
            actor=user,
        )
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(item)
    return SalesProposalItemResponse.model_validate(item)


@router.delete("/{proposal_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    proposal_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> None:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        svc.remove_item(db, proposal, item_id, actor=user)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/{proposal_id}/items/reorder", response_model=list[SalesProposalItemResponse])
def reorder_items(
    proposal_id: UUID,
    body: list[SalesProposalItemReorderEntry],
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> list[SalesProposalItemResponse]:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        items = svc.reorder_items(
            db,
            proposal,
            [entry.model_dump() for entry in body],
            actor=user,
        )
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return [SalesProposalItemResponse.model_validate(i) for i in items]


@router.post("/{proposal_id}/refresh-pricing", response_model=SalesProposalDetailResponse)
def refresh_pricing(
    proposal_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalDetailResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        svc.refresh_stale_pricing(db, proposal, actor=user, request=request)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(proposal)
    return _build_detail(db, proposal, user=user)


@router.get("/{proposal_id}/stale-check", response_model=StaleCheckResponse)
def stale_check(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> StaleCheckResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    result = svc.check_stale(db, proposal)
    return StaleCheckResponse(**result)


@router.post("/{proposal_id}/recipients", response_model=SalesProposalRecipientResponse, status_code=status.HTTP_201_CREATED)
def add_recipient(
    proposal_id: UUID,
    body: SalesProposalRecipientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalRecipientResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        recipient = svc.add_recipient(db, proposal, body.model_dump(), actor=user)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(recipient)
    return SalesProposalRecipientResponse.model_validate(recipient)


@router.delete("/{proposal_id}/recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recipient(
    proposal_id: UUID,
    recipient_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> None:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        svc.remove_recipient(db, proposal, recipient_id)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/{proposal_id}/recipients/{recipient_id}/set-primary", response_model=SalesProposalRecipientResponse)
def set_primary_recipient(
    proposal_id: UUID,
    recipient_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_proposal")),
) -> SalesProposalRecipientResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        recipient = svc.set_primary_recipient(db, proposal, recipient_id, actor=user)
        db.commit()
    except svc.ProposalError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    db.refresh(recipient)
    return SalesProposalRecipientResponse.model_validate(recipient)


@router.get("/{proposal_id}/activities", response_model=list[SalesProposalActivityResponse])
def list_activities(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> list[SalesProposalActivityResponse]:
    try:
        svc.get_proposal_or_raise(db, proposal_id)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return [SalesProposalActivityResponse.model_validate(a) for a in svc.get_activities(db, proposal_id)]


@router.get("/{proposal_id}/approvals", response_model=list[SalesProposalApprovalResponse])
def list_approvals(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_proposal")),
) -> list[SalesProposalApprovalResponse]:
    try:
        svc.get_proposal_or_raise(db, proposal_id)
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return [SalesProposalApprovalResponse.model_validate(a) for a in svc.get_approvals(db, proposal_id)]


@router.get("/{proposal_id}/preview", response_model=ProposalHtmlResponse)
def preview_proposal(
    proposal_id: UUID,
    version_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "generate_proposal")),
) -> ProposalHtmlResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        version = svc._get_version_or_raise(db, version_id) if version_id else svc._get_current_version(db, proposal)
        if version is None:
            raise svc.ProposalError("sales.proposal.errors.no_version")
        items = svc.get_version_items(db, version.id)
        show_prices = user_has_permission(user, "sales", "view_sensitive_proposal_price")
        if not show_prices:
            items = svc.mask_item_amounts(items, user)
        html = output_svc.render_proposal_html(
            db,
            proposal,
            version,
            items=items,
            recipients=svc.get_recipients(db, proposal.id),
            show_sensitive_prices=show_prices,
        )
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return ProposalHtmlResponse(
        html=html,
        proposal_number=proposal.proposal_number,
        version_number=version.version_number,
    )


@router.get("/{proposal_id}/download", response_class=HTMLResponse)
def download_proposal(
    proposal_id: UUID,
    version_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "generate_proposal")),
) -> HTMLResponse:
    try:
        proposal = svc.get_proposal_or_raise(db, proposal_id)
        version = svc._get_version_or_raise(db, version_id) if version_id else svc._get_current_version(db, proposal)
        if version is None:
            raise svc.ProposalError("sales.proposal.errors.no_version")
        items = svc.get_version_items(db, version.id)
        show_prices = user_has_permission(user, "sales", "view_sensitive_proposal_price")
        if not show_prices:
            items = svc.mask_item_amounts(items, user)
        html = output_svc.render_proposal_html(
            db,
            proposal,
            version,
            items=items,
            recipients=svc.get_recipients(db, proposal.id),
            show_sensitive_prices=show_prices,
        )
    except svc.ProposalError as exc:
        raise _handle_error(exc) from exc
    return HTMLResponse(content=html)
