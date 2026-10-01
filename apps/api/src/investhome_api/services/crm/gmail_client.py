"""Gmail API mailbox client. Never logs tokens or message bodies."""

from __future__ import annotations

import base64
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Protocol

from investhome_api.models.crm_communication import CrmUserCommunicationAccount
from investhome_api.services.crm.gmail_oauth import persist_gmail_tokens, refresh_access_token
from investhome_api.services.crm.live_accounts import load_account_credentials

logger = logging.getLogger(__name__)


class GmailMailbox(Protocol):
    def get_profile_history_id(self) -> str: ...

    def list_message_ids(self, query: str) -> Iterator[str]: ...

    def get_message(self, message_id: str) -> dict[str, Any]: ...

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes: ...

    def list_history_message_ids(self, start_history_id: str) -> tuple[list[str], str | None]: ...


class GmailApiError(RuntimeError):
    def __init__(self, code: str, *, needs_reauth: bool = False):
        super().__init__(code)
        self.code = code
        self.needs_reauth = needs_reauth


def _decode_attachment(data: str | None) -> bytes:
    if not data:
        return b""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def load_valid_access_token(account: CrmUserCommunicationAccount) -> str:
    creds = load_account_credentials(account) or {}
    access = str(creds.get("access_token") or "").strip()
    refresh = str(creds.get("refresh_token") or "").strip()
    expiry_raw = creds.get("expiry")
    expired = True
    if expiry_raw:
        try:
            expiry = datetime.fromisoformat(str(expiry_raw))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            expired = expiry <= datetime.now(UTC)
        except ValueError:
            expired = True
    if access and not expired:
        return access
    if not refresh:
        raise GmailApiError("needs_reauth", needs_reauth=True)
    try:
        refreshed = refresh_access_token(refresh)
    except ValueError as exc:
        raise GmailApiError("needs_reauth", needs_reauth=True) from exc
    persist_gmail_tokens(account, refreshed)
    token = str(refreshed.get("access_token") or "").strip()
    if not token:
        raise GmailApiError("needs_reauth", needs_reauth=True)
    return token


class GoogleGmailMailbox:
    def __init__(self, account: CrmUserCommunicationAccount):
        self._account = account
        self._service: Any | None = None

    def _build(self) -> Any:
        if self._service is not None:
            return self._service
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GmailApiError("gmail_client_missing") from exc
        token = load_valid_access_token(self._account)
        creds_blob = load_account_credentials(self._account) or {}
        from investhome_api.services.crm.gmail_oauth import google_oauth_client

        client_id, client_secret = google_oauth_client()
        creds = Credentials(
            token=token,
            refresh_token=creds_blob.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=self._account.scopes,
        )
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def get_profile_history_id(self) -> str:
        service = self._build()
        try:
            profile = service.users().getProfile(userId="me").execute()
        except Exception as exc:
            raise _map_gmail_error(exc) from exc
        return str(profile.get("historyId") or "")

    def list_message_ids(self, query: str) -> Iterator[str]:
        service = self._build()
        page_token: str | None = None
        while True:
            try:
                response = (
                    service.users()
                    .messages()
                    .list(userId="me", q=query, pageToken=page_token, maxResults=100)
                    .execute()
                )
            except Exception as exc:
                raise _map_gmail_error(exc) from exc
            for item in response.get("messages") or []:
                mid = str(item.get("id") or "")
                if mid:
                    yield mid
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def get_message(self, message_id: str) -> dict[str, Any]:
        service = self._build()
        try:
            return (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as exc:
            raise _map_gmail_error(exc) from exc

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        service = self._build()
        try:
            raw = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        except Exception as exc:
            raise _map_gmail_error(exc) from exc
        return _decode_attachment(raw.get("data"))

    def list_history_message_ids(self, start_history_id: str) -> tuple[list[str], str | None]:
        service = self._build()
        page_token: str | None = None
        ids: list[str] = []
        latest: str | None = None
        while True:
            try:
                response = (
                    service.users()
                    .history()
                    .list(
                        userId="me",
                        startHistoryId=start_history_id,
                        historyTypes=["messageAdded"],
                        pageToken=page_token,
                    )
                    .execute()
                )
            except Exception as exc:
                mapped = _map_gmail_error(exc)
                if mapped.code == "history_expired":
                    raise mapped from exc
                raise mapped from exc
            latest = str(response.get("historyId") or latest or "")
            for event in response.get("history") or []:
                for added in event.get("messagesAdded") or []:
                    message = added.get("message") or {}
                    mid = str(message.get("id") or "")
                    labels = set(message.get("labelIds") or [])
                    if mid and not labels.intersection({"SPAM", "TRASH"}):
                        ids.append(mid)
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return ids, latest or None


def _map_gmail_error(exc: Exception) -> GmailApiError:
    status = getattr(getattr(exc, "resp", None), "status", None)
    text = str(exc).lower()
    if status in {401, 403} or "invalid_grant" in text:
        return GmailApiError("needs_reauth", needs_reauth=True)
    if status == 404 and "history" in text:
        return GmailApiError("history_expired")
    logger.warning("gmail_api_error type=%s", type(exc).__name__)
    return GmailApiError("gmail_api_error")
