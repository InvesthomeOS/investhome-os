"""Follow-up read-only tests for confirmed disk file 81568 on comment 507424."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def webhook_base(raw: str) -> str:
    value = (raw or "").strip()
    marker = "BURAYA_BITRIX_URL="
    if marker in value:
        value = value.split(marker, 1)[1].strip()
    parsed = urllib.parse.urlparse(value.strip().strip('"').strip("'"))
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(segs) + "/", "", "", ""))


def origin(base: str) -> str:
    return urllib.parse.urlunparse(urllib.parse.urlparse(base)[:2] + ("", "", "", ""))


def token(base: str) -> str:
    segs = [s for s in urllib.parse.urlparse(base).path.split("/") if s]
    return segs[-1] if segs else ""


def call(base: str, method: str, payload: dict | None = None) -> dict:
    url = urllib.parse.urljoin(base, method + ".json")
    data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": f"HTTP {exc.code}", "error_description": raw[:300]}


def probe(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            chunk = resp.read(240)
            ctype = (resp.headers.get("Content-Type") or "").lower()
            return {
                "http": resp.status,
                "content_type": ctype,
                "content_disposition": resp.headers.get("Content-Disposition"),
                "head": chunk[:80].decode("latin1", errors="replace"),
                "looks_html": chunk.lstrip().startswith(b"<") or "text/html" in ctype,
                "looks_pdf": chunk.startswith(b"%PDF"),
            }
    except urllib.error.HTTPError as exc:
        return {"http": exc.code, "reason": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        return {"exception": type(exc).__name__}


def slim_api(body: dict) -> dict:
    result = body.get("result")
    out = {
        "error": body.get("error"),
        "error_description": body.get("error_description"),
        "has_result": result not in (None, False, [], {}),
    }
    if isinstance(result, dict):
        out["result_keys"] = sorted(result.keys())
        for key in ("ID", "NAME", "IS_ADMIN", "ADMIN", "ACTIVE", "STORAGE_ID", "DOWNLOAD_URL"):
            if key in result:
                out[key] = result.get(key)
    elif result is not None:
        out["result"] = result
    return out


def main() -> None:
    base = webhook_base(load_env(Path("/tmp/.env")).get("BITRIX_WEBHOOK_URL") or "")
    host = origin(base)
    auth = token(base)
    file_id = "81568"
    download = f"{host}/disk/downloadFile/{file_id}/?ncc=1"
    authed = download + f"&auth={auth}"
    comments = call(
        base,
        "crm.timeline.comment.list",
        {"filter[ENTITY_TYPE]": "contact", "filter[ENTITY_ID]": "1128", "start": 0},
    )
    target = None
    for comment in comments.get("result") or []:
        if str(comment.get("ID")) == "507424":
            target = comment
            break
    files = (target or {}).get("FILES") or {}
    node = files.get("81568") or files.get(81568) or {}
    report = {
        "user.admin": slim_api(call(base, "user.admin", {})),
        "user.get.11018": slim_api(call(base, "user.get", {"ID": 11018})),
        "scope": call(base, "scope", {}).get("result"),
        "comment_text": str((target or {}).get("COMMENT") or "")[:250],
        "file_node_keys": sorted(node.keys()) if isinstance(node, dict) else None,
        "urlDownload_path": "/disk/downloadFile/81568/",
        "GET_urlDownload": probe(download),
        "GET_urlDownload_with_webhook_auth": probe(authed),
        "disk.file.get": slim_api(call(base, "disk.file.get", {"id": file_id})),
        "disk.attachedObject.get": slim_api(call(base, "disk.attachedObject.get", {"id": file_id})),
        "disk.storage.getlist": slim_api(call(base, "disk.storage.getlist", {"start": 0})),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    text = text.replace(base, "[REDACTED_WEBHOOK]/").replace(auth, "[REDACTED]")
    text = re.sub(r"https?://investhome2\.bitrix24\.com", "[BITRIX_HOST]", text)
    print(text)


if __name__ == "__main__":
    main()
