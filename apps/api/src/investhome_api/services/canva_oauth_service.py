"""Canva Connect OAuth 2.0 + PKCE — authorize, token exchange, credential storage."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.company_foundation import SystemPreference
from investhome_api.models.platform_core import IntegrationStatus, PlatformIntegration

logger = logging.getLogger(__name__)

CANVA_AUTHORIZE_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
# Must match Canva Developer Portal redirect URL exactly.
CANVA_REDIRECT_URI = "http://127.0.0.1:8000/platform/integrations/canva/callback"

CANVA_SCOPES = (
    "asset:read",
    "asset:write",
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "design:meta:write",
    "profile:read",
)

_PREF_KEY = "integrations.canva_oauth_tokens"
_STATE_TTL_SECONDS = 600
_STATE_REDIS_PREFIX = "canva_oauth:state:"

# Process-local fallback when Redis is unavailable (tests / single-worker dev).
_memory_states: dict[str, dict[str, Any]] = {}


def generate_code_verifier() -> str:
    """PKCE code_verifier: 43–128 URL-safe characters."""
    return secrets.token_urlsafe(64)[:128]


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    return secrets.token_urlsafe(48)


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _seal(payload: dict[str, Any], secret: str) -> str:
    """Obfuscate token payload at rest using JWT_SECRET (no new crypto dependency)."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    key = hashlib.sha256(f"canva-oauth-v1:{secret}".encode("utf-8")).digest()
    # Pad to body length via repeated HMAC blocks
    pad = bytearray()
    counter = 0
    while len(pad) < len(body):
        pad.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    cipher = bytes(a ^ b for a, b in zip(body, pad[: len(body)], strict=True))
    mac = hmac.new(key, cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac + cipher).decode("ascii")


def _unseal(token: str, secret: str) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(raw) < 33:
            return None
        mac, cipher = raw[:32], raw[32:]
        key = hashlib.sha256(f"canva-oauth-v1:{secret}".encode("utf-8")).digest()
        expected = hmac.new(key, cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        pad = bytearray()
        counter = 0
        while len(pad) < len(cipher):
            pad.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
            counter += 1
        body = bytes(a ^ b for a, b in zip(cipher, pad[: len(cipher)], strict=True))
        data = json.loads(body.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


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
        logger.debug("Canva OAuth state Redis unavailable; using memory store", exc_info=True)
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
        logger.debug("Canva OAuth state Redis pop failed; trying memory", exc_info=True)

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
    """Test helper."""
    _memory_states.clear()


def require_canva_credentials() -> tuple[str, str]:
    settings = get_settings()
    client_id = (settings.canva_client_id or "").strip()
    client_secret = (settings.canva_client_secret or "").strip()
    if not client_id or not client_secret:
        raise ValueError("canva_not_configured")
    return client_id, client_secret


def build_authorize_url(*, state: str, code_challenge: str, client_id: str) -> str:
    query = urlencode(
        {
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": " ".join(CANVA_SCOPES),
            "response_type": "code",
            "client_id": client_id,
            "state": state,
            "redirect_uri": CANVA_REDIRECT_URI,
        }
    )
    return f"{CANVA_AUTHORIZE_URL}?{query}"


def start_authorization(*, user_id: str | None = None) -> str:
    client_id, _ = require_canva_credentials()
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()
    save_oauth_state(state=state, code_verifier=code_verifier, user_id=user_id)
    return build_authorize_url(state=state, code_challenge=code_challenge, client_id=client_id)


def exchange_authorization_code(*, code: str, code_verifier: str) -> dict[str, Any]:
    client_id, client_secret = require_canva_credentials()
    headers = {
        "Authorization": _basic_auth_header(client_id, client_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
        "code": code,
        "redirect_uri": CANVA_REDIRECT_URI,
    }
    with http_client() as client:
        response = client.post(CANVA_TOKEN_URL, headers=headers, data=data)
    if response.status_code >= 400:
        logger.warning("Canva token exchange failed status=%s", response.status_code)
        raise ValueError("token_exchange_failed")
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise ValueError("token_exchange_failed")
    return payload


def http_client() -> httpx.Client:
    """Shared Canva HTTP client (timeout only — no credentials in constructor)."""
    return httpx.Client(timeout=30.0)


def refresh_access_token(*, refresh_token: str) -> dict[str, Any]:
    """Exchange a Canva refresh token for a new access + refresh token pair (single-use)."""
    client_id, client_secret = require_canva_credentials()
    headers = {
        "Authorization": _basic_auth_header(client_id, client_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    with http_client() as client:
        response = client.post(CANVA_TOKEN_URL, headers=headers, data=data)
    if response.status_code >= 400:
        logger.warning("Canva token refresh failed status=%s", response.status_code)
        raise ValueError("canva_token_refresh_failed")
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise ValueError("canva_token_refresh_failed")
    return payload


def _parse_expires_at(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def access_token_needs_refresh(tokens: dict[str, Any], *, skew_seconds: int = 60) -> bool:
    expires_at = _parse_expires_at(tokens.get("expires_at"))
    if expires_at is None:
        return False
    return datetime.now(UTC) + timedelta(seconds=skew_seconds) >= expires_at


def refresh_and_store_tokens(db: Session, tokens: dict[str, Any]) -> dict[str, Any]:
    refresh = str(tokens.get("refresh_token") or "").strip()
    if not refresh:
        raise ValueError("canva_not_connected")
    payload = refresh_access_token(refresh_token=refresh)
    if not payload.get("refresh_token"):
        payload["refresh_token"] = refresh
    store_tokens(db, payload)
    db.flush()
    stored = get_stored_tokens(db)
    if not stored or not stored.get("access_token"):
        raise ValueError("canva_token_refresh_failed")
    return stored


def get_valid_access_token(db: Session) -> str:
    """Return a live Canva access token, refreshing via stored OAuth credentials if needed."""
    tokens = get_stored_tokens(db)
    if not tokens or not str(tokens.get("access_token") or "").strip():
        raise ValueError("canva_not_connected")
    if access_token_needs_refresh(tokens):
        tokens = refresh_and_store_tokens(db, tokens)
    return str(tokens["access_token"])


def store_tokens(db: Session, token_payload: dict[str, Any]) -> None:
    settings = get_settings()
    expires_in = int(token_payload.get("expires_in") or 0)
    expires_at = (
        (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat() if expires_in else None
    )
    record = {
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "token_type": token_payload.get("token_type") or "Bearer",
        "expires_in": expires_in,
        "expires_at": expires_at,
        "scope": token_payload.get("scope"),
        "connected_at": datetime.now(UTC).isoformat(),
    }
    sealed = _seal(record, settings.jwt_secret)
    pref = db.scalar(select(SystemPreference).where(SystemPreference.preference_key == _PREF_KEY))
    if pref is None:
        pref = SystemPreference(
            category="integrations",
            preference_key=_PREF_KEY,
            value_json={"value": sealed},
            is_secret=True,
        )
        db.add(pref)
    else:
        pref.value_json = {"value": sealed}
        pref.is_secret = True

    integration = db.scalar(select(PlatformIntegration).where(PlatformIntegration.code == "canva"))
    if integration is None:
        integration = PlatformIntegration(
            code="canva",
            name_en="Canva",
            name_tr="Canva",
            category="creative",
            status=IntegrationStatus.CONNECTED.value,
            description_en="Canva Connect OAuth connected",
            description_tr="Canva Connect OAuth bağlı",
            env_keys_json=["CANVA_CLIENT_ID", "CANVA_CLIENT_SECRET"],
            configured=True,
            sort_order=6,
            metadata_json={"has_tokens": True, "connected_at": record["connected_at"]},
        )
        db.add(integration)
    else:
        integration.status = IntegrationStatus.CONNECTED.value
        integration.configured = True
        integration.env_keys_json = ["CANVA_CLIENT_ID", "CANVA_CLIENT_SECRET"]
        integration.description_en = "Canva Connect OAuth connected"
        integration.description_tr = "Canva Connect OAuth bağlı"
        meta = dict(integration.metadata_json or {})
        meta["has_tokens"] = True
        meta["connected_at"] = record["connected_at"]
        # Never put raw tokens in metadata_json
        meta.pop("access_token", None)
        meta.pop("refresh_token", None)
        integration.metadata_json = meta
    db.flush()


def get_stored_tokens(db: Session) -> dict[str, Any] | None:
    pref = db.scalar(select(SystemPreference).where(SystemPreference.preference_key == _PREF_KEY))
    if pref is None or not pref.value_json:
        return None
    sealed = pref.value_json.get("value")
    if not isinstance(sealed, str) or not sealed:
        return None
    return _unseal(sealed, get_settings().jwt_secret)


def is_canva_connected(db: Session) -> bool:
    tokens = get_stored_tokens(db)
    if not tokens or not tokens.get("access_token"):
        return False
    return True


def disconnect_canva(db: Session) -> None:
    pref = db.scalar(select(SystemPreference).where(SystemPreference.preference_key == _PREF_KEY))
    if pref is not None:
        pref.value_json = {"value": None}

    integration = db.scalar(select(PlatformIntegration).where(PlatformIntegration.code == "canva"))
    if integration is not None:
        integration.status = IntegrationStatus.NOT_CONNECTED.value
        integration.configured = False
        integration.description_en = "Connect Canva via OAuth 2.0 + PKCE"
        integration.description_tr = "Canva'yı OAuth 2.0 + PKCE ile bağlayın"
        meta = dict(integration.metadata_json or {})
        meta["has_tokens"] = False
        meta.pop("connected_at", None)
        integration.metadata_json = meta
    db.flush()
