"""CRM Agreements (Anlaşmalar) list API. No Bitrix write path."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
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
    CrmAgreementBoardCardsResponse,
    CrmAgreementBoardResponse,
    CrmAgreementCalendarResponse,
    CrmAgreementListResponse,
    CrmAgreementPatch,
    CrmPurchaseCard,
    agreement_project_group_options,
)
from investhome_api.services.crm.agreement_service import (
    BOARD_CARD_PAGE_SIZE,
    agreement_board,
    agreement_board_cards,
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    status_filter: Annotated[CrmAgreementStatus | None, Query(alias="status")] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    sort_by: Annotated[str, Query(max_length=40)] = "agreement_date",
    sort_dir: Annotated[str, Query(max_length=4)] = "desc",
    q: Annotated[str | None, Query(max_length=255)] = None,
) -> CrmAgreementListResponse:
    items, total = list_agreements(
        db,
        project_group=project_group,
        status=status_filter,
        contact_id=contact_id,
        search=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
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


def _board_filters(
    *,
    project_group: str | None,
    status_filter: CrmAgreementStatus | None,
    contact_id: UUID | None,
    q: str | None,
    stage: str | None,
    responsible: str | None,
) -> dict[str, object]:
    return {
        "project_group": project_group,
        "status": status_filter,
        "contact_id": contact_id,
        "search": q,
        "stage": stage,
        "responsible": responsible,
    }


@router.get("/board/cards", response_model=CrmAgreementBoardCardsResponse)
def get_agreement_board_cards(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    stage: Annotated[str, Query(min_length=1, max_length=120)],
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    status_filter: Annotated[CrmAgreementStatus | None, Query(alias="status")] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=255)] = None,
    responsible: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = BOARD_CARD_PAGE_SIZE,
) -> CrmAgreementBoardCardsResponse:
    payload = agreement_board_cards(
        db,
        page=page,
        page_size=page_size,
        **_board_filters(
            project_group=project_group,
            status_filter=status_filter,
            contact_id=contact_id,
            q=q,
            stage=stage,
            responsible=responsible,
        ),
    )
    payload["items"] = maybe_strip_agreement_summaries(user, payload["items"])
    return CrmAgreementBoardCardsResponse(**payload, request_id=get_request_id() or "")


@router.get("/board", response_model=CrmAgreementBoardResponse)
def get_agreement_board(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    status_filter: Annotated[CrmAgreementStatus | None, Query(alias="status")] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=255)] = None,
    stage: Annotated[str | None, Query(max_length=120)] = None,
    responsible: Annotated[str | None, Query(max_length=120)] = None,
    page_size: Annotated[int, Query(ge=1, le=50)] = BOARD_CARD_PAGE_SIZE,
) -> CrmAgreementBoardResponse:
    payload = agreement_board(
        db,
        page_size=page_size,
        **_board_filters(
            project_group=project_group,
            status_filter=status_filter,
            contact_id=contact_id,
            q=q,
            stage=stage,
            responsible=responsible,
        ),
    )
    for column in payload["columns"]:
        column["items"] = maybe_strip_agreement_summaries(user, column["items"])
    return CrmAgreementBoardResponse(
        **payload,
        project_groups=agreement_project_group_options(),
        request_id=get_request_id() or "",
    )


@router.get("/activities", response_model=CrmAgreementActivityListResponse)
def get_agreement_activities(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
    activity_type: Annotated[str | None, Query(max_length=40)] = None,
    responsible: Annotated[str | None, Query(max_length=120)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
    project_group: Annotated[str | None, Query(max_length=40)] = None,
    contact_id: Annotated[UUID | None, Query()] = None,
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
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "update"))],
) -> CrmPurchaseCard:
    if body.hemen_kira is None and body.amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="crm.agreements.errors.empty_patch",
        )
    if body.amount is not None and not can_view_crm_financial(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="crm.agreements.errors.not_found",
        )
    return maybe_strip_purchase_card(user, card)


@router.get("/{agreement_id}", response_model=CrmPurchaseCard)
def get_agreement_purchase_card(
    agreement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("crm", "read"))],
    viewer_contact_id: Annotated[UUID | None, Query()] = None,
    include_hidden: Annotated[bool, Query()] = False,
) -> CrmPurchaseCard:
    include_hidden_documents = bool(include_hidden) and _can_include_hidden_purchase_documents(user)
    card = get_purchase_card(
        db,
        agreement_id,
        viewer_contact_id=viewer_contact_id,
        include_hidden_documents=include_hidden_documents,
    )
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="crm.agreements.errors.not_found",
        )
    return maybe_strip_purchase_card(user, card)
