from __future__ import annotations

import json
import urllib.request
from collections import Counter
from http.cookiejar import CookieJar

API = "http://127.0.0.1:8000"
CID = "811c6aed-5f58-4c89-a9b1-0eebed64b9cf"
ALIAS = "ee093070-b3a4-4fb3-b3ca-3aa92379a187"

jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
req = urllib.request.Request(
    f"{API}/auth/login",
    data=json.dumps({"email": "superadmin@investhome.demo", "password": "Investhome2026!"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
opener.open(req).read()


def get(path: str) -> dict:
    with opener.open(f"{API}{path}") as response:
        return json.loads(response.read().decode())


def agr(contact: dict) -> str:
    return "; ".join(
        f"{item['project_group']}:{item.get('unit_number')}:{item.get('amount_and_currency_amount')}"
        for item in contact.get("crm_agreements") or []
    )


def assign(items: list[dict]) -> dict[str, int]:
    return dict(Counter((item.get("project_assignment") or "none") for item in items))


uniloft = get(f"/crm/contacts/{CID}?project_context=uniloft")
ontario = get(f"/crm/contacts/{CID}?project_context=2319_ontario")
all_view = get(f"/crm/contacts/{CID}?project_context=all")
alias = get(f"/crm/contacts/{ALIAS}?project_context=2319_ontario")
timeline_u = get(f"/crm/contacts/{CID}/timeline?project_context=uniloft")
timeline_o = get(f"/crm/contacts/{CID}/timeline?project_context=2319_ontario")
timeline_a = get(f"/crm/contacts/{CID}/timeline?project_context=all")
search = get("/crm/contacts?search=Nedim%20Kondu&include_archived=true")

print("UNILOFT", uniloft["id"], uniloft["display_name"], uniloft.get("amount_and_currency_amount"), uniloft.get("amount_and_currency_currency"), agr(uniloft))
print("UNILOFT_PILOT", json.dumps(uniloft.get("project_card_pilot"), default=str))
print("ONTARIO", ontario.get("amount_and_currency_amount"), agr(ontario))
print("ALL", all_view.get("amount_and_currency_amount"), agr(all_view))
print("ALIAS", alias["id"], alias["display_name"], agr(alias))
print("TIMELINE", len(timeline_u["items"]), len(timeline_o["items"]), len(timeline_a["items"]))
print("ASSIGN_U", assign(timeline_u["items"]))
print("ASSIGN_O", assign(timeline_o["items"]))
print("ASSIGN_A", assign(timeline_a["items"]))
print("SEARCH", [(item["id"][:8], item["status"], item["display_name"]) for item in search.get("items") or []])
ontario_titles = [item.get("title") for item in timeline_o["items"] if "uniloft" in f"{item.get('title')} {item.get('summary')}".lower() and item.get("project_assignment") != "multiple"]
print("ONTARIO_HAS_UNILOFT_TITLES", ontario_titles[:5], "count", len(ontario_titles))
uniloft_titles = [item.get("title") for item in timeline_u["items"] if "ontario" in f"{item.get('title')} {item.get('summary')}".lower() and item.get("project_assignment") != "multiple"]
print("UNILOFT_HAS_ONTARIO_TITLES", uniloft_titles[:5], "count", len(uniloft_titles))
