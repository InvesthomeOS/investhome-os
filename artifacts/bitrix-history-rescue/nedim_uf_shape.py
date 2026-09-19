import json
import urllib.parse
import urllib.request

from investhome_api.services.crm.nedim_purchase_card_apply import DEAL_UF_FILES, _webhook_base

base = _webhook_base()
url = urllib.parse.urljoin(base, "crm.deal.get.json")
data = urllib.parse.urlencode({"id": "198"}).encode()
req = urllib.request.Request(url, data=data, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    body = json.loads(resp.read().decode())
deal = body.get("result") or {}
wanted = set(DEAL_UF_FILES["198"])
report = []
for key, value in deal.items():
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, (str, int, float, type(None))) else str(value)
    if any(fid in text for fid in wanted) or str(key).startswith("UF_"):
        sample_keys = None
        if isinstance(value, list) and value and isinstance(value[0], dict):
            sample_keys = sorted(value[0].keys())
        elif isinstance(value, dict):
            sample_keys = sorted(value.keys())
        report.append(
            {
                "field": key,
                "kind": type(value).__name__,
                "len": len(value) if hasattr(value, "__len__") and not isinstance(value, str) else None,
                "sample_keys": sample_keys,
                "wanted_hit": [fid for fid in wanted if fid in text],
            }
        )
print(
    json.dumps(
        {"error": body.get("error"), "fields": report, "top_keys": list(deal.keys())[:40]},
        ensure_ascii=False,
        indent=2,
    )
)
