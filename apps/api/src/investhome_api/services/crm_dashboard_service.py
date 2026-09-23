"""CRM Pano — live operational dashboard. No demo metrics, no destructive merge."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactDuplicateCandidate, CrmContactStatus
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm import (
    CrmActivitySummary,
    CrmCommunicationSummary,
    CrmDashboardCharts,
    CrmDashboardCount,
    CrmDashboardFeedItem,
    CrmDashboardKpis,
    CrmDashboardPanels,
    CrmDashboardPurchaseScope,
    CrmDashboardResponse,
    CrmMeetingSummary,
    CrmPinnedCompanySummary,
    CrmRelationshipAlert,
    CrmTaskSummary,
)
from investhome_api.services.activity_service import list_activities
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.crm_lead_service import CRM_STAGES, _kpis as lead_kpis, _live_leads, stage_of
from investhome_api.services.crm.crm_match_service import OPEN_STATUSES
from investhome_api.services.crm.document_feed import list_document_feed
from investhome_api.services.crm.report_service import (
    COMM_REPORT_TYPES,
    _channel_expr,
    _source_key_expr,
    _task_section,
)
from investhome_api.services.crm.unit_change import is_historical_unit_change
from investhome_api.services.crm_contact_service import (
    count_active_contacts,
    count_contacts_with_email,
    count_contacts_with_phone,
    count_favorite_contacts,
    fetch_favorite_contacts,
    fetch_pinned_companies,
    fetch_recent_contacts,
    fetch_recently_updated_contacts,
)

CRM_ACTIVITY_ENTITY_TYPES = (
    ActivityEntityType.CRM_CONTACT,
    ActivityEntityType.LEAD,
    ActivityEntityType.INVESTOR,
)

LEAD_STAGE_HREF = {
    "yeni": "/workspaces/crm/leads?stage=yeni",
    "contacted": "/workspaces/crm/leads?stage=contacted",
    "following": "/workspaces/crm/leads?stage=following",
    "qualified": "/workspaces/crm/leads?stage=qualified",
    "converted": "/workspaces/crm/leads?stage=converted",
    "unqualified": "/workspaces/crm/leads?stage=unqualified",
}

TASK_HREF = {
    "active": "/workspaces/crm/tasks?status=active",
    "in_progress": "/workspaces/crm/tasks?status=in_progress",
    "completed": "/workspaces/crm/tasks?status=completed",
    "overdue": "/workspaces/crm/tasks?due=overdue",
}

CHANNEL_HREF = {
    "email": "/workspaces/crm/communication?channel=email",
    "whatsapp": "/workspaces/crm/communication?channel=whatsapp",
    "call": "/workspaces/crm/communication?channel=call",
    "meeting": "/workspaces/crm/communication?channel=meeting",
    "task": "/workspaces/crm/tasks",
    "note": "/workspaces/crm/communication?channel=comment",
}

DOC_STATUS_HREF = {
    "person": "/workspaces/crm/documents?scope=person",
    "purchase": "/workspaces/crm/documents?scope=purchase",
    "hidden": "/workspaces/crm/documents?visibility=hidden",
    "unresolved": "/workspaces/crm/documents?scope=unresolved",
}

MEETING_TYPES = {
    CrmActivityType.MEETING,
    CrmActivityType.ZOOM_MEETING,
    CrmActivityType.TEAMS_MEETING,
    CrmActivityType.SITE_VISIT,
    CrmActivityType.PROPERTY_TOUR,
    CrmActivityType.INVESTOR_MEETING,
    CrmActivityType.CONSTRUCTION_MEETING,
}

CLOSED_TASK = {CrmTaskStatus.COMPLETED, CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED}

PANEL_LIMIT = 8


def _project_label(group: str | None) -> str:
    if not group:
        return "—"
    try:
        return BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup(group)]
    except ValueError:
        return group


def _feed(
    *,
    item_id: object,
    title: str,
    href: str,
    kind: str,
    meta: str | None = None,
    occurred_at: datetime | None = None,
) -> CrmDashboardFeedItem:
    return CrmDashboardFeedItem(
        id=str(item_id),
        title=title,
        meta=meta,
        href=href,
        occurred_at=occurred_at,
        kind=kind,
    )


def _serialize_log_activity(entry) -> CrmActivitySummary:
    return CrmActivitySummary(
        id=entry.id,
        action=entry.action.value,
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        description_key=entry.description_key,
        actor_name=entry.actor_name,
        created_at=entry.created_at,
    )


def _recent_log_activities(db: Session, user: User) -> list[CrmActivitySummary]:
    recent: list[CrmActivitySummary] = []
    for entity_type in CRM_ACTIVITY_ENTITY_TYPES:
        entries, _ = list_activities(db, user, entity_type=entity_type, page=1, page_size=5)
        recent.extend(_serialize_log_activity(entry) for entry in entries)
    recent.sort(key=lambda item: item.created_at, reverse=True)
    return recent[:10]


def _relationship_alerts(db: Session, *, limit: int = 10) -> list[CrmRelationshipAlert]:
    stale_cutoff = datetime.now(tz=UTC) - timedelta(days=90)
    rows = db.scalars(
        select(CrmContact)
        .where(
            CrmContact.archived_at.is_(None),
            CrmContact.status == CrmContactStatus.ACTIVE,
            CrmContact.updated_at < stale_cutoff,
        )
        .order_by(CrmContact.updated_at.asc())
        .limit(limit)
    ).all()
    return [
        CrmRelationshipAlert(
            contact_id=contact.id,
            display_name=contact.display_name,
            alert_type="stale_relationship",
            message_key="crm.alerts.staleRelationship",
            severity="warning",
        )
        for contact in rows
    ]


def _split_agreements(db: Session) -> tuple[list[CrmAgreement], list[CrmAgreement]]:
    rows = list(db.scalars(select(CrmAgreement)).all())
    current = [row for row in rows if not is_historical_unit_change(row)]
    historical = [row for row in rows if is_historical_unit_change(row)]
    return current, historical


def _purchase_charts(current: list[CrmAgreement]) -> tuple[list[CrmDashboardCount], list[CrmDashboardCount]]:
    by_project: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    for row in current:
        group = row.project_group or "unknown"
        by_project[group] += 1
        if row.agreement_date is None:
            by_month["undated"] += 1
        else:
            by_month[row.agreement_date.strftime("%Y-%m")] += 1
    project_rows = [
        CrmDashboardCount(
            key=group,
            label=_project_label(group) if group != "unknown" else "—",
            count=count,
            href=f"/workspaces/crm/agreements?project={group}" if group != "unknown" else "/workspaces/crm/agreements",
        )
        for group, count in sorted(by_project.items(), key=lambda item: (-item[1], item[0]))
    ]
    month_rows = [
        CrmDashboardCount(
            key=key,
            label="Tarihsiz" if key == "undated" else (key[2:] if len(key) >= 7 else key),
            count=count,
            href="/workspaces/crm/agreements",
        )
        for key, count in sorted(by_month.items(), key=lambda item: (item[0] == "undated", item[0]))
    ]
    return project_rows, month_rows


def _investor_count(current: list[CrmAgreement]) -> int:
    return len({row.contact_id for row in current})


def _communication_channels(db: Session) -> list[CrmDashboardCount]:
    source_key = _source_key_expr()
    channel = _channel_expr()
    base = (
        select(
            source_key.label("source_key"),
            channel.label("channel"),
        )
        .where(
            CrmActivity.archived_at.is_(None),
            CrmActivity.activity_type.in_(COMM_REPORT_TYPES),
        )
        .subquery()
    )
    rows = db.execute(
        select(base.c.channel, func.count(distinct(base.c.source_key))).group_by(base.c.channel)
    ).all()
    by_channel = {str(key): int(count or 0) for key, count in rows}
    return [
        CrmDashboardCount(
            key=key,
            label=key,
            count=by_channel.get(key, 0),
            href=CHANNEL_HREF.get(key, "/workspaces/crm/communication"),
        )
        for key in ("email", "whatsapp", "call", "meeting", "task", "note")
    ]


def _matches_pending(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CrmContactDuplicateCandidate)
            .where(CrmContactDuplicateCandidate.status.in_(OPEN_STATUSES))
        )
        or 0
    )


def _lead_pipeline(db: Session) -> tuple[int, list[CrmDashboardCount], list[Lead]]:
    rows = list(db.scalars(_live_leads(db).order_by(Lead.created_at.desc())).all())
    kpis = lead_kpis(rows)
    stage_counts = Counter(stage_of(row) for row in rows)
    pipeline = [
        CrmDashboardCount(
            key=stage,
            label=stage,
            count=int(stage_counts.get(stage, 0)),
            href=LEAD_STAGE_HREF[stage],
        )
        for stage in CRM_STAGES
    ]
    return kpis.active, pipeline, rows[:PANEL_LIMIT]


_QA_NOISE = (
    "os takvim doğrulama",
    "os görev doğrulama",
    "ayşe lead verify",
    "ayse lead verify",
    "canlı crm notlar",
    "kayıt test edildi",
)


def _qa_noise(title: str | None) -> bool:
    text = (title or "").casefold()
    return any(marker in text for marker in _QA_NOISE)


def _crm_activities(db: Session, *, limit: int = PANEL_LIMIT) -> list[CrmActivity]:
    rows = list(
        db.scalars(
            select(CrmActivity)
            .where(CrmActivity.archived_at.is_(None))
            .order_by(CrmActivity.created_at.desc())
            .limit(limit * 4)
        ).all()
    )
    return [row for row in rows if not _qa_noise(row.title)][:limit]


def _upcoming_task_rows(db: Session, *, limit: int = PANEL_LIMIT) -> list[CrmActivity]:
    now = datetime.now(tz=UTC)
    task_match = or_(
        CrmActivity.activity_type == CrmActivityType.TASK,
        CrmActivity.activity_category == CrmActivityCategory.TASK,
    )
    return list(
        db.scalars(
            select(CrmActivity)
            .where(
                task_match,
                CrmActivity.archived_at.is_(None),
                or_(CrmActivity.task_status.is_(None), CrmActivity.task_status.notin_(CLOSED_TASK)),
                CrmActivity.due_date.is_not(None),
                CrmActivity.due_date >= now,
            )
            .order_by(CrmActivity.due_date.asc())
            .limit(limit)
        ).all()
    )


def _todays_meetings(db: Session, *, limit: int = 10) -> list[CrmMeetingSummary]:
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    rows = db.scalars(
        select(CrmActivity)
        .where(
            CrmActivity.archived_at.is_(None),
            CrmActivity.activity_type.in_(MEETING_TYPES),
            CrmActivity.start_date.is_not(None),
            CrmActivity.start_date >= today_start,
            CrmActivity.start_date < today_end,
        )
        .order_by(CrmActivity.start_date.asc())
        .limit(limit)
    ).all()
    return [
        CrmMeetingSummary(
            id=item.id,
            title=item.title,
            start_at=item.start_date,
            status=str(getattr(item.status, "value", item.status) or ""),
        )
        for item in rows
    ]


def _contact_names(db: Session, ids: set[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    return {
        row.id: row.display_name
        for row in db.scalars(select(CrmContact).where(CrmContact.id.in_(ids))).all()
    }


def _activity_href(row: CrmActivity) -> str:
    if row.activity_type == CrmActivityType.TASK or row.activity_category == CrmActivityCategory.TASK:
        return "/workspaces/crm/tasks"
    if row.entity_type.value == "contact":
        return f"/workspaces/crm/contacts/{row.entity_id}"
    return "/workspaces/crm/activities"


def _review_queue(
    db: Session,
    unresolved_docs: list,
    *,
    limit: int = PANEL_LIMIT,
) -> list[CrmDashboardFeedItem]:
    items: list[CrmDashboardFeedItem] = []
    for doc in unresolved_docs[:4]:
        items.append(
            _feed(
                item_id=doc.id,
                title=doc.filename,
                href=f"/workspaces/crm/documents/{doc.id}",
                kind="document",
                meta=doc.contact_name or "Belge inceleme",
                occurred_at=doc.occurred_at,
            )
        )
    match_rows = list(
        db.scalars(
            select(CrmContactDuplicateCandidate)
            .where(CrmContactDuplicateCandidate.status.in_(OPEN_STATUSES))
            .order_by(CrmContactDuplicateCandidate.created_at.desc())
            .limit(4)
        ).all()
    )
    match_ids = {row.contact_id_a for row in match_rows} | {row.contact_id_b for row in match_rows}
    names = _contact_names(db, match_ids)
    for row in match_rows:
        left = names.get(row.contact_id_a, "—")
        right = names.get(row.contact_id_b, "—")
        items.append(
            _feed(
                item_id=row.id,
                title=f"{left} · {right}",
                href=f"/workspaces/crm/matches/{row.id}",
                kind="match",
                meta="Eşleşme bekleyen",
                occurred_at=row.created_at,
            )
        )
    flagged = list(
        db.scalars(
            select(CrmContact)
            .where(
                CrmContact.archived_at.is_(None),
                or_(
                    CrmContact.review_required.is_(True),
                    CrmContact.notes.ilike("%INCELEME_GEREKLI%"),
                ),
            )
            .order_by(CrmContact.updated_at.desc())
            .limit(4)
        ).all()
    )
    for contact in flagged:
        items.append(
            _feed(
                item_id=contact.id,
                title=contact.display_name,
                href=f"/workspaces/crm/contacts/{contact.id}",
                kind="contact",
                meta="INCELEME_GEREKLI",
                occurred_at=contact.updated_at,
            )
        )
    items.sort(key=lambda item: item.occurred_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    return items[:limit]


def build_crm_dashboard(db: Session, user: User) -> CrmDashboardResponse:
    current_agreements, historical_agreements = _split_agreements(db)
    purchases_by_project, purchases_by_month = _purchase_charts(current_agreements)
    investors = _investor_count(current_agreements)
    matches_pending = _matches_pending(db)
    open_leads, lead_pipeline, recent_lead_rows = _lead_pipeline(db)

    tasks = _task_section(db, date_from=None, date_to=None, project_group=None, owner_id=None)
    communication_channels = _communication_channels(db)
    feed = list_document_feed(db, visibility="all", page=1, page_size=20000)
    docs_sorted = sorted(
        feed.items,
        key=lambda item: item.occurred_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    unresolved_docs = [item for item in docs_sorted if item.scope == "unresolved"]

    task_status = [
        CrmDashboardCount(key=row.key, label=row.key, count=row.count, href=TASK_HREF.get(row.key, "/workspaces/crm/tasks"))
        for row in tasks.table
    ]
    document_status = [
        CrmDashboardCount(key="person", label="person", count=feed.stats.person, href=DOC_STATUS_HREF["person"]),
        CrmDashboardCount(key="purchase", label="purchase", count=feed.stats.purchase, href=DOC_STATUS_HREF["purchase"]),
        CrmDashboardCount(key="hidden", label="hidden", count=feed.stats.hidden, href=DOC_STATUS_HREF["hidden"]),
        CrmDashboardCount(
            key="unresolved",
            label="unresolved",
            count=feed.stats.unresolved,
            href=DOC_STATUS_HREF["unresolved"],
        ),
    ]

    crm_activities = _crm_activities(db)
    upcoming = _upcoming_task_rows(db)
    contact_ids = {
        row.entity_id
        for row in [*crm_activities, *upcoming]
        if getattr(row.entity_type, "value", row.entity_type) == "contact"
    }
    names = _contact_names(db, contact_ids)

    activity_panel = [
        item
        for item in (
            _feed(
                item_id=row.id,
                title=row.title,
                href=_activity_href(row),
                kind="activity",
                meta=names.get(row.entity_id) if getattr(row.entity_type, "value", row.entity_type) == "contact" else str(row.activity_type.value),
                occurred_at=row.created_at,
            )
            for row in crm_activities
        )
        if not _qa_noise(item.title) and not _qa_noise(item.meta)
    ]
    task_panel = [
        _feed(
            item_id=row.id,
            title=row.title,
            href="/workspaces/crm/tasks",
            kind="task",
            meta=names.get(row.entity_id) if getattr(row.entity_type, "value", row.entity_type) == "contact" else (row.task_status.value if row.task_status else "aktif"),
            occurred_at=row.due_date,
        )
        for row in upcoming
    ]
    document_panel = [
        _feed(
            item_id=doc.id,
            title=doc.filename,
            href=f"/workspaces/crm/documents/{doc.id}",
            kind="document",
            meta=" · ".join(part for part in [doc.contact_name, doc.project_label or doc.project_group] if part) or "Belge",
            occurred_at=doc.occurred_at,
        )
        for doc in docs_sorted[:PANEL_LIMIT]
    ]
    lead_panel = [
        _feed(
            item_id=lead.id,
            title=lead.full_name,
            href="/workspaces/crm/leads",
            kind="lead",
            meta=" · ".join(part for part in [stage_of(lead), lead.source, lead.interested_project] if part),
            occurred_at=lead.created_at,
        )
        for lead in recent_lead_rows
    ]

    log_activities = _recent_log_activities(db, user)
    pinned = [
        CrmPinnedCompanySummary(
            contact_id=contact.id,
            display_name=contact.display_name,
            organization_name=contact.organization_name,
            contact_type=contact.contact_type,
        )
        for contact in fetch_pinned_companies(db, limit=10)
    ]

    return CrmDashboardResponse(
        recent_contacts=fetch_recent_contacts(db, limit=10),
        recent_activities=log_activities,
        upcoming_tasks=[
            CrmTaskSummary(
                id=item.id,
                title=item.title,
                status=(item.task_status.value if item.task_status else "active"),
                due_at=item.due_date,
                priority=item.priority.value if item.priority else None,
            )
            for item in upcoming
        ],
        todays_meetings=_todays_meetings(db),
        recently_updated=fetch_recently_updated_contacts(db, limit=10),
        relationship_alerts=_relationship_alerts(db),
        favorite_contacts=fetch_favorite_contacts(db, limit=10),
        pinned_companies=pinned,
        communication_summary=CrmCommunicationSummary(
            total_contacts=count_active_contacts(db),
            contacts_with_email=count_contacts_with_email(db),
            contacts_with_phone=count_contacts_with_phone(db),
            favorites_count=count_favorite_contacts(db),
            recent_interactions_count=len(activity_panel) or len(log_activities),
        ),
        kpis=CrmDashboardKpis(
            current_purchases=len(current_agreements),
            investors=investors,
            active_tasks=tasks.active + tasks.in_progress,
            open_leads=open_leads,
            documents_review=feed.stats.unresolved,
            matches_pending=matches_pending,
        ),
        purchase_scope=CrmDashboardPurchaseScope(
            current=len(current_agreements),
            historical=len(historical_agreements),
            total=len(current_agreements) + len(historical_agreements),
        ),
        charts=CrmDashboardCharts(
            purchases_by_project=purchases_by_project,
            purchases_by_month=purchases_by_month,
            task_status=task_status,
            communication_channels=communication_channels,
            lead_pipeline=lead_pipeline,
            document_status=document_status,
        ),
        panels=CrmDashboardPanels(
            recent_activities=activity_panel,
            upcoming_tasks=task_panel,
            recent_documents=document_panel,
            review_queue=_review_queue(db, unresolved_docs),
            recent_leads=lead_panel,
        ),
    )
