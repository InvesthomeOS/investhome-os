"""Marketing content studio API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.marketing import MarketingApproval
from investhome_api.models.marketing_content_studio import ContentTranslation, ContentVariant
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_content_studio import (
    AIGenerationRequest,
    AIGenerationReview,
    ComplianceCheckRequest,
    ContentApprovalAction,
    ContentBriefUpdate,
    ContentCreate,
    ContentEntityLink,
    ContentStatusTransition,
    ContentTranslationCreate,
    ContentUpdate,
    ContentVariantCreate,
    ContentVersionCreate,
    FieldRegistryEntry,
    PublishingReadinessResponse,
)
from investhome_api.services.marketing.ai_content_service import (
    ai_provider_available,
    request_ai_generation,
    review_ai_generation,
)
from investhome_api.services.marketing.content_service import (
    approve_content,
    check_publishing_readiness,
    create_content,
    create_content_version,
    get_content,
    get_content_brief,
    get_field_registry,
    link_entity_to_content,
    list_content_versions,
    list_contents,
    paginate,
    submit_content_approval,
    transition_content_status,
    unlink_entity_from_content,
    update_content,
    update_content_brief,
    content_dashboard_summary,
)
from investhome_api.services.marketing.content_status_service import get_allowed_content_transitions
from investhome_api.services.marketing.content_studio_serializers import (
    ai_record_dict,
    approval_dict,
    brief_dict,
    content_dict,
    translation_dict,
    variant_dict,
    version_dict,
)

router = APIRouter(prefix="/marketing/content", tags=["marketing-content"])


@router.get("/dashboard")
def content_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    return content_dashboard_summary(db)


@router.get("")
def list_content(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    content_type: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> dict:
    items, total = list_contents(
        db, page=page, page_size=page_size, status_filter=status_filter,
        content_type=content_type, search=search, include_archived=include_archived,
    )
    return paginate(items, total, page, page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_content_route(
    body: ContentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = create_content(db, payload=body.model_dump(), actor=user)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content)}


@router.get("/field-registry", response_model=list[FieldRegistryEntry])
def field_registry(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
    content_type: str | None = None,
) -> list:
    return get_field_registry(db, content_type)


@router.get("/calendar")
def content_calendar(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
) -> dict:
    from investhome_api.models.marketing_content_studio import MarketingContent

    rows = db.scalars(
        select(MarketingContent)
        .where(MarketingContent.scheduled_at.is_not(None), MarketingContent.archived_at.is_(None))
        .order_by(MarketingContent.scheduled_at)
    ).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "status": r.status.value,
                "scheduled_at": r.scheduled_at,
                "published_at": r.published_at,
                "content_type": r.content_type,
            }
            for r in rows
        ]
    }


@router.get("/{content_id}")
def get_content_route(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    return content_dict(content)


@router.put("/{content_id}")
def update_content_route(
    content_id: UUID,
    body: ContentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    update_content(db, content, payload=body.model_dump(exclude_unset=True), actor=user)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content)}


@router.post("/{content_id}/transition")
def transition_content(
    content_id: UUID,
    body: ContentStatusTransition,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    transition_content_status(db, content, target_status=body.target_status, actor=user)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content), "allowed_transitions": get_allowed_content_transitions(content.status.value)}


@router.get("/{content_id}/transitions")
def content_transitions(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    return {"current_status": content.status.value, "allowed": get_allowed_content_transitions(content.status.value)}


@router.get("/{content_id}/readiness", response_model=PublishingReadinessResponse)
def publishing_readiness(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    return check_publishing_readiness(db, content)


@router.get("/{content_id}/brief")
def get_brief(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    brief = get_content_brief(db, content_id)
    return {"brief": brief_dict(brief)}


@router.put("/{content_id}/brief")
def update_brief(
    content_id: UUID,
    body: ContentBriefUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    brief = get_content_brief(db, content_id)
    update_content_brief(db, brief, payload=body.model_dump(exclude_unset=True), actor=user)
    db.commit()
    db.refresh(brief)
    return {"brief": brief_dict(brief)}


@router.get("/{content_id}/versions")
def list_versions(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    versions = list_content_versions(db, content_id)
    return {"items": [version_dict(v) for v in versions]}


@router.post("/{content_id}/versions", status_code=status.HTTP_201_CREATED)
def create_version(
    content_id: UUID,
    body: ContentVersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    version = create_content_version(db, content, payload=body.model_dump(), actor=user)
    db.commit()
    db.refresh(version)
    return {"version": version_dict(version)}


@router.get("/{content_id}/variants")
def list_variants(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    variants = db.scalars(select(ContentVariant).where(ContentVariant.content_id == content_id)).all()
    return {"items": [variant_dict(v) for v in variants]}


@router.post("/{content_id}/variants", status_code=status.HTTP_201_CREATED)
def create_variant(
    content_id: UUID,
    body: ContentVariantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    variant = ContentVariant(content_id=content_id, **body.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return {"variant": variant_dict(variant)}


@router.get("/{content_id}/translations")
def list_translations(
    content_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    items = db.scalars(select(ContentTranslation).where(ContentTranslation.content_id == content_id)).all()
    return {"items": [translation_dict(t) for t in items]}


@router.post("/{content_id}/translations", status_code=status.HTTP_201_CREATED)
def create_translation(
    content_id: UUID,
    body: ContentTranslationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    translation = ContentTranslation(content_id=content_id, **body.model_dump())
    db.add(translation)
    db.commit()
    db.refresh(translation)
    return {"translation": translation_dict(translation)}


@router.post("/{content_id}/link")
def link_entity(
    content_id: UUID,
    body: ContentEntityLink,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    link_entity_to_content(content, entity_type=body.entity_type, entity_id=body.entity_id)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content)}


@router.post("/{content_id}/unlink")
def unlink_entity(
    content_id: UUID,
    body: ContentEntityLink,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    unlink_entity_from_content(content, entity_type=body.entity_type, entity_id=body.entity_id)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content)}


@router.post("/{content_id}/submit-approval")
def submit_approval(
    content_id: UUID,
    body: ContentApprovalAction | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    content = get_content(db, content_id)
    version_id = body.version_id if body else None
    approval = submit_content_approval(db, content, actor=user, version_id=version_id)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content), "approval": approval_dict(approval)}


@router.post("/{content_id}/approve")
def approve_content_route(
    content_id: UUID,
    body: ContentApprovalAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "approve_content")),
) -> dict:
    content = get_content(db, content_id)
    approval = db.scalar(
        select(MarketingApproval)
        .where(MarketingApproval.entity_type == "content", MarketingApproval.entity_id == content_id)
        .order_by(MarketingApproval.created_at.desc())
    )
    if approval is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No approval found")
    approve_content(db, content, approval, actor=user, notes=body.notes)
    db.commit()
    db.refresh(content)
    return {"content": content_dict(content), "approval": approval_dict(approval)}


@router.post("/{content_id}/ai/generate")
def ai_generate(
    content_id: UUID,
    body: AIGenerationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_content(db, content_id)
    record = request_ai_generation(
        db,
        content_id=content_id,
        version_id=body.version_id,
        prompt=body.prompt,
        context_json=body.context_json,
        actor=user,
    )
    db.commit()
    db.refresh(record)
    return {
        "record": ai_record_dict(record),
        "provider_available": ai_provider_available(),
        "requires_review": True,
        "auto_publish": False,
    }


@router.post("/ai/{record_id}/review")
def ai_review(
    record_id: UUID,
    body: AIGenerationReview,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "approve_content")),
) -> dict:
    from investhome_api.models.marketing_content_studio import AIContentGenerationRecord

    record = db.get(AIContentGenerationRecord, record_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="AI generation record not found")
    review_ai_generation(db, record, approved=body.approved, actor=user)
    db.commit()
    db.refresh(record)
    return {"record": ai_record_dict(record)}
