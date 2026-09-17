"""Idempotent Bitrix archive → crm_activities import. Does not create contacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
    CrmTaskStatus,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User

ARCHIVE_DEFAULT = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
HISTORY_KEY = "bitrix_history"
COMMENT_KEY = "bitrix_historical_comment"
BB_RE = re.compile(r"\[/?[^\]]+\]")


@dataclass
class PlannedActivity:
    import_key: str
    contact_id: UUID
    activity_type: CrmActivityType
    activity_category: CrmActivityCategory
    title: str
    description: str | None
    occurred_at: datetime | None
    status: CrmActivityStatus
    task_status: CrmTaskStatus | None
    metadata: dict[str, Any]
    skip_reason: str | None = None


@dataclass
class ImportReport:
    archive_rows: int = 0
    matched_contacts: int = 0
    unmatched_contacts: int = 0
    unmatched_names: list[str] = field(default_factory=list)
    existing_activities: int = 0
    existing_bitrix_comments: int = 0
    new_activities: int = 0
    whatsapp_messages: int = 0
    duplicates_skipped: int = 0
    conflicts: list[str] = field(default_factory=list)
    by_type: dict[str, int] = field(default_factory=dict)
    created_by_type: dict[str, int] = field(default_factory=dict)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _sha(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _plain(text: str | None, limit: int = 80) -> str:
    cleaned = BB_RE.sub("", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit] if cleaned else ""


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or item.get("DESCRIPTION") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or "").upper()
    provider_type = str(item.get("PROVIDER_TYPE_ID") or "").upper()
    if (
        "whatsapp" in low
        or "open channel" in low
        or "whatcrm" in low
        or "IMOPENLINES" in provider
        or "IMOL" in provider
    ):
        return "whatsapp_session"
    if "SMS" in provider or provider_type == "SMS" or "sms" in low:
        return "sms"
    if "EMAIL" in provider or "MAIL" in provider or "EMAIL" in provider_type:
        return "email"
    if "VOX" in provider or "CALL" in provider or provider_type == "CALL":
        return "call"
    if "MEETING" in provider or "VISIT" in provider or provider_type == "MEETING":
        return "meeting"
    if provider == "CRM_TODO" or provider_type == "TODO":
        return "meeting"
    if "TASK" in provider or "TASK" in provider_type:
        return "task"
    if "WEBFORM" in provider:
        return "other"
    type_id = str(item.get("TYPE_ID") or "")
    mapping = {"1": "meeting", "2": "call", "4": "email"}
    return mapping.get(type_id, "other")


TYPE_MAP = {
    "comment": (CrmActivityType.COMMENT, CrmActivityCategory.NOTE),
    "whatsapp_message": (CrmActivityType.WHATSAPP, CrmActivityCategory.COMMUNICATION),
    "whatsapp_session": (CrmActivityType.WHATSAPP, CrmActivityCategory.COMMUNICATION),
    "sms": (CrmActivityType.SMS, CrmActivityCategory.COMMUNICATION),
    "call": (CrmActivityType.PHONE_CALL, CrmActivityCategory.COMMUNICATION),
    "email": (CrmActivityType.EMAIL, CrmActivityCategory.COMMUNICATION),
    "meeting": (CrmActivityType.MEETING, CrmActivityCategory.MEETING),
    "task": (CrmActivityType.TASK, CrmActivityCategory.TASK),
    "other": (CrmActivityType.OTHER, CrmActivityCategory.OTHER),
}


def _title_for(kind: str, text: str | None, fallback: str) -> str:
    labels = {
        "comment": "Yorum",
        "whatsapp_message": "WhatsApp",
        "whatsapp_session": "WhatsApp / Open Channel",
        "sms": "SMS",
        "call": "Arama",
        "email": "E-posta",
        "meeting": "Toplantı",
        "task": "Görev",
        "other": "CRM aktivitesi",
    }
    snippet = _plain(text, 72)
    base = labels.get(kind, fallback)
    return f"{base}: {snippet}" if snippet and kind in {"whatsapp_message", "comment", "sms", "email"} else (snippet or base)


def load_author_names(archive: Path) -> dict[str, str]:
    path = archive / "raw" / "users" / "users.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    names = data.get("author_names") or {}
    if isinstance(data.get("users"), dict):
        for uid, rec in data["users"].items():
            if isinstance(rec, dict) and rec.get("name"):
                names[str(uid)] = rec["name"]
    return {str(k): str(v) for k, v in names.items() if v}


def load_contacts(db: Session) -> tuple[dict[UUID, CrmContact], dict[tuple[str, str], UUID]]:
    by_id: dict[UUID, CrmContact] = {}
    by_entity: dict[tuple[str, str], UUID] = {}
    for contact in db.scalars(select(CrmContact)).all():
        by_id[contact.id] = contact
        meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
        bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
        for ext in bitrix.get("external_ids") or []:
            text = str(ext)
            if ":" not in text:
                continue
            file_name, source_id = text.rsplit(":", 1)
            source_id = source_id.strip()
            if not source_id.isdigit():
                continue
            low = file_name.casefold()
            guessed = "contact" if any(token in low for token in ("contact", "kisi", "kişi")) else "lead"
            by_entity.setdefault((guessed, source_id), contact.id)
    return by_id, by_entity


def resolve_contact(
    canonical: str | None,
    entity_type: str,
    entity_id: str,
    by_id: dict[UUID, CrmContact],
    by_entity: dict[tuple[str, str], UUID],
) -> UUID | None:
    if canonical:
        try:
            uid = UUID(str(canonical))
        except ValueError:
            uid = None
        if uid and uid in by_id:
            return uid
    if (entity_type, entity_id) in by_entity:
        return by_entity[(entity_type, entity_id)]
    return None


def existing_index(db: Session) -> tuple[set[str], dict[UUID, set[str]]]:
    keys: set[str] = set()
    hashes: dict[UUID, set[str]] = {}
    for activity in db.scalars(select(CrmActivity)).all():
        metadata = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
        history = metadata.get(HISTORY_KEY)
        if isinstance(history, dict) and history.get("import_key"):
            keys.add(str(history["import_key"]))
        comment = metadata.get(COMMENT_KEY)
        if isinstance(comment, dict):
            if comment.get("import_key"):
                keys.add(str(comment["import_key"]))
            if comment.get("content_sha256"):
                hashes.setdefault(activity.entity_id, set()).add(str(comment["content_sha256"]))
        if activity.description:
            hashes.setdefault(activity.entity_id, set()).add(_sha(activity.description))
    return keys, hashes


def iter_entity_files(archive: Path) -> list[Path]:
    files: list[Path] = []
    for folder in (archive / "raw" / "leads", archive / "raw" / "contacts"):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            files.append(path)
    return files


def plan_import(db: Session, archive: Path) -> tuple[list[PlannedActivity], ImportReport]:
    report = ImportReport(existing_activities=db.query(CrmActivity).count(), dry_run=True)
    by_id, by_entity = load_contacts(db)
    existing_keys, existing_hashes = existing_index(db)
    report.existing_bitrix_comments = sum(
        1
        for activity in db.scalars(select(CrmActivity)).all()
        if isinstance((activity.metadata_json or {}).get(COMMENT_KEY), dict)
    )
    authors = load_author_names(archive)
    plans: list[PlannedActivity] = []
    seen_new: set[str] = set()
    matched: set[UUID] = set()
    unmatched: set[str] = set()
    live_messages_by_entity: dict[tuple[str, str], int] = {}

    live_dir = archive / "raw" / "chats" / "live"
    live_files = list(live_dir.glob("*.json")) if live_dir.exists() else []

    def add_plan(plan: PlannedActivity) -> None:
        report.archive_rows += 1
        if plan.import_key in existing_keys or plan.import_key in seen_new:
            report.duplicates_skipped += 1
            return
        body = plan.description or ""
        if plan.activity_type == CrmActivityType.COMMENT and body:
            digest = _sha(body)
            if digest in existing_hashes.get(plan.contact_id, set()):
                report.duplicates_skipped += 1
                return
        seen_new.add(plan.import_key)
        plans.append(plan)
        report.new_activities += 1
        report.by_type[plan.activity_type.value] = report.by_type.get(plan.activity_type.value, 0) + 1
        if plan.activity_type == CrmActivityType.WHATSAPP and plan.metadata.get(HISTORY_KEY, {}).get("kind") == "whatsapp_message":
            report.whatsapp_messages += 1

    for path in live_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        entity_type = str(data.get("bitrix_entity_type") or "")
        entity_id = str(data.get("bitrix_entity_id") or "")
        count = 0
        for chat in data.get("chats") or []:
            count += len(chat.get("messages") or [])
        live_messages_by_entity[(entity_type, entity_id)] = count

    for path in iter_entity_files(archive):
        data = json.loads(path.read_text(encoding="utf-8"))
        entity_type = str(data.get("bitrix_entity_type") or path.parent.name.rstrip("s"))
        entity_id = str(data.get("bitrix_entity_id") or path.stem)
        contact_id = resolve_contact(
            data.get("canonical_crm_contact_id"),
            entity_type,
            entity_id,
            by_id,
            by_entity,
        )
        comments = data.get("timeline_comments") or []
        activities = data.get("crm_activities") or []
        if contact_id is None:
            unmatched.add(str(data.get("person_name") or f"{entity_type}:{entity_id}"))
            report.archive_rows += len(comments) + len(activities)
            report.conflicts.append(f"unmatched {entity_type}:{entity_id}")
            continue
        matched.add(contact_id)
        person_name = data.get("person_name")
        for comment in comments:
            cid = str(comment.get("ID") or "")
            text = str(comment.get("COMMENT") or comment.get("TEXT") or "")
            if not cid:
                report.archive_rows += 1
                report.duplicates_skipped += 1
                continue
            author_id = str(comment.get("AUTHOR_ID") or "")
            kind = "comment"
            activity_type, category = TYPE_MAP[kind]
            add_plan(
                PlannedActivity(
                    import_key=f"bitrix:comment:{entity_type}:{entity_id}:{cid}",
                    contact_id=contact_id,
                    activity_type=activity_type,
                    activity_category=category,
                    title=_title_for(kind, text, "Yorum"),
                    description=text,
                    occurred_at=_parse_dt(comment.get("CREATED") or comment.get("DATE_CREATE")),
                    status=CrmActivityStatus.COMPLETED,
                    task_status=None,
                    metadata={
                        HISTORY_KEY: {
                            "import_key": f"bitrix:comment:{entity_type}:{entity_id}:{cid}",
                            "source": "bitrix",
                            "kind": "comment",
                            "bitrix_entity_type": entity_type,
                            "bitrix_entity_id": entity_id,
                            "bitrix_record_id": cid,
                            "author_id": author_id,
                            "author_name": authors.get(author_id),
                            "person_name": person_name,
                            "attachment_count": len(comment.get("FILES") or []) if isinstance(comment.get("FILES"), list) else 0,
                        }
                    },
                )
            )
        has_live_messages = live_messages_by_entity.get((entity_type, entity_id), 0) > 0
        for activity in activities:
            kind = classify_activity(activity)
            aid = str(activity.get("ID") or "")
            subject = str(activity.get("SUBJECT") or "")
            description = str(activity.get("DESCRIPTION") or subject)
            if kind == "whatsapp_session" and has_live_messages:
                description = subject  # summary-only; messages stored separately
            activity_type, category = TYPE_MAP[kind]
            author_id = str(activity.get("AUTHOR_ID") or activity.get("RESPONSIBLE_ID") or "")
            completed = str(activity.get("COMPLETED") or "").upper() == "Y"
            status = CrmActivityStatus.COMPLETED if completed or kind != "task" else CrmActivityStatus.IN_PROGRESS
            task_status = None
            if kind == "task":
                task_status = CrmTaskStatus.COMPLETED if completed else CrmTaskStatus.IN_PROGRESS
            add_plan(
                PlannedActivity(
                    import_key=f"bitrix:activity:{entity_type}:{entity_id}:{aid}",
                    contact_id=contact_id,
                    activity_type=activity_type,
                    activity_category=category,
                    title=_title_for(kind, subject, subject or "Aktivite"),
                    description=description if kind != "whatsapp_session" or not has_live_messages else subject,
                    occurred_at=_parse_dt(activity.get("CREATED") or activity.get("START_TIME")),
                    status=status,
                    task_status=task_status,
                    metadata={
                        HISTORY_KEY: {
                            "import_key": f"bitrix:activity:{entity_type}:{entity_id}:{aid}",
                            "source": "bitrix",
                            "kind": kind,
                            "bitrix_entity_type": entity_type,
                            "bitrix_entity_id": entity_id,
                            "bitrix_record_id": aid,
                            "author_id": author_id,
                            "author_name": authors.get(author_id),
                            "person_name": person_name,
                            "provider_id": activity.get("PROVIDER_ID"),
                            "provider_type_id": activity.get("PROVIDER_TYPE_ID"),
                            "attachment_count": len(activity.get("FILES") or []) if isinstance(activity.get("FILES"), list) else 0,
                            "open_channel_summary": kind == "whatsapp_session",
                            "full_messages_recovered": has_live_messages if kind == "whatsapp_session" else None,
                        }
                    },
                )
            )

    for path in live_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        entity_type = str(data.get("bitrix_entity_type") or "")
        entity_id = str(data.get("bitrix_entity_id") or "")
        contact_id = resolve_contact(
            data.get("canonical_crm_contact_id"),
            entity_type,
            entity_id,
            by_id,
            by_entity,
        )
        if contact_id is None:
            unmatched.add(str(data.get("person_name") or f"{entity_type}:{entity_id}"))
            report.archive_rows += sum(len(chat.get("messages") or []) for chat in data.get("chats") or [])
            continue
        matched.add(contact_id)
        person_name = data.get("person_name")
        for chat in data.get("chats") or []:
            chat_id = str(chat.get("chat_id") or "")
            for message in chat.get("messages") or []:
                mid = str(message.get("message_id") or "")
                if not mid:
                    continue
                text = str(message.get("message_text") or "")
                sender_id = str(message.get("sender_id") or "")
                sender_name = message.get("sender_name") or authors.get(sender_id)
                direction = message.get("direction") or ""
                activity_type, category = TYPE_MAP["whatsapp_message"]
                add_plan(
                    PlannedActivity(
                        import_key=f"bitrix:wa:{chat_id}:{mid}",
                        contact_id=contact_id,
                        activity_type=activity_type,
                        activity_category=category,
                        title=_title_for("whatsapp_message", text, "WhatsApp"),
                        description=text,
                        occurred_at=_parse_dt(message.get("date_time")),
                        status=CrmActivityStatus.COMPLETED,
                        task_status=None,
                        metadata={
                            HISTORY_KEY: {
                                "import_key": f"bitrix:wa:{chat_id}:{mid}",
                                "source": "bitrix",
                                "kind": "whatsapp_message",
                                "bitrix_entity_type": entity_type,
                                "bitrix_entity_id": entity_id,
                                "bitrix_record_id": mid,
                                "chat_id": chat_id,
                                "dialog_id": chat.get("dialog_id"),
                                "message_id": mid,
                                "author_id": sender_id,
                                "author_name": sender_name,
                                "direction": direction,
                                "person_name": person_name,
                                "attachment_count": message.get("attachment_count") or 0,
                                "provider": message.get("provider"),
                            }
                        },
                    )
                )

    report.matched_contacts = len(matched)
    report.unmatched_contacts = len(unmatched)
    report.unmatched_names = sorted(unmatched)[:50]
    return plans, report


def apply_import(db: Session, plans: list[PlannedActivity], actor: User | None) -> Counter:
    created: Counter[str] = Counter()
    actor_id = actor.id if actor else None
    for index, plan in enumerate(plans, start=1):
        occurred = plan.occurred_at
        db.add(
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=plan.contact_id,
                activity_type=plan.activity_type,
                activity_category=plan.activity_category,
                title=plan.title[:500],
                summary=(plan.description or "")[:1000] if plan.description else None,
                description=plan.description,
                status=plan.status,
                task_status=plan.task_status,
                priority=CrmActivityPriority.MEDIUM,
                visibility=CrmActivityVisibility.ORGANIZATION,
                start_date=occurred,
                completed_at=occurred if plan.status == CrmActivityStatus.COMPLETED else None,
                created_at=occurred or datetime.now(timezone.utc),
                updated_at=occurred or datetime.now(timezone.utc),
                created_by=actor_id,
                updated_by=actor_id,
                metadata_json=plan.metadata,
            )
        )
        created[plan.activity_type.value] += 1
        if index % 500 == 0:
            db.flush()
    return created


def pick_actor(db: Session) -> User | None:
    return db.scalars(select(User).limit(1)).first()
