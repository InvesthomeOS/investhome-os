"""Conversion events and analytics shells — honest not_connected."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import MarketingConversionEvent


def list_conversion_events(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    event_type: str | None = None,
    form_id: UUID | None = None,
) -> tuple[list[MarketingConversionEvent], int]:
    query = select(MarketingConversionEvent)
    if event_type:
        query = query.where(MarketingConversionEvent.event_type == event_type)
    if form_id:
        query = query.where(MarketingConversionEvent.form_id == form_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingConversionEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_conversion_analytics_shell(db: Session) -> dict:
    """Honest analytics — no fabricated metrics."""
    count = db.scalar(select(func.count()).select_from(MarketingConversionEvent)) or 0
    return {
        "connected": False,
        "message": "Analytics provider not connected",
        "metrics": {"conversion_events_recorded": count} if count else None,
    }


def get_attribution_shell(db: Session) -> dict:
    """Honest attribution shell — no fabricated data."""
    from investhome_api.models.marketing_landing_conversion import MarketingTrackingContext

    tracking_count = db.scalar(select(func.count()).select_from(MarketingTrackingContext)) or 0
    return {
        "connected": False,
        "message": "Attribution data requires analytics provider connection",
        "summary": {"tracking_contexts": tracking_count} if tracking_count else None,
    }


def get_provider_statuses() -> list[dict]:
    return [
        {"provider": "hosting", "connected": False, "status": "not_connected", "message": "Hosting provider not configured"},
        {"provider": "analytics", "connected": False, "status": "not_connected", "message": "Analytics provider not configured"},
        {"provider": "verification", "connected": False, "status": "not_connected", "message": "Verification provider not configured"},
        {"provider": "spam", "connected": False, "status": "not_connected", "message": "Spam filter not configured"},
        {"provider": "booking", "connected": False, "status": "not_connected", "message": "Booking integration not configured"},
        {"provider": "ad_conversion_sync", "connected": False, "status": "not_connected", "message": "Ad conversion sync not configured"},
    ]
