"""Universal global search API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.config.search_config import DEFAULT_PER_ENTITY_LIMIT, DEFAULT_TOTAL_LIMIT, SEARCH_ENTITY_TYPES
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.search import SearchResponse
from investhome_api.services.search_service import SearchFilters, global_search

router = APIRouter(prefix="/search", tags=["search"])


def _parse_entity_types(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {part.strip() for part in raw.split(",") if part.strip()}
    filtered = {value for value in values if value in SEARCH_ENTITY_TYPES}
    return filtered or None


@router.get("", response_model=SearchResponse)
def search_records(
    q: str = Query(..., min_length=1, max_length=255),
    entity_types: str | None = Query(default=None, max_length=500),
    status_filter: str | None = Query(default=None, alias="status", max_length=100),
    assigned_to: str | None = Query(default=None, max_length=255),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=DEFAULT_TOTAL_LIMIT, ge=1, le=100),
    per_entity_limit: int = Query(default=DEFAULT_PER_ENTITY_LIMIT, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("search", "view")),
) -> SearchResponse:
    normalized = q.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query must not be empty")
    filters = SearchFilters(
        entity_types=_parse_entity_types(entity_types),
        status=status_filter,
        assigned_to=assigned_to,
        date_from=date_from,
        date_to=date_to,
    )
    return global_search(
        db,
        user,
        normalized,
        filters=filters,
        per_entity_limit=per_entity_limit,
        total_limit=limit,
    )
