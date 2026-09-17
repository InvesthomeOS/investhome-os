"""Read-only probe of Open Channel / activity payloads. Never prints webhook URLs."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)


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
    if value.startswith("BITRIX_WEBHOOK_URL="):
        value = value.split("=", 1)[1].strip()
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    path = "/" + "/".join(segs) + "/"
    rebuilt = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return rebuilt


def redact(text: str, webhook: str) -> str:
    cleaned = text.replace(webhook, "[REDACTED]")
    cleaned = WEBHOOK_RE.sub("[REDACTED_URL]", cleaned)
    return cleaned


def call(base: str, method: str, payload: dict, webhook: str) -> dict:
    url = urllib.parse.urljoin(base, method if method.endswith(".json") else method + ".json")
    data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}", "detail": redact(raw, webhook)[:2000]}
    except Exception as exc:  # noqa: BLE001
        return {"error": redact(str(exc), webhook)}
    if body.get("error"):
        body["error_description"] = redact(str(body.get("error_description") or ""), webhook)
    return body


def dump(label: str, obj) -> None:
    print(f"\n===== {label} =====")
    text = json.dumps(obj, ensure_ascii=False, default=str)
    if len(text) > 12000:
        text = text[:12000] + "...TRUNCATED"
    print(text)


def main() -> None:
    env = load_env("/tmp/.env")
    raw_url = env.get("BITRIX_WEBHOOK_URL") or ""
    base = webhook_base(raw_url)
    parsed = urllib.parse.urlparse(base)
    segs = [s for s in parsed.path.split("/") if s]
    print("BASE_SEGS", len(segs), "LAST", segs[-1] if segs else "", "BITRIX", "bitrix24" in parsed.netloc.lower())

    dump("lead.get.34456", call(base, "crm.lead.get", {"id": 34456}, base))
    dump(
        "user.get.92",
        call(base, "user.get", {"ID": 92}, base),
    )
    dump("user.current", call(base, "user.current", {}, base))
    dump(
        "user.get.start0",
        call(base, "user.get", {"start": 0}, base),
    )
    acts = call(
        base,
        "crm.activity.list",
        {
            "filter[OWNER_TYPE_ID]": 1,
            "filter[OWNER_ID]": 34456,
            "start": 0,
        },
        base,
    )
    dump("kaan.activities.keys", {"error": acts.get("error"), "n": len(acts.get("result") or []), "first": (acts.get("result") or [None])[0]})
    result = acts.get("result") or []
    wa = next(
        (
            item
            for item in result
            if "whatsapp" in str(item.get("SUBJECT") or "").casefold()
            or "open channel" in str(item.get("SUBJECT") or "").casefold()
        ),
        result[0] if result else None,
    )
    if wa:
        dump("kaan.activity.get", call(base, "crm.activity.get", {"id": wa.get("ID")}, base))
    dump(
        "kaan.chat.get",
        call(
            base,
            "imopenlines.crm.chat.get",
            {"CRM_ENTITY_TYPE": "lead", "CRM_ENTITY": 34456, "ACTIVE_ONLY": "N"},
            base,
        ),
    )
    dump(
        "kaan.chat.getLastId",
        call(
            base,
            "imopenlines.crm.chat.getLastId",
            {"CRM_ENTITY_TYPE": "lead", "CRM_ENTITY": 34456},
            base,
        ),
    )
    dump(
        "berk.chat.get",
        call(
            base,
            "imopenlines.crm.chat.get",
            {"CRM_ENTITY_TYPE": "contact", "CRM_ENTITY": 180, "ACTIVE_ONLY": "N"},
            base,
        ),
    )
    dump(
        "profile",
        call(base, "profile", {}, base),
    )
    dump(
        "methods.imopenlines",
        call(base, "methods", {"full": True, "filter": "imopenlines"}, base),
    )


if __name__ == "__main__":
    main()
