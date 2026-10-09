"""Server-side Meta Messenger / Instagram DM send. Tokens never leave the API process."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm.meta_webhook import (
    FACEBOOK_PSID_KEY,
    FACEBOOK_SOURCE,
    INSTAGRAM_IGSID_KEY,
    INSTAGRAM_SOURCE,
    _active_facebook_lead_for_contact,
    _active_instagram_lead_for_contact,
    _claim_keys,
    _facebook_psid_from_meta,
    _instagram_igsid_from_meta,
    _record_meta_dm_on_lead,
)

logger = get_logger("investhome.meta.send")

GRAPH_API_VERSION = "v21.0"
FACEBOOK_MESSAGES_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages"
GRAPH_MESSAGES_URL = FACEBOOK_MESSAGES_URL
GRAPH_TIMEOUT_SECONDS = 15.0

PUBLIC_NOT_CONFIGURED = "Messenger send is not configured"
PUBLIC_INSTAGRAM_NOT_CONFIGURED = "Instagram send is not configured"
PUBLIC_RECIPIENT_UNAVAILABLE = "Recipient is not available for this conversation"
PUBLIC_EMPTY_MESSAGE = "Message text is required"
PUBLIC_SEND_FAILED = "Message could not be sent"
PUBLIC_UNSUPPORTED_CHANNEL = "Unsupported channel"
PUBLIC_UNKNOWN_CONTACT = "Contact was not found"

SUPPORTED_CHANNELS = frozenset({"facebook", "instagram"})


class MetaSendError(Exception):
    def __init__(self, public_detail: str, status_code: int = 502) -> None:
        super().__init__(public_detail)
        self.public_detail = public_detail
        self.status_code = status_code


def require_page_access_token() -> str:
    token = (get_settings().meta_page_access_token or "").strip()
    if not token:
        logger.warning("meta_send_missing_page_access_token")
        raise MetaSendError(PUBLIC_NOT_CONFIGURED, 503)
    return token


def require_instagram_credentials() -> tuple[str, str]:
    """Instagram Login send credentials. Never fall back to the Facebook Page token."""
    settings = get_settings()
    token = (settings.meta_instagram_access_token or "").strip()
    account_id = (settings.meta_instagram_account_id or "").strip()
    # Outbound Login /me id only. Never fall back to META_INSTAGRAM_WEBHOOK_ACCOUNT_ID.
    if not token or not account_id:
        logger.warning("meta_send_missing_instagram_credentials")
        raise MetaSendError(PUBLIC_INSTAGRAM_NOT_CONFIGURED, 503)
    return token, account_id


def instagram_messages_url(account_id: str) -> str:
    return f"https://graph.instagram.com/{GRAPH_API_VERSION}/{account_id}/messages"


def _post_graph_messages(url: str, payload: dict[str, Any], token: str) -> httpx.Response:
    """POST Graph Send API. Token is Authorization only — never a query string."""
    return httpx.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=GRAPH_TIMEOUT_SECONDS,
    )


def graph_send_text(*, channel: str, recipient_id: str, text: str) -> str:
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }
    if channel == "facebook":
        token = require_page_access_token()
        url = FACEBOOK_MESSAGES_URL
    else:
        token, account_id = require_instagram_credentials()
        url = instagram_messages_url(account_id)
    try:
        response = _post_graph_messages(url, payload, token)
    except httpx.HTTPError:
        logger.warning("meta_send_graph_transport_error")
        raise MetaSendError(PUBLIC_SEND_FAILED, 502) from None

    message_id = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        message_id = str(body.get("message_id") or "").strip()
        nested = body.get("message")
        if not message_id and isinstance(nested, dict):
            message_id = str(nested.get("mid") or nested.get("id") or "").strip()

    if response.status_code >= 400 or not message_id:
        logger.warning("meta_send_graph_rejected status=%s", response.status_code)
        raise MetaSendError(PUBLIC_SEND_FAILED, 502)
    return message_id


def _recipient_id(contact: CrmContact, *, channel: str, conversation_key: str | None) -> str:
    key = (conversation_key or "").strip()
    if key:
        return key
    if channel == "facebook":
        return (_facebook_psid_from_meta(contact.metadata_json) or "").strip()
    return (_instagram_igsid_from_meta(contact.metadata_json) or "").strip()


def send_meta_dm(
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

    if (conversation_key or "").strip().startswith("cmt:"):
        raise MetaSendError(PUBLIC_RECIPIENT_UNAVAILABLE, 400)
    recipient_id = _recipient_id(contact, channel=normalized, conversation_key=conversation_key)
    if not recipient_id:
        raise MetaSendError(PUBLIC_RECIPIENT_UNAVAILABLE, 400)

    provider_message_id = graph_send_text(channel=normalized, recipient_id=recipient_id, text=body)

    idem_prefix = "msg" if normalized == "facebook" else "ig:msg"
    claimed, _duplicates = _claim_keys([f"{idem_prefix}:{provider_message_id}"])
    if not claimed:
        existing = db.scalar(
            select(CrmCommunication).where(
                CrmCommunication.external_provider_id == provider_message_id,
                CrmCommunication.archived_at.is_(None),
            )
        )
        if existing is not None:
            return existing, False

    if normalized == "facebook":
        lead = _active_facebook_lead_for_contact(db, contact=contact, psid=recipient_id)
        source = "live_facebook"
        sender = (get_settings().meta_page_id or "").strip() or "page"
        description_key = "crm.leads.facebook_messenger.sent"
        provider = FACEBOOK_SOURCE
        identity_meta: dict[str, Any] = {FACEBOOK_PSID_KEY: recipient_id, "page_id": sender}
    else:
        lead = _active_instagram_lead_for_contact(db, contact=contact, igsid=recipient_id)
        source = "live_instagram"
        sender = (get_settings().meta_instagram_account_id or "").strip()
        description_key = "crm.leads.instagram_dm.sent"
        provider = INSTAGRAM_SOURCE
        identity_meta = {INSTAGRAM_IGSID_KEY: recipient_id, "ig_account_id": sender}

    comm, created = ingest_live_message(
        db,
        {
            "channel": normalized,
            "direction": "outgoing",
            "source": source,
            "sender": sender,
            "recipients": [recipient_id],
            "body_text": body,
            "external_provider_id": provider_message_id,
            "conversation_key": recipient_id,
            "occurred_at": datetime.now(UTC),
            "contact_id": str(contact.id),
            "metadata_json": {
                "kind": "dm",
                "outbound": True,
                **identity_meta,
                **({"lead_id": str(lead.id)} if lead is not None else {}),
            },
        },
        actor=actor,
    )
    if created and lead is not None:
        _record_meta_dm_on_lead(
            db,
            lead=lead,
            contact=contact,
            mid=provider_message_id,
            text=body,
            occurred_at=comm.occurred_at,
            communication_id=comm.id,
            description_key=description_key,
            provider=provider,
            extra_meta={"direction": "outgoing"},
        )
    return comm, created
