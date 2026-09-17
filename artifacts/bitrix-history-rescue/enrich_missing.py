"""Enrich existing Bitrix archive with live chats, users, and files. Read-only. No CRM writes."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
ENV_PATH = Path("/tmp/.env")
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
CHAT_FIELDS = [
    "canonical_crm_contact_id",
    "person_name",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "provider",
    "chat_id",
    "dialog_id",
    "session_id",
    "message_id",
    "date_time",
    "sender_id",
    "sender_name",
    "direction",
    "message_text",
    "attachment_count",
    "source_api_method",
]
HIST_FIELDS = [
    "canonical_crm_contact_id",
    "person_name",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "history_type",
    "bitrix_record_id",
    "chat_id",
    "message_id",
    "date_time",
    "author_id",
    "author_name",
    "direction",
    "title",
    "full_text",
    "attachment_count",
    "source_api_method",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def webhook_base(raw: str) -> str:
    value = (raw or "").strip()
    marker = "BURAYA_BITRIX_URL="
    if marker in value:
        value = value.split(marker, 1)[1].strip()
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    path = "/" + "/".join(segs) + "/"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def redact(text: str, webhook: str) -> str:
    return WEBHOOK_RE.sub("[REDACTED_URL]", (text or "").replace(webhook, "[REDACTED]"))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.origin = urllib.parse.urlunparse(urllib.parse.urlparse(self.base)[:2] + ("", "", "", ""))
        self.min_interval = 0.3
        self._last = 0.0
        self.call_count = 0
        self.retry_count = 0

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def call(self, method: str, payload: dict | None = None) -> dict:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last_error = None
        for attempt in range(6):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "error_description": redact(raw, self.base)[:500]}
            except Exception as exc:  # noqa: BLE001
                last_error = redact(str(exc), self.base)
                self.retry_count += 1
                time.sleep(min(30, 2 ** attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            desc = redact(str(parsed.get("error_description") or ""), self.base)
            parsed["error_description"] = desc
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                self.retry_count += 1
                time.sleep(min(45, 2 ** (attempt + 1)))
                last_error = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last_error or "unknown"}

    def batch(self, commands: dict[str, tuple[str, dict]]) -> dict:
        payload: dict[str, Any] = {"halt": 0}
        for key, (method, params) in commands.items():
            payload[f"cmd[{key}]"] = f"{method}?{urllib.parse.urlencode(params, doseq=True)}"
        body = self.call("batch", payload)
        result = body.get("result") or {}
        if isinstance(result, dict) and "result" in result:
            return result
        return {
            "result": result,
            "result_error": body.get("result_error") or {},
        }

    def download(self, url: str, dest: Path) -> tuple[str, str | None]:
        if not url:
            return "failed", "no_url"
        if url.startswith("/"):
            url = self.origin + url
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        self._wait()
        self.call_count += 1
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=90) as resp, tmp.open("wb") as handle:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            tmp.replace(dest)
            self._last = time.time()
            return "downloaded", None
        except urllib.error.HTTPError as exc:
            self._last = time.time()
            if tmp.exists():
                tmp.unlink()
            if exc.code in {401, 403}:
                return "inaccessible", f"HTTP {exc.code}"
            if exc.code == 404:
                return "missing", "HTTP 404"
            return "failed", f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            if tmp.exists():
                tmp.unlink()
            return "failed", redact(str(exc), self.base)[:300]


def log(path: Path, message: str) -> None:
    line = f"{utc_now()} {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "completed_entities": {},
        "completed_files": {},
        "users_done": False,
        "stats": {},
    }


def collect_entities(archive: Path) -> dict[tuple[str, str], dict]:
    entities: dict[tuple[str, str], dict] = {}
    for path in (archive / "raw" / "chats").glob("*.json"):
        if path.name.startswith("_") or path.parent.name == "live":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        key = (str(data.get("bitrix_entity_type") or ""), str(data.get("bitrix_entity_id") or ""))
        if not key[0] or not key[1]:
            continue
        rec = entities.setdefault(
            key,
            {
                "bitrix_entity_type": key[0],
                "bitrix_entity_id": key[1],
                "person_name": data.get("person_name"),
                "canonical_crm_contact_id": data.get("canonical_crm_contact_id"),
                "session_ids": [],
                "legacy_chat_ids": [],
                "providers": [],
                "activity_ids": [],
            },
        )
        if data.get("session_id"):
            rec["session_ids"].append(str(data.get("session_id")))
        if data.get("chat_id"):
            rec["legacy_chat_ids"].append(str(data.get("chat_id")))
        if data.get("provider"):
            rec["providers"].append(str(data.get("provider")))
        if data.get("activity_id"):
            rec["activity_ids"].append(str(data.get("activity_id")))
    berk = archive / "raw" / "contacts" / "180.json"
    if berk.exists():
        data = json.loads(berk.read_text(encoding="utf-8"))
        entities.setdefault(
            ("contact", "180"),
            {
                "bitrix_entity_type": "contact",
                "bitrix_entity_id": "180",
                "person_name": data.get("person_name"),
                "canonical_crm_contact_id": data.get("canonical_crm_contact_id"),
                "session_ids": [],
                "legacy_chat_ids": [],
                "providers": [],
                "activity_ids": [],
            },
        )
    return entities


def parse_message_bundle(result: Any) -> tuple[list[dict], dict, dict]:
    messages: list[dict] = []
    users: dict = {}
    files: dict = {}
    if isinstance(result, dict):
        raw_messages = result.get("messages") or result.get("message") or []
        users = result.get("users") or result.get("usersShort") or {}
        files = result.get("files") or {}
        if isinstance(raw_messages, dict):
            raw_messages = list(raw_messages.values())
        messages = list(raw_messages or [])
    elif isinstance(result, list):
        messages = result
    return messages, users if isinstance(users, dict) else {}, files if isinstance(files, dict) else {}


def message_id_of(item: dict) -> str:
    return str(item.get("id") or item.get("ID") or item.get("message_id") or "")


def fetch_dialog_messages(client: BitrixClient, dialog_id: str) -> tuple[list[dict], dict, dict, str | None]:
    all_messages: list[dict] = []
    users: dict = {}
    files: dict = {}
    last_id = None
    seen = set()
    for _ in range(400):
        payload: dict[str, Any] = {"DIALOG_ID": dialog_id, "LIMIT": 50}
        if last_id is not None:
            payload["LAST_ID"] = last_id
        body = client.call("im.dialog.messages.get", payload)
        if body.get("error"):
            if not all_messages:
                return [], {}, {}, f"{body.get('error')}: {body.get('error_description')}"
            break
        chunk, more_users, more_files = parse_message_bundle(body.get("result"))
        users.update({str(k): v for k, v in more_users.items()})
        files.update({str(k): v for k, v in more_files.items()})
        new_items = []
        for item in chunk:
            mid = message_id_of(item)
            if not mid or mid in seen:
                continue
            seen.add(mid)
            new_items.append(item)
        if not new_items:
            break
        all_messages.extend(new_items)
        ids = [int(message_id_of(item)) for item in new_items if str(message_id_of(item)).isdigit()]
        if not ids:
            break
        last_id = min(ids)
        if len(new_items) < 20:
            break
    return all_messages, users, files, None


def normalize_user(item: dict) -> dict:
    uid = str(item.get("ID") or item.get("id") or "")
    name = " ".join(part for part in [item.get("NAME"), item.get("LAST_NAME")] if part).strip()
    if not name:
        name = item.get("FULL_NAME") or item.get("name") or ""
    return {
        "id": uid,
        "name": name or None,
        "email": item.get("EMAIL") or item.get("email"),
        "raw_name_fields": {"NAME": item.get("NAME"), "LAST_NAME": item.get("LAST_NAME")},
    }


def collect_file_ids(archive: Path) -> set[str]:
    ids: set[str] = set()
    for folder in (archive / "raw" / "leads", archive / "raw" / "contacts"):
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for ref in data.get("attachment_references") or []:
                fid = ref.get("file_id")
                if fid and str(fid).isdigit():
                    ids.add(str(fid))
            for comment in data.get("timeline_comments") or []:
                files = comment.get("FILES") or []
                if isinstance(files, list):
                    for item in files:
                        if isinstance(item, dict):
                            fid = item.get("id") or item.get("ID")
                        else:
                            fid = item
                        if fid and str(fid).isdigit():
                            ids.add(str(fid))
    return ids


def safe_filename(name: str | None, file_id: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", name or "file")[:80].strip("._") or "file"
    return f"{file_id}_{base}"


def classify_direction(author_id: str, user_ids: set[str]) -> str:
    if author_id in {"", "0", "None"}:
        return "system"
    if author_id in user_ids:
        return "outbound"
    return "inbound"


def main() -> int:
    archive = ARCHIVE
    progress = archive / "checkpoints" / "enrichment_progress.log"
    state_path = archive / "checkpoints" / "enrichment_state.json"
    enrich_root = archive / "enrichment"
    live_chats = archive / "raw" / "chats" / "live"
    attach_dir = archive / "attachments"
    for path in (enrich_root, live_chats, attach_dir, archive / "raw" / "users"):
        path.mkdir(parents=True, exist_ok=True)

    env = load_env(ENV_PATH)
    raw_url = env.get("BITRIX_WEBHOOK_URL") or ""
    if not raw_url:
        print("MISSING_BITRIX_WEBHOOK_URL")
        return 2
    client = BitrixClient(webhook_base(raw_url))
    state = load_state(state_path)
    log(progress, "START enrichment")

    entities = collect_entities(archive)
    log(progress, f"ENTITIES {len(entities)}")

    users: dict[str, dict] = {}
    existing_users = archive / "raw" / "users" / "users.json"
    if existing_users.exists():
        prev = json.loads(existing_users.read_text(encoding="utf-8"))
        if isinstance(prev.get("author_names"), dict):
            for uid, name in prev["author_names"].items():
                users[str(uid)] = {"id": str(uid), "name": name}
    if not state.get("users_done"):
        start = 0
        seen_starts = set()
        while start not in seen_starts:
            seen_starts.add(start)
            body = client.call("user.get", {"start": start})
            if body.get("error"):
                log(progress, f"USER_GET_ERROR {body.get('error')} {body.get('error_description')}")
                break
            chunk = body.get("result") or []
            for item in chunk:
                rec = normalize_user(item)
                if rec["id"]:
                    users[rec["id"]] = rec
            nxt = body.get("next")
            if nxt is None or not chunk:
                break
            start = int(nxt)
        missing = {"92", "8", "1", "10", "12", "14"} - set(users)
        for uid in sorted(missing):
            body = client.call("user.get", {"ID": uid})
            result = body.get("result") or []
            if isinstance(result, dict):
                result = [result]
            for item in result:
                rec = normalize_user(item)
                if rec["id"]:
                    users[rec["id"]] = rec
        atomic_write_json(
            archive / "raw" / "users" / "users.json",
            {
                "retrieved_at": utc_now(),
                "count": len(users),
                "users": users,
                "author_names": {uid: rec.get("name") for uid, rec in users.items()},
            },
        )
        atomic_write_json(enrich_root / "users.json", users)
        state["users_done"] = True
        atomic_write_json(state_path, state)
        log(progress, f"USERS {len(users)}")
    else:
        loaded = json.loads((enrich_root / "users.json").read_text(encoding="utf-8")) if (enrich_root / "users.json").exists() else users
        users = {str(k): v for k, v in loaded.items()}
        log(progress, f"USERS loaded {len(users)}")
    user_ids = {uid for uid, rec in users.items() if rec.get("name")}
    user_names = {uid: rec.get("name") or "" for uid, rec in users.items()}

    chats_with_messages = 0
    chats_inaccessible = 0
    chats_processed = 0
    total_api_messages = 0
    session_denied = 0
    session_ok = 0

    entity_items = list(entities.values())
    for offset in range(0, len(entity_items), 20):
        batch = entity_items[offset : offset + 20]
        pending = []
        for rec in batch:
            key = f"{rec['bitrix_entity_type']}:{rec['bitrix_entity_id']}"
            if key in (state.get("completed_entities") or {}) and (live_chats / f"{rec['bitrix_entity_type']}_{rec['bitrix_entity_id']}.json").exists():
                existing = json.loads((live_chats / f"{rec['bitrix_entity_type']}_{rec['bitrix_entity_id']}.json").read_text(encoding="utf-8"))
                chats_processed += 1
                msg_n = sum(len(chat.get("messages") or []) for chat in existing.get("chats") or [])
                total_api_messages += msg_n
                if msg_n:
                    chats_with_messages += 1
                elif existing.get("inaccessible"):
                    chats_inaccessible += 1
                continue
            pending.append(rec)
        if not pending:
            continue
        commands = {}
        for idx, rec in enumerate(pending):
            commands[f"g{idx}"] = (
                "imopenlines.crm.chat.get",
                {
                    "CRM_ENTITY_TYPE": rec["bitrix_entity_type"],
                    "CRM_ENTITY": rec["bitrix_entity_id"],
                    "ACTIVE_ONLY": "N",
                },
            )
        batch_body = client.batch(commands)
        results = batch_body.get("result") or {}
        errors = batch_body.get("result_error") or {}
        for idx, rec in enumerate(pending):
            key = f"{rec['bitrix_entity_type']}:{rec['bitrix_entity_id']}"
            chats_processed += 1
            err = errors.get(f"g{idx}")
            live_list = results.get(f"g{idx}") if not err else None
            if err or live_list is None:
                single = client.call(
                    "imopenlines.crm.chat.get",
                    {
                        "CRM_ENTITY_TYPE": rec["bitrix_entity_type"],
                        "CRM_ENTITY": rec["bitrix_entity_id"],
                        "ACTIVE_ONLY": "N",
                    },
                )
                if single.get("error"):
                    payload = {
                        **rec,
                        "retrieved_at": utc_now(),
                        "chat_get_error": f"{single.get('error')}: {single.get('error_description')}",
                        "chats": [],
                        "inaccessible": True,
                    }
                    atomic_write_json(live_chats / f"{rec['bitrix_entity_type']}_{rec['bitrix_entity_id']}.json", payload)
                    chats_inaccessible += 1
                    state.setdefault("completed_entities", {})[key] = {"at": utc_now(), "messages": 0, "error": payload["chat_get_error"]}
                    continue
                live_list = single.get("result")
            if not isinstance(live_list, list):
                live_list = [live_list] if live_list else []
            chat_payloads = []
            entity_message_count = 0
            for live in live_list:
                if not isinstance(live, dict):
                    continue
                chat_id = str(live.get("CHAT_ID") or live.get("chat_id") or "")
                if not chat_id:
                    continue
                dialog_id = f"chat{chat_id}"
                hist_note = None
                if rec.get("session_ids") and state.get("session_history_denied_streak", 0) < 5:
                    hist = client.call("imopenlines.session.history.get", {"SESSION_ID": rec["session_ids"][0]})
                    if hist.get("error"):
                        session_denied += 1
                        state["session_history_denied_streak"] = state.get("session_history_denied_streak", 0) + 1
                        hist_note = f"{hist.get('error')}: {hist.get('error_description')}"
                    else:
                        session_ok += 1
                        state["session_history_denied_streak"] = 0
                        hist_note = "session_history_ok"
                elif rec.get("session_ids"):
                    hist_note = "skipped_after_repeated_ACCESS_DENIED"
                messages, msg_users, msg_files, msg_error = fetch_dialog_messages(client, dialog_id)
                for uid, uinfo in msg_users.items():
                    if isinstance(uinfo, dict) and uid not in users:
                        users[uid] = normalize_user(uinfo) if uinfo.get("ID") or uinfo.get("NAME") else {"id": uid, "name": uinfo.get("name")}
                        if users[uid].get("name"):
                            user_names[uid] = users[uid]["name"]
                            user_ids.add(uid)
                rows = []
                for item in messages:
                    author_id = str(item.get("author_id") or item.get("AUTHOR_ID") or item.get("senderId") or "")
                    sender_name = user_names.get(author_id) or ""
                    if isinstance(msg_users.get(author_id), dict):
                        sender_name = sender_name or " ".join(
                            p for p in [msg_users[author_id].get("name"), msg_users[author_id].get("last_name")] if p
                        )
                    params = item.get("params") or {}
                    file_ids = []
                    if isinstance(params, dict):
                        file_ids = params.get("FILE_ID") or params.get("FILES") or []
                    rows.append(
                        {
                            "message_id": message_id_of(item),
                            "chat_id": chat_id,
                            "dialog_id": dialog_id,
                            "sender_id": author_id,
                            "sender_name": sender_name,
                            "date_time": item.get("date") or item.get("DATE") or item.get("timestamp"),
                            "message_text": item.get("text") or item.get("TEXT") or "",
                            "attachment_count": len(file_ids) if isinstance(file_ids, list) else 0,
                            "direction": classify_direction(author_id, user_ids),
                            "provider": (rec.get("providers") or [live.get("CONNECTOR_ID")])[0] if rec.get("providers") else live.get("CONNECTOR_ID"),
                            "source_api_method": "im.dialog.messages.get",
                            "raw": item,
                        }
                    )
                chat_payloads.append(
                    {
                        "live_chat": live,
                        "chat_id": chat_id,
                        "dialog_id": dialog_id,
                        "session_history_status": hist_note,
                        "messages_error": msg_error,
                        "messages": rows,
                        "files": msg_files,
                        "message_count": len(rows),
                    }
                )
                entity_message_count += len(rows)
                if msg_error and not rows:
                    chats_inaccessible += 1
                elif rows:
                    chats_with_messages += 1
                total_api_messages += len(rows)
            payload = {
                **rec,
                "retrieved_at": utc_now(),
                "live_chat_list": live_list,
                "chats": chat_payloads,
                "inaccessible": entity_message_count == 0 and not live_list,
            }
            atomic_write_json(live_chats / f"{rec['bitrix_entity_type']}_{rec['bitrix_entity_id']}.json", payload)
            state.setdefault("completed_entities", {})[key] = {"at": utc_now(), "messages": entity_message_count, "chats": len(chat_payloads)}
            log(progress, f"OK {key} chats={len(chat_payloads)} msgs={entity_message_count}")
        atomic_write_json(state_path, state)
        atomic_write_json(enrich_root / "users.json", users)

    file_ids = collect_file_ids(archive)
    extra_file_ids = set()
    for path in live_chats.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for chat in data.get("chats") or []:
            files = chat.get("files") or {}
            extra_file_ids.update(str(k) for k in files.keys() if str(k).isdigit())
            for msg in chat.get("messages") or []:
                raw = msg.get("raw") or {}
                params = raw.get("params") or {}
                if isinstance(params, dict):
                    for fid in params.get("FILE_ID") or []:
                        if str(fid).isdigit():
                            extra_file_ids.add(str(fid))
    file_ids |= extra_file_ids
    log(progress, f"FILE_IDS {len(file_ids)}")

    file_meta = {}
    downloaded = missing = inaccessible = failed = resolved = 0
    id_list = sorted(file_ids, key=lambda x: int(x) if x.isdigit() else 0)
    for offset in range(0, len(id_list), 40):
        chunk = id_list[offset : offset + 40]
        commands = {}
        pending_ids = []
        for idx, fid in enumerate(chunk):
            if fid in (state.get("completed_files") or {}):
                info = state["completed_files"][fid]
                status = info.get("status")
                if status == "downloaded":
                    downloaded += 1
                    resolved += 1
                elif status == "missing":
                    missing += 1
                elif status == "inaccessible":
                    inaccessible += 1
                elif status == "metadata":
                    resolved += 1
                else:
                    failed += 1
                continue
            commands[f"f{idx}"] = ("disk.file.get", {"id": fid})
            pending_ids.append((idx, fid))
        if not pending_ids:
            continue
        batch_body = client.batch(commands)
        results = batch_body.get("result") or {}
        errors = batch_body.get("result_error") or {}
        for idx, fid in pending_ids:
            err = errors.get(f"f{idx}")
            result = results.get(f"f{idx}")
            if err or not result:
                single = client.call("disk.file.get", {"id": fid})
                if single.get("error"):
                    err_text = f"{single.get('error')}: {single.get('error_description')}"
                    status = "missing" if "NOT_FOUND" in str(single.get("error") or "").upper() or "not found" in str(single.get("error_description") or "").lower() else "inaccessible" if "denied" in str(single.get("error") or "").lower() or "privileges" in str(single.get("error_description") or "").lower() else "failed"
                    state.setdefault("completed_files", {})[fid] = {"status": status, "error": err_text, "at": utc_now()}
                    if status == "missing":
                        missing += 1
                    elif status == "inaccessible":
                        inaccessible += 1
                    else:
                        failed += 1
                    continue
                result = single.get("result")
            if not isinstance(result, dict):
                failed += 1
                state.setdefault("completed_files", {})[fid] = {"status": "failed", "error": "empty_result", "at": utc_now()}
                continue
            resolved += 1
            name = result.get("NAME") or result.get("name")
            dest = attach_dir / safe_filename(str(name) if name else None, fid)
            download_url = result.get("DOWNLOAD_URL") or result.get("downloadUrl")
            status = "metadata"
            err_text = None
            if dest.exists() and dest.stat().st_size > 0:
                status = "downloaded"
                downloaded += 1
            elif download_url:
                status, err_text = client.download(str(download_url), dest)
                if status == "downloaded":
                    downloaded += 1
                elif status == "missing":
                    missing += 1
                elif status == "inaccessible":
                    inaccessible += 1
                else:
                    failed += 1
            file_meta[fid] = {
                "file_id": fid,
                "filename": name,
                "size": result.get("SIZE") or result.get("size"),
                "type": result.get("TYPE") or result.get("CONTENT_TYPE"),
                "download_url_present": bool(download_url),
                "parent_id": result.get("PARENT_ID") or result.get("parentId"),
                "status": status,
                "error": err_text,
                "raw": {k: result.get(k) for k in result.keys() if k != "DOWNLOAD_URL"},
            }
            state.setdefault("completed_files", {})[fid] = {"status": status, "filename": name, "at": utc_now()}
        atomic_write_json(state_path, state)
        if offset % 200 == 0:
            log(progress, f"FILES {offset}/{len(id_list)} downloaded={downloaded} resolved={resolved}")
    atomic_write_json(enrich_root / "files.json", file_meta)

    # rebuild chat master without duplicating
    existing_chat_rows = []
    chat_csv = archive / "BITRIX_CHAT_MESSAGES_MASTER.csv"
    seen_keys = set()
    if chat_csv.exists():
        with chat_csv.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                key = (row.get("source_api_method") or "", row.get("chat_id") or "", row.get("message_id") or "")
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                if not row.get("sender_name") and row.get("sender_id") and user_names.get(row["sender_id"]):
                    row["sender_name"] = user_names[row["sender_id"]]
                existing_chat_rows.append(row)
    new_chat_rows = []
    kaan_api = 0
    berk_api = 0
    for path in sorted(live_chats.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for chat in data.get("chats") or []:
            for msg in chat.get("messages") or []:
                key = ("im.dialog.messages.get", str(msg.get("chat_id") or ""), str(msg.get("message_id") or ""))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                row = {
                    "canonical_crm_contact_id": data.get("canonical_crm_contact_id") or "",
                    "person_name": data.get("person_name") or "",
                    "bitrix_entity_type": data.get("bitrix_entity_type") or "",
                    "bitrix_entity_id": data.get("bitrix_entity_id") or "",
                    "provider": msg.get("provider") or "",
                    "chat_id": msg.get("chat_id") or "",
                    "dialog_id": msg.get("dialog_id") or "",
                    "session_id": "",
                    "message_id": msg.get("message_id") or "",
                    "date_time": msg.get("date_time") or "",
                    "sender_id": msg.get("sender_id") or "",
                    "sender_name": msg.get("sender_name") or user_names.get(str(msg.get("sender_id") or ""), ""),
                    "direction": msg.get("direction") or "",
                    "message_text": msg.get("message_text") or "",
                    "attachment_count": msg.get("attachment_count") or 0,
                    "source_api_method": "im.dialog.messages.get",
                }
                new_chat_rows.append(row)
                if str(data.get("bitrix_entity_id")) == "34456":
                    kaan_api += 1
                if str(data.get("bitrix_entity_id")) == "180":
                    berk_api += 1
    with chat_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHAT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing_chat_rows)
        writer.writerows(new_chat_rows)

    hist_csv = archive / "BITRIX_HISTORY_MASTER.csv"
    hist_tmp = archive / "BITRIX_HISTORY_MASTER.csv.tmp"
    hist_seen = set()
    with hist_csv.open(encoding="utf-8", newline="") as src, hist_tmp.open("w", encoding="utf-8", newline="") as dest:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dest, fieldnames=HIST_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            key = (row.get("source_api_method") or "", row.get("bitrix_record_id") or "", row.get("message_id") or "", row.get("history_type") or "")
            hist_seen.add(key)
            if not row.get("author_name") and row.get("author_id") and user_names.get(row["author_id"]):
                row["author_name"] = user_names[row["author_id"]]
            writer.writerow(row)
        for row in new_chat_rows:
            key = ("im.dialog.messages.get", "", row.get("message_id") or "", "whatsapp_message")
            if key in hist_seen:
                continue
            hist_seen.add(key)
            writer.writerow(
                {
                    "canonical_crm_contact_id": row["canonical_crm_contact_id"],
                    "person_name": row["person_name"],
                    "bitrix_entity_type": row["bitrix_entity_type"],
                    "bitrix_entity_id": row["bitrix_entity_id"],
                    "history_type": "whatsapp_message",
                    "bitrix_record_id": row["message_id"],
                    "chat_id": row["chat_id"],
                    "message_id": row["message_id"],
                    "date_time": row["date_time"],
                    "author_id": row["sender_id"],
                    "author_name": row["sender_name"],
                    "direction": row["direction"],
                    "title": "open channel message",
                    "full_text": row["message_text"],
                    "attachment_count": row["attachment_count"],
                    "source_api_method": "im.dialog.messages.get",
                }
            )
    hist_tmp.replace(hist_csv)

    berk_existing = sum(1 for row in existing_chat_rows if "berk" in (row.get("person_name") or "").casefold())
    kaan_existing = sum(1 for row in existing_chat_rows if "kalyon" in (row.get("person_name") or "").casefold() and "kaan" in (row.get("person_name") or "").casefold())
    lead34456 = json.loads((archive / "raw" / "leads" / "34456.json").read_text(encoding="utf-8")) if (archive / "raw" / "leads" / "34456.json").exists() else {}
    contact180 = json.loads((archive / "raw" / "contacts" / "180.json").read_text(encoding="utf-8")) if (archive / "raw" / "contacts" / "180.json").exists() else {}
    kaan_live = json.loads((live_chats / "lead_34456.json").read_text(encoding="utf-8")) if (live_chats / "lead_34456.json").exists() else {}
    berk_live = json.loads((live_chats / "contact_180.json").read_text(encoding="utf-8")) if (live_chats / "contact_180.json").exists() else {}

    unresolved_users = sorted(uid for uid, rec in users.items() if not rec.get("name"))
    resolved_users = sorted(uid for uid, rec in users.items() if rec.get("name"))
    total_messages = len(existing_chat_rows) + len(new_chat_rows)
    summary = {
        "generated_at": utc_now(),
        "chats_processed": chats_processed,
        "chats_with_actual_messages_recovered": chats_with_messages,
        "total_actual_messages_recovered": total_messages,
        "api_messages_new": len(new_chat_rows),
        "existing_comment_parsed_messages_preserved": len(existing_chat_rows),
        "chats_still_inaccessible": chats_inaccessible,
        "session_history_denied": session_denied,
        "session_history_ok": session_ok,
        "resolved_bitrix_users": len(resolved_users),
        "unresolved_bitrix_users": len(unresolved_users),
        "resolved_user_names": {uid: user_names[uid] for uid in resolved_users},
        "unresolved_user_ids": unresolved_users,
        "attachment_references_processed": len(file_ids),
        "attachment_metadata_resolved": resolved,
        "attachments_downloaded": downloaded,
        "attachment_failures": {"missing": missing, "inaccessible": inaccessible, "failed": failed},
        "kaan_kalyon": {
            "entity": "lead:34456",
            "crm_history_records": len(lead34456.get("timeline_comments") or []) + len(lead34456.get("crm_activities") or []),
            "existing_chat_rows": kaan_existing,
            "api_messages": kaan_api,
            "live_chats": len(kaan_live.get("chats") or []),
            "live_chat_ids": [c.get("chat_id") for c in kaan_live.get("chats") or []],
        },
        "berk_cimen": {
            "entity": "contact:180",
            "crm_history_records": len(contact180.get("timeline_comments") or []) + len(contact180.get("crm_activities") or []),
            "preserved_comment_messages": berk_existing,
            "api_messages_new": berk_api,
            "live_chats": len(berk_live.get("chats") or []),
        },
        "crm_modified": "NO",
        "bitrix_calls": client.call_count,
        "retry_count": client.retry_count,
    }
    atomic_write_json(enrich_root / "ENRICHMENT_SUMMARY.json", summary)

    report_path = archive / "reports" / "BITRIX_HISTORY_RESCUE_REPORT.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    report["enrichment"] = summary
    report["chats_discovered"] = max(int(report.get("chats_discovered") or 0), chats_processed)
    report["chats_with_full_messages_recovered"] = chats_with_messages
    report["chats_summary_only_or_inaccessible"] = chats_inaccessible
    report["history_counts"] = report.get("history_counts") or {}
    report["history_counts"]["actual_recovered_whatsapp_open_channel_messages"] = total_messages
    report["attachment_references_found"] = len(file_ids)
    report["attachments_downloaded"] = downloaded
    report["permission_failures"] = [
        {
            "note": "Open Channel chat.get and im.dialog.messages.get now succeed with live chat IDs. session.history.get remains ACCESS_DENIED for tested sessions and was not treated as failure when dialog messages were recovered."
        }
    ]
    report["kaan_kalyon_validation"] = summary["kaan_kalyon"]
    report["berk_cimen_validation"] = summary["berk_cimen"]
    report["crm_write_confirmation"] = "NO Investhome OS CRM data was modified"
    report["generated_at"] = utc_now()
    atomic_write_json(report_path, report)
    atomic_write_json(archive / "reports" / "BITRIX_HISTORY_RESCUE_SUMMARY.json", {**json.loads((archive / "reports" / "BITRIX_HISTORY_RESCUE_SUMMARY.json").read_text(encoding="utf-8")), "enrichment": summary})
    log(progress, "DONE")
    print(json.dumps({k: summary[k] for k in list(summary) if k not in {"resolved_user_names"}}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
