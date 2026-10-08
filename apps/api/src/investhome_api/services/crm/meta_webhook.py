"""Meta Page / Messenger and Instagram DM inbound webhook.

Isolated from WhatsApp Cloud API handling. Outbound send lives in meta_send.
Does not create sales opportunities.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings, validate_meta_webhook_secrets
from investhome_api.core.logging_config import get_logger
from investhome_api.models.activity import ActivityAction
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.crm.crm_lead_service import _log, _put_meta
from investhome_api.services.crm.live_ingest import ingest_live_message
from investhome_api.services.crm.whatsapp_webhook import verify_meta_signature, verify_token_matches

logger = get_logger("investhome.meta.webhook")

SIGNATURE_HEADER = "X-Hub-Signature-256"
IDEMPOTENCY_PREFIX = "meta:webhook:idemp:"
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_WEBHOOK_BYTES = 256_000
GENERIC_FORBIDDEN = "Forbidden"
GENERIC_UNAVAILABLE = "Webhook temporarily unavailable"
FACEBOOK_PSID_KEY = "facebook_psid"
FACEBOOK_SOURCE = "facebook"
INSTAGRAM_IGSID_KEY = "instagram_igsid"
INSTAGRAM_SOURCE = "instagram"


class MetaWebhookRejected(Exception):
    def __init__(self, status_code: int, public_detail: str) -> None:
        super().__init__(public_detail)
        self.status_code = status_code
        self.public_detail = public_detail


class MetaIdempotencyStoreError(Exception):
    """Raised when the replay-protection backend cannot apply the policy."""


class MetaIdempotencyStore(Protocol):
    def claim(self, key: str, ttl_seconds: int) -> bool:
        """Return True if this key was newly claimed."""


@dataclass
class _MemoryEntry:
    expires_at: float


class InMemoryMetaIdempotencyStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, _MemoryEntry] = {}
        self._now = now or time.time

    def claim(self, key: str, ttl_seconds: int) -> bool:
        now = self._now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return False
            self._entries[key] = _MemoryEntry(expires_at=now + ttl_seconds)
            return True

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class RedisMetaIdempotencyStore:
    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def _redis(self) -> object:
        if self._client is not None:
            return self._client
        from redis import Redis

        settings = get_settings()
        self._client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            decode_responses=True,
        )
        return self._client

    def claim(self, key: str, ttl_seconds: int) -> bool:
        try:
            client = self._redis()
            created = client.set(key, "1", nx=True, ex=max(1, ttl_seconds))
            return bool(created)
        except Exception as exc:
            raise MetaIdempotencyStoreError("redis meta idempotency failed") from exc


_store: MetaIdempotencyStore | None = None
_memory_fallback = InMemoryMetaIdempotencyStore()


def reset_meta_idempotency_for_tests(store: MetaIdempotencyStore | None = None) -> None:
    global _store, _memory_fallback
    _memory_fallback = InMemoryMetaIdempotencyStore()
    _store = store if store is not None else _memory_fallback


def get_meta_idempotency_store() -> MetaIdempotencyStore:
    global _store
    if _store is None:
        _store = RedisMetaIdempotencyStore()
    return _store


def _is_production() -> bool:
    return (get_settings().environment or "").strip().lower() in {"production", "prod"}


def require_meta_app_secret() -> str:
    settings = get_settings()
    if _is_production():
        validate_meta_webhook_secrets(settings)
    secret = (settings.meta_app_secret or "").strip()
    if not secret:
        logger.warning("meta_webhook_missing_app_secret")
        raise MetaWebhookRejected(503, GENERIC_UNAVAILABLE)
    return secret


def require_meta_verify_token() -> str:
    settings = get_settings()
    if _is_production():
        validate_meta_webhook_secrets(settings)
    token = (settings.meta_verify_token or "").strip()
    if not token:
        logger.warning("meta_webhook_missing_verify_token")
        raise MetaWebhookRejected(503, GENERIC_UNAVAILABLE)
    return token


def require_meta_page_id() -> str:
    settings = get_settings()
    if _is_production():
        validate_meta_webhook_secrets(settings)
    page_id = (settings.meta_page_id or "").strip()
    if not page_id:
        logger.warning("meta_webhook_missing_page_id")
        raise MetaWebhookRejected(503, GENERIC_UNAVAILABLE)
    return page_id


def handle_verification_challenge(
    *,
    hub_mode: str | None,
    hub_verify_token: str | None,
    hub_challenge: str | None,
) -> str:
    expected = require_meta_verify_token()
    if (hub_mode or "").strip() != "subscribe":
        logger.warning("meta_webhook_handshake_invalid_mode")
        raise MetaWebhookRejected(403, GENERIC_FORBIDDEN)
    if not verify_token_matches(configured=expected, provided=hub_verify_token):
        logger.warning("meta_webhook_handshake_token_mismatch")
        raise MetaWebhookRejected(403, GENERIC_FORBIDDEN)
    challenge = (hub_challenge or "").strip()
    if not challenge or len(challenge) > 128 or any(ch.isspace() for ch in challenge):
        logger.warning("meta_webhook_handshake_malformed_challenge")
        raise MetaWebhookRejected(400, "invalid_request")
    return challenge


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _facebook_psid_from_meta(meta: object) -> str | None:
    if not isinstance(meta, dict):
        return None
    direct = str(meta.get(FACEBOOK_PSID_KEY) or "").strip()
    if direct:
        return direct
    nested = meta.get("facebook")
    if isinstance(nested, dict):
        return str(nested.get("psid") or "").strip() or None
    return None


def _placeholder_name(psid: str) -> str:
    suffix = psid[-6:] if len(psid) > 6 else psid
    return f"Facebook · {suffix}"


def _store_psid(meta: dict[str, Any] | None, psid: str) -> dict[str, Any]:
    data = dict(meta) if isinstance(meta, dict) else {}
    data[FACEBOOK_PSID_KEY] = psid
    facebook = data.get("facebook")
    nested = dict(facebook) if isinstance(facebook, dict) else {}
    nested["psid"] = psid
    nested.setdefault("kind", "messenger")
    data["facebook"] = nested
    return data


def find_contact_by_facebook_psid(db: Session, psid: str) -> CrmContact | None:
    if not psid:
        return None
    contacts = list(db.scalars(select(CrmContact).where(CrmContact.archived_at.is_(None))).all())
    for contact in contacts:
        if _facebook_psid_from_meta(contact.metadata_json) == psid:
            return contact
    return None


def find_lead_by_facebook_psid(db: Session, psid: str) -> Lead | None:
    if not psid:
        return None
    leads = list(
        db.scalars(
            select(Lead).where(
                Lead.archived_at.is_(None),
                Lead.provider == FACEBOOK_SOURCE,
            )
        ).all()
    )
    for lead in leads:
        if _facebook_psid_from_meta(lead.metadata_json) == psid:
            return lead
    return None


def _lead_is_active(lead: Lead | None) -> bool:
    return lead is not None and lead.archived_at is None and not lead.is_demo


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _active_facebook_lead_for_contact(db: Session, *, contact: CrmContact, psid: str) -> Lead | None:
    """Reuse the existing live Lead for this Messenger person. Never invent a second one."""
    if contact.lead_id is not None:
        linked = db.get(Lead, contact.lead_id)
        if _lead_is_active(linked):
            return linked
    by_psid = find_lead_by_facebook_psid(db, psid)
    if _lead_is_active(by_psid):
        if contact.lead_id is None:
            contact.lead_id = by_psid.id
            db.flush()
        return by_psid
    converted = db.scalar(
        select(Lead)
        .where(
            Lead.converted_contact_id == contact.id,
            Lead.archived_at.is_(None),
            Lead.is_demo.is_(False),
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    if _lead_is_active(converted):
        if contact.lead_id is None:
            contact.lead_id = converted.id
            db.flush()
        return converted
    return None


def _record_meta_dm_on_lead(
    db: Session,
    *,
    lead: Lead,
    contact: CrmContact,
    mid: str,
    text: str,
    occurred_at: datetime | None,
    communication_id: UUID,
    description_key: str,
    provider: str,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    occurred = _as_utc(occurred_at or datetime.now(UTC))
    preview = (text or "").strip()[:200] or None
    meta_kwargs: dict[str, Any] = {
        "last_communication_id": str(communication_id),
        "existing_person_id": str(contact.id),
        "existing_person_name": contact.display_name,
    }
    if provider == FACEBOOK_SOURCE:
        meta_kwargs["last_messenger_mid"] = mid
        meta_kwargs["last_messenger_at"] = occurred.isoformat()
    else:
        meta_kwargs["last_instagram_mid"] = mid
        meta_kwargs["last_instagram_at"] = occurred.isoformat()
    _put_meta(lead, **meta_kwargs)
    payload = {
        "provider": provider,
        "source": provider,
        "mid": mid,
        "preview": preview,
        "communication_id": str(communication_id),
        "contact_id": str(contact.id),
    }
    if extra_meta:
        payload.update(extra_meta)
    _log(
        db,
        lead,
        action=ActivityAction.UPDATED,
        description_key=description_key,
        actor=None,
        metadata=payload,
        created_at=occurred,
    )
    db.flush()
    db.execute(sql_update(Lead).where(Lead.id == lead.id).values(updated_at=occurred))
    lead.updated_at = occurred


def _record_facebook_message_on_lead(
    db: Session,
    *,
    lead: Lead,
    contact: CrmContact,
    message: "MessengerInbound",
    communication_id: UUID,
) -> None:
    _record_meta_dm_on_lead(
        db,
        lead=lead,
        contact=contact,
        mid=message.mid,
        text=message.text,
        occurred_at=message.occurred_at,
        communication_id=communication_id,
        description_key="crm.leads.facebook_messenger.received",
        provider=FACEBOOK_SOURCE,
    )


def _create_facebook_lead(db: Session, *, contact: CrmContact, psid: str, display_name: str) -> Lead:
    lead = Lead(
        full_name=display_name,
        email=None,
        phone=None,
        source=FACEBOOK_SOURCE,
        notes="Facebook Messenger",
        status=LeadStatus.NEW,
        provider=FACEBOOK_SOURCE,
        ingest_status="ok",
        is_demo=False,
    )
    db.add(lead)
    db.flush()
    _put_meta(
        lead,
        intake="facebook_messenger",
        facebook_psid=psid,
        facebook={"psid": psid, "kind": "dm"},
        existing_person_id=str(contact.id),
        existing_person_name=contact.display_name,
    )
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key="crm.leads.created",
        actor=None,
        metadata={"provider": FACEBOOK_SOURCE, "source": FACEBOOK_SOURCE},
    )
    if contact.lead_id is None:
        contact.lead_id = lead.id
    db.flush()
    return lead


def resolve_facebook_sender(db: Session, *, psid: str) -> CrmContact:
    """Attach to an existing PSID contact, or create Contact + Lead once."""
    existing = find_contact_by_facebook_psid(db, psid)
    if existing is not None:
        if _active_facebook_lead_for_contact(db, contact=existing, psid=psid) is None:
            _create_facebook_lead(
                db,
                contact=existing,
                psid=psid,
                display_name=existing.display_name or _placeholder_name(psid),
            )
        return existing

    display_name = _placeholder_name(psid)
    existing_lead = find_lead_by_facebook_psid(db, psid)
    if existing_lead is not None and existing_lead.converted_contact_id:
        linked = db.get(CrmContact, existing_lead.converted_contact_id)
        if linked is not None and linked.archived_at is None:
            linked.metadata_json = _store_psid(linked.metadata_json, psid)
            db.flush()
            return linked

    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.PROSPECT,
            record_kind=CrmRecordKind.PERSON,
            display_name=display_name,
            source=FACEBOOK_SOURCE,
            notes="Facebook Messenger",
            lifecycle_stage=CrmLifecycleStage.NEW,
            status=CrmContactStatus.PROSPECT,
        ),
        actor=None,
    )
    contact.metadata_json = _store_psid(contact.metadata_json, psid)
    db.flush()

    if existing_lead is None:
        _create_facebook_lead(db, contact=contact, psid=psid, display_name=display_name)
    else:
        if existing_lead.converted_contact_id is None:
            existing_lead.converted_contact_id = contact.id
        if contact.lead_id is None:
            contact.lead_id = existing_lead.id
        db.flush()
    return contact


def _message_timestamp(raw: object) -> datetime | None:
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value > 10_000_000_000:
        value = value / 1000
    return datetime.fromtimestamp(value, tz=UTC)


@dataclass(frozen=True)
class MessengerInbound:
    mid: str
    psid: str
    page_id: str
    text: str
    occurred_at: datetime | None


def extract_messenger_messages(payload: dict[str, Any], *, page_id: str) -> tuple[list[MessengerInbound], int]:
    """Return supported inbound DMs for the configured page, plus ignored-page count."""
    messages: list[MessengerInbound] = []
    unknown_pages = 0
    seen: set[str] = set()
    expected = page_id.strip()
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        if entry_id != expected:
            unknown_pages += 1
            logger.info("meta_webhook_unknown_page")
            continue
        for event in entry.get("messaging") or []:
            if not isinstance(event, dict):
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            if message.get("is_echo"):
                continue
            sender = _dict(event.get("sender"))
            recipient = _dict(event.get("recipient"))
            psid = str(sender.get("id") or "").strip()
            recipient_id = str(recipient.get("id") or "").strip()
            if not psid or psid == expected:
                continue
            if recipient_id and recipient_id != expected:
                continue
            mid = str(message.get("mid") or message.get("id") or "").strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            text = str(message.get("text") or "")
            occurred_at = _message_timestamp(event.get("timestamp") or message.get("timestamp"))
            messages.append(
                MessengerInbound(
                    mid=mid,
                    psid=psid,
                    page_id=entry_id,
                    text=text,
                    occurred_at=occurred_at,
                )
            )
    return messages, unknown_pages


def configured_instagram_account_id() -> str | None:
    return (get_settings().meta_instagram_account_id or "").strip() or None


def _instagram_igsid_from_meta(meta: object) -> str | None:
    if not isinstance(meta, dict):
        return None
    direct = str(meta.get(INSTAGRAM_IGSID_KEY) or "").strip()
    if direct:
        return direct
    nested = meta.get("instagram")
    if isinstance(nested, dict):
        return str(nested.get("igsid") or nested.get("id") or "").strip() or None
    return None


def _placeholder_instagram_name(igsid: str) -> str:
    suffix = igsid[-6:] if len(igsid) > 6 else igsid
    return f"Instagram · {suffix}"


def _store_igsid(meta: dict[str, Any] | None, igsid: str) -> dict[str, Any]:
    data = dict(meta) if isinstance(meta, dict) else {}
    data[INSTAGRAM_IGSID_KEY] = igsid
    instagram = data.get("instagram")
    nested = dict(instagram) if isinstance(instagram, dict) else {}
    nested["igsid"] = igsid
    nested.setdefault("kind", "dm")
    data["instagram"] = nested
    return data


def find_contact_by_instagram_igsid(db: Session, igsid: str) -> CrmContact | None:
    if not igsid:
        return None
    contacts = list(db.scalars(select(CrmContact).where(CrmContact.archived_at.is_(None))).all())
    for contact in contacts:
        if _instagram_igsid_from_meta(contact.metadata_json) == igsid:
            return contact
    return None


def find_lead_by_instagram_igsid(db: Session, igsid: str) -> Lead | None:
    if not igsid:
        return None
    leads = list(
        db.scalars(
            select(Lead).where(
                Lead.archived_at.is_(None),
                Lead.provider == INSTAGRAM_SOURCE,
            )
        ).all()
    )
    for lead in leads:
        if _instagram_igsid_from_meta(lead.metadata_json) == igsid:
            return lead
    return None


def _active_instagram_lead_for_contact(db: Session, *, contact: CrmContact, igsid: str) -> Lead | None:
    if contact.lead_id is not None:
        linked = db.get(Lead, contact.lead_id)
        if _lead_is_active(linked):
            return linked
    by_igsid = find_lead_by_instagram_igsid(db, igsid)
    if _lead_is_active(by_igsid):
        if contact.lead_id is None:
            contact.lead_id = by_igsid.id
            db.flush()
        return by_igsid
    converted = db.scalar(
        select(Lead)
        .where(
            Lead.converted_contact_id == contact.id,
            Lead.archived_at.is_(None),
            Lead.is_demo.is_(False),
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    if _lead_is_active(converted):
        if contact.lead_id is None:
            contact.lead_id = converted.id
            db.flush()
        return converted
    return None


def _create_instagram_lead(db: Session, *, contact: CrmContact, igsid: str, display_name: str) -> Lead:
    lead = Lead(
        full_name=display_name,
        email=None,
        phone=None,
        source=INSTAGRAM_SOURCE,
        notes="Instagram Direct",
        status=LeadStatus.NEW,
        provider=INSTAGRAM_SOURCE,
        ingest_status="ok",
        is_demo=False,
    )
    db.add(lead)
    db.flush()
    _put_meta(
        lead,
        intake="instagram_dm",
        instagram_igsid=igsid,
        instagram={"igsid": igsid, "kind": "dm"},
        existing_person_id=str(contact.id),
        existing_person_name=contact.display_name,
    )
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key="crm.leads.created",
        actor=None,
        metadata={"provider": INSTAGRAM_SOURCE, "source": INSTAGRAM_SOURCE},
    )
    if contact.lead_id is None:
        contact.lead_id = lead.id
    db.flush()
    return lead


def resolve_instagram_sender(db: Session, *, igsid: str) -> CrmContact:
    existing = find_contact_by_instagram_igsid(db, igsid)
    if existing is not None:
        if _active_instagram_lead_for_contact(db, contact=existing, igsid=igsid) is None:
            _create_instagram_lead(
                db,
                contact=existing,
                igsid=igsid,
                display_name=existing.display_name or _placeholder_instagram_name(igsid),
            )
        return existing

    display_name = _placeholder_instagram_name(igsid)
    existing_lead = find_lead_by_instagram_igsid(db, igsid)
    if existing_lead is not None and existing_lead.converted_contact_id:
        linked = db.get(CrmContact, existing_lead.converted_contact_id)
        if linked is not None and linked.archived_at is None:
            linked.metadata_json = _store_igsid(linked.metadata_json, igsid)
            db.flush()
            return linked

    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.PROSPECT,
            record_kind=CrmRecordKind.PERSON,
            display_name=display_name,
            source=INSTAGRAM_SOURCE,
            notes="Instagram Direct",
            lifecycle_stage=CrmLifecycleStage.NEW,
            status=CrmContactStatus.PROSPECT,
        ),
        actor=None,
    )
    contact.metadata_json = _store_igsid(contact.metadata_json, igsid)
    db.flush()

    if existing_lead is None:
        _create_instagram_lead(db, contact=contact, igsid=igsid, display_name=display_name)
    else:
        if existing_lead.converted_contact_id is None:
            existing_lead.converted_contact_id = contact.id
        if contact.lead_id is None:
            contact.lead_id = existing_lead.id
        db.flush()
    return contact


@dataclass(frozen=True)
class InstagramInbound:
    mid: str
    igsid: str
    ig_account_id: str
    text: str
    occurred_at: datetime | None


def extract_instagram_messages(payload: dict[str, Any], *, account_id: str | None) -> list[InstagramInbound]:
    messages: list[InstagramInbound] = []
    seen: set[str] = set()
    expected = (account_id or "").strip() or None
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        if expected and entry_id != expected:
            logger.info("meta_webhook_unknown_instagram_account")
            continue
        for event in entry.get("messaging") or []:
            if not isinstance(event, dict):
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            if message.get("is_echo"):
                continue
            sender = _dict(event.get("sender"))
            recipient = _dict(event.get("recipient"))
            igsid = str(sender.get("id") or "").strip()
            recipient_id = str(recipient.get("id") or "").strip()
            if not igsid or (expected and igsid == expected):
                continue
            if recipient_id and expected and recipient_id != expected:
                continue
            mid = str(message.get("mid") or message.get("id") or "").strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            text = str(message.get("text") or "")
            occurred_at = _message_timestamp(event.get("timestamp") or message.get("timestamp"))
            messages.append(
                InstagramInbound(
                    mid=mid,
                    igsid=igsid,
                    ig_account_id=entry_id,
                    text=text,
                    occurred_at=occurred_at,
                )
            )
    return messages


def _ingest_instagram_messages(db: Session, messages: list[InstagramInbound], claimed: set[str]) -> int:
    created = 0
    for item in messages:
        if f"ig:msg:{item.mid}" not in claimed:
            continue
        contact = resolve_instagram_sender(db, igsid=item.igsid)
        lead = _active_instagram_lead_for_contact(db, contact=contact, igsid=item.igsid)
        comm, was_created = ingest_live_message(
            db,
            {
                "channel": "instagram",
                "direction": "incoming",
                "source": "live_instagram",
                "sender": item.igsid,
                "body_text": item.text,
                "external_provider_id": item.mid,
                "conversation_key": item.igsid,
                "occurred_at": item.occurred_at,
                "contact_id": str(contact.id),
                "metadata_json": {
                    "kind": "dm",
                    INSTAGRAM_IGSID_KEY: item.igsid,
                    "ig_account_id": item.ig_account_id,
                    **({"lead_id": str(lead.id)} if lead is not None else {}),
                },
            },
            actor=None,
        )
        if was_created:
            created += 1
            if lead is not None:
                _record_meta_dm_on_lead(
                    db,
                    lead=lead,
                    contact=contact,
                    mid=item.mid,
                    text=item.text,
                    occurred_at=item.occurred_at,
                    communication_id=comm.id,
                    description_key="crm.leads.instagram_dm.received",
                    provider=INSTAGRAM_SOURCE,
                )
    return created


def _process_instagram(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    messages = extract_instagram_messages(payload, account_id=configured_instagram_account_id())
    if not messages:
        return {"ok": True, "duplicate": False, "ingested": 0}
    keys = [f"ig:msg:{item.mid}" for item in messages]
    claimed, duplicates = _claim_keys(keys)
    if duplicates:
        logger.info("meta_webhook_instagram_replay_duplicate count=%s", len(duplicates))
    if not claimed:
        return {"ok": True, "duplicate": True, "ingested": 0}
    ingested = _ingest_instagram_messages(db, messages, set(claimed))
    return {"ok": True, "duplicate": False, "ingested": ingested}


def _claim_keys(keys: list[str]) -> tuple[list[str], list[str]]:
    store = get_meta_idempotency_store()
    claimed: list[str] = []
    duplicates: list[str] = []

    def _run(active: MetaIdempotencyStore) -> None:
        claimed.clear()
        duplicates.clear()
        for key in keys:
            redis_key = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(key.encode('utf-8')).hexdigest()}"
            if active.claim(redis_key, IDEMPOTENCY_TTL_SECONDS):
                claimed.append(key)
            else:
                duplicates.append(key)

    try:
        _run(store)
    except MetaIdempotencyStoreError:
        logger.exception("meta_webhook_idempotency_backend_failure")
        if _is_production():
            raise MetaWebhookRejected(503, GENERIC_UNAVAILABLE) from None
        logger.error("meta_webhook_idempotency_memory_fallback")
        _run(_memory_fallback)
    return claimed, duplicates


def _ingest_messages(db: Session, messages: list[MessengerInbound], claimed: set[str]) -> int:
    created = 0
    for item in messages:
        if f"msg:{item.mid}" not in claimed:
            continue
        contact = resolve_facebook_sender(db, psid=item.psid)
        lead = _active_facebook_lead_for_contact(db, contact=contact, psid=item.psid)
        comm, was_created = ingest_live_message(
            db,
            {
                "channel": "facebook",
                "direction": "incoming",
                "source": "live_facebook",
                "sender": item.psid,
                "body_text": item.text,
                "external_provider_id": item.mid,
                "conversation_key": item.psid,
                "occurred_at": item.occurred_at,
                "contact_id": str(contact.id),
                "metadata_json": {
                    "kind": "dm",
                    FACEBOOK_PSID_KEY: item.psid,
                    "page_id": item.page_id,
                    **({"lead_id": str(lead.id)} if lead is not None else {}),
                },
            },
            actor=None,
        )
        if was_created:
            created += 1
            if lead is not None:
                _record_facebook_message_on_lead(
                    db,
                    lead=lead,
                    contact=contact,
                    message=item,
                    communication_id=comm.id,
                )
    return created


def process_meta_webhook(
    db: Session,
    *,
    raw_body: bytes,
    signature_header: str | None,
) -> dict[str, Any]:
    if len(raw_body) > MAX_WEBHOOK_BYTES:
        logger.warning("meta_webhook_malformed reason=too_large")
        raise MetaWebhookRejected(400, "invalid_request")

    app_secret = require_meta_app_secret()
    if not signature_header:
        logger.warning("meta_webhook_signature_failure reason=missing")
        raise MetaWebhookRejected(403, GENERIC_FORBIDDEN)
    if not verify_meta_signature(
        app_secret=app_secret,
        raw_body=raw_body,
        signature_header=signature_header,
    ):
        logger.warning("meta_webhook_signature_failure reason=invalid")
        raise MetaWebhookRejected(403, GENERIC_FORBIDDEN)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("meta_webhook_malformed reason=invalid_json")
        raise MetaWebhookRejected(400, "invalid_request") from None
    if not isinstance(payload, dict):
        logger.warning("meta_webhook_malformed reason=unexpected_object")
        raise MetaWebhookRejected(400, "invalid_request")

    object_name = str(payload.get("object") or "").strip()
    if object_name == "instagram":
        return _process_instagram(db, payload)
    if object_name != "page":
        logger.info("meta_webhook_ignored_object")
        return {"ok": True, "duplicate": False, "ingested": 0, "ignored": True}

    page_id = require_meta_page_id()
    messages, _unknown_pages = extract_messenger_messages(payload, page_id=page_id)
    if not messages:
        return {"ok": True, "duplicate": False, "ingested": 0}

    keys = [f"msg:{item.mid}" for item in messages]
    claimed, duplicates = _claim_keys(keys)
    if duplicates:
        logger.info("meta_webhook_replay_duplicate count=%s", len(duplicates))
    if not claimed:
        return {"ok": True, "duplicate": True, "ingested": 0}

    ingested = _ingest_messages(db, messages, set(claimed))
    return {"ok": True, "duplicate": False, "ingested": ingested}
