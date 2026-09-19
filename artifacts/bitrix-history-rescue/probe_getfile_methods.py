"""Find getFile methods and fetch WhatsApp file via chat pagination."""
from __future__ import annotations

import json
from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base, is_binary


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    methods = client.call("methods", {"full": True}).get("result") or []
    hits = [m for m in methods if "getfile" in str(m).lower() or "get_file" in str(m).lower() or "file.download" in str(m).lower()]
    dialog = client.call("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LAST_ID": 2055945, "LIMIT": 15})
    result = dialog.get("result") or {}
    files = result.get("files") or {}
    file_meta = None
    download = None
    if isinstance(files, dict):
        node = files.get("89178") or files.get(89178)
        if isinstance(node, dict):
            file_meta = {k: (v if not isinstance(v, str) or len(v) < 40 else v.split("?")[0]) for k, v in node.items() if k.lower() in {"id", "name", "type", "size", "urldownload", "url", "download_url", "authorid"}}
            url = node.get("urlDownload") or node.get("url") or node.get("DOWNLOAD_URL")
            content, mime, err = try_download(client, url or "")
            download = {"ok": bool(content and is_binary(content, mime)), "bytes": len(content or b""), "mime": mime, "err": err, "pdf": bool(content and content.startswith(b"%PDF"))}
            if not content:
                disk = client.call("disk.file.get", {"id": "89178"})
                res = disk.get("result") if isinstance(disk.get("result"), dict) else {}
                content, mime, err = try_download(client, res.get("DOWNLOAD_URL") or "")
                download = {"via": "disk.file.get", "disk_error": disk.get("error"), "ok": bool(content), "bytes": len(content or b""), "mime": mime, "err": err, "name": res.get("NAME"), "pdf": bool(content and content.startswith(b"%PDF"))}
    print(json.dumps({
        "getfile_methods": hits,
        "dialog_error": dialog.get("error"),
        "file_keys": list(files.keys())[:20] if isinstance(files, dict) else type(files).__name__,
        "file_89178_meta": file_meta,
        "download": download,
        "message_ids": [m.get("id") for m in (result.get("messages") or [])[:8]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
