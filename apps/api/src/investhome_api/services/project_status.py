"""Centralized project status transition rules (existing ProjectStatus values only)."""

from __future__ import annotations

from fastapi import HTTPException, status

from investhome_api.models.project import ProjectStatus

VALID_STATUS_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.PIPELINE: {
        ProjectStatus.DUE_DILIGENCE,
        ProjectStatus.ACQUISITION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.DUE_DILIGENCE: {
        ProjectStatus.ACQUISITION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.ACQUISITION: {
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.PRE_DEVELOPMENT: {
        ProjectStatus.PERMITTING,
        ProjectStatus.CONSTRUCTION,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.PERMITTING: {
        ProjectStatus.CONSTRUCTION,
        ProjectStatus.ON_HOLD,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.CONSTRUCTION: {
        ProjectStatus.LEASING,
        ProjectStatus.SALES,
        ProjectStatus.STABILIZATION,
        ProjectStatus.ON_HOLD,
        ProjectStatus.COMPLETED,
    },
    ProjectStatus.SALES: {
        ProjectStatus.LEASING,
        ProjectStatus.STABILIZATION,
        ProjectStatus.COMPLETED,
    },
    ProjectStatus.LEASING: {
        ProjectStatus.STABILIZATION,
        ProjectStatus.COMPLETED,
    },
    ProjectStatus.STABILIZATION: {
        ProjectStatus.COMPLETED,
        ProjectStatus.ON_HOLD,
    },
    ProjectStatus.COMPLETED: set(),
    ProjectStatus.ON_HOLD: {
        ProjectStatus.PIPELINE,
        ProjectStatus.DUE_DILIGENCE,
        ProjectStatus.ACQUISITION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.PERMITTING,
        ProjectStatus.CONSTRUCTION,
        ProjectStatus.LEASING,
        ProjectStatus.SALES,
        ProjectStatus.STABILIZATION,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.CANCELLED: set(),
}


def get_allowed_transitions(current: ProjectStatus) -> list[ProjectStatus]:
    return sorted(VALID_STATUS_TRANSITIONS.get(current, set()), key=lambda item: item.value)


def validate_status_transition(current: ProjectStatus, target: ProjectStatus) -> None:
    if current == target:
        return
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        allowed_labels = ", ".join(sorted(status.value for status in allowed)) or "none"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot transition project from '{current.value}' to '{target.value}'. "
                f"Allowed: {allowed_labels}"
            ),
        )
