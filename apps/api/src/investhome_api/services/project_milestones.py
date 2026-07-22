"""Derive upcoming project milestones from schedule fields (no persisted table)."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from investhome_api.models.project import Project
from investhome_api.schemas.project_dashboard import MilestoneType, ProjectMilestoneItem


def _item(
    *,
    project: Project,
    milestone_type: MilestoneType,
    title: str,
    milestone_date: date,
    today: date,
    description: str | None = None,
) -> ProjectMilestoneItem:
    days = (milestone_date - today).days
    return ProjectMilestoneItem(
        id=f"{project.id}:{milestone_type.value}:{milestone_date.isoformat()}",
        project_id=project.id,
        project_name=project.project_name,
        title=title,
        type=milestone_type,
        description=description,
        date=milestone_date,
        status="overdue" if days < 0 else "upcoming",
        priority=project.priority.value if project.priority else "medium",
        days_remaining=days,
        is_overdue=days < 0,
        owner=project.assigned_project_manager,
        source="derived_schedule",
        action_url=f"/dashboard/projects?id={project.id}",
    )


def derive_milestones_for_project(
    project: Project,
    *,
    today: date,
    window_days: int,
) -> list[ProjectMilestoneItem]:
    if project.archived_at is not None:
        return []

    horizon = today + timedelta(days=window_days)
    # Include recently overdue milestones (up to 30 days past)
    floor = today - timedelta(days=30)
    candidates: list[tuple[MilestoneType, str, date | None, str | None]] = [
        (
            MilestoneType.ACQUISITION,
            "Acquisition date",
            project.acquisition_date,
            "Scheduled acquisition",
        ),
        (
            MilestoneType.START,
            "Estimated start",
            project.start_date,
            "Estimated project start",
        ),
        (
            MilestoneType.COMPLETION,
            "Estimated completion",
            project.target_completion_date,
            "Target completion date",
        ),
        (
            MilestoneType.CLOSING,
            "Estimated closing",
            project.estimated_closing_date,
            "Estimated closing date",
        ),
        (
            MilestoneType.DELIVERY,
            "Actual completion",
            project.actual_completion_date,
            "Recorded actual completion",
        ),
    ]

    items: list[ProjectMilestoneItem] = []
    for milestone_type, title, milestone_date, description in candidates:
        if milestone_date is None:
            continue
        if milestone_date < floor or milestone_date > horizon:
            continue
        items.append(
            _item(
                project=project,
                milestone_type=milestone_type,
                title=title,
                milestone_date=milestone_date,
                today=today,
                description=description,
            )
        )
    return items


def derive_upcoming_milestones(
    projects: list[Project],
    *,
    today: date | None = None,
    days: int = 30,
    project_id: UUID | None = None,
    limit: int = 50,
) -> list[ProjectMilestoneItem]:
    today = today or date.today()
    items: list[ProjectMilestoneItem] = []
    for project in projects:
        if project_id is not None and project.id != project_id:
            continue
        items.extend(derive_milestones_for_project(project, today=today, window_days=days))
    items.sort(key=lambda item: (item.days_remaining, item.project_name))
    return items[:limit]
