"""Channel calendar aggregation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_channel_communications import (
    EmailCampaign,
    SmsCampaign,
    SocialPost,
    WhatsAppCampaign,
)


def list_channel_calendar_items(db: Session) -> list[dict]:
    items: list[dict] = []

    for post in db.scalars(
        select(SocialPost)
        .where(SocialPost.archived_at.is_(None), SocialPost.scheduled_at.is_not(None))
        .order_by(SocialPost.scheduled_at)
    ).all():
        items.append({
            "id": str(post.id),
            "channel": "social",
            "title": post.title or "Social post",
            "status": post.status.value,
            "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        })

    for model, channel, label in (
        (EmailCampaign, "email", "Email campaign"),
        (WhatsAppCampaign, "whatsapp", "WhatsApp campaign"),
        (SmsCampaign, "sms", "SMS campaign"),
    ):
        for campaign in db.scalars(
            select(model)
            .where(model.archived_at.is_(None), model.scheduled_at.is_not(None))
            .order_by(model.scheduled_at)
        ).all():
            items.append({
                "id": str(campaign.id),
                "channel": channel,
                "title": campaign.name or label,
                "status": campaign.status.value,
                "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
            })

    items.sort(key=lambda x: x.get("scheduled_at") or "")
    return items
