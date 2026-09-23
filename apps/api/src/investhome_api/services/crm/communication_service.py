"""CRM communication center services."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationAttachment,
    CrmCommunicationChannel,
    CrmCommunicationDirection,
    CrmCommunicationPreference,
    CrmCommunicationSequence,
    CrmCommunicationSequenceStep,
    CrmCommunicationSignature,
    CrmCommunicationStatus,
    CrmCommunicationTemplate,
    CrmCommunicationThread,
    CrmCommunicationVisibility,
    CrmThreadStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_communications import (
    AnalyticsDashboardResponse,
    AnalyticsMetricSchema,
    CommunicationCreate,
    CommunicationDetail,
    CommunicationSummary,
    CommunicationUpdate,
    PreferenceDetail,
    PreferenceUpsert,
    ProviderStatusSchema,
    SequenceCreate,
    SequenceDetail,
    SequenceSummary,
    SequenceUpdate,
    SignatureCreate,
    SignatureDetail,
    SignatureSummary,
    SignatureUpdate,
    TemplateCreate,
    TemplateDetail,
    TemplateSummary,
    TemplateUpdate,
    ThreadDetail,
    ThreadSummary,
)
from investhome_api.services.crm.providers.registry import get_all_provider_statuses
from investhome_api.services.crm_communication_activity import (
    record_communication_archived,
    record_communication_created,
    record_communication_restored,
    record_communication_updated,
    snapshot_communication,
)
from investhome_api.services.permission_service import user_has_permission

FOLDER_STATUS_MAP: dict[str, list[str]] = {
    "inbox": [CrmCommunicationStatus.SENT.value, CrmCommunicationStatus.DELIVERED.value, CrmCommunicationStatus.OPENED.value, CrmCommunicationStatus.REPLIED.value],
    "sent": [CrmCommunicationStatus.SENT.value, CrmCommunicationStatus.DELIVERED.value],
    "drafts": [CrmCommunicationStatus.DRAFT.value],
    "scheduled": [CrmCommunicationStatus.SCHEDULED.value, CrmCommunicationStatus.QUEUED.value],
    "failed": [CrmCommunicationStatus.FAILED.value],
    "archived": [CrmCommunicationStatus.ARCHIVED.value],
}

CHANNEL_FOLDER_MAP: dict[str, str] = {
    "calls": CrmCommunicationChannel.PHONE.value,
    "whatsapp": CrmCommunicationChannel.WHATSAPP.value,
    "sms": CrmCommunicationChannel.SMS.value,
    "meetings": CrmCommunicationChannel.MEETING.value,
    "internal": CrmCommunicationChannel.INTERNAL_MESSAGE.value,
}


def _can_view_private(user: User) -> bool:
    return user_has_permission(user, "crm", "view_private_communications")


def _can_view_restricted(user: User) -> bool:
    return user_has_permission(user, "crm", "view_restricted_communications") or _can_view_private(user)


def _can_override_restrictions(user: User) -> bool:
    return user_has_permission(user, "crm", "override_restrictions")


def _visibility_filter(user: User):
    if _can_view_restricted(user):
        return None
    if _can_view_private(user):
        return or_(
            CrmCommunication.visibility != CrmCommunicationVisibility.RESTRICTED.value,
            CrmCommunication.created_by == user.id,
            CrmCommunication.owner_id == user.id,
            CrmCommunication.assigned_user_id == user.id,
        )
    return or_(
        CrmCommunication.visibility.in_(
            [
                CrmCommunicationVisibility.TEAM.value,
                CrmCommunicationVisibility.ORGANIZATION.value,
            ]
        ),
        CrmCommunication.created_by == user.id,
        CrmCommunication.owner_id == user.id,
        CrmCommunication.assigned_user_id == user.id,
    )


def _thread_visibility_filter(user: User):
    if _can_view_restricted(user):
        return None
    return or_(
        CrmCommunicationThread.owner_id == user.id,
        CrmCommunicationThread.assigned_user_id == user.id,
        CrmCommunicationThread.owner_id.is_(None),
    )


def _make_preview(body: str | None, body_text: str | None, max_len: int = 200) -> str | None:
    text = body_text or body
    if not text:
        return None
    stripped = text.strip()
    return stripped[:max_len] + ("…" if len(stripped) > max_len else "")


def _serialize_comm_summary(comm: CrmCommunication) -> CommunicationSummary:
    return CommunicationSummary(
        id=comm.id,
        channel=CrmCommunicationChannel(comm.channel),
        direction=CrmCommunicationDirection(comm.direction),
        status=CrmCommunicationStatus(comm.status),
        subject=comm.subject,
        preview=comm.preview,
        thread_id=comm.thread_id,
        recipient_entity_type=comm.recipient_entity_type,
        recipient_entity_id=comm.recipient_entity_id,
        priority=comm.priority,
        visibility=comm.visibility,
        owner_id=comm.owner_id,
        assigned_user_id=comm.assigned_user_id,
        scheduled_at=comm.scheduled_at,
        sent_at=comm.sent_at,
        tags=comm.tags,
        has_attachments=bool(comm.attachments),
        created_at=comm.created_at,
        updated_at=comm.updated_at,
        archived_at=comm.archived_at,
    )


def _serialize_comm_detail(comm: CrmCommunication) -> CommunicationDetail:
    summary = _serialize_comm_summary(comm)
    return CommunicationDetail(
        **summary.model_dump(),
        body=comm.body,
        body_html=comm.body_html,
        body_text=comm.body_text,
        sender_entity_type=comm.sender_entity_type,
        sender_entity_id=comm.sender_entity_id,
        recipients=comm.recipients,
        cc_recipients=comm.cc_recipients,
        bcc_recipients=comm.bcc_recipients,
        participants=comm.participants,
        related_entities=comm.related_entities,
        parent_communication_id=comm.parent_communication_id,
        external_provider_id=comm.external_provider_id,
        provider_thread_id=comm.provider_thread_id,
        delivered_at=comm.delivered_at,
        opened_at=comm.opened_at,
        clicked_at=comm.clicked_at,
        replied_at=comm.replied_at,
        failed_at=comm.failed_at,
        failure_reason=comm.failure_reason,
        assigned_team_id=comm.assigned_team_id,
        metadata_json=comm.metadata_json,
        call_duration_seconds=comm.call_duration_seconds,
        call_outcome=comm.call_outcome,
        call_direction=comm.call_direction,
        meeting_url=comm.meeting_url,
        meeting_start_at=comm.meeting_start_at,
        meeting_end_at=comm.meeting_end_at,
        activity_id=comm.activity_id,
        attachments=comm.attachments,
        created_by=comm.created_by,
        updated_by=comm.updated_by,
    )


def _serialize_thread_summary(thread: CrmCommunicationThread, preview: str | None = None) -> ThreadSummary:
    return ThreadSummary(
        id=thread.id,
        subject=thread.subject,
        channel=CrmCommunicationChannel(thread.channel),
        channels=thread.channels,
        unread_count=thread.unread_count,
        message_count=thread.message_count,
        priority=thread.priority,
        status=thread.status,
        tags=thread.tags,
        follow_up_date=thread.follow_up_date,
        last_communication_at=thread.last_communication_at,
        last_inbound_at=thread.last_inbound_at,
        last_outbound_at=thread.last_outbound_at,
        owner_id=thread.owner_id,
        assigned_user_id=thread.assigned_user_id,
        assigned_team_id=thread.assigned_team_id,
        is_pinned=thread.is_pinned,
        snoozed_until=thread.snoozed_until,
        preview=preview,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        archived_at=thread.archived_at,
    )


def _update_thread_stats(db: Session, thread: CrmCommunicationThread) -> None:
    count_stmt = select(func.count()).where(
        CrmCommunication.thread_id == thread.id,
        CrmCommunication.archived_at.is_(None),
    )
    thread.message_count = db.scalar(count_stmt) or 0
    last_comm = db.scalar(
        select(CrmCommunication)
        .where(CrmCommunication.thread_id == thread.id, CrmCommunication.archived_at.is_(None))
        .order_by(CrmCommunication.created_at.desc())
        .limit(1)
    )
    if last_comm:
        thread.last_communication_at = last_comm.sent_at or last_comm.created_at
        thread.subject = thread.subject or last_comm.subject or "(No subject)"
        if last_comm.direction == CrmCommunicationDirection.INBOUND.value:
            thread.last_inbound_at = last_comm.sent_at or last_comm.created_at
        elif last_comm.direction == CrmCommunicationDirection.OUTBOUND.value:
            thread.last_outbound_at = last_comm.sent_at or last_comm.created_at


def _link_activity_for_communication(db: Session, comm: CrmCommunication, user: User) -> None:
    activity_type_map = {
        CrmCommunicationChannel.EMAIL.value: CrmActivityType.EMAIL,
        CrmCommunicationChannel.WHATSAPP.value: CrmActivityType.WHATSAPP,
        CrmCommunicationChannel.SMS.value: CrmActivityType.SMS,
        CrmCommunicationChannel.PHONE.value: CrmActivityType.PHONE_CALL,
        CrmCommunicationChannel.MEETING.value: CrmActivityType.MEETING,
        CrmCommunicationChannel.ZOOM.value: CrmActivityType.ZOOM_MEETING,
        CrmCommunicationChannel.TEAMS.value: CrmActivityType.TEAMS_MEETING,
        CrmCommunicationChannel.INTERNAL_MESSAGE.value: CrmActivityType.INTERNAL_DISCUSSION,
        CrmCommunicationChannel.NOTE.value: CrmActivityType.NOTE,
    }
    activity_type = activity_type_map.get(comm.channel, CrmActivityType.OTHER)
    entity_type = comm.recipient_entity_type or CrmActivityEntityType.CONTACT.value
    entity_id = comm.recipient_entity_id
    if not entity_id and comm.related_entities:
        first = comm.related_entities[0]
        entity_type = first.get("entity_type", CrmActivityEntityType.CONTACT.value)
        entity_id = first.get("entity_id")
    if not entity_id:
        return
    activity = CrmActivity(
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type.value,
        activity_category=CrmActivityCategory.COMMUNICATION.value,
        title=comm.subject or comm.preview or f"{comm.channel} communication",
        summary=comm.preview,
        description=comm.body_text or comm.body,
        status=CrmActivityStatus.COMPLETED.value if comm.status == CrmCommunicationStatus.SENT.value else CrmActivityStatus.PLANNED.value,
        owner_id=comm.owner_id or user.id,
        assigned_user_id=comm.assigned_user_id,
        visibility=comm.visibility,
        meeting_url=comm.meeting_url,
        start_date=comm.meeting_start_at,
        end_date=comm.meeting_end_at,
        duration_minutes=(comm.call_duration_seconds // 60) if comm.call_duration_seconds else None,
        metadata_json={"communication_id": str(comm.id), "channel": comm.channel},
        created_by=user.id,
    )
    db.add(activity)
    db.flush()
    comm.activity_id = activity.id


def check_consent_warnings(
    db: Session,
    *,
    channel: CrmCommunicationChannel,
    recipient_entity_type: str | None,
    recipient_entity_id: UUID | None,
) -> list[str]:
    if not recipient_entity_type or not recipient_entity_id:
        return []
    pref = db.scalar(
        select(CrmCommunicationPreference).where(
            CrmCommunicationPreference.entity_type == recipient_entity_type,
            CrmCommunicationPreference.entity_id == recipient_entity_id,
        )
    )
    if pref is None:
        return []
    warnings: list[str] = []
    if pref.do_not_contact:
        warnings.append("crm.communications.warnings.do_not_contact")
    channel_consent = {
        CrmCommunicationChannel.EMAIL: pref.consent_email,
        CrmCommunicationChannel.SMS: pref.consent_sms,
        CrmCommunicationChannel.WHATSAPP: pref.consent_whatsapp,
        CrmCommunicationChannel.PHONE: pref.consent_phone,
    }
    consent = channel_consent.get(channel)
    if consent is False:
        warnings.append(f"crm.communications.warnings.no_consent_{channel.value}")
    if pref.blocked_channels and channel.value in pref.blocked_channels:
        warnings.append("crm.communications.warnings.channel_blocked")
    return warnings


def get_communication_or_none(db: Session, communication_id: UUID) -> CrmCommunication | None:
    return db.scalar(
        select(CrmCommunication)
        .options(selectinload(CrmCommunication.attachments))
        .where(CrmCommunication.id == communication_id)
    )


def get_thread_or_none(db: Session, thread_id: UUID) -> CrmCommunicationThread | None:
    return db.scalar(
        select(CrmCommunicationThread)
        .options(selectinload(CrmCommunicationThread.communications))
        .where(CrmCommunicationThread.id == thread_id)
    )


def list_threads(
    db: Session,
    user: User,
    *,
    folder: str | None = None,
    search: str | None = None,
    channel: CrmCommunicationChannel | None = None,
    channels: list[CrmCommunicationChannel] | None = None,
    status: CrmThreadStatus | None = None,
    owner_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    assigned_team_id: UUID | None = None,
    unread_only: bool = False,
    follow_up_due: bool = False,
    include_archived: bool = False,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    sort_by: str = "last_communication_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[ThreadSummary], dict[str, int]]:
    stmt = select(CrmCommunicationThread)
    vis = _thread_visibility_filter(user)
    if vis is not None:
        stmt = stmt.where(vis)
    if not include_archived:
        stmt = stmt.where(CrmCommunicationThread.archived_at.is_(None))
    if folder == "assigned_to_me":
        stmt = stmt.where(CrmCommunicationThread.assigned_user_id == user.id)
    elif folder == "unread":
        stmt = stmt.where(CrmCommunicationThread.unread_count > 0)
    elif folder == "follow_up_due":
        stmt = stmt.where(
            CrmCommunicationThread.follow_up_date.isnot(None),
            CrmCommunicationThread.follow_up_date <= datetime.now(tz=UTC),
        )
    elif folder == "archived":
        stmt = stmt.where(CrmCommunicationThread.archived_at.isnot(None))
    elif folder and folder in CHANNEL_FOLDER_MAP:
        stmt = stmt.where(CrmCommunicationThread.channel == CHANNEL_FOLDER_MAP[folder])
    if channel:
        stmt = stmt.where(CrmCommunicationThread.channel == channel.value)
    if channels:
        channel_values = [c.value for c in channels]
        stmt = stmt.where(CrmCommunicationThread.channel.in_(channel_values))
    if status:
        stmt = stmt.where(CrmCommunicationThread.status == status.value)
    if owner_id:
        stmt = stmt.where(CrmCommunicationThread.owner_id == owner_id)
    if assigned_user_id:
        stmt = stmt.where(CrmCommunicationThread.assigned_user_id == assigned_user_id)
    if assigned_team_id:
        stmt = stmt.where(CrmCommunicationThread.assigned_team_id == assigned_team_id)
    if unread_only:
        stmt = stmt.where(CrmCommunicationThread.unread_count > 0)
    if follow_up_due:
        stmt = stmt.where(
            CrmCommunicationThread.follow_up_date.isnot(None),
            CrmCommunicationThread.follow_up_date <= datetime.now(tz=UTC),
        )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(CrmCommunicationThread.subject.ilike(pattern))
    if entity_type and entity_id:
        stmt = stmt.where(
            CrmCommunicationThread.related_entity_ids.contains([{"entity_type": entity_type, "entity_id": str(entity_id)}])
        )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    sort_col = getattr(CrmCommunicationThread, sort_by, CrmCommunicationThread.last_communication_at)
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    rows = db.scalars(stmt.order_by(CrmCommunicationThread.is_pinned.desc(), order).offset((page - 1) * page_size).limit(page_size)).all()
    items = [_serialize_thread_summary(row) for row in rows]
    pages = math.ceil(total / page_size) if page_size else 0
    return items, {"page": page, "page_size": page_size, "total": total, "pages": pages}


def get_thread_detail(db: Session, user: User, thread_id: UUID) -> ThreadDetail | None:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return None
    vis = _thread_visibility_filter(user)
    if vis is not None:
        allowed = db.scalar(select(CrmCommunicationThread.id).where(CrmCommunicationThread.id == thread_id, vis))
        if allowed is None:
            return None
    comms_stmt = (
        select(CrmCommunication)
        .options(selectinload(CrmCommunication.attachments))
        .where(CrmCommunication.thread_id == thread_id, CrmCommunication.archived_at.is_(None))
        .order_by(CrmCommunication.created_at.asc())
    )
    vis_comm = _visibility_filter(user)
    if vis_comm is not None:
        comms_stmt = comms_stmt.where(vis_comm)
    comms = db.scalars(comms_stmt).all()
    summary = _serialize_thread_summary(thread, preview=comms[-1].preview if comms else None)
    return ThreadDetail(
        **summary.model_dump(),
        participant_ids=thread.participant_ids,
        related_entity_ids=thread.related_entity_ids,
        response_time_seconds=thread.response_time_seconds,
        sentiment=thread.sentiment,
        communications=[_serialize_comm_summary(c) for c in comms],
    )


def list_communications(
    db: Session,
    user: User,
    *,
    folder: str | None = None,
    search: str | None = None,
    channel: CrmCommunicationChannel | None = None,
    direction: CrmCommunicationDirection | None = None,
    status: CrmCommunicationStatus | None = None,
    thread_id: UUID | None = None,
    owner_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[CommunicationSummary], dict[str, int]]:
    stmt = select(CrmCommunication).options(selectinload(CrmCommunication.attachments))
    vis = _visibility_filter(user)
    if vis is not None:
        stmt = stmt.where(vis)
    if not include_archived:
        stmt = stmt.where(CrmCommunication.archived_at.is_(None))
    if folder and folder in FOLDER_STATUS_MAP:
        stmt = stmt.where(CrmCommunication.status.in_(FOLDER_STATUS_MAP[folder]))
    elif folder and folder in CHANNEL_FOLDER_MAP:
        stmt = stmt.where(CrmCommunication.channel == CHANNEL_FOLDER_MAP[folder])
    elif folder == "assigned_to_me":
        stmt = stmt.where(CrmCommunication.assigned_user_id == user.id)
    if channel:
        stmt = stmt.where(CrmCommunication.channel == channel.value)
    if direction:
        stmt = stmt.where(CrmCommunication.direction == direction.value)
    if status:
        stmt = stmt.where(CrmCommunication.status == status.value)
    if thread_id:
        stmt = stmt.where(CrmCommunication.thread_id == thread_id)
    if owner_id:
        stmt = stmt.where(CrmCommunication.owner_id == owner_id)
    if assigned_user_id:
        stmt = stmt.where(CrmCommunication.assigned_user_id == assigned_user_id)
    if entity_type and entity_id:
        stmt = stmt.where(
            CrmCommunication.recipient_entity_type == entity_type,
            CrmCommunication.recipient_entity_id == entity_id,
        )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(CrmCommunication.subject.ilike(pattern), CrmCommunication.preview.ilike(pattern)))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    sort_col = getattr(CrmCommunication, sort_by, CrmCommunication.created_at)
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    rows = db.scalars(stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    items = [_serialize_comm_summary(row) for row in rows]
    pages = math.ceil(total / page_size) if page_size else 0
    return items, {"page": page, "page_size": page_size, "total": total, "pages": pages}


def create_communication(
    db: Session,
    user: User,
    payload: CommunicationCreate,
    *,
    request: Any = None,
) -> tuple[CommunicationDetail, list[str]]:
    warnings = check_consent_warnings(
        db,
        channel=payload.channel,
        recipient_entity_type=payload.recipient_entity_type.value if payload.recipient_entity_type else None,
        recipient_entity_id=payload.recipient_entity_id,
    )
    if warnings and not _can_override_restrictions(user):
        pass  # warnings returned to client; creation still allowed for drafts

    preview = _make_preview(payload.body, payload.body_text)
    thread_id = payload.thread_id
    thread: CrmCommunicationThread | None = None
    if thread_id:
        thread = get_thread_or_none(db, thread_id)
    elif payload.subject or preview:
        thread = CrmCommunicationThread(
            subject=payload.subject or preview or "(No subject)",
            channel=payload.channel.value,
            channels=[payload.channel.value],
            owner_id=payload.owner_id or user.id,
            assigned_user_id=payload.assigned_user_id,
            assigned_team_id=payload.assigned_team_id,
            related_entity_ids=[e.model_dump(mode="json") for e in payload.related_entities] if payload.related_entities else None,
            last_communication_at=datetime.now(tz=UTC),
            message_count=0,
        )
        db.add(thread)
        db.flush()
        thread_id = thread.id

    comm = CrmCommunication(
        channel=payload.channel.value,
        direction=payload.direction.value,
        status=payload.status.value,
        subject=payload.subject,
        preview=preview,
        body=payload.body,
        body_html=payload.body_html,
        body_text=payload.body_text,
        sender_entity_type=payload.sender_entity_type.value if payload.sender_entity_type else None,
        sender_entity_id=payload.sender_entity_id,
        recipient_entity_type=payload.recipient_entity_type.value if payload.recipient_entity_type else None,
        recipient_entity_id=payload.recipient_entity_id,
        recipients=[r.model_dump(mode="json") for r in payload.recipients] if payload.recipients else None,
        cc_recipients=[r.model_dump(mode="json") for r in payload.cc_recipients] if payload.cc_recipients else None,
        bcc_recipients=[r.model_dump(mode="json") for r in payload.bcc_recipients] if payload.bcc_recipients else None,
        participants=payload.participants,
        related_entities=[e.model_dump(mode="json") for e in payload.related_entities] if payload.related_entities else None,
        thread_id=thread_id,
        parent_communication_id=payload.parent_communication_id,
        scheduled_at=payload.scheduled_at,
        priority=payload.priority.value,
        visibility=payload.visibility.value,
        owner_id=payload.owner_id or user.id,
        assigned_user_id=payload.assigned_user_id,
        assigned_team_id=payload.assigned_team_id,
        tags=payload.tags,
        metadata_json=payload.metadata_json,
        call_duration_seconds=payload.call_duration_seconds,
        call_outcome=payload.call_outcome,
        call_direction=payload.call_direction,
        meeting_url=payload.meeting_url,
        meeting_start_at=payload.meeting_start_at,
        meeting_end_at=payload.meeting_end_at,
        created_by=user.id,
    )
    if payload.status == CrmCommunicationStatus.SENT:
        comm.sent_at = datetime.now(tz=UTC)
    db.add(comm)
    db.flush()

    if payload.status in {CrmCommunicationStatus.SENT, CrmCommunicationStatus.DELIVERED}:
        _link_activity_for_communication(db, comm, user)

    if thread:
        _update_thread_stats(db, thread)

    record_communication_created(db, comm.id, user, request=request)
    db.commit()
    db.refresh(comm)
    return _serialize_comm_detail(comm), warnings


def update_communication(
    db: Session,
    user: User,
    communication_id: UUID,
    payload: CommunicationUpdate,
    *,
    request: Any = None,
) -> CommunicationDetail | None:
    comm = get_communication_or_none(db, communication_id)
    if comm is None:
        return None
    before = snapshot_communication(comm)
    data = payload.model_dump(exclude_unset=True)
    if "recipients" in data and data["recipients"] is not None:
        data["recipients"] = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in data["recipients"]]
    if "cc_recipients" in data and data["cc_recipients"] is not None:
        data["cc_recipients"] = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in data["cc_recipients"]]
    if "bcc_recipients" in data and data["bcc_recipients"] is not None:
        data["bcc_recipients"] = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in data["bcc_recipients"]]
    for key, value in data.items():
        if key in {"status", "priority", "visibility"} and value is not None:
            setattr(comm, key, value.value if hasattr(value, "value") else value)
        elif value is not None:
            setattr(comm, key, value)
    if payload.body or payload.body_text:
        comm.preview = _make_preview(comm.body, comm.body_text)
    comm.updated_by = user.id
    after = snapshot_communication(comm)
    record_communication_updated(db, comm.id, user, before, after, request=request)
    db.commit()
    db.refresh(comm)
    return _serialize_comm_detail(comm)


def archive_communication(db: Session, user: User, communication_id: UUID, *, request: Any = None) -> bool:
    comm = get_communication_or_none(db, communication_id)
    if comm is None:
        return False
    comm.archived_at = datetime.now(tz=UTC)
    comm.status = CrmCommunicationStatus.ARCHIVED.value
    comm.updated_by = user.id
    record_communication_archived(db, comm.id, user, request=request)
    db.commit()
    return True


def restore_communication(db: Session, user: User, communication_id: UUID, *, request: Any = None) -> bool:
    comm = get_communication_or_none(db, communication_id)
    if comm is None or comm.archived_at is None:
        return False
    comm.archived_at = None
    comm.status = CrmCommunicationStatus.DRAFT.value
    comm.updated_by = user.id
    record_communication_restored(db, comm.id, user, request=request)
    db.commit()
    return True


def mark_thread_read(db: Session, thread_id: UUID) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.unread_count = 0
    db.commit()
    return True


def mark_thread_unread(db: Session, thread_id: UUID) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.unread_count = max(thread.unread_count, 1)
    db.commit()
    return True


def assign_thread(
    db: Session,
    thread_id: UUID,
    *,
    assigned_user_id: UUID | None = None,
    assigned_team_id: UUID | None = None,
) -> ThreadDetail | None:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return None
    thread.assigned_user_id = assigned_user_id
    thread.assigned_team_id = assigned_team_id
    db.commit()
    db.refresh(thread)
    return ThreadDetail(
        **_serialize_thread_summary(thread).model_dump(),
        participant_ids=thread.participant_ids,
        related_entity_ids=thread.related_entity_ids,
        response_time_seconds=thread.response_time_seconds,
        sentiment=thread.sentiment,
        communications=[],
    )


def set_thread_follow_up(db: Session, thread_id: UUID, follow_up_date: datetime | None) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.follow_up_date = follow_up_date
    db.commit()
    return True


def pin_thread(db: Session, thread_id: UUID, pinned: bool) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.is_pinned = pinned
    db.commit()
    return True


def snooze_thread(db: Session, thread_id: UUID, snoozed_until: datetime) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.snoozed_until = snoozed_until
    thread.status = CrmThreadStatus.SNOOZED.value
    db.commit()
    return True


def archive_thread(db: Session, thread_id: UUID) -> bool:
    thread = get_thread_or_none(db, thread_id)
    if thread is None:
        return False
    thread.archived_at = datetime.now(tz=UTC)
    thread.status = CrmThreadStatus.ARCHIVED.value
    db.commit()
    return True


# Templates
def list_templates(db: Session, user: User, *, page: int = 1, page_size: int = 30, search: str | None = None) -> tuple[list[TemplateSummary], dict]:
    stmt = select(CrmCommunicationTemplate).where(CrmCommunicationTemplate.archived_at.is_(None))
    if search:
        stmt = stmt.where(CrmCommunicationTemplate.name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(CrmCommunicationTemplate.name).offset((page - 1) * page_size).limit(page_size)).all()
    items = [
        TemplateSummary(
            id=r.id,
            name=r.name,
            template_type=r.template_type,
            subject=r.subject,
            channel=r.channel,
            is_shared=r.is_shared,
            is_active=r.is_active,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    pages = math.ceil(total / page_size) if page_size else 0
    return items, {"page": page, "page_size": page_size, "total": total, "pages": pages}


def create_template(db: Session, user: User, payload: TemplateCreate) -> TemplateDetail:
    tpl = CrmCommunicationTemplate(
        name=payload.name,
        template_type=payload.template_type.value,
        subject=payload.subject,
        body=payload.body,
        body_html=payload.body_html,
        variables=payload.variables,
        channel=payload.channel.value if payload.channel else None,
        is_shared=payload.is_shared,
        tags=payload.tags,
        owner_id=user.id,
        created_by=user.id,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return TemplateDetail(
        id=tpl.id,
        name=tpl.name,
        template_type=tpl.template_type,
        subject=tpl.subject,
        channel=tpl.channel,
        is_shared=tpl.is_shared,
        is_active=tpl.is_active,
        tags=tpl.tags,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        body=tpl.body,
        body_html=tpl.body_html,
        variables=tpl.variables,
        owner_id=tpl.owner_id,
        team_id=tpl.team_id,
        created_by=tpl.created_by,
    )


def update_template(db: Session, template_id: UUID, payload: TemplateUpdate) -> TemplateDetail | None:
    tpl = db.scalar(select(CrmCommunicationTemplate).where(CrmCommunicationTemplate.id == template_id))
    if tpl is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, key, value)
    db.commit()
    db.refresh(tpl)
    return TemplateDetail(
        id=tpl.id,
        name=tpl.name,
        template_type=tpl.template_type,
        subject=tpl.subject,
        channel=tpl.channel,
        is_shared=tpl.is_shared,
        is_active=tpl.is_active,
        tags=tpl.tags,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        body=tpl.body,
        body_html=tpl.body_html,
        variables=tpl.variables,
        owner_id=tpl.owner_id,
        team_id=tpl.team_id,
        created_by=tpl.created_by,
    )


def archive_template(db: Session, template_id: UUID) -> bool:
    tpl = db.scalar(select(CrmCommunicationTemplate).where(CrmCommunicationTemplate.id == template_id))
    if tpl is None:
        return False
    tpl.archived_at = datetime.now(tz=UTC)
    tpl.is_active = False
    db.commit()
    return True


# Signatures
def list_signatures(db: Session, user: User) -> list[SignatureSummary]:
    rows = db.scalars(
        select(CrmCommunicationSignature)
        .where(CrmCommunicationSignature.archived_at.is_(None))
        .where(or_(CrmCommunicationSignature.owner_id == user.id, CrmCommunicationSignature.scope != "personal"))
        .order_by(CrmCommunicationSignature.name)
    ).all()
    return [
        SignatureSummary(
            id=r.id,
            name=r.name,
            channel=r.channel,
            scope=r.scope,
            is_default=r.is_default,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


def create_signature(db: Session, user: User, payload: SignatureCreate) -> SignatureDetail:
    sig = CrmCommunicationSignature(
        name=payload.name,
        body_html=payload.body_html,
        body_text=payload.body_text,
        channel=payload.channel.value if payload.channel else None,
        scope=payload.scope,
        is_default=payload.is_default,
        owner_id=user.id,
        created_by=user.id,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return SignatureDetail(
        id=sig.id,
        name=sig.name,
        channel=sig.channel,
        scope=sig.scope,
        is_default=sig.is_default,
        is_active=sig.is_active,
        created_at=sig.created_at,
        updated_at=sig.updated_at,
        body_html=sig.body_html,
        body_text=sig.body_text,
        owner_id=sig.owner_id,
        team_id=sig.team_id,
        department_id=sig.department_id,
    )


def update_signature(db: Session, signature_id: UUID, payload: SignatureUpdate) -> SignatureDetail | None:
    sig = db.scalar(select(CrmCommunicationSignature).where(CrmCommunicationSignature.id == signature_id))
    if sig is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sig, key, value)
    db.commit()
    db.refresh(sig)
    return SignatureDetail(
        id=sig.id,
        name=sig.name,
        channel=sig.channel,
        scope=sig.scope,
        is_default=sig.is_default,
        is_active=sig.is_active,
        created_at=sig.created_at,
        updated_at=sig.updated_at,
        body_html=sig.body_html,
        body_text=sig.body_text,
        owner_id=sig.owner_id,
        team_id=sig.team_id,
        department_id=sig.department_id,
    )


# Sequences
def list_sequences(db: Session, *, page: int = 1, page_size: int = 30) -> tuple[list[SequenceSummary], dict]:
    stmt = select(CrmCommunicationSequence).where(CrmCommunicationSequence.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(CrmCommunicationSequence.steps))
        .order_by(CrmCommunicationSequence.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        SequenceSummary(
            id=r.id,
            name=r.name,
            description=r.description,
            enrollment_type=r.enrollment_type,
            is_active=r.is_active,
            step_count=len(r.steps),
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    pages = math.ceil(total / page_size) if page_size else 0
    return items, {"page": page, "page_size": page_size, "total": total, "pages": pages}


def create_sequence(db: Session, user: User, payload: SequenceCreate) -> SequenceDetail:
    seq = CrmCommunicationSequence(
        name=payload.name,
        description=payload.description,
        enrollment_type=payload.enrollment_type.value,
        tags=payload.tags,
        owner_id=user.id,
        created_by=user.id,
        is_active=False,
    )
    db.add(seq)
    db.flush()
    for step in payload.steps:
        db.add(
            CrmCommunicationSequenceStep(
                sequence_id=seq.id,
                step_order=step.step_order,
                step_type=step.step_type.value,
                template_id=step.template_id,
                wait_days=step.wait_days,
                wait_hours=step.wait_hours,
                condition_json=step.condition_json,
                config_json=step.config_json,
            )
        )
    db.commit()
    db.refresh(seq)
    return _serialize_sequence_detail(seq)


def _serialize_sequence_detail(seq: CrmCommunicationSequence) -> SequenceDetail:
    return SequenceDetail(
        id=seq.id,
        name=seq.name,
        description=seq.description,
        enrollment_type=seq.enrollment_type,
        is_active=seq.is_active,
        step_count=len(seq.steps),
        tags=seq.tags,
        created_at=seq.created_at,
        updated_at=seq.updated_at,
        steps=seq.steps,
        owner_id=seq.owner_id,
        created_by=seq.created_by,
    )


def update_sequence(db: Session, sequence_id: UUID, payload: SequenceUpdate) -> SequenceDetail | None:
    seq = db.scalar(
        select(CrmCommunicationSequence)
        .options(selectinload(CrmCommunicationSequence.steps))
        .where(CrmCommunicationSequence.id == sequence_id)
    )
    if seq is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    steps = data.pop("steps", None)
    for key, value in data.items():
        if key == "enrollment_type" and value is not None:
            setattr(seq, key, value.value if hasattr(value, "value") else value)
        elif value is not None:
            setattr(seq, key, value)
    if steps is not None:
        for existing in list(seq.steps):
            db.delete(existing)
        db.flush()
        for step in steps:
            db.add(
                CrmCommunicationSequenceStep(
                    sequence_id=seq.id,
                    step_order=step["step_order"] if isinstance(step, dict) else step.step_order,
                    step_type=step["step_type"] if isinstance(step, dict) else step.step_type.value,
                    template_id=step.get("template_id") if isinstance(step, dict) else step.template_id,
                    wait_days=step.get("wait_days") if isinstance(step, dict) else step.wait_days,
                    wait_hours=step.get("wait_hours") if isinstance(step, dict) else step.wait_hours,
                    condition_json=step.get("condition_json") if isinstance(step, dict) else step.condition_json,
                    config_json=step.get("config_json") if isinstance(step, dict) else step.config_json,
                )
            )
    db.commit()
    db.refresh(seq)
    return _serialize_sequence_detail(seq)


# Preferences
def get_preferences(db: Session, entity_type: str, entity_id: UUID) -> PreferenceDetail | None:
    pref = db.scalar(
        select(CrmCommunicationPreference).where(
            CrmCommunicationPreference.entity_type == entity_type,
            CrmCommunicationPreference.entity_id == entity_id,
        )
    )
    if pref is None:
        return None
    return PreferenceDetail.model_validate(pref)


def upsert_preferences(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: UUID,
    payload: PreferenceUpsert,
) -> PreferenceDetail:
    pref = db.scalar(
        select(CrmCommunicationPreference).where(
            CrmCommunicationPreference.entity_type == entity_type,
            CrmCommunicationPreference.entity_id == entity_id,
        )
    )
    if pref is None:
        pref = CrmCommunicationPreference(entity_type=entity_type, entity_id=entity_id)
        db.add(pref)
    data = payload.model_dump(exclude_unset=True)
    if "preferred_channel" in data and data["preferred_channel"] is not None:
        data["preferred_channel"] = data["preferred_channel"].value
    for key, value in data.items():
        setattr(pref, key, value)
    pref.updated_by = user.id
    db.commit()
    db.refresh(pref)
    return PreferenceDetail.model_validate(pref)


# Analytics
def get_analytics_dashboard(db: Session, user: User) -> AnalyticsDashboardResponse:
    now = datetime.now(tz=UTC)
    total_comms = db.scalar(select(func.count()).where(CrmCommunication.archived_at.is_(None))) or 0
    draft_count = db.scalar(
        select(func.count()).where(
            CrmCommunication.status == CrmCommunicationStatus.DRAFT.value,
            CrmCommunication.archived_at.is_(None),
        )
    ) or 0
    scheduled_count = db.scalar(
        select(func.count()).where(
            CrmCommunication.status == CrmCommunicationStatus.SCHEDULED.value,
            CrmCommunication.archived_at.is_(None),
        )
    ) or 0
    failed_count = db.scalar(
        select(func.count()).where(
            CrmCommunication.status == CrmCommunicationStatus.FAILED.value,
            CrmCommunication.archived_at.is_(None),
        )
    ) or 0
    follow_up_due = db.scalar(
        select(func.count()).where(
            CrmCommunicationThread.follow_up_date.isnot(None),
            CrmCommunicationThread.follow_up_date <= now,
            CrmCommunicationThread.archived_at.is_(None),
        )
    ) or 0
    providers = get_all_provider_statuses()
    any_connected = any(p["status"] == "available" for p in providers)

    metrics = [
        AnalyticsMetricSchema(key="total_communications", label="Total Communications", value=total_comms),
        AnalyticsMetricSchema(key="drafts", label="Drafts", value=draft_count),
        AnalyticsMetricSchema(key="scheduled", label="Scheduled", value=scheduled_count),
        AnalyticsMetricSchema(key="failed", label="Failed", value=failed_count),
        AnalyticsMetricSchema(key="follow_ups_due", label="Follow-ups Due", value=follow_up_due),
        AnalyticsMetricSchema(
            key="response_rate",
            label="Response Rate",
            value=None,
            unavailable=True,
            unavailable_reason="Email tracking provider not connected",
        ),
        AnalyticsMetricSchema(
            key="open_rate",
            label="Open Rate",
            value=None,
            unavailable=not any_connected,
            unavailable_reason="Provider integration required for tracking metrics",
        ),
        AnalyticsMetricSchema(
            key="avg_response_time",
            label="Avg Response Time",
            value=None,
            unavailable=True,
            unavailable_reason="Insufficient inbound/outbound data",
        ),
    ]
    return AnalyticsDashboardResponse(metrics=metrics)


def get_provider_statuses() -> list[ProviderStatusSchema]:
    return [ProviderStatusSchema(**item) for item in get_all_provider_statuses()]
