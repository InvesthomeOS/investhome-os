"""Authorized CRM relationship corrections. Does not delete contacts or history."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_agreements import (
    CrmAgreementOwnerAdd,
    CrmAgreementOwnerShares,
    CrmAgreementUnitChange,
    CrmPurchaseCard,
)
from investhome_api.services.crm.agreement_service import get_purchase_card
from investhome_api.services.crm.known_crm_corrections import (
    apply_known_crm_corrections,
    preview_known_crm_corrections,
)
from investhome_api.services.crm.relationship_corrections import (
    RelationshipCorrectionError,
    add_agreement_owner,
    archive_agent,
    change_agreement_unit,
    remove_agreement_owner,
    remove_duplicate_owner,
    restore_agent,
    set_ownership_percentages,
)

router = APIRouter(prefix="/crm", tags=["crm-corrections"])


def _run(db: Session, work) -> None:
    try:
        work()
        db.commit()
    except RelationshipCorrectionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc
    except Exception:
        db.rollback()
        raise


def _card(db: Session, agreement_id: UUID) -> CrmPurchaseCard:
    card = get_purchase_card(db, agreement_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agreement_not_found")
    return card


@router.post("/agreements/{agreement_id}/owners", response_model=CrmPurchaseCard)
def post_agreement_owner(
    agreement_id: UUID,
    body: CrmAgreementOwnerAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_ownership")),
) -> CrmPurchaseCard:
    _run(
        db,
        lambda: add_agreement_owner(
            db,
            agreement_id,
            body.contact_id,
            body.ownership_pct,
            actor=user,
        ),
    )
    return _card(db, agreement_id)


@router.delete("/agreements/{agreement_id}/owners/{contact_id}", response_model=CrmPurchaseCard)
def delete_agreement_owner(
    agreement_id: UUID,
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_ownership")),
) -> CrmPurchaseCard:
    _run(
        db,
        lambda: remove_agreement_owner(db, agreement_id, contact_id, actor=user),
    )
    return _card(db, agreement_id)


@router.put("/agreements/{agreement_id}/owners", response_model=CrmPurchaseCard)
def put_agreement_owners(
    agreement_id: UUID,
    body: CrmAgreementOwnerShares,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_ownership")),
) -> CrmPurchaseCard:
    shares = [(item.contact_id, item.ownership_pct) for item in body.owners]
    _run(db, lambda: set_ownership_percentages(db, agreement_id, shares, actor=user))
    return _card(db, agreement_id)


@router.post("/agreements/{agreement_id}/owners/duplicates", response_model=CrmPurchaseCard)
def post_remove_duplicate_owner(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_ownership")),
) -> CrmPurchaseCard:
    _run(db, lambda: remove_duplicate_owner(db, agreement_id, actor=user))
    return _card(db, agreement_id)


@router.patch("/agreements/{agreement_id}/unit", response_model=CrmPurchaseCard)
def patch_agreement_unit(
    agreement_id: UUID,
    body: CrmAgreementUnitChange,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmPurchaseCard:
    _run(
        db,
        lambda: change_agreement_unit(db, agreement_id, body.unit_number, actor=user),
    )
    return _card(db, agreement_id)


@router.get("/corrections/known/preview")
def get_known_corrections_preview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "correct_relationships")),
) -> dict[str, object]:
    del user
    results = preview_known_crm_corrections(db)
    db.rollback()
    return {"results": results}


@router.post("/corrections/known")
def post_known_corrections(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "correct_relationships")),
) -> dict[str, object]:
    try:
        results = apply_known_crm_corrections(db, actor=user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"results": results}


@router.post("/agents/{contact_id}/archive")
def post_archive_agent(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive")),
) -> dict[str, str]:
    status_value = "archived"

    def work() -> None:
        nonlocal status_value
        status_value = archive_agent(db, contact_id, actor=user)

    _run(db, work)
    return {"status": status_value}


@router.post("/agents/{contact_id}/restore")
def post_restore_agent(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "restore")),
) -> dict[str, str]:
    status_value = "restored"

    def work() -> None:
        nonlocal status_value
        status_value = restore_agent(db, contact_id, actor=user)

    _run(db, work)
    return {"status": status_value}
