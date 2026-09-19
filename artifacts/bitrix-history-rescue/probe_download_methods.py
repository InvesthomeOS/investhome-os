"""Probe extra download methods. Read-only. Never print webhook URLs."""
from __future__ import annotations

import json
from recover_remaining_66 import ENV_PATH, load_env, webhook_base, BitrixClient, with_auth, try_download


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    act = client.call("crm.activity.get", {"id": "23482"}).get("result") or {}
    keys = sorted(act.keys())
    interesting = {k: act.get(k) for k in keys if any(t in k.upper() for t in ("MAIL", "MESSAGE", "PROVIDER", "ASSOCIAT", "STORAGE", "UF_", "OWNER", "TYPE", "DIRECTION", "SUBJECT"))}
    # truncate strings
    for k, v in list(interesting.items()):
        if isinstance(v, str) and len(v) > 200:
            interesting[k] = v[:200] + "..."
    contact = client.call("crm.contact.get", {"id": "390"}).get("result") or {}
    uf = contact.get("UF_CRM_1692366477437") or {}
    rel = uf.get("downloadUrl") or ""
    abs_url = client.origin + rel if rel.startswith("/") else rel
    tests = {}
    for label, url in (
        ("uf_raw", abs_url),
        ("uf_auth", with_auth(client, abs_url)),
        ("email_raw", (act.get("FILES") or [{}])[0].get("url")),
        ("email_auth", with_auth(client, (act.get("FILES") or [{}])[0].get("url") or "")),
    ):
        content, mime, err = try_download(client, url or "")
        tests[label] = {
            "ok": bool(content),
            "bytes": len(content or b""),
            "mime": mime,
            "err": err,
            "magic": (content[:8].hex() if content else None),
        }
    methods = {}
    for method, payload in (
        ("crm.item.get", {"entityTypeId": 3, "id": 390}),
        ("mail.message.get", {"id": act.get("ASSOCIATED_ENTITY_ID") or act.get("UF_MAIL_MESSAGE") or 0}),
        ("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LIMIT": 5}),
        ("im.dialog.messages.get", {"DIALOG_ID": "13496", "CHAT_ID": 13496, "LIMIT": 5}),
        ("im.chat.get", {"CHAT_ID": 13496}),
        ("imopenlines.session.history.get", {"SESSION_ID": 13496}),
        ("methods", {"full": True, "filter": "file"}),
    ):
        key = f"{method}:{json.dumps(payload, sort_keys=True)[:80]}"
        body = client.call(method, payload)
        result = body.get("result")
        methods[key] = {
            "error": body.get("error"),
            "error_description": str(body.get("error_description") or "")[:180],
            "result_type": type(result).__name__,
            "result_keys": list(result.keys())[:20] if isinstance(result, dict) else None,
            "result_len": len(result) if isinstance(result, (list, dict, str)) else None,
        }
    print(json.dumps({"activity_interesting": interesting, "tests": tests, "methods": methods, "activity_keys": keys}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
