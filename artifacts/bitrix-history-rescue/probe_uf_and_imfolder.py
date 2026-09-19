"""Probe user.userfield.file.get and im.disk.folder.get. Read-only."""
from __future__ import annotations

import json
from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base, is_binary


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    calls = {}
    for payload in (
        {"id": 86818},
        {"fileId": 86818, "fieldName": "UF_CRM_1692366477437", "ownerId": 390, "entityId": 390},
        {"FILE_ID": 86818, "FIELD_NAME": "UF_CRM_1692366477437", "USER_ID": 390},
    ):
        body = client.call("user.userfield.file.get", payload)
        calls[json.dumps(payload, sort_keys=True)] = {
            "error": body.get("error"),
            "desc": str(body.get("error_description") or "")[:200],
            "result_type": type(body.get("result")).__name__,
            "result_preview": str(body.get("result"))[:150] if body.get("result") is not None else None,
        }
    folders = {}
    for payload in (
        {"CHAT_ID": 13496},
        {"chatId": 13496},
        {"DIALOG_ID": "chat13496"},
        {"folderId": 13496},
    ):
        body = client.call("im.disk.folder.get", payload)
        res = body.get("result")
        folders[json.dumps(payload, sort_keys=True)] = {
            "error": body.get("error"),
            "desc": str(body.get("error_description") or "")[:200],
            "result_type": type(res).__name__,
            "keys": list(res.keys())[:20] if isinstance(res, dict) else None,
            "len": len(res) if isinstance(res, (list, dict)) else None,
        }
        if isinstance(res, dict) and (res.get("ID") or res.get("id")):
            kids = client.call("disk.folder.getchildren", {"id": res.get("ID") or res.get("id")})
            folders[json.dumps(payload) + ":children"] = {
                "error": kids.get("error"),
                "count": len(kids.get("result") or []) if isinstance(kids.get("result"), list) else None,
                "first": (kids.get("result") or [None])[0] if isinstance(kids.get("result"), list) and kids.get("result") else None,
            }
            first = (kids.get("result") or [None])[0] if isinstance(kids.get("result"), list) else None
            if isinstance(first, dict):
                # redact urls
                first = {k: (v.split("?")[0][:80] if isinstance(v, str) and "http" in v else v) for k, v in first.items() if k in {"ID", "NAME", "TYPE", "SIZE", "DOWNLOAD_URL", "id", "name"}}
                folders[json.dumps(payload) + ":first"] = first
    print(json.dumps({"userfield": calls, "im_folder": folders}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
