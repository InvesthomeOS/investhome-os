import json
from pathlib import Path

p = Path(__file__).with_name("_nedim_izzet_fields.tmp.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("calls", d.get("calls"))


def show_entity(name, row, reqs):
    print("\n====", name, "====")
    if not isinstance(row, dict):
        print(row)
        return
    keep = [
        "id",
        "name",
        "phones",
        "emails",
        "company_id",
        "post",
        "source_id",
        "source_name",
        "assigned_id",
        "assigned_name",
        "comments",
        "address",
        "address_city",
        "address_postal",
        "address_country",
    ]
    for key in keep:
        value = row.get(key)
        if value not in (None, "", [], {}):
            print(f"  {key}: {value}")
    pop = row.get("populated") or []
    print("  populated_count", len(pop))
    skip = set(keep) | {
        "ID",
        "NAME",
        "LAST_NAME",
        "SECOND_NAME",
        "PHONE",
        "EMAIL",
        "ASSIGNED_BY_ID",
        "SOURCE_ID",
        "COMPANY_ID",
        "POST",
        "COMMENTS",
        "ADDRESS",
        "ADDRESS_CITY",
        "ADDRESS_POSTAL_CODE",
        "ADDRESS_COUNTRY",
    }
    for item in pop:
        if item.get("key") in skip:
            continue
        text = json.dumps(item.get("value"), ensure_ascii=False)
        print(f"  FIELD {item.get('label')} [{item.get('key')}] = {text[:240]}")
    print("  requisites", json.dumps(reqs, ensure_ascii=False)[:800] if reqs else "[]")


show_entity("contact_588", d.get("contact_588"), d.get("contact_588_requisites"))
show_entity("contact_1160", d.get("contact_1160"), d.get("contact_1160_requisites"))
show_entity("lead_12512", d.get("lead_12512"), d.get("lead_12512_requisites"))

for deal in ("deal_198", "deal_656", "deal_720"):
    row = d.get(deal) or {}
    print("\n====", deal, "====")
    for key in (
        "title",
        "opportunity",
        "currency",
        "stage_id",
        "stage_name",
        "begin",
        "close",
        "assigned_id",
        "assigned_name",
        "comments",
        "contact_id",
        "company_id",
        "company",
        "activity_count",
        "comment_count",
        "file_ids",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            if isinstance(value, (str, int, float)):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {json.dumps(value, ensure_ascii=False)[:400]}")
    print("  participants", json.dumps(row.get("participants"), ensure_ascii=False)[:400])
    print("  PAYMENT:")
    for item in row.get("payment_fields") or []:
        text = json.dumps(item.get("value"), ensure_ascii=False)
        print(f"    {item.get('label')} [{item.get('key')}] = {text[:300]}")
    print("  LLC:")
    for item in row.get("llc_fields") or []:
        text = json.dumps(item.get("value"), ensure_ascii=False)
        print(f"    {item.get('label')} [{item.get('key')}] = {text[:300]}")
    print("  requisites", json.dumps(row.get("requisites"), ensure_ascii=False)[:500] if row.get("requisites") else "[]")
    print("  OTHER POPULATED:")
    skip = {
        "ID",
        "TITLE",
        "OPPORTUNITY",
        "CURRENCY_ID",
        "STAGE_ID",
        "BEGINDATE",
        "CLOSEDATE",
        "ASSIGNED_BY_ID",
        "COMMENTS",
        "CONTACT_ID",
        "COMPANY_ID",
        "TYPE_ID",
        "CATEGORY_ID",
        "DATE_CREATE",
        "DATE_MODIFY",
        "CREATED_BY_ID",
        "MODIFY_BY_ID",
        "OPENED",
        "CLOSED",
        "IS_NEW",
        "IS_RECURRING",
        "IS_RETURN_CUSTOMER",
        "IS_REPEATED_APPROACH",
        "PROBABILITY",
        "TAX_VALUE",
        "ADDITIONAL_INFO",
        "ORIGINATOR_ID",
        "ORIGIN_ID",
        "UTM_SOURCE",
        "UTM_MEDIUM",
        "UTM_CAMPAIGN",
        "UTM_CONTENT",
        "UTM_TERM",
        "LOCATION_ID",
        "MOVED_BY_ID",
        "MOVED_TIME",
        "LAST_ACTIVITY_BY",
        "LAST_ACTIVITY_TIME",
        "SOURCE_ID",
        "SOURCE_DESCRIPTION",
    }
    for item in row.get("populated_fields") or []:
        if item.get("key") in skip:
            continue
        text = json.dumps(item.get("value"), ensure_ascii=False)
        print(f"    {item.get('label')} [{item.get('key')}] = {text[:280]}")
