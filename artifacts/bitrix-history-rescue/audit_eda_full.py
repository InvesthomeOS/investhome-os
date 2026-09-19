"""Read-only full audit for Eda Kestellioglu Yurttutan. Does not write."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from investhome_api.db.session import SessionLocal

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
DOCS = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS")
RECOVERY = Path("/export/2026-09-final/BITRIX_MANUAL_RECOVERY/reports/BITRIX_MANUAL_RECOVERY_42.csv")
TARGET_CONTACT = "1128"
TARGET_LEAD = "29102"
TARGET_UUID = "2b2c8330-541d-4100-95ea-fb0c036d4e0d"
NAME_RE = re.compile(r"eda|kestelli|yurttutan", re.I)
FOLD = str.maketrans({"ı": "i", "İ": "i", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c"})


def fold(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").translate(FOLD).casefold()).strip()


def is_eda(name: str | None) -> bool:
    n = fold(name)
    return "eda" in n and ("kestelli" in n or "yurttutan" in n)


def count_files(payload: Any) -> int:
    if isinstance(payload, list):
        return sum(1 for x in payload if isinstance(x, dict) and (x.get("id") or x.get("FILE_ID") or x.get("fileId")))
    if isinstance(payload, dict):
        return len(payload)
    return 0


def csv_rows(path: Path, predicate) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if predicate(row)]


def slim_bitrix(body: dict) -> dict:
    return {
        "error": body.get("error"),
        "error_description": body.get("error_description"),
        "result_type": type(body.get("result")).__name__,
        "len": len(body.get("result")) if isinstance(body.get("result"), list) else None,
    }


def flatten_payload(payload: dict) -> dict:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            for inner_k, inner_v in value.items():
                out[f"{key}[{inner_k}]"] = inner_v
        elif isinstance(value, list):
            out[key] = value
        else:
            out[key] = value
    return out


def bitrix_list(client: BitrixClient, method: str, payload: dict) -> list:
    rows: list = []
    start = 0
    for _ in range(20):
        body = client.call(method, {**flatten_payload(payload), "start": start})
        result = body.get("result")
        chunk = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else None)
        if not isinstance(chunk, list) or not chunk:
            if body.get("error") and not rows:
                return [{"_error": body.get("error"), "_error_description": body.get("error_description")}]
            break
        rows.extend(chunk)
        next_start = (body.get("next") if isinstance(body.get("next"), int) else None)
        if next_start is None:
            break
        start = next_start
    return rows


def main() -> None:
    db = SessionLocal()
    out: dict[str, Any] = {"bitrix_contact_id": TARGET_CONTACT, "target_uuid_hint": TARGET_UUID}

    contacts = db.execute(
        text(
            """
            select id::text, display_name, first_name, last_name, primary_email, primary_phone,
                   status, source, created_at::text, metadata_json
            from crm_contacts
            where display_name ilike '%eda%'
               or display_name ilike '%kestelli%'
               or display_name ilike '%yurttutan%'
               or id::text = :uid
            order by display_name
            """
        ),
        {"uid": TARGET_UUID},
    ).mappings().all()

    contact_rows = []
    for row in contacts:
        meta = row["metadata_json"] if isinstance(row["metadata_json"], dict) else {}
        bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
        contact_rows.append(
            {
                "id": row["id"],
                "display_name": row["display_name"],
                "email": row["primary_email"],
                "phone": row["primary_phone"],
                "status": row["status"],
                "source": row["source"],
                "created_at": row["created_at"],
                "is_eda_target": is_eda(row["display_name"]),
                "external_ids": bitrix.get("external_ids") or [],
                "source_files": bitrix.get("source_files") or [],
                "sources": bitrix.get("sources") or [],
            }
        )
    out["crm_name_hits"] = contact_rows
    eda = [c for c in contact_rows if c["is_eda_target"] or c["id"] == TARGET_UUID]
    duplicates = [c for c in eda]
    canonical = eda[0] if eda else None
    if len(eda) > 1:
        exact = [c for c in eda if fold(c["display_name"]) == fold("Eda Kestellioglu Yurttutan")]
        canonical = exact[0] if exact else eda[0]
    cid = canonical["id"] if canonical else None
    out["canonical_contact"] = canonical
    out["duplicate_contacts"] = [c for c in duplicates if canonical and c["id"] != canonical["id"]]

    phone = (canonical or {}).get("phone") or ""
    email = (canonical or {}).get("email") or ""
    extra = []
    if phone or email:
        extra = db.execute(
            text(
                """
                select id::text, display_name, primary_email, primary_phone, status
                from crm_contacts
                where (:phone <> '' and regexp_replace(coalesce(primary_phone,''), '[^0-9]', '', 'g')
                         like '%' || right(regexp_replace(:phone, '[^0-9]', '', 'g'), 10))
                   or (:email <> '' and lower(coalesce(primary_email,'')) = lower(:email))
                """
            ),
            {"phone": phone or "", "email": email or ""},
        ).mappings().all()
    out["phone_email_hits"] = [dict(r) for r in extra]

    agreements = []
    activities = []
    docs = []
    links = []
    if cid:
        agreements = [dict(r) for r in db.execute(
            text(
                """
                select id::text, project_group, status, unit_number, source, source_external_id,
                       investment_amount::text, agreement_date::text, created_at::text,
                       metadata_json
                from crm_agreements
                where contact_id = cast(:cid as uuid)
                """
            ),
            {"cid": cid},
        ).mappings().all()]
        for ag in agreements:
            meta = ag.get("metadata_json") if isinstance(ag.get("metadata_json"), dict) else {}
            ag["source_file"] = (meta or {}).get("source_file")
            ag["display_name_in_source"] = ((meta or {}).get("source_data") or {}).get("source_fields", {}).get("19:İletişim") if isinstance(meta, dict) else None
            ag.pop("metadata_json", None)
        activities = [dict(r) for r in db.execute(
            text(
                """
                select id::text, activity_type, activity_category, title, status,
                       left(coalesce(description,''), 180) as description,
                       start_date::text, created_at::text, archived_at::text,
                       metadata_json
                from crm_activities
                where entity_type = 'contact' and entity_id = cast(:cid as uuid)
                order by coalesce(start_date, created_at)
                """
            ),
            {"cid": cid},
        ).mappings().all()]
        for act in activities:
            meta = act.get("metadata_json") if isinstance(act.get("metadata_json"), dict) else {}
            hist = meta.get("bitrix_history") if isinstance(meta, dict) else None
            act["has_bitrix_history"] = isinstance(hist, dict)
            act["has_excel_comment"] = isinstance((meta or {}).get("bitrix_historical_comment"), dict) if isinstance(meta, dict) else False
            act["import_key"] = (hist or {}).get("import_key") if isinstance(hist, dict) else None
            act.pop("metadata_json", None)
        links = [dict(r) for r in db.execute(
            text(
                """
                select l.id::text, l.document_id::text, l.entity_type, l.entity_id::text,
                       d.title, d.original_file_name, d.status, d.archived_at::text,
                       d.file_size
                from document_links l
                join documents d on d.id = l.document_id
                where l.entity_id = cast(:cid as uuid)
                """
            ),
            {"cid": cid},
        ).mappings().all()]
        docs = links

    mapped_1128 = db.execute(
        text(
            """
            select id::text, display_name
            from crm_contacts
            where metadata_json::text ilike '%1128%'
            """
        )
    ).mappings().all()
    mapped_29102 = db.execute(
        text(
            """
            select id::text, display_name
            from crm_contacts
            where metadata_json::text ilike '%29102%'
            """
        )
    ).mappings().all()
    out["contacts_mentioning_bitrix_1128"] = [dict(r) for r in mapped_1128]
    out["contacts_mentioning_bitrix_29102"] = [dict(r) for r in mapped_29102]

    activity_logs = []
    if cid:
        activity_logs = [dict(r) for r in db.execute(
            text(
                """
                select id::text, action, description_key, created_at::text
                from activity_logs
                where entity_id = cast(:cid as uuid)
                order by created_at
                limit 50
                """
            ),
            {"cid": cid},
        ).mappings().all()]
    out["activity_logs"] = {"total_capped": len(activity_logs), "rows": activity_logs}
    out["agreements"] = agreements
    out["crm_activities"] = {
        "total": len(activities),
        "by_type": dict(Counter(a["activity_type"] for a in activities)),
        "archived": sum(1 for a in activities if a.get("archived_at")),
        "bitrix_history": sum(1 for a in activities if a.get("has_bitrix_history")),
        "excel_comments": sum(1 for a in activities if a.get("has_excel_comment")),
        "rows": activities,
    }
    out["crm_documents"] = {
        "links_total": len(links),
        "active": sum(1 for d in links if not d.get("archived_at")),
        "archived": sum(1 for d in links if d.get("archived_at")),
        "entity_types": dict(Counter(d["entity_type"] for d in links)),
        "rows": docs,
    }

    entity_keys = []
    if canonical:
        for ext in canonical.get("external_ids") or []:
            text_ext = str(ext)
            if ":" not in text_ext:
                continue
            file_name, source_id = text_ext.rsplit(":", 1)
            if not source_id.strip().isdigit():
                continue
            low = file_name.casefold()
            guessed = "contact" if any(token in low for token in ("contact", "kisi", "kişi")) else "lead"
            entity_keys.append(f"{guessed}:{source_id.strip()}")
    out["history_import_resolve"] = {
        "contact_1128_mapped": any(k == f"contact:{TARGET_CONTACT}" for k in entity_keys),
        "lead_29102_mapped": any(k == f"lead:{TARGET_LEAD}" for k in entity_keys),
        "entity_keys_for_canonical": entity_keys,
        "note": "history import matches archive files via canonical UUID or metadata.bitrix_import.external_ids guessed as lead/contact",
    }

    master = csv_rows(
        ARCHIVE / "BITRIX_HISTORY_MASTER.csv",
        lambda r: (
            str(r.get("bitrix_entity_id") or "") in {TARGET_CONTACT, TARGET_LEAD}
            and str(r.get("bitrix_entity_type") or "") in {"contact", "lead"}
        )
        or str(r.get("canonical_crm_contact_id") or "") == (cid or "")
        or is_eda(r.get("person_name")),
    )
    chats_master = csv_rows(
        ARCHIVE / "BITRIX_CHAT_MESSAGES_MASTER.csv",
        lambda r: (
            str(r.get("bitrix_entity_id") or "") in {TARGET_CONTACT, TARGET_LEAD}
            or str(r.get("canonical_crm_contact_id") or "") == (cid or "")
            or is_eda(r.get("person_name"))
        ),
    )
    out["history_master"] = {
        "rows": len(master),
        "by_type": dict(Counter(r.get("history_type") or "" for r in master)),
        "entities": sorted({f"{r.get('bitrix_entity_type')}:{r.get('bitrix_entity_id')}" for r in master}),
        "names": sorted({r.get("person_name") or "" for r in master}),
        "sample": [
            {k: r.get(k) for k in ("person_name", "bitrix_entity_type", "bitrix_entity_id", "history_type", "bitrix_record_id", "title")}
            for r in master[:8]
        ],
    }
    out["chat_master"] = {
        "rows": len(chats_master),
        "names": sorted({r.get("person_name") or "" for r in chats_master}),
    }

    archive_files = {
        "raw/contacts/1128.json": (ARCHIVE / "raw" / "contacts" / f"{TARGET_CONTACT}.json").exists(),
        "raw/leads/29102.json": (ARCHIVE / "raw" / "leads" / f"{TARGET_LEAD}.json").exists(),
        "raw/chats/live/contact_1128.json": (ARCHIVE / "raw" / "chats" / "live" / f"contact_{TARGET_CONTACT}.json").exists(),
        "raw/chats/live/lead_29102.json": (ARCHIVE / "raw" / "chats" / "live" / f"lead_{TARGET_LEAD}.json").exists(),
    }
    out["archive_files_exist"] = archive_files

    archive_entities = []
    for folder, etype in ((ARCHIVE / "raw" / "contacts", "contact"), (ARCHIVE / "raw" / "leads", "lead")):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            name = str(data.get("person_name") or "")
            eid = str(data.get("bitrix_entity_id") or path.stem)
            canon = str(data.get("canonical_crm_contact_id") or "")
            if eid in {TARGET_CONTACT, TARGET_LEAD} or canon == (cid or "") or is_eda(name):
                comments = data.get("timeline_comments") or []
                acts = data.get("crm_activities") or []
                tasks = [a for a in acts if str(a.get("PROVIDER_ID") or a.get("TYPE_ID") or "").upper().find("TASK") >= 0 or str(a.get("PROVIDER_TYPE_ID") or "").upper() == "TASK"]
                meetings = [a for a in acts if str(a.get("PROVIDER_TYPE_ID") or "").upper() in {"MEETING", "TODO"} or str(a.get("TYPE_ID") or "") == "1"]
                emails = [a for a in acts if "EMAIL" in str(a.get("PROVIDER_ID") or "").upper() or "MAIL" in str(a.get("PROVIDER_ID") or "").upper() or str(a.get("TYPE_ID") or "") == "4"]
                wa = [a for a in acts if "IMOPEN" in str(a.get("PROVIDER_ID") or "").upper() or "whatsapp" in str(a.get("SUBJECT") or "").lower() or "open channel" in str(a.get("SUBJECT") or "").lower()]
                file_refs = 0
                for a in acts:
                    file_refs += count_files(a.get("FILES") or a.get("STORAGE_ELEMENT_IDS") or [])
                    settings = a.get("SETTINGS") if isinstance(a.get("SETTINGS"), dict) else {}
                    file_refs += count_files(settings.get("FILES") or [])
                archive_entities.append(
                    {
                        "path": str(path.relative_to(ARCHIVE)),
                        "entity": f"{etype}:{eid}",
                        "person_name": name,
                        "canonical_crm_contact_id": canon,
                        "timeline_comments": len(comments),
                        "crm_activities": len(acts),
                        "emails": len(emails),
                        "whatsapp_open_channel": len(wa),
                        "tasks": len(tasks),
                        "meetings": len(meetings),
                        "attachment_file_refs": file_refs,
                        "activity_subjects": [str(a.get("SUBJECT") or "")[:80] for a in acts[:12]],
                    }
                )
    out["archive_entity_files"] = archive_entities

    manifest_path = DOCS / "reports" / "BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
    manifest = csv_rows(
        manifest_path,
        lambda r: str(r.get("canonical_crm_contact_id") or "") == (cid or "")
        or is_eda(r.get("person_name"))
        or str(r.get("bitrix_entity_id") or "") in {TARGET_CONTACT, TARGET_LEAD},
    )
    recovery = csv_rows(
        RECOVERY,
        lambda r: str(r.get("canonical_crm_contact_id") or "") == (cid or "") or is_eda(r.get("person_name")),
    )
    downloaded = [r for r in manifest if str(r.get("downloaded") or "").lower() in {"1", "true", "yes"}]
    linked = [r for r in manifest if str(r.get("crm_imported") or "").lower() in {"1", "true", "yes"}]
    inaccessible = recovery or [r for r in manifest if str(r.get("downloaded") or "").lower() not in {"1", "true", "yes"}]
    out["agreement_documents"] = {
        "manifest_rows": len(manifest),
        "downloaded": len(downloaded),
        "crm_linked_in_manifest": len(linked),
        "inaccessible_or_recovery": len(inaccessible),
        "by_source": dict(Counter(r.get("source_type") or "" for r in manifest or inaccessible)),
        "file_ids": [r.get("bitrix_file_id") for r in (manifest or inaccessible)],
        "recovery_rows": [
            {k: r.get(k) for k in ("person_name", "source_type", "source_record_id", "bitrix_file_id", "bitrix_entity_type", "bitrix_entity_id", "original_filename")}
            for r in recovery
        ],
        "manifest_sample": [
            {k: r.get(k) for k in ("person_name", "source_type", "bitrix_file_id", "downloaded", "crm_imported", "failure_reason", "bitrix_entity_type", "bitrix_entity_id")}
            for r in manifest[:12]
        ],
    }

    api_sim: dict[str, Any] = {}
    if cid:
        timeline_types = Counter(a["activity_type"] for a in activities if not a.get("archived_at"))
        timeline_len = len([a for a in activities if not a.get("archived_at")]) + len(agreements)
        api_sim["detail_id"] = cid
        api_sim["detail_name"] = canonical.get("display_name") if canonical else None
        api_sim["detail_crm_activities_len"] = len([a for a in activities if not a.get("archived_at")])
        api_sim["detail_agreements_len"] = len(agreements)
        api_sim["timeline_len"] = timeline_len
        api_sim["timeline_by_source"] = {
            "crm_activity": len([a for a in activities if not a.get("archived_at")]),
            "crm_agreement": len(agreements),
        }
        api_sim["timeline_by_type"] = dict(timeline_types)
        if agreements:
            api_sim["timeline_by_type"]["contract_signed"] = api_sim["timeline_by_type"].get("contract_signed", 0) + len(agreements)
        api_sim["timeline_titles"] = [a.get("title") for a in activities if not a.get("archived_at")] + [
            f"Anlaşma: {ag.get('project_group')}" for ag in agreements
        ]
        api_sim["documents_crm_contact_total"] = sum(1 for d in links if d.get("entity_type") == "crm_contact" and not d.get("archived_at"))
        api_sim["documents_contact_total"] = sum(1 for d in links if d.get("entity_type") == "contact" and not d.get("archived_at"))
        api_sim["ui_note"] = (
            "Unified Contact Card GET /crm/contacts/{id}/timeline reads crm_activities (entity_type=contact) "
            "plus agreement system events. Documents come from GET /documents/by-entity/crm_contact/{id} and /contact/{id}, "
            "excluding archived_at. Card will show comments/history only if crm_activities rows exist."
        )
    out["contact_card_api"] = api_sim

    # Live Bitrix read-only: confirm contact 1128 and whether history exists unarchived.
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    live: dict[str, Any] = {}
    contact_get = client.call("crm.contact.get", {"id": TARGET_CONTACT})
    rec = contact_get.get("result") if isinstance(contact_get.get("result"), dict) else {}
    live["contact_get"] = {
        **slim_bitrix(contact_get),
        "id": rec.get("ID"),
        "name": " ".join(p for p in [str(rec.get("NAME") or "").strip(), str(rec.get("LAST_NAME") or "").strip()] if p),
        "assigned": rec.get("ASSIGNED_BY_ID"),
        "has_imol": rec.get("HAS_IMOL"),
        "has_email": rec.get("HAS_EMAIL"),
        "has_phone": rec.get("HAS_PHONE"),
        "phone": rec.get("PHONE"),
        "email": rec.get("EMAIL"),
    }
    lead_get = client.call("crm.lead.get", {"id": TARGET_LEAD})
    lead = lead_get.get("result") if isinstance(lead_get.get("result"), dict) else {}
    live["lead_get"] = {
        **slim_bitrix(lead_get),
        "id": lead.get("ID"),
        "title": lead.get("TITLE"),
        "name": " ".join(p for p in [str(lead.get("NAME") or "").strip(), str(lead.get("LAST_NAME") or "").strip()] if p),
        "status": lead.get("STATUS_ID"),
        "contact_id": lead.get("CONTACT_ID"),
        "assigned": lead.get("ASSIGNED_BY_ID"),
    }
    for label, entity_type, owner_id in (
        ("contact_1128_comments", "contact", TARGET_CONTACT),
        ("lead_29102_comments", "lead", TARGET_LEAD),
    ):
        rows = bitrix_list(client, "crm.timeline.comment.list", {"filter": {"ENTITY_ID": owner_id, "ENTITY_TYPE": entity_type}})
        err = rows[0] if rows and isinstance(rows[0], dict) and rows[0].get("_error") else None
        live[label] = {
            "error": (err or {}).get("_error"),
            "count": 0 if err else len(rows),
            "ids": [r.get("ID") for r in rows[:20] if isinstance(r, dict) and not r.get("_error")],
        }
    for label, owner_type, owner_id in (
        ("contact_1128_activities", 3, TARGET_CONTACT),
        ("lead_29102_activities", 1, TARGET_LEAD),
    ):
        rows = bitrix_list(
            client,
            "crm.activity.list",
            {
                "filter": {"OWNER_TYPE_ID": owner_type, "OWNER_ID": owner_id},
                "select": ["ID", "SUBJECT", "TYPE_ID", "PROVIDER_ID", "PROVIDER_TYPE_ID", "FILES"],
            },
        )
        err = rows[0] if rows and isinstance(rows[0], dict) and rows[0].get("_error") else None
        file_refs = 0
        kinds = Counter()
        for r in rows:
            if not isinstance(r, dict) or r.get("_error"):
                continue
            kinds[str(r.get("PROVIDER_TYPE_ID") or r.get("PROVIDER_ID") or r.get("TYPE_ID") or "")] += 1
            file_refs += count_files(r.get("FILES") or [])
        live[label] = {
            "error": (err or {}).get("_error"),
            "count": 0 if err else len(rows),
            "kinds": dict(kinds),
            "file_refs": file_refs,
            "subjects": [str(r.get("SUBJECT") or "")[:80] for r in rows[:15] if isinstance(r, dict) and not r.get("_error")],
        }
    oc = client.call("imopenlines.crm.chat.get", {"CRM_ENTITY_TYPE": "CONTACT", "CRM_ENTITY": TARGET_CONTACT, "ACTIVE_ONLY": "N"})
    live["open_channel_contact"] = {**slim_bitrix(oc), "result": oc.get("result") if not oc.get("error") else None}
    oc2 = client.call("imopenlines.crm.chat.get", {"CRM_ENTITY_TYPE": "LEAD", "CRM_ENTITY": TARGET_LEAD, "ACTIVE_ONLY": "N"})
    live["open_channel_lead"] = {**slim_bitrix(oc2), "result": oc2.get("result") if not oc2.get("error") else None}
    live["bitrix_calls"] = client.call_count
    out["live_bitrix"] = live

    history_found = (
        sum(e.get("timeline_comments", 0) + e.get("crm_activities", 0) for e in archive_entities)
        + out["history_master"]["rows"]
        + (live.get("contact_1128_comments") or {}).get("count", 0)
        + (live.get("lead_29102_comments") or {}).get("count", 0)
        + (live.get("contact_1128_activities") or {}).get("count", 0)
        + (live.get("lead_29102_activities") or {}).get("count", 0)
    )
    live_history = (
        (live.get("contact_1128_comments") or {}).get("count", 0)
        + (live.get("lead_29102_comments") or {}).get("count", 0)
        + (live.get("contact_1128_activities") or {}).get("count", 0)
        + (live.get("lead_29102_activities") or {}).get("count", 0)
    )
    file_refs = (
        sum(e.get("attachment_file_refs", 0) for e in archive_entities)
        + (live.get("contact_1128_activities") or {}).get("file_refs", 0)
        + (live.get("lead_29102_activities") or {}).get("file_refs", 0)
        + len(recovery)
        + len(manifest)
    )
    out["counts"] = {
        "canonical_contact_id": cid,
        "agreements": len(agreements),
        "bitrix_history_records_in_archive": out["history_master"]["rows"] + sum(e.get("timeline_comments", 0) + e.get("crm_activities", 0) for e in archive_entities),
        "live_bitrix_history_records": live_history,
        "crm_activities_rows": len(activities),
        "bitrix_file_references": len(set(out["agreement_documents"]["file_ids"])) or file_refs,
        "downloaded_files": len(downloaded),
        "crm_linked_documents": out["crm_documents"]["active"],
        "inaccessible_files": len(recovery),
        "duplicate_contacts": len(out["duplicate_contacts"]),
        "contact_card_timeline_items": api_sim.get("timeline_len"),
        "contact_card_documents_crm_contact": api_sim.get("documents_crm_contact_total"),
        "contact_card_documents_contact": api_sim.get("documents_contact_total"),
        "contact_card_detail_activities": api_sim.get("detail_crm_activities_len"),
    }
    causes = []
    if not archive_files["raw/contacts/1128.json"] and not archive_files["raw/leads/29102.json"]:
        causes.append("contact 1128 and lead 29102 were never exported into BITRIX_FINAL_HISTORY_ARCHIVE, so history import had nothing to attach")
    if out["history_master"]["rows"] == 0:
        causes.append("BITRIX_HISTORY_MASTER.csv has 0 rows for Eda / contact 1128 / lead 29102 / her UUID")
    if cid and not out["history_import_resolve"]["entity_keys_for_canonical"]:
        causes.append("canonical contact metadata has no Bitrix contact/lead entity key; history import cannot match 1128 even if archived later")
    elif cid and ("contact", TARGET_CONTACT) not in {(k.split(":")[0], k.split(":")[1]) for k in out["history_import_resolve"]["entity_keys_for_canonical"]}:
        causes.append("canonical contact is not mapped to Bitrix contact 1128 in metadata.bitrix_import.external_ids")
    if len(activities) == 0:
        causes.append("crm_activities has 0 rows for the canonical UUID, so Unified Contact Card timeline has no comments/emails/WhatsApp")
    if out["crm_documents"]["active"] == 0:
        causes.append("no active document_links for her UUID; card documents panel is empty")
    if len(recovery) and len(downloaded) == 0:
        causes.append("agreement-contact rescue found email attachments on lead 29102 but binaries are inaccessible to the admin webhook, so they were never imported")
    if live_history:
        causes.append(f"live Bitrix still has {live_history} comment/activity records that were not archived or imported")
    out["root_cause"] = causes
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    db.close()


if __name__ == "__main__":
    main()
