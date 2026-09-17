"""Debug Bitrix webhook path construction without printing secrets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


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
    return value if value.endswith("/") else value + "/"


def describe(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    segs = [s for s in parsed.path.split("/") if s]
    return {
        "scheme": parsed.scheme,
        "has_query": bool(parsed.query),
        "path_seg_count": len(segs),
        "first_seg": segs[0] if segs else "",
        "last_seg": segs[-1] if segs else "",
        "last_seg_len": len(segs[-1]) if segs else 0,
        "host_has_bitrix": "bitrix24" in (parsed.netloc or "").lower(),
    }


def call(url: str, payload: dict, method: str = "POST") -> dict:
    if method == "GET":
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(payload, doseq=True)
        req = urllib.request.Request(full, method="GET")
    else:
        data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {"http": resp.status, "keys": list(body.keys()), "error": body.get("error"), "error_description": body.get("error_description"), "has_result": "result" in body, "result_type": type(body.get("result")).__name__}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:500]
        return {"http": exc.code, "body": raw.replace("http://", "").replace("https://", "")}
    except Exception as exc:  # noqa: BLE001
        return {"exception": type(exc).__name__, "msg": str(exc)[:200]}


def main() -> None:
    env = load_env("/tmp/.env")
    raw = env.get("BITRIX_WEBHOOK_URL") or ""
    base = webhook_base(raw)
    print("RAW_LEN", len(raw))
    print("BASE", describe(base))
    joined = urllib.parse.urljoin(base, "crm.lead.get.json")
    concat = base + "crm.lead.get.json"
    print("JOINED", describe(joined))
    print("CONCAT", describe(concat))
    print("JOINED_EQ_CONCAT", joined == concat)
    print("POST_JOIN", call(joined, {"id": 34456}, "POST"))
    print("POST_CONCAT", call(concat, {"id": 34456}, "POST"))
    print("GET_CONCAT", call(concat, {"id": 34456}, "GET"))


if __name__ == "__main__":
    main()
