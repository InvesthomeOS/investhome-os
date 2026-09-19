"""Inspect crm.item.get file fields and WhatsApp chat files. Read-only."""
from __future__ import annotations

import json
from probe_remaining_file_types import shape
from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base
from pathlib import Path

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    item = client.call("crm.item.get", {"entityTypeId": 3, "id": 390}).get("result") or {}
    inner = item.get("item") or {}
    fileish = {}
    for k, v in inner.items():
        if v in (None, "", [], {}, 0, "0"):
            continue
        kl = str(k).lower()
        if "file" in kl or "ufCrm1692366477437" in k or "identification" in kl or k.startswith("uf"):
            fileish[k] = shape(v)
    dialog = client.call("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LIMIT": 50})
    result = dialog.get("result") or {}
    files = result.get("files") or {}
    file_index = {}
    if isinstance(files, dict):
        file_index = {str(k): shape(v) for k, v in list(files.items())[:8]}
        hit = files.get("89178") or files.get(89178)
    else:
        hit = None
    # also chat 12068
    dialog2 = client.call("im.dialog.messages.get", {"DIALOG_ID": "chat12068", "LIMIT": 50})
    files2 = (dialog2.get("result") or {}).get("files") or {}
    hit2 = None
    if isinstance(files2, dict):
        hit2 = files2.get("89178") or files2.get(89178)
        keys2 = list(files2.keys())[:20]
    else:
        keys2 = []
    methods = client.call("methods", {"full": True, "filter": "file"}).get("result") or []
    interesting = [m for m in methods if any(tok in str(m).lower() for tok in ("download", "crm.item", "attached", "uf", "show", "mail"))][:80]
    # try disk.file.get on a whatsapp file id from files map
    sample_fid = next(iter(files.keys()), None) if isinstance(files, dict) and files else None
    disk_try = None
    if sample_fid:
        body = client.call("disk.file.get", {"id": sample_fid})
        disk_try = {"id": sample_fid, "error": body.get("error"), "has_url": bool((body.get("result") or {}).get("DOWNLOAD_URL") if isinstance(body.get("result"), dict) else None)}
        if isinstance(body.get("result"), dict):
            content, mime, err = try_download(client, body["result"].get("DOWNLOAD_URL") or "")
            disk_try["download_ok"] = bool(content)
            disk_try["bytes"] = len(content or b"")
            disk_try["err"] = err
            disk_try["name"] = body["result"].get("NAME")
    print(json.dumps({
        "item_fileish": fileish,
        "chat13496_file_count": len(files) if isinstance(files, dict) else None,
        "chat13496_files": file_index,
        "chat13496_89178": shape(hit) if hit else None,
        "chat12068_file_keys": keys2,
        "chat12068_89178": shape(hit2) if hit2 else None,
        "interesting_methods": interesting,
        "disk_try": disk_try,
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
