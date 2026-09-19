"""Read-only Bitrix owner/access audit for the remaining 42 inaccessible files.

Does not download binaries. Does not modify Bitrix or CRM.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from link_agreement_documents import (  # type: ignore
    BitrixClient,
    ENV_PATH,
    load_env,
    utc_now,
    webhook_base,
)

PACKAGE_CSV = Path("/export/2026-09-final/BITRIX_MANUAL_RECOVERY/reports/BITRIX_MANUAL_RECOVERY_42.csv")
ARCHIVE_CHATS = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE/raw/chats/live")
OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports")


def user_name(rec: dict | None) -> str:
    if not isinstance(rec, dict):
        return ""
    parts = [str(rec.get("NAME") or "").strip(), str(rec.get("LAST_NAME") or "").strip()]
    name = " ".join(p for p in parts if p)
    return name or str(rec.get("EMAIL") or rec.get("LOGIN") or "")


def pick_id(*values: Any) -> str:
    for value in values:
        if value in (None, "", [], {}, 0, "0"):
            continue
        return str(value)
    return ""


class Auditor:
    def __init__(self, client: BitrixClient) -> None:
        self.client = client
        self.users: dict[str, dict] = {}
        self.activities: dict[str, dict] = {}
        self.entities: dict[tuple[str, str], dict] = {}
        self.chats: dict[str, dict] = {}
        self.messages: dict[tuple[str, str], dict] = {}
        self.open_chats: dict[tuple[str, str], Any] = {}
        self.dialogs: dict[str, dict] = {}
        self.lines: dict[str, dict] = {}

    def user(self, user_id: str) -> dict:
        if not user_id:
            return {}
        if user_id not in self.users:
            body = self.client.call("user.get", {"ID": user_id})
            rows = body.get("result") if not body.get("error") else None
            rec = rows[0] if isinstance(rows, list) and rows else {}
            self.users[user_id] = rec if isinstance(rec, dict) else {}
        return self.users[user_id]

    def activity(self, activity_id: str) -> dict:
        if activity_id not in self.activities:
            body = self.client.call("crm.activity.get", {"id": activity_id})
            rec = body.get("result") if not body.get("error") else None
            self.activities[activity_id] = rec if isinstance(rec, dict) else {"error": body.get("error")}
        return self.activities[activity_id]

    def entity(self, entity_type: str, entity_id: str) -> dict:
        key = (entity_type, entity_id)
        if key not in self.entities:
            method = "crm.lead.get" if entity_type == "lead" else "crm.contact.get"
            body = self.client.call(method, {"id": entity_id})
            rec = body.get("result") if not body.get("error") else None
            self.entities[key] = rec if isinstance(rec, dict) else {}
        return self.entities[key]

    def chat(self, chat_id: str) -> dict:
        if chat_id not in self.chats:
            body = self.client.call("im.chat.get", {"ID": chat_id})
            rec = body.get("result") if not body.get("error") else None
            if not isinstance(rec, dict):
                body = self.client.call("im.chat.get", {"CHAT_ID": chat_id})
                rec = body.get("result") if not body.get("error") else None
            self.chats[chat_id] = rec if isinstance(rec, dict) else {"error": body.get("error")}
        return self.chats[chat_id]

    def message(self, dialog_id: str, message_id: str) -> dict:
        key = (dialog_id, message_id)
        if key not in self.messages:
            params: dict[str, Any] = {"DIALOG_ID": dialog_id, "LIMIT": 5}
            if message_id.isdigit():
                params["LAST_ID"] = int(message_id) + 1
            body = self.client.call("im.dialog.messages.get", params)
            result = body.get("result") if not body.get("error") else None
            hit: dict = {}
            if isinstance(result, dict):
                for msg in result.get("messages") or []:
                    if str(msg.get("id") or msg.get("ID") or "") == message_id:
                        hit = msg
                        break
            self.messages[key] = hit
        return self.messages[key]

    def dialog(self, dialog_id: str) -> dict:
        if dialog_id not in self.dialogs:
            body = self.client.call("im.dialog.get", {"DIALOG_ID": dialog_id})
            rec = body.get("result") if not body.get("error") else None
            self.dialogs[dialog_id] = rec if isinstance(rec, dict) else {}
        return self.dialogs[dialog_id]

    def line(self, line_id: str) -> dict:
        if not line_id:
            return {}
        if line_id not in self.lines:
            body = self.client.call("imopenlines.config.get", {"CONFIG_ID": line_id})
            rec = body.get("result") if not body.get("error") else None
            self.lines[line_id] = rec if isinstance(rec, dict) else {}
        return self.lines[line_id]


def chat_id_from_url(url: str) -> str:
    marker = "IM_HISTORY=chat"
    if marker in url:
        tail = url.split(marker, 1)[1]
        digits = ""
        for ch in tail:
            if ch.isdigit():
                digits += ch
            else:
                break
        return digits
    return ""


def archive_wa_meta(entity_type: str, entity_id: str, message_id: str) -> dict:
    path = ARCHIVE_CHATS / f"{entity_type}_{entity_id}.json"
    out = {"dialog_id": "", "chat_id": "", "author_id": "", "text": ""}
    if not path.exists():
        return out
    data = json.loads(path.read_text(encoding="utf-8"))
    for chat in data.get("chats") or []:
        chat_id = str(chat.get("chat_id") or "")
        dialog_id = str(chat.get("dialog_id") or (f"chat{chat_id}" if chat_id else ""))
        for message in chat.get("messages") or []:
            raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
            mid = str(message.get("message_id") or raw.get("id") or "")
            if mid != message_id:
                continue
            out.update(
                {
                    "dialog_id": dialog_id,
                    "chat_id": chat_id,
                    "author_id": str(message.get("author_id") or raw.get("author_id") or raw.get("senderId") or ""),
                    "text": str(message.get("message_text") or raw.get("text") or "")[:160],
                }
            )
            return out
    return out


def email_sender(activity: dict) -> str:
    settings = activity.get("SETTINGS") if isinstance(activity.get("SETTINGS"), dict) else {}
    email_meta = settings.get("EMAIL_META") if isinstance(settings.get("EMAIL_META"), dict) else {}
    from_field = email_meta.get("from") or activity.get("LOCATION") or ""
    if isinstance(from_field, list):
        from_field = ", ".join(str(x) for x in from_field[:3])
    return str(from_field)[:200]


def main() -> None:
    env = load_env(ENV_PATH)
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    client = BitrixClient(webhook_base(raw))
    current = client.call("user.current", {})
    admin = current.get("result") if isinstance(current.get("result"), dict) else {}
    admin_id = str(admin.get("ID") or "")
    admin_name = user_name(admin)
    auditor = Auditor(client)

    with PACKAGE_CSV.open(encoding="utf-8", newline="") as handle:
        files = list(csv.DictReader(handle))

    rows = []
    for src in files:
        person = src.get("person_name") or ""
        source_type = src.get("source_type") or ""
        source_id = str(src.get("source_record_id") or "")
        file_id = str(src.get("bitrix_file_id") or "")
        entity_type = src.get("bitrix_entity_type") or ""
        entity_id = str(src.get("bitrix_entity_id") or "")
        responsible_id = ""
        author_id = ""
        operator_id = ""
        email_from = ""
        likely_id = ""
        notes = []
        if source_type.lower() == "email":
            act = auditor.activity(source_id)
            entity = auditor.entity(entity_type, entity_id)
            responsible_id = pick_id(act.get("RESPONSIBLE_ID"), entity.get("ASSIGNED_BY_ID"))
            author_id = pick_id(act.get("AUTHOR_ID"), act.get("EDITOR_ID"), act.get("CREATED_BY"))
            email_from = email_sender(act)
            likely_id = responsible_id or author_id
            notes.append("email_binary_blocked_for_admin_webhook_html_login")
        else:
            wa = archive_wa_meta(entity_type, entity_id, source_id)
            chat_id = pick_id(
                chat_id_from_url(str(src.get("source_record_url") or "")),
                wa.get("chat_id"),
                "13496",
            )
            dialog_id = wa["dialog_id"] or f"chat{chat_id}"
            live_msg = auditor.message(dialog_id, source_id)
            dialog = auditor.dialog(dialog_id)
            author_id = pick_id(live_msg.get("author_id"), live_msg.get("senderId"), wa.get("author_id"))
            entity_code = str(dialog.get("entity_id") or "")
            line_id = ""
            parts = [p for p in entity_code.split("|") if p]
            if len(parts) >= 2 and parts[1].isdigit():
                line_id = parts[1]
            line = auditor.line(line_id)
            queue = [str(x) for x in (line.get("QUEUE") or []) if str(x) not in {"", "0"}]
            line_name = str(line.get("LINE_NAME") or "")
            operator_id = pick_id(*(queue[::-1] if queue else []), dialog.get("owner"))
            if "92" in queue:
                operator_id = "92"
            entity = auditor.entity(entity_type, entity_id)
            responsible_id = pick_id(entity.get("ASSIGNED_BY_ID"))
            likely_id = operator_id or responsible_id
            if author_id and author_id not in {*queue, operator_id, responsible_id, admin_id}:
                notes.append("message_author_is_whatcrm_connector_guest")
            if line_name:
                notes.append(f"open_channel_line={line_id}:{line_name}")
            if queue:
                notes.append("queue_user_ids=" + ",".join(queue))
            notes.append(f"chat_id={chat_id}")
            notes.append("whatsapp_binary_denied_for_admin_disk_api")

        for uid in (responsible_id, author_id, operator_id, likely_id):
            auditor.user(uid)
        author_name = user_name(auditor.user(author_id))
        if source_type.lower() != "email" and author_id == "10784" and not author_name:
            author_name = "Berk Çimen (WhatCRM connector guest)"
        row = {
            "person_name": person,
            "source_type": source_type,
            "source_record_id": source_id,
            "bitrix_file_id": file_id,
            "bitrix_entity_type": entity_type,
            "bitrix_entity_id": entity_id,
            "responsible_user_id": responsible_id,
            "responsible_user_name": user_name(auditor.user(responsible_id)),
            "activity_author_id": author_id,
            "activity_author_name": author_name,
            "chat_operator_id": operator_id,
            "chat_operator_name": user_name(auditor.user(operator_id)),
            "email_owner_or_sender": email_from,
            "admin_user_id": admin_id,
            "admin_user_name": admin_name,
            "admin_can_access_binary": "no",
            "likely_download_user_id": likely_id,
            "likely_download_user_name": user_name(auditor.user(likely_id)),
            "notes": "; ".join(notes),
        }
        rows.append(row)

    by_user: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = row["likely_download_user_id"] or "UNKNOWN"
        by_user[key].append(row)
    users_involved = []
    for uid, items in sorted(by_user.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        users_involved.append(
            {
                "user_id": uid,
                "user_name": items[0]["likely_download_user_name"] or uid,
                "file_count": len(items),
                "source_types": dict(Counter(i["source_type"] for i in items)),
                "customers": sorted({i["person_name"] for i in items}),
            }
        )
    berk = [r for r in rows if r["person_name"] == "Berk Çimen" and r["source_type"].lower() == "whatsapp"]
    berk_owner = {
        "file_count": len(berk),
        "likely_user_id": berk[0]["likely_download_user_id"] if berk else "",
        "likely_user_name": berk[0]["likely_download_user_name"] if berk else "",
        "responsible_user_id": berk[0]["responsible_user_id"] if berk else "",
        "responsible_user_name": berk[0]["responsible_user_name"] if berk else "",
        "chat_operator_id": berk[0]["chat_operator_id"] if berk else "",
        "chat_operator_name": berk[0]["chat_operator_name"] if berk else "",
        "authors": sorted({(r["activity_author_id"], r["activity_author_name"] or "WhatCRM connector guest") for r in berk}),
        "file_ids": [r["bitrix_file_id"] for r in berk],
        "notes": sorted({r.get("notes", "") for r in berk}),
        "why": (
            "CRM assignee is admin user 8, who already cannot download these binaries. "
            "Both chats are WhatCRM Open Channels named for Beyza; line 24 queue is only 92; "
            "line 18 queue is 1148+92; inbound WhatsApp number 905396792039 is Beyza's work phone."
        ),
    }
    webhook_set = [
        {
            "user_id": u["user_id"],
            "user_name": u["user_name"],
            "files": u["file_count"],
            "reason": "incoming-webhook as this Bitrix user; needed to open mailbox/IM disk files the admin REST user cannot download",
        }
        for u in users_involved
        if u["user_id"] not in {"", "UNKNOWN", admin_id}
    ]
    if "1148" not in {u["user_id"] for u in webhook_set}:
        webhook_set.append(
            {
                "user_id": "1148",
                "user_name": user_name(auditor.user("1148")) or "Musa Çobaner",
                "files": 0,
                "reason": "optional fallback only if Beyza webhook cannot open chat13496 (line 18 queue also includes user 1148)",
            }
        )
    summary = {
        "generated_at": utc_now(),
        "unresolved_files": len(rows),
        "admin_user": {"id": admin_id, "name": admin_name, "can_access_binaries": False},
        "users_involved": users_involved,
        "file_count_per_user": {u["user_name"] or u["user_id"]: u["file_count"] for u in users_involved},
        "berk_whatsapp_owner": berk_owner,
        "recommended_user_webhooks": webhook_set,
        "rows": rows,
        "bitrix_calls": client.call_count,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "BITRIX_FILE_ACCESS_OWNER_AUDIT.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    csv_fields = [
        "person_name",
        "source_type",
        "source_record_id",
        "bitrix_file_id",
        "responsible_user_id",
        "responsible_user_name",
        "activity_author_id",
        "activity_author_name",
        "chat_operator_id",
        "chat_operator_name",
        "email_owner_or_sender",
        "admin_can_access_binary",
        "likely_download_user_id",
        "likely_download_user_name",
        "notes",
    ]
    with (OUT / "BITRIX_FILE_ACCESS_OWNER_AUDIT.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "unresolved_files": summary["unresolved_files"],
                "users_involved": summary["users_involved"],
                "file_count_per_user": summary["file_count_per_user"],
                "berk_whatsapp_owner": berk_owner,
                "recommended_user_webhooks": webhook_set,
                "bitrix_calls": client.call_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
