import json
import urllib.error
import urllib.parse
import urllib.request

from investhome_api.services.crm.nedim_purchase_card_apply import _webhook_base

base = _webhook_base()
url = urllib.parse.urljoin(base, "crm.item.get.json")
payload = urllib.parse.urlencode({"entityTypeId": 2, "id": 198}).encode()
req = urllib.request.Request(url, data=payload, method="POST")
try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read().decode())
except urllib.error.HTTPError as exc:
    print(json.dumps({"http": exc.code, "method": "crm.item.get"}))
    raise SystemExit(0)
item = (body.get("result") or {}).get("item") if isinstance(body.get("result"), dict) else None
keys = []
if isinstance(item, dict):
    for key, value in item.items():
        if isinstance(value, dict) and (value.get("urlMachine") or value.get("url")):
            keys.append({"field": key, "has_urlMachine": bool(value.get("urlMachine")), "has_url": bool(value.get("url")), "id": str(value.get("id") or "")})
        elif isinstance(value, list) and value and isinstance(value[0], dict) and (value[0].get("urlMachine") or value[0].get("url")):
            keys.append({"field": key, "list": True, "count": len(value), "ids": [str(v.get("id") or "") for v in value if isinstance(v, dict)][:8]})
print(json.dumps({"error": body.get("error"), "file_fields": keys[:20]}, ensure_ascii=False, indent=2))
