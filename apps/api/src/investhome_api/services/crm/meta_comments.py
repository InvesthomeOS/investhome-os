"""Facebook Page and Instagram Login comment inbound + public reply.

Does not create Leads or Opportunities. Does not copy media bytes.
Parent post/ad context is metadata/reference only (URLs may expire).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm.meta_send import (
    FACEBOOK_MESSAGES_URL,
    GRAPH_API_VERSION,
    GRAPH_TIMEOUT_SECONDS,
    MetaSendError,
    PUBLIC_EMPTY_MESSAGE,
    PUBLIC_UNKNOWN_CONTACT,
    PUBLIC_UNSUPPORTED_CHANNEL,
    _post_graph_messages,
    instagram_messages_url,
    require_instagram_credentials,
    require_page_access_token,
)
from investhome_api.services.crm.meta_webhook import (
    FACEBOOK_SOURCE,
    INSTAGRAM_IGSID_KEY,
    INSTAGRAM_SOURCE,
    _claim_keys,
    _dict,
    _facebook_psid_from_meta,
    _instagram_igsid_from_meta,
    _message_timestamp,
    _placeholder_instagram_name,
    _placeholder_name,
    _store_igsid,
    _store_psid,
    find_contact_by_facebook_psid,
    find_contact_by_instagram_igsid,
)

logger = get_logger("investhome.meta.comments")

COMMENT_KIND = "comment"
CONVERSATION_PREFIX = "cmt:"
FACEBOOK_COMMENTER_KEY = "facebook_commenter_id"
INSTAGRAM_COMMENTER_KEY = "instagram_commenter_id"
PUBLIC_COMMENT_NOT_CONFIGURED = "Comment reply is not configured"
PUBLIC_COMMENT_SEND_FAILED = "Comment reply could not be sent"
PUBLIC_COMMENT_UNAVAILABLE = "This comment cannot be replied to"
PUBLIC_PRIVATE_REPLY_UNAVAILABLE = "Private reply is not available for this comment"
PUBLIC_PRIVATE_REPLY_ALREADY_SENT = "A private reply was already sent for this comment"
PUBLIC_PRIVATE_REPLY_FAILED = "Private reply could not be sent"
PUBLIC_LIKE_UNSUPPORTED = "Liking comments is not supported for this platform"
PUBLIC_LIKE_FAILED = "Comment like could not be updated"
PUBLIC_CONTEXT_UNAVAILABLE = "Post preview is not available"
PRIVATE_REPLY_WINDOW = timedelta(days=7)
INSTAGRAM_LIKE_SUPPORTED = False
FACEBOOK_LIKE_SUPPORTED = True

SUPPORTED_CHANNELS = frozenset({"facebook", "instagram"})


@dataclass(frozen=True)
class MetaCommentInbound:
    comment_id: str
    commenter_id: str
    commenter_name: str | None
    text: str
    parent_id: str
    occurred_at: datetime | None
    platform: str
    account_id: str
    permalink: str | None
    media_product_type: str | None
    ad_id: str | None
    ad_title: str | None
    original_media_id: str | None
    is_published: bool | None
    promotion_status: str | None
    parent_comment_id: str | None


def comment_conversation_key(comment_id: str) -> str:
    return f"{CONVERSATION_PREFIX}{comment_id.strip()}"


def parse_comment_id(conversation_key: str | None) -> str | None:
    key = (conversation_key or "").strip()
    if key.startswith(CONVERSATION_PREFIX):
        comment_id = key[len(CONVERSATION_PREFIX) :].strip()
        return comment_id or None
    return None


def _graph_get(url: str, *, token: str, fields: str) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            url,
            params={"fields": fields},
            headers={"Authorization": f"Bearer {token}"},
            timeout=min(GRAPH_TIMEOUT_SECONDS, 8.0),
        )
    except httpx.HTTPError:
        logger.info("meta_comment_context_unavailable")
        return None
    if response.status_code >= 400:
        logger.info("meta_comment_context_unavailable status=%s", response.status_code)
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _graph_delete(url: str, *, token: str) -> httpx.Response | None:
    try:
        return httpx.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=min(GRAPH_TIMEOUT_SECONDS, 8.0),
        )
    except httpx.HTTPError:
        logger.info("meta_comment_like_transport_error")
        return None


def _clean_ctx(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None and value != ""}


def context_is_visible(ctx: dict[str, Any] | None) -> bool:
    if not isinstance(ctx, dict):
        return False
    return bool(str(ctx.get("preview_url") or "").strip() or str(ctx.get("caption") or "").strip())


def _merge_ctx(base: dict[str, Any] | None, extra: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base) if isinstance(base, dict) else {}
    if isinstance(extra, dict):
        for key, value in extra.items():
            if value is not None and value != "":
                merged[key] = value
    return _clean_ctx(merged)


def _reply_prefix(username: str | None) -> str | None:
    handle = str(username or "").strip().lstrip("@")
    if not handle or " " in handle:
        return None
    return f"@{handle} "


def _facebook_commenter_from_meta(meta: object) -> str | None:
    if not isinstance(meta, dict):
        return None
    direct = str(meta.get(FACEBOOK_COMMENTER_KEY) or "").strip()
    if direct:
        return direct
    nested = meta.get("facebook")
    if isinstance(nested, dict):
        return str(nested.get("commenter_id") or "").strip() or None
    return None


def _instagram_commenter_from_meta(meta: object) -> str | None:
    if not isinstance(meta, dict):
        return None
    direct = str(meta.get(INSTAGRAM_COMMENTER_KEY) or "").strip()
    if direct:
        return direct
    nested = meta.get("instagram")
    if isinstance(nested, dict):
        return str(nested.get("commenter_id") or "").strip() or None
    return None


def find_contact_by_facebook_commenter(db: Session, user_id: str) -> CrmContact | None:
    existing = find_contact_by_facebook_psid(db, user_id)
    if existing is not None:
        return existing
    contacts = list(db.scalars(select(CrmContact).where(CrmContact.archived_at.is_(None))).all())
    for contact in contacts:
        if _facebook_commenter_from_meta(contact.metadata_json) == user_id:
            return contact
    return None


def find_contact_by_instagram_commenter(db: Session, user_id: str) -> CrmContact | None:
    existing = find_contact_by_instagram_igsid(db, user_id)
    if existing is not None:
        return existing
    contacts = list(db.scalars(select(CrmContact).where(CrmContact.archived_at.is_(None))).all())
    for contact in contacts:
        if _instagram_commenter_from_meta(contact.metadata_json) == user_id:
            return contact
    return None


def _store_facebook_commenter(meta: dict[str, Any] | None, user_id: str) -> dict[str, Any]:
    data = dict(meta) if isinstance(meta, dict) else {}
    if _facebook_psid_from_meta(data) == user_id:
        data = _store_psid(data, user_id)
    data[FACEBOOK_COMMENTER_KEY] = user_id
    facebook = data.get("facebook")
    nested = dict(facebook) if isinstance(facebook, dict) else {}
    nested["commenter_id"] = user_id
    if not nested.get("kind"):
        nested["kind"] = "messenger" if _facebook_psid_from_meta(data) else "comment"
    data["facebook"] = nested
    return data


def _store_instagram_commenter(meta: dict[str, Any] | None, user_id: str) -> dict[str, Any]:
    data = _store_igsid(meta, user_id)
    data[INSTAGRAM_COMMENTER_KEY] = user_id
    instagram = data.get("instagram")
    nested = dict(instagram) if isinstance(instagram, dict) else {}
    nested["commenter_id"] = user_id
    nested.setdefault("kind", "comment")
    data["instagram"] = nested
    return data


def resolve_facebook_commenter(db: Session, *, user_id: str, display_name: str | None) -> CrmContact:
    existing = find_contact_by_facebook_commenter(db, user_id)
    if existing is not None:
        existing.metadata_json = _store_facebook_commenter(existing.metadata_json, user_id)
        db.flush()
        return existing
    name = (display_name or "").strip() or _placeholder_name(user_id)
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.PROSPECT,
            record_kind=CrmRecordKind.PERSON,
            display_name=name,
            source=FACEBOOK_SOURCE,
            notes="Facebook comment",
            lifecycle_stage=CrmLifecycleStage.NEW,
            status=CrmContactStatus.PROSPECT,
        ),
        actor=None,
    )
    contact.metadata_json = _store_facebook_commenter(contact.metadata_json, user_id)
    db.flush()
    return contact


def resolve_instagram_commenter(db: Session, *, user_id: str, display_name: str | None) -> CrmContact:
    existing = find_contact_by_instagram_commenter(db, user_id)
    if existing is not None:
        existing.metadata_json = _store_instagram_commenter(existing.metadata_json, user_id)
        db.flush()
        return existing
    name = (display_name or "").strip() or _placeholder_instagram_name(user_id)
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.PROSPECT,
            record_kind=CrmRecordKind.PERSON,
            display_name=name,
            source=INSTAGRAM_SOURCE,
            notes="Instagram comment",
            lifecycle_stage=CrmLifecycleStage.NEW,
            status=CrmContactStatus.PROSPECT,
        ),
        actor=None,
    )
    contact.metadata_json = _store_instagram_commenter(contact.metadata_json, user_id)
    db.flush()
    return contact


def extract_facebook_comments(payload: dict[str, Any], *, page_id: str) -> list[MetaCommentInbound]:
    expected = page_id.strip()
    comments: list[MetaCommentInbound] = []
    seen: set[str] = set()
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id or entry_id != expected:
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict) or str(change.get("field") or "") != "feed":
                continue
            value = _dict(change.get("value"))
            if str(value.get("item") or "") != "comment":
                continue
            if str(value.get("verb") or "").strip().lower() not in {"add", "edited"}:
                continue
            comment_id = str(value.get("comment_id") or value.get("commentId") or "").strip()
            if not comment_id or comment_id in seen:
                continue
            sender = _dict(value.get("from"))
            commenter_id = str(sender.get("id") or "").strip()
            if not commenter_id or commenter_id == expected:
                continue
            post = _dict(value.get("post"))
            post_id = str(value.get("post_id") or post.get("id") or "").strip()
            if not post_id:
                continue
            parent_id = str(value.get("parent_id") or "").strip() or post_id
            parent_comment_id = parent_id if parent_id != post_id else None
            seen.add(comment_id)
            published = post.get("is_published")
            comments.append(
                MetaCommentInbound(
                    comment_id=comment_id,
                    commenter_id=commenter_id,
                    commenter_name=str(sender.get("name") or "").strip() or None,
                    text=str(value.get("message") or ""),
                    parent_id=post_id,
                    occurred_at=_message_timestamp(value.get("created_time") or entry.get("time")),
                    platform="facebook",
                    account_id=entry_id,
                    permalink=str(post.get("permalink_url") or value.get("post_url") or "").strip() or None,
                    media_product_type="ad" if published is False else "post",
                    ad_id=str(value.get("ad_id") or post.get("ad_id") or "").strip() or None,
                    ad_title=str(value.get("ad_title") or post.get("ad_title") or "").strip() or None,
                    original_media_id=None,
                    is_published=published if isinstance(published, bool) else None,
                    promotion_status=str(post.get("promotion_status") or "").strip() or None,
                    parent_comment_id=parent_comment_id,
                )
            )
    return comments


def extract_instagram_comments(payload: dict[str, Any], *, account_id: str | None) -> list[MetaCommentInbound]:
    expected = (account_id or "").strip() or None
    if not expected:
        logger.warning("meta_webhook_missing_instagram_webhook_account_id")
        return []
    comments: list[MetaCommentInbound] = []
    seen: set[str] = set()
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id or entry_id != expected:
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict) or str(change.get("field") or "") != "comments":
                continue
            value = _dict(change.get("value"))
            comment_id = str(value.get("id") or value.get("comment_id") or "").strip()
            if not comment_id or comment_id in seen:
                continue
            sender = _dict(value.get("from"))
            commenter_id = str(sender.get("id") or "").strip()
            if not commenter_id or commenter_id == expected:
                continue
            media = _dict(value.get("media"))
            media_id = str(media.get("id") or value.get("media_id") or "").strip()
            if not media_id:
                continue
            seen.add(comment_id)
            product = str(media.get("media_product_type") or "FEED").strip() or "FEED"
            comments.append(
                MetaCommentInbound(
                    comment_id=comment_id,
                    commenter_id=commenter_id,
                    commenter_name=str(sender.get("username") or sender.get("name") or "").strip() or None,
                    text=str(value.get("text") or value.get("message") or ""),
                    parent_id=media_id,
                    occurred_at=_message_timestamp(value.get("timestamp") or entry.get("time")),
                    platform="instagram",
                    account_id=entry_id,
                    permalink=None,
                    media_product_type=product.lower(),
                    ad_id=str(media.get("ad_id") or "").strip() or None,
                    ad_title=str(media.get("ad_title") or "").strip() or None,
                    original_media_id=str(media.get("original_media_id") or "").strip() or None,
                    is_published=None,
                    promotion_status=None,
                    parent_comment_id=str(value.get("parent_id") or "").strip() or None,
                )
            )
    return comments


def _apply_facebook_post_payload(context: dict[str, Any], payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    context["parent_id"] = str(payload.get("id") or context.get("parent_id") or "").strip() or context.get("parent_id")
    context["caption"] = str(payload.get("message") or payload.get("story") or "").strip() or context.get("caption")
    context["permalink"] = str(payload.get("permalink_url") or "").strip() or context.get("permalink")
    context["preview_url"] = str(payload.get("full_picture") or payload.get("picture") or "").strip() or context.get("preview_url")
    context["published_time"] = str(payload.get("created_time") or "").strip() or context.get("published_time")
    context["media_type"] = str(payload.get("status_type") or context.get("media_type") or "").strip() or context.get("media_type")
    if payload.get("is_published") is False:
        context["is_published"] = False
        context["media_type"] = context.get("media_type") or "ad"
    frm = payload.get("from")
    if isinstance(frm, dict):
        context["account_name"] = str(frm.get("name") or "").strip() or context.get("account_name")


def _apply_instagram_media_payload(context: dict[str, Any], payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    context["parent_id"] = str(payload.get("id") or context.get("parent_id") or "").strip() or context.get("parent_id")
    context["caption"] = str(payload.get("caption") or "").strip() or context.get("caption")
    context["permalink"] = str(payload.get("permalink") or "").strip() or context.get("permalink")
    context["media_type"] = str(payload.get("media_type") or context.get("media_type") or "").strip() or context.get("media_type")
    context["preview_url"] = str(payload.get("thumbnail_url") or payload.get("media_url") or "").strip() or context.get("preview_url")
    context["published_time"] = str(payload.get("timestamp") or "").strip() or context.get("published_time")
    context["account_name"] = str(payload.get("username") or "").strip() or context.get("account_name")


def _facebook_post_context(item: MetaCommentInbound) -> dict[str, Any]:
    context: dict[str, Any] = {
        "platform": "facebook",
        "comment_id": item.comment_id,
        "parent_id": item.parent_id,
        "permalink": item.permalink,
        "media_type": item.media_product_type,
        "is_published": item.is_published,
        "promotion_status": item.promotion_status,
        "account_id": item.account_id,
        "commenter_name": item.commenter_name,
    }
    if item.ad_id:
        context["ad_id"] = item.ad_id
    if item.ad_title:
        context["ad_name"] = item.ad_title
    token = (get_settings().meta_page_access_token or "").strip()
    if not token:
        return _clean_ctx(context)
    comment_payload = _graph_get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{item.comment_id}",
        token=token,
        fields="id,from,message,created_time,permalink_url,can_reply_privately,can_comment,user_likes,attachment",
    )
    if comment_payload:
        context["can_reply_privately"] = bool(comment_payload.get("can_reply_privately"))
        context["can_comment"] = comment_payload.get("can_comment")
        context["user_likes"] = bool(comment_payload.get("user_likes"))
        context["permalink"] = str(comment_payload.get("permalink_url") or "").strip() or context.get("permalink")
        frm = comment_payload.get("from")
        if isinstance(frm, dict):
            context["commenter_name"] = str(frm.get("name") or "").strip() or context.get("commenter_name")
        attachment = comment_payload.get("attachment")
        if isinstance(attachment, dict):
            media = attachment.get("media") if isinstance(attachment.get("media"), dict) else {}
            context["preview_url"] = str(media.get("image", {}).get("src") if isinstance(media.get("image"), dict) else media.get("src") or "").strip() or context.get("preview_url")
    _apply_facebook_post_payload(
        context,
        _graph_get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{item.parent_id}",
            token=token,
            fields="id,message,story,permalink_url,created_time,full_picture,picture,status_type,is_published,from{name,id}",
        ) if item.parent_id else None,
    )
    if item.ad_id:
        ad_payload = _graph_get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{item.ad_id}",
            token=token,
            fields="id,name,campaign_id,campaign{id,name}",
        )
        if ad_payload:
            context["ad_id"] = str(ad_payload.get("id") or item.ad_id).strip() or item.ad_id
            context["ad_name"] = str(ad_payload.get("name") or context.get("ad_name") or "").strip() or context.get("ad_name")
            context["campaign_id"] = str(ad_payload.get("campaign_id") or "").strip() or None
            campaign = ad_payload.get("campaign")
            if isinstance(campaign, dict):
                context["campaign_id"] = str(campaign.get("id") or context.get("campaign_id") or "").strip() or context.get("campaign_id")
                context["campaign_name"] = str(campaign.get("name") or "").strip() or None
    context["context_status"] = "ready" if context_is_visible(context) else "unavailable"
    if context["context_status"] == "unavailable":
        context["context_error"] = PUBLIC_CONTEXT_UNAVAILABLE
    return _clean_ctx(context)


def _instagram_media_context(item: MetaCommentInbound) -> dict[str, Any]:
    context: dict[str, Any] = {
        "platform": "instagram",
        "comment_id": item.comment_id,
        "parent_id": item.parent_id,
        "media_type": item.media_product_type,
        "account_id": item.account_id,
        "commenter_name": item.commenter_name,
        "commenter_username": item.commenter_name if item.commenter_name and " " not in item.commenter_name else None,
    }
    if item.ad_id:
        context["ad_id"] = item.ad_id
    if item.ad_title:
        context["ad_name"] = item.ad_title
    if item.original_media_id:
        context["original_media_id"] = item.original_media_id
    token = (get_settings().meta_instagram_access_token or "").strip()
    if not token:
        context["context_status"] = "unavailable"
        context["context_error"] = PUBLIC_CONTEXT_UNAVAILABLE
        return _clean_ctx(context)
    comment_payload = _graph_get(
        f"https://graph.instagram.com/{GRAPH_API_VERSION}/{item.comment_id}",
        token=token,
        fields="id,text,timestamp,username,from,media{id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username}",
    )
    if comment_payload:
        context["commenter_username"] = str(comment_payload.get("username") or "").strip() or context.get("commenter_username")
        frm = comment_payload.get("from")
        if isinstance(frm, dict):
            context["commenter_username"] = str(frm.get("username") or "").strip() or context.get("commenter_username")
            context["commenter_name"] = str(frm.get("username") or frm.get("name") or "").strip() or context.get("commenter_name")
        media = comment_payload.get("media")
        if isinstance(media, dict):
            _apply_instagram_media_payload(context, media)
    media_id = str(context.get("parent_id") or item.original_media_id or item.parent_id or "").strip()
    if not context_is_visible(context) and media_id:
        _apply_instagram_media_payload(
            context,
            _graph_get(
                f"https://graph.instagram.com/{GRAPH_API_VERSION}/{media_id}",
                token=token,
                fields="id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
            ),
        )
    context["context_status"] = "ready" if context_is_visible(context) else "unavailable"
    if context["context_status"] == "unavailable":
        context["context_error"] = PUBLIC_CONTEXT_UNAVAILABLE
    return _clean_ctx(context)


def _ingest_comment(db: Session, item: MetaCommentInbound, *, claimed: set[str], prefix: str) -> bool:
    key = f"{prefix}:{item.comment_id}"
    if key not in claimed:
        return False
    if item.platform == "facebook":
        contact = resolve_facebook_commenter(db, user_id=item.commenter_id, display_name=item.commenter_name)
        context = _facebook_post_context(item)
        source = "live_facebook"
        identity = {FACEBOOK_COMMENTER_KEY: item.commenter_id}
        subject = "Facebook comment"
    else:
        contact = resolve_instagram_commenter(db, user_id=item.commenter_id, display_name=item.commenter_name)
        context = _instagram_media_context(item)
        source = "live_instagram"
        identity = {INSTAGRAM_COMMENTER_KEY: item.commenter_id, INSTAGRAM_IGSID_KEY: item.commenter_id}
        subject = "Instagram comment"
    thread_id = item.parent_comment_id or item.comment_id
    comm, created = ingest_live_message(
        db,
        {
            "channel": item.platform,
            "direction": "incoming",
            "source": source,
            "sender": item.commenter_id,
            "sender_identity": item.commenter_name,
            "subject": subject,
            "body_text": item.text,
            "external_provider_id": item.comment_id,
            "conversation_key": comment_conversation_key(thread_id),
            "occurred_at": item.occurred_at,
            "contact_id": str(contact.id),
            "metadata_json": {
                "kind": COMMENT_KIND,
                "comment_id": item.comment_id,
                "parent_id": item.parent_id,
                "comment_context": context,
                **identity,
            },
        },
        actor=None,
    )
    _ = comm
    return created


def ingest_page_comments(db: Session, payload: dict[str, Any], *, page_id: str) -> dict[str, Any]:
    comments = extract_facebook_comments(payload, page_id=page_id)
    if not comments:
        return {"ingested": 0, "duplicate": False}
    keys = [f"fb:cmt:{item.comment_id}" for item in comments]
    claimed, duplicates = _claim_keys(keys)
    if duplicates:
        logger.info("meta_webhook_facebook_comment_replay count=%s", len(duplicates))
    if not claimed:
        return {"ingested": 0, "duplicate": True}
    created = sum(1 for item in comments if _ingest_comment(db, item, claimed=set(claimed), prefix="fb:cmt"))
    return {"ingested": created, "duplicate": False}


def ingest_instagram_comments(db: Session, payload: dict[str, Any], *, account_id: str | None) -> dict[str, Any]:
    comments = extract_instagram_comments(payload, account_id=account_id)
    if not comments:
        return {"ingested": 0, "duplicate": False}
    keys = [f"ig:cmt:{item.comment_id}" for item in comments]
    claimed, duplicates = _claim_keys(keys)
    if duplicates:
        logger.info("meta_webhook_instagram_comment_replay count=%s", len(duplicates))
    if not claimed:
        return {"ingested": 0, "duplicate": True}
    created = sum(1 for item in comments if _ingest_comment(db, item, claimed=set(claimed), prefix="ig:cmt"))
    return {"ingested": created, "duplicate": False}


def _inbound_from_communication(comm: CrmCommunication) -> MetaCommentInbound | None:
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    if str(meta.get("kind") or "").strip().lower() != COMMENT_KIND:
        return None
    ctx = meta.get("comment_context") if isinstance(meta.get("comment_context"), dict) else {}
    comment_id = str(meta.get("comment_id") or parse_comment_id(comm.conversation_key) or comm.external_provider_id or "").strip()
    parent_id = str(meta.get("parent_id") or ctx.get("parent_id") or "").strip() or comment_id
    if not comment_id:
        return None
    return MetaCommentInbound(
        comment_id=comment_id,
        commenter_id=str(meta.get(FACEBOOK_COMMENTER_KEY) or meta.get(INSTAGRAM_COMMENTER_KEY) or "").strip() or "unknown",
        commenter_name=str(ctx.get("commenter_name") or comm.sender_identity or "").strip() or None,
        text=str(comm.body_text or comm.preview or ""),
        parent_id=parent_id,
        occurred_at=comm.occurred_at,
        platform=comm.channel,
        account_id=str(ctx.get("account_id") or "").strip() or "",
        permalink=str(ctx.get("permalink") or "").strip() or None,
        media_product_type=str(ctx.get("media_type") or "").strip() or None,
        ad_id=str(ctx.get("ad_id") or "").strip() or None,
        ad_title=str(ctx.get("ad_name") or "").strip() or None,
        original_media_id=str(ctx.get("original_media_id") or "").strip() or None,
        is_published=ctx.get("is_published") if isinstance(ctx.get("is_published"), bool) else None,
        promotion_status=str(ctx.get("promotion_status") or "").strip() or None,
        parent_comment_id=parse_comment_id(comm.conversation_key) if parse_comment_id(comm.conversation_key) != comment_id else None,
    )


def _persist_comment_context(db: Session, comm: CrmCommunication, context: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    meta = dict(comm.metadata_json) if isinstance(comm.metadata_json, dict) else {}
    meta["comment_context"] = _merge_ctx(meta.get("comment_context") if isinstance(meta.get("comment_context"), dict) else {}, context)
    if extra:
        meta.update(extra)
    comm.metadata_json = meta
    db.add(comm)
    if comm.activity_id:
        from investhome_api.models.crm_activity import CrmActivity

        activity = db.get(CrmActivity, comm.activity_id)
        if activity is not None:
            activity_meta = dict(activity.metadata_json) if isinstance(activity.metadata_json, dict) else {}
            live = dict(activity_meta.get("live_thread")) if isinstance(activity_meta.get("live_thread"), dict) else {}
            live["comment_context"] = meta["comment_context"]
            activity_meta["live_thread"] = live
            activity_meta["comment_context"] = meta["comment_context"]
            activity_meta["kind"] = COMMENT_KIND
            activity.metadata_json = activity_meta
            db.add(activity)
    db.flush()


def enrich_comment_communication(db: Session, comm: CrmCommunication) -> dict[str, Any]:
    item = _inbound_from_communication(comm)
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    current = meta.get("comment_context") if isinstance(meta.get("comment_context"), dict) else {}
    if item is None:
        return current if isinstance(current, dict) else {}
    fetched = _instagram_media_context(item) if comm.channel == "instagram" else _facebook_post_context(item)
    merged = _merge_ctx(current, fetched)
    extra: dict[str, Any] = {}
    if merged.get("user_likes") is not None:
        extra["user_likes"] = bool(merged.get("user_likes"))
    if merged.get("can_reply_privately") is not None:
        extra["can_reply_privately"] = bool(merged.get("can_reply_privately"))
    _persist_comment_context(db, comm, merged, extra or None)
    return merged


def comment_capabilities(comm: CrmCommunication) -> dict[str, Any]:
    meta = comm.metadata_json if isinstance(comm.metadata_json, dict) else {}
    ctx = meta.get("comment_context") if isinstance(meta.get("comment_context"), dict) else {}
    username = str(ctx.get("commenter_username") or "").strip() or None
    if comm.channel == "instagram" and not username:
        identity = str(comm.sender_identity or "").strip()
        username = identity if identity and " " not in identity else None
    sent = bool(meta.get("private_reply_sent") or ctx.get("private_reply_sent"))
    occurred = comm.occurred_at or comm.created_at
    within_window = True
    if occurred is not None:
        stamp = occurred if occurred.tzinfo else occurred.replace(tzinfo=UTC)
        within_window = datetime.now(UTC) - stamp.astimezone(UTC) <= PRIVATE_REPLY_WINDOW
    if comm.channel == "facebook":
        can_private = bool(ctx.get("can_reply_privately") or meta.get("can_reply_privately")) and not sent and within_window
        can_like = FACEBOOK_LIKE_SUPPORTED
        liked = bool(ctx.get("user_likes") or meta.get("user_likes"))
        prefix = None
    else:
        can_private = not sent and within_window
        can_like = INSTAGRAM_LIKE_SUPPORTED
        liked = False
        prefix = _reply_prefix(username)
    visible = context_is_visible(ctx)
    return {
        "can_public_reply": True,
        "can_private_reply": can_private,
        "can_like": can_like,
        "liked": liked,
        "reply_prefix": prefix,
        "commenter_name": str(ctx.get("commenter_name") or comm.sender_identity or "").strip() or None,
        "context_status": "ready" if visible else str(ctx.get("context_status") or "unavailable"),
        "context_error": None if visible else str(ctx.get("context_error") or PUBLIC_CONTEXT_UNAVAILABLE),
    }


def load_comment_thread_meta(db: Session, *, conversation_key: str | None, channel: str | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not parse_comment_id(conversation_key) or channel not in SUPPORTED_CHANNELS:
        return None, None
    rows = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.archived_at.is_(None),
                CrmCommunication.channel == channel,
                CrmCommunication.conversation_key == conversation_key,
            )
        ).all()
    )
    seed = next(
        (
            row
            for row in rows
            if isinstance(row.metadata_json, dict)
            and str(row.metadata_json.get("kind") or "") == COMMENT_KIND
            and row.direction == "inbound"
        ),
        next(
            (
                row
                for row in rows
                if isinstance(row.metadata_json, dict) and str(row.metadata_json.get("kind") or "") == COMMENT_KIND
            ),
            None,
        ),
    )
    if seed is None:
        return None, None
    enrich_comment_communication(db, seed)
    db.refresh(seed)
    ctx = seed.metadata_json.get("comment_context") if isinstance(seed.metadata_json, dict) else None
    return ctx if isinstance(ctx, dict) else {}, comment_capabilities(seed)


def _comment_reply_url(channel: str, comment_id: str) -> str:
    if channel == "facebook":
        return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{comment_id}/comments"
    return f"https://graph.instagram.com/{GRAPH_API_VERSION}/{comment_id}/replies"


def graph_reply_comment(*, channel: str, comment_id: str, text: str) -> str:
    try:
        if channel == "facebook":
            token = require_page_access_token()
        else:
            token, _account_id = require_instagram_credentials()
    except MetaSendError:
        raise MetaSendError(PUBLIC_COMMENT_NOT_CONFIGURED, 503) from None
    url = _comment_reply_url(channel, comment_id)
    try:
        response = _post_graph_messages(url, {"message": text}, token)
    except httpx.HTTPError:
        logger.warning("meta_comment_reply_transport_error")
        raise MetaSendError(PUBLIC_COMMENT_SEND_FAILED, 502) from None
    reply_id = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        reply_id = str(body.get("id") or body.get("comment_id") or "").strip()
    if response.status_code >= 400 or not reply_id:
        logger.warning("meta_comment_reply_rejected status=%s", response.status_code)
        raise MetaSendError(PUBLIC_COMMENT_SEND_FAILED, 502)
    return reply_id


def send_meta_comment_reply(
    db: Session,
    *,
    channel: str,
    contact_id: UUID,
    text: str,
    conversation_key: str | None,
    actor: User,
) -> tuple[CrmCommunication, bool]:
    normalized = (channel or "").strip().lower()
    if normalized not in SUPPORTED_CHANNELS:
        raise MetaSendError(PUBLIC_UNSUPPORTED_CHANNEL, 400)
    body = (text or "").strip()
    if not body:
        raise MetaSendError(PUBLIC_EMPTY_MESSAGE, 400)
    contact = db.get(CrmContact, contact_id)
    if contact is None or contact.archived_at is not None:
        raise MetaSendError(PUBLIC_UNKNOWN_CONTACT, 404)
    comment_id = parse_comment_id(conversation_key)
    if not comment_id:
        raise MetaSendError(PUBLIC_COMMENT_UNAVAILABLE, 400)

    provider_id = graph_reply_comment(channel=normalized, comment_id=comment_id, text=body)
    prefix = "fb:cmt" if normalized == "facebook" else "ig:cmt"
    claimed, _duplicates = _claim_keys([f"{prefix}:{provider_id}"])
    if not claimed:
        existing = db.scalar(
            select(CrmCommunication).where(
                CrmCommunication.external_provider_id == provider_id,
                CrmCommunication.archived_at.is_(None),
            )
        )
        if existing is not None:
            return existing, False

    source = "live_facebook" if normalized == "facebook" else "live_instagram"
    parent_context: dict[str, Any] = {}
    seed = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.conversation_key == conversation_key,
            CrmCommunication.archived_at.is_(None),
        )
    )
    if seed is not None and isinstance(seed.metadata_json, dict):
        ctx = seed.metadata_json.get("comment_context")
        if isinstance(ctx, dict):
            parent_context = dict(ctx)
        parent_context.setdefault("parent_id", seed.metadata_json.get("parent_id"))
        parent_context.setdefault("comment_id", comment_id)

    comm, created = ingest_live_message(
        db,
        {
            "channel": normalized,
            "direction": "outgoing",
            "source": source,
            "sender": "page" if normalized == "facebook" else "instagram",
            "recipients": [comment_id],
            "subject": "Facebook comment reply" if normalized == "facebook" else "Instagram comment reply",
            "body_text": body,
            "external_provider_id": provider_id,
            "conversation_key": conversation_key,
            "occurred_at": datetime.now(UTC),
            "contact_id": str(contact.id),
            "metadata_json": {
                "kind": COMMENT_KIND,
                "outbound": True,
                "comment_id": provider_id,
                "in_reply_to": comment_id,
                "parent_id": parent_context.get("parent_id"),
                "comment_context": parent_context or None,
            },
        },
        actor=actor,
    )
    return comm, created


def _comment_seed(db: Session, *, conversation_key: str | None, channel: str) -> CrmCommunication | None:
    rows = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.archived_at.is_(None),
                CrmCommunication.channel == channel,
                CrmCommunication.conversation_key == conversation_key,
            )
        ).all()
    )
    return next(
        (
            row
            for row in rows
            if isinstance(row.metadata_json, dict) and str(row.metadata_json.get("kind") or "") == COMMENT_KIND
        ),
        None,
    )


def graph_private_reply(*, channel: str, comment_id: str, text: str) -> tuple[str, str | None]:
    try:
        if channel == "facebook":
            token = require_page_access_token()
            url = FACEBOOK_MESSAGES_URL
        else:
            token, account_id = require_instagram_credentials()
            url = instagram_messages_url(account_id)
    except MetaSendError:
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_UNAVAILABLE, 503) from None
    payload = {"recipient": {"comment_id": comment_id}, "message": {"text": text}}
    if channel == "facebook":
        payload["messaging_type"] = "RESPONSE"
    try:
        response = _post_graph_messages(url, payload, token)
    except httpx.HTTPError:
        logger.warning("meta_private_reply_transport_error")
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_FAILED, 502) from None
    body: dict[str, Any] | None
    try:
        parsed = response.json()
        body = parsed if isinstance(parsed, dict) else None
    except ValueError:
        body = None
    message_id = ""
    recipient_id = None
    if body:
        message_id = str(body.get("message_id") or body.get("id") or "").strip()
        recipient_id = str(body.get("recipient_id") or "").strip() or None
        nested = body.get("message")
        if not message_id and isinstance(nested, dict):
            message_id = str(nested.get("mid") or nested.get("id") or "").strip()
    if response.status_code >= 400 or not message_id:
        logger.warning("meta_private_reply_rejected status=%s", response.status_code)
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_FAILED, 502)
    return message_id, recipient_id


def send_meta_private_reply(
    db: Session,
    *,
    channel: str,
    contact_id: UUID,
    text: str,
    conversation_key: str | None,
    actor: User,
) -> tuple[CrmCommunication, bool]:
    normalized = (channel or "").strip().lower()
    if normalized not in SUPPORTED_CHANNELS:
        raise MetaSendError(PUBLIC_UNSUPPORTED_CHANNEL, 400)
    body = (text or "").strip()
    if not body:
        raise MetaSendError(PUBLIC_EMPTY_MESSAGE, 400)
    contact = db.get(CrmContact, contact_id)
    if contact is None or contact.archived_at is not None:
        raise MetaSendError(PUBLIC_UNKNOWN_CONTACT, 404)
    comment_id = parse_comment_id(conversation_key)
    if not comment_id:
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_UNAVAILABLE, 400)
    seed = _comment_seed(db, conversation_key=conversation_key, channel=normalized)
    if seed is None:
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_UNAVAILABLE, 400)
    enrich_comment_communication(db, seed)
    db.refresh(seed)
    caps = comment_capabilities(seed)
    if not caps.get("can_private_reply"):
        meta = seed.metadata_json if isinstance(seed.metadata_json, dict) else {}
        if meta.get("private_reply_sent"):
            raise MetaSendError(PUBLIC_PRIVATE_REPLY_ALREADY_SENT, 409)
        raise MetaSendError(PUBLIC_PRIVATE_REPLY_UNAVAILABLE, 400)

    provider_id, recipient_id = graph_private_reply(channel=normalized, comment_id=comment_id, text=body)
    prefix = "msg" if normalized == "facebook" else "ig:msg"
    claimed, _duplicates = _claim_keys([f"{prefix}:{provider_id}"])
    if not claimed:
        existing = db.scalar(
            select(CrmCommunication).where(
                CrmCommunication.external_provider_id == provider_id,
                CrmCommunication.archived_at.is_(None),
            )
        )
        if existing is not None:
            return existing, False

    if recipient_id:
        if normalized == "facebook":
            contact.metadata_json = _store_psid(contact.metadata_json, recipient_id)
        else:
            contact.metadata_json = _store_instagram_commenter(contact.metadata_json, recipient_id)
        db.add(contact)

    _persist_comment_context(
        db,
        seed,
        {},
        {
            "private_reply_sent": True,
            "private_reply_message_id": provider_id,
            "private_reply_recipient_id": recipient_id,
        },
    )

    source = "live_facebook" if normalized == "facebook" else "live_instagram"
    thread_key = recipient_id or conversation_key
    comm, created = ingest_live_message(
        db,
        {
            "channel": normalized,
            "direction": "outgoing",
            "source": source,
            "sender": "page" if normalized == "facebook" else "instagram",
            "recipients": [recipient_id or comment_id],
            "subject": "Facebook private reply" if normalized == "facebook" else "Instagram private reply",
            "body_text": body,
            "external_provider_id": provider_id,
            "conversation_key": thread_key,
            "occurred_at": datetime.now(UTC),
            "contact_id": str(contact.id),
            "metadata_json": {
                "kind": "dm",
                "outbound": True,
                "private_reply": True,
                "source_comment_id": comment_id,
                "source_conversation_key": conversation_key,
            },
        },
        actor=actor,
    )
    return comm, created


def set_comment_like(
    db: Session,
    *,
    channel: str,
    conversation_key: str | None,
    liked: bool,
) -> dict[str, Any]:
    normalized = (channel or "").strip().lower()
    if normalized == "instagram" or not FACEBOOK_LIKE_SUPPORTED:
        raise MetaSendError(PUBLIC_LIKE_UNSUPPORTED, 400)
    if normalized != "facebook":
        raise MetaSendError(PUBLIC_UNSUPPORTED_CHANNEL, 400)
    comment_id = parse_comment_id(conversation_key)
    if not comment_id:
        raise MetaSendError(PUBLIC_COMMENT_UNAVAILABLE, 400)
    try:
        token = require_page_access_token()
    except MetaSendError:
        raise MetaSendError(PUBLIC_COMMENT_NOT_CONFIGURED, 503) from None
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{comment_id}/likes"
    if liked:
        try:
            response = _post_graph_messages(url, {}, token)
        except httpx.HTTPError:
            raise MetaSendError(PUBLIC_LIKE_FAILED, 502) from None
        if response.status_code >= 400:
            raise MetaSendError(PUBLIC_LIKE_FAILED, 502)
    else:
        response = _graph_delete(url, token=token)
        if response is None or response.status_code >= 400:
            raise MetaSendError(PUBLIC_LIKE_FAILED, 502)
    seed = _comment_seed(db, conversation_key=conversation_key, channel=normalized)
    if seed is not None:
        _persist_comment_context(db, seed, {"user_likes": liked}, {"user_likes": liked})
    return {"liked": liked, "can_like": True}
