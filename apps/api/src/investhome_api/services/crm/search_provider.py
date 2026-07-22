"""Replaceable CRM search provider interface.

Primary implementation: PostgreSQL full-text search (tsvector + GIN indexes).
Future providers: Elasticsearch, OpenSearch, Meilisearch, Typesense, Vector DB.

Required indexes (PostgreSQL):
- crm_contacts.search_vector GIN — display_name, email, phone, org, city, notes
- crm_companies.search_vector GIN — display_name, legal_name, domain, registration
- crm_activities.search_vector GIN — title, summary, description

Sensitive excluded fields: compliance notes, financial profiles, private communication body,
referral compensation, confidential relationship metadata.

Reindex strategy: migration 0037 adds generated STORED columns; re-run ANALYZE after bulk imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_company import CrmCompany
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.crm_relationship import CrmRelationship
from investhome_api.models.user_auth import User
from investhome_api.services.crm.search_ranking import (
    build_highlight_html,
    build_snippet,
    compute_combined_score,
    score_recency,
    score_text_match,
)


@dataclass
class InternalCrmSearchHit:
    entity_type: str
    entity_id: UUID
    title: str
    subtitle: str | None = None
    description: str | None = None
    preview: str | None = None
    entity_status: str | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_activity_at: datetime | None = None
    score: float = 0.0
    relevance_score: float = 0.0
    recency_score: float = 0.0
    relationship_score: float = 0.0
    matched_fields: dict[str, str] = field(default_factory=dict)
    is_favorite: bool = False
    is_pinned: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class CrmSearchProvider(ABC):
    @abstractmethod
    def search_entity(
        self,
        db: Session,
        user: User,
        entity_type: str,
        query: str,
        *,
        limit: int,
        include_archived: bool,
        exact_match: bool,
        fuzzy_match: bool,
    ) -> list[InternalCrmSearchHit]:
        ...


def _pattern(query: str) -> str:
    return f"%{query.strip()}%"


def _collect_matched(query: str, fields: dict[str, str | None]) -> dict[str, str]:
    needle = query.strip().lower()
    matched: dict[str, str] = {}
    for name, value in fields.items():
        if value and needle in str(value).lower():
            matched[name] = str(value)
    return matched


def _enum_val(value: Any) -> str | None:
    if value is None:
        return None
    return str(value.value if hasattr(value, "value") else value)


class PostgresFtsCrmSearchProvider(CrmSearchProvider):
    """PostgreSQL FTS with ILIKE fallback for SQLite tests."""

    def _use_fts(self, db: Session) -> bool:
        return db.bind is not None and db.bind.dialect.name == "postgresql"

    def _fts_condition(self, column_name: str, query: str):
        ts_query = func.plainto_tsquery("simple", query.strip())
        return text(f"{column_name} @@ plainto_tsquery('simple', :q)").bindparams(q=query.strip())

    def search_entity(
        self,
        db: Session,
        user: User,
        entity_type: str,
        query: str,
        *,
        limit: int,
        include_archived: bool,
        exact_match: bool,
        fuzzy_match: bool,
    ) -> list[InternalCrmSearchHit]:
        dispatch = {
            "crm_contact": self._search_contacts,
            "crm_company": self._search_companies,
            "crm_relationship": self._search_relationships,
            "crm_activity": self._search_activities,
            "crm_communication": self._search_communications,
        }
        handler = dispatch.get(entity_type)
        if handler is None:
            return []
        return handler(db, query, limit=limit, include_archived=include_archived, exact_match=exact_match)

    def _search_contacts(
        self, db: Session, query: str, *, limit: int, include_archived: bool, exact_match: bool
    ) -> list[InternalCrmSearchHit]:
        pattern = _pattern(query)
        stmt = select(CrmContact)
        if not include_archived:
            stmt = stmt.where(CrmContact.archived_at.is_(None))
        if self._use_fts(db):
            stmt = stmt.where(text("search_vector @@ plainto_tsquery('simple', :q)").bindparams(q=query.strip()))
        else:
            stmt = stmt.where(
                or_(
                    CrmContact.display_name.ilike(pattern),
                    CrmContact.primary_email.ilike(pattern),
                    CrmContact.primary_phone.ilike(pattern),
                    CrmContact.organization_name.ilike(pattern),
                    CrmContact.first_name.ilike(pattern),
                    CrmContact.last_name.ilike(pattern),
                    CrmContact.city.ilike(pattern),
                    CrmContact.notes.ilike(pattern),
                )
            )
        rows = db.scalars(stmt.limit(limit * 2)).all()
        hits: list[InternalCrmSearchHit] = []
        for row in rows:
            fields = {
                "display_name": row.display_name,
                "email": row.primary_email,
                "phone": row.primary_phone,
                "organization": row.organization_name,
            }
            text_score = score_text_match(query, *fields.values(), exact=exact_match)
            if text_score <= 0:
                continue
            recency = score_recency(row.updated_at)
            combined, rel, rec, _ = compute_combined_score(
                text_score=text_score,
                recency_score=recency,
                is_favorite=bool(row.is_favorite),
                is_pinned=bool(row.is_pinned),
            )
            hits.append(
                InternalCrmSearchHit(
                    entity_type="crm_contact",
                    entity_id=row.id,
                    title=row.display_name,
                    subtitle=row.primary_email or row.primary_phone,
                    description=row.notes,
                    preview=build_snippet(row.notes or row.organization_name or "", query),
                    entity_status=_enum_val(row.status),
                    owner_id=row.owner_user_id,
                    tags=row.tags or [],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    last_activity_at=row.last_contact_at,
                    score=combined,
                    relevance_score=rel,
                    recency_score=rec,
                    matched_fields=_collect_matched(query, fields),
                    is_favorite=bool(row.is_favorite),
                    metadata={"contact_type": _enum_val(row.contact_type)},
                )
            )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]

    def _search_companies(
        self, db: Session, query: str, *, limit: int, include_archived: bool, exact_match: bool
    ) -> list[InternalCrmSearchHit]:
        pattern = _pattern(query)
        stmt = select(CrmCompany)
        if not include_archived:
            stmt = stmt.where(CrmCompany.archived_at.is_(None))
        if self._use_fts(db):
            stmt = stmt.where(text("search_vector @@ plainto_tsquery('simple', :q)").bindparams(q=query.strip()))
        else:
            stmt = stmt.where(
                or_(
                    CrmCompany.display_name.ilike(pattern),
                    CrmCompany.legal_name.ilike(pattern),
                    CrmCompany.trade_name.ilike(pattern),
                    CrmCompany.primary_email.ilike(pattern),
                    CrmCompany.domain.ilike(pattern),
                    CrmCompany.registration_number.ilike(pattern),
                )
            )
        rows = db.scalars(stmt.limit(limit * 2)).all()
        hits: list[InternalCrmSearchHit] = []
        for row in rows:
            fields = {
                "display_name": row.display_name,
                "legal_name": row.legal_name,
                "domain": row.domain,
                "email": row.primary_email,
            }
            text_score = score_text_match(query, *fields.values(), exact=exact_match)
            if text_score <= 0:
                continue
            recency = score_recency(row.updated_at)
            combined, rel, rec, _ = compute_combined_score(text_score=text_score, recency_score=recency, is_pinned=bool(row.is_pinned))
            hits.append(
                InternalCrmSearchHit(
                    entity_type="crm_company",
                    entity_id=row.id,
                    title=row.display_name,
                    subtitle=row.legal_name or row.domain,
                    description=row.description,
                    preview=build_snippet(row.description or "", query),
                    entity_status=_enum_val(row.status),
                    owner_id=row.owner_user_id,
                    tags=row.tags or [],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    score=combined,
                    relevance_score=rel,
                    recency_score=rec,
                    matched_fields=_collect_matched(query, fields),
                    is_pinned=bool(row.is_pinned),
                )
            )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]

    def _search_relationships(
        self, db: Session, query: str, *, limit: int, include_archived: bool, exact_match: bool
    ) -> list[InternalCrmSearchHit]:
        pattern = _pattern(query)
        stmt = select(CrmRelationship)
        if not include_archived:
            stmt = stmt.where(CrmRelationship.archived_at.is_(None))
        stmt = stmt.where(or_(CrmRelationship.relationship_type.ilike(pattern), CrmRelationship.notes.ilike(pattern)))
        rows = db.scalars(stmt.limit(limit * 2)).all()
        hits: list[InternalCrmSearchHit] = []
        for row in rows:
            fields = {"relationship_type": row.relationship_type, "notes": row.notes}
            text_score = score_text_match(query, *fields.values(), exact=exact_match)
            if text_score <= 0:
                continue
            from investhome_api.services.crm.search_ranking import score_relationship_strength

            rel_score = score_relationship_strength(_enum_val(row.strength))
            recency = score_recency(row.updated_at)
            combined, rel, rec, rs = compute_combined_score(
                text_score=text_score, recency_score=recency, relationship_score=rel_score
            )
            hits.append(
                InternalCrmSearchHit(
                    entity_type="crm_relationship",
                    entity_id=row.id,
                    title=row.relationship_type,
                    subtitle=_enum_val(row.category),
                    description=row.notes,
                    preview=build_snippet(row.notes or "", query),
                    entity_status=_enum_val(row.status),
                    owner_id=row.owner_user_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    score=combined,
                    relevance_score=rel,
                    recency_score=rec,
                    relationship_score=rs,
                    matched_fields=_collect_matched(query, fields),
                )
            )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]

    def _search_activities(
        self, db: Session, query: str, *, limit: int, include_archived: bool, exact_match: bool
    ) -> list[InternalCrmSearchHit]:
        pattern = _pattern(query)
        stmt = select(CrmActivity).where(CrmActivity.archived_at.is_(None))
        if self._use_fts(db):
            stmt = stmt.where(text("search_vector @@ plainto_tsquery('simple', :q)").bindparams(q=query.strip()))
        else:
            stmt = stmt.where(
                or_(
                    CrmActivity.title.ilike(pattern),
                    CrmActivity.summary.ilike(pattern),
                    CrmActivity.description.ilike(pattern),
                )
            )
        rows = db.scalars(stmt.limit(limit * 2)).all()
        hits: list[InternalCrmSearchHit] = []
        for row in rows:
            fields = {"title": row.title, "summary": row.summary, "description": row.description}
            text_score = score_text_match(query, *fields.values(), exact=exact_match)
            if text_score <= 0:
                continue
            recency = score_recency(row.updated_at)
            combined, rel, rec, _ = compute_combined_score(
                text_score=text_score, recency_score=recency, is_favorite=bool(row.is_favorite)
            )
            hits.append(
                InternalCrmSearchHit(
                    entity_type="crm_activity",
                    entity_id=row.id,
                    title=row.title,
                    subtitle=row.summary,
                    description=row.description,
                    preview=build_snippet(row.description or row.summary or "", query),
                    entity_status=_enum_val(row.status),
                    owner_id=row.owner_id,
                    tags=row.tags or [],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    score=combined,
                    relevance_score=rel,
                    recency_score=rec,
                    matched_fields=_collect_matched(query, fields),
                    is_favorite=bool(row.is_favorite),
                    metadata={"activity_type": _enum_val(row.activity_type)},
                )
            )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]

    def _search_communications(
        self, db: Session, query: str, *, limit: int, include_archived: bool, exact_match: bool
    ) -> list[InternalCrmSearchHit]:
        pattern = _pattern(query)
        stmt = select(CrmCommunication).where(CrmCommunication.archived_at.is_(None))
        stmt = stmt.where(
            or_(
                CrmCommunication.subject.ilike(pattern),
                CrmCommunication.preview.ilike(pattern),
                CrmCommunication.body_text.ilike(pattern),
            )
        )
        rows = db.scalars(stmt.limit(limit * 2)).all()
        hits: list[InternalCrmSearchHit] = []
        for row in rows:
            fields = {"subject": row.subject, "preview": row.preview}
            text_score = score_text_match(query, *fields.values(), exact=exact_match)
            if text_score <= 0:
                continue
            recency = score_recency(row.updated_at or row.sent_at)
            combined, rel, rec, _ = compute_combined_score(text_score=text_score, recency_score=recency)
            hits.append(
                InternalCrmSearchHit(
                    entity_type="crm_communication",
                    entity_id=row.id,
                    title=row.subject or row.preview or "Communication",
                    subtitle=_enum_val(row.channel),
                    preview=build_snippet(row.preview or "", query),
                    entity_status=_enum_val(row.status),
                    owner_id=row.owner_id,
                    tags=row.tags or [],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    score=combined,
                    relevance_score=rel,
                    recency_score=rec,
                    matched_fields=_collect_matched(query, fields),
                    metadata={"channel": _enum_val(row.channel), "direction": _enum_val(row.direction)},
                )
            )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]


def get_default_provider() -> CrmSearchProvider:
    return PostgresFtsCrmSearchProvider()


def hit_to_highlight_fields(query: str, matched: dict[str, str]) -> list[dict]:
    return [
        {
            "field": field,
            "snippet": build_snippet(value, query),
            "highlighted_html": build_highlight_html(value, query),
        }
        for field, value in matched.items()
    ]
