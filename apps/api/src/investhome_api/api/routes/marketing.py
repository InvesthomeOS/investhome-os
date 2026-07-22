"""Marketing workspace API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.marketing import (
    MarketingAlert,
    MarketingApproval,
    MarketingBudget,
    MarketingChannel,
    MarketingContentAsset,
    MarketingEvent,
    MarketingRecommendation,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing import (
    MarketingAlertSummary,
    MarketingApprovalSummary,
    MarketingBudgetSummary,
    MarketingContentAssetSummary,
    MarketingDashboardResponse,
    MarketingEventSummary,
    MarketingNavigationResponse,
    MarketingProviderStatusesResponse,
    MarketingQuickActionsResponse,
    MarketingRecommendationSummary,
    MarketingWorkspaceOverviewResponse,
)
from investhome_api.services.marketing.campaign_service import compute_pages, get_workspace_overview
from investhome_api.services.marketing.dashboard_service import build_marketing_dashboard
from investhome_api.services.marketing.navigation_service import build_navigation, build_quick_actions

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.get("/dashboard", response_model=MarketingDashboardResponse)
def get_marketing_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> MarketingDashboardResponse:
    return build_marketing_dashboard(db, user)


@router.get("/overview", response_model=MarketingWorkspaceOverviewResponse)
def get_marketing_workspace_overview(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_any_permission(
            ("marketing", "view"),
            ("marketing", "view_dashboard"),
            ("marketing", "manage_campaigns"),
        )
    ),
) -> MarketingWorkspaceOverviewResponse:
    return get_workspace_overview(db)


@router.get("/navigation", response_model=MarketingNavigationResponse)
def get_marketing_navigation(
    user: User = Depends(require_permission("marketing", "view")),
) -> MarketingNavigationResponse:
    return build_navigation(user)


@router.get("/quick-actions", response_model=MarketingQuickActionsResponse)
def get_marketing_quick_actions(
    user: User = Depends(require_permission("marketing", "view")),
) -> MarketingQuickActionsResponse:
    return build_quick_actions(user)


@router.get("/provider-statuses", response_model=MarketingProviderStatusesResponse)
def get_marketing_provider_statuses(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_provider_connections")),
) -> MarketingProviderStatusesResponse:
    from investhome_api.services.marketing.dashboard_service import _fetch_provider_statuses

    return MarketingProviderStatusesResponse(providers=_fetch_provider_statuses(db))


def _list_entities(db: Session, model, summary_cls, *, page: int, page_size: int):
    query = select(model)
    if hasattr(model, "archived_at"):
        query = query.where(model.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(model.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items = [summary_cls.model_validate(row) for row in rows]
    return items, total



@router.get("/events")
def list_marketing_events(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_events")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    items, total = _list_entities(db, MarketingEvent, MarketingEventSummary, page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}


@router.get("/budgets")
def list_marketing_budgets(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_budgets")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    items, total = _list_entities(db, MarketingBudget, MarketingBudgetSummary, page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}


@router.get("/approvals")
def list_marketing_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "approve_content")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    items, total = _list_entities(db, MarketingApproval, MarketingApprovalSummary, page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}


@router.get("/alerts")
def list_marketing_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    items, total = _list_entities(db, MarketingAlert, MarketingAlertSummary, page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}


@router.get("/recommendations")
def list_marketing_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    items, total = _list_entities(db, MarketingRecommendation, MarketingRecommendationSummary, page=page, page_size=page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}


@router.get("/channels")
def list_marketing_channels(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    rows = db.scalars(select(MarketingChannel).order_by(MarketingChannel.name)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "name": row.name,
                "category": row.category.value,
                "provider": row.provider,
                "status": row.status.value,
                "connection_status": row.connection_status.value,
            }
            for row in rows
        ]
    }
