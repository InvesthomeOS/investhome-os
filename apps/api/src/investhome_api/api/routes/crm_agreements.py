"""CRM Agreements (Anlaşmalar) list API. No Bitrix write path."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.crm_agreement import CrmAgreementStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_agreements import (
    CrmAgreementListResponse,
    CrmPurchaseCard,
    agreement_project_group_options,
)
from investhome_api.services.crm.agreement_service import agreement_list_meta, get_purchase_card, list_agreements

router = APIRouter(prefix="/crm/agreements", tags=["crm-agreements"])


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
    del user
    items, total = list_agreements(
        db,
        project_group=project_group,
        status=status_filter,
        contact_id=contact_id,
        page=page,
        page_size=page_size,
    )
    meta = agreement_list_meta(total=total, page=page, page_size=page_size)
    return CrmAgreementListResponse(
        items=items,
        request_id=get_request_id() or "",
        project_groups=agreement_project_group_options(),
        **meta,
    )


@router.get("/{agreement_id}", response_model=CrmPurchaseCard)
def get_agreement_purchase_card(
    agreement_id: UUID,
    viewer_contact_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmPurchaseCard:
    del user
    card = get_purchase_card(db, agreement_id, viewer_contact_id=viewer_contact_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.agreements.errors.not_found")
    return card
