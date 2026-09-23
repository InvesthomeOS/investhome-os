"""CRM reporting aggregates from existing tables. No BI, no invented totals."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import String, case, cast, distinct, func, literal, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.models.crm_relationship import CrmRelationship, CrmRelationshipEntityType
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.sales import SalesOpportunity
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_reports import (
    CrmReportAmount,
    CrmReportCount,
    CrmReportMoney,
    CrmReportOption,
    CrmReportsCommunication,
    CrmReportsDocuments,
    CrmReportsFilterOptions,
    CrmReportsInvestorRow,
    CrmReportsInvestors,
    CrmReportsKpis,
    CrmReportsLeadConversion,
    CrmReportsLeadRow,
    CrmReportsLeads,
    CrmReportsSales,
    CrmReportsSalesProjectRow,
    CrmReportsSummary,
    CrmReportsTasks,
    CrmReportsWorkspace,
)
from investhome_api.services.crm.agreement_service import _purchase_amount
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.communication_feed import _contact_ids_for_project
from investhome_api.services.crm.contact_service import list_crm_contacts
from investhome_api.services.crm.document_feed import CATEGORY_LABELS, list_document_feed
from investhome_api.services.crm.unit_change import historical_unit_change_clause, is_historical_unit_change

UNSPECIFIED_CURRENCY = "unspecified"
CLOSED_LEAD_STATUSES = {LeadStatus.WON, LeadStatus.LOST}
COMM_CHANNEL_TYPES: dict[str, tuple[CrmActivityType, ...]] = {
    "email": (CrmActivityType.EMAIL,),
    "whatsapp": (CrmActivityType.WHATSAPP,),
    "call": (CrmActivityType.PHONE_CALL,),
    "meeting": (
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.SITE_VISIT,
        CrmActivityType.PROPERTY_TOUR,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
    ),
    "task": (CrmActivityType.TASK,),
    "note": (CrmActivityType.COMMENT, CrmActivityType.NOTE),
}
COMM_REPORT_TYPES = tuple(item for types in COMM_CHANNEL_TYPES.values() for item in types)
_CURRENCY_ALIASES = {
    "$": "USD",
    "USD": "USD",
    "US DOLLAR": "USD",
    "DOLLAR": "USD",
    "EUR": "EUR",
    "EURO": "EUR",
    "€": "EUR",
    "TRY": "TRY",
    "TL": "TRY",
    "₺": "TRY",
    "GBP": "GBP",
    "£": "GBP",
}


def _enum_key(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _contact_count(db: Session, **kwargs) -> int:
    _, total = list_crm_contacts(db, page=1, page_size=1, **kwargs)
    return int(total)


def _parse_investment_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip().replace("\xa0", " ")
    if not text:
        return None
    for token in ("USD", "EUR", "TRY", "GBP", "TL", "tl", " ", ",", "$", "€", "₺", "£"):
        text = text.replace(token, "")
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _normalize_currency(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip().upper().replace("\xa0", " ")
    if not text:
        return None
    return _CURRENCY_ALIASES.get(text, text)


def _agreement_money(row: CrmAgreement) -> tuple[float | None, str | None]:
    amount_raw, currency_raw = _purchase_amount(row)
    amount = _parse_investment_amount(amount_raw)
    if amount is None:
        return None, None
    currency = _normalize_currency(currency_raw) or UNSPECIFIED_CURRENCY
    return amount, currency


def _add_money(bucket: dict[str, list[float]], currency: str | None, amount: float | None) -> None:
    if amount is None or currency is None:
        return
    bucket.setdefault(currency, []).append(amount)


def _money_list(bucket: dict[str, list[float]]) -> list[CrmReportMoney]:
    rows = [
        CrmReportMoney(currency=currency, total=round(sum(values), 2), populated_count=len(values))
        for currency, values in bucket.items()
        if values
    ]
    rows.sort(key=lambda item: (-item.total, item.currency))
    return rows


def _project_label(group: str | None) -> str:
    if not group:
        return "—"
    try:
        return BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup(group)]
    except ValueError:
        return group


def _as_date(value: datetime | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _grouped_counts(rows: list[tuple[object, int]]) -> list[CrmReportCount]:
    return [CrmReportCount(key=_enum_key(key) or "unknown", count=int(count or 0)) for key, count in rows]


def _source_key_expr():
    history = CrmActivity.metadata_json["bitrix_history"]
    record_id = func.coalesce(
        func.nullif(history["bitrix_record_id"].as_string(), ""),
        func.nullif(history["message_id"].as_string(), ""),
    )
    kind = func.lower(
        func.coalesce(
            func.nullif(history["kind"].as_string(), ""),
            cast(CrmActivity.activity_type, String),
        )
    )
    return case(
        (record_id.is_not(None), func.concat(kind, literal(":"), record_id)),
        else_=func.concat(literal("activity:"), cast(CrmActivity.id, String)),
    )


def _channel_expr():
    return case(
        (CrmActivity.activity_type == CrmActivityType.EMAIL, "email"),
        (CrmActivity.activity_type == CrmActivityType.WHATSAPP, "whatsapp"),
        (CrmActivity.activity_type == CrmActivityType.PHONE_CALL, "call"),
        (
            CrmActivity.activity_type.in_(COMM_CHANNEL_TYPES["meeting"]),
            "meeting",
        ),
        (CrmActivity.activity_type == CrmActivityType.TASK, "task"),
        (
            CrmActivity.activity_type.in_(COMM_CHANNEL_TYPES["note"]),
            "note",
        ),
        else_="other",
    )


def _user_names(db: Session, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    return {
        row.id: row.full_name or row.email
        for row in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }


def build_crm_reports_summary(db: Session) -> CrmReportsSummary:
    contacts_total = db.scalar(select(func.count()).select_from(CrmContact)) or 0
    contacts_active = _contact_count(db, status=CrmContactStatus.ACTIVE)
    contacts_junk = _contact_count(db, bitrix_list="current_junk")
    contacts_agents = _contact_count(db, role_group="agent")
    contacts_agreement = _contact_count(db, category="agreement")

    pipeline_total = db.scalar(
        select(func.count(func.distinct(SalesOpportunity.crm_contact_id))).where(
            SalesOpportunity.crm_contact_id.is_not(None)
        )
    ) or 0
    pipeline_by_stage = _grouped_counts(
        db.execute(
            select(SalesOpportunity.stage, func.count(func.distinct(SalesOpportunity.crm_contact_id)))
            .where(SalesOpportunity.crm_contact_id.is_not(None))
            .group_by(SalesOpportunity.stage)
        ).all()
    )

    activities_total = db.scalar(select(func.count()).select_from(CrmActivity)) or 0
    activities_by_type = _grouped_counts(
        db.execute(select(CrmActivity.activity_type, func.count()).group_by(CrmActivity.activity_type)).all()
    )

    task_match = or_(
        CrmActivity.activity_type == CrmActivityType.TASK,
        CrmActivity.activity_category == CrmActivityCategory.TASK,
    )
    completed_task = CrmActivity.task_status == CrmTaskStatus.COMPLETED
    cancelled_task = CrmActivity.task_status.in_([CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED])
    tasks_pending = db.scalar(
        select(func.count()).select_from(CrmActivity).where(task_match, ~completed_task, ~cancelled_task)
    ) or 0
    tasks_completed = db.scalar(
        select(func.count()).select_from(CrmActivity).where(task_match, completed_task)
    ) or 0
    now = datetime.now(tz=UTC)
    tasks_overdue = db.scalar(
        select(func.count())
        .select_from(CrmActivity)
        .where(
            task_match,
            ~completed_task,
            ~cancelled_task,
            CrmActivity.due_date.is_not(None),
            CrmActivity.due_date < now,
        )
    ) or 0

    agreements_total = db.scalar(
        select(func.count())
        .select_from(CrmAgreement)
        .where(~historical_unit_change_clause())
    ) or 0
    agreements_by_project = _grouped_counts(
        db.execute(
            select(CrmAgreement.project_group, func.count())
            .where(~historical_unit_change_clause())
            .group_by(CrmAgreement.project_group)
        ).all()
    )

    reit_rows = db.scalars(
        select(CrmAgreement).where(
            func.lower(CrmAgreement.project_group) == "reit",
            ~historical_unit_change_clause(),
        )
    ).all()
    parsed_amounts = [amount for amount, _currency in (_agreement_money(row) for row in reit_rows) if amount is not None]
    reit_total = CrmReportAmount(
        populated_count=len(parsed_amounts),
        total=round(sum(parsed_amounts), 2) if parsed_amounts else None,
    )

    companies_total = db.scalar(select(func.count()).select_from(CrmCompany)) or 0
    company_contact_links = db.scalar(select(func.count()).select_from(CrmCompanyContact)) or 0

    relationships_total = db.scalar(select(func.count()).select_from(CrmRelationship)) or 0
    relationships_contact_company = db.scalar(
        select(func.count())
        .select_from(CrmRelationship)
        .where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.COMPANY,
        )
    ) or 0
    relationships_investor_project = db.scalar(
        select(func.count())
        .select_from(CrmRelationship)
        .where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.PROJECT,
            CrmRelationship.relationship_type == "investor",
        )
    ) or 0

    return CrmReportsSummary(
        contacts_total=int(contacts_total),
        contacts_active=int(contacts_active),
        contacts_junk=int(contacts_junk),
        contacts_agents=int(contacts_agents),
        contacts_agreement=int(contacts_agreement),
        pipeline_total=int(pipeline_total),
        pipeline_by_stage=pipeline_by_stage,
        activities_total=int(activities_total),
        activities_by_type=activities_by_type,
        tasks_pending=int(tasks_pending),
        tasks_completed=int(tasks_completed),
        tasks_overdue=int(tasks_overdue),
        agreements_total=int(agreements_total),
        agreements_by_project_group=agreements_by_project,
        reit_investment=reit_total,
        companies_total=int(companies_total),
        company_contact_links=int(company_contact_links),
        relationships_total=int(relationships_total),
        relationships_contact_company=int(relationships_contact_company),
        relationships_investor_project=int(relationships_investor_project),
    )


def _filter_agreements(
    rows: list[CrmAgreement],
    contacts: dict[UUID, CrmContact],
    *,
    date_from: date | None,
    date_to: date | None,
    project_group: str | None,
    owner_id: UUID | None,
    source: str | None,
    currency: str | None,
    current_only: bool | None,
) -> list[CrmAgreement]:
    source_key = (source or "").strip().lower()
    currency_key = _normalize_currency(currency) if currency else None
    filtered: list[CrmAgreement] = []
    for row in rows:
        historical = is_historical_unit_change(row)
        if current_only is True and historical:
            continue
        if current_only is False and not historical:
            continue
        if project_group and row.project_group != project_group:
            continue
        if date_from or date_to:
            if row.agreement_date is None:
                continue
            if date_from and row.agreement_date < date_from:
                continue
            if date_to and row.agreement_date > date_to:
                continue
        contact = contacts.get(row.contact_id)
        if owner_id and (contact is None or contact.owner_user_id != owner_id):
            continue
        if source_key:
            contact_source = (contact.source or "").strip().lower() if contact else ""
            if contact_source != source_key:
                continue
        if currency_key:
            amount, row_currency = _agreement_money(row)
            if amount is None or row_currency != currency_key:
                continue
        filtered.append(row)
    return filtered


def _sales_section(
    current_rows: list[CrmAgreement],
    historical_rows: list[CrmAgreement],
) -> CrmReportsSales:
    totals: dict[str, list[float]] = {}
    by_project: dict[str, dict[str, object]] = {}

    def _bucket(group: str) -> dict[str, object]:
        item = by_project.get(group)
        if item is None:
            item = {
                "current": 0,
                "historical": 0,
                "amounts": {},
            }
            by_project[group] = item
        return item

    for row in current_rows:
        bucket = _bucket(row.project_group)
        bucket["current"] = int(bucket["current"]) + 1
        amount, currency = _agreement_money(row)
        _add_money(bucket["amounts"], currency, amount)  # type: ignore[arg-type]
        _add_money(totals, currency, amount)

    for row in historical_rows:
        bucket = _bucket(row.project_group)
        bucket["historical"] = int(bucket["historical"]) + 1

    month_counts: Counter[str] = Counter()
    for row in current_rows:
        if row.agreement_date is None:
            month_counts["undated"] += 1
        else:
            month_counts[row.agreement_date.strftime("%Y-%m")] += 1

    project_rows = [
        CrmReportsSalesProjectRow(
            key=group,
            label=_project_label(group),
            current_count=int(values["current"]),
            historical_count=int(values["historical"]),
            amounts=_money_list(values["amounts"]),  # type: ignore[arg-type]
            href=f"/workspaces/crm/agreements?project={group}",
        )
        for group, values in sorted(by_project.items(), key=lambda item: (-int(item[1]["current"]), item[0]))
    ]
    month_rows = [
        CrmReportCount(key=key, label=key, count=count)
        for key, count in sorted(month_counts.items(), key=lambda item: item[0])
    ]
    return CrmReportsSales(
        current_count=len(current_rows),
        historical_count=len(historical_rows),
        by_project=project_rows,
        by_month=month_rows,
        table=project_rows,
    )


def _investor_section(current_rows: list[CrmAgreement], contacts: dict[UUID, CrmContact]) -> CrmReportsInvestors:
    by_contact: dict[UUID, list[CrmAgreement]] = defaultdict(list)
    for row in current_rows:
        by_contact[row.contact_id].append(row)
    purchase_distribution: Counter[str] = Counter()
    project_counts: Counter[str] = Counter()
    table: list[CrmReportsInvestorRow] = []
    for contact_id, rows in by_contact.items():
        purchase_distribution[str(len(rows))] += 1
        projects = sorted({row.project_group for row in rows})
        for group in projects:
            project_counts[group] += 1
        amounts: dict[str, list[float]] = {}
        for row in rows:
            amount, currency = _agreement_money(row)
            _add_money(amounts, currency, amount)
        contact = contacts.get(contact_id)
        table.append(
            CrmReportsInvestorRow(
                contact_id=str(contact_id),
                name=(contact.display_name if contact else None) or "—",
                purchases=len(rows),
                projects=[_project_label(group) for group in projects],
                amounts=_money_list(amounts),
                href=f"/workspaces/crm/contacts/{contact_id}",
            )
        )
    table.sort(key=lambda item: (-item.purchases, item.name.casefold()))
    return CrmReportsInvestors(
        count=len(by_contact),
        purchases_per_investor=[
            CrmReportCount(key=key, label=key, count=count)
            for key, count in sorted(purchase_distribution.items(), key=lambda item: int(item[0]))
        ],
        by_project=[
            CrmReportCount(
                key=group,
                label=_project_label(group),
                count=count,
                href=f"/workspaces/crm/agreements?project={group}",
            )
            for group, count in sorted(project_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        table=table,
    )


def _lead_section(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    project_group: str | None,
    owner_id: UUID | None,
    source: str | None,
) -> CrmReportsLeads:
    query = select(Lead).where(Lead.is_demo.is_(False), Lead.archived_at.is_(None))
    if date_from is not None:
        query = query.where(Lead.created_at >= date_from)
    if date_to is not None:
        query = query.where(Lead.created_at <= date_to)
    if project_group:
        query = query.where(func.lower(func.coalesce(Lead.interested_project, "")) == project_group.lower())
    if owner_id is not None:
        query = query.where(Lead.assigned_manager_id == owner_id)
    if source:
        query = query.where(func.lower(func.coalesce(Lead.source, "")) == source.strip().lower())
    rows = list(db.scalars(query.order_by(Lead.created_at.desc())).all())
    owner_ids = {row.assigned_manager_id for row in rows if row.assigned_manager_id}
    owners = _user_names(db, owner_ids)
    by_source: Counter[str] = Counter()
    by_stage: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    by_project: Counter[str] = Counter()
    conversion: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    open_count = 0
    table: list[CrmReportsLeadRow] = []
    for row in rows:
        source_key = (row.source or "").strip() or "unknown"
        stage_key = _enum_key(row.status) or "unknown"
        owner_key = str(row.assigned_manager_id) if row.assigned_manager_id else "unassigned"
        project_key = (row.interested_project or "").strip() or "unknown"
        by_source[source_key] += 1
        by_stage[stage_key] += 1
        by_owner[owner_key] += 1
        by_project[project_key] += 1
        status = row.status if isinstance(row.status, LeadStatus) else LeadStatus(str(row.status))
        if status not in CLOSED_LEAD_STATUSES:
            open_count += 1
        if status == LeadStatus.WON:
            conversion[source_key][0] += 1
        elif status == LeadStatus.LOST:
            conversion[source_key][1] += 1
        table.append(
            CrmReportsLeadRow(
                id=str(row.id),
                name=row.full_name,
                source=row.source,
                stage=str(getattr(row.status, "value", row.status)),
                owner=owners.get(row.assigned_manager_id) if row.assigned_manager_id else None,
                project=row.interested_project,
                href=f"/workspaces/crm/leads",
            )
        )
    conversion_rows = []
    for key, (won, lost) in sorted(conversion.items()):
        closed = won + lost
        conversion_rows.append(
            CrmReportsLeadConversion(
                key=key,
                label=key,
                won=won,
                lost=lost,
                rate=round(won / closed, 4) if closed else None,
            )
        )
    return CrmReportsLeads(
        total=len(rows),
        open_count=open_count,
        by_source=[CrmReportCount(key=key, label=key, count=count) for key, count in by_source.most_common()],
        by_stage=[CrmReportCount(key=key, label=key, count=count) for key, count in by_stage.most_common()],
        by_owner=[
            CrmReportCount(
                key=key,
                label=owners.get(UUID(key), "—") if key != "unassigned" else "—",
                count=count,
            )
            for key, count in by_owner.most_common()
        ],
        by_project=[
            CrmReportCount(key=key, label=_project_label(key) if key != "unknown" else "—", count=count)
            for key, count in by_project.most_common()
        ],
        conversion=conversion_rows,
        table=table[:100],
    )


def _activity_channel(activity: CrmActivity) -> str:
    value = activity.activity_type
    for channel, types in COMM_CHANNEL_TYPES.items():
        if value in types:
            return channel
    return "other"


def _communication_section_python(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    project_group: str | None,
    owner_id: UUID | None,
) -> CrmReportsCommunication:
    from investhome_api.services.crm.contact_service import _activity_source_key

    query = select(CrmActivity).where(
        CrmActivity.archived_at.is_(None),
        CrmActivity.activity_type.in_(COMM_REPORT_TYPES),
    )
    if date_from is not None:
        query = query.where(func.coalesce(CrmActivity.start_date, CrmActivity.created_at) >= date_from)
    if date_to is not None:
        query = query.where(func.coalesce(CrmActivity.start_date, CrmActivity.created_at) <= date_to)
    if owner_id is not None:
        query = query.where(or_(CrmActivity.assigned_user_id == owner_id, CrmActivity.owner_id == owner_id))
    if project_group:
        contact_ids = _contact_ids_for_project(db, project_group)
        query = query.where(
            CrmActivity.entity_id.in_(contact_ids or [UUID("00000000-0000-0000-0000-000000000000")])
        )
    seen: set[str] = set()
    by_channel: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    owner_ids: set[UUID] = set()
    for row in db.scalars(query).all():
        key = _activity_source_key(row)
        if key in seen:
            continue
        seen.add(key)
        channel = _activity_channel(row)
        by_channel[channel] += 1
        occurred = row.start_date or row.created_at
        if occurred is not None:
            by_month[occurred.strftime("%Y-%m")] += 1
        owner = row.assigned_user_id or row.owner_id
        owner_key = str(owner) if owner else "unassigned"
        by_owner[owner_key] += 1
        if owner:
            owner_ids.add(owner)
    owners = _user_names(db, owner_ids)
    channel_table = [
        CrmReportCount(
            key=key,
            label=key,
            count=by_channel.get(key, 0),
            href=(
                "/workspaces/crm/tasks"
                if key == "task"
                else f"/workspaces/crm/communication?channel={'comment' if key == 'note' else key}"
            ),
        )
        for key in ("email", "whatsapp", "call", "meeting", "task", "note")
    ]
    return CrmReportsCommunication(
        total=len(seen),
        email=by_channel.get("email", 0),
        whatsapp=by_channel.get("whatsapp", 0),
        calls=by_channel.get("call", 0),
        meetings=by_channel.get("meeting", 0),
        tasks=by_channel.get("task", 0),
        notes=by_channel.get("note", 0),
        by_channel=channel_table,
        by_month=[CrmReportCount(key=key, label=key, count=count) for key, count in sorted(by_month.items())],
        by_owner=[
            CrmReportCount(
                key=key,
                label=owners.get(UUID(key), "—") if key != "unassigned" else "—",
                count=count,
                href="/workspaces/crm/communication",
            )
            for key, count in by_owner.most_common(20)
        ],
        table=channel_table,
    )


def _communication_section(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    project_group: str | None,
    owner_id: UUID | None,
) -> CrmReportsCommunication:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        return _communication_section_python(
            db,
            date_from=date_from,
            date_to=date_to,
            project_group=project_group,
            owner_id=owner_id,
        )
    source_key = _source_key_expr()
    channel = _channel_expr()
    occurred = func.coalesce(CrmActivity.start_date, CrmActivity.created_at)
    owner = func.coalesce(CrmActivity.assigned_user_id, CrmActivity.owner_id)
    query = select(
        source_key.label("source_key"),
        channel.label("channel"),
        occurred.label("occurred"),
        owner.label("owner_id"),
    ).where(
        CrmActivity.archived_at.is_(None),
        CrmActivity.activity_type.in_(COMM_REPORT_TYPES),
    )
    if date_from is not None:
        query = query.where(occurred >= date_from)
    if date_to is not None:
        query = query.where(occurred <= date_to)
    if owner_id is not None:
        query = query.where(or_(CrmActivity.assigned_user_id == owner_id, CrmActivity.owner_id == owner_id))
    if project_group:
        contact_ids = _contact_ids_for_project(db, project_group)
        query = query.where(
            CrmActivity.entity_id.in_(contact_ids or [UUID("00000000-0000-0000-0000-000000000000")])
        )
    base = query.subquery()
    by_channel_rows = db.execute(
        select(base.c.channel, func.count(distinct(base.c.source_key))).group_by(base.c.channel)
    ).all()
    by_channel = {str(key): int(count or 0) for key, count in by_channel_rows}
    total = int(sum(by_channel.values()))
    month_expr = func.to_char(func.date_trunc("month", base.c.occurred), "YYYY-MM")
    month_rows = db.execute(
        select(month_expr, func.count(distinct(base.c.source_key)))
        .where(base.c.occurred.is_not(None))
        .group_by(month_expr)
        .order_by(month_expr)
    ).all()
    owner_rows = db.execute(
        select(base.c.owner_id, func.count(distinct(base.c.source_key)))
        .group_by(base.c.owner_id)
        .order_by(func.count(distinct(base.c.source_key)).desc())
        .limit(20)
    ).all()
    owner_ids = {row[0] for row in owner_rows if row[0]}
    owners = _user_names(db, owner_ids)
    channel_table = [
        CrmReportCount(
            key=key,
            label=key,
            count=by_channel.get(key, 0),
                href=(
                    "/workspaces/crm/tasks"
                    if key == "task"
                    else f"/workspaces/crm/communication?channel={'comment' if key == 'note' else key}"
                ),
        )
        for key in ("email", "whatsapp", "call", "meeting", "task", "note")
    ]
    return CrmReportsCommunication(
        total=total,
        email=by_channel.get("email", 0),
        whatsapp=by_channel.get("whatsapp", 0),
        calls=by_channel.get("call", 0),
        meetings=by_channel.get("meeting", 0),
        tasks=by_channel.get("task", 0),
        notes=by_channel.get("note", 0),
        by_channel=channel_table,
        by_month=[CrmReportCount(key=str(key), label=str(key), count=int(count or 0)) for key, count in month_rows],
        by_owner=[
            CrmReportCount(
                key=str(user_id) if user_id else "unassigned",
                label=owners.get(user_id, "—") if user_id else "—",
                count=int(count or 0),
                href="/workspaces/crm/communication",
            )
            for user_id, count in owner_rows
        ],
        table=channel_table,
    )


def _task_section(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    project_group: str | None,
    owner_id: UUID | None,
) -> CrmReportsTasks:
    task_match = or_(
        CrmActivity.activity_type == CrmActivityType.TASK,
        CrmActivity.activity_category == CrmActivityCategory.TASK,
    )
    occurred = func.coalesce(CrmActivity.due_date, CrmActivity.created_at)
    filters = [task_match, CrmActivity.archived_at.is_(None)]
    if date_from is not None:
        filters.append(occurred >= date_from)
    if date_to is not None:
        filters.append(occurred <= date_to)
    if owner_id is not None:
        filters.append(or_(CrmActivity.assigned_user_id == owner_id, CrmActivity.owner_id == owner_id))
    if project_group:
        contact_ids = _contact_ids_for_project(db, project_group)
        filters.append(
            CrmActivity.entity_id.in_(contact_ids or [UUID("00000000-0000-0000-0000-000000000000")])
        )
    status_rows = {
        _enum_key(status): int(count or 0)
        for status, count in db.execute(
            select(CrmActivity.task_status, func.count()).where(*filters).group_by(CrmActivity.task_status)
        ).all()
    }
    completed = status_rows.get(CrmTaskStatus.COMPLETED.value, 0)
    in_progress = status_rows.get(CrmTaskStatus.IN_PROGRESS.value, 0) + status_rows.get(CrmTaskStatus.WAITING.value, 0)
    cancelled = status_rows.get(CrmTaskStatus.CANCELLED.value, 0) + status_rows.get(CrmTaskStatus.DEFERRED.value, 0)
    total = int(sum(status_rows.values()))
    active = max(total - completed - cancelled - in_progress, 0)
    now = datetime.now(tz=UTC)
    overdue = int(
        db.scalar(
            select(func.count())
            .select_from(CrmActivity)
            .where(
                *filters,
                CrmActivity.task_status.notin_([CrmTaskStatus.COMPLETED, CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED]),
                CrmActivity.due_date.is_not(None),
                CrmActivity.due_date < now,
            )
        )
        or 0
    )
    owner_col = func.coalesce(CrmActivity.assigned_user_id, CrmActivity.owner_id)
    owner_rows = db.execute(
        select(owner_col, func.count())
        .where(*filters)
        .group_by(owner_col)
        .order_by(func.count().desc())
        .limit(20)
    ).all()
    owner_ids = {row[0] for row in owner_rows if row[0]}
    owners = _user_names(db, owner_ids)
    table = [
        CrmReportCount(key="active", label="active", count=active, href="/workspaces/crm/tasks?status=active"),
        CrmReportCount(key="in_progress", label="in_progress", count=in_progress, href="/workspaces/crm/tasks?status=in_progress"),
        CrmReportCount(key="completed", label="completed", count=completed, href="/workspaces/crm/tasks?status=completed"),
        CrmReportCount(key="overdue", label="overdue", count=overdue, href="/workspaces/crm/tasks?due=overdue"),
    ]
    return CrmReportsTasks(
        active=active,
        in_progress=in_progress,
        completed=completed,
        overdue=overdue,
        by_owner=[
            CrmReportCount(
                key=str(user_id) if user_id else "unassigned",
                label=owners.get(user_id, "—") if user_id else "—",
                count=int(count or 0),
                href="/workspaces/crm/tasks",
            )
            for user_id, count in owner_rows
        ],
        table=table,
    )


def _document_section(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    project_group: str | None,
    source: str | None,
) -> CrmReportsDocuments:
    feed = list_document_feed(
        db,
        project_group=project_group,
        source=source,
        visibility="all",
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=20000,
    )
    items = feed.items
    by_category: Counter[str] = Counter()
    by_project: Counter[str] = Counter()
    for item in items:
        by_category[item.category or "other"] += 1
        by_project[item.project_group or "unknown"] += 1
    return CrmReportsDocuments(
        total=len(items),
        person=sum(1 for item in items if item.scope == "person"),
        purchase=sum(1 for item in items if item.scope == "purchase"),
        hidden=sum(1 for item in items if item.hidden),
        review_required=sum(1 for item in items if item.scope == "unresolved"),
        by_category=[
            CrmReportCount(
                key=key,
                label=CATEGORY_LABELS.get(key, key),
                count=count,
                href="/workspaces/crm/documents",
            )
            for key, count in by_category.most_common()
        ],
        by_project=[
            CrmReportCount(
                key=key,
                label=_project_label(key) if key != "unknown" else "—",
                count=count,
                href=f"/workspaces/crm/documents?project={key}" if key != "unknown" else "/workspaces/crm/documents",
            )
            for key, count in by_project.most_common()
        ],
        table=[
            CrmReportCount(key="total", label="total", count=len(items), href="/workspaces/crm/documents"),
            CrmReportCount(key="person", label="person", count=sum(1 for item in items if item.scope == "person"), href="/workspaces/crm/documents?scope=person"),
            CrmReportCount(key="purchase", label="purchase", count=sum(1 for item in items if item.scope == "purchase"), href="/workspaces/crm/documents?scope=purchase"),
            CrmReportCount(key="hidden", label="hidden", count=sum(1 for item in items if item.hidden), href="/workspaces/crm/documents?visibility=hidden"),
            CrmReportCount(key="review", label="review", count=sum(1 for item in items if item.scope == "unresolved"), href="/workspaces/crm/documents?scope=unresolved"),
        ],
    )


def _filter_options(db: Session, agreements: list[CrmAgreement], contacts: dict[UUID, CrmContact]) -> CrmReportsFilterOptions:
    projects = sorted({row.project_group for row in agreements})
    sources = sorted(
        {
            (contact.source or "").strip().lower()
            for contact in contacts.values()
            if (contact.source or "").strip()
        }
        | {
            (source or "").strip().lower()
            for source in db.scalars(select(Lead.source).where(Lead.is_demo.is_(False), Lead.source.is_not(None))).all()
            if source
        }
    )
    currencies: set[str] = set()
    for row in agreements:
        if is_historical_unit_change(row):
            continue
        amount, currency = _agreement_money(row)
        if amount is not None and currency:
            currencies.add(currency)
    return CrmReportsFilterOptions(
        projects=[CrmReportOption(key=group, label=_project_label(group)) for group in projects],
        sources=[CrmReportOption(key=item, label=item) for item in sources],
        currencies=[CrmReportOption(key=item, label=item.upper() if item != UNSPECIFIED_CURRENCY else item) for item in sorted(currencies)],
    )


def build_crm_reports_workspace(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    project_group: str | None = None,
    owner_id: UUID | None = None,
    source: str | None = None,
    currency: str | None = None,
) -> CrmReportsWorkspace:
    agreements = list(db.scalars(select(CrmAgreement)).all())
    contact_ids = {row.contact_id for row in agreements}
    contacts = {
        row.id: row for row in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
    } if contact_ids else {}
    start = _as_date(date_from)
    end = _as_date(date_to)
    current_rows = _filter_agreements(
        agreements,
        contacts,
        date_from=start,
        date_to=end,
        project_group=project_group,
        owner_id=owner_id,
        source=source,
        currency=currency,
        current_only=True,
    )
    historical_rows = _filter_agreements(
        agreements,
        contacts,
        date_from=start,
        date_to=end,
        project_group=project_group,
        owner_id=owner_id,
        source=source,
        currency=None,
        current_only=False,
    )
    sales = _sales_section(current_rows, historical_rows)
    investors = _investor_section(current_rows, contacts)
    leads = _lead_section(
        db,
        date_from=date_from,
        date_to=date_to,
        project_group=project_group,
        owner_id=owner_id,
        source=source,
    )
    communication = _communication_section(
        db,
        date_from=date_from,
        date_to=date_to,
        project_group=project_group,
        owner_id=owner_id,
    )
    tasks = _task_section(
        db,
        date_from=date_from,
        date_to=date_to,
        project_group=project_group,
        owner_id=owner_id,
    )
    documents = _document_section(
        db,
        date_from=date_from,
        date_to=date_to,
        project_group=project_group,
        source=None,
    )
    sales_totals: dict[str, list[float]] = {}
    for row in current_rows:
        amount, row_currency = _agreement_money(row)
        _add_money(sales_totals, row_currency, amount)
    return CrmReportsWorkspace(
        kpis=CrmReportsKpis(
            current_purchases=len(current_rows),
            investors=investors.count,
            sales_totals=_money_list(sales_totals),
            active_tasks=tasks.active + tasks.in_progress,
            open_leads=leads.open_count,
            documents_review=documents.review_required,
        ),
        sales=sales,
        investors=investors,
        leads=leads,
        communication=communication,
        tasks=tasks,
        documents=documents,
        filter_options=_filter_options(db, agreements, contacts),
    )
