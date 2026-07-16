"""Notifications for sales proposals."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.models.sales_proposal import SalesProposal
from investhome_api.services.notification_hooks import notify_users_with_permission


def _notify(
    db: Session,
    *,
    rule_key: str,
    title_key: str,
    message_key: str,
    proposal: SalesProposal,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    ntype: NotificationType = NotificationType.SYSTEM,
    extra: dict | None = None,
    resource: str = "sales",
    action: str = "view_proposal",
) -> None:
    metadata = {
        "proposal_id": str(proposal.id),
        "proposal_number": proposal.proposal_number,
        "title": proposal.title,
        **(extra or {}),
    }
    notify_users_with_permission(
        db,
        resource=resource,
        action=action,
        type=ntype,
        priority=priority,
        title_key=title_key,
        message_key=message_key,
        rule_key=rule_key,
        related_entity_type="sales_proposal",
        related_entity_id=proposal.id,
        metadata=metadata,
    )


def notify_review_required(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.review_required",
        title_key="notifications.sales.proposal.review_required.title",
        message_key="notifications.sales.proposal.review_required.message",
        proposal=proposal,
        action="review_proposal",
    )


def notify_revision_requested(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.revision_requested",
        title_key="notifications.sales.proposal.revision_requested.title",
        message_key="notifications.sales.proposal.revision_requested.message",
        proposal=proposal,
    )


def notify_approved(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.approved",
        title_key="notifications.sales.proposal.approved.title",
        message_key="notifications.sales.proposal.approved.message",
        proposal=proposal,
    )


def notify_rejected(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.rejected",
        title_key="notifications.sales.proposal.rejected.title",
        message_key="notifications.sales.proposal.rejected.message",
        proposal=proposal,
        ntype=NotificationType.WARNING,
    )


def notify_ready_to_send(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.ready_to_send",
        title_key="notifications.sales.proposal.ready_to_send.title",
        message_key="notifications.sales.proposal.ready_to_send.message",
        proposal=proposal,
    )


def notify_expiring(db: Session, proposal: SalesProposal, *, days_left: int) -> None:
    _notify(
        db,
        rule_key="sales.proposal.expiring",
        title_key="notifications.sales.proposal.expiring.title",
        message_key="notifications.sales.proposal.expiring.message",
        proposal=proposal,
        priority=NotificationPriority.HIGH,
        ntype=NotificationType.WARNING,
        extra={"days_left": days_left},
    )


def notify_expired(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.expired",
        title_key="notifications.sales.proposal.expired.title",
        message_key="notifications.sales.proposal.expired.message",
        proposal=proposal,
        ntype=NotificationType.WARNING,
    )


def notify_viewed(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.viewed",
        title_key="notifications.sales.proposal.viewed.title",
        message_key="notifications.sales.proposal.viewed.message",
        proposal=proposal,
        priority=NotificationPriority.LOW,
    )


def notify_accepted(db: Session, proposal: SalesProposal) -> None:
    _notify(
        db,
        rule_key="sales.proposal.accepted",
        title_key="notifications.sales.proposal.accepted.title",
        message_key="notifications.sales.proposal.accepted.message",
        proposal=proposal,
        priority=NotificationPriority.HIGH,
    )


def notify_stale(db: Session, proposal: SalesProposal, *, stale_count: int) -> None:
    _notify(
        db,
        rule_key="sales.proposal.stale",
        title_key="notifications.sales.proposal.stale.title",
        message_key="notifications.sales.proposal.stale.message",
        proposal=proposal,
        ntype=NotificationType.WARNING,
        extra={"stale_count": stale_count},
    )
