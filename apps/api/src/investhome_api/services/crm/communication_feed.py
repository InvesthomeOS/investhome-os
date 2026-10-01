"""Central CRM communication feed — Bitrix history + live-foundation records.

No provider connection. No sending. Source-ID dedupe so co-owner copies are hidden.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType, CrmActivityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_communication import CrmCommunication, CrmCommunicationMatchStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_live_communications import (
    CommunicationConversationMessage,
    CommunicationConversationResponse,
    CommunicationFeedItem,
    CommunicationFeedResponse,
    CommunicationFeedStats,
)
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.contact_service import _activity_source_key
from investhome_api.services.crm.nedim_purchase_card import activity_deal_id

COMM_TYPES = (
    CrmActivityType.EMAIL,
    CrmActivityType.WHATSAPP,
    CrmActivityType.PHONE_CALL,
    CrmActivityType.SMS,
    CrmActivityType.COMMENT,
    CrmActivityType.NOTE,
    CrmActivityType.MEETING,
    CrmActivityType.ZOOM_MEETING,
    CrmActivityType.TEAMS_MEETING,
    CrmActivityType.SITE_VISIT,
    CrmActivityType.PROPERTY_TOUR,
    CrmActivityType.INVESTOR_MEETING,
    CrmActivityType.CONSTRUCTION_MEETING,
)

CHANNEL_TYPES: dict[str, tuple[CrmActivityType, ...]] = {
    "email": (CrmActivityType.EMAIL,),
    "whatsapp": (CrmActivityType.WHATSAPP,),
    "call": (CrmActivityType.PHONE_CALL,),
    "sms": (CrmActivityType.SMS,),
    "comment": (CrmActivityType.COMMENT, CrmActivityType.NOTE),
    "meeting": (
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.SITE_VISIT,
        CrmActivityType.PROPERTY_TOUR,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
    ),
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _plain(value: str | None, *, limit: int = 220) -> str:
    text = _TAG_RE.sub(" ", str(value or ""))
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _history(activity: CrmActivity) -> dict:
    metadata = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
    history = metadata.get("bitrix_history")
    if isinstance(history, dict):
        return history
    live = metadata.get("live_thread")
    return live if isinstance(live, dict) else {}


def _channel(activity: CrmActivity) -> str:
    history = _history(activity)
    kind = str(history.get("kind") or "").lower()
    if "whatsapp" in kind:
        return "whatsapp"
    if "email" in kind:
        return "email"
    value = activity.activity_type.value if hasattr(activity.activity_type, "value") else str(activity.activity_type)
    for channel, types in CHANNEL_TYPES.items():
        if any(item.value == value for item in types):
            return channel
    return "other"


def _direction(activity: CrmActivity) -> str:
    history = _history(activity)
    raw = str(history.get("direction") or "").strip().lower()
    if raw in {"outgoing", "outbound", "out"}:
        return "outbound"
    if raw in {"system", "internal"}:
        return "internal"
    return "inbound"


def _occurred(activity: CrmActivity) -> datetime:
    return activity.start_date or activity.created_at


def _project_label(group: str | None) -> str | None:
    if not group:
        return None
    try:
        return BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup(group)]
    except ValueError:
        return group


def _contact_ids_for_project(db: Session, project_group: str) -> list[UUID]:
    agreement_ids = list(db.scalars(select(CrmAgreement.id).where(CrmAgreement.project_group == project_group)).all())
    if not agreement_ids:
        return []
    owners = list(db.scalars(select(CrmAgreement.contact_id).where(CrmAgreement.id.in_(agreement_ids))).all())
    participants = list(
        db.scalars(
            select(CrmAgreementParticipant.contact_id).where(CrmAgreementParticipant.agreement_id.in_(agreement_ids))
        ).all()
    )
    return list({item for item in [*owners, *participants] if item})


def _activity_query(
    db: Session,
    *,
    search: str | None,
    channel: str | None,
    contact_id: UUID | None,
    person: str | None,
    project_group: str | None,
    owner_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[tuple[CrmActivity]]:
    query = (
        select(CrmActivity)
        .outerjoin(
            CrmContact,
            (CrmActivity.entity_type == CrmActivityEntityType.CONTACT) & (CrmActivity.entity_id == CrmContact.id),
        )
        .where(CrmActivity.archived_at.is_(None), CrmActivity.activity_type.in_(COMM_TYPES))
    )
    if channel and channel in CHANNEL_TYPES:
        query = query.where(CrmActivity.activity_type.in_(CHANNEL_TYPES[channel]))
    if contact_id:
        query = query.where(
            CrmActivity.entity_id == contact_id,
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
        )
    if person:
        query = query.where(CrmContact.display_name.ilike(f"%{person.strip()}%"))
    if owner_id:
        query = query.where(
            or_(
                CrmActivity.assigned_user_id == owner_id,
                CrmActivity.owner_id == owner_id,
                CrmActivity.created_by == owner_id,
            )
        )
    if date_from is not None:
        query = query.where(func.coalesce(CrmActivity.start_date, CrmActivity.created_at) >= date_from)
    if date_to is not None:
        query = query.where(func.coalesce(CrmActivity.start_date, CrmActivity.created_at) <= date_to)
    if project_group:
        ids = _contact_ids_for_project(db, project_group)
        query = query.where(
            CrmActivity.entity_id.in_(ids or [UUID("00000000-0000-0000-0000-000000000000")]),
            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
        )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                CrmActivity.title.ilike(pattern),
                CrmActivity.summary.ilike(pattern),
                CrmActivity.description.ilike(pattern),
                CrmContact.display_name.ilike(pattern),
            )
        )
    return query


def _dedupe_activities(rows: list[CrmActivity]) -> list[CrmActivity]:
    chosen: dict[str, CrmActivity] = {}
    order: list[str] = []
    for activity in sorted(rows, key=_occurred, reverse=True):
        key = _activity_source_key(activity)
        if key in chosen:
            continue
        chosen[key] = activity
        order.append(key)
    return [chosen[key] for key in order]


def _group_whatsapp_latest(rows: list[CrmActivity]) -> list[CrmActivity]:
    """Keep one WhatsApp row per chat/person so the hub lists conversations, not every bubble."""
    latest: dict[str, CrmActivity] = {}
    order: list[str] = []
    for activity in rows:
        if _channel(activity) != "whatsapp":
            key = _activity_source_key(activity)
        else:
            history = _history(activity)
            chat = str(history.get("chat_id") or "").strip()
            person = str(activity.entity_id or "")
            key = f"wa-thread:{chat or person or activity.id}"
        if key in latest:
            continue
        latest[key] = activity
        order.append(key)
    return [latest[key] for key in order]


def communication_stats(db: Session) -> CommunicationFeedStats:
    counts = {
        (item.value if hasattr(item, "value") else str(item)): int(total)
        for item, total in db.execute(
            select(CrmActivity.activity_type, func.count())
            .where(CrmActivity.archived_at.is_(None), CrmActivity.activity_type.in_(COMM_TYPES))
            .group_by(CrmActivity.activity_type)
        ).all()
    }

    def _count(*types: CrmActivityType) -> int:
        return int(sum(int(counts.get(item.value) or 0) for item in types))

    email = _count(CrmActivityType.EMAIL)
    whatsapp = _count(CrmActivityType.WHATSAPP)
    total = _count(*COMM_TYPES)
    unmatched = int(
        db.scalar(
            select(func.count())
            .select_from(CrmCommunication)
            .where(
                CrmCommunication.archived_at.is_(None),
                CrmCommunication.match_status.in_(
                    [CrmCommunicationMatchStatus.UNMATCHED.value, CrmCommunicationMatchStatus.AMBIGUOUS.value]
                ),
            )
        )
        or 0
    )
    return CommunicationFeedStats(total=total, email=email, whatsapp=whatsapp, unmatched=unmatched)


def _agreements_for_contacts(db: Session, contact_ids: list[UUID]) -> dict[UUID, list[CrmAgreement]]:
    if not contact_ids:
        return {}
    owner_rows = list(db.scalars(select(CrmAgreement).where(CrmAgreement.contact_id.in_(contact_ids))).all())
    part_rows = list(
        db.execute(
            select(CrmAgreementParticipant.contact_id, CrmAgreement)
            .join(CrmAgreement, CrmAgreement.id == CrmAgreementParticipant.agreement_id)
            .where(CrmAgreementParticipant.contact_id.in_(contact_ids))
        ).all()
    )
    grouped: dict[UUID, list[CrmAgreement]] = {}
    seen: dict[UUID, set[UUID]] = {}
    for agreement in owner_rows:
        bucket = grouped.setdefault(agreement.contact_id, [])
        ids = seen.setdefault(agreement.contact_id, set())
        if agreement.id not in ids:
            ids.add(agreement.id)
            bucket.append(agreement)
    for contact_id, agreement in part_rows:
        bucket = grouped.setdefault(contact_id, [])
        ids = seen.setdefault(contact_id, set())
        if agreement.id not in ids:
            ids.add(agreement.id)
            bucket.append(agreement)
    return grouped


def _pick_purchase(activity: CrmActivity, agreements: list[CrmAgreement]) -> CrmAgreement | None:
    deal = activity_deal_id(activity.metadata_json if isinstance(activity.metadata_json, dict) else None)
    if deal:
        for agreement in agreements:
            source = str(agreement.source_external_id or "")
            if source == f"bitrix_deal:{deal}" or source.endswith(f":{deal}") or source == deal:
                return agreement
    if len(agreements) == 1:
        return agreements[0]
    return None


def _serialize_activity(
    activity: CrmActivity,
    *,
    contacts: dict[UUID, CrmContact],
    users: dict[UUID, User],
    agreements: dict[UUID, list[CrmAgreement]],
) -> CommunicationFeedItem:
    contact = contacts.get(activity.entity_id) if activity.entity_type == CrmActivityEntityType.CONTACT else None
    owner_id = activity.assigned_user_id or activity.owner_id or activity.created_by
    owner = users.get(owner_id) if owner_id else None
    history = _history(activity)
    purchases = agreements.get(activity.entity_id, []) if contact else []
    purchase = _pick_purchase(activity, purchases)
    project_label = _project_label(purchase.project_group) if purchase else None
    unit = purchase.unit_number if purchase else None
    project_unit = " · ".join([item for item in [project_label, unit] if item]) or None
    preview_source = activity.summary or activity.description or activity.title
    return CommunicationFeedItem(
        id=activity.id,
        source="activity",
        channel=_channel(activity),
        direction=_direction(activity),
        occurred_at=_occurred(activity),
        subject=_plain(activity.title, limit=160) or None,
        preview=_plain(preview_source),
        contact_id=contact.id if contact else None,
        contact_name=contact.display_name if contact else None,
        agreement_id=purchase.id if purchase else None,
        project_group=purchase.project_group if purchase else None,
        project_label=project_label,
        unit_number=unit,
        project_unit=project_unit,
        owner_id=owner_id,
        owner_name=owner.full_name if owner else None,
        conversation_key=str(history.get("chat_id") or "") or None,
        source_key=_activity_source_key(activity),
        activity_id=activity.id,
    )


def _serialize_live(
    row: CrmCommunication,
    *,
    contacts: dict[UUID, CrmContact],
    users: dict[UUID, User],
    agreements: dict[UUID, list[CrmAgreement]],
) -> CommunicationFeedItem:
    contact = contacts.get(row.contact_id) if row.contact_id else None
    owner_id = row.assigned_user_id or row.owner_id or row.created_by
    owner = users.get(owner_id) if owner_id else None
    purchases = agreements.get(row.contact_id, []) if row.contact_id else []
    purchase = next((item for item in purchases if item.id == row.agreement_id), None)
    if purchase is None and len(purchases) == 1:
        purchase = purchases[0]
    project_label = _project_label(purchase.project_group) if purchase else None
    unit = purchase.unit_number if purchase else None
    project_unit = " · ".join([item for item in [project_label, unit] if item]) or None
    channel = "call" if row.channel in {"phone", "call"} else row.channel
    direction = row.direction if row.direction in {"inbound", "outbound", "internal"} else "inbound"
    source_id = str(row.external_provider_id or row.content_hash or row.id)
    return CommunicationFeedItem(
        id=row.id,
        source=row.source or "live",
        channel=channel,
        direction=direction,
        occurred_at=row.occurred_at or row.created_at,
        subject=_plain(row.subject, limit=160) or None,
        preview=_plain(row.preview or row.body_text or row.body),
        contact_id=contact.id if contact else None,
        contact_name=contact.display_name if contact else None,
        agreement_id=purchase.id if purchase else row.agreement_id,
        project_group=purchase.project_group if purchase else None,
        project_label=project_label,
        unit_number=unit,
        project_unit=project_unit,
        owner_id=owner_id,
        owner_name=owner.full_name if owner else None,
        conversation_key=row.conversation_key,
        source_key=f"live:{channel}:{source_id}",
        activity_id=row.activity_id,
    )


def _matched_live_rows(
    db: Session,
    *,
    search: str | None,
    channel: str | None,
    contact_id: UUID | None,
    person: str | None,
    project_group: str | None,
    owner_id: UUID | None,
    direction: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[CrmCommunication]:
    query = (
        select(CrmCommunication)
        .outerjoin(CrmContact, CrmCommunication.contact_id == CrmContact.id)
        .where(
            CrmCommunication.archived_at.is_(None),
            CrmCommunication.match_status == CrmCommunicationMatchStatus.MATCHED.value,
        )
    )
    if channel:
        aliases = {"call": ("call", "phone"), "comment": ("comment", "note")}
        query = query.where(CrmCommunication.channel.in_(aliases.get(channel, (channel,))))
    if contact_id:
        query = query.where(CrmCommunication.contact_id == contact_id)
    if person:
        query = query.where(CrmContact.display_name.ilike(f"%{person.strip()}%"))
    if owner_id:
        query = query.where(
            or_(
                CrmCommunication.assigned_user_id == owner_id,
                CrmCommunication.owner_id == owner_id,
                CrmCommunication.created_by == owner_id,
            )
        )
    if date_from is not None:
        query = query.where(func.coalesce(CrmCommunication.occurred_at, CrmCommunication.created_at) >= date_from)
    if date_to is not None:
        query = query.where(func.coalesce(CrmCommunication.occurred_at, CrmCommunication.created_at) <= date_to)
    if project_group:
        ids = _contact_ids_for_project(db, project_group)
        query = query.where(CrmCommunication.contact_id.in_(ids or [UUID("00000000-0000-0000-0000-000000000000")]))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                CrmCommunication.subject.ilike(pattern),
                CrmCommunication.preview.ilike(pattern),
                CrmCommunication.body_text.ilike(pattern),
                CrmContact.display_name.ilike(pattern),
            )
        )
    if direction in {"inbound", "outbound", "internal"}:
        query = query.where(CrmCommunication.direction == direction)
    return list(
        db.scalars(
            query.order_by(
                func.coalesce(CrmCommunication.occurred_at, CrmCommunication.created_at).desc(),
                CrmCommunication.id.desc(),
            ).limit(80)
        ).all()
    )


def list_communication_feed(
    db: Session,
    *,
    search: str | None = None,
    channel: str | None = None,
    contact_id: UUID | None = None,
    person: str | None = None,
    project_group: str | None = None,
    owner_id: UUID | None = None,
    direction: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> CommunicationFeedResponse:
    stats = communication_stats(db)
    query = _activity_query(
        db,
        search=search,
        channel=channel,
        contact_id=contact_id,
        person=person,
        project_group=project_group,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
    )
    ordered = query.order_by(func.coalesce(CrmActivity.start_date, CrmActivity.created_at).desc(), CrmActivity.id.desc())
    total = int(db.scalar(select(func.count()).select_from(ordered.order_by(None).subquery())) or 0)
    window = max(page_size * (12 if direction else 4), 80)
    start = max(page - 1, 0) * page_size
    fetched = list(db.scalars(ordered.offset(max(start - page_size, 0)).limit(window)).all())
    if direction in {"inbound", "outbound", "internal"}:
        fetched = [row for row in fetched if _direction(row) == direction]
    unique = _group_whatsapp_latest(_dedupe_activities(fetched))
    if start > 0:
        skip = start - max(start - page_size, 0)
        unique = unique[skip:]
    page_rows = unique[:page_size]
    live_rows = _matched_live_rows(
        db,
        search=search,
        channel=channel,
        contact_id=contact_id,
        person=person,
        project_group=project_group,
        owner_id=owner_id,
        direction=direction,
        date_from=date_from,
        date_to=date_to,
    ) if page == 1 else []
    contact_ids = [
        item
        for item in [
            *[row.entity_id for row in page_rows if row.entity_type == CrmActivityEntityType.CONTACT],
            *[row.contact_id for row in live_rows if row.contact_id],
        ]
        if item
    ]
    contacts = {
        item.id: item for item in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
    } if contact_ids else {}
    user_ids = {
        item
        for row in [*page_rows, *live_rows]
        for item in (row.assigned_user_id, row.owner_id, row.created_by)
        if item
    }
    users = {item.id: item for item in db.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
    agreements = _agreements_for_contacts(db, contact_ids)
    items = [_serialize_activity(row, contacts=contacts, users=users, agreements=agreements) for row in page_rows]
    if live_rows:
        live_items = [_serialize_live(row, contacts=contacts, users=users, agreements=agreements) for row in live_rows]
        merged = {item.source_key: item for item in live_items}
        for item in items:
            merged[item.source_key] = item
        items = sorted(
            merged.values(),
            key=lambda item: (item.occurred_at.replace(tzinfo=None) if item.occurred_at and item.occurred_at.tzinfo else item.occurred_at)
            or datetime(1970, 1, 1),
            reverse=True,
        )[:page_size]
    return CommunicationFeedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size) if total else 1,
        stats=stats,
    )


def list_whatsapp_conversation(
    db: Session,
    *,
    activity_id: UUID | None = None,
    contact_id: UUID | None = None,
    chat_id: str | None = None,
) -> CommunicationConversationResponse:
    seed = db.get(CrmActivity, activity_id) if activity_id else None
    history = _history(seed) if seed else {}
    chat = (chat_id or str(history.get("chat_id") or "")).strip()
    person_id = contact_id or (seed.entity_id if seed and seed.entity_type == CrmActivityEntityType.CONTACT else None)
    query = select(CrmActivity).where(
        CrmActivity.archived_at.is_(None),
        CrmActivity.activity_type == CrmActivityType.WHATSAPP,
    )
    if person_id:
        query = query.where(CrmActivity.entity_id == person_id, CrmActivity.entity_type == CrmActivityEntityType.CONTACT)
    rows = list(db.scalars(query).all())
    if chat:
        matched = [row for row in rows if str(_history(row).get("chat_id") or "").strip() == chat]
        if matched:
            rows = matched
    unique = _dedupe_activities(rows)
    unique.sort(key=_occurred)
    messages = [
        CommunicationConversationMessage(
            id=row.id,
            title=row.title,
            summary=row.summary or row.description or row.title,
            actor_name=str(_history(row).get("author_name") or "") or None,
            created_at=_occurred(row),
            activity_type="whatsapp",
            metadata={"bitrix_history": _history(row)},
        )
        for row in unique
    ]
    contact = db.get(CrmContact, person_id) if person_id else None
    return CommunicationConversationResponse(
        contact_id=person_id,
        contact_name=contact.display_name if contact else None,
        conversation_key=chat or None,
        messages=messages,
    )
