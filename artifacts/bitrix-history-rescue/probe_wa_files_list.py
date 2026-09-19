"""Inspect IM files list items and mobile.disk.getfilebyobjectid."""
from __future__ import annotations

import json
from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base, is_binary


def slim(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str) and ("http" in v or v.startswith("/")):
                out[k] = v.split("?")[0][:90]
            elif isinstance(v, (dict, list)):
                out[k] = slim(v)
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [slim(x) for x in obj[:5]]
    return obj


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    dialog = client.call("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LAST_ID": 2055945, "LIMIT": 3})
    files = (dialog.get("result") or {}).get("files")
    mobile = client.call("mobile.disk.getfilebyobjectid", {"id": 89178})
    mobile2 = client.call("mobile.disk.getfilebyobjectid", {"objectId": 89178})
    results = {}
    if isinstance(files, list):
        for node in files:
            if not isinstance(node, dict):
                continue
            fid = str(node.get("id") or node.get("ID") or "")
            if fid != "89178" and len(files) > 1:
                continue
            for key in ("urlDownload", "url", "downloadUrl", "DOWNLOAD_URL", "urlPreview", "urlShow"):
                url = node.get(key)
                if url:
                    content, mime, err = try_download(client, url)
                    results[f"{fid}:{key}"] = {"ok": bool(content and is_binary(content, mime)), "bytes": len(content or b""), "mime": mime, "err": err, "pdf": bool(content and content.startswith(b"%PDF"))}
    print(json.dumps({
        "files_len": len(files) if isinstance(files, list) else files,
        "files_slim": slim(files),
        "mobile_error": mobile.get("error"),
        "mobile_desc": str(mobile.get("error_description") or "")[:200],
        "mobile2_error": mobile2.get("error"),
        "downloads": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
