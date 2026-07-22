"""Project cost tracking service (Sprint 10A4B).

Recognition rules:
  - Actual cost = posted vendor bill line net_amount + tax_amount
  - Committed cost = sum of current_committed_amount for APPROVED/EXECUTED/ACTIVE/COMPLETED
  - Never sum legacy ProjectBudget.paid_amount with normalized actuals
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from math import ceil
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.project import Project
from investhome_api.models.project_budget import (
    BudgetVersionStatus,
    ProjectBudgetCategory,
    ProjectBudgetLine,
    ProjectBudgetVersion,
)
from investhome_api.models.project_cost import (
    COMMITTED_COST_STATUSES,
    POSTED_BILL_STATUSES,
    ChangeOrderStatus,
    ProjectCommitment,
    ProjectCommitmentChangeOrder,
    ProjectCommitmentChangeOrderLine,
    ProjectCommitmentLine,
    ProjectCommitmentStatus,
    ProjectPayment,
    ProjectPaymentAllocation,
    ProjectPaymentStatus,
    ProjectRetainageRelease,
    ProjectVendor,
    ProjectVendorBill,
    ProjectVendorBillLine,
    ProjectVendorStatus,
    RetainageReleaseStatus,
    Vendor,
    VendorBillStatus,
    VendorStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_cost import (
    ChangeOrderCreate,
    ChangeOrderLineInput,
    ChangeOrderResponse,
    ChangeOrderUpdate,
    CommitmentApproveRequest,
    CommitmentCreate,
    CommitmentLineBulkCreateRequest,
    CommitmentLineCreate,
    CommitmentLineResponse,
    CommitmentLineUpdate,
    CommitmentListResponse,
    CommitmentResponse,
    CommitmentUpdate,
    CostByBudgetLineRow,
    CostByCategoryRow,
    CostByVendorRow,
    CostPermissions,
    CostSummaryResponse,
    PaymentAllocationCreate,
    PaymentAllocationResponse,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentUpdate,
    ProjectVendorCreate,
    ProjectVendorResponse,
    ProjectVendorUpdate,
    RetainageReleaseCreate,
    RetainageReleaseResponse,
    RetainageSummaryResponse,
    VendorBillCreate,
    VendorBillLineBulkCreateRequest,
    VendorBillLineCreate,
    VendorBillLineResponse,
    VendorBillLineUpdate,
    VendorBillListResponse,
    VendorBillResponse,
    VendorBillUpdate,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from investhome_api.schemas.project_dashboard import metric, unavailable
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_cost_numbering import (
    next_bill_number,
    next_change_order_number,
    next_commitment_number,
    next_payment_number,
    next_retainage_release_number,
    next_vendor_code,
)
from investhome_api.services.project_cost_status import (
    assert_bill_editable,
    assert_change_order_editable,
    assert_commitment_editable,
    assert_payment_editable,
    validate_bill_transition,
    validate_change_order_transition,
    validate_commitment_transition,
    validate_payment_transition,
    validate_retainage_transition,
)
from investhome_api.services import project_service as project_svc

ZERO = Decimal("0")

# WARNING (default) allows over-budget with override_reason; HARD_BLOCK rejects.
# Tests may monkeypatch this constant.
BUDGET_CONTROL_MODE = "WARNING"

_SNAP_FIELDS = [
    "status",
    "name",
    "title",
    "description",
    "role",
    "original_amount",
    "current_committed_amount",
    "approved_change_orders",
    "invoiced_amount",
    "paid_amount",
    "retained_amount",
    "gross_amount",
    "net_amount",
    "subtotal",
    "total_amount",
    "approved_amount",
    "balance_due",
    "retainage_amount",
    "amount",
    "requested_amount",
    "vendor_invoice_number",
    "payment_method",
    "currency",
    "is_active",
]


def _snap(entity: object) -> dict:
    return snapshot_entity(entity, _SNAP_FIELDS)


def _perm(user: User, action: str) -> bool:
    return user_has_permission(user, "projects", action)


def cost_permissions(user: User) -> CostPermissions:
    view = _perm(user, "view_financial") or _perm(user, "edit_financial")
    edit = _perm(user, "edit_financial")
    return CostPermissions(
        can_view=view,
        can_manage_vendors=_perm(user, "manage_project_vendors") or edit,
        can_manage_commitments=_perm(user, "manage_commitments") or edit,
        can_approve_commitments=_perm(user, "approve_commitments") or edit,
        can_manage_bills=_perm(user, "manage_bills") or edit,
        can_approve_bills=_perm(user, "approve_bills") or edit,
        can_post_bills=_perm(user, "post_bills") or edit,
        can_manage_payments=_perm(user, "manage_payments") or edit,
        can_post_payments=_perm(user, "post_payments") or edit,
        can_manage_retainage=_perm(user, "manage_retainage") or edit,
        can_approve_retainage=_perm(user, "approve_retainage") or edit,
        can_override_budget_control=_perm(user, "override_budget_control") or edit,
        can_export=_perm(user, "export") or view,
    )


def require_view(user: User) -> None:
    if not cost_permissions(user).can_view:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Financial access required")


def require_manage_vendors(user: User) -> None:
    if not cost_permissions(user).can_manage_vendors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor manage access required")


def require_manage_commitments(user: User) -> None:
    if not cost_permissions(user).can_manage_commitments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Commitment manage access required"
        )


def require_approve_commitments(user: User) -> None:
    if not cost_permissions(user).can_approve_commitments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Commitment approve access required"
        )


def require_manage_bills(user: User) -> None:
    if not cost_permissions(user).can_manage_bills:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bill manage access required")


def require_approve_bills(user: User) -> None:
    if not cost_permissions(user).can_approve_bills:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bill approve access required")


def require_post_bills(user: User) -> None:
    if not cost_permissions(user).can_post_bills:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bill post access required")


def require_manage_payments(user: User) -> None:
    if not cost_permissions(user).can_manage_payments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Payment manage access required"
        )


def require_post_payments(user: User) -> None:
    if not cost_permissions(user).can_post_payments:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment post access required")


def require_manage_retainage(user: User) -> None:
    if not cost_permissions(user).can_manage_retainage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Retainage manage access required"
        )


def require_approve_retainage(user: User) -> None:
    if not cost_permissions(user).can_approve_retainage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Retainage approve access required"
        )


def _load_project(db: Session, project_id: UUID) -> Project:
    return project_svc.get_project_or_404(db, project_id, include_archived=True)


def _money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid monetary value",
        ) from exc
    return amount.quantize(Decimal("0.01"))


def _now() -> datetime:
    return datetime.now(UTC)


def _pages(total: int, page_size: int) -> int:
    return max(1, ceil(total / page_size)) if total else 0


def _load_vendor(db: Session, vendor_id: UUID) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def _load_commitment(db: Session, project_id: UUID, commitment_id: UUID) -> ProjectCommitment:
    row = db.get(ProjectCommitment, commitment_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found")
    return row


def _load_bill(db: Session, project_id: UUID, bill_id: UUID) -> ProjectVendorBill:
    row = db.get(ProjectVendorBill, bill_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor bill not found")
    return row


def _load_payment(db: Session, project_id: UUID, payment_id: UUID) -> ProjectPayment:
    row = db.get(ProjectPayment, payment_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return row


def _assert_vendor_usable(vendor: Vendor) -> None:
    if vendor.status in {VendorStatus.BLOCKED, VendorStatus.ARCHIVED, VendorStatus.INACTIVE}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Vendor status {vendor.status.value} cannot receive new commitments or bills",
        )


def _load_budget_line(db: Session, project_id: UUID, budget_line_id: UUID) -> ProjectBudgetLine:
    line = db.get(ProjectBudgetLine, budget_line_id)
    if line is None or line.project_id != project_id or not line.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Budget line not found or inactive for this project",
        )
    return line


def _recalc_commitment_line(line: ProjectCommitmentLine) -> None:
    line.current_amount = _money(line.original_amount) + _money(line.approved_change_orders)
    line.remaining_amount = line.current_amount - _money(line.invoiced_amount)


def _recalc_commitment(db: Session, commitment: ProjectCommitment) -> None:
    lines = list(
        db.scalars(
            select(ProjectCommitmentLine).where(
                ProjectCommitmentLine.commitment_id == commitment.id,
                ProjectCommitmentLine.is_active.is_(True),
            )
        ).all()
    )
    for line in lines:
        _recalc_commitment_line(line)
    commitment.original_amount = sum((_money(line.original_amount) for line in lines), ZERO)
    commitment.approved_change_orders = sum(
        (_money(line.approved_change_orders) for line in lines), ZERO
    )
    commitment.current_committed_amount = (
        commitment.original_amount + commitment.approved_change_orders
    )
    commitment.invoiced_amount = sum((_money(line.invoiced_amount) for line in lines), ZERO)
    commitment.paid_amount = sum((_money(line.paid_amount) for line in lines), ZERO)
    commitment.retained_amount = sum((_money(line.retained_amount) for line in lines), ZERO)
    commitment.remaining_commitment = (
        commitment.current_committed_amount - commitment.invoiced_amount
    )
    commitment.version_number = int(commitment.version_number or 1) + 1
    db.flush()


def _recalc_bill_line(line: ProjectVendorBillLine) -> None:
    line.net_amount = _money(line.gross_amount) - _money(line.retainage_amount)
    line.current_billed_amount = _money(line.gross_amount)


def _recalc_bill(db: Session, bill: ProjectVendorBill) -> None:
    lines = list(
        db.scalars(
            select(ProjectVendorBillLine).where(ProjectVendorBillLine.vendor_bill_id == bill.id)
        ).all()
    )
    for line in lines:
        _recalc_bill_line(line)
    bill.subtotal = sum((_money(line.gross_amount) for line in lines), ZERO)
    bill.retainage_amount = sum((_money(line.retainage_amount) for line in lines), ZERO)
    bill.tax_amount = sum((_money(line.tax_amount) for line in lines), ZERO)
    bill.total_amount = bill.subtotal + bill.tax_amount
    bill.approved_amount = bill.total_amount - bill.retainage_amount
    bill.balance_due = bill.approved_amount - _money(bill.paid_amount)
    bill.version_number = int(bill.version_number or 1) + 1
    db.flush()


def _bill_is_overdue(bill: ProjectVendorBill, today: date | None = None) -> bool:
    today = today or date.today()
    if bill.due_date is None:
        return False
    if bill.status in {VendorBillStatus.PAID, VendorBillStatus.VOID, VendorBillStatus.ARCHIVED}:
        return False
    return bill.due_date < today and _money(bill.balance_due) > ZERO


def _sync_commitment_invoiced_from_bills(db: Session, commitment: ProjectCommitment) -> None:
    """Refresh commitment/line invoiced & retained from posted bills only."""
    lines = list(
        db.scalars(
            select(ProjectCommitmentLine).where(
                ProjectCommitmentLine.commitment_id == commitment.id
            )
        ).all()
    )
    for line in lines:
        line.invoiced_amount = ZERO
        line.retained_amount = ZERO
        line.paid_amount = ZERO

    posted_lines = db.execute(
        select(ProjectVendorBillLine, ProjectVendorBill)
        .join(ProjectVendorBill, ProjectVendorBill.id == ProjectVendorBillLine.vendor_bill_id)
        .where(
            ProjectVendorBill.commitment_id == commitment.id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
    ).all()
    for bill_line, _bill in posted_lines:
        if bill_line.commitment_line_id is None:
            continue
        target = next((row for row in lines if row.id == bill_line.commitment_line_id), None)
        if target is None:
            continue
        # Invoiced uses recognized amount (net + tax) per actual-cost rule.
        recognized = _money(bill_line.net_amount) + _money(bill_line.tax_amount)
        target.invoiced_amount = _money(target.invoiced_amount) + recognized
        target.retained_amount = _money(target.retained_amount) + _money(bill_line.retainage_amount)

    paid_rows = db.execute(
        select(
            ProjectVendorBillLine.commitment_line_id,
            func.coalesce(func.sum(ProjectPaymentAllocation.allocated_amount), 0),
        )
        .join(ProjectVendorBill, ProjectVendorBill.id == ProjectVendorBillLine.vendor_bill_id)
        .join(
            ProjectPaymentAllocation,
            ProjectPaymentAllocation.vendor_bill_id == ProjectVendorBill.id,
        )
        .join(ProjectPayment, ProjectPayment.id == ProjectPaymentAllocation.payment_id)
        .where(
            ProjectVendorBill.commitment_id == commitment.id,
            ProjectPayment.status == ProjectPaymentStatus.POSTED,
            ProjectVendorBillLine.commitment_line_id.is_not(None),
        )
        .group_by(ProjectVendorBillLine.commitment_line_id)
    ).all()
    paid_map = {row[0]: _money(row[1]) for row in paid_rows}
    for line in lines:
        if line.id in paid_map:
            line.paid_amount = paid_map[line.id]

    released = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectRetainageRelease.amount), 0)).where(
                ProjectRetainageRelease.commitment_id == commitment.id,
                ProjectRetainageRelease.status == RetainageReleaseStatus.POSTED,
            )
        )
    )
    # Reduce retained by posted releases at commitment level after line sums.
    _recalc_commitment(db, commitment)
    commitment.retained_amount = max(commitment.retained_amount - released, ZERO)
    db.flush()


def _committed_by_budget_line(db: Session, project_id: UUID) -> dict[UUID, Decimal]:
    rows = db.execute(
        select(
            ProjectCommitmentLine.budget_line_id,
            func.coalesce(func.sum(ProjectCommitmentLine.current_amount), 0),
        )
        .join(ProjectCommitment, ProjectCommitment.id == ProjectCommitmentLine.commitment_id)
        .where(
            ProjectCommitment.project_id == project_id,
            ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
            ProjectCommitmentLine.is_active.is_(True),
        )
        .group_by(ProjectCommitmentLine.budget_line_id)
    ).all()
    return {row[0]: _money(row[1]) for row in rows}


def _pending_by_budget_line(db: Session, project_id: UUID) -> dict[UUID, Decimal]:
    rows = db.execute(
        select(
            ProjectCommitmentLine.budget_line_id,
            func.coalesce(func.sum(ProjectCommitmentLine.current_amount), 0),
        )
        .join(ProjectCommitment, ProjectCommitment.id == ProjectCommitmentLine.commitment_id)
        .where(
            ProjectCommitment.project_id == project_id,
            ProjectCommitment.status == ProjectCommitmentStatus.IN_REVIEW,
            ProjectCommitmentLine.is_active.is_(True),
        )
        .group_by(ProjectCommitmentLine.budget_line_id)
    ).all()
    return {row[0]: _money(row[1]) for row in rows}


def _actual_by_budget_line(db: Session, project_id: UUID) -> dict[UUID, Decimal]:
    """Actual cost = posted bill line net_amount + tax_amount."""
    rows = db.execute(
        select(
            ProjectVendorBillLine.budget_line_id,
            func.coalesce(
                func.sum(
                    ProjectVendorBillLine.net_amount
                    + func.coalesce(ProjectVendorBillLine.tax_amount, 0)
                ),
                0,
            ),
        )
        .join(ProjectVendorBill, ProjectVendorBill.id == ProjectVendorBillLine.vendor_bill_id)
        .where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
        .group_by(ProjectVendorBillLine.budget_line_id)
    ).all()
    return {row[0]: _money(row[1]) for row in rows}


def _paid_by_budget_line(db: Session, project_id: UUID) -> dict[UUID, Decimal]:
    # Allocate posted payment amounts proportionally is complex; attribute via bill lines share.
    # Practical approach: sum allocations on bills, then distribute by bill-line recognized share.
    bills = list(
        db.scalars(
            select(ProjectVendorBill).where(
                ProjectVendorBill.project_id == project_id,
                ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
            )
        ).all()
    )
    result: dict[UUID, Decimal] = {}
    for bill in bills:
        paid = _money(bill.paid_amount)
        if paid <= ZERO:
            continue
        lines = list(
            db.scalars(
                select(ProjectVendorBillLine).where(ProjectVendorBillLine.vendor_bill_id == bill.id)
            ).all()
        )
        recognized_total = sum(
            (_money(line.net_amount) + _money(line.tax_amount) for line in lines), ZERO
        )
        if recognized_total <= ZERO:
            continue
        for line in lines:
            share = (_money(line.net_amount) + _money(line.tax_amount)) / recognized_total
            result[line.budget_line_id] = result.get(line.budget_line_id, ZERO) + _money(paid * share)
    return result


def _retained_by_budget_line(db: Session, project_id: UUID) -> dict[UUID, Decimal]:
    retained_rows = db.execute(
        select(
            ProjectVendorBillLine.budget_line_id,
            func.coalesce(func.sum(ProjectVendorBillLine.retainage_amount), 0),
        )
        .join(ProjectVendorBill, ProjectVendorBill.id == ProjectVendorBillLine.vendor_bill_id)
        .where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
        .group_by(ProjectVendorBillLine.budget_line_id)
    ).all()
    retained = {row[0]: _money(row[1]) for row in retained_rows}
    released_total = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectRetainageRelease.amount), 0)).where(
                ProjectRetainageRelease.project_id == project_id,
                ProjectRetainageRelease.status == RetainageReleaseStatus.POSTED,
            )
        )
    )
    # Apply releases proportionally across retained lines when present.
    total_retained = sum(retained.values(), ZERO)
    if total_retained > ZERO and released_total > ZERO:
        for key, value in list(retained.items()):
            share = value / total_retained
            retained[key] = max(value - _money(released_total * share), ZERO)
    return retained


def project_has_normalized_cost_data(db: Session, project_id: UUID) -> bool:
    has_commitment = db.scalar(
        select(func.count())
        .select_from(ProjectCommitment)
        .where(
            ProjectCommitment.project_id == project_id,
            ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
        )
    )
    has_bill = db.scalar(
        select(func.count())
        .select_from(ProjectVendorBill)
        .where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
    )
    return bool(has_commitment or has_bill)


def project_cost_totals(db: Session, project_id: UUID) -> dict[str, Decimal]:
    committed = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectCommitment.current_committed_amount), 0)).where(
                ProjectCommitment.project_id == project_id,
                ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
            )
        )
    )
    pending = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectCommitment.current_committed_amount), 0)).where(
                ProjectCommitment.project_id == project_id,
                ProjectCommitment.status == ProjectCommitmentStatus.IN_REVIEW,
            )
        )
    )
    actual_map = _actual_by_budget_line(db, project_id)
    actual = sum(actual_map.values(), ZERO)
    paid = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectPaymentAllocation.allocated_amount), 0))
            .join(ProjectPayment, ProjectPayment.id == ProjectPaymentAllocation.payment_id)
            .where(
                ProjectPayment.project_id == project_id,
                ProjectPayment.status == ProjectPaymentStatus.POSTED,
            )
        )
    )
    retained_map = _retained_by_budget_line(db, project_id)
    retained = sum(retained_map.values(), ZERO)
    return {
        "committed_cost": committed,
        "pending_commitments": pending,
        "actual_cost": actual,
        "paid_cost": paid,
        "retained_cost": retained,
    }


def _check_budget_control(
    db: Session,
    *,
    project_id: UUID,
    commitment: ProjectCommitment,
    user: User,
    override_reason: str | None,
) -> list[str]:
    warnings: list[str] = []
    committed_map = _committed_by_budget_line(db, project_id)
    # Include this commitment's lines as if approved for the check.
    lines = list(
        db.scalars(
            select(ProjectCommitmentLine).where(
                ProjectCommitmentLine.commitment_id == commitment.id,
                ProjectCommitmentLine.is_active.is_(True),
            )
        ).all()
    )
    overages: list[dict[str, str]] = []
    for line in lines:
        budget_line = db.get(ProjectBudgetLine, line.budget_line_id)
        if budget_line is None:
            continue
        already = committed_map.get(line.budget_line_id, ZERO)
        # If commitment already counted (re-approve path), exclude its prior amount.
        if commitment.status in COMMITTED_COST_STATUSES:
            already = already - _money(line.current_amount)
        projected = already + _money(line.current_amount)
        available = _money(budget_line.current_budget) - already
        if projected > _money(budget_line.current_budget):
            overages.append(
                {
                    "budget_line_id": str(line.budget_line_id),
                    "available_to_commit": str(available),
                    "requested": str(_money(line.current_amount)),
                }
            )
    if not overages:
        return warnings

    mode = (BUDGET_CONTROL_MODE or "WARNING").upper()
    detail = {
        "message": "Commitment exceeds available budget on one or more lines",
        "mode": mode,
        "overages": overages,
    }
    if mode == "HARD_BLOCK":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    if not override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                **detail,
                "message": "Over-budget commitment requires override_reason in WARNING mode",
            },
        )
    if not cost_permissions(user).can_override_budget_control:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="override_budget_control permission required",
        )
    commitment.budget_override_reason = override_reason
    warnings.append("Budget control override applied")
    return warnings


# ---------------------------------------------------------------------------
# Vendor CRUD / project vendors
# ---------------------------------------------------------------------------


def create_vendor(
    db: Session, payload: VendorCreate, *, actor: User, request: Request | None = None
) -> VendorResponse:
    require_manage_vendors(actor)
    code = (payload.vendor_code or "").strip() or next_vendor_code(db, company_id=payload.company_id)
    vendor = Vendor(
        company_id=payload.company_id,
        name=payload.name.strip(),
        legal_name=payload.legal_name,
        vendor_code=code,
        tax_id_last4=payload.tax_id_last4,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        website=payload.website,
        vendor_type=payload.vendor_type,
        status=payload.status,
        payment_terms=payload.payment_terms,
        default_currency=payload.default_currency.upper(),
        insurance_expiration_date=payload.insurance_expiration_date,
        license_number=payload.license_number,
        license_expiration_date=payload.license_expiration_date,
        notes=payload.notes,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(vendor)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Vendor code already exists"
        ) from exc
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR,
        entity_id=vendor.id,
        description_key="activity.project_vendor.created",
        actor=actor,
        metadata={"vendor_code": vendor.vendor_code, "name": vendor.name},
        request=request,
    )
    db.commit()
    db.refresh(vendor)
    return VendorResponse.model_validate(vendor)


def update_vendor(
    db: Session,
    vendor_id: UUID,
    payload: VendorUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> VendorResponse:
    require_manage_vendors(actor)
    vendor = _load_vendor(db, vendor_id)
    before = _snap(vendor)
    data = payload.model_dump(exclude_unset=True)
    if "default_currency" in data and data["default_currency"]:
        data["default_currency"] = data["default_currency"].upper()
    if data.get("status") == VendorStatus.ARCHIVED:
        vendor.archived_at = _now()
    for key, value in data.items():
        setattr(vendor, key, value)
    vendor.updated_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR,
        entity_id=vendor.id,
        description_key="activity.project_vendor.updated",
        actor=actor,
        before=before,
        after=_snap(vendor),
        request=request,
    )
    db.commit()
    db.refresh(vendor)
    return VendorResponse.model_validate(vendor)


def list_vendors(
    db: Session,
    *,
    user: User,
    company_id: UUID | None = None,
    search: str | None = None,
    active_only: bool = True,
) -> list[VendorResponse]:
    require_view(user)
    query = select(Vendor)
    if company_id is not None:
        query = query.where(or_(Vendor.company_id == company_id, Vendor.company_id.is_(None)))
    if active_only:
        query = query.where(Vendor.status == VendorStatus.ACTIVE)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Vendor.name.ilike(term), Vendor.vendor_code.ilike(term)))
    rows = db.scalars(query.order_by(Vendor.name.asc())).all()
    return [VendorResponse.model_validate(row) for row in rows]


def list_project_vendors(
    db: Session, user: User, project_id: UUID
) -> list[ProjectVendorResponse]:
    require_view(user)
    _load_project(db, project_id)
    rows = db.execute(
        select(ProjectVendor, Vendor)
        .join(Vendor, Vendor.id == ProjectVendor.vendor_id)
        .where(ProjectVendor.project_id == project_id)
        .order_by(Vendor.name.asc())
    ).all()
    items: list[ProjectVendorResponse] = []
    for link, vendor in rows:
        item = ProjectVendorResponse.model_validate(link)
        items.append(
            item.model_copy(
                update={
                    "vendor_name": vendor.name,
                    "vendor_code": vendor.vendor_code,
                    "vendor_status": vendor.status,
                }
            )
        )
    return items


def add_project_vendor(
    db: Session,
    project_id: UUID,
    payload: ProjectVendorCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> ProjectVendorResponse:
    require_manage_vendors(actor)
    project = _load_project(db, project_id)
    vendor = _load_vendor(db, payload.vendor_id)
    if (
        project.company_id is not None
        and vendor.company_id is not None
        and project.company_id != vendor.company_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vendor and project must belong to the same company",
        )
    link = ProjectVendor(
        company_id=project.company_id,
        project_id=project_id,
        vendor_id=vendor.id,
        role=payload.role.strip() or "vendor",
        status=payload.status,
        primary_contact_id=payload.primary_contact_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
        created_by_user_id=actor.id,
    )
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project vendor role already exists",
        ) from exc
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR,
        entity_id=link.id,
        description_key="activity.project_vendor.assigned",
        actor=actor,
        metadata={"project_id": str(project_id), "vendor_id": str(vendor.id)},
        request=request,
    )
    db.commit()
    db.refresh(link)
    response = ProjectVendorResponse.model_validate(link)
    return response.model_copy(
        update={"vendor_name": vendor.name, "vendor_code": vendor.vendor_code, "vendor_status": vendor.status}
    )


def update_project_vendor(
    db: Session,
    project_id: UUID,
    project_vendor_id: UUID,
    payload: ProjectVendorUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> ProjectVendorResponse:
    require_manage_vendors(actor)
    _load_project(db, project_id)
    link = db.get(ProjectVendor, project_vendor_id)
    if link is None or link.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project vendor not found")
    before = _snap(link)
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == ProjectVendorStatus.ARCHIVED:
        link.archived_at = _now()
    for key, value in data.items():
        setattr(link, key, value)
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR,
        entity_id=link.id,
        description_key="activity.project_vendor.updated",
        actor=actor,
        before=before,
        after=_snap(link),
        request=request,
    )
    db.commit()
    db.refresh(link)
    vendor = _load_vendor(db, link.vendor_id)
    return ProjectVendorResponse.model_validate(link).model_copy(
        update={"vendor_name": vendor.name, "vendor_code": vendor.vendor_code, "vendor_status": vendor.status}
    )


def remove_project_vendor(
    db: Session,
    project_id: UUID,
    project_vendor_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_vendors(actor)
    _load_project(db, project_id)
    link = db.get(ProjectVendor, project_vendor_id)
    if link is None or link.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project vendor not found")
    before = _snap(link)
    link.status = ProjectVendorStatus.ARCHIVED
    link.archived_at = _now()
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR,
        entity_id=link.id,
        description_key="activity.project_vendor.removed",
        actor=actor,
        before=before,
        after=_snap(link),
        request=request,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------


def _to_commitment_response(
    db: Session, commitment: ProjectCommitment, *, include_lines: bool = False, warnings: list[str] | None = None
) -> CommitmentResponse:
    vendor = db.get(Vendor, commitment.vendor_id)
    data = CommitmentResponse.model_validate(commitment)
    update: dict = {
        "vendor_name": vendor.name if vendor else None,
        "budget_warnings": warnings or [],
    }
    if include_lines:
        lines = db.scalars(
            select(ProjectCommitmentLine)
            .where(ProjectCommitmentLine.commitment_id == commitment.id)
            .order_by(ProjectCommitmentLine.sort_order.asc(), ProjectCommitmentLine.line_number.asc())
        ).all()
        update["lines"] = [CommitmentLineResponse.model_validate(line) for line in lines]
    return data.model_copy(update=update)


def _add_commitment_line(
    db: Session,
    *,
    project: Project,
    commitment: ProjectCommitment,
    payload: CommitmentLineCreate,
    actor: User,
    line_number: str | None = None,
) -> ProjectCommitmentLine:
    budget_line = _load_budget_line(db, project.id, payload.budget_line_id)
    category_id = payload.category_id or budget_line.category_id
    if category_id != budget_line.category_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="category_id must match budget line category",
        )
    cost_code_id = payload.cost_code_id if payload.cost_code_id is not None else budget_line.cost_code_id
    number = line_number or payload.line_number
    if not number:
        count = db.scalar(
            select(func.count()).select_from(ProjectCommitmentLine).where(
                ProjectCommitmentLine.commitment_id == commitment.id
            )
        ) or 0
        number = str(int(count) + 1)
    amount = _money(payload.original_amount)
    if amount < ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Commitment line amount cannot be negative",
        )
    line = ProjectCommitmentLine(
        company_id=project.company_id,
        project_id=project.id,
        commitment_id=commitment.id,
        budget_line_id=budget_line.id,
        category_id=category_id,
        cost_code_id=cost_code_id,
        line_number=number,
        description=payload.description.strip(),
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=_money(payload.unit_price) if payload.unit_price is not None else None,
        original_amount=amount,
        approved_change_orders=ZERO,
        current_amount=amount,
        invoiced_amount=ZERO,
        paid_amount=ZERO,
        retained_amount=ZERO,
        remaining_amount=amount,
        tax_amount=_money(payload.tax_amount) if payload.tax_amount is not None else None,
        notes=payload.notes,
        sort_order=payload.sort_order,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(line)
    db.flush()
    return line


def create_commitment(
    db: Session,
    project_id: UUID,
    payload: CommitmentCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> CommitmentResponse:
    require_manage_commitments(actor)
    project = _load_project(db, project_id)
    vendor = _load_vendor(db, payload.vendor_id)
    _assert_vendor_usable(vendor)
    budget_version_id = payload.budget_version_id
    if budget_version_id is None:
        current = db.scalars(
            select(ProjectBudgetVersion).where(
                ProjectBudgetVersion.project_id == project_id,
                ProjectBudgetVersion.is_current.is_(True),
                ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
            )
        ).first()
        budget_version_id = current.id if current else None
    number = next_commitment_number(db, project_id=project_id, commitment_type=payload.commitment_type)
    commitment = ProjectCommitment(
        company_id=project.company_id,
        project_id=project_id,
        vendor_id=vendor.id,
        budget_version_id=budget_version_id,
        commitment_number=number,
        commitment_type=payload.commitment_type,
        title=payload.title.strip(),
        description=payload.description,
        status=ProjectCommitmentStatus.DRAFT,
        currency=payload.currency.upper(),
        executed_date=payload.executed_date,
        start_date=payload.start_date,
        end_date=payload.end_date,
        payment_terms=payload.payment_terms,
        retainage_percentage=payload.retainage_percentage,
        document_id=payload.document_id,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(commitment)
    db.flush()
    for item in payload.lines:
        _add_commitment_line(db, project=project, commitment=commitment, payload=item, actor=actor)
    _recalc_commitment(db, commitment)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=commitment.id,
        description_key="activity.project_commitment.created",
        actor=actor,
        metadata={"commitment_number": commitment.commitment_number},
        request=request,
    )
    db.commit()
    db.refresh(commitment)
    return _to_commitment_response(db, commitment, include_lines=True)


def list_commitments(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    status_filter: str | None = None,
    commitment_type: str | None = None,
    vendor_id: UUID | None = None,
    search: str | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> CommitmentListResponse:
    require_view(user)
    _load_project(db, project_id)
    query = select(ProjectCommitment).where(ProjectCommitment.project_id == project_id)
    if not include_archived:
        query = query.where(ProjectCommitment.status != ProjectCommitmentStatus.ARCHIVED)
    if status_filter:
        query = query.where(ProjectCommitment.status == status_filter)
    if commitment_type:
        query = query.where(ProjectCommitment.commitment_type == commitment_type)
    if vendor_id:
        query = query.where(ProjectCommitment.vendor_id == vendor_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                ProjectCommitment.title.ilike(term),
                ProjectCommitment.commitment_number.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ProjectCommitment.created_at.desc())
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
    ).all()
    return CommitmentListResponse(
        items=[_to_commitment_response(db, row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
        pages=_pages(int(total), page_size),
    )


def get_commitment(
    db: Session, user: User, project_id: UUID, commitment_id: UUID
) -> CommitmentResponse:
    require_view(user)
    commitment = _load_commitment(db, project_id, commitment_id)
    return _to_commitment_response(db, commitment, include_lines=True)


def update_commitment(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> CommitmentResponse:
    require_manage_commitments(actor)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    before = _snap(commitment)
    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(commitment, key, value)
    commitment.updated_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=commitment.id,
        description_key="activity.project_commitment.updated",
        actor=actor,
        before=before,
        after=_snap(commitment),
        request=request,
    )
    db.commit()
    db.refresh(commitment)
    return _to_commitment_response(db, commitment, include_lines=True)


def delete_commitment(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_commitments(actor)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    before = _snap(commitment)
    commitment.status = ProjectCommitmentStatus.CANCELLED
    commitment.cancelled_at = _now()
    commitment.cancelled_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=commitment.id,
        description_key="activity.project_commitment.cancelled",
        actor=actor,
        before=before,
        after=_snap(commitment),
        request=request,
    )
    db.commit()


def list_commitment_lines(
    db: Session, user: User, project_id: UUID, commitment_id: UUID
) -> list[CommitmentLineResponse]:
    require_view(user)
    _load_commitment(db, project_id, commitment_id)
    rows = db.scalars(
        select(ProjectCommitmentLine)
        .where(ProjectCommitmentLine.commitment_id == commitment_id)
        .order_by(ProjectCommitmentLine.sort_order.asc())
    ).all()
    return [CommitmentLineResponse.model_validate(row) for row in rows]


def add_commitment_line(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentLineCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> CommitmentLineResponse:
    require_manage_commitments(actor)
    project = _load_project(db, project_id)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    line = _add_commitment_line(
        db, project=project, commitment=commitment, payload=payload, actor=actor
    )
    _recalc_commitment(db, commitment)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=line.id,
        description_key="activity.project_commitment.line_created",
        actor=actor,
        metadata={"commitment_id": str(commitment_id)},
        request=request,
    )
    db.commit()
    db.refresh(line)
    return CommitmentLineResponse.model_validate(line)


def update_commitment_line(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    line_id: UUID,
    payload: CommitmentLineUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> CommitmentLineResponse:
    require_manage_commitments(actor)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    line = db.get(ProjectCommitmentLine, line_id)
    if line is None or line.commitment_id != commitment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment line not found")
    before = _snap(line)
    data = payload.model_dump(exclude_unset=True)
    if "budget_line_id" in data and data["budget_line_id"]:
        budget_line = _load_budget_line(db, project_id, data["budget_line_id"])
        line.budget_line_id = budget_line.id
        line.category_id = budget_line.category_id
        data.pop("budget_line_id", None)
        data.pop("category_id", None)
    if "original_amount" in data:
        data["original_amount"] = _money(data["original_amount"])
    for key, value in data.items():
        setattr(line, key, value)
    line.updated_by_user_id = actor.id
    _recalc_commitment_line(line)
    _recalc_commitment(db, commitment)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=line.id,
        description_key="activity.project_commitment.line_updated",
        actor=actor,
        before=before,
        after=_snap(line),
        request=request,
    )
    db.commit()
    db.refresh(line)
    return CommitmentLineResponse.model_validate(line)


def delete_commitment_line(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    line_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_commitments(actor)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    line = db.get(ProjectCommitmentLine, line_id)
    if line is None or line.commitment_id != commitment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment line not found")
    before = _snap(line)
    line.is_active = False
    _recalc_commitment(db, commitment)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=line.id,
        description_key="activity.project_commitment.line_removed",
        actor=actor,
        before=before,
        after=_snap(line),
        request=request,
    )
    db.commit()


def bulk_add_commitment_lines(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentLineBulkCreateRequest,
    *,
    actor: User,
    request: Request | None = None,
) -> list[CommitmentLineResponse]:
    require_manage_commitments(actor)
    project = _load_project(db, project_id)
    commitment = _load_commitment(db, project_id, commitment_id)
    assert_commitment_editable(commitment.status)
    created: list[ProjectCommitmentLine] = []
    for item in payload.lines:
        created.append(
            _add_commitment_line(db, project=project, commitment=commitment, payload=item, actor=actor)
        )
    _recalc_commitment(db, commitment)
    db.commit()
    return [CommitmentLineResponse.model_validate(row) for row in created]


def _transition_commitment(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    *,
    target: ProjectCommitmentStatus,
    actor: User,
    request: Request | None,
    approve_payload: CommitmentApproveRequest | None = None,
) -> CommitmentResponse:
    commitment = _load_commitment(db, project_id, commitment_id)
    validate_commitment_transition(commitment.status, target)
    before = _snap(commitment)
    warnings: list[str] = []

    if target == ProjectCommitmentStatus.IN_REVIEW:
        require_manage_commitments(actor)
        lines = db.scalars(
            select(ProjectCommitmentLine).where(
                ProjectCommitmentLine.commitment_id == commitment.id,
                ProjectCommitmentLine.is_active.is_(True),
            )
        ).all()
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Commitment requires at least one active line",
            )
        commitment.submitted_at = _now()
        commitment.submitted_by_user_id = actor.id
    elif target == ProjectCommitmentStatus.APPROVED:
        require_approve_commitments(actor)
        vendor = _load_vendor(db, commitment.vendor_id)
        _assert_vendor_usable(vendor)
        if commitment.budget_version_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Commitment requires a budget version",
            )
        version = db.get(ProjectBudgetVersion, commitment.budget_version_id)
        if version is None or version.status != BudgetVersionStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Budget version must be approved",
            )
        _recalc_commitment(db, commitment)
        warnings = _check_budget_control(
            db,
            project_id=project_id,
            commitment=commitment,
            user=actor,
            override_reason=approve_payload.override_reason if approve_payload else None,
        )
        commitment.approved_at = _now()
        commitment.approved_by_user_id = actor.id
    elif target == ProjectCommitmentStatus.REJECTED:
        require_approve_commitments(actor)
        commitment.rejected_at = _now()
        commitment.rejected_by_user_id = actor.id
    elif target == ProjectCommitmentStatus.EXECUTED:
        require_manage_commitments(actor)
        if commitment.executed_date is None:
            commitment.executed_date = date.today()
    elif target == ProjectCommitmentStatus.ACTIVE:
        require_manage_commitments(actor)
    elif target == ProjectCommitmentStatus.COMPLETED:
        require_manage_commitments(actor)
    elif target == ProjectCommitmentStatus.CLOSED:
        require_manage_commitments(actor)
        commitment.closed_at = _now()
        commitment.closed_by_user_id = actor.id
    elif target == ProjectCommitmentStatus.CANCELLED:
        require_manage_commitments(actor)
        if commitment.status in {
            ProjectCommitmentStatus.APPROVED,
            ProjectCommitmentStatus.ACTIVE,
        }:
            bill_count = db.scalar(
                select(func.count()).select_from(ProjectVendorBill).where(
                    ProjectVendorBill.commitment_id == commitment.id,
                    ProjectVendorBill.status != VendorBillStatus.VOID,
                )
            ) or 0
            if bill_count:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot cancel commitment with existing bills",
                )
        commitment.cancelled_at = _now()
        commitment.cancelled_by_user_id = actor.id
    else:
        require_manage_commitments(actor)

    commitment.status = target
    commitment.updated_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=commitment.id,
        description_key="activity.project_commitment.updated",
        actor=actor,
        before=before,
        after=_snap(commitment),
        request=request,
    )
    db.commit()
    db.refresh(commitment)
    return _to_commitment_response(db, commitment, include_lines=True, warnings=warnings)


def submit_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.IN_REVIEW, actor=actor, request=request
    )


def approve_commitment(
    db, project_id, commitment_id, *, actor, payload: CommitmentApproveRequest | None = None, request=None
):
    return _transition_commitment(
        db,
        project_id,
        commitment_id,
        target=ProjectCommitmentStatus.APPROVED,
        actor=actor,
        request=request,
        approve_payload=payload or CommitmentApproveRequest(),
    )


def reject_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.REJECTED, actor=actor, request=request
    )


def execute_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.EXECUTED, actor=actor, request=request
    )


def activate_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.ACTIVE, actor=actor, request=request
    )


def complete_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.COMPLETED, actor=actor, request=request
    )


def close_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.CLOSED, actor=actor, request=request
    )


def cancel_commitment(db, project_id, commitment_id, *, actor, request=None):
    return _transition_commitment(
        db, project_id, commitment_id, target=ProjectCommitmentStatus.CANCELLED, actor=actor, request=request
    )


# ---------------------------------------------------------------------------
# Change orders
# ---------------------------------------------------------------------------


def _to_change_order_response(db: Session, co: ProjectCommitmentChangeOrder) -> ChangeOrderResponse:
    lines = db.scalars(
        select(ProjectCommitmentChangeOrderLine).where(
            ProjectCommitmentChangeOrderLine.change_order_id == co.id
        )
    ).all()
    data = ChangeOrderResponse.model_validate(co)
    return data.model_copy(
        update={"lines": [ChangeOrderLineResponse_from(line) for line in lines]}
    )


def ChangeOrderLineResponse_from(line: ProjectCommitmentChangeOrderLine):
    from investhome_api.schemas.project_cost import ChangeOrderLineResponse

    return ChangeOrderLineResponse.model_validate(line)


def list_change_orders(
    db: Session, user: User, project_id: UUID, commitment_id: UUID
) -> list[ChangeOrderResponse]:
    require_view(user)
    _load_commitment(db, project_id, commitment_id)
    rows = db.scalars(
        select(ProjectCommitmentChangeOrder)
        .where(ProjectCommitmentChangeOrder.commitment_id == commitment_id)
        .order_by(ProjectCommitmentChangeOrder.created_at.desc())
    ).all()
    return [_to_change_order_response(db, row) for row in rows]


def create_change_order(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    payload: ChangeOrderCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> ChangeOrderResponse:
    require_manage_commitments(actor)
    project = _load_project(db, project_id)
    commitment = _load_commitment(db, project_id, commitment_id)
    if commitment.status not in {
        ProjectCommitmentStatus.APPROVED,
        ProjectCommitmentStatus.EXECUTED,
        ProjectCommitmentStatus.ACTIVE,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Change orders require an approved/active commitment",
        )
    number = next_change_order_number(db, commitment_id=commitment_id)
    requested = sum((_money(item.amount) for item in payload.lines), ZERO)
    co = ProjectCommitmentChangeOrder(
        company_id=project.company_id,
        project_id=project_id,
        commitment_id=commitment_id,
        change_order_number=number,
        title=payload.title.strip(),
        description=payload.description,
        reason=payload.reason,
        status=ChangeOrderStatus.DRAFT,
        requested_amount=requested,
        effective_date=payload.effective_date,
    )
    db.add(co)
    db.flush()
    for item in payload.lines:
        cline = db.get(ProjectCommitmentLine, item.commitment_line_id)
        if cline is None or cline.commitment_id != commitment_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid commitment_line_id on change order",
            )
        db.add(
            ProjectCommitmentChangeOrderLine(
                change_order_id=co.id,
                commitment_line_id=cline.id,
                budget_line_id=item.budget_line_id or cline.budget_line_id,
                description=item.description,
                amount=_money(item.amount),
                notes=item.notes,
            )
        )
    db.flush()
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=co.id,
        description_key="activity.project_commitment.change_order_created",
        actor=actor,
        metadata={"change_order_number": co.change_order_number},
        request=request,
    )
    db.commit()
    db.refresh(co)
    return _to_change_order_response(db, co)


def get_change_order(
    db: Session, user: User, project_id: UUID, commitment_id: UUID, change_order_id: UUID
) -> ChangeOrderResponse:
    require_view(user)
    _load_commitment(db, project_id, commitment_id)
    co = db.get(ProjectCommitmentChangeOrder, change_order_id)
    if co is None or co.commitment_id != commitment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change order not found")
    return _to_change_order_response(db, co)


def update_change_order(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    payload: ChangeOrderUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> ChangeOrderResponse:
    require_manage_commitments(actor)
    _load_commitment(db, project_id, commitment_id)
    co = db.get(ProjectCommitmentChangeOrder, change_order_id)
    if co is None or co.commitment_id != commitment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change order not found")
    assert_change_order_editable(co.status)
    before = _snap(co)
    data = payload.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)
    for key, value in data.items():
        setattr(co, key, value)
    if lines is not None:
        existing = db.scalars(
            select(ProjectCommitmentChangeOrderLine).where(
                ProjectCommitmentChangeOrderLine.change_order_id == co.id
            )
        ).all()
        for row in existing:
            db.delete(row)
        db.flush()
        requested = ZERO
        for item in lines:
            parsed = ChangeOrderLineInput.model_validate(item)
            cline = db.get(ProjectCommitmentLine, parsed.commitment_line_id)
            if cline is None or cline.commitment_id != commitment_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid commitment_line_id on change order",
                )
            amount = _money(parsed.amount)
            requested += amount
            db.add(
                ProjectCommitmentChangeOrderLine(
                    change_order_id=co.id,
                    commitment_line_id=cline.id,
                    budget_line_id=parsed.budget_line_id or cline.budget_line_id,
                    description=parsed.description,
                    amount=amount,
                    notes=parsed.notes,
                )
            )
        co.requested_amount = requested
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=co.id,
        description_key="activity.project_commitment.change_order_updated",
        actor=actor,
        before=before,
        after=_snap(co),
        request=request,
    )
    db.commit()
    db.refresh(co)
    return _to_change_order_response(db, co)


def _transition_change_order(
    db: Session,
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    *,
    target: ChangeOrderStatus,
    actor: User,
    request: Request | None,
) -> ChangeOrderResponse:
    commitment = _load_commitment(db, project_id, commitment_id)
    co = db.get(ProjectCommitmentChangeOrder, change_order_id)
    if co is None or co.commitment_id != commitment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change order not found")
    validate_change_order_transition(co.status, target)
    before = _snap(co)

    if target == ChangeOrderStatus.IN_REVIEW:
        require_manage_commitments(actor)
        co.submitted_at = _now()
        co.submitted_by_user_id = actor.id
    elif target == ChangeOrderStatus.APPROVED:
        require_approve_commitments(actor)
        if co.applied_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Change order already applied"
            )
        lines = list(
            db.scalars(
                select(ProjectCommitmentChangeOrderLine).where(
                    ProjectCommitmentChangeOrderLine.change_order_id == co.id
                )
            ).all()
        )
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Change order has no lines",
            )
        approved_total = ZERO
        for item in lines:
            cline = db.get(ProjectCommitmentLine, item.commitment_line_id)
            if cline is None:
                continue
            cline.approved_change_orders = _money(cline.approved_change_orders) + _money(item.amount)
            _recalc_commitment_line(cline)
            approved_total += _money(item.amount)
        co.approved_amount = approved_total
        co.approved_at = _now()
        co.approved_by_user_id = actor.id
        co.applied_at = _now()
        _recalc_commitment(db, commitment)
    elif target == ChangeOrderStatus.REJECTED:
        require_approve_commitments(actor)
        co.rejected_at = _now()
        co.rejected_by_user_id = actor.id
    elif target == ChangeOrderStatus.CANCELLED:
        require_manage_commitments(actor)
        co.cancelled_at = _now()
        co.cancelled_by_user_id = actor.id

    co.status = target
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_COMMITMENT,
        entity_id=co.id,
        description_key="activity.project_commitment.change_order_updated",
        actor=actor,
        before=before,
        after=_snap(co),
        request=request,
    )
    db.commit()
    db.refresh(co)
    return _to_change_order_response(db, co)


def submit_change_order(db, project_id, commitment_id, change_order_id, *, actor, request=None):
    return _transition_change_order(
        db, project_id, commitment_id, change_order_id,
        target=ChangeOrderStatus.IN_REVIEW, actor=actor, request=request,
    )


def approve_change_order(db, project_id, commitment_id, change_order_id, *, actor, request=None):
    return _transition_change_order(
        db, project_id, commitment_id, change_order_id,
        target=ChangeOrderStatus.APPROVED, actor=actor, request=request,
    )


def reject_change_order(db, project_id, commitment_id, change_order_id, *, actor, request=None):
    return _transition_change_order(
        db, project_id, commitment_id, change_order_id,
        target=ChangeOrderStatus.REJECTED, actor=actor, request=request,
    )


def cancel_change_order(db, project_id, commitment_id, change_order_id, *, actor, request=None):
    return _transition_change_order(
        db, project_id, commitment_id, change_order_id,
        target=ChangeOrderStatus.CANCELLED, actor=actor, request=request,
    )


# ---------------------------------------------------------------------------
# Vendor bills
# ---------------------------------------------------------------------------


def _to_bill_response(
    db: Session, bill: ProjectVendorBill, *, include_lines: bool = False
) -> VendorBillResponse:
    vendor = db.get(Vendor, bill.vendor_id)
    data = VendorBillResponse.model_validate(bill)
    update: dict = {
        "vendor_name": vendor.name if vendor else None,
        "is_overdue": _bill_is_overdue(bill),
    }
    if include_lines:
        lines = db.scalars(
            select(ProjectVendorBillLine)
            .where(ProjectVendorBillLine.vendor_bill_id == bill.id)
            .order_by(ProjectVendorBillLine.sort_order.asc())
        ).all()
        update["lines"] = [VendorBillLineResponse.model_validate(line) for line in lines]
    return data.model_copy(update=update)


def _add_bill_line(
    db: Session,
    *,
    project: Project,
    bill: ProjectVendorBill,
    payload: VendorBillLineCreate,
    actor: User,
) -> ProjectVendorBillLine:
    budget_line = _load_budget_line(db, project.id, payload.budget_line_id)
    category_id = payload.category_id or budget_line.category_id
    if category_id != budget_line.category_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="category_id must match budget line category",
        )
    commitment_id = payload.commitment_id or bill.commitment_id
    if payload.commitment_line_id:
        cline = db.get(ProjectCommitmentLine, payload.commitment_line_id)
        if cline is None or cline.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid commitment_line_id",
            )
        commitment_id = cline.commitment_id
    count = db.scalar(
        select(func.count()).select_from(ProjectVendorBillLine).where(
            ProjectVendorBillLine.vendor_bill_id == bill.id
        )
    ) or 0
    number = payload.line_number or str(int(count) + 1)
    gross = _money(payload.gross_amount)
    retainage = _money(payload.retainage_amount)
    if retainage > gross:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Retainage cannot exceed gross amount",
        )
    line = ProjectVendorBillLine(
        company_id=project.company_id,
        project_id=project.id,
        vendor_bill_id=bill.id,
        commitment_id=commitment_id,
        commitment_line_id=payload.commitment_line_id,
        budget_line_id=budget_line.id,
        category_id=category_id,
        cost_code_id=payload.cost_code_id or budget_line.cost_code_id,
        line_number=number,
        description=payload.description.strip(),
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=_money(payload.unit_price) if payload.unit_price is not None else None,
        gross_amount=gross,
        retainage_amount=retainage,
        net_amount=gross - retainage,
        tax_amount=_money(payload.tax_amount) if payload.tax_amount is not None else None,
        previously_billed_amount=_money(payload.previously_billed_amount),
        current_billed_amount=gross,
        stored_materials_amount=(
            _money(payload.stored_materials_amount)
            if payload.stored_materials_amount is not None
            else None
        ),
        notes=payload.notes,
        sort_order=payload.sort_order,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(line)
    db.flush()
    return line


def create_vendor_bill(
    db: Session,
    project_id: UUID,
    payload: VendorBillCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> VendorBillResponse:
    require_manage_bills(actor)
    project = _load_project(db, project_id)
    vendor = _load_vendor(db, payload.vendor_id)
    _assert_vendor_usable(vendor)
    if payload.commitment_id:
        commitment = _load_commitment(db, project_id, payload.commitment_id)
        if commitment.vendor_id != vendor.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Commitment vendor must match bill vendor",
            )
    number = next_bill_number(db, project_id=project_id)
    bill = ProjectVendorBill(
        company_id=project.company_id,
        project_id=project_id,
        vendor_id=vendor.id,
        commitment_id=payload.commitment_id,
        bill_number=number,
        vendor_invoice_number=payload.vendor_invoice_number.strip(),
        status=VendorBillStatus.DRAFT,
        currency=payload.currency.upper(),
        invoice_date=payload.invoice_date,
        received_date=payload.received_date,
        due_date=payload.due_date,
        billing_period_start=payload.billing_period_start,
        billing_period_end=payload.billing_period_end,
        payment_terms=payload.payment_terms,
        description=payload.description,
        document_id=payload.document_id,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(bill)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate vendor invoice number",
        ) from exc
    for item in payload.lines:
        _add_bill_line(db, project=project, bill=bill, payload=item, actor=actor)
    _recalc_bill(db, bill)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=bill.id,
        description_key="activity.project_vendor_bill.created",
        actor=actor,
        metadata={"bill_number": bill.bill_number},
        request=request,
    )
    db.commit()
    db.refresh(bill)
    return _to_bill_response(db, bill, include_lines=True)


def list_vendor_bills(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    status_filter: str | None = None,
    vendor_id: UUID | None = None,
    commitment_id: UUID | None = None,
    overdue: bool | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> VendorBillListResponse:
    require_view(user)
    _load_project(db, project_id)
    query = select(ProjectVendorBill).where(ProjectVendorBill.project_id == project_id)
    if status_filter:
        query = query.where(ProjectVendorBill.status == status_filter)
    if vendor_id:
        query = query.where(ProjectVendorBill.vendor_id == vendor_id)
    if commitment_id:
        query = query.where(ProjectVendorBill.commitment_id == commitment_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                ProjectVendorBill.bill_number.ilike(term),
                ProjectVendorBill.vendor_invoice_number.ilike(term),
            )
        )
    rows = list(db.scalars(query.order_by(ProjectVendorBill.created_at.desc())).all())
    if overdue is True:
        rows = [row for row in rows if _bill_is_overdue(row)]
    elif overdue is False:
        rows = [row for row in rows if not _bill_is_overdue(row)]
    total = len(rows)
    start = max(page - 1, 0) * page_size
    page_rows = rows[start : start + page_size]
    return VendorBillListResponse(
        items=[_to_bill_response(db, row) for row in page_rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
    )


def get_vendor_bill(
    db: Session, user: User, project_id: UUID, bill_id: UUID
) -> VendorBillResponse:
    require_view(user)
    bill = _load_bill(db, project_id, bill_id)
    return _to_bill_response(db, bill, include_lines=True)


def update_vendor_bill(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> VendorBillResponse:
    require_manage_bills(actor)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    before = _snap(bill)
    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(bill, key, value)
    bill.updated_by_user_id = actor.id
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Duplicate vendor invoice number"
        ) from exc
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=bill.id,
        description_key="activity.project_vendor_bill.updated",
        actor=actor,
        before=before,
        after=_snap(bill),
        request=request,
    )
    db.commit()
    db.refresh(bill)
    return _to_bill_response(db, bill, include_lines=True)


def delete_vendor_bill(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_bills(actor)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    before = _snap(bill)
    bill.status = VendorBillStatus.VOID
    bill.voided_at = _now()
    bill.voided_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=bill.id,
        description_key="activity.project_vendor_bill.voided",
        actor=actor,
        before=before,
        after=_snap(bill),
        request=request,
    )
    db.commit()


def list_bill_lines(
    db: Session, user: User, project_id: UUID, bill_id: UUID
) -> list[VendorBillLineResponse]:
    require_view(user)
    _load_bill(db, project_id, bill_id)
    rows = db.scalars(
        select(ProjectVendorBillLine).where(ProjectVendorBillLine.vendor_bill_id == bill_id)
    ).all()
    return [VendorBillLineResponse.model_validate(row) for row in rows]


def add_bill_line(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillLineCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> VendorBillLineResponse:
    require_manage_bills(actor)
    project = _load_project(db, project_id)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    line = _add_bill_line(db, project=project, bill=bill, payload=payload, actor=actor)
    _recalc_bill(db, bill)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=line.id,
        description_key="activity.project_vendor_bill.line_created",
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(line)
    return VendorBillLineResponse.model_validate(line)


def update_bill_line(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    line_id: UUID,
    payload: VendorBillLineUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> VendorBillLineResponse:
    require_manage_bills(actor)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    line = db.get(ProjectVendorBillLine, line_id)
    if line is None or line.vendor_bill_id != bill_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill line not found")
    before = _snap(line)
    data = payload.model_dump(exclude_unset=True)
    for money_key in ("gross_amount", "retainage_amount", "tax_amount", "previously_billed_amount"):
        if money_key in data and data[money_key] is not None:
            data[money_key] = _money(data[money_key])
    if "budget_line_id" in data and data["budget_line_id"]:
        budget_line = _load_budget_line(db, project_id, data["budget_line_id"])
        line.budget_line_id = budget_line.id
        line.category_id = budget_line.category_id
        data.pop("budget_line_id", None)
        data.pop("category_id", None)
    for key, value in data.items():
        setattr(line, key, value)
    _recalc_bill_line(line)
    _recalc_bill(db, bill)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=line.id,
        description_key="activity.project_vendor_bill.line_updated",
        actor=actor,
        before=before,
        after=_snap(line),
        request=request,
    )
    db.commit()
    db.refresh(line)
    return VendorBillLineResponse.model_validate(line)


def delete_bill_line(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    line_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_bills(actor)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    line = db.get(ProjectVendorBillLine, line_id)
    if line is None or line.vendor_bill_id != bill_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill line not found")
    db.delete(line)
    db.flush()
    _recalc_bill(db, bill)
    db.commit()


def bulk_add_bill_lines(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillLineBulkCreateRequest,
    *,
    actor: User,
    request: Request | None = None,
) -> list[VendorBillLineResponse]:
    require_manage_bills(actor)
    project = _load_project(db, project_id)
    bill = _load_bill(db, project_id, bill_id)
    assert_bill_editable(bill.status)
    created = [
        _add_bill_line(db, project=project, bill=bill, payload=item, actor=actor)
        for item in payload.lines
    ]
    _recalc_bill(db, bill)
    db.commit()
    return [VendorBillLineResponse.model_validate(row) for row in created]


def _transition_bill(
    db: Session,
    project_id: UUID,
    bill_id: UUID,
    *,
    target: VendorBillStatus,
    actor: User,
    request: Request | None,
) -> VendorBillResponse:
    bill = _load_bill(db, project_id, bill_id)
    validate_bill_transition(bill.status, target)
    before = _snap(bill)

    if target == VendorBillStatus.IN_REVIEW:
        require_manage_bills(actor)
        lines = db.scalars(
            select(ProjectVendorBillLine).where(ProjectVendorBillLine.vendor_bill_id == bill.id)
        ).all()
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Bill requires at least one line",
            )
        _recalc_bill(db, bill)
        bill.submitted_at = _now()
        bill.submitted_by_user_id = actor.id
    elif target == VendorBillStatus.APPROVED:
        require_approve_bills(actor)
        vendor = _load_vendor(db, bill.vendor_id)
        if vendor.status == VendorStatus.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vendor is blocked"
            )
        _recalc_bill(db, bill)
        bill.approved_at = _now()
        bill.approved_by_user_id = actor.id
    elif target == VendorBillStatus.REJECTED:
        require_approve_bills(actor)
        bill.rejected_at = _now()
        bill.rejected_by_user_id = actor.id
    elif target == VendorBillStatus.POSTED:
        require_post_bills(actor)
        if bill.posted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Bill already posted"
            )
        _recalc_bill(db, bill)
        bill.posted_at = _now()
        bill.posted_by_user_id = actor.id
    elif target == VendorBillStatus.VOID:
        require_manage_bills(actor)
        if bill.status in POSTED_BILL_STATUSES and _money(bill.paid_amount) > ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot void a paid bill; void payments first",
            )
        bill.voided_at = _now()
        bill.voided_by_user_id = actor.id

    bill.status = target
    bill.updated_by_user_id = actor.id
    db.flush()
    # Sync commitment invoiced/retained after status is visible to POSTED filters.
    if bill.commitment_id and target in {
        VendorBillStatus.POSTED,
        VendorBillStatus.VOID,
        VendorBillStatus.PARTIALLY_PAID,
        VendorBillStatus.PAID,
    }:
        commitment = _load_commitment(db, project_id, bill.commitment_id)
        _sync_commitment_invoiced_from_bills(db, commitment)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_VENDOR_BILL,
        entity_id=bill.id,
        description_key="activity.project_vendor_bill.updated",
        actor=actor,
        before=before,
        after=_snap(bill),
        request=request,
    )
    db.commit()
    db.refresh(bill)
    return _to_bill_response(db, bill, include_lines=True)


def submit_vendor_bill(db, project_id, bill_id, *, actor, request=None):
    return _transition_bill(
        db, project_id, bill_id, target=VendorBillStatus.IN_REVIEW, actor=actor, request=request
    )


def approve_vendor_bill(db, project_id, bill_id, *, actor, request=None):
    return _transition_bill(
        db, project_id, bill_id, target=VendorBillStatus.APPROVED, actor=actor, request=request
    )


def reject_vendor_bill(db, project_id, bill_id, *, actor, request=None):
    return _transition_bill(
        db, project_id, bill_id, target=VendorBillStatus.REJECTED, actor=actor, request=request
    )


def post_vendor_bill(db, project_id, bill_id, *, actor, request=None):
    return _transition_bill(
        db, project_id, bill_id, target=VendorBillStatus.POSTED, actor=actor, request=request
    )


def void_vendor_bill(db, project_id, bill_id, *, actor, request=None):
    return _transition_bill(
        db, project_id, bill_id, target=VendorBillStatus.VOID, actor=actor, request=request
    )


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


def _allocation_total(db: Session, payment_id: UUID) -> Decimal:
    return _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectPaymentAllocation.allocated_amount), 0)).where(
                ProjectPaymentAllocation.payment_id == payment_id
            )
        )
    )


def _to_payment_response(
    db: Session, payment: ProjectPayment, *, include_allocations: bool = False
) -> PaymentResponse:
    vendor = db.get(Vendor, payment.vendor_id)
    allocated = _allocation_total(db, payment.id)
    data = PaymentResponse.model_validate(payment)
    update: dict = {
        "vendor_name": vendor.name if vendor else None,
        "allocated_amount": allocated,
        "unallocated_amount": _money(payment.gross_amount) - allocated,
    }
    if include_allocations:
        rows = db.scalars(
            select(ProjectPaymentAllocation).where(ProjectPaymentAllocation.payment_id == payment.id)
        ).all()
        update["allocations"] = [PaymentAllocationResponse.model_validate(row) for row in rows]
    return data.model_copy(update=update)


def _refresh_bill_paid_status(db: Session, bill: ProjectVendorBill) -> None:
    paid = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectPaymentAllocation.allocated_amount), 0))
            .join(ProjectPayment, ProjectPayment.id == ProjectPaymentAllocation.payment_id)
            .where(
                ProjectPaymentAllocation.vendor_bill_id == bill.id,
                ProjectPayment.status == ProjectPaymentStatus.POSTED,
            )
        )
    )
    bill.paid_amount = paid
    bill.balance_due = _money(bill.approved_amount) - paid
    if bill.status in POSTED_BILL_STATUSES or bill.status in {
        VendorBillStatus.PARTIALLY_PAID,
        VendorBillStatus.PAID,
    }:
        if paid <= ZERO:
            if bill.status != VendorBillStatus.VOID:
                bill.status = VendorBillStatus.POSTED
        elif paid < _money(bill.approved_amount):
            bill.status = VendorBillStatus.PARTIALLY_PAID
        else:
            bill.status = VendorBillStatus.PAID
    db.flush()


def create_payment(
    db: Session,
    project_id: UUID,
    payload: PaymentCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> PaymentResponse:
    require_manage_payments(actor)
    project = _load_project(db, project_id)
    vendor = _load_vendor(db, payload.vendor_id)
    number = next_payment_number(db, project_id=project_id)
    payment = ProjectPayment(
        company_id=project.company_id,
        project_id=project_id,
        vendor_id=vendor.id,
        payment_number=number,
        payment_date=payload.payment_date,
        status=ProjectPaymentStatus.DRAFT,
        payment_method=payload.payment_method,
        currency=payload.currency.upper(),
        gross_amount=_money(payload.gross_amount),
        reference_number=payload.reference_number,
        memo=payload.memo,
        document_id=payload.document_id,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(payment)
    db.flush()
    for item in payload.allocations:
        _add_allocation(db, project=project, payment=payment, payload=item, actor=actor)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_PAYMENT,
        entity_id=payment.id,
        description_key="activity.project_payment.created",
        actor=actor,
        metadata={"payment_number": payment.payment_number},
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return _to_payment_response(db, payment, include_allocations=True)


def _add_allocation(
    db: Session,
    *,
    project: Project,
    payment: ProjectPayment,
    payload: PaymentAllocationCreate,
    actor: User,
) -> ProjectPaymentAllocation:
    bill = _load_bill(db, project.id, payload.vendor_bill_id)
    if bill.vendor_id != payment.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment and bill vendor must match",
        )
    if bill.currency != payment.currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment and bill currency must match",
        )
    amount = _money(payload.allocated_amount)
    if amount <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Allocation amount must be positive",
        )
    if amount > _money(bill.balance_due) and payment.status == ProjectPaymentStatus.DRAFT:
        # Allow draft over-balance check against approved_amount - paid for draft payments
        available = _money(bill.approved_amount) - _money(bill.paid_amount)
        if amount > available:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Allocation exceeds bill balance due",
            )
    allocated = _allocation_total(db, payment.id)
    if allocated + amount > _money(payment.gross_amount):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Total allocations exceed payment amount",
        )
    row = ProjectPaymentAllocation(
        company_id=project.company_id,
        payment_id=payment.id,
        vendor_bill_id=bill.id,
        project_id=project.id,
        allocated_amount=amount,
        retainage_release_amount=_money(payload.retainage_release_amount),
        discount_amount=(
            _money(payload.discount_amount) if payload.discount_amount is not None else None
        ),
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    return row


def list_payments(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    status_filter: str | None = None,
    vendor_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaymentListResponse:
    require_view(user)
    _load_project(db, project_id)
    query = select(ProjectPayment).where(ProjectPayment.project_id == project_id)
    if status_filter:
        query = query.where(ProjectPayment.status == status_filter)
    if vendor_id:
        query = query.where(ProjectPayment.vendor_id == vendor_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                ProjectPayment.payment_number.ilike(term),
                ProjectPayment.reference_number.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ProjectPayment.created_at.desc())
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
    ).all()
    return PaymentListResponse(
        items=[_to_payment_response(db, row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
        pages=_pages(int(total), page_size),
    )


def get_payment(
    db: Session, user: User, project_id: UUID, payment_id: UUID
) -> PaymentResponse:
    require_view(user)
    payment = _load_payment(db, project_id, payment_id)
    return _to_payment_response(db, payment, include_allocations=True)


def update_payment(
    db: Session,
    project_id: UUID,
    payment_id: UUID,
    payload: PaymentUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> PaymentResponse:
    require_manage_payments(actor)
    payment = _load_payment(db, project_id, payment_id)
    assert_payment_editable(payment.status)
    before = _snap(payment)
    data = payload.model_dump(exclude_unset=True)
    if "gross_amount" in data:
        data["gross_amount"] = _money(data["gross_amount"])
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(payment, key, value)
    payment.updated_by_user_id = actor.id
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_PAYMENT,
        entity_id=payment.id,
        description_key="activity.project_payment.updated",
        actor=actor,
        before=before,
        after=_snap(payment),
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return _to_payment_response(db, payment, include_allocations=True)


def list_allocations(
    db: Session, user: User, project_id: UUID, payment_id: UUID
) -> list[PaymentAllocationResponse]:
    require_view(user)
    _load_payment(db, project_id, payment_id)
    rows = db.scalars(
        select(ProjectPaymentAllocation).where(ProjectPaymentAllocation.payment_id == payment_id)
    ).all()
    return [PaymentAllocationResponse.model_validate(row) for row in rows]


def add_allocation(
    db: Session,
    project_id: UUID,
    payment_id: UUID,
    payload: PaymentAllocationCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> PaymentAllocationResponse:
    require_manage_payments(actor)
    project = _load_project(db, project_id)
    payment = _load_payment(db, project_id, payment_id)
    assert_payment_editable(payment.status)
    row = _add_allocation(db, project=project, payment=payment, payload=payload, actor=actor)
    db.commit()
    db.refresh(row)
    return PaymentAllocationResponse.model_validate(row)


def delete_allocation(
    db: Session,
    project_id: UUID,
    payment_id: UUID,
    allocation_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    require_manage_payments(actor)
    payment = _load_payment(db, project_id, payment_id)
    assert_payment_editable(payment.status)
    row = db.get(ProjectPaymentAllocation, allocation_id)
    if row is None or row.payment_id != payment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    db.delete(row)
    db.commit()


def post_payment(
    db: Session,
    project_id: UUID,
    payment_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> PaymentResponse:
    require_post_payments(actor)
    payment = _load_payment(db, project_id, payment_id)
    validate_payment_transition(payment.status, ProjectPaymentStatus.POSTED)
    before = _snap(payment)
    allocations = list(
        db.scalars(
            select(ProjectPaymentAllocation).where(ProjectPaymentAllocation.payment_id == payment.id)
        ).all()
    )
    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment requires at least one allocation",
        )
    if _allocation_total(db, payment.id) > _money(payment.gross_amount):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Allocations exceed payment amount",
        )
    payment.status = ProjectPaymentStatus.POSTED
    payment.posted_at = _now()
    payment.posted_by_user_id = actor.id
    db.flush()
    for allocation in allocations:
        bill = _load_bill(db, project_id, allocation.vendor_bill_id)
        if bill.status not in POSTED_BILL_STATUSES and bill.status not in {
            VendorBillStatus.PARTIALLY_PAID,
            VendorBillStatus.PAID,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Can only allocate posted payments to posted bills",
            )
        _refresh_bill_paid_status(db, bill)
        if bill.commitment_id:
            commitment = _load_commitment(db, project_id, bill.commitment_id)
            _sync_commitment_invoiced_from_bills(db, commitment)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_PAYMENT,
        entity_id=payment.id,
        description_key="activity.project_payment.updated",
        actor=actor,
        before=before,
        after=_snap(payment),
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return _to_payment_response(db, payment, include_allocations=True)


def void_payment(
    db: Session,
    project_id: UUID,
    payment_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> PaymentResponse:
    require_post_payments(actor)
    payment = _load_payment(db, project_id, payment_id)
    validate_payment_transition(payment.status, ProjectPaymentStatus.VOID)
    before = _snap(payment)
    was_posted = payment.status == ProjectPaymentStatus.POSTED
    allocations = list(
        db.scalars(
            select(ProjectPaymentAllocation).where(ProjectPaymentAllocation.payment_id == payment.id)
        ).all()
    )
    payment.status = ProjectPaymentStatus.VOID
    payment.voided_at = _now()
    payment.voided_by_user_id = actor.id
    db.flush()
    if was_posted:
        for allocation in allocations:
            bill = _load_bill(db, project_id, allocation.vendor_bill_id)
            _refresh_bill_paid_status(db, bill)
            if bill.commitment_id:
                commitment = _load_commitment(db, project_id, bill.commitment_id)
                _sync_commitment_invoiced_from_bills(db, commitment)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_PAYMENT,
        entity_id=payment.id,
        description_key="activity.project_payment.updated",
        actor=actor,
        before=before,
        after=_snap(payment),
        request=request,
    )
    db.commit()
    db.refresh(payment)
    return _to_payment_response(db, payment, include_allocations=True)


# ---------------------------------------------------------------------------
# Retainage
# ---------------------------------------------------------------------------


def get_retainage_summary(
    db: Session, user: User, project_id: UUID
) -> RetainageSummaryResponse:
    require_view(user)
    _load_project(db, project_id)
    retained_map = _retained_by_budget_line(db, project_id)
    total_retained = sum(retained_map.values(), ZERO)
    total_released = _money(
        db.scalar(
            select(func.coalesce(func.sum(ProjectRetainageRelease.amount), 0)).where(
                ProjectRetainageRelease.project_id == project_id,
                ProjectRetainageRelease.status == RetainageReleaseStatus.POSTED,
            )
        )
    )
    by_vendor_rows = db.execute(
        select(
            ProjectVendorBill.vendor_id,
            Vendor.name,
            func.coalesce(func.sum(ProjectVendorBill.retainage_amount), 0),
        )
        .join(Vendor, Vendor.id == ProjectVendorBill.vendor_id)
        .where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
        .group_by(ProjectVendorBill.vendor_id, Vendor.name)
    ).all()
    by_commitment_rows = db.execute(
        select(
            ProjectCommitment.id,
            ProjectCommitment.commitment_number,
            ProjectCommitment.retained_amount,
        ).where(ProjectCommitment.project_id == project_id)
    ).all()
    return RetainageSummaryResponse(
        total_retained=metric(total_retained),
        total_released=metric(total_released),
        outstanding_retainage=metric(max(total_retained, ZERO)),
        by_vendor=[
            {"vendor_id": str(row[0]), "vendor_name": row[1], "retained": str(_money(row[2]))}
            for row in by_vendor_rows
        ],
        by_commitment=[
            {
                "commitment_id": str(row[0]),
                "commitment_number": row[1],
                "retained": str(_money(row[2])),
            }
            for row in by_commitment_rows
            if _money(row[2]) > ZERO
        ],
    )


def list_retainage_releases(
    db: Session, user: User, project_id: UUID
) -> list[RetainageReleaseResponse]:
    require_view(user)
    _load_project(db, project_id)
    rows = db.scalars(
        select(ProjectRetainageRelease)
        .where(ProjectRetainageRelease.project_id == project_id)
        .order_by(ProjectRetainageRelease.created_at.desc())
    ).all()
    return [RetainageReleaseResponse.model_validate(row) for row in rows]


def create_retainage_release(
    db: Session,
    project_id: UUID,
    payload: RetainageReleaseCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> RetainageReleaseResponse:
    require_manage_retainage(actor)
    project = _load_project(db, project_id)
    commitment = _load_commitment(db, project_id, payload.commitment_id)
    vendor = _load_vendor(db, payload.vendor_id)
    if commitment.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Retainage release vendor must match commitment vendor",
        )
    amount = _money(payload.amount)
    if amount <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Release amount must be positive",
        )
    outstanding = _money(commitment.retained_amount)
    if amount > outstanding:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Release exceeds retained balance",
        )
    number = next_retainage_release_number(db, project_id=project_id)
    row = ProjectRetainageRelease(
        company_id=project.company_id,
        project_id=project_id,
        vendor_id=vendor.id,
        commitment_id=commitment.id,
        vendor_bill_id=payload.vendor_bill_id,
        release_number=number,
        status=RetainageReleaseStatus.DRAFT,
        release_date=payload.release_date,
        amount=amount,
        description=payload.description,
        document_id=payload.document_id,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    log_entity_created(
        db,
        entity_type=ActivityEntityType.PROJECT_RETAINAGE_RELEASE,
        entity_id=row.id,
        description_key="activity.project_retainage_release.created",
        actor=actor,
        metadata={"release_number": row.release_number},
        request=request,
    )
    db.commit()
    db.refresh(row)
    return RetainageReleaseResponse.model_validate(row)


def _transition_retainage(
    db: Session,
    project_id: UUID,
    release_id: UUID,
    *,
    target: RetainageReleaseStatus,
    actor: User,
    request: Request | None,
) -> RetainageReleaseResponse:
    row = db.get(ProjectRetainageRelease, release_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Retainage release not found"
        )
    validate_retainage_transition(row.status, target)
    before = _snap(row)
    commitment = _load_commitment(db, project_id, row.commitment_id)

    if target == RetainageReleaseStatus.IN_REVIEW:
        require_manage_retainage(actor)
        row.submitted_at = _now()
        row.submitted_by_user_id = actor.id
    elif target == RetainageReleaseStatus.APPROVED:
        require_approve_retainage(actor)
        if _money(row.amount) > _money(commitment.retained_amount):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Release exceeds retained balance",
            )
        row.approved_at = _now()
        row.approved_by_user_id = actor.id
    elif target == RetainageReleaseStatus.REJECTED:
        require_approve_retainage(actor)
        row.rejected_at = _now()
        row.rejected_by_user_id = actor.id
    elif target == RetainageReleaseStatus.POSTED:
        require_approve_retainage(actor)
        if row.posted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Retainage release already posted"
            )
        if _money(row.amount) > _money(commitment.retained_amount):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Release exceeds retained balance",
            )
        row.posted_at = _now()
        row.posted_by_user_id = actor.id
        commitment.retained_amount = _money(commitment.retained_amount) - _money(row.amount)
        if commitment.retained_amount < ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Retainage cannot become negative",
            )
    elif target == RetainageReleaseStatus.VOID:
        require_manage_retainage(actor)
        if row.status == RetainageReleaseStatus.POSTED:
            commitment.retained_amount = _money(commitment.retained_amount) + _money(row.amount)
        row.voided_at = _now()
        row.voided_by_user_id = actor.id

    row.status = target
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT_RETAINAGE_RELEASE,
        entity_id=row.id,
        description_key="activity.project_retainage_release.updated",
        actor=actor,
        before=before,
        after=_snap(row),
        request=request,
    )
    db.commit()
    db.refresh(row)
    return RetainageReleaseResponse.model_validate(row)


def submit_retainage_release(db, project_id, release_id, *, actor, request=None):
    return _transition_retainage(
        db, project_id, release_id, target=RetainageReleaseStatus.IN_REVIEW, actor=actor, request=request
    )


def approve_retainage_release(db, project_id, release_id, *, actor, request=None):
    return _transition_retainage(
        db, project_id, release_id, target=RetainageReleaseStatus.APPROVED, actor=actor, request=request
    )


def reject_retainage_release(db, project_id, release_id, *, actor, request=None):
    return _transition_retainage(
        db, project_id, release_id, target=RetainageReleaseStatus.REJECTED, actor=actor, request=request
    )


def post_retainage_release(db, project_id, release_id, *, actor, request=None):
    return _transition_retainage(
        db, project_id, release_id, target=RetainageReleaseStatus.POSTED, actor=actor, request=request
    )


def void_retainage_release(db, project_id, release_id, *, actor, request=None):
    return _transition_retainage(
        db, project_id, release_id, target=RetainageReleaseStatus.VOID, actor=actor, request=request
    )


# ---------------------------------------------------------------------------
# Cost rollups / exports
# ---------------------------------------------------------------------------


def cost_by_budget_line(
    db: Session, user: User, project_id: UUID
) -> list[CostByBudgetLineRow]:
    require_view(user)
    _load_project(db, project_id)
    version = db.scalars(
        select(ProjectBudgetVersion).where(
            ProjectBudgetVersion.project_id == project_id,
            ProjectBudgetVersion.is_current.is_(True),
            ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
        )
    ).first()
    if version is None:
        return []
    lines = list(
        db.scalars(
            select(ProjectBudgetLine).where(
                ProjectBudgetLine.budget_version_id == version.id,
                ProjectBudgetLine.is_active.is_(True),
                ProjectBudgetLine.is_summary.is_(False),
            )
        ).all()
    )
    committed = _committed_by_budget_line(db, project_id)
    pending = _pending_by_budget_line(db, project_id)
    actual = _actual_by_budget_line(db, project_id)
    paid = _paid_by_budget_line(db, project_id)
    retained = _retained_by_budget_line(db, project_id)
    rows: list[CostByBudgetLineRow] = []
    for line in lines:
        current = _money(line.current_budget)
        c = committed.get(line.id, ZERO)
        a = actual.get(line.id, ZERO)
        remaining_commitment = max(c - a, ZERO)
        forecast = a + remaining_commitment
        rows.append(
            CostByBudgetLineRow(
                budget_line_id=line.id,
                line_number=line.line_number,
                name=line.name,
                category_id=line.category_id,
                current_budget=current,
                committed_cost=c,
                pending_commitments=pending.get(line.id, ZERO),
                actual_cost=a,
                paid_cost=paid.get(line.id, ZERO),
                retained_cost=retained.get(line.id, ZERO),
                remaining_budget=current - a,
                available_to_commit=current - c,
                basic_forecast_at_completion=forecast,
                projected_variance=current - forecast,
            )
        )
    return rows


def cost_by_category(db: Session, user: User, project_id: UUID) -> list[CostByCategoryRow]:
    require_view(user)
    line_rows = cost_by_budget_line(db, user, project_id)
    if not line_rows:
        return []
    categories = {
        row.id: row
        for row in db.scalars(
            select(ProjectBudgetCategory).where(
                ProjectBudgetCategory.id.in_({item.category_id for item in line_rows})
            )
        ).all()
    }
    buckets: dict[UUID, CostByCategoryRow] = {}
    for item in line_rows:
        category = categories.get(item.category_id)
        if category is None:
            continue
        bucket = buckets.get(category.id)
        if bucket is None:
            bucket = CostByCategoryRow(
                category_id=category.id,
                category_code=category.code,
                category_name=category.name,
                current_budget=ZERO,
                committed_cost=ZERO,
                actual_cost=ZERO,
                paid_cost=ZERO,
                retained_cost=ZERO,
                remaining_budget=ZERO,
                available_to_commit=ZERO,
            )
            buckets[category.id] = bucket
        bucket.current_budget += item.current_budget
        bucket.committed_cost += item.committed_cost
        bucket.actual_cost += item.actual_cost
        bucket.paid_cost += item.paid_cost
        bucket.retained_cost += item.retained_cost
        bucket.remaining_budget += item.remaining_budget
        bucket.available_to_commit += item.available_to_commit
    return sorted(buckets.values(), key=lambda row: row.category_code)


def cost_by_vendor(db: Session, user: User, project_id: UUID) -> list[CostByVendorRow]:
    require_view(user)
    _load_project(db, project_id)
    commitments = db.execute(
        select(
            ProjectCommitment.vendor_id,
            Vendor.name,
            func.coalesce(func.sum(ProjectCommitment.current_committed_amount), 0),
            func.coalesce(func.sum(ProjectCommitment.retained_amount), 0),
        )
        .join(Vendor, Vendor.id == ProjectCommitment.vendor_id)
        .where(
            ProjectCommitment.project_id == project_id,
            ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
        )
        .group_by(ProjectCommitment.vendor_id, Vendor.name)
    ).all()
    actual_rows = db.execute(
        select(
            ProjectVendorBill.vendor_id,
            func.coalesce(
                func.sum(
                    ProjectVendorBillLine.net_amount
                    + func.coalesce(ProjectVendorBillLine.tax_amount, 0)
                ),
                0,
            ),
        )
        .join(ProjectVendorBillLine, ProjectVendorBillLine.vendor_bill_id == ProjectVendorBill.id)
        .where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(POSTED_BILL_STATUSES)),
        )
        .group_by(ProjectVendorBill.vendor_id)
    ).all()
    paid_rows = db.execute(
        select(
            ProjectPayment.vendor_id,
            func.coalesce(func.sum(ProjectPaymentAllocation.allocated_amount), 0),
        )
        .join(ProjectPaymentAllocation, ProjectPaymentAllocation.payment_id == ProjectPayment.id)
        .where(
            ProjectPayment.project_id == project_id,
            ProjectPayment.status == ProjectPaymentStatus.POSTED,
        )
        .group_by(ProjectPayment.vendor_id)
    ).all()
    balance_rows = db.execute(
        select(
            ProjectVendorBill.vendor_id,
            func.coalesce(func.sum(ProjectVendorBill.balance_due), 0),
        ).where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(
                [
                    VendorBillStatus.POSTED,
                    VendorBillStatus.PARTIALLY_PAID,
                    VendorBillStatus.APPROVED,
                ]
            ),
        )
        .group_by(ProjectVendorBill.vendor_id)
    ).all()
    actual_map = {row[0]: _money(row[1]) for row in actual_rows}
    paid_map = {row[0]: _money(row[1]) for row in paid_rows}
    balance_map = {row[0]: _money(row[1]) for row in balance_rows}
    return [
        CostByVendorRow(
            vendor_id=row[0],
            vendor_name=row[1],
            committed_cost=_money(row[2]),
            actual_cost=actual_map.get(row[0], ZERO),
            paid_cost=paid_map.get(row[0], ZERO),
            retained_cost=_money(row[3]),
            open_bills_balance=balance_map.get(row[0], ZERO),
        )
        for row in commitments
    ]


def get_cost_summary(db: Session, user: User, project_id: UUID) -> CostSummaryResponse:
    require_view(user)
    project = _load_project(db, project_id)
    permissions = cost_permissions(user)
    warnings: list[str] = []
    completeness: dict[str, str] = {}
    version = db.scalars(
        select(ProjectBudgetVersion).where(
            ProjectBudgetVersion.project_id == project_id,
            ProjectBudgetVersion.is_current.is_(True),
            ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
        )
    ).first()
    current_budget = ZERO
    if version is not None:
        current_budget = _money(
            db.scalar(
                select(func.coalesce(func.sum(ProjectBudgetLine.current_budget), 0)).where(
                    ProjectBudgetLine.budget_version_id == version.id,
                    ProjectBudgetLine.is_active.is_(True),
                    ProjectBudgetLine.is_summary.is_(False),
                )
            )
        )
        completeness["budget"] = "approved"
    else:
        completeness["budget"] = "missing"
        warnings.append("No approved current budget version")

    has_normalized = project_has_normalized_cost_data(db, project_id)
    totals_raw = project_cost_totals(db, project_id)
    committed = totals_raw["committed_cost"]
    pending = totals_raw["pending_commitments"]
    actual = totals_raw["actual_cost"]
    paid = totals_raw["paid_cost"]
    retained = totals_raw["retained_cost"]
    remaining_budget = current_budget - actual
    available_to_commit = current_budget - committed
    commitment_remaining = max(committed - actual, ZERO)
    basic_forecast = actual + commitment_remaining
    projected_variance = current_budget - basic_forecast

    source = "NORMALIZED" if has_normalized or version is not None else "UNAVAILABLE"
    completeness["committed_cost"] = "normalized" if has_normalized else "zero"
    completeness["actual_cost"] = "normalized" if has_normalized else "zero"
    completeness["forecast"] = "basic_commitment_based"

    overdue_count = 0
    bills = db.scalars(
        select(ProjectVendorBill).where(ProjectVendorBill.project_id == project_id)
    ).all()
    for bill in bills:
        if _bill_is_overdue(bill):
            overdue_count += 1

    return CostSummaryResponse(
        source=source,
        totals={
            "current_budget": metric(current_budget) if version else unavailable("No approved budget"),
            "committed_cost": metric(committed),
            "pending_commitments": metric(pending),
            "actual_cost": metric(actual),
            "paid_cost": metric(paid),
            "retained_cost": metric(retained),
            "remaining_budget": (
                metric(remaining_budget) if version else unavailable("No approved budget")
            ),
            "available_to_commit": (
                metric(available_to_commit) if version else unavailable("No approved budget")
            ),
            "basic_forecast_at_completion": metric(basic_forecast),
            "projected_variance": (
                metric(projected_variance) if version else unavailable("No approved budget")
            ),
            "overdue_bills_count": metric(overdue_count),
        },
        permissions=permissions,
        warnings=warnings
        + [
            "basic_forecast_at_completion is a commitment-based estimate, not a full forecasting engine",
            f"currency={project.currency}",
        ],
        data_completeness=completeness,
    )


def get_cost_activity(db: Session, user: User, project_id: UUID) -> list[dict]:
    require_view(user)
    _load_project(db, project_id)
    items: list[dict] = []
    for commitment in db.scalars(
        select(ProjectCommitment)
        .where(ProjectCommitment.project_id == project_id)
        .order_by(ProjectCommitment.updated_at.desc())
        .limit(25)
    ).all():
        items.append(
            {
                "entity_type": "commitment",
                "entity_id": str(commitment.id),
                "number": commitment.commitment_number,
                "status": commitment.status.value,
                "amount": str(commitment.current_committed_amount),
                "updated_at": commitment.updated_at.isoformat() if commitment.updated_at else None,
            }
        )
    for bill in db.scalars(
        select(ProjectVendorBill)
        .where(ProjectVendorBill.project_id == project_id)
        .order_by(ProjectVendorBill.updated_at.desc())
        .limit(25)
    ).all():
        items.append(
            {
                "entity_type": "vendor_bill",
                "entity_id": str(bill.id),
                "number": bill.bill_number,
                "status": bill.status.value,
                "amount": str(bill.total_amount),
                "updated_at": bill.updated_at.isoformat() if bill.updated_at else None,
            }
        )
    items.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return items[:50]


def export_commitments_csv(db: Session, user: User, project_id: UUID) -> str:
    require_view(user)
    if not cost_permissions(user).can_export:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Export access required")
    rows = list_commitments(db, user, project_id, page=1, page_size=5000).items
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "commitment_number",
            "type",
            "vendor_id",
            "title",
            "status",
            "original_amount",
            "approved_change_orders",
            "current_committed_amount",
            "invoiced_amount",
            "paid_amount",
            "retained_amount",
            "remaining_commitment",
            "currency",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.commitment_number,
                row.commitment_type.value,
                str(row.vendor_id),
                row.title,
                row.status.value,
                str(row.original_amount),
                str(row.approved_change_orders),
                str(row.current_committed_amount),
                str(row.invoiced_amount),
                str(row.paid_amount),
                str(row.retained_amount),
                str(row.remaining_commitment),
                row.currency,
            ]
        )
    return buffer.getvalue()


def export_bills_csv(db: Session, user: User, project_id: UUID) -> str:
    require_view(user)
    if not cost_permissions(user).can_export:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Export access required")
    rows = list_vendor_bills(db, user, project_id, page=1, page_size=5000).items
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "bill_number",
            "vendor_invoice_number",
            "vendor_id",
            "status",
            "invoice_date",
            "due_date",
            "subtotal",
            "tax_amount",
            "retainage_amount",
            "total_amount",
            "paid_amount",
            "balance_due",
            "is_overdue",
            "currency",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.bill_number,
                row.vendor_invoice_number,
                str(row.vendor_id),
                row.status.value,
                row.invoice_date.isoformat(),
                row.due_date.isoformat() if row.due_date else "",
                str(row.subtotal),
                str(row.tax_amount),
                str(row.retainage_amount),
                str(row.total_amount),
                str(row.paid_amount),
                str(row.balance_due),
                str(row.is_overdue),
                row.currency,
            ]
        )
    return buffer.getvalue()
