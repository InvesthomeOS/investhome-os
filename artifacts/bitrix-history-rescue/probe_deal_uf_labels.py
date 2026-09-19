"""Dump raw UF deal field labels from crm.deal.fields."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    values = {}
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


def call(base: str, method: str, payload=None) -> dict:
    url = urllib.parse.urljoin(base, method + ".json")
    data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def label_of(spec: dict) -> str:
    for key in ("formLabel", "listLabel", "filterLabel", "title", "editFormLabel"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip() and not val.startswith("UF_"):
            return val.strip()
        if isinstance(val, dict):
            for lang in ("tr", "en", "br"):
                if val.get(lang):
                    return str(val[lang]).strip()
            for item in val.values():
                if item:
                    return str(item).strip()
    return str(spec.get("title") or "")


def main() -> None:
    base = webhook_base(load_env(Path("/tmp/.env")).get("BITRIX_ADMIN_WEBHOOK_URL") or "")
    fields = (call(base, "crm.deal.fields", {}).get("result") or {})
    uf = []
    for fid, spec in fields.items():
        if not str(fid).startswith("UF_") or not isinstance(spec, dict):
            continue
        uf.append(
            {
                "id": fid,
                "label": label_of(spec),
                "type": spec.get("type"),
                "keys": sorted(spec.keys()),
                "formLabel": spec.get("formLabel"),
                "listLabel": spec.get("listLabel"),
                "editFormLabel": spec.get("editFormLabel"),
            }
        )
    Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_DEAL_UF_FIELDS.json").write_text(
        json.dumps(uf, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("UF_COUNT", len(uf))
    for row in uf:
        if row["label"] and row["label"] != row["id"]:
            print(row["id"], "|", row["type"], "|", row["label"])
    if not any(r["label"] and r["label"] != r["id"] for r in uf):
        print("NO_HUMAN_LABELS")
        print(json.dumps(uf[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
