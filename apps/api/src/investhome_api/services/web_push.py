"""Browser push subscriptions.

Production keys are never invented here. Push is skipped until
WEB_PUSH_VAPID_PUBLIC_KEY, WEB_PUSH_VAPID_PRIVATE_KEY, and
WEB_PUSH_VAPID_SUBJECT are configured and the optional `pywebpush`
package is installed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.user_auth import User
from investhome_api.models.user_notification_preference import UserPushSubscription

logger = logging.getLogger(__name__)


def push_configuration() -> dict[str, object]:
    settings = get_settings()
    public = (settings.web_push_vapid_public_key or "").strip()
    private = (settings.web_push_vapid_private_key or "").strip()
    subject = (settings.web_push_vapid_subject or "").strip()
    configured = bool(public and private and subject)
    return {"configured": configured, "public_key": public if configured else None}


def save_push_subscription(db: Session, user: User, body: dict[str, Any]) -> UserPushSubscription:
    endpoint = str(body.get("endpoint") or "").strip()
    keys = body.get("keys") if isinstance(body.get("keys"), dict) else {}
    p256dh = str(keys.get("p256dh") or body.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or body.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        raise ValueError("Push subscription is incomplete")
    row = db.scalar(
        select(UserPushSubscription).where(
            UserPushSubscription.user_id == user.id,
            UserPushSubscription.endpoint == endpoint,
        )
    )
    if row is None:
        row = UserPushSubscription(
            user_id=user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=str(body.get("user_agent") or "")[:300] or None,
        )
        db.add(row)
    else:
        row.p256dh = p256dh
        row.auth = auth
    db.flush()
    return row


def dispatch_web_push(db: Session, *, user_id, title: str, body: str, notification_id: str) -> None:
    """Best-effort native push. Missing keys or library leave in-app delivery alone."""
    config = push_configuration()
    if not config["configured"]:
        return
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.info("pywebpush is not installed; desktop push stays disabled")
        return
    settings = get_settings()
    rows = list(
        db.scalars(select(UserPushSubscription).where(UserPushSubscription.user_id == user_id)).all()
    )
    payload = json.dumps({"title": title, "body": body, "notification_id": notification_id})
    for row in rows:
        try:
            webpush(
                subscription_info={
                    "endpoint": row.endpoint,
                    "keys": {"p256dh": row.p256dh, "auth": row.auth},
                },
                data=payload,
                vapid_private_key=settings.web_push_vapid_private_key,
                vapid_claims={"sub": settings.web_push_vapid_subject},
            )
        except WebPushException:
            logger.info("web push failed for subscription %s", row.id)
        except Exception:
            logger.info("web push skipped for subscription %s", row.id)
