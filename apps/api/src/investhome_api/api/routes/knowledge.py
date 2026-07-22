"""Knowledge Hub API — secure organize/search/review over canonical Documents."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.knowledge import (
    KnowledgeAiSearchRequest,
    KnowledgeAiSearchResponse,
    KnowledgeCategoryCreate,
    KnowledgeCategoryResponse,
    KnowledgeCategoryUpdate,
    KnowledgeCollectionCreate,
    KnowledgeCollectionItemCreate,
    KnowledgeCollectionResponse,
    KnowledgeCollectionUpdate,
    KnowledgeFoundationPlaceholder,
    KnowledgeOverviewResponse,
    KnowledgePipelineStatusResponse,
    KnowledgeRetentionPolicyCreate,
    KnowledgeRetentionPolicyResponse,
    KnowledgeReviewItemResponse,
    KnowledgeReviewResolveRequest,
    KnowledgeSettingsResponse,
    KnowledgeSettingsUpdate,
)
from investhome_api.services import knowledge_service as svc
from investhome_api.models.knowledge import KnowledgeCategory

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/overview", response_model=KnowledgeOverviewResponse)
def knowledge_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> KnowledgeOverviewResponse:
    return svc.build_knowledge_overview(db, user)


@router.get("/pipeline", response_model=KnowledgePipelineStatusResponse)
def knowledge_pipeline(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> KnowledgePipelineStatusResponse:
    _ = user
    return svc.pipeline_status(db)


@router.get("/categories", response_model=list[KnowledgeCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> list[KnowledgeCategoryResponse]:
    _ = user
    return svc.list_categories(db)


@router.post("/categories", response_model=KnowledgeCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    body: KnowledgeCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeCategoryResponse:
    _ = user
    try:
        return svc.create_category(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/categories/{category_id}", response_model=KnowledgeCategoryResponse)
def update_category(
    category_id: UUID,
    body: KnowledgeCategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeCategoryResponse:
    _ = user
    row = db.get(KnowledgeCategory, category_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category_not_found")
    if body.name_en is not None:
        row.name_en = body.name_en
    if body.name_tr is not None:
        row.name_tr = body.name_tr
    if body.description is not None:
        row.description = body.description
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_active is not None:
        if row.is_system and body.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_deactivate_system")
        row.is_active = body.is_active
    db.flush()
    return KnowledgeCategoryResponse.model_validate(row)


@router.get("/collections", response_model=list[KnowledgeCollectionResponse])
def list_collections(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> list[KnowledgeCollectionResponse]:
    _ = user
    return svc.list_collections(db)


@router.post("/collections", response_model=KnowledgeCollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    body: KnowledgeCollectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeCollectionResponse:
    return svc.create_collection(db, user, body)


@router.patch("/collections/{collection_id}", response_model=KnowledgeCollectionResponse)
def update_collection(
    collection_id: UUID,
    body: KnowledgeCollectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeCollectionResponse:
    _ = user
    try:
        return svc.update_collection(db, collection_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/collections/{collection_id}/items",
    response_model=KnowledgeCollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_collection_item(
    collection_id: UUID,
    body: KnowledgeCollectionItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeCollectionResponse:
    try:
        return svc.add_document_to_collection(db, collection_id, body.document_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/review", response_model=list[KnowledgeReviewItemResponse])
def list_review_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    reason: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission(("knowledge", "review"), ("documents", "approve"), ("documents", "update"))
    ),
) -> list[KnowledgeReviewItemResponse]:
    _ = user
    return svc.list_review_items(db, status=status_filter, reason=reason, limit=limit)


@router.post("/review/sync", response_model=dict)
def sync_review_queue(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission(("knowledge", "review"), ("documents", "approve"), ("documents", "update"))
    ),
) -> dict:
    _ = user
    created = svc.sync_review_queue(db)
    return {"created": created}


@router.post("/review/{item_id}/resolve", response_model=KnowledgeReviewItemResponse)
def resolve_review(
    item_id: UUID,
    body: KnowledgeReviewResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission(("knowledge", "review"), ("documents", "approve"), ("documents", "update"))
    ),
) -> KnowledgeReviewItemResponse:
    try:
        return svc.resolve_review_item(db, item_id, user, body.status, body.resolution_notes)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/retention", response_model=list[KnowledgeRetentionPolicyResponse])
def list_retention(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> list[KnowledgeRetentionPolicyResponse]:
    _ = user
    return svc.list_retention_policies(db)


@router.post("/retention", response_model=KnowledgeRetentionPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_retention(
    body: KnowledgeRetentionPolicyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeRetentionPolicyResponse:
    _ = user
    return svc.create_retention_policy(db, body)


@router.post("/ai-search", response_model=KnowledgeAiSearchResponse)
def knowledge_ai_search(
    body: KnowledgeAiSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> KnowledgeAiSearchResponse:
    # Permission-aware: document detail still enforces documents.* separately.
    _ = user
    return svc.ai_search(db, body.query, body.limit)


@router.get("/settings", response_model=KnowledgeSettingsResponse)
def get_knowledge_settings(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> KnowledgeSettingsResponse:
    _ = user
    return svc.get_settings(db)


@router.patch("/settings", response_model=KnowledgeSettingsResponse)
def patch_knowledge_settings(
    body: KnowledgeSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge", "manage")),
) -> KnowledgeSettingsResponse:
    _ = user
    return svc.update_settings(db, body)


@router.get("/placeholders", response_model=list[KnowledgeFoundationPlaceholder])
def list_placeholders(
    user: User = Depends(require_any_permission(("knowledge", "view"), ("documents", "view"))),
) -> list[KnowledgeFoundationPlaceholder]:
    _ = user
    return svc.foundation_placeholders()
