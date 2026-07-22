"""Company workspace unified search provider."""

from __future__ import annotations

from sqlalchemy.orm import Session

from investhome_api.config.search_config import DEFAULT_PER_ENTITY_LIMIT, DEFAULT_TOTAL_LIMIT
from investhome_api.models.user_auth import User
from investhome_api.schemas.search import SearchResponse
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.search_service import SearchFilters, global_search

COMPANY_SEARCH_ENTITY_TYPES = frozenset(
    {
        "managed_company",
        "company",
        "branch",
        "company_department",
        "department",
        "team",
        "user",
        "document",
        "project",
        "office",
    }
)


def _allowed_entity_types(user: User) -> set[str]:
    allowed: set[str] = set()
    if user_has_permission(user, "company", "read") or user_has_permission(user, "company", "view"):
        allowed.update({"managed_company", "company"})
    if user_has_permission(user, "branch", "read"):
        allowed.add("branch")
    if user_has_permission(user, "department", "read"):
        allowed.add("company_department")
    if user_has_permission(user, "organization", "view"):
        allowed.update({"department", "team"})
    if user_has_permission(user, "offices", "view"):
        allowed.add("office")
    if user_has_permission(user, "users", "view"):
        allowed.add("user")
    if user_has_permission(user, "documents", "view"):
        allowed.add("document")
    if user_has_permission(user, "projects", "view"):
        allowed.add("project")
    return allowed


def company_workspace_search(
    db: Session,
    user: User,
    query: str,
    *,
    entity_types: set[str] | None = None,
    limit: int = DEFAULT_TOTAL_LIMIT,
    per_entity_limit: int = DEFAULT_PER_ENTITY_LIMIT,
) -> SearchResponse:
    allowed = _allowed_entity_types(user)
    if not allowed:
        return SearchResponse(groups=[], total=0, query=query.strip())

    requested = entity_types or COMPANY_SEARCH_ENTITY_TYPES
    filtered = {value for value in requested if value in allowed and value in COMPANY_SEARCH_ENTITY_TYPES}
    if not filtered:
        return SearchResponse(groups=[], total=0, query=query.strip())

    return global_search(
        db,
        user,
        query.strip(),
        filters=SearchFilters(entity_types=filtered),
        per_entity_limit=per_entity_limit,
        total_limit=limit,
    )
