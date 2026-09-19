"""Read-only: dump Bitrix deal field labels and a sample deal. Never prints webhook URLs."""

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
            return {"error": f"HTTP {exc.code}"}


def main() -> None:
    base = webhook_base(load_env(Path("/tmp/.env")).get("BITRIX_ADMIN_WEBHOOK_URL") or "")
    fields = call(base, "crm.deal.fields", {})
    result = fields.get("result") or {}
    rows = []
    for fid, spec in result.items() if isinstance(result, dict) else []:
        if not isinstance(spec, dict):
            continue
        title = spec.get("title") or spec.get("listLabel") or spec.get("formLabel") or ""
        rows.append(
            {
                "id": fid,
                "title": title,
                "type": spec.get("type"),
                "isRequired": spec.get("isRequired"),
                "isReadOnly": spec.get("isReadOnly"),
            }
        )
    rows.sort(key=lambda r: str(r["id"]))
    interesting = [
        r
        for r in rows
        if re.search(
            r"sat[iı][sş]|yat[iı]r[iı]m|öde|ode|tutar|bedel|deposit|kapora|pe[sş]inat|"
            r"kalan|toplam|closing|unit|daire|proje|project|opportunity|amount|paid|"
            r"payment|currency|stage|pipeline|contact|lead|title|date|anla[sş]",
            f"{r['id']} {r['title']}",
            re.I,
        )
    ]
    sample = call(base, "crm.deal.list", {"select[]": ["ID", "TITLE", "CONTACT_ID", "LEAD_ID", "OPPORTUNITY", "CURRENCY_ID", "STAGE_ID"], "start": 0})
    deals = sample.get("result") or []
    print(json.dumps({"field_count": len(rows), "interesting": interesting, "sample_deals": deals[:5], "deal_list_error": sample.get("error")}, ensure_ascii=False, indent=2))
    Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports").mkdir(parents=True, exist_ok=True)
    Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_DEAL_FIELDS.json").write_text(
        json.dumps({"fields": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
