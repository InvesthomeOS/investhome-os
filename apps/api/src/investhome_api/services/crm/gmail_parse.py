"""Parse a Gmail API message resource into a live-ingest payload. No network."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from investhome_api.services.crm.identity import normalize_email

logger = logging.getLogger(__name__)

SKIP_LABELS = frozenset({"SPAM", "TRASH"})


@dataclass
class ParsedGmailAttachment:
    file_name: str
    mime_type: str | None
    attachment_id: str | None
    size: int | None = None
    inline_data: bytes | None = None


@dataclass
class ParsedGmailMessage:
    gmail_id: str
    thread_id: str
    rfc_message_id: str | None
    direction: str
    sender: str | None
    recipients: list[str]
    cc: list[str]
    subject: str | None
    occurred_at: datetime
    body_html: str | None
    body_text: str | None
    label_ids: list[str]
    skip: bool
    attachments: list[ParsedGmailAttachment] = field(default_factory=list)


def _b64url(data: str | None) -> bytes:
    if not data:
        return b""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in payload.get("headers") or []:
        name = str(item.get("name") or "").strip().lower()
        value = str(item.get("value") or "").strip()
        if name:
            headers[name] = value
    return headers


def _emails(header: str | None) -> list[str]:
    if not header:
        return []
    found: list[str] = []
    for _, address in getaddresses([header]):
        normalized = normalize_email(address)
        if normalized and normalized not in found:
            found.append(normalized)
    return found


def _walk_parts(payload: dict[str, Any], attachments: list[ParsedGmailAttachment]) -> tuple[str | None, str | None]:
    text: str | None = None
    html: str | None = None
    mime = str(payload.get("mimeType") or "")
    filename = str(payload.get("filename") or "").strip()
    body = payload.get("body") or {}
    data = body.get("data")
    attachment_id = body.get("attachmentId")
    if filename and (attachment_id or data):
        inline = _b64url(data) if data and not attachment_id else None
        attachments.append(
            ParsedGmailAttachment(
                file_name=filename,
                mime_type=mime or None,
                attachment_id=str(attachment_id) if attachment_id else None,
                size=body.get("size"),
                inline_data=inline,
            )
        )
    elif mime.startswith("text/plain") and data:
        decoded = _b64url(data).decode("utf-8", errors="replace")
        text = decoded if text is None else text
    elif mime.startswith("text/html") and data:
        decoded = _b64url(data).decode("utf-8", errors="replace")
        html = decoded if html is None else html
    for part in payload.get("parts") or []:
        if not isinstance(part, dict):
            continue
        child_text, child_html = _walk_parts(part, attachments)
        if child_text and text is None:
            text = child_text
        if child_html and html is None:
            html = child_html
    return text, html


def _occurred_at(message: dict[str, Any], headers: dict[str, str]) -> datetime:
    internal = message.get("internalDate")
    if internal:
        try:
            return datetime.fromtimestamp(int(internal) / 1000, tz=UTC)
        except (TypeError, ValueError, OSError):
            pass
    raw_date = headers.get("date")
    if raw_date:
        try:
            parsed = parsedate_to_datetime(raw_date)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError, IndexError):
            pass
    return datetime.now(UTC)


def parse_gmail_message(message: dict[str, Any], *, account_email: str | None = None) -> ParsedGmailMessage:
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    headers = _header_map(payload)
    labels = [str(item) for item in (message.get("labelIds") or [])]
    skip = bool(SKIP_LABELS.intersection(labels))
    sender_list = _emails(headers.get("from"))
    recipients = _emails(headers.get("to"))
    cc = _emails(headers.get("cc"))
    account = normalize_email(account_email)
    if "SENT" in labels or (account and sender_list and sender_list[0] == account):
        direction = "outgoing"
    else:
        direction = "incoming"
    attachments: list[ParsedGmailAttachment] = []
    body_text, body_html = _walk_parts(payload, attachments)
    snippet = str(message.get("snippet") or "").strip() or None
    rfc = (headers.get("message-id") or "").strip() or None
    return ParsedGmailMessage(
        gmail_id=str(message.get("id") or ""),
        thread_id=str(message.get("threadId") or message.get("thread_id") or ""),
        rfc_message_id=rfc,
        direction=direction,
        sender=sender_list[0] if sender_list else None,
        recipients=recipients,
        cc=cc,
        subject=(headers.get("subject") or "").strip() or None,
        occurred_at=_occurred_at(message, headers),
        body_html=body_html,
        body_text=body_text or snippet,
        label_ids=labels,
        skip=skip,
        attachments=attachments,
    )


def parsed_to_ingest_payload(
    parsed: ParsedGmailMessage,
    *,
    account_id: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "channel": "email",
        "direction": parsed.direction,
        "source": "live_email",
        "account_id": account_id,
        "subject": parsed.subject,
        "body_html": parsed.body_html,
        "body_text": parsed.body_text,
        "sender": parsed.sender,
        "sender_identity": parsed.sender,
        "recipients": parsed.recipients,
        "cc": parsed.cc,
        "occurred_at": parsed.occurred_at,
        "external_provider_id": parsed.gmail_id,
        "conversation_id": parsed.thread_id,
        "rfc_message_id": parsed.rfc_message_id,
        "attachments": attachments or [],
    }
