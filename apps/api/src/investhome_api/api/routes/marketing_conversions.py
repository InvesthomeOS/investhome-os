"""Marketing conversions and attribution API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    AttributionShell,
    ConversionAnalyticsShell,
    ConversionEventResponse,
    ProviderStatusResponse,
)
from investhome_api.services.marketing.conversion_service import (
    get_attribution_shell,
    get_conversion_analytics_shell,
    get_provider_statuses,
    list_conversion_events,
)
from investhome_api.services.marketing.submission_service import compute_pages

router = APIRouter(prefix="/marketing/conversions", tags=["marketing-conversions"])
attribution_router = APIRouter(prefix="/marketing/attribution", tags=["marketing-attribution"])


@router.get("/events", response_model=list[ConversionEventResponse])
def list_events_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_conversions")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    event_type: str | None = None,
    form_id: UUID | None = None,
):
    items, _ = list_conversion_events(db, page=page, page_size=page_size, event_type=event_type, form_id=form_id)
    return [
        ConversionEventResponse(
            id=e.id,
            event_type=e.event_type,
            submission_id=e.submission_id,
            lead_context_id=e.lead_context_id,
            created_at=e.created_at,
        )
        for e in items
    ]


@router.get("/analytics", response_model=ConversionAnalyticsShell)
def conversion_analytics_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export_analytics")),
):
    return get_conversion_analytics_shell(db)


@router.get("/providers", response_model=list[ProviderStatusResponse])
def conversion_providers_route(
    user: User = Depends(require_permission("marketing", "view_conversions")),
):
    return get_provider_statuses()


@attribution_router.get("", response_model=AttributionShell)
def attribution_shell_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
):
    return get_attribution_shell(db)
