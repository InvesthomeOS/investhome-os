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
from sqlalchemy.orm import Session, joinedload

from investhome_api.config.search_config import (
    DEFAULT_PER_ENTITY_LIMIT,
    DEFAULT_TOTAL_LIMIT,
    ENTITY_LINK_MODULES,
    ENTITY_PERMISSION_RESOURCE,
    FINANCE_TAB_BY_ENTITY,
    SEARCH_ENTITY_TYPES,
)
from investhome_api.models.activity import ActivityLog
from investhome_api.models.company_foundation import BrandAsset, Department, Office, Team
from investhome_api.models.design_studio import DesignProject, DesignVersion, FurnitureItem, MaterialPackage, StylePreset
from investhome_api.models.document import Document, DocumentAnalysis
from investhome_api.models.drawing_intelligence import DrawingAnalysis
from investhome_api.models.finance import (
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    PaymentObligation,
)
from investhome_api.models.investor import Investor
from investhome_api.models.inventory import (
    Building,
    Floor,
    InventoryAsset,
    InventoryReservation,
    PENDING_PRICE_REQUEST_STATUSES,
    PriceChangeRequest,
    SENSITIVE_PRICE_TYPES,
)
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
from investhome_api.services.document_service import confidentiality_filter, user_can_view_document


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
    if entity_type == "office":
        return {"tab": "offices"}
    if entity_type == "department" or entity_type == "team":
        return {"tab": "organization"}
    if entity_type == "brand_asset":
        return {"tab": "brandAssets"}
    if entity_type == "design_version":
        return {}
    if entity_type == "style_preset":
        return {"tab": "style-presets"}
    if entity_type == "material_package":
        return {"tab": "material-packages"}
    if entity_type == "furniture_item":
        return {"tab": "furniture"}
    if entity_type in {"building", "floor", "inventory_asset"}:
        return query
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
        if not user_can_view_activity_entry(user, entry, db):
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


def _search_documents(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "document"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(Document)
        .outerjoin(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .outerjoin(DrawingAnalysis, DrawingAnalysis.document_id == Document.id)
        .options(joinedload(Document.analysis))
        .options(joinedload(Document.drawing_analysis))
        .where(
            Document.archived_at.is_(None),
            Document.is_latest_version.is_(True),
        )
    )
    conf_filter = confidentiality_filter(user)
    if conf_filter is not True:
        stmt = stmt.where(conf_filter)
    if filters.status:
        stmt = stmt.where(Document.status == filters.status)
    stmt = stmt.where(
        or_(
            Document.title.ilike(pattern),
            Document.original_file_name.ilike(pattern),
            Document.category.ilike(pattern),
            Document.description.ilike(pattern),
            Document.tags.ilike(pattern),
            cast(Document.document_type, String).ilike(pattern),
            DocumentAnalysis.ai_summary.ilike(pattern),
            DocumentAnalysis.ai_summary_en.ilike(pattern),
            DocumentAnalysis.extracted_text_preview.ilike(pattern),
            DocumentAnalysis.detected_document_type.ilike(pattern),
            DocumentAnalysis.extracted_entities_json.ilike(pattern),
            DrawingAnalysis.summary.ilike(pattern),
            DrawingAnalysis.summary_en.ilike(pattern),
            DrawingAnalysis.discipline.ilike(pattern),
            DrawingAnalysis.drawing_type.ilike(pattern),
        )
    )
    documents = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for document in documents:
        if not user_can_view_document(user, document):
            continue
        if not _apply_date_filter(document.updated_at, filters):
            continue
        fields = {
            "title": document.title,
            "file_name": document.original_file_name,
            "category": document.category,
            "description": document.description,
            "tags": document.tags,
            "document_type": _enum_value(document.document_type),
            "ai_summary": document.analysis.ai_summary if document.analysis else None,
            "detected_type": document.analysis.detected_document_type if document.analysis else None,
            "extracted_preview": document.analysis.extracted_text_preview if document.analysis else None,
            "drawing_summary": document.drawing_analysis.summary_en if document.drawing_analysis else None,
            "drawing_discipline": document.drawing_analysis.discipline if document.drawing_analysis else None,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="document",
                entity_id=document.id,
                title=document.title,
                subtitle=document.original_file_name,
                preview=document.description or document.category,
                status=_enum_value(document.status),
                created_at=document.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_offices(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "office"):
        return []
    pattern = _pattern(query)
    stmt = select(Office).where(Office.archived_at.is_(None)).where(
        or_(
            Office.office_name.ilike(pattern),
            Office.office_code.ilike(pattern),
            Office.city.ilike(pattern),
            Office.country.ilike(pattern),
        )
    )
    offices = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for office in offices:
        fields = {
            "office_name": office.office_name,
            "office_code": office.office_code,
            "city": office.city,
            "country": office.country,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="office",
                entity_id=office.id,
                title=office.office_name,
                subtitle=office.city,
                preview=office.country,
                status=office.status,
                created_at=office.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_departments(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "department"):
        return []
    pattern = _pattern(query)
    stmt = select(Department).where(
        or_(Department.name.ilike(pattern), Department.code.ilike(pattern), Department.description.ilike(pattern))
    )
    departments = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for dept in departments:
        fields = {"name": dept.name, "code": dept.code, "description": dept.description}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="department",
                entity_id=dept.id,
                title=dept.name,
                subtitle=dept.code,
                preview=dept.description,
                status=dept.status,
                created_at=dept.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_teams(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "team"):
        return []
    pattern = _pattern(query)
    stmt = select(Team).where(
        or_(Team.name.ilike(pattern), Team.code.ilike(pattern), Team.description.ilike(pattern))
    )
    teams = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for team in teams:
        fields = {"name": team.name, "code": team.code, "description": team.description}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="team",
                entity_id=team.id,
                title=team.name,
                subtitle=team.code,
                preview=team.description,
                status=team.status,
                created_at=team.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_brand_assets(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "brand_asset"):
        return []
    pattern = _pattern(query)
    stmt = select(BrandAsset).where(BrandAsset.archived_at.is_(None)).where(
        or_(
            BrandAsset.title.ilike(pattern),
            BrandAsset.asset_type.ilike(pattern),
            BrandAsset.usage_notes.ilike(pattern),
        )
    )
    assets = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for asset in assets:
        fields = {
            "title": asset.title,
            "asset_type": asset.asset_type,
            "usage_notes": asset.usage_notes,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="brand_asset",
                entity_id=asset.id,
                title=asset.title or asset.asset_type,
                subtitle=asset.asset_type,
                preview=asset.usage_notes,
                status=asset.status,
                created_at=asset.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_design_projects(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "design_project"):
        return []

    pattern = _pattern(query)
    design_projects = db.scalars(
        select(DesignProject)
        .where(
            DesignProject.archived_at.is_(None),
            or_(
                DesignProject.title.ilike(pattern),
                cast(DesignProject.design_type, String).ilike(pattern),
                cast(DesignProject.status, String).ilike(pattern),
            ),
        )
        .order_by(DesignProject.updated_at.desc())
        .limit(limit * 3)
    ).all()

    results: list[InternalSearchResult] = []
    for design_project in design_projects:
        project = db.get(Project, design_project.project_id)
        document = db.get(Document, design_project.document_id)
        fields = {
            "title": design_project.title,
            "design_type": _enum_value(design_project.design_type),
            "status": _enum_value(design_project.status),
            "project_name": project.project_name if project else None,
            "document_title": document.title if document else None,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        subtitle_parts = [
            part
            for part in (
                project.project_name if project else None,
                document.title if document else None,
                _enum_value(design_project.design_type),
            )
            if part
        ]
        results.append(
            InternalSearchResult(
                entity_type="design_project",
                entity_id=design_project.id,
                title=design_project.title,
                subtitle=" · ".join(subtitle_parts) if subtitle_parts else None,
                preview=design_project.description,
                status=_enum_value(design_project.status),
                created_at=design_project.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_style_presets(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "style_preset"):
        return []
    pattern = _pattern(query)
    presets = db.scalars(
        select(StylePreset)
        .where(
            StylePreset.archived_at.is_(None),
            or_(StylePreset.name.ilike(pattern), StylePreset.code.ilike(pattern)),
        )
        .order_by(StylePreset.name)
        .limit(limit * 2)
    ).all()
    results: list[InternalSearchResult] = []
    for preset in presets:
        fields = {"name": preset.name, "code": preset.code, "description": preset.description}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="style_preset",
                entity_id=preset.id,
                title=preset.name,
                subtitle=preset.code,
                preview=preset.description,
                created_at=preset.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_material_packages(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "material_package"):
        return []
    pattern = _pattern(query)
    packages = db.scalars(
        select(MaterialPackage)
        .where(
            MaterialPackage.archived_at.is_(None),
            or_(MaterialPackage.name.ilike(pattern), MaterialPackage.description.ilike(pattern)),
        )
        .order_by(MaterialPackage.name)
        .limit(limit * 2)
    ).all()
    results: list[InternalSearchResult] = []
    for package in packages:
        fields = {"name": package.name, "description": package.description, "flooring": package.flooring}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="material_package",
                entity_id=package.id,
                title=package.name,
                subtitle=package.flooring,
                preview=package.description,
                created_at=package.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_furniture_items(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "furniture_item"):
        return []
    pattern = _pattern(query)
    items = db.scalars(
        select(FurnitureItem)
        .where(
            FurnitureItem.archived_at.is_(None),
            or_(FurnitureItem.name.ilike(pattern), FurnitureItem.code.ilike(pattern)),
        )
        .order_by(FurnitureItem.name)
        .limit(limit * 2)
    ).all()
    results: list[InternalSearchResult] = []
    for item in items:
        fields = {
            "name": item.name,
            "code": item.code,
            "furniture_type": _enum_value(item.furniture_type),
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="furniture_item",
                entity_id=item.id,
                title=item.name,
                subtitle=_enum_value(item.furniture_type),
                created_at=item.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_design_versions(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "design_version"):
        return []
    pattern = _pattern(query)
    rows = db.execute(
        select(DesignVersion, DesignProject)
        .join(DesignProject, DesignVersion.design_project_id == DesignProject.id)
        .where(
            DesignProject.archived_at.is_(None),
            or_(
                DesignProject.title.ilike(pattern),
                cast(DesignVersion.version_number, String).ilike(pattern),
            ),
        )
        .order_by(DesignVersion.created_at.desc())
        .limit(limit * 2)
    ).all()
    results: list[InternalSearchResult] = []
    for version, project in rows:
        title = f"{project.title} v{version.version_number}"
        fields = {"title": title, "project_title": project.title}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="design_version",
                entity_id=version.id,
                title=title,
                subtitle=project.title,
                status=_enum_value(project.status),
                created_at=version.created_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_buildings(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "building"):
        return []
    pattern = _pattern(query)
    stmt = select(Building).where(Building.archived_at.is_(None)).where(
        or_(
            Building.name.ilike(pattern),
            Building.code.ilike(pattern),
            Building.address.ilike(pattern),
            Building.description.ilike(pattern),
        )
    )
    buildings = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for building in buildings:
        if not _apply_date_filter(building.updated_at, filters):
            continue
        fields = {"name": building.name, "code": building.code, "address": building.address}
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="building",
                entity_id=building.id,
                title=building.name,
                subtitle=building.code,
                status=_enum_value(building.status),
                created_at=building.updated_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_floors(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "floor"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(Floor, Building)
        .join(Building, Floor.building_id == Building.id)
        .where(Floor.archived_at.is_(None))
        .where(
            or_(
                Floor.display_name.ilike(pattern),
                Floor.level_code.ilike(pattern),
                Floor.description.ilike(pattern),
            )
        )
    )
    rows = db.execute(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for floor, building in rows:
        if not _apply_date_filter(floor.updated_at, filters):
            continue
        title = floor.display_name or f"Floor {floor.floor_number}"
        fields = {
            "display_name": floor.display_name,
            "level_code": floor.level_code,
            "building_code": building.code,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="floor",
                entity_id=floor.id,
                title=title,
                subtitle=building.code,
                status=_enum_value(floor.status),
                created_at=floor.updated_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_inventory_assets(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "inventory_asset"):
        return []
    pattern = _pattern(query)
    stmt = select(InventoryAsset).where(InventoryAsset.archived_at.is_(None)).where(
        or_(
            InventoryAsset.display_id.ilike(pattern),
            InventoryAsset.system_code.ilike(pattern),
            InventoryAsset.legal_identifier.ilike(pattern),
            InventoryAsset.description.ilike(pattern),
        )
    )
    assets = db.scalars(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for asset in assets:
        if not _apply_date_filter(asset.updated_at, filters):
            continue
        fields = {
            "display_id": asset.display_id,
            "system_code": asset.system_code,
            "legal_identifier": asset.legal_identifier,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="inventory_asset",
                entity_id=asset.id,
                title=asset.display_id,
                subtitle=asset.system_code,
                status=_enum_value(asset.availability_status),
                created_at=asset.updated_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_inventory_reservations(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "inventory_reservation"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(InventoryReservation, InventoryAsset)
        .join(InventoryAsset, InventoryAsset.id == InventoryReservation.inventory_asset_id)
        .where(
            or_(
                InventoryAsset.display_id.ilike(pattern),
                InventoryAsset.system_code.ilike(pattern),
                InventoryReservation.notes.ilike(pattern),
            )
        )
    )
    rows = db.execute(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for reservation, asset in rows:
        if not _apply_date_filter(reservation.updated_at, filters):
            continue
        fields = {
            "display_id": asset.display_id,
            "system_code": asset.system_code,
            "status": reservation.status.value,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="inventory_reservation",
                entity_id=reservation.id,
                title=f"{asset.display_id} — {reservation.status.value}",
                subtitle=asset.system_code,
                status=reservation.status.value,
                created_at=reservation.updated_at,
                score=score,
                matched_fields=_collect_matched_fields(query, fields),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _search_price_change_requests(
    db: Session,
    user: User,
    query: str,
    filters: SearchFilters,
    limit: int,
) -> list[InternalSearchResult]:
    if not _user_can_search_entity(user, "price_change_request"):
        return []
    if not user_has_permission(user, "inventory", "view_price"):
        return []
    pattern = _pattern(query)
    stmt = (
        select(PriceChangeRequest, InventoryAsset)
        .join(InventoryAsset, InventoryAsset.id == PriceChangeRequest.inventory_asset_id)
        .where(
            or_(
                InventoryAsset.display_id.ilike(pattern),
                InventoryAsset.system_code.ilike(pattern),
                PriceChangeRequest.reason.ilike(pattern),
            ),
            PriceChangeRequest.archived_at.is_(None),
        )
    )
    rows = db.execute(stmt.limit(limit * 2)).all()
    results: list[InternalSearchResult] = []
    for price_request, asset in rows:
        if not _apply_date_filter(price_request.updated_at, filters):
            continue
        can_show_amount = user_has_permission(user, "inventory", "view_sensitive_price") or (
            price_request.price_type not in SENSITIVE_PRICE_TYPES
        )
        amount_label = (
            str(price_request.proposed_amount) if can_show_amount else "—"
        )
        fields = {
            "display_id": asset.display_id,
            "system_code": asset.system_code,
            "price_type": price_request.price_type.value,
            "status": price_request.status.value,
        }
        score = _score_match(query, *fields.values())
        if score <= 0:
            continue
        results.append(
            InternalSearchResult(
                entity_type="price_change_request",
                entity_id=price_request.id,
                title=f"{asset.display_id} — {price_request.price_type.value} ({amount_label})",
                subtitle=price_request.status.value,
                status=price_request.status.value,
                created_at=price_request.updated_at,
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
    "document": _search_documents,
    "office": _search_offices,
    "department": _search_departments,
    "team": _search_teams,
    "brand_asset": _search_brand_assets,
    "design_project": _search_design_projects,
    "style_preset": _search_style_presets,
    "material_package": _search_material_packages,
    "furniture_item": _search_furniture_items,
    "design_version": _search_design_versions,
    "building": _search_buildings,
    "floor": _search_floors,
    "inventory_asset": _search_inventory_assets,
    "inventory_reservation": _search_inventory_reservations,
    "price_change_request": _search_price_change_requests,
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
    "document": "search.entities.document",
    "office": "search.entities.office",
    "department": "search.entities.department",
    "team": "search.entities.team",
    "brand_asset": "search.entities.brand_asset",
    "design_project": "search.entities.design_project",
    "style_preset": "search.entities.style_preset",
    "material_package": "search.entities.material_package",
    "furniture_item": "search.entities.furniture_item",
    "design_version": "search.entities.design_version",
    "building": "search.entities.building",
    "floor": "search.entities.floor",
    "inventory_asset": "search.entities.inventory_asset",
    "inventory_reservation": "search.entities.inventory_reservation",
    "price_change_request": "search.entities.price_change_request",
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
