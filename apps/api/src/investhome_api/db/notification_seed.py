"""Backfill notifications from existing demo and live business data."""

from sqlalchemy import select

from investhome_api.models.notification import Notification
from investhome_api.services.notification_generator import sync_notifications_for_all_users


def seed_notifications() -> int:
    from investhome_api.db.session import SessionLocal

    with SessionLocal() as session:
        existing = session.scalar(select(Notification.id).limit(1))
        if existing is not None:
            return 0
        return sync_notifications_for_all_users(session)
