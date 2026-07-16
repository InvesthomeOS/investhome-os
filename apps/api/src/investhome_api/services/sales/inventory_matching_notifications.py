"""Notifications for sales inventory matching."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAsset
from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.models.sales_inventory_matching import SalesInventoryMatch
from investhome_api.services.notification_hooks import notify_users_with_permission


def notify_shortlisted_unavailable(
    db: Session,
    *,
    match: SalesInventoryMatch,
    asset: InventoryAsset,
) -> None:
    """Notify when a shortlisted asset becomes unavailable."""
    entity_id = match.opportunity_id or match.lead_id
    if entity_id is None:
        return

    notify_users_with_permission(
        db,
        resource="sales",
        action="view_inventory_matching",
        type=NotificationType.WARNING,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.sales.shortlisted_unavailable.title",
        message_key="notifications.sales.shortlisted_unavailable.message",
        rule_key="sales.inventory.shortlisted_unavailable",
        related_entity_type="sales_opportunity" if match.opportunity_id else "lead",
        related_entity_id=entity_id,
        metadata={
            "match_id": str(match.id),
            "asset_id": str(asset.id),
            "display_id": asset.display_id,
        },
    )


def notify_shortlist_shared(
    db: Session,
    *,
    shortlist_id: UUID,
    title: str,
    entity_id: UUID,
    opportunity: bool,
) -> None:
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_inventory_matching",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.LOW,
        title_key="notifications.sales.shortlist_shared.title",
        message_key="notifications.sales.shortlist_shared.message",
        rule_key="sales.shortlist.shared",
        related_entity_type="sales_opportunity" if opportunity else "lead",
        related_entity_id=entity_id,
        metadata={"shortlist_id": str(shortlist_id), "title": title},
    )
