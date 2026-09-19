"""Probe controller getFile for email attachments and im.* file methods."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from recover_remaining_66 import ENV_PATH, BitrixClient, HTML_HEAD, load_env, webhook_base, with_auth


def raw_get(client, path_or_url, payload=None):
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = urllib.parse.urljoin(client.base, path_or_url)
        if payload:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(payload)
    url = with_auth(client, url)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(64)
            rest = b""
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                rest += chunk
            body = data + rest
            ctype = (resp.headers.get("Content-Type") or "").lower()
            return {
                "http": resp.status,
                "ctype": ctype.split(";")[0],
                "bytes": len(body),
                "html": bool(HTML_HEAD.search(body[:200])),
                "pdf": body.startswith(b"%PDF"),
                "jpeg": body[:3] == b"\xff\xd8\xff",
                "json_error": body.lstrip()[:1] == b"{" and b"error" in body[:200],
                "magic": body[:12].hex(),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(200)
        return {"http": exc.code, "err": str(exc.reason), "magic": raw[:20].hex()}


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    methods = client.call("methods", {"full": True, "filter": "im."}).get("result") or []
    im_file = [m for m in methods if "file" in str(m).lower() or "disk" in str(m).lower()]
    json_calls = {}
    for method, payload in (
        ("crm.controller.item.getFile", {"entityTypeId": 6, "id": 23482, "fieldName": "FILES", "fileId": 30942}),
        ("crm.controller.item.getFile", {"entityTypeId": 1, "id": 13924, "fieldName": "FILES", "fileId": 30942}),
        ("crm.activity.configurable.get", {"id": 23482}),
    ):
        body = client.call(method, payload)
        json_calls[f"{method}:{payload.get('entityTypeId') or payload.get('id')}"] = {
            "error": body.get("error"),
            "desc": str(body.get("error_description") or "")[:180],
            "result_type": type(body.get("result")).__name__,
        }
    raw = {
        "controller_email": raw_get(client, "crm.controller.item.getFile", {"entityTypeId": 6, "id": 23482, "fieldName": "FILES", "fileId": 30942}),
        "controller_contact_known": None,
    }
    print(json.dumps({"im_file_methods": im_file, "json_calls": json_calls, "raw": raw}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
