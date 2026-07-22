"""Knowledge Hub service — extends Documents Workspace, never duplicates Document rows."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.knowledge_config import SEED_CATEGORIES
from investhome_api.models.document import Document, DocumentAnalysis, DocumentLink, ProcessingStatus
from investhome_api.models.document_intelligence import DocumentChunk
from investhome_api.models.knowledge import (
    KnowledgeCategory,
    KnowledgeCollection,
    KnowledgeCollectionItem,
    KnowledgeRetentionPolicy,
    KnowledgeReviewItem,
    KnowledgeSetting,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.knowledge import (
    KnowledgeAiSearchHit,
    KnowledgeAiSearchResponse,
    KnowledgeCategoryCreate,
    KnowledgeCategoryResponse,
    KnowledgeCollectionCreate,
    KnowledgeCollectionResponse,
    KnowledgeCollectionUpdate,
    KnowledgeFoundationPlaceholder,
    KnowledgeMetricValue,
    KnowledgeOverviewResponse,
    KnowledgePipelineStage,
    KnowledgePipelineStatusResponse,
    KnowledgeRetentionPolicyCreate,
    KnowledgeRetentionPolicyResponse,
    KnowledgeReviewItemResponse,
    KnowledgeSettingsResponse,
    KnowledgeSettingsUpdate,
)
from investhome_api.services.knowledge.adapters import (
    ai_capability,
    all_provider_statuses,
    indexing_capability,
    malware_capability,
    ocr_capability,
    vector_capability,
)


SETTINGS_KEY = "hub_defaults"


def ensure_seed_categories(db: Session) -> None:
    existing = {c.code for c in db.scalars(select(KnowledgeCategory)).all()}
    for idx, item in enumerate(SEED_CATEGORIES):
        if item["code"] in existing:
            continue
        db.add(
            KnowledgeCategory(
                id=uuid.uuid4(),
                code=item["code"],
                name_en=item["name_en"],
                name_tr=item["name_tr"],
                description=item.get("description"),
                sort_order=idx,
                is_active=True,
                is_system=True,
            )
        )
    db.flush()


def _metric(value: int | float | None, *, drilldown: str | None = None) -> KnowledgeMetricValue:
    return KnowledgeMetricValue(value=value, available=True, drilldown=drilldown)


def build_knowledge_overview(db: Session, user: User) -> KnowledgeOverviewResponse:
    ensure_seed_categories(db)

    base = select(func.count()).select_from(Document).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
    )
    total = int(db.scalar(base) or 0)

    recent_since = datetime.now(UTC) - timedelta(days=7)
    recent = int(
        db.scalar(base.where(Document.created_at >= recent_since)) or 0
    )

    awaiting = int(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeReviewItem)
            .where(KnowledgeReviewItem.status.in_(("open", "in_progress")))
        )
        or 0
    )

    expiring_before = (datetime.now(UTC) + timedelta(days=30)).date()
    expiring = int(
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.is_latest_version.is_(True),
                Document.archived_at.is_(None),
                Document.expiration_date.is_not(None),
                Document.expiration_date <= expiring_before,
            )
        )
        or 0
    )

    failed = int(
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.is_latest_version.is_(True),
                Document.archived_at.is_(None),
                Document.processing_status == ProcessingStatus.FAILED,
            )
        )
        or 0
    )

    has_link = exists(select(DocumentLink.id).where(DocumentLink.document_id == Document.id))
    unlinked = int(
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.is_latest_version.is_(True),
                Document.archived_at.is_(None),
                Document.project_id.is_(None),
                Document.investor_id.is_(None),
                Document.lead_id.is_(None),
                Document.transaction_id.is_(None),
                ~has_link,
            )
        )
        or 0
    )

    duplicates = int(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeReviewItem)
            .where(
                KnowledgeReviewItem.reason == "duplicate_candidate",
                KnowledgeReviewItem.status.in_(("open", "in_progress")),
            )
        )
        or 0
    )

    storage = int(
        db.scalar(
            select(func.coalesce(func.sum(Document.file_size), 0)).where(
                Document.is_latest_version.is_(True),
                Document.archived_at.is_(None),
            )
        )
        or 0
    )

    collections = int(db.scalar(select(func.count()).select_from(KnowledgeCollection)) or 0)

    return KnowledgeOverviewResponse(
        total_documents=_metric(total, drilldown="/dashboard/knowledge/documents"),
        recent_uploads=_metric(recent, drilldown="/dashboard/knowledge/documents?sort=recent"),
        awaiting_review=_metric(awaiting, drilldown="/dashboard/knowledge/review"),
        expiring_soon=_metric(expiring, drilldown="/dashboard/knowledge/retention"),
        failed_jobs=_metric(failed, drilldown="/dashboard/knowledge/review?reason=failed_processing"),
        unlinked=_metric(unlinked, drilldown="/dashboard/knowledge/review?reason=unlinked"),
        duplicate_candidates=_metric(
            duplicates, drilldown="/dashboard/knowledge/review?reason=duplicate_candidate"
        ),
        storage_used_bytes=_metric(storage, drilldown="/dashboard/knowledge/documents"),
        collections=_metric(collections, drilldown="/dashboard/knowledge/collections"),
        indexing_status=indexing_capability(),
        ocr_status=ocr_capability(),
        ai_status=ai_capability(),
        malware_scan_status=malware_capability(),
        vector_search_status=vector_capability(),
    )


def list_categories(db: Session) -> list[KnowledgeCategoryResponse]:
    ensure_seed_categories(db)
    rows = db.scalars(
        select(KnowledgeCategory).order_by(KnowledgeCategory.sort_order, KnowledgeCategory.code)
    ).all()
    return [KnowledgeCategoryResponse.model_validate(r) for r in rows]


def create_category(db: Session, body: KnowledgeCategoryCreate) -> KnowledgeCategoryResponse:
    ensure_seed_categories(db)
    code = body.code.strip().lower().replace(" ", "_")
    existing = db.scalar(select(KnowledgeCategory).where(KnowledgeCategory.code == code))
    if existing:
        raise ValueError("category_code_exists")
    row = KnowledgeCategory(
        id=uuid.uuid4(),
        code=code,
        name_en=body.name_en.strip(),
        name_tr=body.name_tr.strip(),
        description=body.description,
        sort_order=body.sort_order,
        is_active=True,
        is_system=False,
    )
    db.add(row)
    db.flush()
    return KnowledgeCategoryResponse.model_validate(row)


def list_collections(db: Session) -> list[KnowledgeCollectionResponse]:
    rows = db.scalars(
        select(KnowledgeCollection).order_by(KnowledgeCollection.updated_at.desc())
    ).all()
    return [KnowledgeCollectionResponse.model_validate(r) for r in rows]


def create_collection(
    db: Session, user: User, body: KnowledgeCollectionCreate
) -> KnowledgeCollectionResponse:
    rules = json.dumps(body.smart_rules) if body.smart_rules else None
    if body.collection_type == "smart" and not rules:
        rules = json.dumps({"folder": None, "category_code": None, "tags_contains": None})
    row = KnowledgeCollection(
        id=uuid.uuid4(),
        name=body.name.strip(),
        description=body.description,
        collection_type=body.collection_type if body.collection_type in ("manual", "smart") else "manual",
        smart_rules_json=rules,
        owner_user_id=user.id,
        is_shared=body.is_shared,
        document_count=0,
    )
    db.add(row)
    db.flush()
    if row.collection_type == "smart":
        refresh_smart_collection(db, row)
    return KnowledgeCollectionResponse.model_validate(row)


def update_collection(
    db: Session, collection_id: uuid.UUID, body: KnowledgeCollectionUpdate
) -> KnowledgeCollectionResponse:
    row = db.get(KnowledgeCollection, collection_id)
    if not row:
        raise LookupError("collection_not_found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.description is not None:
        row.description = body.description
    if body.is_shared is not None:
        row.is_shared = body.is_shared
    if body.smart_rules is not None:
        row.smart_rules_json = json.dumps(body.smart_rules)
        if row.collection_type == "smart":
            refresh_smart_collection(db, row)
    db.flush()
    return KnowledgeCollectionResponse.model_validate(row)


def add_document_to_collection(
    db: Session, collection_id: uuid.UUID, document_id: uuid.UUID, user: User
) -> KnowledgeCollectionResponse:
    row = db.get(KnowledgeCollection, collection_id)
    if not row:
        raise LookupError("collection_not_found")
    doc = db.get(Document, document_id)
    if not doc:
        raise LookupError("document_not_found")
    existing = db.scalar(
        select(KnowledgeCollectionItem).where(
            KnowledgeCollectionItem.collection_id == collection_id,
            KnowledgeCollectionItem.document_id == document_id,
        )
    )
    if not existing:
        db.add(
            KnowledgeCollectionItem(
                id=uuid.uuid4(),
                collection_id=collection_id,
                document_id=document_id,
                added_by_user_id=user.id,
                source="manual",
            )
        )
        row.document_count = int(row.document_count or 0) + 1
        db.flush()
    return KnowledgeCollectionResponse.model_validate(row)


def refresh_smart_collection(db: Session, collection: KnowledgeCollection) -> None:
    """Apply simple smart rules: folder / category_code / tags_contains."""
    rules: dict = {}
    if collection.smart_rules_json:
        try:
            rules = json.loads(collection.smart_rules_json)
        except json.JSONDecodeError:
            rules = {}

    q = select(Document.id).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
    )
    if rules.get("folder"):
        q = q.where(Document.folder == rules["folder"])
    if rules.get("category_code"):
        q = q.where(
            or_(
                Document.category_code == rules["category_code"],
                Document.category == rules["category_code"],
            )
        )
    if rules.get("tags_contains"):
        q = q.where(Document.tags.ilike(f"%{rules['tags_contains']}%"))

    doc_ids = list(db.scalars(q.limit(500)).all())
    # Clear auto items then re-add
    existing = db.scalars(
        select(KnowledgeCollectionItem).where(
            KnowledgeCollectionItem.collection_id == collection.id,
            KnowledgeCollectionItem.source == "smart",
        )
    ).all()
    for item in existing:
        db.delete(item)
    db.flush()

    for doc_id in doc_ids:
        already = db.scalar(
            select(KnowledgeCollectionItem).where(
                KnowledgeCollectionItem.collection_id == collection.id,
                KnowledgeCollectionItem.document_id == doc_id,
            )
        )
        if already:
            continue
        db.add(
            KnowledgeCollectionItem(
                id=uuid.uuid4(),
                collection_id=collection.id,
                document_id=doc_id,
                source="smart",
            )
        )
    count = int(
        db.scalar(
            select(func.count())
            .select_from(KnowledgeCollectionItem)
            .where(KnowledgeCollectionItem.collection_id == collection.id)
        )
        or 0
    )
    collection.document_count = count
    db.flush()


def sync_review_queue(db: Session) -> int:
    """Enqueue review items for common quality issues (idempotent)."""
    created = 0
    now = datetime.now(UTC)

    # Failed processing
    failed_docs = db.scalars(
        select(Document).where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            Document.processing_status == ProcessingStatus.FAILED,
        ).limit(100)
    ).all()
    for doc in failed_docs:
        created += _ensure_review(db, doc.id, "failed_processing", f"Processing failed for {doc.title}")

    # Unlinked
    has_link = exists(select(DocumentLink.id).where(DocumentLink.document_id == Document.id))
    unlinked_docs = db.scalars(
        select(Document)
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            Document.project_id.is_(None),
            Document.investor_id.is_(None),
            Document.lead_id.is_(None),
            Document.transaction_id.is_(None),
            ~has_link,
        )
        .limit(100)
    ).all()
    for doc in unlinked_docs:
        created += _ensure_review(db, doc.id, "unlinked", "Document has no entity links")

    # Missing metadata
    missing = db.scalars(
        select(Document)
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            or_(Document.category_code.is_(None), Document.tags.is_(None), Document.description.is_(None)),
        )
        .limit(100)
    ).all()
    for doc in missing:
        created += _ensure_review(db, doc.id, "missing_metadata", "Category, tags, or description missing")

    # Low confidence classification
    analyses = db.scalars(
        select(DocumentAnalysis)
        .where(DocumentAnalysis.classification_confidence.in_(("low", "very_low", "0.3", "0.2", "0.1")))
        .limit(100)
    ).all()
    for analysis in analyses:
        created += _ensure_review(
            db,
            analysis.document_id,
            "low_confidence",
            "AI classification confidence is low",
            confidence=analysis.classification_confidence,
        )

    # Duplicate candidates by checksum (same checksum, different ids)
    checksum_rows = db.execute(
        select(Document.checksum, func.count())
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            Document.checksum.is_not(None),
        )
        .group_by(Document.checksum)
        .having(func.count() > 1)
        .limit(50)
    ).all()
    for checksum, _count in checksum_rows:
        docs = db.scalars(
            select(Document).where(
                Document.checksum == checksum,
                Document.is_latest_version.is_(True),
                Document.archived_at.is_(None),
            )
        ).all()
        for doc in docs:
            created += _ensure_review(
                db,
                doc.id,
                "duplicate_candidate",
                f"Duplicate checksum candidate ({len(docs)} files)",
            )

    # Expiring soon
    expiring_before = (now + timedelta(days=30)).date()
    expiring_docs = db.scalars(
        select(Document)
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            Document.expiration_date.is_not(None),
            Document.expiration_date <= expiring_before,
        )
        .limit(100)
    ).all()
    for doc in expiring_docs:
        created += _ensure_review(
            db,
            doc.id,
            "expiring",
            f"Expires on {doc.expiration_date.isoformat() if doc.expiration_date else 'unknown'}",
            priority="high",
        )

    db.flush()
    return created


def _ensure_review(
    db: Session,
    document_id: uuid.UUID,
    reason: str,
    details: str,
    *,
    confidence: str | None = None,
    priority: str = "normal",
) -> int:
    existing = db.scalar(
        select(KnowledgeReviewItem).where(
            KnowledgeReviewItem.document_id == document_id,
            KnowledgeReviewItem.reason == reason,
            KnowledgeReviewItem.status.in_(("open", "in_progress")),
        )
    )
    if existing:
        return 0
    db.add(
        KnowledgeReviewItem(
            id=uuid.uuid4(),
            document_id=document_id,
            reason=reason,
            status="open",
            priority=priority,
            details=details,
            confidence_score=confidence,
        )
    )
    doc = db.get(Document, document_id)
    if doc and not doc.review_status:
        doc.review_status = "pending_review"
    return 1


def list_review_items(
    db: Session,
    *,
    status: str | None = None,
    reason: str | None = None,
    limit: int = 50,
) -> list[KnowledgeReviewItemResponse]:
    sync_review_queue(db)
    q = select(KnowledgeReviewItem).order_by(KnowledgeReviewItem.created_at.desc())
    if status:
        q = q.where(KnowledgeReviewItem.status == status)
    else:
        q = q.where(KnowledgeReviewItem.status.in_(("open", "in_progress")))
    if reason:
        q = q.where(KnowledgeReviewItem.reason == reason)
    rows = db.scalars(q.limit(limit)).all()
    out: list[KnowledgeReviewItemResponse] = []
    for row in rows:
        doc = db.get(Document, row.document_id)
        item = KnowledgeReviewItemResponse.model_validate(row)
        item.document_title = doc.title if doc else None
        out.append(item)
    return out


def resolve_review_item(
    db: Session,
    item_id: uuid.UUID,
    user: User,
    status: str,
    notes: str | None,
) -> KnowledgeReviewItemResponse:
    row = db.get(KnowledgeReviewItem, item_id)
    if not row:
        raise LookupError("review_not_found")
    if status not in ("resolved", "dismissed"):
        raise ValueError("invalid_status")
    row.status = status
    row.resolved_by_user_id = user.id
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = notes
    doc = db.get(Document, row.document_id)
    if doc:
        remaining = db.scalar(
            select(func.count())
            .select_from(KnowledgeReviewItem)
            .where(
                KnowledgeReviewItem.document_id == doc.id,
                KnowledgeReviewItem.status.in_(("open", "in_progress")),
                KnowledgeReviewItem.id != row.id,
            )
        )
        if not remaining:
            doc.review_status = "reviewed"
    db.flush()
    resp = KnowledgeReviewItemResponse.model_validate(row)
    resp.document_title = doc.title if doc else None
    return resp


def list_retention_policies(db: Session) -> list[KnowledgeRetentionPolicyResponse]:
    rows = db.scalars(
        select(KnowledgeRetentionPolicy).order_by(KnowledgeRetentionPolicy.name)
    ).all()
    return [KnowledgeRetentionPolicyResponse.model_validate(r) for r in rows]


def create_retention_policy(
    db: Session, body: KnowledgeRetentionPolicyCreate
) -> KnowledgeRetentionPolicyResponse:
    row = KnowledgeRetentionPolicy(
        id=uuid.uuid4(),
        name=body.name.strip(),
        description=body.description,
        category_code=body.category_code,
        retention_days=body.retention_days,
        action_on_expiry=body.action_on_expiry if body.action_on_expiry in ("notify", "archive", "review") else "notify",
        is_active=True,
        legal_hold_capable=body.legal_hold_capable,
    )
    db.add(row)
    db.flush()
    return KnowledgeRetentionPolicyResponse.model_validate(row)


def ai_search(db: Session, query: str, limit: int = 20) -> KnowledgeAiSearchResponse:
    """Citation-grounded search over document chunks + titles. Vector optional."""
    vector = vector_capability()
    ai = ai_capability()
    q = query.strip()
    pattern = f"%{q}%"

    hits: list[KnowledgeAiSearchHit] = []

    # Keyword over titles / tags / description
    docs = db.scalars(
        select(Document)
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            or_(
                Document.title.ilike(pattern),
                Document.tags.ilike(pattern),
                Document.description.ilike(pattern),
                Document.original_file_name.ilike(pattern),
            ),
        )
        .limit(limit)
    ).all()

    seen: set[uuid.UUID] = set()
    for doc in docs:
        seen.add(doc.id)
        analysis = db.scalar(
            select(DocumentAnalysis).where(DocumentAnalysis.document_id == doc.id)
        )
        hits.append(
            KnowledgeAiSearchHit(
                document_id=doc.id,
                title=doc.title,
                snippet=(doc.description or doc.original_file_name or "")[:280],
                citation=None,
                page=None,
                score=1.0,
                source="keyword",
                ai_summary=analysis.ai_summary if analysis else None,
            )
        )

    # Chunk-based citation search (source_reference may include page/range)
    remaining = max(0, limit - len(hits))
    if remaining:
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.content.ilike(pattern))
            .limit(remaining * 2)
        ).all()
        for chunk in chunks:
            if chunk.document_id in seen:
                continue
            doc = db.get(Document, chunk.document_id)
            if not doc or not doc.is_latest_version or doc.archived_at:
                continue
            seen.add(doc.id)
            citation = chunk.source_reference
            page: int | None = None
            if citation:
                # Parse "page N" style references when present
                match = re.search(r"page\s+(\d+)", citation, re.IGNORECASE)
                if match:
                    page = int(match.group(1))
            analysis = None
            if chunk.analysis_id:
                analysis = db.get(DocumentAnalysis, chunk.analysis_id)
            hits.append(
                KnowledgeAiSearchHit(
                    document_id=doc.id,
                    title=doc.title,
                    snippet=(chunk.content or "")[:280],
                    citation=citation,
                    page=page,
                    score=0.8,
                    source="chunk",
                    ai_summary=analysis.ai_summary if analysis else None,
                )
            )
            if len(hits) >= limit:
                break

    note = None
    if not vector.available:
        note = "Vector semantic search unavailable — results use keyword and chunk matching with citations when available."
    if not ai.available and note:
        note += " AI provider not configured; summaries shown only when previously stored."

    return KnowledgeAiSearchResponse(
        query=q,
        hits=hits[:limit],
        provider=vector if vector.available else ai,
        note=note,
    )


def get_settings(db: Session) -> KnowledgeSettingsResponse:
    row = db.scalar(select(KnowledgeSetting).where(KnowledgeSetting.key == SETTINGS_KEY))
    data: dict = {}
    if row and row.value_json:
        try:
            data = json.loads(row.value_json)
        except json.JSONDecodeError:
            data = {}
    providers = all_provider_statuses()
    return KnowledgeSettingsResponse(
        auto_enqueue_review_on_low_confidence=bool(data.get("auto_enqueue_review_on_low_confidence", True)),
        expiration_alert_days=int(data.get("expiration_alert_days", 30)),
        enable_duplicate_detection=bool(data.get("enable_duplicate_detection", True)),
        vector_indexing_enabled=providers["vector"].available,
        malware_scanning_enabled=providers["malware"].available,
        providers=providers,
        placeholders={
            "templates": "Document templates — foundation placeholder",
            "document_requests": "Document request workflows — foundation placeholder",
            "comments": "Document comments — foundation placeholder",
            "external_sharing": "Secure external sharing — requires EXTERNAL_SHARE_SIGNING_KEY",
            "legal_hold": "Legal hold flag on documents — UI foundation ready",
            "website_publish": "publish_to_website flag — public site integration pending",
            "comparison": "Version comparison UI — uses existing version chain",
            "malware": "Malware scan status — requires MALWARE_SCAN_* env",
        },
    )


def update_settings(db: Session, body: KnowledgeSettingsUpdate) -> KnowledgeSettingsResponse:
    row = db.scalar(select(KnowledgeSetting).where(KnowledgeSetting.key == SETTINGS_KEY))
    data: dict = {}
    if row and row.value_json:
        try:
            data = json.loads(row.value_json)
        except json.JSONDecodeError:
            data = {}
    if body.auto_enqueue_review_on_low_confidence is not None:
        data["auto_enqueue_review_on_low_confidence"] = body.auto_enqueue_review_on_low_confidence
    if body.expiration_alert_days is not None:
        data["expiration_alert_days"] = body.expiration_alert_days
    if body.enable_duplicate_detection is not None:
        data["enable_duplicate_detection"] = body.enable_duplicate_detection
    if not row:
        row = KnowledgeSetting(id=uuid.uuid4(), key=SETTINGS_KEY, value_json=json.dumps(data))
        db.add(row)
    else:
        row.value_json = json.dumps(data)
    db.flush()
    return get_settings(db)


def pipeline_status(db: Session) -> KnowledgePipelineStatusResponse:
    stages_def = [
        ("uploaded", "Uploaded"),
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("extracting_text", "Extracting text"),
        ("running_ocr", "OCR"),
        ("classifying", "Classifying"),
        ("analyzing", "Analyzing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("not_supported", "Not supported"),
    ]
    stages: list[KnowledgePipelineStage] = []
    for stage, label in stages_def:
        try:
            status_enum = ProcessingStatus(stage)
        except ValueError:
            continue
        count = int(
            db.scalar(
                select(func.count())
                .select_from(Document)
                .where(
                    Document.is_latest_version.is_(True),
                    Document.archived_at.is_(None),
                    Document.processing_status == status_enum,
                )
            )
            or 0
        )
        health = "healthy"
        if stage == "failed" and count:
            health = "attention"
        if stage == "running_ocr" and not ocr_capability().available:
            health = "unavailable"
        stages.append(
            KnowledgePipelineStage(stage=stage, label=label, count=count, status=health)
        )
    return KnowledgePipelineStatusResponse(
        stages=stages,
        automation_hook="/automation",
        note="Document processing jobs surface in Automation Center health when workers are registered.",
    )


def foundation_placeholders() -> list[KnowledgeFoundationPlaceholder]:
    return [
        KnowledgeFoundationPlaceholder(
            feature="templates",
            status="placeholder",
            description="Reusable document templates with metadata defaults.",
            required_env=[],
            endpoints=["GET /knowledge/placeholders"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="document_requests",
            status="placeholder",
            description="Request documents from counterparties with due dates.",
            required_env=[],
            endpoints=["GET /knowledge/placeholders"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="comments",
            status="placeholder",
            description="Threaded comments on documents (audit-logged).",
            required_env=[],
            endpoints=["GET /knowledge/placeholders"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="external_sharing",
            status="placeholder",
            description="Time-limited secure external share links.",
            required_env=["EXTERNAL_SHARE_SIGNING_KEY", "EXTERNAL_SHARE_BASE_URL"],
            endpoints=["POST /knowledge/shares (planned)"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="legal_hold",
            status="foundation",
            description="legal_hold boolean on Document — enforce retention overrides.",
            required_env=[],
            endpoints=["PATCH /documents/{id}"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="website_publish",
            status="foundation",
            description="publish_to_website flag — public website sync pending.",
            required_env=["PUBLIC_WEBSITE_API_URL"],
            endpoints=["PATCH /documents/{id}"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="version_comparison",
            status="placeholder",
            description="Side-by-side version compare UI over existing version chain.",
            required_env=[],
            endpoints=["GET /documents/{id}/versions"],
        ),
        KnowledgeFoundationPlaceholder(
            feature="malware_scan",
            status="unavailable" if not malware_capability().available else "ready",
            description="Malware scan status column; scanning runs only when provider configured.",
            required_env=["MALWARE_SCAN_PROVIDER", "MALWARE_SCAN_ENDPOINT", "MALWARE_SCAN_API_KEY"],
            endpoints=["POST /documents"],
        ),
    ]
