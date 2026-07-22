"""Marketing social media API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_channel_communications import (
    IdempotentSendRequest,
    ReadinessResponse,
    SendOperationResponse,
    SocialAccountCreate,
    SocialAccountResponse,
    SocialDashboardResponse,
    SocialInboxItemResponse,
    SocialPostCreate,
    SocialPostListResponse,
    SocialPostResponse,
    SocialPostUpdate,
)
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.social_service import (
    create_social_account,
    create_social_post,
    get_social_dashboard,
    get_social_post,
    list_social_accounts,
    list_social_inbox,
    list_social_posts,
    publish_social_post,
    schedule_social_post,
    sync_social_account,
    update_social_post,
)

router = APIRouter(prefix="/marketing/social", tags=["marketing-social"])


@router.get("/dashboard", response_model=SocialDashboardResponse)
def social_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view_dashboard")),
) -> dict:
    return get_social_dashboard(db)


@router.get("/accounts", response_model=list[SocialAccountResponse])
def get_accounts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> list:
    return list_social_accounts(db)


@router.post("/accounts", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED)
def post_account(
    payload: SocialAccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_provider_connections")),
) -> object:
    account = create_social_account(db, user, payload.model_dump())
    db.commit()
    db.refresh(account)
    return account


@router.post("/accounts/{account_id}/sync")
def post_account_sync(
    account_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "manage_provider_connections")),
) -> dict:
    return sync_social_account(db, account_id)


@router.get("/posts", response_model=SocialPostListResponse)
def get_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    items, total = list_social_posts(db, page=page, page_size=page_size, status_filter=status_filter)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": compute_pages(total, page_size),
    }


@router.post("/posts", response_model=SocialPostResponse, status_code=status.HTTP_201_CREATED)
def post_create_post(
    payload: SocialPostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> object:
    post = create_social_post(db, user, payload.model_dump())
    db.commit()
    db.refresh(post)
    return post


@router.get("/posts/{post_id}", response_model=SocialPostResponse)
def get_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> object:
    return get_social_post(db, post_id)


@router.patch("/posts/{post_id}", response_model=SocialPostResponse)
def patch_post(
    post_id: UUID,
    payload: SocialPostUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> object:
    post = update_social_post(db, user, post_id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/{post_id}/readiness", response_model=ReadinessResponse)
def post_readiness(
    post_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    from investhome_api.services.marketing.social_service import calculate_social_readiness
    return calculate_social_readiness(db, post_id)


@router.post("/posts/{post_id}/schedule", response_model=SendOperationResponse)
def post_schedule(
    post_id: UUID,
    payload: IdempotentSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    result = schedule_social_post(
        db, user, post_id,
        idempotency_key=payload.idempotency_key,
        scheduled_at=payload.scheduled_at,
    )
    db.commit()
    return result


@router.post("/posts/{post_id}/publish", response_model=SendOperationResponse)
def post_publish(
    post_id: UUID,
    payload: IdempotentSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    result = publish_social_post(db, user, post_id, idempotency_key=payload.idempotency_key)
    db.commit()
    return result


@router.get("/inbox", response_model=list[SocialInboxItemResponse])
def get_inbox(
    account_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> list:
    return list_social_inbox(db, account_id)
