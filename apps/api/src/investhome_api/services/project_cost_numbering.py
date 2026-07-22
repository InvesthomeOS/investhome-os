"""Transactional number generation for project cost entities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.project_cost import (
    ProjectCommitment,
    ProjectCommitmentChangeOrder,
    ProjectCommitmentType,
    ProjectPayment,
    ProjectRetainageRelease,
    ProjectVendorBill,
    Vendor,
)

COMMITMENT_PREFIX: dict[ProjectCommitmentType, str] = {
    ProjectCommitmentType.CONTRACT: "CTR",
    ProjectCommitmentType.PURCHASE_ORDER: "PO",
    ProjectCommitmentType.SUBCONTRACT: "SUB",
    ProjectCommitmentType.PROFESSIONAL_SERVICES: "CTR",
    ProjectCommitmentType.CONSULTING_AGREEMENT: "CTR",
    ProjectCommitmentType.LETTER_OF_INTENT: "CTR",
    ProjectCommitmentType.OTHER: "CTR",
}


def _next_suffix(db: Session, existing: list[str], prefix: str, width: int) -> str:
    max_n = 0
    for value in existing:
        if not value.startswith(prefix + "-"):
            continue
        tail = value.split("-", 1)[-1]
        if tail.isdigit():
            max_n = max(max_n, int(tail))
    return f"{prefix}-{max_n + 1:0{width}d}"


def next_commitment_number(
    db: Session,
    *,
    project_id: UUID,
    commitment_type: ProjectCommitmentType,
) -> str:
    prefix = COMMITMENT_PREFIX.get(commitment_type, "CTR")
    rows = list(
        db.scalars(
            select(ProjectCommitment.commitment_number).where(
                ProjectCommitment.project_id == project_id,
                ProjectCommitment.commitment_number.like(f"{prefix}-%"),
            )
        ).all()
    )
    return _next_suffix(db, rows, prefix, 4)


def next_change_order_number(db: Session, *, commitment_id: UUID) -> str:
    rows = list(
        db.scalars(
            select(ProjectCommitmentChangeOrder.change_order_number).where(
                ProjectCommitmentChangeOrder.commitment_id == commitment_id
            )
        ).all()
    )
    return _next_suffix(db, rows, "CO", 3)


def next_bill_number(db: Session, *, project_id: UUID) -> str:
    rows = list(
        db.scalars(
            select(ProjectVendorBill.bill_number).where(ProjectVendorBill.project_id == project_id)
        ).all()
    )
    return _next_suffix(db, rows, "BILL", 6)


def next_payment_number(db: Session, *, project_id: UUID) -> str:
    rows = list(
        db.scalars(
            select(ProjectPayment.payment_number).where(ProjectPayment.project_id == project_id)
        ).all()
    )
    return _next_suffix(db, rows, "PAY", 6)


def next_retainage_release_number(db: Session, *, project_id: UUID) -> str:
    rows = list(
        db.scalars(
            select(ProjectRetainageRelease.release_number).where(
                ProjectRetainageRelease.project_id == project_id
            )
        ).all()
    )
    return _next_suffix(db, rows, "RET", 6)


def next_vendor_code(db: Session, *, company_id: UUID | None) -> str:
    query = select(func.count()).select_from(Vendor)
    if company_id is None:
        query = query.where(Vendor.company_id.is_(None))
    else:
        query = query.where(Vendor.company_id == company_id)
    count = int(db.scalar(query) or 0)
    return f"V-{count + 1:05d}"
