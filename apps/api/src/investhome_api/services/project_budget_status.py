"""Centralized budget version and revision status transitions."""

from __future__ import annotations

from fastapi import HTTPException, status

from investhome_api.models.project_budget import BudgetRevisionStatus, BudgetVersionStatus

VERSION_TRANSITIONS: dict[BudgetVersionStatus, frozenset[BudgetVersionStatus]] = {
    BudgetVersionStatus.DRAFT: frozenset(
        {BudgetVersionStatus.IN_REVIEW, BudgetVersionStatus.ARCHIVED}
    ),
    BudgetVersionStatus.IN_REVIEW: frozenset(
        {BudgetVersionStatus.APPROVED, BudgetVersionStatus.REJECTED}
    ),
    BudgetVersionStatus.REJECTED: frozenset(
        {BudgetVersionStatus.DRAFT, BudgetVersionStatus.ARCHIVED}
    ),
    BudgetVersionStatus.APPROVED: frozenset({BudgetVersionStatus.SUPERSEDED}),
    BudgetVersionStatus.SUPERSEDED: frozenset(),
    BudgetVersionStatus.ARCHIVED: frozenset(),
}

REVISION_TRANSITIONS: dict[BudgetRevisionStatus, frozenset[BudgetRevisionStatus]] = {
    BudgetRevisionStatus.DRAFT: frozenset(
        {BudgetRevisionStatus.IN_REVIEW, BudgetRevisionStatus.CANCELLED}
    ),
    BudgetRevisionStatus.IN_REVIEW: frozenset(
        {
            BudgetRevisionStatus.APPROVED,
            BudgetRevisionStatus.REJECTED,
            BudgetRevisionStatus.CANCELLED,
        }
    ),
    BudgetRevisionStatus.REJECTED: frozenset({BudgetRevisionStatus.DRAFT}),
    BudgetRevisionStatus.APPROVED: frozenset(),
    BudgetRevisionStatus.CANCELLED: frozenset(),
}

EDITABLE_VERSION_STATUSES = frozenset({BudgetVersionStatus.DRAFT, BudgetVersionStatus.REJECTED})
LOCKED_VERSION_STATUSES = frozenset(
    {
        BudgetVersionStatus.APPROVED,
        BudgetVersionStatus.SUPERSEDED,
        BudgetVersionStatus.ARCHIVED,
        BudgetVersionStatus.IN_REVIEW,
    }
)


def validate_version_transition(
    current: BudgetVersionStatus, target: BudgetVersionStatus
) -> None:
    allowed = VERSION_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid budget status transition: {current.value} -> {target.value}",
        )


def validate_revision_transition(
    current: BudgetRevisionStatus, target: BudgetRevisionStatus
) -> None:
    allowed = REVISION_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid revision status transition: {current.value} -> {target.value}",
        )


def assert_version_editable(status_value: BudgetVersionStatus) -> None:
    if status_value not in EDITABLE_VERSION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget is locked and cannot be edited",
        )
