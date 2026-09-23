"""Server-side Gmail OAuth 2.0 — reuses Google Drive client id/secret, not Drive tokens."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import (
    CrmUserCommunicationAccount,
    CrmUserCommunicationAccountHealth,
    CrmUserCommunicationAccountStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.identity import normalize_email
from investhome_api.services.crm.live_accounts import load_account_credentials
from investhome_api.services.crm_communication_activity import record_communication_audit
from investhome_api.services.crypto_seal import seal_secret

logger = logging.getLogger(__name__)

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GMAIL_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
)

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/crm/settings/communication-accounts/gmail/callback"
_STATE_TTL_SECONDS = 600
_STATE_REDIS_PREFIX = "gmail_oauth:state:"
_memory_states: dict[str, dict[str, Any]] = {}

PILOT_PROVIDER = "gmail"
PILOT_CHANNEL = "email"


def gmail_redirect_uri() -> str:
    settings = get_settings()
    override = (settings.gmail_oauth_redirect_uri or "").strip()
    if override:
        return override
    return DEFAULT_REDIRECT_URI


def google_oauth_client() -> tuple[str, str]:
    """Reuse the existing Drive OAuth client. Never return Drive's refresh token."""
    settings = get_settings()
    client_id = (settings.google_drive_client_id or "").strip()
    client_secret = (settings.google_drive_client_secret or "").strip()
    if not client_id or not client_secret:
        raise ValueError("gmail_not_configured")
    return client_id, client_secret


def gmail_oauth_configured() -> bool:
    try:
        google_oauth_client()
        return True
    except ValueError:
        return False


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    import base64

    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    return secrets.token_urlsafe(48)


def _redis_client():
    settings = get_settings()
    from redis import Redis

    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1.5,
        socket_timeout=1.5,
        decode_responses=True,
    )


def save_oauth_state(*, state: str, code_verifier: str, user_id: str | None = None) -> None:
    payload = {
        "code_verifier": code_verifier,
        "user_id": user_id,
        "created_at": time.time(),
    }
    serialized = json.dumps(payload)
    try:
        client = _redis_client()
        client.setex(f"{_STATE_REDIS_PREFIX}{state}", _STATE_TTL_SECONDS, serialized)
        return
    except Exception:
        logger.debug("gmail_oauth_state_redis_unavailable", exc_info=True)
    _memory_states[state] = {**payload, "expires_at": time.time() + _STATE_TTL_SECONDS}


def pop_oauth_state(state: str) -> dict[str, Any] | None:
    try:
        client = _redis_client()
        key = f"{_STATE_REDIS_PREFIX}{state}"
        raw = client.get(key)
        if raw:
            client.delete(key)
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("gmail_oauth_state_redis_pop_failed", exc_info=True)

    entry = _memory_states.pop(state, None)
    if not entry:
        return None
    if float(entry.get("expires_at", 0)) < time.time():
        return None
    return {
        "code_verifier": entry.get("code_verifier"),
        "user_id": entry.get("user_id"),
        "created_at": entry.get("created_at"),
    }


def clear_memory_states() -> None:
    _memory_states.clear()


def start_authorization(*, user_id: str | None = None) -> str:
    client_id, _ = google_oauth_client()
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()
    save_oauth_state(state=state, code_verifier=code_verifier, user_id=user_id)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": gmail_redirect_uri(),
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "false",
        }
    )
    return f"{GOOGLE_AUTHORIZE_URL}?{query}"


def _http() -> httpx.Client:
    return httpx.Client(timeout=20.0)


def exchange_authorization_code(*, code: str, code_verifier: str) -> dict[str, Any]:
    client_id, client_secret = google_oauth_client()
    with _http() as http:
        response = http.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": gmail_redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
    if response.status_code >= 400:
        logger.warning("gmail_oauth_token_exchange_failed status=%s", response.status_code)
        raise ValueError("token_exchange_failed")
    data = response.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise ValueError("token_exchange_failed")
    if "gmail.readonly" not in str(data.get("scope") or " ".join(GMAIL_SCOPES)):
        logger.warning("gmail_oauth_scope_missing_readonly")
    return data


def fetch_google_userinfo(access_token: str) -> dict[str, Any]:
    with _http() as http:
        response = http.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        logger.warning("gmail_oauth_userinfo_failed status=%s", response.status_code)
        raise ValueError("token_exchange_failed")
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("token_exchange_failed")
    return data


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    client_id, client_secret = google_oauth_client()
    with _http() as http:
        response = http.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code >= 400:
        logger.warning("gmail_oauth_refresh_failed status=%s", response.status_code)
        raise ValueError("needs_reauth")
    data = response.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise ValueError("needs_reauth")
    return data


def _token_blob(token_response: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    expires_in = int(token_response.get("expires_in") or 3600)
    expiry = datetime.now(UTC) + timedelta(seconds=max(expires_in - 60, 30))
    refresh = token_response.get("refresh_token") or (existing or {}).get("refresh_token")
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": refresh,
        "token_type": token_response.get("token_type") or "Bearer",
        "expiry": expiry.isoformat(),
        "scope": token_response.get("scope") or " ".join(GMAIL_SCOPES),
        "google_sub": (existing or {}).get("google_sub"),
    }


def persist_gmail_tokens(
    account: CrmUserCommunicationAccount,
    token_response: dict[str, Any],
    *,
    google_sub: str | None = None,
) -> None:
    existing = load_account_credentials(account) or {}
    blob = _token_blob(token_response, existing=existing)
    if google_sub:
        blob["google_sub"] = google_sub
    elif existing.get("google_sub"):
        blob["google_sub"] = existing["google_sub"]
    account.encrypted_credentials = seal_secret(blob)
    account.scopes = list(GMAIL_SCOPES)


def connected_gmail_accounts(db: Session) -> list[CrmUserCommunicationAccount]:
    return list(
        db.scalars(
            select(CrmUserCommunicationAccount).where(
                CrmUserCommunicationAccount.provider == PILOT_PROVIDER,
                CrmUserCommunicationAccount.channel_type == PILOT_CHANNEL,
                CrmUserCommunicationAccount.archived_at.is_(None),
                CrmUserCommunicationAccount.status.in_(
                    [
                        CrmUserCommunicationAccountStatus.CONNECTED.value,
                        CrmUserCommunicationAccountStatus.PENDING.value,
                        CrmUserCommunicationAccountStatus.ERROR.value,
                        CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value,
                    ]
                ),
            )
        ).all()
    )


def complete_authorization(
    db: Session,
    *,
    code: str,
    state: str,
) -> CrmUserCommunicationAccount:
    saved = pop_oauth_state(state)
    if not saved or not saved.get("code_verifier"):
        raise ValueError("invalid_state")
    user_id_raw = saved.get("user_id")
    if not user_id_raw:
        raise ValueError("invalid_state")
    try:
        user_id = UUID(str(user_id_raw))
    except ValueError as exc:
        raise ValueError("invalid_state") from exc
    actor = db.get(User, user_id)
    if actor is None:
        raise ValueError("invalid_state")

    tokens = exchange_authorization_code(code=code, code_verifier=str(saved["code_verifier"]))
    userinfo = fetch_google_userinfo(str(tokens["access_token"]))
    email = normalize_email(str(userinfo.get("email") or ""))
    google_sub = str(userinfo.get("sub") or "").strip() or None
    if not email:
        raise ValueError("token_exchange_failed")

    existing_same = db.scalar(
        select(CrmUserCommunicationAccount).where(
            CrmUserCommunicationAccount.channel_type == PILOT_CHANNEL,
            CrmUserCommunicationAccount.identity == email,
        )
    )
    others = [item for item in connected_gmail_accounts(db) if item.identity != email]
    if others and (existing_same is None or existing_same.archived_at is not None):
        raise ValueError("gmail_pilot_limit")

    if existing_same:
        account = existing_same
        account.archived_at = None
        account.user_id = user_id
        account.account_label = account.account_label or email
    else:
        account = CrmUserCommunicationAccount(
            user_id=user_id,
            channel_type=PILOT_CHANNEL,
            provider=PILOT_PROVIDER,
            identity=email,
            account_label=email,
            created_by=user_id,
        )
        db.add(account)
        db.flush()

    persist_gmail_tokens(account, tokens, google_sub=google_sub)
    account.status = CrmUserCommunicationAccountStatus.CONNECTED.value
    account.health = CrmUserCommunicationAccountHealth.HEALTHY.value
    account.last_error = None
    meta = dict(account.metadata_json or {})
    meta.update(
        {
            "google_sub": google_sub,
            "gmail_address": email,
            "sync_pending": True,
        }
    )
    account.metadata_json = meta
    record_communication_audit(
        db,
        event_type="account.gmail_connected",
        actor=actor,
        details={"account_id": str(account.id), "identity": email, "google_sub": google_sub},
    )
    logger.info("gmail_oauth_connected account=%s user=%s", account.id, user_id)
    return account


def mark_needs_reauth(account: CrmUserCommunicationAccount, *, error: str) -> None:
    account.status = CrmUserCommunicationAccountStatus.NEEDS_REAUTH.value
    account.health = CrmUserCommunicationAccountHealth.ERROR.value
    account.last_error = error[:500]
