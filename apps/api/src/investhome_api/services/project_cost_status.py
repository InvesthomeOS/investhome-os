"""Centralized project cost status transitions (Sprint 10A4B)."""

from __future__ import annotations

from fastapi import HTTPException, status

from investhome_api.models.project_cost import (
    ChangeOrderStatus,
    ProjectCommitmentStatus,
    ProjectPaymentStatus,
    RetainageReleaseStatus,
    VendorBillStatus,
)

COMMITMENT_TRANSITIONS: dict[ProjectCommitmentStatus, frozenset[ProjectCommitmentStatus]] = {
    ProjectCommitmentStatus.DRAFT: frozenset(
        {ProjectCommitmentStatus.IN_REVIEW, ProjectCommitmentStatus.CANCELLED}
    ),
    ProjectCommitmentStatus.IN_REVIEW: frozenset(
        {
            ProjectCommitmentStatus.APPROVED,
            ProjectCommitmentStatus.REJECTED,
            ProjectCommitmentStatus.CANCELLED,
        }
    ),
    ProjectCommitmentStatus.REJECTED: frozenset(
        {ProjectCommitmentStatus.DRAFT, ProjectCommitmentStatus.CANCELLED}
    ),
    ProjectCommitmentStatus.APPROVED: frozenset(
        {ProjectCommitmentStatus.EXECUTED, ProjectCommitmentStatus.CANCELLED}
    ),
    ProjectCommitmentStatus.EXECUTED: frozenset({ProjectCommitmentStatus.ACTIVE}),
    ProjectCommitmentStatus.ACTIVE: frozenset(
        {ProjectCommitmentStatus.COMPLETED, ProjectCommitmentStatus.CANCELLED}
    ),
    ProjectCommitmentStatus.COMPLETED: frozenset({ProjectCommitmentStatus.CLOSED}),
    ProjectCommitmentStatus.CLOSED: frozenset({ProjectCommitmentStatus.ARCHIVED}),
    ProjectCommitmentStatus.CANCELLED: frozenset({ProjectCommitmentStatus.ARCHIVED}),
    ProjectCommitmentStatus.ARCHIVED: frozenset(),
}

CHANGE_ORDER_TRANSITIONS: dict[ChangeOrderStatus, frozenset[ChangeOrderStatus]] = {
    ChangeOrderStatus.DRAFT: frozenset({ChangeOrderStatus.IN_REVIEW, ChangeOrderStatus.CANCELLED}),
    ChangeOrderStatus.IN_REVIEW: frozenset(
        {
            ChangeOrderStatus.APPROVED,
            ChangeOrderStatus.REJECTED,
            ChangeOrderStatus.CANCELLED,
        }
    ),
    ChangeOrderStatus.REJECTED: frozenset({ChangeOrderStatus.DRAFT}),
    ChangeOrderStatus.APPROVED: frozenset(),
    ChangeOrderStatus.CANCELLED: frozenset(),
}

BILL_TRANSITIONS: dict[VendorBillStatus, frozenset[VendorBillStatus]] = {
    VendorBillStatus.DRAFT: frozenset({VendorBillStatus.IN_REVIEW, VendorBillStatus.VOID}),
    VendorBillStatus.IN_REVIEW: frozenset(
        {VendorBillStatus.APPROVED, VendorBillStatus.REJECTED, VendorBillStatus.VOID}
    ),
    VendorBillStatus.REJECTED: frozenset({VendorBillStatus.DRAFT, VendorBillStatus.VOID}),
    VendorBillStatus.APPROVED: frozenset({VendorBillStatus.POSTED, VendorBillStatus.VOID}),
    VendorBillStatus.POSTED: frozenset(
        {VendorBillStatus.PARTIALLY_PAID, VendorBillStatus.PAID, VendorBillStatus.VOID}
    ),
    VendorBillStatus.PARTIALLY_PAID: frozenset(
        {VendorBillStatus.PAID, VendorBillStatus.POSTED, VendorBillStatus.VOID}
    ),
    VendorBillStatus.PAID: frozenset({VendorBillStatus.PARTIALLY_PAID, VendorBillStatus.VOID}),
    VendorBillStatus.VOID: frozenset(),
    VendorBillStatus.ARCHIVED: frozenset(),
}

PAYMENT_TRANSITIONS: dict[ProjectPaymentStatus, frozenset[ProjectPaymentStatus]] = {
    ProjectPaymentStatus.DRAFT: frozenset({ProjectPaymentStatus.POSTED, ProjectPaymentStatus.VOID}),
    ProjectPaymentStatus.POSTED: frozenset({ProjectPaymentStatus.VOID}),
    ProjectPaymentStatus.VOID: frozenset(),
}

RETAINAGE_TRANSITIONS: dict[RetainageReleaseStatus, frozenset[RetainageReleaseStatus]] = {
    RetainageReleaseStatus.DRAFT: frozenset(
        {RetainageReleaseStatus.IN_REVIEW, RetainageReleaseStatus.VOID}
    ),
    RetainageReleaseStatus.IN_REVIEW: frozenset(
        {
            RetainageReleaseStatus.APPROVED,
            RetainageReleaseStatus.REJECTED,
            RetainageReleaseStatus.VOID,
        }
    ),
    RetainageReleaseStatus.REJECTED: frozenset({RetainageReleaseStatus.DRAFT}),
    RetainageReleaseStatus.APPROVED: frozenset(
        {RetainageReleaseStatus.POSTED, RetainageReleaseStatus.VOID}
    ),
    RetainageReleaseStatus.POSTED: frozenset({RetainageReleaseStatus.VOID}),
    RetainageReleaseStatus.VOID: frozenset(),
}

EDITABLE_COMMITMENT_STATUSES = frozenset(
    {ProjectCommitmentStatus.DRAFT, ProjectCommitmentStatus.REJECTED}
)
LOCKED_COMMITMENT_STATUSES = frozenset(
    {
        ProjectCommitmentStatus.IN_REVIEW,
        ProjectCommitmentStatus.APPROVED,
        ProjectCommitmentStatus.EXECUTED,
        ProjectCommitmentStatus.ACTIVE,
        ProjectCommitmentStatus.COMPLETED,
        ProjectCommitmentStatus.CLOSED,
        ProjectCommitmentStatus.CANCELLED,
        ProjectCommitmentStatus.ARCHIVED,
    }
)
EDITABLE_BILL_STATUSES = frozenset({VendorBillStatus.DRAFT, VendorBillStatus.REJECTED})
EDITABLE_PAYMENT_STATUSES = frozenset({ProjectPaymentStatus.DRAFT})
EDITABLE_CHANGE_ORDER_STATUSES = frozenset({ChangeOrderStatus.DRAFT, ChangeOrderStatus.REJECTED})


def validate_commitment_transition(
    current: ProjectCommitmentStatus, target: ProjectCommitmentStatus
) -> None:
    allowed = COMMITMENT_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid commitment status transition: {current.value} -> {target.value}",
        )


def validate_change_order_transition(
    current: ChangeOrderStatus, target: ChangeOrderStatus
) -> None:
    allowed = CHANGE_ORDER_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid change order status transition: {current.value} -> {target.value}",
        )


def validate_bill_transition(current: VendorBillStatus, target: VendorBillStatus) -> None:
    allowed = BILL_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bill status transition: {current.value} -> {target.value}",
        )


def validate_payment_transition(
    current: ProjectPaymentStatus, target: ProjectPaymentStatus
) -> None:
    allowed = PAYMENT_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payment status transition: {current.value} -> {target.value}",
        )


def validate_retainage_transition(
    current: RetainageReleaseStatus, target: RetainageReleaseStatus
) -> None:
    allowed = RETAINAGE_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid retainage release status transition: {current.value} -> {target.value}",
        )


def assert_commitment_editable(status_value: ProjectCommitmentStatus) -> None:
    if status_value not in EDITABLE_COMMITMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Commitment is locked and cannot be edited",
        )


def assert_bill_editable(status_value: VendorBillStatus) -> None:
    if status_value not in EDITABLE_BILL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bill is locked and cannot be edited",
        )


def assert_payment_editable(status_value: ProjectPaymentStatus) -> None:
    if status_value not in EDITABLE_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment is locked and cannot be edited",
        )


def assert_change_order_editable(status_value: ChangeOrderStatus) -> None:
    if status_value not in EDITABLE_CHANGE_ORDER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Change order is locked and cannot be edited",
        )
