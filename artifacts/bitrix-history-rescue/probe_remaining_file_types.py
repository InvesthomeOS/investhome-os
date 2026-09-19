"""Probe live descriptors for one entity-field, one email, one WhatsApp file. Read-only."""
from __future__ import annotations

import json
import re
from pathlib import Path
import urllib.parse

from recover_remaining_66 import ENV_PATH, load_env, webhook_base, BitrixClient, redact, walk_urls_and_ids

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")


def shape(obj, depth=0):
    if depth > 4:
        return "..."
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("url", "href", "src", "download", "show")) and isinstance(v, str):
                parsed = urllib.parse.urlparse(v)
                qs = urllib.parse.parse_qs(parsed.query)
                out[k] = {
                    "path": parsed.path,
                    "qs_keys": sorted(qs.keys()),
                    "has_auth": bool(qs.get("auth")),
                    "fileId": (qs.get("fileId") or qs.get("fileid") or [None])[0],
                    "ownerTypeId": (qs.get("ownerTypeId") or qs.get("ownerType") or [None])[0],
                    "ownerId": (qs.get("ownerId") or [None])[0],
                    "prefix": v[:80].split("auth=")[0],
                }
            else:
                out[k] = shape(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [shape(x, depth + 1) for x in obj[:6]] + (["..."] if len(obj) > 6 else [])
    if isinstance(obj, str) and len(obj) > 120:
        return obj[:120] + "..."
    return obj


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    contact = client.call("crm.contact.get", {"id": "390"})
    rec = contact.get("result") or {}
    uf = rec.get("UF_CRM_1692366477437")
    photo = rec.get("PHOTO")
    uf_keys = [k for k in rec.keys() if str(k).upper().startswith("UF") and rec.get(k) not in (None, "", [], {})]
    activity = client.call("crm.activity.get", {"id": "23482"})
    act = activity.get("result") or {}
    act_file_keys = {k: type(act.get(k)).__name__ for k in act.keys() if any(tok in str(k).upper() for tok in ("FILE", "STORAGE", "WEBDAV", "ATTACH"))}
    # chats archive
    chat_path = ARCHIVE / "raw" / "chats" / "live" / "contact_180.json"
    chats = {}
    if chat_path.exists():
        raw = json.loads(chat_path.read_text(encoding="utf-8"))
        chats = {
            "chat_ids": [c.get("chat_id") or c.get("dialog_id") for c in (raw.get("chats") or [])][:10],
            "file_keys": list(((raw.get("chats") or [{}])[0].get("files") or {}).keys())[:10] if raw.get("chats") else [],
        }
        # find 89178
        hit = None
        for c in raw.get("chats") or []:
            files = c.get("files") or {}
            if "89178" in {str(k) for k in files}:
                node = files.get("89178") or files.get(89178)
                hit = {"chat_id": c.get("chat_id"), "dialog_id": c.get("dialog_id"), "file_shape": shape(node)}
                break
        chats["file_89178"] = hit
    # try im.dialog with archive chat id
    dialog_try = None
    if chats.get("chat_ids"):
        dialog_try = client.call("im.dialog.messages.get", {"DIALOG_ID": chats["chat_ids"][0], "LIMIT": 5})
        dialog_try = {
            "error": dialog_try.get("error"),
            "result_keys": list((dialog_try.get("result") or {}).keys()) if isinstance(dialog_try.get("result"), dict) else type(dialog_try.get("result")).__name__,
            "files_shape": shape((dialog_try.get("result") or {}).get("files") or (dialog_try.get("result") or {}).get("FILES")) if isinstance(dialog_try.get("result"), dict) else None,
        }
    fields = client.call("crm.contact.fields", {})
    spec = (fields.get("result") or {}).get("UF_CRM_1692366477437") or {}
    out = {
        "uf_type": spec.get("type"),
        "uf_title": spec.get("formLabel") or spec.get("listLabel") or spec.get("title"),
        "uf_value_shape": shape(uf),
        "photo_shape": shape(photo),
        "populated_uf_keys": uf_keys[:30],
        "activity_file_keys": act_file_keys,
        "activity_files_shape": shape(act.get("FILES")),
        "activity_storage": shape(act.get("STORAGE_ELEMENT_IDS")),
        "activity_settings_has_files": "FILE" in json.dumps(act.get("SETTINGS") or {}),
        "chats": chats,
        "dialog_try": dialog_try,
        "contact_error": contact.get("error"),
        "activity_error": activity.get("error"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
