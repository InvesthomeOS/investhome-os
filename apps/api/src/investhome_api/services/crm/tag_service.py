"""Live CRM tags — create, edit, deactivate, assign. No demo seed. No hard-delete."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.crm_contact import CrmContact, CrmContactTag, CrmTag, CrmTagEvent
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm import (
    CrmTagAssignRequest,
    CrmTagContactRef,
    CrmTagCreate,
    CrmTagDetail,
    CrmTagItem,
    CrmTagListResponse,
    CrmTagStats,
    CrmTagUpdate,
)
from investhome_api.schemas.crm_contacts import CrmContactTagItem

ACTIVE = "active"
INACTIVE = "inactive"


class TagConflictError(ValueError):
    pass


class TagNotFoundError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _status(value: str | None) -> str:
    raw = (value or ACTIVE).strip().lower()
    return INACTIVE if raw in {INACTIVE, "passive", "archived", "pasif"} else ACTIVE


def _record_event(
    db: Session,
    *,
    tag_id: UUID,
    action: str,
    actor: User | None,
    contact_id: UUID | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        CrmTagEvent(
            id=uuid4(),
            tag_id=tag_id,
            contact_id=contact_id,
            actor_user_id=actor.id if actor is not None else None,
            action=action,
            payload=payload,
        )
    )


def _sync_contact_tag_names(contact: CrmContact) -> None:
    names: list[str] = []
    seen: set[str] = set()
    for link in contact.tag_links or []:
        tag = getattr(link, "tag", None)
        name = str(getattr(tag, "name", "") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    contact.tags = names or None


def serialize_contact_tag_items(contact: CrmContact) -> list[CrmContactTagItem]:
    items: list[CrmContactTagItem] = []
    seen: set[UUID] = set()
    for link in getattr(contact, "tag_links", None) or []:
        tag = getattr(link, "tag", None)
        if tag is None or tag.id in seen:
            continue
        seen.add(tag.id)
        items.append(
            CrmContactTagItem(
                id=tag.id,
                name=tag.name,
                status=_status(getattr(tag, "status", None)),
            )
        )
    return items


def tag_stats(db: Session) -> CrmTagStats:
    total_tags = int(db.scalar(select(func.count()).select_from(CrmTag)) or 0)
    people_query = select(func.count()).select_from(CrmContact).where(CrmContact.archived_at.is_(None))
    total_people = int(db.scalar(people_query) or 0)
    tagged_people = int(
        db.scalar(
            select(func.count(func.distinct(CrmContactTag.contact_id)))
            .select_from(CrmContactTag)
            .join(CrmContact, CrmContact.id == CrmContactTag.contact_id)
            .where(CrmContact.archived_at.is_(None))
        )
        or 0
    )
    untagged_people = max(total_people - tagged_people, 0)
    return CrmTagStats(
        total_tags=total_tags,
        tagged_people=tagged_people,
        untagged_people=untagged_people,
    )


def _usage_map(db: Session, tag_ids: list[UUID]) -> dict[UUID, int]:
    if not tag_ids:
        return {}
    rows = db.execute(
        select(CrmContactTag.tag_id, func.count())
        .where(CrmContactTag.tag_id.in_(tag_ids))
        .group_by(CrmContactTag.tag_id)
    ).all()
    return {tag_id: int(count) for tag_id, count in rows}


def serialize_tag(tag: CrmTag, usage_count: int = 0) -> CrmTagItem:
    return CrmTagItem(
        id=tag.id,
        name=tag.name,
        description=tag.description,
        status=_status(tag.status),
        color=tag.color,
        usage_count=usage_count,
        created_at=tag.created_at,
        updated_at=tag.updated_at or tag.created_at,
    )


def list_tags(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
) -> CrmTagListResponse:
    query = select(CrmTag)
    if search and search.strip():
        query = query.where(CrmTag.name.ilike(f"%{search.strip()}%"))
    if status and status.strip() and status.strip().lower() not in {"all", "tumu", "tümü"}:
        query = query.where(CrmTag.status == _status(status))
    rows = list(db.scalars(query.order_by(CrmTag.name.asc())).all())
    usage = _usage_map(db, [row.id for row in rows])
    return CrmTagListResponse(
        items=[serialize_tag(row, usage.get(row.id, 0)) for row in rows],
        stats=tag_stats(db),
    )


def get_tag(db: Session, tag_id: UUID) -> CrmTagDetail:
    tag = db.get(CrmTag, tag_id)
    if tag is None:
        raise TagNotFoundError("crm.tags.errors.not_found")
    usage = _usage_map(db, [tag.id]).get(tag.id, 0)
    people_rows = db.execute(
        select(CrmContact)
        .join(CrmContactTag, CrmContactTag.contact_id == CrmContact.id)
        .where(CrmContactTag.tag_id == tag.id)
        .order_by(CrmContact.display_name.asc())
        .options(selectinload(CrmContact.tag_links))
    ).scalars().all()
    return CrmTagDetail(
        **serialize_tag(tag, usage).model_dump(),
        people=[
            CrmTagContactRef(id=person.id, display_name=person.display_name)
            for person in people_rows
        ],
    )


def create_tag(db: Session, payload: CrmTagCreate, *, actor: User | None) -> CrmTagDetail:
    name = payload.name.strip()
    if not name:
        raise TagConflictError("crm.tags.errors.name_required")
    existing = db.scalar(select(CrmTag).where(func.lower(CrmTag.name) == name.casefold()))
    if existing is not None:
        raise TagConflictError("crm.tags.errors.duplicate_name")
    tag = CrmTag(
        id=uuid4(),
        name=name,
        description=(payload.description or "").strip() or None,
        status=_status(payload.status),
        color="navy",
        created_by=actor.id if actor is not None else None,
        updated_by=actor.id if actor is not None else None,
    )
    db.add(tag)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise TagConflictError("crm.tags.errors.duplicate_name") from exc
    _record_event(
        db,
        tag_id=tag.id,
        action="created",
        actor=actor,
        payload={"name": tag.name, "status": tag.status},
    )
    db.commit()
    db.refresh(tag)
    return get_tag(db, tag.id)


def update_tag(db: Session, tag_id: UUID, payload: CrmTagUpdate, *, actor: User | None) -> CrmTagDetail:
    tag = db.get(CrmTag, tag_id)
    if tag is None:
        raise TagNotFoundError("crm.tags.errors.not_found")
    before = {"name": tag.name, "description": tag.description, "status": tag.status}
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise TagConflictError("crm.tags.errors.name_required")
        clash = db.scalar(
            select(CrmTag).where(func.lower(CrmTag.name) == name.casefold(), CrmTag.id != tag.id)
        )
        if clash is not None:
            raise TagConflictError("crm.tags.errors.duplicate_name")
        tag.name = name
    if payload.description is not None:
        tag.description = payload.description.strip() or None
    if payload.status is not None:
        tag.status = _status(payload.status)
    tag.updated_by = actor.id if actor is not None else None
    tag.updated_at = _utcnow()
    _record_event(
        db,
        tag_id=tag.id,
        action="updated",
        actor=actor,
        payload={"before": before, "after": {"name": tag.name, "description": tag.description, "status": tag.status}},
    )
    db.add(tag)
    db.commit()
    return get_tag(db, tag.id)


def set_tag_status(db: Session, tag_id: UUID, status: str, *, actor: User | None) -> CrmTagDetail:
    tag = db.get(CrmTag, tag_id)
    if tag is None:
        raise TagNotFoundError("crm.tags.errors.not_found")
    next_status = _status(status)
    if tag.status != next_status:
        tag.status = next_status
        tag.updated_by = actor.id if actor is not None else None
        tag.updated_at = _utcnow()
        _record_event(
            db,
            tag_id=tag.id,
            action="deactivated" if next_status == INACTIVE else "activated",
            actor=actor,
            payload={"status": next_status},
        )
        db.add(tag)
        db.commit()
    return get_tag(db, tag.id)


def assign_tag(
    db: Session,
    *,
    contact_id: UUID,
    payload: CrmTagAssignRequest,
    actor: User | None,
) -> list[CrmContactTagItem]:
    contact = db.scalar(
        select(CrmContact)
        .where(CrmContact.id == contact_id)
        .options(selectinload(CrmContact.tag_links).selectinload(CrmContactTag.tag))
    )
    if contact is None:
        raise TagNotFoundError("crm.contacts.errors.not_found")
    tag = db.get(CrmTag, payload.tag_id)
    if tag is None:
        raise TagNotFoundError("crm.tags.errors.not_found")
    if _status(tag.status) != ACTIVE:
        raise TagConflictError("crm.tags.errors.inactive")
    already = next((link for link in contact.tag_links if link.tag_id == tag.id), None)
    if already is not None:
        raise TagConflictError("crm.tags.errors.already_assigned")
    link = CrmContactTag(
        contact_id=contact.id,
        tag_id=tag.id,
        created_by=actor.id if actor is not None else None,
    )
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise TagConflictError("crm.tags.errors.already_assigned") from exc
    contact.tag_links.append(link)
    link.tag = tag
    _sync_contact_tag_names(contact)
    _record_event(
        db,
        tag_id=tag.id,
        action="assigned",
        actor=actor,
        contact_id=contact.id,
        payload={"contact_id": str(contact.id), "contact_name": contact.display_name},
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return serialize_contact_tag_items(contact)


def remove_tag(
    db: Session,
    *,
    contact_id: UUID,
    tag_id: UUID,
    actor: User | None,
) -> list[CrmContactTagItem]:
    contact = db.scalar(
        select(CrmContact)
        .where(CrmContact.id == contact_id)
        .options(selectinload(CrmContact.tag_links).selectinload(CrmContactTag.tag))
    )
    if contact is None:
        raise TagNotFoundError("crm.contacts.errors.not_found")
    link = next((item for item in contact.tag_links if item.tag_id == tag_id), None)
    if link is None:
        return serialize_contact_tag_items(contact)
    contact.tag_links.remove(link)
    db.delete(link)
    _sync_contact_tag_names(contact)
    _record_event(
        db,
        tag_id=tag_id,
        action="removed",
        actor=actor,
        contact_id=contact.id,
        payload={"contact_id": str(contact.id), "contact_name": contact.display_name},
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return serialize_contact_tag_items(contact)
