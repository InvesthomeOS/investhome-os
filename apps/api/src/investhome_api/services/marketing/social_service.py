"""Marketing social media service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_channel_communications import (
    ChannelApprovalStatus,
    ChannelReadinessState,
    DeliveryEventType,
    SocialAccount,
    SocialInboxItem,
    SocialNetwork,
    SocialPost,
    SocialPostStatus,
    SocialPostVariant,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.channel_shared_service import (
    check_readiness,
    compute_material_change_hash,
    create_send_operation,
    get_provider_status,
    record_delivery_event,
    record_idempotent_operation,
)
from investhome_api.services.marketing.providers.social import get_social_provider


def _get_post_or_404(db: Session, post_id: UUID) -> SocialPost:
    post = db.get(SocialPost, post_id)
    if post is None or post.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social post not found")
    return post


def list_social_accounts(db: Session, *, include_archived: bool = False) -> list[SocialAccount]:
    query = select(SocialAccount)
    if not include_archived:
        query = query.where(SocialAccount.archived_at.is_(None))
    return list(db.scalars(query.order_by(SocialAccount.display_name)).all())


def create_social_account(db: Session, user: User, payload: dict) -> SocialAccount:
    account = SocialAccount(
        network=SocialNetwork(payload["network"]),
        display_name=payload["display_name"],
        handle=payload.get("handle"),
        channel_id=payload.get("channel_id"),
        connection_status="not_connected",
        capabilities_json=payload.get("capabilities_json"),
        created_by_user_id=user.id,
    )
    db.add(account)
    db.flush()
    return account


def list_social_posts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
) -> tuple[list[SocialPost], int]:
    query = select(SocialPost).where(SocialPost.archived_at.is_(None))
    if status_filter:
        query = query.where(SocialPost.status == SocialPostStatus(status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(SocialPost.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_social_dashboard(db: Session) -> dict:
    total_posts = db.scalar(
        select(func.count()).where(SocialPost.archived_at.is_(None))
    ) or 0
    scheduled = db.scalar(
        select(func.count()).where(
            SocialPost.archived_at.is_(None),
            SocialPost.status == SocialPostStatus.SCHEDULED,
        )
    ) or 0
    accounts = db.scalar(
        select(func.count()).where(SocialAccount.archived_at.is_(None))
    ) or 0
    provider = get_provider_status("social")
    return {
        "total_posts": total_posts,
        "scheduled_posts": scheduled,
        "connected_accounts": accounts,
        "provider_status": provider,
    }


def create_social_post(db: Session, user: User, payload: dict) -> SocialPost:
    post = SocialPost(
        title=payload.get("title"),
        body_text=payload.get("body_text"),
        marketing_campaign_id=payload.get("marketing_campaign_id"),
        content_id=payload.get("content_id"),
        content_version_id=payload.get("content_version_id"),
        scheduled_at=payload.get("scheduled_at"),
        media_refs_json=payload.get("media_refs_json"),
        created_by_user_id=user.id,
    )
    db.add(post)
    db.flush()
    for variant in payload.get("variants", []):
        db.add(
            SocialPostVariant(
                post_id=post.id,
                social_account_id=variant["social_account_id"],
                network=SocialNetwork(variant["network"]),
                body_text=variant.get("body_text"),
                media_refs_json=variant.get("media_refs_json"),
            )
        )
    db.flush()
    return post


def get_social_post(db: Session, post_id: UUID) -> SocialPost:
    return _get_post_or_404(db, post_id)


def update_social_post(db: Session, user: User, post_id: UUID, payload: dict) -> SocialPost:
    post = _get_post_or_404(db, post_id)
    for field in ("title", "body_text", "scheduled_at", "media_refs_json", "content_id", "content_version_id"):
        if field in payload:
            setattr(post, field, payload[field])
    post.material_change_hash = compute_material_change_hash({
        "body": post.body_text,
        "content_version_id": str(post.content_version_id) if post.content_version_id else None,
    })
    if post.approval_status == ChannelApprovalStatus.APPROVED:
        post.approval_status = ChannelApprovalStatus.INVALIDATED
    post.updated_by_user_id = user.id
    db.flush()
    return post


def calculate_social_readiness(db: Session, post_id: UUID) -> dict:
    post = _get_post_or_404(db, post_id)
    result = check_readiness(
        db,
        channel="social",
        audience_id=None,
        content_id=post.content_id,
        content_version_id=post.content_version_id,
        approval_status=post.approval_status.value,
        scheduled_at=post.scheduled_at,
        provider_channel="social",
        require_audience=False,
    )
    post.readiness_state = ChannelReadinessState(result["state"])
    post.readiness_checks_json = result
    db.flush()
    return result


def schedule_social_post(
    db: Session,
    user: User,
    post_id: UUID,
    *,
    idempotency_key: str,
    scheduled_at: datetime | None = None,
) -> dict:
    existing = record_idempotent_operation(
        db,
        idempotency_key=idempotency_key,
        channel="social",
        operation="schedule",
        resource_type="social_post",
        resource_id=post_id,
        user=user,
    )
    if existing:
        return {"idempotent": True, **(existing.result_json or {})}

    post = _get_post_or_404(db, post_id)
    readiness = calculate_social_readiness(db, post_id)
    if readiness["state"] == ChannelReadinessState.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=readiness)

    provider = get_social_provider("linkedin")
    schedule_time = scheduled_at or post.scheduled_at or datetime.now(UTC)
    result = provider.schedule_post({"post_id": str(post_id), "body": post.body_text}, schedule_time)

    if result.get("scheduled"):
        post.status = SocialPostStatus.SCHEDULED
        post.scheduled_at = schedule_time
    else:
        post.status = SocialPostStatus.SCHEDULED
        post.scheduled_at = schedule_time
        record_delivery_event(
            db,
            channel="social",
            campaign_type="social_post",
            campaign_id=post_id,
            event_type=DeliveryEventType.NOT_CONNECTED,
            payload_json=result,
        )

    post.last_idempotency_key = idempotency_key
    op = create_send_operation(
        db,
        idempotency_key=idempotency_key,
        channel="social",
        operation="schedule",
        resource_type="social_post",
        resource_id=post_id,
        status_value="queued" if not result.get("scheduled") else "scheduled",
        result_json={**result, "provider_status": result.get("status")},
        user=user,
    )
    db.flush()
    return {"idempotent": False, "operation_id": str(op.id), **result}


def publish_social_post(db: Session, user: User, post_id: UUID, *, idempotency_key: str) -> dict:
    existing = record_idempotent_operation(
        db,
        idempotency_key=idempotency_key,
        channel="social",
        operation="publish",
        resource_type="social_post",
        resource_id=post_id,
        user=user,
    )
    if existing:
        return {"idempotent": True, **(existing.result_json or {})}

    post = _get_post_or_404(db, post_id)
    readiness = calculate_social_readiness(db, post_id)
    if readiness["state"] == ChannelReadinessState.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=readiness)

    provider = get_social_provider("linkedin")
    result = provider.publish_post({"post_id": str(post_id), "body": post.body_text})

    if result.get("published"):
        post.status = SocialPostStatus.PUBLISHED
        post.published_at = datetime.now(UTC)
        event_type = DeliveryEventType.PUBLISHED
    else:
        event_type = DeliveryEventType.NOT_CONNECTED

    record_delivery_event(
        db,
        channel="social",
        campaign_type="social_post",
        campaign_id=post_id,
        event_type=event_type,
        payload_json=result,
    )
    post.last_idempotency_key = idempotency_key
    op = create_send_operation(
        db,
        idempotency_key=idempotency_key,
        channel="social",
        operation="publish",
        resource_type="social_post",
        resource_id=post_id,
        status_value="not_connected" if not result.get("published") else "published",
        result_json=result,
        user=user,
    )
    db.flush()
    return {"idempotent": False, "operation_id": str(op.id), **result}


def list_social_inbox(db: Session, account_id: UUID | None = None) -> list[SocialInboxItem]:
    query = select(SocialInboxItem)
    if account_id:
        query = query.where(SocialInboxItem.social_account_id == account_id)
    return list(db.scalars(query.order_by(SocialInboxItem.received_at.desc()).limit(100)).all())


def sync_social_account(db: Session, account_id: UUID) -> dict:
    account = db.get(SocialAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    provider = get_social_provider(account.network.value)
    return provider.sync_account(str(account_id))
