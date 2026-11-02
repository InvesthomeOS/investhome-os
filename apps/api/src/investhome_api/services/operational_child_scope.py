"""Visibility of demo child rows under a project.

Demo children stay available for a demo parent project.
A real parent (`projects.is_demo = false`) excludes `child.is_demo = true`.
This rule does not delete or archive rows.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.sql.elements import ColumnElement

from investhome_api.models.project import Project


def operational_child_clause(
    child_is_demo: ColumnElement[bool],
    child_project_id: ColumnElement,
) -> ColumnElement[bool]:
    """Include every non-demo child, and demo children only when the parent is demo."""
    parent_is_demo = (
        select(Project.is_demo).where(Project.id == child_project_id).scalar_subquery()
    )
    return or_(child_is_demo.is_(False), parent_is_demo.is_(True))
