"""Centralized universal search service with entity providers."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.search_config import (
    DEFAULT_PER_ENTITY_LIMIT,
    DEFAULT_TOTAL_LIMIT,
    ENTITY_LINK_MODULES,
    ENTITY_PERMISSION_RESOURCE,
    FINANCE_TAB_BY_ENTITY,
    SEARCH_ENTITY_TYPES,
)
from investhome_api.models.activity import ActivityLog
from investhome_api.models.finance import (
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    PaymentObligation,
)
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.notification import Notification, NotificationStatus
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.search import SearchGroup, SearchHighlight, SearchResponse, SearchResultItem
from investhome_api.services.activity_service import (
    resolve_entity_label,
    user_can_view_activity_entry,
)
from investhome_api.services.notification_service import user_can_view_notification
from investhome_api.services.permission_service import is_super_admin, user_has_permission


@dataclass
class SearchFilters:
    entity_types: set[str] | None = None
    status: str | None = None
    assigned_to: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass
class InternalSearchResult:
    entity_type: str
    entity_id: UUID
    title: str
    subtitle: str | None = None
    preview: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    created_at: datetime | None = None
    score: float = 0.0
    matched_fields: dict[str, str] = field(default_factory=dict)


def _normalize_query(query: str) -> str:
    return query.strip()


def _pattern(query: str) -> str:
    return f"%{_normalize_query(query)}%"


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _score_match(query: str, *values: str | None) -> float:
    needle = _normalize_query(query).lower()
    if not needle:
        return 0.0
    best = 0.0
    for raw in values:
        if not raw:
            continue
        hay = str(raw).lower()
        if hay == needle:
            best = max(best, 100.0)
        elif hay.startswith(needle):
            best = max(best, 85.0)
        elif needle in hay:
            best = max(best, 65.0)
        else:
            tokens = re.split(r"\s+", needle)
            if all(token in hay for token in tokens if token):
                best = max(best, 55.0)
    return best


def _build_snippet(query: str, text: str, *, max_len: int = 120) -> str:
    needle = _normalize_query(query)
    if not text:
        return ""
    lower = text.lower()
    idx = lower.find(needle.lower())
    if idx < 0:
        return text[:max_len] + ("…" if len(text) > max_len else "")
    start = max(0, idx - 24)
    end = min(len(text), idx + len(needle) + 48)
    snippet = text[start:end]
    if start > 0:
        snippet = f"…{snippet}"
    if end < len(text):
        snippet = f"{snippet}…"
    return snippet


def _highlights(query: str, matched_fields: dict[str, str]) -> list[SearchHighlight]:
    items: list[SearchHighlight] = []
    for field_name, value in matched_fields.items():
        if not value:
            continue
        items.append(
            SearchHighlight(field=field_name, snippet=_build_snippet(query, value))
        )
    return items


def _link_query(entity_type: str, entity_id: UUID) -> dict[str, str]:
    query: dict[str, str] = {"id": str(entity_id)}
    if entity_type in FINANCE_TAB_BY_ENTITY:
        query["tab"] = FINANCE_TAB_BY_ENTITY[entity_type]
    if entity_type == "notification":
        return {"openNotifications": "1"}
    if entity_type == "activity":
        return {"activityId": str(entity_id)}
    return query


def _to_item(query: str, result: InternalSearchResult) -> SearchResultItem:
    module = ENTITY_LINK_MODULES[result.entity_type]
    return SearchResultItem(
        entity_type=result.entity_type,
        entity_id=result.entity_id,
        title=result.title,
        subtitle=result.subtitle,
        preview=result.preview,
        module=module,
        link_query=_link_query(result.entity_type, result.entity_id),
        status=result.status,
        assigned_to=result.assigned_to,
        created_at=result.created_at,
        score=result.score,
        highlights=_highlights(query, result.matched_fields),
    )


def _apply_date_filter(created_at: datetime | None, filters: SearchFilters) -> bool:
    if created_at is None:
        return filters.date_from is None and filters.date_to is None
    if filters.date_from is not None and created_at < filters.date_from:
        return False
    if filters.date_to is not None and created_at > filters.date_to:
        return False
    return True


def _user_can_search_entity(user: User, entity_type: str) -> bool:
    from investhome_api.config.settings import get_settings

    if entity_type not in SEARCH_ENTITY_TYPES:
        return False
    if not get_settings().auth_enabled:
        return True
    if is_super_admin(user):
        return True
    resource = ENTITY_PERMISSION_RESOURCE.get(entity_type)
    if resource is None:
        return False
    return user_has_permission(user, resource, "view")


def _collect_matched_fields(query: str, field_map: dict[str, str | None]) -> dict[str, str]:
    matched: dict[str, str] = {}
    needle = _normalize_query(query).lower()
    for name, value in field_map.items():
        if value and needle in str(value).lower():
            matched[name] = str(value)
    return matched


def _search_leads(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "lead"):
        return []
    pattern = _pattern(query)
    stmt = select(Lead).where(Lead.archived_at.is_(None))
    if filters.status:
        stmt = stmt.where(Lead.status == filters.status)
    if filters.assigned_to:
        stmt = stmt.where(Lead.assigned_to.ilike(f"%{filters.assigned_to.strip()}%"))
    stmt = stmt.where(
        or_(
            Lead.full_name.ilike(pattern),
            Lead.email.ilike(pattern),
            Lead.phone.ilike(pattern),
            Lead.notes.ilike(pattern),
            Lead.interested_project.ilike(pattern),
        )
    )
    leads = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for lead in leads:
        if not _apply_date_filter(lead.updated_at, filters):
            continue
        fields = {
            "name": lead.full_name,
            "email": lead.email,
            "phone": lead.phone,
            "notes": lead.notes,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        matched = _collect_matched_fields(query, fields)
        results.append(
            InternalSearchResult(
                entity_type="lead",
                entity_id=lead.id,
                title=lead.full_name,
                subtitle=lead.email or lead.phone,
                preview=lead.notes,
                status=_enum_value(lead.status),
                assigned_to=lead.assigned_to,
                created_at=lead.created_at,
                score=score,
                matched_fields=matched,
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_investors(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "investor"):
        return []
    pattern = _pattern(query)
    stmt = select(Investor).where(Investor.archived_at.is_(None))
    if filters.status:
        stmt = stmt.where(Investor.status == filters.status)
    if filters.assigned_to:
        stmt = stmt.where(Investor.assigned_to.ilike(f"%{filters.assigned_to.strip()}%"))
    stmt = stmt.where(
        or_(
            Investor.full_name.ilike(pattern),
            Investor.email.ilike(pattern),
            Investor.phone.ilike(pattern),
            Investor.country.ilike(pattern),
            Investor.city.ilike(pattern),
            Investor.notes.ilike(pattern),
            Investor.preferred_markets.ilike(pattern),
            Investor.preferred_projects.ilike(pattern),
        )
    )
    investors = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for investor in investors:
        if not _apply_date_filter(investor.updated_at, filters):
            continue
        company_label = investor.full_name if investor.investor_type.value == "company" else None
        fields = {
            "name": investor.full_name,
            "company": company_label,
            "email": investor.email,
            "country": investor.country,
            "city": investor.city,
            "notes": investor.notes,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        location = ", ".join(part for part in [investor.city, investor.country] if part)
        results.append(
            InternalSearchResult(
                entity_type="investor",
                entity_id=investor.id,
                title=investor.full_name,
                subtitle=investor.email or location or None,
                preview=investor.notes,
                status=_enum_value(investor.status),
                assigned_to=investor.assigned_to,
                created_at=investor.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_projects(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "project"):
        return []
    pattern = _pattern(query)
    stmt = select(Project).where(Project.archived_at.is_(None))
    if filters.status:
        stmt = stmt.where(Project.project_status == filters.status)
    if filters.assigned_to:
        stmt = stmt.where(
            Project.assigned_project_manager.ilike(f"%{filters.assigned_to.strip()}%")
        )
    stmt = stmt.where(
        or_(
            Project.project_name.ilike(pattern),
            Project.project_code.ilike(pattern),
            Project.address.ilike(pattern),
            Project.city.ilike(pattern),
            Project.description.ilike(pattern),
            Project.notes.ilike(pattern),
        )
    )
    projects = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for project in projects:
        if not _apply_date_filter(project.updated_at, filters):
            continue
        fields = {
            "project_name": project.project_name,
            "project_code": project.project_code,
            "address": project.address,
            "city": project.city,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        subtitle_parts = [part for part in [project.project_code, project.city] if part]
        results.append(
            InternalSearchResult(
                entity_type="project",
                entity_id=project.id,
                title=project.project_name,
                subtitle=" · ".join(subtitle_parts) if subtitle_parts else project.address,
                preview=project.description or project.address,
                status=_enum_value(project.project_status),
                assigned_to=project.assigned_project_manager,
                created_at=project.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_financial_accounts(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "financial_account"):
        return []
    pattern = _pattern(query)
    stmt = select(FinancialAccount).where(FinancialAccount.archived_at.is_(None))
    if filters.status:
        stmt = stmt.where(FinancialAccount.status == filters.status)
    stmt = stmt.where(
        or_(
            FinancialAccount.account_name.ilike(pattern),
            FinancialAccount.institution_name.ilike(pattern),
            FinancialAccount.ownership_entity.ilike(pattern),
            FinancialAccount.account_reference.ilike(pattern),
            FinancialAccount.notes.ilike(pattern),
        )
    )
    accounts = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for account in accounts:
        if not _apply_date_filter(account.updated_at, filters):
            continue
        fields = {
            "account_name": account.account_name,
            "institution_name": account.institution_name,
            "account_reference": account.account_reference,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="financial_account",
                entity_id=account.id,
                title=account.account_name,
                subtitle=account.institution_name or account.account_reference,
                preview=account.notes,
                status=_enum_value(account.status),
                created_at=account.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_financial_transactions(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "financial_transaction"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(FinanceTransaction, FinancialAccount)
        .join(FinancialAccount, FinanceTransaction.account_id == FinancialAccount.id)
        .where(FinanceTransaction.archived_at.is_(None))
    )
    if filters.status:
        stmt = stmt.where(FinanceTransaction.status == filters.status)
    stmt = stmt.where(
        or_(
            FinanceTransaction.description.ilike(pattern),
            FinanceTransaction.reference_number.ilike(pattern),
            FinanceTransaction.counterparty.ilike(pattern),
            FinanceTransaction.category.ilike(pattern),
            FinanceTransaction.notes.ilike(pattern),
            FinancialAccount.account_name.ilike(pattern),
        )
    )
    rows = db.execute(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for transaction, account in rows:
        if not _apply_date_filter(transaction.updated_at, filters):
            continue
        fields = {
            "description": transaction.description,
            "reference_number": transaction.reference_number,
            "account": account.account_name,
            "counterparty": transaction.counterparty,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        title = transaction.description or transaction.reference_number or "Transaction"
        results.append(
            InternalSearchResult(
                entity_type="financial_transaction",
                entity_id=transaction.id,
                title=title,
                subtitle=f"{account.account_name} · {transaction.amount} {transaction.currency}",
                preview=transaction.notes,
                status=_enum_value(transaction.status),
                created_at=transaction.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_funding_commitments(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "funding_commitment"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(FundingCommitment, Project, Investor)
        .join(Project, FundingCommitment.project_id == Project.id)
        .join(Investor, FundingCommitment.investor_id == Investor.id)
    )
    if filters.status:
        stmt = stmt.where(FundingCommitment.status == filters.status)
    stmt = stmt.where(
        or_(
            FundingCommitment.notes.ilike(pattern),
            Project.project_name.ilike(pattern),
            Investor.full_name.ilike(pattern),
        )
    )
    rows = db.execute(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for commitment, project, investor in rows:
        if not _apply_date_filter(commitment.updated_at, filters):
            continue
        fields = {
            "project": project.project_name,
            "investor": investor.full_name,
            "notes": commitment.notes,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="funding_commitment",
                entity_id=commitment.id,
                title=f"{investor.full_name} → {project.project_name}",
                subtitle=f"{commitment.committed_amount} {commitment.currency}",
                preview=commitment.notes,
                status=_enum_value(commitment.status),
                created_at=commitment.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_payment_obligations(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "payment_obligation"):
        return []
    pattern = _pattern(query)
    stmt = select(PaymentObligation).where(PaymentObligation.archived_at.is_(None))
    if filters.status:
        stmt = stmt.where(PaymentObligation.status == filters.status)
    stmt = stmt.where(
        or_(
            PaymentObligation.payee.ilike(pattern),
            PaymentObligation.description.ilike(pattern),
            PaymentObligation.notes.ilike(pattern),
        )
    )
    obligations = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for obligation in obligations:
        if not _apply_date_filter(obligation.updated_at, filters):
            continue
        fields = {
            "payee": obligation.payee,
            "description": obligation.description,
            "notes": obligation.notes,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        title = obligation.payee or obligation.description or "Payment obligation"
        results.append(
            InternalSearchResult(
                entity_type="payment_obligation",
                entity_id=obligation.id,
                title=title,
                subtitle=f"{obligation.amount} {obligation.currency}",
                preview=obligation.description or obligation.notes,
                status=_enum_value(obligation.status),
                created_at=obligation.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_users(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "user"):
        return []
    pattern = _pattern(query)
    stmt = select(User).where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE)
    if filters.status:
        stmt = stmt.where(User.status == filters.status)
    stmt = stmt.where(
        or_(
            User.full_name.ilike(pattern),
            User.email.ilike(pattern),
            User.job_title.ilike(pattern),
            User.department.ilike(pattern),
        )
    )
    users = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for item in users:
        if not _apply_date_filter(item.created_at, filters):
            continue
        fields = {
            "name": item.full_name,
            "email": item.email,
            "job_title": item.job_title,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        subtitle = item.email or item.job_title
        results.append(
            InternalSearchResult(
                entity_type="user",
                entity_id=item.id,
                title=item.full_name,
                subtitle=subtitle,
                preview=item.department,
                status=_enum_value(item.status),
                created_at=item.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _metadata_to_text(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""
    try:
        return json.dumps(metadata, ensure_ascii=False)
    except TypeError:
        return str(metadata)


def _search_notifications(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "notification"):
        return []
    pattern = _pattern(query)
    stmt = select(Notification).where(
        Notification.recipient_user_id == user.id,
        Notification.status != NotificationStatus.DISMISSED,
    )
    if filters.status:
        stmt = stmt.where(Notification.status == filters.status)
    stmt = stmt.where(
        or_(
            Notification.title_key.ilike(pattern),
            Notification.message_key.ilike(pattern),
            Notification.related_entity_type.ilike(pattern),
            cast(Notification.metadata_json, String).ilike(pattern),
        )
    )
    notifications = db.scalars(stmt.limit(limit * 3)).all()
    results: list[InternalSearchResult] = []
    for notification in notifications:
        if not user_can_view_notification(user, notification):
            continue
        if not _apply_date_filter(notification.created_at, filters):
            continue
        metadata = notification.metadata_json or {}
        related_label = metadata.get("related_label")
        meta_text = _metadata_to_text(metadata)
        fields = {
            "title_key": notification.title_key,
            "message_key": notification.message_key,
            "related_label": str(related_label) if related_label else None,
            "metadata": meta_text,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        title = str(related_label) if related_label else notification.title_key
        results.append(
            InternalSearchResult(
                entity_type="notification",
                entity_id=notification.id,
                title=title,
                subtitle=notification.title_key,
                preview=notification.message_key,
                status=_enum_value(notification.status),
                created_at=notification.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_activity(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "activity"):
        return []
    pattern = _pattern(query)
    stmt = select(ActivityLog)
    if filters.status:
        stmt = stmt.where(ActivityLog.action == filters.status)
    if filters.assigned_to:
        stmt = stmt.where(ActivityLog.actor_name.ilike(f"%{filters.assigned_to.strip()}%"))
    stmt = stmt.where(
        or_(
            ActivityLog.actor_name.ilike(pattern),
            ActivityLog.description_key.ilike(pattern),
            ActivityLog.event_type.ilike(pattern),
            cast(ActivityLog.metadata_json, String).ilike(pattern),
        )
    )
    entries = db.scalars(stmt.order_by(ActivityLog.created_at.desc()).limit(limit * 3)).all()
    results: list[InternalSearchResult] = []
    for entry in entries:
        if not user_can_view_activity_entry(user, entry):
            continue
        if not _apply_date_filter(entry.created_at, filters):
            continue
        metadata = entry.metadata_json or {}
        entity_label = resolve_entity_label(metadata)
        fields = {
            "actor_name": entry.actor_name,
            "description_key": entry.description_key,
            "entity_label": entity_label,
            "metadata": _metadata_to_text(metadata),
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        title = entity_label or entry.description_key
        results.append(
            InternalSearchResult(
                entity_type="activity",
                entity_id=entry.id,
                title=title,
                subtitle=entry.actor_name or entry.event_type,
                preview=entry.description_key,
                status=_enum_value(entry.action),
                assigned_to=entry.actor_name,
                created_at=entry.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


PROVIDER_MAP = {
    "lead": _search_leads,
    "investor": _search_investors,
    "project": _search_projects,
    "financial_account": _search_financial_accounts,
    "financial_transaction": _search_financial_transactions,
    "funding_commitment": _search_funding_commitments,
    "payment_obligation": _search_payment_obligations,
    "user": _search_users,
    "notification": _search_notifications,
    "activity": _search_activity,
}

ENTITY_LABEL_KEYS = {
    "lead": "search.entities.lead",
    "investor": "search.entities.investor",
    "project": "search.entities.project",
    "financial_account": "search.entities.financial_account",
    "financial_transaction": "search.entities.financial_transaction",
    "funding_commitment": "search.entities.funding_commitment",
    "payment_obligation": "search.entities.payment_obligation",
    "user": "search.entities.user",
    "notification": "search.entities.notification",
    "activity": "search.entities.activity",
}


def global_search(
    db: Session,
    user: User,
    query: str,
    *,
    filters: SearchFilters | None = None,
    per_entity_limit: int = DEFAULT_PER_ENTITY_LIMIT,
    total_limit: int = DEFAULT_TOTAL_LIMIT,
) -> SearchResponse:
    """Run permission-aware universal search across entity providers."""
    started = time.perf_counter()
    normalized = _normalize_query(query)
    active_filters = filters or SearchFilters()

    if not normalized:
        return SearchResponse(query=normalized, groups=[], total=0, took_ms=0)

    requested_types = active_filters.entity_types or set(SEARCH_ENTITY_TYPES)
    entity_types = [entity for entity in requested_types if entity in SEARCH_ENTITY_TYPES]

    grouped: dict[str, list[InternalSearchResult]] = {}
    for entity_type in entity_types:
        provider = PROVIDER_MAP.get(entity_type)
        if provider is None or not _user_can_search_entity(user, entity_type):
            continue
        grouped[entity_type] = provider(db, user, normalized, active_filters, per_entity_limit)

    flat = [item for items in grouped.values() for item in items]
    flat.sort(key=lambda item: item.score, reverse=True)
    flat = flat[:total_limit]

    allowed_after_trim: dict[str, list[InternalSearchResult]] = {key: [] for key in grouped}
    for item in flat:
        allowed_after_trim[item.entity_type].append(item)

    groups: list[SearchGroup] = []
    total = 0
    for entity_type in entity_types:
        items = allowed_after_trim.get(entity_type, [])
        if not items:
            continue
        serialized = [_to_item(normalized, item) for item in items]
        groups.append(
            SearchGroup(
                entity_type=entity_type,
                label_key=ENTITY_LABEL_KEYS[entity_type],
                items=serialized,
                total=len(serialized),
            )
        )
        total += len(serialized)

    took_ms = int((time.perf_counter() - started) * 1000)
    return SearchResponse(query=normalized, groups=groups, total=total, took_ms=took_ms)
