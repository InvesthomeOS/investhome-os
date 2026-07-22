"""CRM global search orchestration service."""

from __future__ import annotations

import csv
import io
import time
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_search import CrmRecentSearch, CrmSavedSearch, CrmSearchAuditLog
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_search import (
    CrmDuplicateDiscoveryMatch,
    CrmDuplicateDiscoveryResponse,
    CrmEntityPickerResponse,
    CrmNaturalLanguageResponse,
    CrmParseQueryResponse,
    CrmRecentSearchCreate,
    CrmRecentSearchResponse,
    CrmSavedSearchCreate,
    CrmSavedSearchResponse,
    CrmSavedSearchUpdate,
    CrmSearchAnalyticsSummary,
    CrmSearchExportResponse,
    CrmSearchHighlightField,
    CrmSearchQueryRequest,
    CrmSearchResponse,
    CrmSearchResultGroup,
    CrmSearchResultItem,
    CrmSearchSuggestionItem,
    CrmSearchSuggestionsResponse,
)
from investhome_api.services.crm.search_parser import parse_structured_search_query, parsed_to_dict
from investhome_api.services.crm.search_permissions import (
    allowed_entity_types,
    can_export_search_results,
    can_manage_saved_searches,
    can_search_archived,
    can_search_communication_content,
    can_search_restricted,
    can_use_natural_language_search,
    can_view_search_analytics,
)
from investhome_api.services.crm.search_provider import get_default_provider, hit_to_highlight_fields
from investhome_api.services.crm.search_ranking import suggest_did_you_mean
from investhome_api.services.search_service import global_search, SearchFilters

ENTITY_LABEL_KEYS = {
    "crm_contact": "crm.search.entities.contact",
    "crm_company": "crm.search.entities.company",
    "crm_relationship": "crm.search.entities.relationship",
    "crm_activity": "crm.search.entities.activity",
    "crm_communication": "crm.search.entities.communication",
    "crm_task": "crm.search.entities.task",
    "sales_opportunity": "crm.search.entities.opportunity",
    "investor": "crm.search.entities.investor",
    "project": "crm.search.entities.project",
    "inventory_asset": "crm.search.entities.property",
    "financial_transaction": "crm.search.entities.transaction",
    "document": "crm.search.entities.document",
}

ENTITY_URLS = {
    "crm_contact": "/workspaces/crm/contacts/{id}",
    "crm_company": "/workspaces/crm/companies/{id}",
    "crm_relationship": "/workspaces/crm/relationships/{id}",
    "crm_activity": "/workspaces/crm/activities?id={id}",
    "crm_communication": "/workspaces/crm/communication?id={id}",
    "sales_opportunity": "/dashboard/sales?id={id}",
    "investor": "/dashboard/investors?id={id}",
    "project": "/dashboard/projects?id={id}",
    "inventory_asset": "/dashboard/inventory?id={id}",
    "financial_transaction": "/dashboard/finance?id={id}",
    "document": "/dashboard/documents?id={id}",
}

ENTITY_ICONS = {
    "crm_contact": "user",
    "crm_company": "building",
    "crm_relationship": "link",
    "crm_activity": "activity",
    "crm_communication": "mail",
    "sales_opportunity": "target",
    "investor": "trending-up",
    "project": "folder",
    "inventory_asset": "home",
    "financial_transaction": "dollar",
    "document": "file",
}

CROSS_MODULE_TYPES = frozenset({"sales_opportunity", "investor", "project", "inventory_asset", "financial_transaction", "document"})

DEFAULT_SAVED_SEARCH_CONFIGS = [
    {
        "name": "Active Investors",
        "description": "CRM contacts tagged as investors with active status",
        "query": "type:investor status:active",
        "entity_types": ["crm_contact"],
        "is_default": True,
    },
    {
        "name": "Follow-Up Overdue",
        "description": "Contacts with overdue follow-ups",
        "query": "status:active",
        "entity_types": ["crm_contact"],
        "is_default": True,
    },
]

QUICK_SEARCH_PER_ENTITY = 5
GLOBAL_MODULE_PER_ENTITY = 3


def _audit(db: Session, user: User, action: str, *, query: str | None = None, entity_type: str | None = None, entity_id: UUID | None = None, metadata: dict | None = None) -> None:
    db.add(
        CrmSearchAuditLog(
            user_id=user.id,
            action=action,
            query=query,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
        )
    )


def _serialize_hit(hit, query: str) -> CrmSearchResultItem:
    url_template = ENTITY_URLS.get(hit.entity_type, "/workspaces/crm/search")
    return CrmSearchResultItem(
        id=hit.entity_id,
        entity_type=hit.entity_type,
        entity_id=hit.entity_id,
        title=hit.title,
        subtitle=hit.subtitle,
        description=hit.description,
        preview=hit.preview,
        highlighted_fields=[
            CrmSearchHighlightField(**h) for h in hit_to_highlight_fields(query, hit.matched_fields)
        ],
        matched_fields=list(hit.matched_fields.keys()),
        score=hit.score,
        relevance_score=hit.relevance_score,
        recency_score=hit.recency_score,
        relationship_score=hit.relationship_score,
        entity_status=hit.entity_status,
        owner_id=hit.owner_id,
        owner_name=hit.owner_name,
        tags=hit.tags,
        url=url_template.format(id=hit.entity_id),
        icon=ENTITY_ICONS.get(hit.entity_type),
        created_at=hit.created_at,
        updated_at=hit.updated_at,
        last_activity_at=hit.last_activity_at,
        permission_level="read",
        metadata=hit.metadata,
    )


def _resolve_entity_types(user: User, requested: list[str] | None) -> list[str]:
    allowed = allowed_entity_types(user)
    if not requested:
        return sorted(allowed)
    return [et for et in requested if et in allowed]


def _apply_parsed_filters(request: CrmSearchQueryRequest, parsed) -> CrmSearchQueryRequest:
    if parsed.entity_types and not request.entity_types:
        request.entity_types = parsed.entity_types
    if parsed.free_text:
        request.query = parsed.free_text
    return request


def crm_global_search(db: Session, user: User, request: CrmSearchQueryRequest) -> CrmSearchResponse:
    started = time.perf_counter()
    parsed = parse_structured_search_query(request.query)
    if parsed.errors:
        return CrmSearchResponse(
            query=request.query,
            parsed_query=parsed_to_dict(parsed),
            total=0,
            explanation="; ".join(parsed.errors),
        )
    request = _apply_parsed_filters(request, parsed)

    if request.saved_search_id:
        saved = db.get(CrmSavedSearch, request.saved_search_id)
        if saved and (saved.owner_id == user.id or saved.visibility == "shared"):
            request.query = saved.query or request.query
            request.entity_types = saved.entity_types or request.entity_types
            if saved.filters_json:
                request.filters = None  # applied via saved config

    include_archived = request.include_archived and can_search_archived(user)
    entity_types = _resolve_entity_types(user, request.entity_types)
    provider = get_default_provider()
    per_entity = request.page_size
    all_hits = []

    for entity_type in entity_types:
        if entity_type in CROSS_MODULE_TYPES:
            continue
        if entity_type == "crm_communication" and not can_search_communication_content(user):
            continue
        hits = provider.search_entity(
            db,
            user,
            entity_type,
            request.query,
            limit=per_entity,
            include_archived=include_archived,
            exact_match=request.exact_match,
            fuzzy_match=request.fuzzy_match,
        )
        all_hits.extend(hits)

    # Cross-module entities via existing global search
    cross_types = [et for et in entity_types if et in CROSS_MODULE_TYPES]
    if cross_types and request.query.strip():
        gs = global_search(
            db,
            user,
            request.query.strip(),
            filters=SearchFilters(entity_types=set(cross_types)),
            per_entity_limit=GLOBAL_MODULE_PER_ENTITY,
            total_limit=request.page_size,
        )
        for group in gs.groups:
            for item in group.items:
                all_hits.append(
                    type(
                        "Hit",
                        (),
                        {
                            "entity_type": item.entity_type,
                            "entity_id": item.entity_id,
                            "title": item.title,
                            "subtitle": item.subtitle,
                            "description": None,
                            "preview": item.preview,
                            "entity_status": item.status,
                            "owner_id": None,
                            "owner_name": item.assigned_to,
                            "tags": [],
                            "created_at": item.created_at,
                            "updated_at": item.created_at,
                            "last_activity_at": None,
                            "score": item.score,
                            "relevance_score": item.score,
                            "recency_score": 0.0,
                            "relationship_score": 0.0,
                            "matched_fields": {h.field: h.snippet for h in item.highlights},
                            "metadata": {},
                        },
                    )()
                )

    reverse = request.sort_dir != "asc"
    if request.sort.value == "recency":
        all_hits.sort(key=lambda h: h.updated_at or h.created_at or datetime.min.replace(tzinfo=UTC), reverse=reverse)
    elif request.sort.value == "title":
        all_hits.sort(key=lambda h: h.title.lower(), reverse=reverse)
    else:
        all_hits.sort(key=lambda h: h.score, reverse=True)

    total = len(all_hits)
    offset = (request.page - 1) * request.page_size
    page_hits = all_hits[offset : offset + request.page_size]
    items = [_serialize_hit(h, request.query) for h in page_hits]

    grouped: dict[str, list] = {}
    for item in items:
        grouped.setdefault(item.entity_type, []).append(item)
    groups = [
        CrmSearchResultGroup(
            entity_type=et,
            label_key=ENTITY_LABEL_KEYS.get(et, f"crm.search.entities.{et}"),
            items=group_items,
            total=len(group_items),
        )
        for et, group_items in grouped.items()
    ]

    took_ms = int((time.perf_counter() - started) * 1000)
    _audit(db, user, "search_executed", query=request.query, metadata={"total": total, "took_ms": took_ms})
    db.flush()

    return CrmSearchResponse(
        query=request.query,
        parsed_query=parsed_to_dict(parsed),
        groups=groups,
        items=items,
        total=total,
        page=request.page,
        page_size=request.page_size,
        has_more=offset + request.page_size < total,
        took_ms=took_ms,
        did_you_mean=suggest_did_you_mean(request.query, []) if total == 0 else None,
        explanation=None if total else "No results match your query and filters.",
        active_filters=[f"{f.field}:{f.value}" for f in parsed.field_filters],
    )


def crm_quick_search(db: Session, user: User, query: str, *, limit: int = 25) -> CrmSearchResponse:
    request = CrmSearchQueryRequest(query=query, page_size=limit, page=1)
    return crm_global_search(db, user, request)


def crm_search_suggestions(db: Session, user: User, query: str) -> CrmSearchSuggestionsResponse:
    if len(query.strip()) < 2:
        return CrmSearchSuggestionsResponse(query=query, suggestions=[])
    response = crm_quick_search(db, user, query, limit=8)
    suggestions = [
        CrmSearchSuggestionItem(text=item.title, type="entity", entity_type=item.entity_type)
        for item in response.items[:8]
    ]
    return CrmSearchSuggestionsResponse(query=query, suggestions=suggestions)


def parse_query(query: str) -> CrmParseQueryResponse:
    parsed = parse_structured_search_query(query)
    return CrmParseQueryResponse(query=query, parsed=parsed_to_dict(parsed), errors=parsed.errors, warnings=parsed.warnings)


def interpret_natural_language(db: Session, user: User, query: str) -> CrmNaturalLanguageResponse:
    if not can_use_natural_language_search(user):
        return CrmNaturalLanguageResponse(
            query=query,
            available=False,
            message="Natural-language search requires AI integration (not configured).",
        )
    return CrmNaturalLanguageResponse(
        query=query,
        available=False,
        message="AI provider not configured. Use structured filters or field syntax instead.",
    )


def list_recent_searches(db: Session, user: User, *, limit: int = 20) -> list[CrmRecentSearchResponse]:
    rows = db.scalars(
        select(CrmRecentSearch)
        .where(CrmRecentSearch.user_id == user.id)
        .order_by(desc(CrmRecentSearch.searched_at))
        .limit(limit)
    ).all()
    return [
        CrmRecentSearchResponse(
            id=r.id,
            query=r.query,
            filters=r.filters_json,
            entity_types=r.entity_types,
            result_count=r.result_count,
            opened_result_id=r.opened_result_id,
            opened_entity_type=r.opened_entity_type,
            searched_at=r.searched_at,
        )
        for r in rows
    ]


def record_recent_search(db: Session, user: User, payload: CrmRecentSearchCreate) -> CrmRecentSearchResponse:
    row = CrmRecentSearch(
        user_id=user.id,
        query=payload.query,
        filters_json=payload.filters,
        entity_types=payload.entity_types,
        result_count=payload.result_count,
        opened_result_id=payload.opened_result_id,
        opened_entity_type=payload.opened_entity_type,
    )
    db.add(row)
    db.flush()
    return CrmRecentSearchResponse(
        id=row.id,
        query=row.query,
        filters=row.filters_json,
        entity_types=row.entity_types,
        result_count=row.result_count,
        opened_result_id=row.opened_result_id,
        opened_entity_type=row.opened_entity_type,
        searched_at=row.searched_at,
    )


def clear_recent_searches(db: Session, user: User) -> None:
    db.execute(delete(CrmRecentSearch).where(CrmRecentSearch.user_id == user.id))


def remove_recent_search(db: Session, user: User, search_id: UUID) -> bool:
    row = db.scalar(
        select(CrmRecentSearch).where(CrmRecentSearch.id == search_id, CrmRecentSearch.user_id == user.id)
    )
    if row is None:
        return False
    db.delete(row)
    return True


def _serialize_saved(row: CrmSavedSearch) -> CrmSavedSearchResponse:
    return CrmSavedSearchResponse(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        query=row.query,
        filters=row.filters_json,
        entity_types=row.entity_types,
        sort=row.sort_json,
        grouping=row.grouping,
        visible_fields=row.visible_fields,
        view_mode=row.view_mode,
        visibility=row.visibility,
        shared_with=row.shared_with,
        notification_settings=row.notification_settings,
        is_default=row.is_default,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_saved_searches(db: Session, user: User) -> list[CrmSavedSearchResponse]:
    rows = db.scalars(
        select(CrmSavedSearch).where(
            or_(
                CrmSavedSearch.owner_id == user.id,
                CrmSavedSearch.visibility == "shared",
                CrmSavedSearch.is_default.is_(True),
            )
        ).order_by(CrmSavedSearch.name)
    ).all()
    if not rows:
        for cfg in DEFAULT_SAVED_SEARCH_CONFIGS:
            row = CrmSavedSearch(
                owner_id=user.id,
                name=cfg["name"],
                description=cfg.get("description"),
                query=cfg.get("query"),
                entity_types=cfg.get("entity_types"),
                is_default=cfg.get("is_default", False),
            )
            db.add(row)
        db.flush()
        rows = db.scalars(select(CrmSavedSearch).where(CrmSavedSearch.owner_id == user.id)).all()
    return [_serialize_saved(r) for r in rows]


def create_saved_search(db: Session, user: User, payload: CrmSavedSearchCreate) -> CrmSavedSearchResponse:
    row = CrmSavedSearch(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        query=payload.query,
        filters_json=payload.filters,
        entity_types=payload.entity_types,
        sort_json=payload.sort,
        grouping=payload.grouping,
        visible_fields=payload.visible_fields,
        view_mode=payload.view_mode,
        visibility=payload.visibility,
        shared_with=[str(x) for x in payload.shared_with] if payload.shared_with else None,
        notification_settings=payload.notification_settings,
    )
    db.add(row)
    db.flush()
    return _serialize_saved(row)


def update_saved_search(db: Session, user: User, search_id: UUID, payload: CrmSavedSearchUpdate) -> CrmSavedSearchResponse | None:
    row = db.get(CrmSavedSearch, search_id)
    if row is None or (row.owner_id != user.id and not row.is_default):
        return None
    for field, attr in [
        ("name", "name"), ("description", "description"), ("query", "query"),
        ("filters", "filters_json"), ("entity_types", "entity_types"), ("sort", "sort_json"),
        ("grouping", "grouping"), ("visible_fields", "visible_fields"), ("view_mode", "view_mode"),
        ("visibility", "visibility"), ("notification_settings", "notification_settings"),
    ]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(row, attr, val)
    if payload.shared_with is not None:
        row.shared_with = [str(x) for x in payload.shared_with]
    row.updated_at = datetime.now(UTC)
    db.flush()
    return _serialize_saved(row)


def delete_saved_search(db: Session, user: User, search_id: UUID) -> bool:
    row = db.get(CrmSavedSearch, search_id)
    if row is None or row.owner_id != user.id or row.is_default:
        return False
    db.delete(row)
    return True


def execute_saved_search(db: Session, user: User, search_id: UUID) -> CrmSearchResponse:
    row = db.get(CrmSavedSearch, search_id)
    if row is None:
        return CrmSearchResponse(query="", total=0, explanation="Saved search not found.")
    request = CrmSearchQueryRequest(
        query=row.query or "",
        entity_types=row.entity_types,
        saved_search_id=search_id,
        page_size=25,
    )
    return crm_global_search(db, user, request)


def entity_picker_results(db: Session, user: User, query: str, *, entity_types: list[str] | None, page: int, page_size: int, exclude_ids: list[UUID] | None) -> CrmEntityPickerResponse:
    request = CrmSearchQueryRequest(query=query, entity_types=entity_types or ["crm_contact", "crm_company"], page=page, page_size=page_size)
    response = crm_global_search(db, user, request)
    items = response.items
    if exclude_ids:
        exclude = set(exclude_ids)
        items = [i for i in items if i.entity_id not in exclude]
    return CrmEntityPickerResponse(
        items=items,
        total=response.total,
        page=page,
        page_size=page_size,
        has_more=response.has_more,
    )


def discover_duplicates(db: Session, user: User, *, entity_type: str, entity_id: UUID | None, display_name: str | None, email: str | None, phone: str | None) -> CrmDuplicateDiscoveryResponse:
    from investhome_api.models.crm_contact import CrmContact
    from investhome_api.models.crm_company import CrmCompany
    from investhome_api.services.crm.contact_service import check_duplicates
    from investhome_api.schemas.crm_contacts import CrmDuplicateCheckRequest

    matches: list[CrmDuplicateDiscoveryMatch] = []
    if entity_type == "crm_contact":
        dupes = check_duplicates(
            db,
            CrmDuplicateCheckRequest(
                display_name=display_name,
                primary_email=email,
                primary_phone=phone,
                exclude_contact_id=entity_id,
            ),
        )
        matches = [
            CrmDuplicateDiscoveryMatch(
                entity_type="crm_contact",
                entity_id=d.contact_id,
                title=d.display_name,
                match_reason=d.match_reason,
                score=d.match_score,
            )
            for d in dupes
        ]
    elif entity_type == "crm_company" and display_name:
        pattern = f"%{display_name.strip()}%"
        companies = db.scalars(
            select(CrmCompany).where(
                CrmCompany.archived_at.is_(None),
                or_(CrmCompany.display_name.ilike(pattern), CrmCompany.legal_name.ilike(pattern)),
            ).limit(10)
        ).all()
        matches = [
            CrmDuplicateDiscoveryMatch(
                entity_type="crm_company",
                entity_id=c.id,
                title=c.display_name,
                match_reason="similar_name",
                score=80.0,
            )
            for c in companies
            if entity_id is None or c.id != entity_id
        ]
    _audit(db, user, "duplicate_discovery", entity_type=entity_type, entity_id=entity_id)
    return CrmDuplicateDiscoveryResponse(matches=matches)


def search_related_entities(db: Session, user: User, entity_type: str, entity_id: UUID, query: str = "") -> CrmSearchResponse:
    from investhome_api.services.crm.relationship_graph_service import get_relationship_graph

    graph = get_relationship_graph(
        db,
        center_entity_type=entity_type.replace("crm_", ""),
        center_entity_id=entity_id,
        depth=2,
        limit=50,
        include_confidential=can_search_restricted(user),
    )
    items: list[CrmSearchResultItem] = []
    for node in graph.nodes:
        if query and query.lower() not in node.label.lower():
            continue
        et = f"crm_{node.entity_type}" if not node.entity_type.startswith("crm_") else node.entity_type
        items.append(
            CrmSearchResultItem(
                id=node.entity_id,
                entity_type=et,
                entity_id=node.entity_id,
                title=node.label,
                subtitle=node.entity_type,
                url=ENTITY_URLS.get(et, "/workspaces/crm/search").format(id=node.entity_id),
                icon=ENTITY_ICONS.get(et),
            )
        )
    return CrmSearchResponse(query=query, items=items, total=len(items))


def search_warm_introduction_candidates(db: Session, user: User, target_type: str, target_id: UUID) -> CrmSearchResponse:
    from investhome_api.services.crm.introduction_path_service import find_introduction_paths

    paths = find_introduction_paths(
        db,
        source_entity_type="contact",
        source_entity_id=target_id,
        target_entity_type=target_type,
        target_entity_id=target_id,
        include_confidential=can_search_restricted(user),
    )
    items: list[CrmSearchResultItem] = []
    for path in paths.paths[:10]:
        if path.steps:
            first = path.steps[0]
            items.append(
                CrmSearchResultItem(
                    id=first.entity_id,
                    entity_type=f"crm_{first.entity_type}",
                    entity_id=first.entity_id,
                    title=first.label,
                    subtitle=f"Path strength: {path.total_strength}",
                    url="/workspaces/crm/relationships/network",
                    score=path.total_strength,
                )
            )
    return CrmSearchResponse(query="", items=items, total=len(items))


def export_search_results(db: Session, user: User, *, format: str, items: list[CrmSearchResultItem], visible_fields: list[str] | None) -> CrmSearchExportResponse:
    if not can_export_search_results(user):
        return CrmSearchExportResponse(format=format, row_count=0)
    fields = visible_fields or ["entity_type", "title", "subtitle", "entity_status", "url"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for item in items:
        writer.writerow({f: getattr(item, f, "") for f in fields})
    _audit(db, user, "search_export", metadata={"format": format, "count": len(items)})
    return CrmSearchExportResponse(format=format, content=buffer.getvalue(), row_count=len(items))


def search_analytics(db: Session, user: User) -> CrmSearchAnalyticsSummary:
    if not can_view_search_analytics(user):
        return CrmSearchAnalyticsSummary()
    total = db.scalar(select(func.count()).select_from(CrmSearchAuditLog).where(CrmSearchAuditLog.action == "search_executed")) or 0
    return CrmSearchAnalyticsSummary(total_searches=total)
