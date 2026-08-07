"""AI semantic / hybrid search API — retrieval only (no chat / LLM answers)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.ai_search import AiSearchRequest, AiSearchResponse, AiSearchResultItem
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search

router = APIRouter(tags=["ai-search"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.post("/ai/search", response_model=AiSearchResponse)
def ai_search(
    body: AiSearchRequest,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> AiSearchResponse:
    """Hybrid semantic + keyword search over indexed AI Documents."""
    try:
        hits = hybrid_search(
            db,
            query=body.query,
            project_scope=body.project_scope,
            project_id=body.project_id,
            project_ids=body.project_ids,
            limit=body.limit,
            category=body.category,
            builder=body.builder,
        )
    except ProjectScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    items = [
        AiSearchResultItem(
            asset_id=h.asset_id,
            document_id=h.document_id,
            chunk_id=h.chunk_id,
            chunk=h.chunk_text,
            chunk_order=h.chunk_order,
            score=h.score,
            semantic_score=h.semantic_score,
            keyword_score=h.keyword_score,
            summary=h.summary,
            source=h.source,
            file=h.file,
            project_id=h.project_id,
            category=h.category,
            builders=h.builders,
        )
        for h in hits
    ]
    return AiSearchResponse(
        query=body.query.strip(),
        project_scope=body.project_scope,
        total=len(items),
        items=items,
    )
