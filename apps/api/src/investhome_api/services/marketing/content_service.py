"""Marketing content studio service — lifecycle, readiness, approvals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingApproval, MarketingApprovalStatus, MarketingApprovalType
from investhome_api.models.marketing_content_studio import (
    AssetRightsStatus,
    ContentTranslation,
    ContentTypeFieldRegistry,
    ContentVariant,
    ContentVersion,
    MarketingAsset,
    MarketingContent,
    MarketingContentBrief,
    MarketingContentStatus,
    PublishingReadinessState,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.content_status_service import (
    PUBLISHABLE_STATUSES,
    get_allowed_content_transitions,
    validate_content_status_transition,
)


def _to_summary(content: MarketingContent) -> dict:
    return {
        "id": str(content.id),
        "title": content.title,
        "code": content.code,
        "content_type": content.content_type,
        "format": content.format,
        "status": content.status.value,
        "owner_user_id": str(content.owner_user_id) if content.owner_user_id else None,
        "primary_language": content.primary_language,
        "scheduled_at": content.scheduled_at,
        "published_at": content.published_at,
        "tags": content.tags,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


def _to_detail(content: MarketingContent) -> dict:
    return {
        **_to_summary(content),
        "description": content.description,
        "team_id": content.team_id,
        "project_ids": content.project_ids,
        "property_ids": content.property_ids,
        "audience_ids": content.audience_ids,
        "campaign_ids": content.campaign_ids,
        "asset_ids": content.asset_ids,
        "channel_ids": content.channel_ids,
        "current_version_id": content.current_version_id,
        "expires_at": content.expires_at,
        "archived_at": content.archived_at,
    }


def get_content(db: Session, content_id: UUID, *, include_archived: bool = False) -> MarketingContent:
    content = db.get(MarketingContent, content_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if not include_archived and content.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return content


def list_contents(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    content_type: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> tuple[list[dict], int]:
    query = select(MarketingContent)
    if not include_archived:
        query = query.where(MarketingContent.archived_at.is_(None))
    if status_filter:
        query = query.where(MarketingContent.status == status_filter)
    if content_type:
        query = query.where(MarketingContent.content_type == content_type)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(MarketingContent.title.ilike(pattern), MarketingContent.code.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingContent.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [_to_summary(row) for row in rows], total


def create_content(db: Session, *, payload: dict, actor: User) -> MarketingContent:
    content = MarketingContent(
        title=payload["title"],
        code=payload.get("code"),
        description=payload.get("description"),
        content_type=payload.get("content_type", "other"),
        format=payload.get("format"),
        status=MarketingContentStatus.IDEA,
        owner_user_id=payload.get("owner_user_id") or actor.id,
        team_id=payload.get("team_id"),
        primary_language=payload.get("primary_language", "en"),
        project_ids=payload.get("project_ids"),
        property_ids=payload.get("property_ids"),
        audience_ids=payload.get("audience_ids"),
        campaign_ids=payload.get("campaign_ids"),
        channel_ids=payload.get("channel_ids"),
        tags=payload.get("tags"),
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(content)
    db.flush()
    brief = MarketingContentBrief(content_id=content.id, created_by_user_id=actor.id, updated_by_user_id=actor.id)
    db.add(brief)
    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        label="Initial",
        body_json=payload.get("body_json") or {},
        created_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    content.current_version_id = version.id
    return content


def update_content(db: Session, content: MarketingContent, *, payload: dict, actor: User) -> MarketingContent:
    for field in (
        "title", "code", "description", "content_type", "format", "owner_user_id", "team_id",
        "primary_language", "project_ids", "property_ids", "audience_ids", "campaign_ids",
        "asset_ids", "channel_ids", "scheduled_at", "expires_at", "tags",
    ):
        if field in payload:
            setattr(content, field, payload[field])
    content.updated_by_user_id = actor.id
    return content


def transition_content_status(
    db: Session, content: MarketingContent, *, target_status: str, actor: User
) -> MarketingContent:
    current = content.status.value
    validate_content_status_transition(current, target_status)
    if target_status == "published":
        readiness = check_publishing_readiness(db, content)
        if readiness["state"] == PublishingReadinessState.BLOCKED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Publishing blocked", "remediation": readiness["remediation"]},
            )
    content.status = MarketingContentStatus(target_status)
    content.updated_by_user_id = actor.id
    if target_status == "published":
        content.published_at = datetime.now(UTC)
    return content


def _has_pending_approval(db: Session, content_id: UUID, version_id: UUID | None) -> bool:
    query = select(MarketingApproval).where(
        MarketingApproval.entity_type == "content",
        MarketingApproval.entity_id == content_id,
        MarketingApproval.status.in_([MarketingApprovalStatus.PENDING, MarketingApprovalStatus.DRAFT]),
    )
    if version_id:
        query = query.where(
            or_(MarketingApproval.version_id == version_id, MarketingApproval.version_id.is_(None))
        )
    return db.scalar(select(func.count()).select_from(query.subquery())) > 0


def _has_approved_version(db: Session, content_id: UUID, version_id: UUID | None) -> bool:
    query = select(MarketingApproval).where(
        MarketingApproval.entity_type == "content",
        MarketingApproval.entity_id == content_id,
        MarketingApproval.status == MarketingApprovalStatus.APPROVED,
    )
    if version_id:
        query = query.where(MarketingApproval.version_id == version_id)
    return db.scalar(select(func.count()).select_from(query.subquery())) > 0


def check_publishing_readiness(db: Session, content: MarketingContent) -> dict:
    remediation: list[str] = []
    state = PublishingReadinessState.READY

    if content.current_version_id is None:
        remediation.append("Create at least one content version")
        state = PublishingReadinessState.BLOCKED

    version = db.get(ContentVersion, content.current_version_id) if content.current_version_id else None
    if version and not version.body_json:
        remediation.append("Current version has no content body")
        if state != PublishingReadinessState.BLOCKED:
            state = PublishingReadinessState.WARNING

    if _has_pending_approval(db, content.id, content.current_version_id):
        remediation.append("Pending approval must be completed before publishing")
        state = PublishingReadinessState.BLOCKED

    if content.status.value not in PUBLISHABLE_STATUSES and content.status.value != "published":
        if not _has_approved_version(db, content.id, content.current_version_id):
            remediation.append("Content must be approved before publishing")
            state = PublishingReadinessState.BLOCKED

    if content.asset_ids:
        for asset_id_str in content.asset_ids:
            try:
                asset_id = UUID(str(asset_id_str))
            except ValueError:
                continue
            asset = db.get(MarketingAsset, asset_id)
            if asset and asset.rights_status == AssetRightsStatus.UNKNOWN:
                remediation.append(f"Asset '{asset.name}' has unknown rights — cannot treat as cleared")
                state = PublishingReadinessState.BLOCKED
            elif asset and asset.rights_status == AssetRightsStatus.RESTRICTED:
                remediation.append(f"Asset '{asset.name}' has restricted rights")
                state = PublishingReadinessState.BLOCKED
            elif asset and asset.rights_status == AssetRightsStatus.EXPIRED:
                remediation.append(f"Asset '{asset.name}' rights have expired")
                state = PublishingReadinessState.BLOCKED

    variants = db.scalars(
        select(ContentVariant).where(ContentVariant.content_id == content.id)
    ).all()
    for variant in variants:
        if variant.validation_status == "invalid":
            remediation.append(f"Channel variant '{variant.variant_key}' failed validation")
            if state == PublishingReadinessState.READY:
                state = PublishingReadinessState.WARNING

    return {
        "state": state.value,
        "remediation": remediation,
        "content_id": str(content.id),
        "status": content.status.value,
    }


def get_content_brief(db: Session, content_id: UUID) -> MarketingContentBrief:
    brief = db.scalar(select(MarketingContentBrief).where(MarketingContentBrief.content_id == content_id))
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    return brief


def update_content_brief(db: Session, brief: MarketingContentBrief, *, payload: dict, actor: User) -> MarketingContentBrief:
    for field in (
        "objective", "target_audience", "key_messages", "tone_and_voice",
        "deliverables", "constraints", "success_criteria",
    ):
        if field in payload:
            setattr(brief, field, payload[field])
    brief.updated_by_user_id = actor.id
    return brief


def list_content_versions(db: Session, content_id: UUID) -> list[ContentVersion]:
    return list(
        db.scalars(
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.version_number.desc())
        ).all()
    )


def create_content_version(db: Session, content: MarketingContent, *, payload: dict, actor: User) -> ContentVersion:
    latest = db.scalar(
        select(func.max(ContentVersion.version_number)).where(ContentVersion.content_id == content.id)
    ) or 0
    version = ContentVersion(
        content_id=content.id,
        version_number=latest + 1,
        label=payload.get("label"),
        body_json=payload.get("body_json") or {},
        document_id=payload.get("document_id"),
        change_summary=payload.get("change_summary"),
        created_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    content.current_version_id = version.id
    content.updated_by_user_id = actor.id
    db.scalars(
        select(ContentTranslation).where(
            ContentTranslation.content_id == content.id,
            ContentTranslation.version_id != version.id,
        )
    )
    for translation in db.scalars(
        select(ContentTranslation).where(ContentTranslation.content_id == content.id)
    ).all():
        translation.is_outdated = True
    return version


def submit_content_approval(
    db: Session, content: MarketingContent, *, actor: User, version_id: UUID | None = None
) -> MarketingApproval:
    vid = version_id or content.current_version_id
    if _has_pending_approval(db, content.id, vid):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval already pending")
    approval = MarketingApproval(
        entity_type="content",
        entity_id=content.id,
        version_id=vid,
        approval_type=MarketingApprovalType.CONTENT,
        status=MarketingApprovalStatus.PENDING,
        requested_by_user_id=actor.id,
    )
    db.add(approval)
    if content.status.value in {"internal_review", "in_production", "draft"}:
        content.status = MarketingContentStatus.PENDING_APPROVAL
    content.updated_by_user_id = actor.id
    return approval


def approve_content(
    db: Session, content: MarketingContent, approval: MarketingApproval, *, actor: User, notes: str | None = None
) -> MarketingContent:
    if approval.status != MarketingApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval is not pending")
    approval.status = MarketingApprovalStatus.APPROVED
    approval.approved_by_user_id = actor.id
    approval.notes = notes
    content.status = MarketingContentStatus.APPROVED
    content.updated_by_user_id = actor.id
    return content


def link_entity_to_content(content: MarketingContent, *, entity_type: str, entity_id: UUID) -> MarketingContent:
    field_map = {
        "campaign": "campaign_ids",
        "project": "project_ids",
        "property": "property_ids",
        "audience": "audience_ids",
        "asset": "asset_ids",
    }
    field = field_map.get(entity_type)
    if field is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown entity type: {entity_type}")
    ids = list(getattr(content, field) or [])
    eid = str(entity_id)
    if eid not in ids:
        ids.append(eid)
    setattr(content, field, ids)
    return content


def unlink_entity_from_content(content: MarketingContent, *, entity_type: str, entity_id: UUID) -> MarketingContent:
    field_map = {
        "campaign": "campaign_ids",
        "project": "project_ids",
        "property": "property_ids",
        "audience": "audience_ids",
        "asset": "asset_ids",
    }
    field = field_map.get(entity_type)
    if field is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown entity type: {entity_type}")
    ids = [i for i in (getattr(content, field) or []) if str(i) != str(entity_id)]
    setattr(content, field, ids or None)
    return content


def get_field_registry(db: Session, content_type: str | None = None) -> list[ContentTypeFieldRegistry]:
    query = select(ContentTypeFieldRegistry).where(ContentTypeFieldRegistry.is_active.is_(True))
    if content_type:
        query = query.where(ContentTypeFieldRegistry.content_type == content_type)
    return list(db.scalars(query.order_by(ContentTypeFieldRegistry.sort_order)).all())


def content_dashboard_summary(db: Session) -> dict:
    total = db.scalar(
        select(func.count()).select_from(
            select(MarketingContent).where(MarketingContent.archived_at.is_(None)).subquery()
        )
    ) or 0
    by_status: dict[str, int] = {}
    for row in db.execute(
        select(MarketingContent.status, func.count())
        .where(MarketingContent.archived_at.is_(None))
        .group_by(MarketingContent.status)
    ).all():
        by_status[row[0].value if hasattr(row[0], "value") else str(row[0])] = row[1]
    return {"total": total, "by_status": by_status}


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }
