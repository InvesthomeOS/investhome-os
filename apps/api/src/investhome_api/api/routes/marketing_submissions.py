"""Marketing submissions API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    PUBLIC_FORM_MAX_BODY_BYTES,
    PublicFormSubmit,
    ReviewItemResponse,
    SubmissionDetail,
    SubmissionListResponse,
    SubmissionReviewAction,
    SubmissionSummary,
)
from investhome_api.services.login_rate_limit import resolve_client_ip
from investhome_api.services.marketing.submission_service import (
    compute_pages,
    list_review_queue,
    list_submissions,
    process_public_submission,
    review_submission,
)
from investhome_api.services.public_form_bot import enforce_public_form_bot
from investhome_api.services.public_form_rate_limit import enforce_public_form_rate_limit
from investhome_api.core.logging_config import get_logger

router = APIRouter(prefix="/marketing/submissions", tags=["marketing-submissions"])
public_router = APIRouter(prefix="/public/marketing/forms", tags=["marketing-public"])
_public_form_log = get_logger("investhome.public_form")


def _reject_oversized_public_form(request: Request) -> None:
    raw = request.headers.get("content-length")
    if raw is None:
        return
    try:
        size = int(raw)
    except ValueError:
        raise HTTPException(
            status_code=413,
            detail="Payload too large",
        ) from None
    if size > PUBLIC_FORM_MAX_BODY_BYTES:
        _public_form_log.warning("public_form_payload_too_large")
        raise HTTPException(
            status_code=413,
            detail="Payload too large",
        )


def _reject_oversized_payload(payload: PublicFormSubmit) -> None:
    size = len(payload.idempotency_key) + len(payload.hp_website or "")
    size += len(payload.cf_turnstile_response or "")
    for key, raw in payload.values.items():
        size += len(key)
        if isinstance(raw, str):
            size += len(raw)
    if payload.tracking:
        for value in payload.tracking.model_dump().values():
            if isinstance(value, str):
                size += len(value)
    if size > PUBLIC_FORM_MAX_BODY_BYTES:
        _public_form_log.warning("public_form_payload_too_large")
        raise HTTPException(
            status_code=413,
            detail="Payload too large",
        )


def _submission_summary(sub) -> SubmissionSummary:
    return SubmissionSummary(
        id=sub.id,
        form_id=sub.form_id,
        landing_page_id=sub.landing_page_id,
        status=sub.status.value if hasattr(sub.status, "value") else sub.status,
        contact_id=sub.contact_id,
        lead_context_id=sub.lead_context_id,
        created_at=sub.created_at,
    )


@router.get("", response_model=SubmissionListResponse)
def list_submissions_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_submissions")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    form_id: UUID | None = None,
    status: str | None = None,
):
    items, total = list_submissions(db, page=page, page_size=page_size, form_id=form_id, status_filter=status)
    return SubmissionListResponse(
        items=[_submission_summary(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.get("/review-queue", response_model=list[ReviewItemResponse])
def review_queue_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "review_submissions")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, _ = list_review_queue(db, page=page, page_size=page_size)
    return [
        ReviewItemResponse(
            id=i.id,
            submission_id=i.submission_id,
            review_type=i.review_type,
            status=i.status.value if hasattr(i.status, "value") else i.status,
            reason=i.reason,
            created_at=i.created_at,
        )
        for i in items
    ]


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission_route(
    submission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_submissions")),
):
    from fastapi import HTTPException
    from investhome_api.models.marketing_landing_conversion import MarketingFormSubmission

    sub = db.get(MarketingFormSubmission, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return SubmissionDetail(
        **_submission_summary(sub).model_dump(),
        normalized_values_json=sub.normalized_values_json,
        tracking_context_id=sub.tracking_context_id,
        consent_evidence_id=sub.consent_evidence_id,
        duplicate_of_submission_id=sub.duplicate_of_submission_id,
        pipeline_errors_json=sub.pipeline_errors_json,
    )


@router.post("/{submission_id}/review", response_model=SubmissionSummary)
def review_submission_route(
    submission_id: UUID,
    payload: SubmissionReviewAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "review_submissions")),
):
    sub = review_submission(db, submission_id, payload.action, payload.reason, user)
    db.commit()
    return _submission_summary(sub)


@public_router.post("/{form_slug}/submit", response_model=SubmissionSummary, status_code=201)
def public_submit_route(
    form_slug: str,
    payload: PublicFormSubmit,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public form submit — Redis rate limit, bot check, then server validation."""
    _reject_oversized_public_form(request)
    _reject_oversized_payload(payload)
    if (payload.hp_website or "").strip():
        _public_form_log.warning("public_form_honeypot")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to submit form.",
        )
    ip = resolve_client_ip(request)
    enforce_public_form_bot(token=payload.cf_turnstile_response, ip=ip)
    enforce_public_form_rate_limit(ip=ip, form_slug=form_slug)
    ua = request.headers.get("user-agent")
    sub = process_public_submission(
        db,
        form_slug,
        payload.model_dump(exclude={"cf_turnstile_response", "hp_website"}),
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return _submission_summary(sub)
