"""CRM Agreements (Anlaşmalar) list API. No Bitrix write path."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.crm_agreement import CrmAgreementStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_agreements import (
    CrmAgreementActivityListResponse,
    CrmAgreementCalendarResponse,
    CrmAgreementListResponse,
    CrmAgreementPatch,
    CrmPurchaseCard,
    agreement_project_group_options,
)
from investhome_api.services.crm.agreement_service import (
    agreement_list_meta,
    get_purchase_card,
    list_agreements,
    list_purchase_activities,
    list_purchase_calendar,
    patch_agreement,
)
from investhome_api.services.crm.contact_service import paginate_total_pages
from investhome_api.services.crm.financial_visibility import (
    can_view_crm_financial,
    maybe_strip_agreement_summaries,
    maybe_strip_purchase_card,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm/agreements", tags=["crm-agreements"])


def _can_include_hidden_purchase_documents(user: User) -> bool:
    return user_has_permission(user, "documents", "view_confidential") or user_has_permission(
        user, "documents", "view_highly_confidential"
    )


@router.get("", response_model=CrmAgreementListResponse)
def get_agreements(
    project_group: str | None = Query(default=None, max_length=40),
    status_filter: CrmAgreementStatus | None = Query(default=None, alias="status"),
    contact_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmAgreementListResponse:
    items, total = list_agreements(
        db,
        project_group=project_group,
        status=status_filter,
        contact_id=contact_id,
        page=page,
        page_size=page_size,
    )
    items = maybe_strip_agreement_summaries(user, items)
    meta = agreement_list_meta(total=total, page=page, page_size=page_size)
    return CrmAgreementListResponse(
        items=items,
        request_id=get_request_id() or "",
        project_groups=agreement_project_group_options(),
        **meta,
    )


@router.get("/activities", response_model=CrmAgreementActivityListResponse)
def get_agreement_activities(
    project_group: str | None = Query(default=None, max_length=40),
    contact_id: UUID | None = Query(default=None),
    activity_type: str | None = Query(default=None, max_length=40),
    responsible: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmAgreementActivityListResponse:
    del user
    items, total = list_purchase_activities(
        db,
        project_group=project_group,
        contact_id=contact_id,
        activity_type=activity_type,
        responsible=responsible,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return CrmAgreementActivityListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=paginate_total_pages(total, page_size),
        request_id=get_request_id() or "",
    )


@router.get("/calendar", response_model=CrmAgreementCalendarResponse)
def get_agreement_calendar(
    start: date = Query(...),
    end: date = Query(...),
    project_group: str | None = Query(default=None, max_length=40),
    contact_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmAgreementCalendarResponse:
    del user
    items = list_purchase_calendar(
        db,
        start=start,
        end=end,
        project_group=project_group,
        contact_id=contact_id,
    )
    return CrmAgreementCalendarResponse(items=items, start=start, end=end)


@router.patch("/{agreement_id}", response_model=CrmPurchaseCard)
def patch_agreement_route(
    agreement_id: UUID,
    body: CrmAgreementPatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmPurchaseCard:
    if body.hemen_kira is None and body.amount is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="crm.agreements.errors.empty_patch")
    if body.amount is not None and not can_view_crm_financial(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        card = patch_agreement(
            db,
            agreement_id,
            hemen_kira=body.hemen_kira,
            amount=body.amount,
            actor=user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.agreements.errors.not_found")
    return maybe_strip_purchase_card(user, card)


@router.get("/{agreement_id}", response_model=CrmPurchaseCard)
def get_agreement_purchase_card(
    agreement_id: UUID,
    viewer_contact_id: UUID | None = Query(default=None),
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmPurchaseCard:
    include_hidden_documents = bool(include_hidden) and _can_include_hidden_purchase_documents(user)
    card = get_purchase_card(
        db,
        agreement_id,
        viewer_contact_id=viewer_contact_id,
        include_hidden_documents=include_hidden_documents,
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.agreements.errors.not_found")
    return maybe_strip_purchase_card(user, card)
