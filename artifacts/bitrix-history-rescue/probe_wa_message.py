"""Dump one WhatsApp message attachment descriptors without URLs."""
from __future__ import annotations

import json
from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base, is_binary


def redact_strings(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str) and ("http" in v or v.startswith("/")):
                out[k] = v.split("?")[0][:80]
            else:
                out[k] = redact_strings(v)
        return out
    if isinstance(obj, list):
        return [redact_strings(x) for x in obj]
    return obj


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    dialog = client.call("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LAST_ID": 2055945, "LIMIT": 3})
    result = dialog.get("result") or {}
    msgs = result.get("messages") or []
    target = next((m for m in msgs if str(m.get("id")) == "2055944"), msgs[0] if msgs else {})
    disk = client.call("disk.file.get", {"id": 89178})
    disk_res = disk.get("result") if isinstance(disk.get("result"), dict) else {}
    content = None
    mime = err = None
    if disk_res.get("DOWNLOAD_URL"):
        content, mime, err = try_download(client, disk_res["DOWNLOAD_URL"])
    attached = client.call("disk.attachedObject.get", {"id": 89178})
    imdisk = client.call("im.disk.file.get", {"id": 89178})
    print(json.dumps({
        "result_keys": list(result.keys()),
        "message": redact_strings(target),
        "files_type": type(result.get("files")).__name__,
        "disk_error": disk.get("error"),
        "disk_name": disk_res.get("NAME"),
        "disk_ok": bool(content),
        "disk_bytes": len(content or b""),
        "disk_mime": mime,
        "disk_err": err,
        "disk_pdf": bool(content and content.startswith(b"%PDF")),
        "attached_error": attached.get("error"),
        "attached_keys": list((attached.get("result") or {}).keys()) if isinstance(attached.get("result"), dict) else None,
        "imdisk_error": imdisk.get("error"),
        "imdisk_keys": list((imdisk.get("result") or {}).keys()) if isinstance(imdisk.get("result"), dict) else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
