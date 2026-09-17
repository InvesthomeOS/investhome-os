"""Probe remaining read-only chat/history methods. Never prints webhook URLs."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


def load_env(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip().lstrip("\ufeff")
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def webhook_base(raw: str) -> str:
    value = raw.strip()
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


def call(base: str, method: str, payload: dict) -> dict:
    url = urllib.parse.urljoin(base, method + ".json")
    data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:800]
        return {"http_error": exc.code, "body": raw}
    except Exception as exc:  # noqa: BLE001
        return {"exception": type(exc).__name__, "msg": str(exc)[:200]}
    if body.get("error"):
        return {"error": body.get("error"), "error_description": body.get("error_description")}
    result = body.get("result")
    text = json.dumps(result, ensure_ascii=False, default=str)
    if len(text) > 6000:
        text = text[:6000] + "...TRUNCATED"
    return {"ok": True, "result": json.loads(text) if text.endswith("}") or text.endswith("]") else text, "time": body.get("time")}


def dump(label: str, obj) -> None:
    print(f"\n===== {label} =====")
    print(json.dumps(obj, ensure_ascii=False, default=str)[:8000])


def main() -> None:
    base = webhook_base(load_env("/tmp/.env").get("BITRIX_WEBHOOK_URL") or "")
    dump("scope", call(base, "scope", {}))
    dump("history.session.10542", call(base, "imopenlines.session.history.get", {"SESSION_ID": 10542}))
    dump("history.session.str", call(base, "imopenlines.session.history.get", {"SESSION_ID": "10542"}))
    dump("dialog.get.10706", call(base, "imopenlines.dialog.get", {"CHAT_ID": 10706}))
    dump("dialog.get.user_code", call(base, "imopenlines.dialog.get", {"USER_CODE": "bitrix_whatcrm_net_70680444|24|chat.905327066018|10706"}))
    dump("dialog.multi", call(base, "imopenlines.dialog.multi.get", {"USER_CODE": "bitrix_whatcrm_net_70680444|24|chat.905327066018|10706"}))
    dump("im.dialog.messages.chat10706", call(base, "im.dialog.messages.get", {"DIALOG_ID": "chat10706"}))
    dump("im.dialog.messages.10706", call(base, "im.dialog.messages.get", {"DIALOG_ID": "10706"}))
    dump("user.search.92", call(base, "user.search", {"FILTER[ID]": 92}))
    dump("department.get", call(base, "department.get", {}))
    dump("crm.status.list", call(base, "crm.status.list", {"filter[ENTITY_ID]": "STATUS"}))
    dump("disk.storage.getlist", call(base, "disk.storage.getlist", {"start": 0}))
    dump("batch.user", call(base, "batch", {"halt": 0, "cmd[u]": "user.get?ID=92"}))
    dump("imopenlines.config.list", call(base, "imopenlines.config.list.get", {}))


if __name__ == "__main__":
    main()
