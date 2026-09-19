"""Read-only admin webhook test for disk file 81568. Never prints webhook URLs."""

from __future__ import annotations

import json
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
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    path = "/" + "/".join(segs) + "/"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


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
            return {"error": f"HTTP {exc.code}", "error_description": "non-json"}


def download_probe(url: str) -> dict:
    if not url:
        return {"ok": False, "error": "no_url"}
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            chunk = resp.read(512)
            rest_len = 0
            while True:
                more = resp.read(64 * 1024)
                if not more:
                    break
                rest_len += len(more)
            total = len(chunk) + rest_len
            ctype = (resp.headers.get("Content-Type") or "").lower()
            is_pdf = chunk.startswith(b"%PDF")
            is_html = chunk.lstrip().startswith(b"<") or "text/html" in ctype
            return {
                "ok": bool(is_pdf and total > 100),
                "http": resp.status,
                "content_type": ctype,
                "bytes": total,
                "is_pdf": is_pdf,
                "is_html": is_html,
                "disposition": resp.headers.get("Content-Disposition"),
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http": exc.code, "error": str(exc.reason)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}


def main() -> None:
    env = load_env(Path("/tmp/.env"))
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    if not raw:
        print(json.dumps({"error": "MISSING_BITRIX_ADMIN_WEBHOOK_URL"}))
        return
    base = webhook_base(raw)
    current = call(base, "user.current", {})
    user = current.get("result") if isinstance(current.get("result"), dict) else {}
    name = " ".join(p for p in [user.get("NAME"), user.get("LAST_NAME")] if p).strip()
    admin = call(base, "user.admin", {})
    disk = call(base, "disk.file.get", {"id": 81568})
    result = disk.get("result") if isinstance(disk.get("result"), dict) else {}
    download = {}
    if result and not disk.get("error"):
        url = result.get("DOWNLOAD_URL") or result.get("downloadUrl")
        download = download_probe(url)
    report = {
        "webhook_user_name": name or None,
        "webhook_user_id": user.get("ID"),
        "user.current_error": current.get("error"),
        "user.admin": admin.get("result"),
        "user.admin_error": admin.get("error"),
        "disk.file.get_error": disk.get("error"),
        "disk.file.get_error_description": disk.get("error_description"),
        "filename": result.get("NAME") or result.get("name"),
        "size": result.get("SIZE") or result.get("size"),
        "binary_ok": download.get("ok") if download else False,
        "download": {k: v for k, v in download.items() if k != "head"} if download else None,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
