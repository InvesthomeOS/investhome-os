"""Project cost tracking routes (Sprint 10A4B). Thin handlers only."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_cost import (
    ChangeOrderCreate,
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
from investhome_api.services import project_cost_service as svc

router = APIRouter(tags=["project-costs"])


# ---------------------------------------------------------------------------
# Vendors (company-scoped master)
# ---------------------------------------------------------------------------


@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(
    search: str | None = Query(default=None, max_length=255),
    company_id: UUID | None = None,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[VendorResponse]:
    return svc.list_vendors(
        db, user=user, company_id=company_id, search=search, active_only=active_only
    )


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorResponse:
    return svc.create_vendor(db, payload, actor=actor)


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: UUID,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorResponse:
    return svc.update_vendor(db, vendor_id, payload, actor=actor)


# ---------------------------------------------------------------------------
# Project vendors
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/vendors", response_model=list[ProjectVendorResponse])
def list_project_vendors(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[ProjectVendorResponse]:
    return svc.list_project_vendors(db, user, project_id)


@router.post(
    "/projects/{project_id}/vendors",
    response_model=ProjectVendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_vendor(
    project_id: UUID,
    payload: ProjectVendorCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ProjectVendorResponse:
    return svc.add_project_vendor(db, project_id, payload, actor=actor)


@router.patch(
    "/projects/{project_id}/vendors/{project_vendor_id}",
    response_model=ProjectVendorResponse,
)
def update_project_vendor(
    project_id: UUID,
    project_vendor_id: UUID,
    payload: ProjectVendorUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ProjectVendorResponse:
    return svc.update_project_vendor(db, project_id, project_vendor_id, payload, actor=actor)


@router.delete(
    "/projects/{project_id}/vendors/{project_vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project_vendor(
    project_id: UUID,
    project_vendor_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.remove_project_vendor(db, project_id, project_vendor_id, actor=actor)


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/commitments", response_model=CommitmentListResponse)
def list_commitments(
    project_id: UUID,
    status: str | None = Query(default=None, alias="status"),
    type: str | None = Query(default=None, alias="type"),
    vendor_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> CommitmentListResponse:
    return svc.list_commitments(
        db,
        user,
        project_id,
        status_filter=status,
        commitment_type=type,
        vendor_id=vendor_id,
        search=search,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/commitments",
    response_model=CommitmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commitment(
    project_id: UUID,
    payload: CommitmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.create_commitment(db, project_id, payload, actor=actor)


@router.get(
    "/projects/{project_id}/commitments/{commitment_id}",
    response_model=CommitmentResponse,
)
def get_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.get_commitment(db, user, project_id, commitment_id)


@router.patch(
    "/projects/{project_id}/commitments/{commitment_id}",
    response_model=CommitmentResponse,
)
def update_commitment(
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.update_commitment(db, project_id, commitment_id, payload, actor=actor)


@router.delete(
    "/projects/{project_id}/commitments/{commitment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/submit",
    response_model=CommitmentResponse,
)
def submit_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.submit_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/approve",
    response_model=CommitmentResponse,
)
def approve_commitment(
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentApproveRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.approve_commitment(
        db, project_id, commitment_id, actor=actor, payload=payload or CommitmentApproveRequest()
    )


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/reject",
    response_model=CommitmentResponse,
)
def reject_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.reject_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/execute",
    response_model=CommitmentResponse,
)
def execute_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.execute_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/activate",
    response_model=CommitmentResponse,
)
def activate_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.activate_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/complete",
    response_model=CommitmentResponse,
)
def complete_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.complete_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/close",
    response_model=CommitmentResponse,
)
def close_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.close_commitment(db, project_id, commitment_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/cancel",
    response_model=CommitmentResponse,
)
def cancel_commitment(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentResponse:
    return svc.cancel_commitment(db, project_id, commitment_id, actor=actor)


# ---------------------------------------------------------------------------
# Commitment lines
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/commitments/{commitment_id}/lines",
    response_model=list[CommitmentLineResponse],
)
def list_commitment_lines(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[CommitmentLineResponse]:
    return svc.list_commitment_lines(db, user, project_id, commitment_id)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/lines",
    response_model=CommitmentLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_commitment_line(
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentLineCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentLineResponse:
    return svc.add_commitment_line(db, project_id, commitment_id, payload, actor=actor)


@router.patch(
    "/projects/{project_id}/commitments/{commitment_id}/lines/{line_id}",
    response_model=CommitmentLineResponse,
)
def update_commitment_line(
    project_id: UUID,
    commitment_id: UUID,
    line_id: UUID,
    payload: CommitmentLineUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CommitmentLineResponse:
    return svc.update_commitment_line(
        db, project_id, commitment_id, line_id, payload, actor=actor
    )


@router.delete(
    "/projects/{project_id}/commitments/{commitment_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_commitment_line(
    project_id: UUID,
    commitment_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_commitment_line(db, project_id, commitment_id, line_id, actor=actor)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/lines/bulk",
    response_model=list[CommitmentLineResponse],
    status_code=status.HTTP_201_CREATED,
)
def bulk_add_commitment_lines(
    project_id: UUID,
    commitment_id: UUID,
    payload: CommitmentLineBulkCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> list[CommitmentLineResponse]:
    return svc.bulk_add_commitment_lines(db, project_id, commitment_id, payload, actor=actor)


# ---------------------------------------------------------------------------
# Change orders
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders",
    response_model=list[ChangeOrderResponse],
)
def list_change_orders(
    project_id: UUID,
    commitment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[ChangeOrderResponse]:
    return svc.list_change_orders(db, user, project_id, commitment_id)


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders",
    response_model=ChangeOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_order(
    project_id: UUID,
    commitment_id: UUID,
    payload: ChangeOrderCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.create_change_order(db, project_id, commitment_id, payload, actor=actor)


@router.get(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}",
    response_model=ChangeOrderResponse,
)
def get_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.get_change_order(db, user, project_id, commitment_id, change_order_id)


@router.patch(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}",
    response_model=ChangeOrderResponse,
)
def update_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    payload: ChangeOrderUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.update_change_order(
        db, project_id, commitment_id, change_order_id, payload, actor=actor
    )


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}/submit",
    response_model=ChangeOrderResponse,
)
def submit_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.submit_change_order(
        db, project_id, commitment_id, change_order_id, actor=actor
    )


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}/approve",
    response_model=ChangeOrderResponse,
)
def approve_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.approve_change_order(
        db, project_id, commitment_id, change_order_id, actor=actor
    )


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}/reject",
    response_model=ChangeOrderResponse,
)
def reject_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.reject_change_order(
        db, project_id, commitment_id, change_order_id, actor=actor
    )


@router.post(
    "/projects/{project_id}/commitments/{commitment_id}/change-orders/{change_order_id}/cancel",
    response_model=ChangeOrderResponse,
)
def cancel_change_order(
    project_id: UUID,
    commitment_id: UUID,
    change_order_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> ChangeOrderResponse:
    return svc.cancel_change_order(
        db, project_id, commitment_id, change_order_id, actor=actor
    )


# ---------------------------------------------------------------------------
# Vendor bills
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/vendor-bills", response_model=VendorBillListResponse)
def list_vendor_bills(
    project_id: UUID,
    status: str | None = Query(default=None, alias="status"),
    vendor_id: UUID | None = None,
    commitment_id: UUID | None = None,
    overdue: bool | None = None,
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> VendorBillListResponse:
    return svc.list_vendor_bills(
        db,
        user,
        project_id,
        status_filter=status,
        vendor_id=vendor_id,
        commitment_id=commitment_id,
        overdue=overdue,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/vendor-bills",
    response_model=VendorBillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_bill(
    project_id: UUID,
    payload: VendorBillCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.create_vendor_bill(db, project_id, payload, actor=actor)


@router.get(
    "/projects/{project_id}/vendor-bills/{bill_id}",
    response_model=VendorBillResponse,
)
def get_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.get_vendor_bill(db, user, project_id, bill_id)


@router.patch(
    "/projects/{project_id}/vendor-bills/{bill_id}",
    response_model=VendorBillResponse,
)
def update_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.update_vendor_bill(db, project_id, bill_id, payload, actor=actor)


@router.delete(
    "/projects/{project_id}/vendor-bills/{bill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_vendor_bill(db, project_id, bill_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/submit",
    response_model=VendorBillResponse,
)
def submit_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.submit_vendor_bill(db, project_id, bill_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/approve",
    response_model=VendorBillResponse,
)
def approve_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.approve_vendor_bill(db, project_id, bill_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/reject",
    response_model=VendorBillResponse,
)
def reject_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.reject_vendor_bill(db, project_id, bill_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/post",
    response_model=VendorBillResponse,
)
def post_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.post_vendor_bill(db, project_id, bill_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/void",
    response_model=VendorBillResponse,
)
def void_vendor_bill(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillResponse:
    return svc.void_vendor_bill(db, project_id, bill_id, actor=actor)


@router.get(
    "/projects/{project_id}/vendor-bills/{bill_id}/lines",
    response_model=list[VendorBillLineResponse],
)
def list_bill_lines(
    project_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[VendorBillLineResponse]:
    return svc.list_bill_lines(db, user, project_id, bill_id)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/lines",
    response_model=VendorBillLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_bill_line(
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillLineCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillLineResponse:
    return svc.add_bill_line(db, project_id, bill_id, payload, actor=actor)


@router.patch(
    "/projects/{project_id}/vendor-bills/{bill_id}/lines/{line_id}",
    response_model=VendorBillLineResponse,
)
def update_bill_line(
    project_id: UUID,
    bill_id: UUID,
    line_id: UUID,
    payload: VendorBillLineUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> VendorBillLineResponse:
    return svc.update_bill_line(db, project_id, bill_id, line_id, payload, actor=actor)


@router.delete(
    "/projects/{project_id}/vendor-bills/{bill_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bill_line(
    project_id: UUID,
    bill_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_bill_line(db, project_id, bill_id, line_id, actor=actor)


@router.post(
    "/projects/{project_id}/vendor-bills/{bill_id}/lines/bulk",
    response_model=list[VendorBillLineResponse],
    status_code=status.HTTP_201_CREATED,
)
def bulk_add_bill_lines(
    project_id: UUID,
    bill_id: UUID,
    payload: VendorBillLineBulkCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> list[VendorBillLineResponse]:
    return svc.bulk_add_bill_lines(db, project_id, bill_id, payload, actor=actor)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/payments", response_model=PaymentListResponse)
def list_payments(
    project_id: UUID,
    status: str | None = Query(default=None, alias="status"),
    vendor_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> PaymentListResponse:
    return svc.list_payments(
        db,
        user,
        project_id,
        status_filter=status,
        vendor_id=vendor_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    project_id: UUID,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> PaymentResponse:
    return svc.create_payment(db, project_id, payload, actor=actor)


@router.get(
    "/projects/{project_id}/payments/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    project_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> PaymentResponse:
    return svc.get_payment(db, user, project_id, payment_id)


@router.patch(
    "/projects/{project_id}/payments/{payment_id}",
    response_model=PaymentResponse,
)
def update_payment(
    project_id: UUID,
    payment_id: UUID,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> PaymentResponse:
    return svc.update_payment(db, project_id, payment_id, payload, actor=actor)


@router.post(
    "/projects/{project_id}/payments/{payment_id}/post",
    response_model=PaymentResponse,
)
def post_payment(
    project_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> PaymentResponse:
    return svc.post_payment(db, project_id, payment_id, actor=actor)


@router.post(
    "/projects/{project_id}/payments/{payment_id}/void",
    response_model=PaymentResponse,
)
def void_payment(
    project_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> PaymentResponse:
    return svc.void_payment(db, project_id, payment_id, actor=actor)


@router.get(
    "/projects/{project_id}/payments/{payment_id}/allocations",
    response_model=list[PaymentAllocationResponse],
)
def list_allocations(
    project_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[PaymentAllocationResponse]:
    return svc.list_allocations(db, user, project_id, payment_id)


@router.post(
    "/projects/{project_id}/payments/{payment_id}/allocations",
    response_model=PaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_allocation(
    project_id: UUID,
    payment_id: UUID,
    payload: PaymentAllocationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> PaymentAllocationResponse:
    return svc.add_allocation(db, project_id, payment_id, payload, actor=actor)


@router.delete(
    "/projects/{project_id}/payments/{payment_id}/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_allocation(
    project_id: UUID,
    payment_id: UUID,
    allocation_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_allocation(db, project_id, payment_id, allocation_id, actor=actor)


# ---------------------------------------------------------------------------
# Retainage
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/retainage", response_model=RetainageSummaryResponse)
def get_retainage(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> RetainageSummaryResponse:
    return svc.get_retainage_summary(db, user, project_id)


@router.get(
    "/projects/{project_id}/retainage-releases",
    response_model=list[RetainageReleaseResponse],
)
def list_retainage_releases(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[RetainageReleaseResponse]:
    return svc.list_retainage_releases(db, user, project_id)


@router.post(
    "/projects/{project_id}/retainage-releases",
    response_model=RetainageReleaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_retainage_release(
    project_id: UUID,
    payload: RetainageReleaseCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.create_retainage_release(db, project_id, payload, actor=actor)


@router.post(
    "/projects/{project_id}/retainage-releases/{release_id}/submit",
    response_model=RetainageReleaseResponse,
)
def submit_retainage_release(
    project_id: UUID,
    release_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.submit_retainage_release(db, project_id, release_id, actor=actor)


@router.post(
    "/projects/{project_id}/retainage-releases/{release_id}/approve",
    response_model=RetainageReleaseResponse,
)
def approve_retainage_release(
    project_id: UUID,
    release_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.approve_retainage_release(db, project_id, release_id, actor=actor)


@router.post(
    "/projects/{project_id}/retainage-releases/{release_id}/reject",
    response_model=RetainageReleaseResponse,
)
def reject_retainage_release(
    project_id: UUID,
    release_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.reject_retainage_release(db, project_id, release_id, actor=actor)


@router.post(
    "/projects/{project_id}/retainage-releases/{release_id}/post",
    response_model=RetainageReleaseResponse,
)
def post_retainage_release(
    project_id: UUID,
    release_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.post_retainage_release(db, project_id, release_id, actor=actor)


@router.post(
    "/projects/{project_id}/retainage-releases/{release_id}/void",
    response_model=RetainageReleaseResponse,
)
def void_retainage_release(
    project_id: UUID,
    release_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> RetainageReleaseResponse:
    return svc.void_retainage_release(db, project_id, release_id, actor=actor)


# ---------------------------------------------------------------------------
# Cost summary / rollups / exports
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/cost-summary", response_model=CostSummaryResponse)
def get_cost_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> CostSummaryResponse:
    return svc.get_cost_summary(db, user, project_id)


@router.get(
    "/projects/{project_id}/cost-by-budget-line",
    response_model=list[CostByBudgetLineRow],
)
def get_cost_by_budget_line(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[CostByBudgetLineRow]:
    return svc.cost_by_budget_line(db, user, project_id)


@router.get(
    "/projects/{project_id}/cost-by-category",
    response_model=list[CostByCategoryRow],
)
def get_cost_by_category(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[CostByCategoryRow]:
    return svc.cost_by_category(db, user, project_id)


@router.get("/projects/{project_id}/cost-by-vendor", response_model=list[CostByVendorRow])
def get_cost_by_vendor(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[CostByVendorRow]:
    return svc.cost_by_vendor(db, user, project_id)


@router.get("/projects/{project_id}/cost-activity")
def get_cost_activity(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> list[dict]:
    return svc.get_cost_activity(db, user, project_id)


@router.get("/projects/{project_id}/exports/commitments")
def export_commitments(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> Response:
    content = svc.export_commitments_csv(db, user, project_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commitments.csv"},
    )


@router.get("/projects/{project_id}/exports/vendor-bills")
def export_bills(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> Response:
    content = svc.export_bills_csv(db, user, project_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vendor-bills.csv"},
    )
