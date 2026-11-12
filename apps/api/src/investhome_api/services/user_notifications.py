"""One dispatch path for in-app notifications and optional preference-based email."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.notification import (
    NotificationPriority,
    NotificationSource,
    NotificationType,
)
from investhome_api.models.user_auth import User
from investhome_api.models.user_notification_preference import (
    NotificationDelivery,
    UserNotificationPreference,
)
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    NotificationChannel,
    get_notification_gateway,
)
from investhome_api.services.notification_service import _dedupe_key, create_notification
from investhome_api.services.user_invitation import _frontend_base_url

logger = logging.getLogger(__name__)

# Stable keys. Labels live in the web translations.
NOTIFICATION_EVENTS: tuple[str, ...] = (
    "instagram_message",
    "facebook_message",
    "new_lead",
    "task_reminder",
    "task_overdue",
    "meeting_reminder",
    "agreement_event",
    "social_publish",
)

_DONE_IN_APP = frozenset({"sent", "duplicate", "disabled"})
_DONE_EMAIL = frozenset({"sent", "duplicate", "disabled", "missing"})


@dataclass
class DispatchRequest:
    event_key: str
    recipient_user_id: UUID
    title_key: str
    message_key: str
    rule_key: str
    related_entity_type: str
    related_entity_id: UUID
    metadata: dict[str, Any] = field(default_factory=dict)
    link_module: str | None = None
    link_query: dict[str, str] | None = None
    destination_path: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    notification_type: NotificationType = NotificationType.SYSTEM
    priority: NotificationPriority = NotificationPriority.MEDIUM
    source: NotificationSource = NotificationSource.AUTOMATION
    allow_in_app: bool = True
    allow_email: bool = True
    retry_email: bool = False


def list_preference_state(db: Session, user_id: UUID) -> list[dict[str, object]]:
    rows = {
        row.event_key: row
        for row in db.scalars(
            select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)
        ).all()
    }
    items: list[dict[str, object]] = []
    for event_key in NOTIFICATION_EVENTS:
        row = rows.get(event_key)
        items.append(
            {
                "event_key": event_key,
                "in_app": True if row is None else bool(row.in_app),
                "email": False if row is None else bool(row.email),
            }
        )
    return items


def save_preference_state(db: Session, user_id: UUID, items: list[dict[str, object]]) -> list[dict[str, object]]:
    known = set(NOTIFICATION_EVENTS)
    for item in items:
        event_key = str(item.get("event_key") or "")
        if event_key not in known:
            continue
        row = db.scalar(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id,
                UserNotificationPreference.event_key == event_key,
            )
        )
        in_app = bool(item.get("in_app", True))
        email = bool(item.get("email", False))
        if row is None:
            db.add(
                UserNotificationPreference(
                    user_id=user_id,
                    event_key=event_key,
                    in_app=in_app,
                    email=email,
                )
            )
        else:
            row.in_app = in_app
            row.email = email
    db.flush()
    return list_preference_state(db, user_id)


def in_app_enabled(db: Session, user_id: UUID, event_key: str) -> bool:
    row = _preference(db, user_id, event_key)
    return True if row is None else bool(row.in_app)


def email_enabled(db: Session, user_id: UUID, event_key: str) -> bool:
    row = _preference(db, user_id, event_key)
    return False if row is None else bool(row.email)


def _preference(db: Session, user_id: UUID, event_key: str) -> UserNotificationPreference | None:
    return db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.event_key == event_key,
        )
    )


def dispatch_user_event(db: Session, request: DispatchRequest) -> dict[str, str]:
    """Create the in-app record and optional email once per recipient and rule."""
    if request.event_key not in NOTIFICATION_EVENTS:
        logger.info("user_notification_skipped event=%s reason=unknown", request.event_key)
        return {"in_app": "skipped", "email": "skipped"}
    dedupe = _dedupe_key(request.rule_key, request.related_entity_type, request.related_entity_id)
    delivery = db.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.recipient_user_id == request.recipient_user_id,
            NotificationDelivery.dedupe_key == dedupe,
        )
    )
    if delivery is None:
        delivery = NotificationDelivery(
            recipient_user_id=request.recipient_user_id,
            event_key=request.event_key,
            dedupe_key=dedupe,
        )
        db.add(delivery)
        db.flush()

    wants_in_app = request.allow_in_app and in_app_enabled(db, request.recipient_user_id, request.event_key)
    wants_email = request.allow_email and email_enabled(db, request.recipient_user_id, request.event_key)
    result = {"in_app": delivery.in_app_status or "skipped", "email": delivery.email_status or "skipped"}

    if not request.allow_in_app:
        result["in_app"] = delivery.in_app_status or "skipped"
    elif delivery.in_app_status in _DONE_IN_APP:
        result["in_app"] = "duplicate" if delivery.in_app_status == "sent" else delivery.in_app_status
    elif not wants_in_app:
        delivery.in_app_status = "disabled"
        result["in_app"] = "disabled"
    else:
        metadata = dict(request.metadata)
        if request.link_module:
            metadata["link_module"] = request.link_module
        if request.link_query:
            metadata["link_query"] = request.link_query
        if request.destination_path:
            metadata["destination_path"] = request.destination_path
        notification = create_notification(
            db,
            recipient_user_id=request.recipient_user_id,
            type=request.notification_type,
            priority=request.priority,
            title_key=request.title_key,
            message_key=request.message_key,
            rule_key=request.rule_key,
            related_entity_type=request.related_entity_type,
            related_entity_id=request.related_entity_id,
            metadata=metadata,
            source=request.source,
        )
        delivery.in_app_status = "sent" if notification is not None else "failed"
        result["in_app"] = delivery.in_app_status

    if not request.allow_email:
        result["email"] = delivery.email_status or "skipped"
    elif delivery.email_status == "sent":
        result["email"] = "duplicate"
    elif delivery.email_status in _DONE_EMAIL and not (
        request.retry_email and delivery.email_status == "failed"
    ):
        result["email"] = delivery.email_status
    elif not wants_email:
        delivery.email_status = "disabled"
        result["email"] = "disabled"
    else:
        result["email"] = _send_email(db, request)
        delivery.email_status = result["email"]

    logger.info(
        "user_notification event=%s user=%s in_app=%s email=%s",
        request.event_key,
        request.recipient_user_id,
        result["in_app"],
        result["email"],
    )
    return result


def _send_email(db: Session, request: DispatchRequest) -> str:
    user = db.get(User, request.recipient_user_id)
    email = (user.email or "").strip() if user is not None else ""
    if "@" not in email:
        logger.warning(
            "user_notification_email_missing event=%s user=%s",
            request.event_key,
            request.recipient_user_id,
        )
        return "missing"
    subject = request.email_subject or request.metadata.get("title") or request.event_key
    body = request.email_body or _default_email_body(request)
    try:
        outcome = get_notification_gateway().dispatch(
            GatewayMessage(
                channel=NotificationChannel.EMAIL,
                recipient=email,
                subject=str(subject),
                body=body,
                locale="tr",
                metadata={"purpose": "user_notification", "event_key": request.event_key},
            ),
            provider_id="email_smtp",
        )
    except Exception:
        logger.warning(
            "user_notification_email_failed event=%s user=%s reason=gateway",
            request.event_key,
            request.recipient_user_id,
        )
        return "failed"
    if not outcome.ok:
        logger.warning(
            "user_notification_email_failed event=%s user=%s status=%s",
            request.event_key,
            request.recipient_user_id,
            outcome.status,
        )
        return "failed"
    return "sent"


def _default_email_body(request: DispatchRequest) -> str:
    lines = []
    title = request.metadata.get("title") or request.metadata.get("name")
    if title:
        lines.append(str(title))
    if request.destination_path:
        lines.extend(["", _frontend_base_url() + request.destination_path])
    return "\n".join(lines) + ("\n" if lines else "")


def workspace_url(path: str) -> str:
    return f"{_frontend_base_url()}{path}"


def _active_sales_ids(db: Session) -> list[UUID]:
    from investhome_api.models.user_auth import Role, UserRole, UserStatus

    return list(
        db.scalars(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code == "sales",
                User.status == UserStatus.ACTIVE,
                User.archived_at.is_(None),
            )
        ).all()
    )


def notify_new_lead(db: Session, lead: Any, *, actor: User | None = None, contact_id: UUID | None = None) -> None:
    """Notify once when a lead row is created. Updates of the same lead do not call this."""
    recipient_ids: list[UUID] = []
    manager_id = getattr(lead, "assigned_manager_id", None)
    if manager_id is not None:
        recipient_ids.append(manager_id)
    elif actor is not None:
        recipient_ids.append(actor.id)
    else:
        recipient_ids.extend(_active_sales_ids(db))
    seen: set[UUID] = set()
    name = str(getattr(lead, "full_name", "") or "").strip() or "Lead"
    linked_contact = contact_id or getattr(lead, "converted_contact_id", None)
    link_query = {"lead": str(lead.id)}
    if linked_contact is not None:
        link_query["contact"] = str(linked_contact)
        destination = f"/workspaces/crm/contacts?contact={linked_contact}&lead={lead.id}"
        module = "crm/contacts"
    else:
        destination = f"/workspaces/crm/leads?lead={lead.id}"
        module = "crm/leads"
    for user_id in recipient_ids:
        if user_id in seen:
            continue
        seen.add(user_id)
        dispatch_user_event(
            db,
            DispatchRequest(
                event_key="new_lead",
                recipient_user_id=user_id,
                title_key="notifications.crm.new_lead.title",
                message_key="notifications.crm.new_lead.message",
                rule_key="crm.lead.created",
                related_entity_type="lead",
                related_entity_id=lead.id,
                link_module=module,
                link_query=link_query,
                destination_path=destination,
                email_subject=f"Yeni Lead: {name}",
                email_body=f"Yeni Lead: {name}\n{workspace_url(destination)}\n",
                notification_type=NotificationType.SYSTEM,
                priority=NotificationPriority.MEDIUM,
                source=NotificationSource.ACTIVITY,
                metadata={"name": name, "title": name, "related_label": name},
            ),
        )


def notify_agreement_created(
    db: Session,
    agreement: Any,
    *,
    actor: User | None = None,
    contact_name: str | None = None,
    contact_id: UUID | None = None,
) -> None:
    recipient_id = actor.id if actor is not None else None
    if recipient_id is None:
        return
    label = (contact_name or "").strip() or str(getattr(agreement, "project_group", "") or "Anlaşma")
    query: dict[str, str] = {}
    if contact_id is not None:
        query["contact"] = str(contact_id)
    query["agreement"] = str(agreement.id)
    destination = "/workspaces/crm/contacts?" + "&".join(f"{key}={value}" for key, value in query.items())
    dispatch_user_event(
        db,
        DispatchRequest(
            event_key="agreement_event",
            recipient_user_id=recipient_id,
            title_key="notifications.crm.agreement_created.title",
            message_key="notifications.crm.agreement_created.message",
            rule_key="crm.agreement.created",
            related_entity_type="crm_agreement",
            related_entity_id=agreement.id,
            link_module="crm/contacts",
            link_query=query,
            destination_path=destination,
            email_subject=f"Yeni anlaşma oluşturuldu: {label}",
            email_body=f"Yeni anlaşma oluşturuldu: {label}\n{workspace_url(destination)}\n",
            notification_type=NotificationType.SYSTEM,
            priority=NotificationPriority.MEDIUM,
            source=NotificationSource.ACTIVITY,
            metadata={"name": label, "title": label, "related_label": label},
        ),
    )


def notify_social_published(db: Session, *, user_id: UUID, post_id: UUID, title: str) -> None:
    """Called only after a provider reports a real publish. The current adapters do not."""
    dispatch_user_event(
        db,
        DispatchRequest(
            event_key="social_publish",
            recipient_user_id=user_id,
            title_key="notifications.crm.social_published.title",
            message_key="notifications.crm.social_published.message",
            rule_key="marketing.social.published",
            related_entity_type="social_post",
            related_entity_id=post_id,
            link_module="marketing",
            destination_path="/workspaces/marketing",
            email_subject=f"Sosyal medya yayını: {title}",
            email_body=f"Sosyal medya yayını tamamlandı: {title}\n",
            notification_type=NotificationType.SYSTEM,
            priority=NotificationPriority.LOW,
            source=NotificationSource.INTEGRATION,
            metadata={"title": title, "name": title, "related_label": title},
        ),
    )
