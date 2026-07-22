"""CRM global search API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_search import (
    CrmDuplicateDiscoveryRequest,
    CrmDuplicateDiscoveryResponse,
    CrmEntityPickerRequest,
    CrmEntityPickerResponse,
    CrmNaturalLanguageRequest,
    CrmNaturalLanguageResponse,
    CrmParseQueryRequest,
    CrmParseQueryResponse,
    CrmRecentSearchCreate,
    CrmRecentSearchResponse,
    CrmSavedSearchCreate,
    CrmSavedSearchResponse,
    CrmSavedSearchUpdate,
    CrmSearchAnalyticsSummary,
    CrmSearchExportRequest,
    CrmSearchExportResponse,
    CrmSearchQueryRequest,
    CrmSearchResponse,
    CrmSearchSuggestionsResponse,
)
from investhome_api.services.crm.search_permissions import (
    can_manage_saved_searches,
    can_use_advanced_search,
    can_use_global_search,
    can_view_search_analytics,
    can_view_suggestions,
)
from investhome_api.services.crm.search_service import (
    clear_recent_searches,
    create_saved_search,
    crm_global_search,
    crm_quick_search,
    crm_search_suggestions,
    delete_saved_search,
    discover_duplicates,
    entity_picker_results,
    execute_saved_search,
    export_search_results,
    interpret_natural_language,
    list_recent_searches,
    list_saved_searches,
    parse_query,
    record_recent_search,
    remove_recent_search,
    search_analytics,
    search_related_entities,
    search_warm_introduction_candidates,
    update_saved_search,
)

router = APIRouter(prefix="/crm/search", tags=["crm-search"])


def _require_crm_search():
    return require_permission("crm", "use_global_search")


@router.post("/global", response_model=CrmSearchResponse)
def global_search_endpoint(
    payload: CrmSearchQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmSearchResponse:
    if not can_use_global_search(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return crm_global_search(db, user, payload)


@router.get("/quick", response_model=CrmSearchResponse)
def quick_search_endpoint(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(default=25, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmSearchResponse:
    return crm_quick_search(db, user, q.strip(), limit=limit)


@router.post("/advanced", response_model=CrmSearchResponse)
def advanced_search_endpoint(
    payload: CrmSearchQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "advanced_search")),
) -> CrmSearchResponse:
    if not can_use_advanced_search(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return crm_global_search(db, user, payload)


@router.get("/suggestions", response_model=CrmSearchSuggestionsResponse)
def suggestions_endpoint(
    q: str = Query(..., min_length=1, max_length=255),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "view_suggestions")),
) -> CrmSearchSuggestionsResponse:
    if not can_view_suggestions(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return crm_search_suggestions(db, user, q.strip())


@router.post("/parse", response_model=CrmParseQueryResponse)
def parse_query_endpoint(
    payload: CrmParseQueryRequest,
    user: User = Depends(_require_crm_search()),
) -> CrmParseQueryResponse:
    return parse_query(payload.query)


@router.post("/natural-language", response_model=CrmNaturalLanguageResponse)
def natural_language_endpoint(
    payload: CrmNaturalLanguageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "natural_language_search")),
) -> CrmNaturalLanguageResponse:
    return interpret_natural_language(db, user, payload.query)


@router.get("/recent", response_model=list[CrmRecentSearchResponse])
def list_recent_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> list[CrmRecentSearchResponse]:
    return list_recent_searches(db, user)


@router.post("/recent", response_model=CrmRecentSearchResponse, status_code=status.HTTP_201_CREATED)
def record_recent_endpoint(
    payload: CrmRecentSearchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmRecentSearchResponse:
    result = record_recent_search(db, user, payload)
    db.commit()
    return result


@router.delete("/recent", status_code=status.HTTP_204_NO_CONTENT)
def clear_recent_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> None:
    clear_recent_searches(db, user)
    db.commit()


@router.delete("/recent/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recent_endpoint(
    search_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> None:
    if not remove_recent_search(db, user, search_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


@router.get("/saved", response_model=list[CrmSavedSearchResponse])
def list_saved_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_saved_searches")),
) -> list[CrmSavedSearchResponse]:
    if not can_manage_saved_searches(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    result = list_saved_searches(db, user)
    db.commit()
    return result


@router.post("/saved", response_model=CrmSavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_endpoint(
    payload: CrmSavedSearchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_saved_searches")),
) -> CrmSavedSearchResponse:
    result = create_saved_search(db, user, payload)
    db.commit()
    return result


@router.put("/saved/{search_id}", response_model=CrmSavedSearchResponse)
def update_saved_endpoint(
    search_id: UUID,
    payload: CrmSavedSearchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_saved_searches")),
) -> CrmSavedSearchResponse:
    result = update_saved_search(db, user, search_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return result


@router.delete("/saved/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_endpoint(
    search_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_saved_searches")),
) -> None:
    if not delete_saved_search(db, user, search_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


@router.post("/saved/{search_id}/execute", response_model=CrmSearchResponse)
def execute_saved_endpoint(
    search_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmSearchResponse:
    return execute_saved_search(db, user, search_id)


@router.post("/entity-picker", response_model=CrmEntityPickerResponse)
def entity_picker_endpoint(
    payload: CrmEntityPickerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmEntityPickerResponse:
    return entity_picker_results(
        db,
        user,
        payload.query,
        entity_types=payload.entity_types,
        page=payload.page,
        page_size=payload.page_size,
        exclude_ids=payload.exclude_ids,
    )


@router.post("/duplicates", response_model=CrmDuplicateDiscoveryResponse)
def duplicates_endpoint(
    payload: CrmDuplicateDiscoveryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmDuplicateDiscoveryResponse:
    return discover_duplicates(
        db,
        user,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
    )


@router.get("/related/{entity_type}/{entity_id}", response_model=CrmSearchResponse)
def related_entities_endpoint(
    entity_type: str,
    entity_id: UUID,
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmSearchResponse:
    return search_related_entities(db, user, entity_type, entity_id, q)


@router.get("/warm-intro/{target_type}/{target_id}", response_model=CrmSearchResponse)
def warm_intro_endpoint(
    target_type: str,
    target_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_search()),
) -> CrmSearchResponse:
    return search_warm_introduction_candidates(db, user, target_type, target_id)


@router.post("/export", response_model=CrmSearchExportResponse)
def export_endpoint(
    payload: CrmSearchExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "export_search_results")),
) -> CrmSearchExportResponse:
    search_response = crm_global_search(
        db,
        user,
        CrmSearchQueryRequest(query=payload.query or "", filters=None),
    )
    items = search_response.items
    if payload.result_ids:
        allowed = set(payload.result_ids)
        items = [i for i in items if i.id in allowed]
    return export_search_results(db, user, format=payload.format, items=items, visible_fields=payload.visible_fields)


@router.get("/analytics", response_model=CrmSearchAnalyticsSummary)
def analytics_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "view_search_analytics")),
) -> CrmSearchAnalyticsSummary:
    if not can_view_search_analytics(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return search_analytics(db, user)
