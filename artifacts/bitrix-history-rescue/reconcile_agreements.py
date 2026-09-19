"""Final Bitrix agreement reconciliation. Bitrix is read-only. OS writes only blank-field ADDs."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact

OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION")
ENV_PATH = Path("/tmp/.env")
NON_DIGIT = re.compile(r"\D+")
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
PROJECT_TOKENS = {
    "uniloft": ["uniloft"],
    "1812_h_pl": ["1812"],
    "2319_ontario": ["ontario", "2319"],
    "the_temple": ["temple"],
    "reit": ["reit"],
    "1307_k_st": ["1307", "k st", "k.st", "k street"],
    "1313_penn": ["1313", "penn"],
}
PAYMENT_ROLES = {
    "ön ödeme tutarı": "down_payment",
    "on odeme tutari": "down_payment",
    "peşinat": "deposit",
    "pesinat": "deposit",
    "teslimde ödeme tutarı": "delivery_payment",
    "teslimde odeme tutari": "delivery_payment",
    "yatırım tutarı (r)": "investment_amount",
    "yatirim tutari (r)": "investment_amount",
    "yatırılacak para $ (r)": "investment_amount_money",
    "opportunity": "total_deal_value",
    "total": "total_deal_value",
    "ödeme tarihleri": "payment_dates",
    "odeme tarihleri": "payment_dates",
    "daire no": "unit_number",
    "alınan ev proje adresi": "project_address",
    "alinan ev proje adresi": "project_address",
    "ödeme şekli": "payment_method",
    "odeme sekli": "payment_method",
    "start date": "begin_date",
    "end date": "end_date",
    "ödenen tutar": "amount_paid",
    "odenen tutar": "amount_paid",
    "kalan ödeme": "remaining_balance",
    "kalan odeme": "remaining_balance",
    "kapora": "deposit",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def redact(text: str, webhook: str) -> str:
    return WEBHOOK_RE.sub("[REDACTED_URL]", (text or "").replace(webhook, "[REDACTED]"))


def digits(value: str | None) -> str:
    return NON_DIGIT.sub("", value or "")


def phone_keys(value: str | None) -> set[str]:
    raw = digits(value)
    keys: set[str] = set()
    if len(raw) >= 10:
        keys.add(raw)
        keys.add(raw[-10:])
        if raw.startswith("90") and len(raw) >= 12:
            keys.add(raw[-10:])
    return {k for k in keys if len(k) >= 10}


def phones_of(item: dict) -> list[str]:
    values = []
    field = item.get("PHONE") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        val = row.get("VALUE") if isinstance(row, dict) else str(row or "")
        if digits(val):
            values.append(val)
    return values


def emails_of(item: dict) -> list[str]:
    values = []
    field = item.get("EMAIL") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        val = (row.get("VALUE") if isinstance(row, dict) else str(row or "")).strip().lower()
        if val and "@" in val:
            values.append(val)
    return values


def label_of(spec: dict) -> str:
    for key in ("formLabel", "listLabel", "filterLabel", "title", "editFormLabel"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip() and not val.startswith("UF_"):
            return val.strip()
        if isinstance(val, dict):
            for lang in ("tr", "en"):
                if val.get(lang):
                    return str(val[lang]).strip()
            for item in val.values():
                if item:
                    return str(item).strip()
    return str(spec.get("title") or "")


def fold_label(value: str) -> str:
    table = str.maketrans({"ı": "i", "İ": "i", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c"})
    return re.sub(r"\s+", " ", (value or "").translate(table).casefold()).strip()


def present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [scalar(v) for v in value if present(v)]
        return " | ".join(p for p in parts if p)
    if isinstance(value, dict):
        if "VALUE" in value:
            amount = value.get("VALUE") or value.get("amount") or ""
            curr = value.get("CURRENCY") or value.get("currency") or ""
            return f"{amount} {curr}".strip()
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value).strip()


def normalize_amount(value: str) -> str:
    text = (value or "").strip().replace(" ", "").replace(",", "")
    text = re.sub(r"[^\d.\-]", "", text)
    if text.endswith(".00000000"):
        text = text[:-9]
    if text.endswith(".00"):
        text = text[:-3]
    return text


def amounts_equal(a: str, b: str) -> bool:
    na, nb = normalize_amount(a), normalize_amount(b)
    if na and nb:
        try:
            return abs(float(na) - float(nb)) < 0.01
        except ValueError:
            return na == nb
    return (a or "").strip().casefold() == (b or "").strip().casefold()


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.min_interval = 0.3
        self._last = 0.0
        self.call_count = 0

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def call(self, method: str, payload: dict | None = None) -> dict:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last = None
        for attempt in range(5):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "error_description": redact(raw, self.base)[:300]}
            except Exception as exc:  # noqa: BLE001
                last = redact(str(exc), self.base)
                time.sleep(min(15, 2 ** attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            parsed["error_description"] = redact(str(parsed.get("error_description") or ""), self.base)
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                time.sleep(min(25, 2 ** (attempt + 1)))
                last = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last or "unknown"}

    def list_all(self, method: str, payload: dict) -> list[dict]:
        items: list[dict] = []
        start = 0
        seen = set()
        while start not in seen:
            seen.add(start)
            body = dict(payload)
            body["start"] = start
            parsed = self.call(method, body)
            if parsed.get("error"):
                break
            chunk = parsed.get("result") or []
            if isinstance(chunk, dict):
                chunk = chunk.get("items") or []
            items.extend(chunk)
            nxt = parsed.get("next")
            if nxt is None or not chunk:
                break
            start = int(nxt)
        return items


def load_people(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            select c.id::text as cid, c.display_name, c.first_name, c.last_name,
                   c.primary_email, c.secondary_emails, c.primary_phone, c.secondary_phones,
                   c.whatsapp, c.organization_name, c.job_title,
                   c.address_line1, c.city, c.state_province, c.postal_code, c.country,
                   c.metadata_json as contact_meta,
                   a.id::text as agreement_id, a.project_group, a.unit_number,
                   a.investment_amount, a.agreement_date::text, a.source_external_id,
                   a.status, a.metadata_json as agreement_meta
            from crm_agreements a
            join crm_contacts c on c.id = a.contact_id
            order by c.display_name, a.project_group
            """
        )
    ).mappings().all()
    people: dict[str, dict] = {}
    for row in rows:
        rec = people.setdefault(
            row["cid"],
            {
                "cid": row["cid"],
                "name": row["display_name"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "email": (row["primary_email"] or "").strip().lower(),
                "emails": set(),
                "phones": [],
                "whatsapp": row["whatsapp"],
                "organization_name": row["organization_name"],
                "job_title": row["job_title"],
                "address_line1": row["address_line1"],
                "city": row["city"],
                "country": row["country"],
                "agreements": [],
                "entities": [],
                "deals": [],
                "status": "unmatched",
            },
        )
        if row["primary_email"]:
            rec["emails"].add(row["primary_email"].strip().lower())
        se = row["secondary_emails"] or []
        if isinstance(se, list):
            rec["emails"].update(str(x).strip().lower() for x in se if x)
        for phone in [row["primary_phone"], row["whatsapp"], *(row["secondary_phones"] or [] if isinstance(row["secondary_phones"], list) else [])]:
            if phone:
                rec["phones"].append(str(phone))
        rec["agreements"].append(
            {
                "id": row["agreement_id"],
                "project_group": row["project_group"],
                "unit_number": row["unit_number"] or "",
                "investment_amount": row["investment_amount"] or "",
                "agreement_date": row["agreement_date"] or "",
                "source_external_id": row["source_external_id"] or "",
                "status": row["status"],
                "metadata": row["agreement_meta"] if isinstance(row["agreement_meta"], dict) else {},
            }
        )
    for rec in people.values():
        rec["emails"] = sorted(rec["emails"])
        rec["phone_keys"] = set()
        for phone in rec["phones"]:
            rec["phone_keys"] |= phone_keys(phone)
    return list(people.values())


def add_entity(person: dict, etype: str, eid: str, how: str, record: dict | None = None) -> None:
    key = (etype, str(eid))
    if key in {(e["type"], e["id"]) for e in person["entities"]}:
        return
    person["entities"].append({"type": etype, "id": str(eid), "how": how, "record": record or {}})


def match_people(client: BitrixClient, people: list[dict]) -> None:
    select = ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "TITLE", "PHONE", "EMAIL", "COMPANY_TITLE", "POST", "ADDRESS", "ASSIGNED_BY_ID"]
    for person in people:
        found = []
        seen_phone = set()
        for phone in person["phones"]:
            variants = [phone]
            d = digits(phone)
            if d:
                variants.extend([d, "+" + d])
                if len(d) >= 10:
                    variants.append(d[-10:])
            for variant in variants:
                if not variant or variant in seen_phone:
                    continue
                seen_phone.add(variant)
                for method, etype in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
                    body = client.call(method, {"filter[PHONE]": variant, "select[]": select, "start": 0})
                    for item in body.get("result") or []:
                        rec_keys: set[str] = set()
                        for value in phones_of(item):
                            rec_keys |= phone_keys(value)
                        if person["phone_keys"] and rec_keys and not (person["phone_keys"] & rec_keys):
                            continue
                        found.append((etype, str(item.get("ID")), "phone", item))
                if found:
                    break
            if found:
                break
        if not found:
            for email in person["emails"]:
                for method, etype in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
                    body = client.call(method, {"filter[EMAIL]": email, "select[]": select, "start": 0})
                    for item in body.get("result") or []:
                        if email not in set(emails_of(item)):
                            continue
                        found.append((etype, str(item.get("ID")), "email", item))
        for etype, eid, how, item in found:
            add_entity(person, etype, eid, how, item)
        person["status"] = "matched" if person["entities"] else "unmatched"


def deal_role(field_id: str, label: str) -> str | None:
    folded = fold_label(label)
    if field_id == "OPPORTUNITY":
        return "total_deal_value"
    return PAYMENT_ROLES.get(folded)


def extract_deal_values(deal: dict, field_meta: dict[str, dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for fid, value in deal.items():
        if not present(value):
            continue
        spec = field_meta.get(fid) or {}
        label = spec.get("label") or fid
        role = deal_role(str(fid), label)
        rec = {
            "bitrix_field_id": fid,
            "bitrix_field_label": label,
            "value": scalar(value),
            "type": spec.get("type"),
            "role": role,
        }
        if role:
            out.setdefault(role, rec)
        out.setdefault("_all", {"values": []})
    return out


def score_deal(deal: dict, agreement: dict, field_meta: dict) -> int:
    score = 0
    title = str(deal.get("TITLE") or "").casefold()
    unit = (agreement.get("unit_number") or "").strip()
    if unit and (unit.casefold() in title or unit in scalar(deal.get("UF_CRM_1690887880212"))):
        score += 50
    tokens = PROJECT_TOKENS.get(agreement["project_group"], [])
    blob = " ".join(
        [
            title,
            scalar(deal.get("UF_CRM_1690533085532")).casefold(),
            scalar(deal.get("COMMENTS")).casefold(),
        ]
    )
    if any(tok in blob for tok in tokens):
        score += 30
    return score


def pair_deals(person: dict, field_meta: dict) -> None:
    deals = person["deals"]
    agreements = person["agreements"]
    person["pairs"] = []
    used_deals: set[str] = set()
    if len(deals) == 1 and len(agreements) == 1:
        person["pairs"].append({"agreement": agreements[0], "deal": deals[0], "how": "single"})
        used_deals.add(str(deals[0].get("ID")))
        return
    for agreement in agreements:
        ranked = []
        for deal in deals:
            did = str(deal.get("ID"))
            if did in used_deals:
                continue
            ranked.append((score_deal(deal, agreement, field_meta), did, deal))
        ranked.sort(key=lambda x: -x[0])
        if ranked and ranked[0][0] >= 30 and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
            person["pairs"].append({"agreement": agreement, "deal": ranked[0][2], "how": "unit_or_project"})
            used_deals.add(ranked[0][1])
        elif ranked and ranked[0][0] >= 30:
            person["status"] = "REVIEW_REQUIRED"
            person.setdefault("ambiguous_reason", []).append(f"multiple deals for {agreement['project_group']} {agreement['unit_number']}")
        else:
            person["pairs"].append({"agreement": agreement, "deal": None, "how": "no_deal"})
    leftover = [d for d in deals if str(d.get("ID")) not in used_deals]
    if leftover and person["status"] != "unmatched":
        if len(agreements) == 1 and len(deals) > 1 and not person["pairs"]:
            person["status"] = "REVIEW_REQUIRED"
        person["unpaired_deals"] = [{"id": d.get("ID"), "title": d.get("TITLE")} for d in leftover]


def compare_value(os_value: str, bx_value: str, field: str) -> str:
    if present(os_value) and present(bx_value):
        if field in {"investment_amount", "down_payment", "deposit", "total_deal_value"} or "amount" in field:
            return "same" if amounts_equal(os_value, bx_value) else "CONFLICT_REVIEW"
        return "same" if os_value.strip().casefold() == bx_value.strip().casefold() else "CONFLICT_REVIEW"
    if not present(os_value) and present(bx_value):
        return "ADD"
    if present(os_value) and not present(bx_value):
        return "missing_in_bitrix"
    return "both_blank"


def main() -> None:
    progress = OUT / "reports" / "progress.log"
    progress.parent.mkdir(parents=True, exist_ok=True)
    env = load_env(ENV_PATH)
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    if not raw:
        print("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
        return
    client = BitrixClient(webhook_base(raw))
    admin = client.call("user.admin", {})
    if admin.get("result") is not True:
        print("NOT_ADMIN")
        return

    field_body = client.call("crm.deal.fields", {})
    field_meta: dict[str, dict] = {}
    for fid, spec in (field_body.get("result") or {}).items():
        if isinstance(spec, dict):
            field_meta[fid] = {"label": label_of(spec) or fid, "type": spec.get("type")}
    uf_ids = [fid for fid in field_meta if str(fid).startswith("UF_")]
    select = [
        "ID",
        "TITLE",
        "STAGE_ID",
        "CATEGORY_ID",
        "CURRENCY_ID",
        "OPPORTUNITY",
        "CONTACT_ID",
        "LEAD_ID",
        "COMPANY_ID",
        "ASSIGNED_BY_ID",
        "BEGINDATE",
        "CLOSEDATE",
        "DATE_CREATE",
        "COMMENTS",
        "SOURCE_ID",
        *uf_ids,
    ]

    db = SessionLocal()
    try:
        people = load_people(db)
        print(f"{utc_now()} PEOPLE {len(people)} AGREEMENTS {sum(len(p['agreements']) for p in people)}", flush=True)
        match_people(client, people)
        bitrix_to_people: dict[tuple[str, str], set[str]] = defaultdict(set)
        for person in people:
            for ent in person["entities"]:
                bitrix_to_people[(ent["type"], ent["id"])].add(person["cid"])
        for person in people:
            for ent in person["entities"]:
                owners = bitrix_to_people[(ent["type"], ent["id"])]
                if len(owners) > 1:
                    person["status"] = "REVIEW_REQUIRED"
                    person.setdefault("ambiguous_reason", []).append("shared_bitrix_entity:" + ent["type"] + ":" + ent["id"])

        for person in people:
            deals = []
            seen = set()
            for ent in person["entities"]:
                filt = {"CONTACT_ID": ent["id"]} if ent["type"] == "contact" else {"LEAD_ID": ent["id"]}
                payload = {f"filter[{k}]": v for k, v in filt.items()}
                for key in select:
                    payload.setdefault("select[]", [])
                # rebuild payload properly
                payload = {f"filter[{k}]": v for k, v in filt.items()}
                payload["select"] = select
                # bitrix list uses select[]
                encoded = {f"filter[{k}]": v for k, v in filt.items()}
                for item in select:
                    encoded.setdefault("select[]", [])
                # manual
                encoded = {}
                for k, v in filt.items():
                    encoded[f"filter[{k}]"] = v
                for item in select:
                    encoded.setdefault("select[]", [])
                    if not isinstance(encoded["select[]"], list):
                        encoded["select[]"] = [encoded["select[]"]]
                    encoded["select[]"].append(item)
                chunk = client.list_all("crm.deal.list", encoded)
                for deal in chunk:
                    did = str(deal.get("ID"))
                    if did in seen:
                        continue
                    seen.add(did)
                    deals.append(deal)
            person["deals"] = deals
            if person["status"] == "unmatched":
                continue
            if not deals:
                person["status"] = person["status"]
            pair_deals(person, field_meta)
            print(f"{utc_now()} MATCH {person['name']} entities={len(person['entities'])} deals={len(deals)} status={person['status']}", flush=True)

        csv_rows = []
        proposed = []
        contact_updates = []
        agreement_updates = []
        for person in people:
            # contact comparison
            bx_phones, bx_emails = [], []
            bx_company = bx_post = bx_address = ""
            for ent in person["entities"]:
                rec = ent.get("record") or {}
                bx_phones.extend(phones_of(rec))
                bx_emails.extend(emails_of(rec))
                bx_company = bx_company or scalar(rec.get("COMPANY_TITLE"))
                bx_post = bx_post or scalar(rec.get("POST"))
                bx_address = bx_address or scalar(rec.get("ADDRESS"))
            extra_phones = [p for p in bx_phones if phone_keys(p) and not (phone_keys(p) & person["phone_keys"])]
            extra_emails = [e for e in bx_emails if e and e not in set(person["emails"])]
            if extra_phones:
                csv_rows.append(row_out(person, None, None, "contact.secondary_phones", "", " | ".join(extra_phones), "ADD", "", "", "add extra Bitrix phones"))
                contact_updates.append({"cid": person["cid"], "field": "secondary_phones", "value": extra_phones, "action": "ADD"})
            if extra_emails:
                csv_rows.append(row_out(person, None, None, "contact.secondary_emails", "", " | ".join(extra_emails), "ADD", "", "", "add extra Bitrix emails"))
                contact_updates.append({"cid": person["cid"], "field": "secondary_emails", "value": extra_emails, "action": "ADD"})
            if not present(person.get("organization_name")) and present(bx_company):
                csv_rows.append(row_out(person, None, None, "contact.organization_name", "", bx_company, "ADD", "", "", "fill blank company"))
                contact_updates.append({"cid": person["cid"], "field": "organization_name", "value": bx_company, "action": "ADD"})
            elif present(person.get("organization_name")) and present(bx_company) and person["organization_name"].strip().casefold() != bx_company.casefold():
                csv_rows.append(row_out(person, None, None, "contact.organization_name", person["organization_name"], bx_company, "CONFLICT_REVIEW", "", "", "do not overwrite"))
            if not present(person.get("job_title")) and present(bx_post):
                csv_rows.append(row_out(person, None, None, "contact.job_title", "", bx_post, "ADD", "", "", "fill blank position"))
                contact_updates.append({"cid": person["cid"], "field": "job_title", "value": bx_post, "action": "ADD"})
            if not present(person.get("address_line1")) and present(bx_address):
                csv_rows.append(row_out(person, None, None, "contact.address_line1", "", bx_address, "ADD", "", "", "fill blank address"))
                contact_updates.append({"cid": person["cid"], "field": "address_line1", "value": bx_address[:255], "action": "ADD"})

            for pair in person.get("pairs") or [{"agreement": a, "deal": None} for a in person["agreements"]]:
                agreement = pair["agreement"]
                deal = pair.get("deal")
                if not deal:
                    csv_rows.append(row_out(person, agreement, None, "deal", "", "", "missing", "", "", "no deterministic Bitrix deal"))
                    continue
                roles = {}
                for fid, value in deal.items():
                    if not present(value) or fid in {"ID"}:
                        continue
                    spec = field_meta.get(fid) or {}
                    label = spec.get("label") or fid
                    role = deal_role(str(fid), label)
                    if role:
                        roles[role] = {
                            "value": scalar(value),
                            "field_id": fid,
                            "label": label,
                        }
                comparisons = [
                    ("agreement.unit_number", agreement.get("unit_number") or "", (roles.get("unit_number") or {}).get("value") or "", roles.get("unit_number")),
                    ("agreement.investment_amount", agreement.get("investment_amount") or "", (roles.get("investment_amount") or roles.get("investment_amount_money") or {}).get("value") or "", roles.get("investment_amount") or roles.get("investment_amount_money")),
                    ("agreement.agreement_date", agreement.get("agreement_date") or "", (roles.get("begin_date") or {}).get("value") or "", roles.get("begin_date")),
                    ("payment.total_deal_value", "", (roles.get("total_deal_value") or {}).get("value") or "", roles.get("total_deal_value")),
                    ("payment.down_payment", "", (roles.get("down_payment") or {}).get("value") or "", roles.get("down_payment")),
                    ("payment.deposit", "", (roles.get("deposit") or {}).get("value") or "", roles.get("deposit")),
                    ("payment.delivery_payment", "", (roles.get("delivery_payment") or {}).get("value") or "", roles.get("delivery_payment")),
                    ("payment.amount_paid", "", (roles.get("amount_paid") or {}).get("value") or "", roles.get("amount_paid")),
                    ("payment.remaining_balance", "", (roles.get("remaining_balance") or {}).get("value") or "", roles.get("remaining_balance")),
                    ("payment.payment_dates", "", (roles.get("payment_dates") or {}).get("value") or "", roles.get("payment_dates")),
                    ("payment.currency", "", scalar(deal.get("CURRENCY_ID")), {"field_id": "CURRENCY_ID", "label": "Currency", "value": scalar(deal.get("CURRENCY_ID"))} if deal.get("CURRENCY_ID") else None),
                ]
                payment_snapshot = {
                    "source": "bitrix",
                    "bitrix_entity_type": "deal",
                    "bitrix_deal_id": str(deal.get("ID")),
                    "bitrix_deal_title": deal.get("TITLE"),
                    "retrieved_at": utc_now(),
                    "currency": scalar(deal.get("CURRENCY_ID")),
                    "stage_id": deal.get("STAGE_ID"),
                    "total_deal_value": (roles.get("total_deal_value") or {}).get("value"),
                    "amount_paid": (roles.get("amount_paid") or {}).get("value"),
                    "deposit": (roles.get("deposit") or {}).get("value"),
                    "down_payment": (roles.get("down_payment") or {}).get("value"),
                    "delivery_payment": (roles.get("delivery_payment") or {}).get("value"),
                    "remaining_balance": (roles.get("remaining_balance") or {}).get("value"),
                    "payment_dates": (roles.get("payment_dates") or {}).get("value"),
                    "fields": [],
                }
                for role_name, rec in roles.items():
                    payment_snapshot["fields"].append(
                        {
                            "role": role_name,
                            "bitrix_field_id": rec["field_id"],
                            "bitrix_field_label": rec["label"],
                            "value": rec["value"],
                        }
                    )
                meta_add = True
                for field, os_val, bx_val, meta in comparisons:
                    status = compare_value(os_val, bx_val, field)
                    if field.startswith("payment.") and not os_val and bx_val:
                        status = "ADD"
                    action = {
                        "ADD": "add blank OS field / metadata from Bitrix",
                        "same": "no action",
                        "CONFLICT_REVIEW": "do not overwrite",
                        "missing_in_bitrix": "keep OS value",
                        "both_blank": "no action",
                    }.get(status, status)
                    csv_rows.append(
                        row_out(
                            person,
                            agreement,
                            deal,
                            field,
                            os_val,
                            bx_val,
                            status,
                            (meta or {}).get("field_id") or "",
                            (meta or {}).get("label") or "",
                            action,
                        )
                    )
                    if status == "ADD" and field == "agreement.unit_number":
                        agreement_updates.append({"id": agreement["id"], "field": "unit_number", "value": bx_val[:80], "deal": deal, "meta": meta})
                    if status == "ADD" and field == "agreement.investment_amount":
                        agreement_updates.append({"id": agreement["id"], "field": "investment_amount", "value": bx_val[:80], "deal": deal, "meta": meta})
                    if status == "ADD" and field == "agreement.agreement_date":
                        agreement_updates.append({"id": agreement["id"], "field": "agreement_date", "value": bx_val[:10], "deal": deal, "meta": meta})
                if meta_add:
                    agreement_updates.append({"id": agreement["id"], "field": "metadata_payment", "value": payment_snapshot, "deal": deal, "meta": None})

        reports = OUT / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        fields = [
            "canonical_crm_contact_id",
            "person_name",
            "agreement_id",
            "project_group",
            "unit",
            "bitrix_deal_id",
            "bitrix_deal_title",
            "field",
            "investhome_value",
            "bitrix_value",
            "status",
            "bitrix_field_id",
            "bitrix_field_label",
            "recommended_action",
            "match_status",
        ]
        with (reports / "BITRIX_AGREEMENT_RECONCILIATION.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(csv_rows)

        matched = sum(1 for p in people if p["status"] in {"matched", "REVIEW_REQUIRED"} and p["entities"])
        unmatched = [p["name"] for p in people if not p["entities"]]
        ambiguous = [p["name"] for p in people if p["status"] == "REVIEW_REQUIRED"]
        deals_found = sum(len(p["deals"]) for p in people)
        missing_contact = sum(1 for r in csv_rows if r["field"].startswith("contact.") and r["status"] == "ADD")
        missing_agreement = sum(1 for r in csv_rows if r["field"].startswith("agreement.") and r["status"] == "ADD")
        payment_found = sum(1 for r in csv_rows if r["field"].startswith("payment.") and r["bitrix_value"])
        conflicts = sum(1 for r in csv_rows if r["status"] == "CONFLICT_REVIEW")
        safe = [u for u in agreement_updates + contact_updates]
        summary = {
            "agreement_contacts_checked": len(people),
            "bitrix_people_matched": matched,
            "bitrix_deals_found": deals_found,
            "unmatched_people": unmatched,
            "ambiguous_matches": ambiguous,
            "missing_contact_fields_found": missing_contact,
            "missing_agreement_fields_found": missing_agreement,
            "payment_fields_found": payment_found,
            "conflicts_requiring_review": conflicts,
            "csv_rows": len(csv_rows),
            "safe_update_candidates": len(agreement_updates) + len(contact_updates),
        }
        (reports / "BITRIX_AGREEMENT_RECONCILIATION_DRY_RUN.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("DRY_RUN", json.dumps(summary, ensure_ascii=False), flush=True)

        # Apply safe ADDs only
        applied = 0
        by_agreement: dict[str, list] = defaultdict(list)
        for upd in agreement_updates:
            by_agreement[upd["id"]].append(upd)
        for ag_id, upds in by_agreement.items():
            ag = db.get(CrmAgreement, UUID(ag_id))
            if ag is None:
                continue
            meta = dict(ag.metadata_json or {})
            recon = dict(meta.get("bitrix_reconciliation") or {})
            changed = False
            for upd in upds:
                deal = upd.get("deal") or {}
                prov = {
                    "source": "bitrix",
                    "bitrix_entity_type": "deal",
                    "bitrix_entity_id": str(deal.get("ID") or ""),
                    "bitrix_deal_id": str(deal.get("ID") or ""),
                    "bitrix_field_id": ((upd.get("meta") or {}) or {}).get("field_id"),
                    "bitrix_field_label": ((upd.get("meta") or {}) or {}).get("label"),
                    "retrieved_at": utc_now(),
                }
                if upd["field"] == "unit_number" and not present(ag.unit_number):
                    ag.unit_number = str(upd["value"])[:80]
                    recon["unit_number"] = {**prov, "value": ag.unit_number}
                    changed = True
                elif upd["field"] == "investment_amount" and not present(ag.investment_amount):
                    ag.investment_amount = str(upd["value"])[:80]
                    recon["investment_amount"] = {**prov, "value": ag.investment_amount}
                    changed = True
                elif upd["field"] == "agreement_date" and ag.agreement_date is None:
                    raw_date = str(upd["value"])[:10]
                    try:
                        ag.agreement_date = date.fromisoformat(raw_date)
                        recon["agreement_date"] = {**prov, "value": raw_date}
                        changed = True
                    except ValueError:
                        pass
                elif upd["field"] == "metadata_payment":
                    recon["payment"] = upd["value"]
                    changed = True
            if changed:
                meta["bitrix_reconciliation"] = recon
                ag.metadata_json = meta
                applied += 1
        by_contact: dict[str, list] = defaultdict(list)
        for upd in contact_updates:
            by_contact[upd["cid"]].append(upd)
        for cid, upds in by_contact.items():
            contact = db.get(CrmContact, UUID(cid))
            if contact is None:
                continue
            meta = dict(contact.metadata_json or {})
            recon = dict(meta.get("bitrix_reconciliation") or {})
            changed = False
            for upd in upds:
                if upd["field"] == "organization_name" and not present(contact.organization_name):
                    contact.organization_name = str(upd["value"])[:255]
                    changed = True
                elif upd["field"] == "job_title" and not present(contact.job_title):
                    contact.job_title = str(upd["value"])[:120]
                    changed = True
                elif upd["field"] == "address_line1" and not present(contact.address_line1):
                    contact.address_line1 = str(upd["value"])[:255]
                    changed = True
                elif upd["field"] == "secondary_phones":
                    current = list(contact.secondary_phones or [])
                    for phone in upd["value"]:
                        if phone and phone not in current and phone != contact.primary_phone:
                            current.append(phone)
                    if current != (contact.secondary_phones or []):
                        contact.secondary_phones = current
                        changed = True
                elif upd["field"] == "secondary_emails":
                    current = list(contact.secondary_emails or [])
                    for email in upd["value"]:
                        if email and email not in current and email != (contact.primary_email or "").lower():
                            current.append(email)
                    if current != (contact.secondary_emails or []):
                        contact.secondary_emails = current
                        changed = True
            if changed:
                recon["retrieved_at"] = utc_now()
                recon["source"] = "bitrix"
                meta["bitrix_reconciliation"] = recon
                contact.metadata_json = meta
                applied += 1
        db.commit()

        counts = db.execute(
            text("select (select count(*) from crm_agreements) a, (select count(distinct contact_id) from crm_agreements) c")
        ).one()
        albert = next((p for p in people if "albert" in p["name"].casefold() and "levi" in fold_label(p["name"])), None)
        berk = next((p for p in people if p["name"].casefold().startswith("berk")), None)
        final = {
            **summary,
            "safe_updates_applied": applied,
            "albert_levi": albert_report(albert) if albert else None,
            "berk_cimen": {"name": berk["name"], "status": berk["status"], "deals": len(berk["deals"]), "entities": berk["entities"]} if berk else None,
            "final_agreements": counts[0],
            "final_agreement_contacts": counts[1],
            "backup_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/backups/investhome-pre-agreement-reconciliation-20260917.dump",
            "report_paths": {
                "csv": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_AGREEMENT_RECONCILIATION.csv",
                "summary": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_AGREEMENT_RECONCILIATION_SUMMARY.json",
            },
            "bitrix_calls": client.call_count,
            "generated_at": utc_now(),
        }
        # samples
        samples = {}
        for rec in people:
            pg = rec["agreements"][0]["project_group"] if rec["agreements"] else ""
            samples.setdefault(pg, [])
            if len(samples[pg]) < 8:
                samples[pg].append({"name": rec["name"], "status": rec["status"], "deals": [d.get("TITLE") for d in rec["deals"]], "entities": [e["type"]+":"+e["id"] for e in rec["entities"]]})
        final["samples_by_project"] = samples
        (reports / "BITRIX_AGREEMENT_RECONCILIATION_SUMMARY.json").write_text(
            json.dumps(final, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print("SUMMARY", json.dumps(final, ensure_ascii=False, indent=2, default=str), flush=True)
    finally:
        db.close()


def row_out(person, agreement, deal, field, os_val, bx_val, status, field_id, label, action) -> dict:
    return {
        "canonical_crm_contact_id": person["cid"],
        "person_name": person["name"],
        "agreement_id": (agreement or {}).get("id") or "",
        "project_group": (agreement or {}).get("project_group") or "",
        "unit": (agreement or {}).get("unit_number") or "",
        "bitrix_deal_id": str((deal or {}).get("ID") or ""),
        "bitrix_deal_title": (deal or {}).get("TITLE") or "",
        "field": field,
        "investhome_value": os_val or "",
        "bitrix_value": bx_val or "",
        "status": status,
        "bitrix_field_id": field_id or "",
        "bitrix_field_label": label or "",
        "recommended_action": action,
        "match_status": person.get("status") or "",
    }


def albert_report(person: dict) -> dict:
    return {
        "canonical_crm_contact_id": person["cid"],
        "name": person["name"],
        "status": person["status"],
        "entities": [{"type": e["type"], "id": e["id"], "how": e["how"]} for e in person["entities"]],
        "deals": [{"id": d.get("ID"), "title": d.get("TITLE"), "opportunity": d.get("OPPORTUNITY"), "currency": d.get("CURRENCY_ID")} for d in person["deals"]],
        "agreements": person["agreements"],
        "ambiguous_reason": person.get("ambiguous_reason"),
    }


if __name__ == "__main__":
    main()
