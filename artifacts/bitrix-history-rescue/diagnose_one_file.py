"""Read-only diagnostic: user.current + one inaccessible agreement-contact file."""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
MANIFEST = Path(
    "/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports/BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
)
ENV_PATH = Path("/tmp/.env")


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


def redact(obj, base: str) -> object:
    import re

    text = json.dumps(obj, ensure_ascii=False, default=str)
    text = text.replace(base, "[REDACTED_WEBHOOK]/")
    token_segs = [s for s in urllib.parse.urlparse(base).path.split("/") if s]
    if token_segs:
        text = text.replace(token_segs[-1], "[REDACTED]")
    text = re.sub(r"https?://investhome2\.bitrix24\.com", "[BITRIX_HOST]", text)
    text = re.sub(r"auth=[^&\"'\\s]+", "auth=[REDACTED]", text)
    return json.loads(text)


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
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": f"HTTP {exc.code}", "error_description": raw[:400]}
        return parsed


def pick_row() -> dict:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    inacc = [r for r in rows if r.get("recovered") != "yes"]
    # Prefer a named IDENTITY/PAYMENT/CLOSING comment or email with a numeric file id.
    ranked = []
    for row in inacc:
        cat = row.get("document_category")
        src = row.get("source_type")
        name = (row.get("original_filename") or "").lower()
        if cat not in {"IDENTITY", "PAYMENT", "CLOSING"} or not row.get("bitrix_file_id"):
            continue
        score = 0
        if src == "comment":
            score += 50
        if src == "email":
            score += 30
        if any(tok in name for tok in ("pasaport", "passport", "kimlik", "dekont", "swift", "closing")):
            score += 40
        if row.get("original_filename"):
            score += 10
        ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else inacc[0]


def find_in_archive(row: dict) -> tuple[dict, dict]:
    """Search archive entity file first, then all lead/contact files for this source/file id."""
    entity_type = row["bitrix_entity_type"]
    entity_id = row["bitrix_entity_id"]
    data = load_entity(entity_type, entity_id)
    payload = find_payload(data, row)
    if payload.get("matched") and payload.get("node"):
        return data, payload
    file_id = str(row.get("bitrix_file_id") or "")
    source_id = str(row.get("source_record_id") or "")
    for folder, etype in ((ARCHIVE / "raw" / "leads", "lead"), (ARCHIVE / "raw" / "contacts", "contact")):
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            raw = path.read_text(encoding="utf-8")
            if file_id not in raw and source_id not in raw:
                continue
            candidate = json.loads(raw)
            payload = find_payload(candidate, row)
            if payload.get("matched"):
                return candidate, payload
            # fallback: scan comments/activities for file id even if source id differs
            for comment in candidate.get("timeline_comments") or []:
                files = comment.get("FILES") or {}
                if isinstance(files, dict) and (file_id in files or any(str((v or {}).get("id")) == file_id for v in files.values() if isinstance(v, dict))):
                    node = files.get(file_id)
                    if node is None:
                        for val in files.values():
                            if isinstance(val, dict) and str(val.get("id")) == file_id:
                                node = val
                                break
                    return candidate, {
                        "matched": True,
                        "where": "timeline_comments.FILES",
                        "comment_id": comment.get("ID"),
                        "comment_keys": sorted(comment.keys()),
                        "node": node,
                        "surrounding_text": str(comment.get("COMMENT") or "")[:400],
                    }
            for activity in candidate.get("crm_activities") or []:
                for item in activity.get("FILES") or []:
                    if isinstance(item, dict) and str(item.get("id") or "") == file_id:
                        return candidate, {
                            "matched": True,
                            "where": "crm_activities.FILES",
                            "activity_id": activity.get("ID"),
                            "provider": activity.get("PROVIDER_ID"),
                            "type_id": activity.get("TYPE_ID"),
                            "subject": activity.get("SUBJECT"),
                            "activity_keys": sorted(activity.keys()),
                            "node": item,
                        }
    return data, payload


def load_entity(entity_type: str, entity_id: str) -> dict:
    folder = "contacts" if entity_type == "contact" else "leads"
    path = ARCHIVE / "raw" / folder / f"{entity_id}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def find_payload(data: dict, row: dict) -> dict:
    source = row["source_type"]
    source_id = str(row.get("source_record_id") or "")
    file_id = str(row.get("bitrix_file_id") or "")
    found = {"matched": False, "where": None, "node": None, "parent_keys": []}
    if source == "comment":
        for comment in data.get("timeline_comments") or []:
            if str(comment.get("ID") or "") != source_id:
                continue
            files = comment.get("FILES") or {}
            node = None
            if isinstance(files, dict):
                node = files.get(file_id) or files.get(int(file_id) if file_id.isdigit() else file_id)
                if node is None:
                    for val in files.values():
                        if isinstance(val, dict) and str(val.get("id") or val.get("ID") or "") == file_id:
                            node = val
                            break
            found = {
                "matched": True,
                "where": "timeline_comments.FILES",
                "comment_id": comment.get("ID"),
                "comment_keys": sorted(comment.keys()),
                "files_type": type(files).__name__,
                "node": node,
                "surrounding_text": str(comment.get("COMMENT") or "")[:300],
            }
            return found
    if source == "email":
        for activity in data.get("crm_activities") or []:
            if str(activity.get("ID") or "") != source_id:
                continue
            files = activity.get("FILES")
            node = None
            for item in files or []:
                if isinstance(item, dict) and str(item.get("id") or item.get("ID") or "") == file_id:
                    node = item
                    break
            found = {
                "matched": True,
                "where": "crm_activities.FILES",
                "activity_id": activity.get("ID"),
                "provider": activity.get("PROVIDER_ID"),
                "type_id": activity.get("TYPE_ID"),
                "subject": activity.get("SUBJECT"),
                "activity_keys": sorted(activity.keys()),
                "files": files,
                "node": node,
            }
            return found
    if source == "WhatsApp":
        live = ARCHIVE / "raw" / "chats" / "live" / f"{data.get('bitrix_entity_type')}_{data.get('bitrix_entity_id')}.json"
        # try glob
        live_dir = ARCHIVE / "raw" / "chats" / "live"
        for path in live_dir.glob("*.json"):
            chat_data = json.loads(path.read_text(encoding="utf-8"))
            if str(chat_data.get("bitrix_entity_id")) != str(data.get("bitrix_entity_id")):
                continue
            for chat in chat_data.get("chats") or []:
                for message in chat.get("messages") or []:
                    raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
                    params = raw.get("params") or {}
                    file_ids = params.get("FILE_ID") or []
                    if str(file_id) in {str(x) for x in (file_ids if isinstance(file_ids, list) else [file_ids])}:
                        return {
                            "matched": True,
                            "where": "live_chat.params.FILE_ID",
                            "message_id": message.get("message_id") or raw.get("id"),
                            "params_keys": list(params.keys()) if isinstance(params, dict) else [],
                            "FILE_ID": file_ids,
                            "FILES": params.get("FILES") if isinstance(params, dict) else None,
                            "raw_keys": list(raw.keys()),
                            "text": str(message.get("message_text") or raw.get("text") or "")[:200],
                        }
    return found


def classify_id(row: dict, payload: dict) -> str:
    source = row["source_type"]
    node = payload.get("node") if isinstance(payload.get("node"), dict) else {}
    if source == "comment" and node:
        if node.get("urlDownload") or node.get("urlShow"):
            url = str(node.get("urlDownload") or node.get("urlShow") or "")
            if "/disk/downloadFile/" in url:
                return "disk file ID (comment FILES.id used by /disk/downloadFile/{id}/)"
            if "attachedId=" in url or "uf.php" in url:
                return "disk attached object ID (UF attachedId)"
        if node.get("type") == "file" and node.get("id"):
            return "disk file ID (Bitrix comment FILES disk object)"
    if source == "email":
        url = ""
        if node:
            url = str(node.get("url") or "")
        if "crm_show_file.php" in url or "fileId=" in url:
            return "CRM email/activity file ID (crm_show_file.php fileId, not disk.file.get id)"
        return "CRM email/activity file ID"
    if source == "WhatsApp":
        return "WhatsApp/Open Channel IM FILE_ID (chat attachment, not necessarily disk.file.get id)"
    if source == "entity_field":
        return "CRM entity file-field ID"
    return "unknown attachment identifier"


def summarize_user(result: dict) -> dict:
    if not isinstance(result, dict):
        return {"raw_type": type(result).__name__}
    name = " ".join(p for p in [result.get("NAME"), result.get("LAST_NAME")] if p).strip()
    folded = name.casefold().replace("ı", "i")
    is_hasan = "hasan" in folded and "acar" in folded
    keep_keys = [
        "ID",
        "XML_ID",
        "ACTIVE",
        "NAME",
        "LAST_NAME",
        "SECOND_NAME",
        "EMAIL",
        "IS_ONLINE",
        "IS_ADMIN",
        "ADMIN",
        "USER_TYPE",
        "EXTERNAL_AUTH_ID",
        "UF_DEPARTMENT",
        "PERSONAL_PROFESSION",
        "WORK_POSITION",
        "WORK_DEPARTMENT",
    ]
    fields = {k: result.get(k) for k in keep_keys if k in result}
    extra_admin = {k: result.get(k) for k in result if any(tok in k.upper() for tok in ("ADMIN", "PERM", "ACCESS", "RIGHT"))}
    return {
        "id": result.get("ID"),
        "name": name or None,
        "is_hasan_acar": is_hasan,
        "selected_fields": fields,
        "admin_or_permission_fields": extra_admin,
        "all_keys": sorted(result.keys()),
    }


def probe_url(url: str, base: str) -> dict:
    if not url:
        return {"skipped": True}
    if url.startswith("/"):
        origin = urllib.parse.urlunparse(urllib.parse.urlparse(base)[:2] + ("", "", "", ""))
        url = origin + url
    parsed = urllib.parse.urlparse(url)
    token = [s for s in urllib.parse.urlparse(base).path.split("/") if s][-1]
    q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if not q.get("auth") or q.get("auth") == [""]:
        q["auth"] = [token]
        authed = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(q, doseq=True)))
    else:
        authed = url
    out = {}
    for label, target in (("plain", url), ("with_webhook_auth", authed)):
        req = urllib.request.Request(target, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                chunk = resp.read(200)
                ctype = resp.headers.get("Content-Type") or ""
                out[label] = {
                    "http": resp.status,
                    "content_type": ctype,
                    "bytes": len(chunk),
                    "looks_html": chunk.lstrip()[:1] in (b"<",) or "text/html" in ctype.lower(),
                    "disposition": resp.headers.get("Content-Disposition"),
                }
        except urllib.error.HTTPError as exc:
            out[label] = {"http": exc.code, "error": str(exc.reason)}
        except Exception as exc:  # noqa: BLE001
            out[label] = {"exception": type(exc).__name__}
    return out


def main() -> None:
    base = webhook_base(load_env(ENV_PATH).get("BITRIX_WEBHOOK_URL") or "")
    user_body = call(base, "user.current", {})
    user_result = user_body.get("result") if not user_body.get("error") else None
    user_summary = {
        "error": user_body.get("error"),
        "error_description": user_body.get("error_description"),
        "user": summarize_user(user_result) if isinstance(user_result, dict) else None,
    }
    if user_summary["user"] is None:
        profile = call(base, "profile", {})
        user_summary["profile_fallback"] = redact(profile, base)

    row = pick_row()
    data, payload = find_in_archive(row)
    entity_type = str(data.get("bitrix_entity_type") or row["bitrix_entity_type"])
    entity_id = str(data.get("bitrix_entity_id") or row["bitrix_entity_id"])
    id_type = classify_id(row, payload)

    tests = []
    file_id = row.get("bitrix_file_id")
    source = row["source_type"]
    source_id = row.get("source_record_id")

    # Always inspect live source record.
    if source == "comment":
        live = call(
            base,
            "crm.timeline.comment.list",
            {"filter[ENTITY_TYPE]": entity_type, "filter[ENTITY_ID]": entity_id, "start": 0},
        )
        comments = live.get("result") or []
        target = None
        wanted_comment = str(payload.get("comment_id") or source_id)
        for comment in comments:
            if str(comment.get("ID") or "") == wanted_comment:
                target = comment
                break
        tests.append(
            {
                "method": "crm.timeline.comment.list",
                "purpose": "refresh FILES for the exact comment on this Bitrix entity",
                "error": live.get("error"),
                "error_description": live.get("error_description"),
                "result_count": len(comments) if isinstance(comments, list) else None,
                "matched_comment_id": (target or {}).get("ID"),
                "matched_files_ids": list((target or {}).get("FILES") or {}) if isinstance((target or {}).get("FILES"), dict) else (target or {}).get("FILES"),
                "matched_file_node": ((target or {}).get("FILES") or {}).get(file_id)
                if isinstance((target or {}).get("FILES"), dict)
                else None,
            }
        )
    if source == "email" and source_id:
        live = call(base, "crm.activity.get", {"id": source_id})
        result = live.get("result") if not live.get("error") else None
        tests.append(
            {
                "method": "crm.activity.get",
                "purpose": "refresh email activity FILES for this source record",
                "error": live.get("error"),
                "error_description": live.get("error_description"),
                "files": result.get("FILES") if isinstance(result, dict) else None,
                "storage": result.get("STORAGE_ELEMENT_IDS") if isinstance(result, dict) else None,
                "provider": result.get("PROVIDER_ID") if isinstance(result, dict) else None,
            }
        )

    if "disk file ID" in id_type:
        disk = call(base, "disk.file.get", {"id": file_id})
        tests.append(
            {
                "method": "disk.file.get",
                "purpose": "ID confirmed as disk file ID from comment FILES.urlDownload=/disk/downloadFile/{id}/",
                "error": disk.get("error"),
                "error_description": disk.get("error_description"),
                "has_result": isinstance(disk.get("result"), dict),
                "result_keys": sorted((disk.get("result") or {}).keys()) if isinstance(disk.get("result"), dict) else [],
            }
        )
        attached = call(base, "disk.attachedObject.get", {"id": file_id})
        tests.append(
            {
                "method": "disk.attachedObject.get",
                "purpose": "negative check: same numeric ID as attached object",
                "error": attached.get("error"),
                "error_description": attached.get("error_description"),
            }
        )
    elif source == "email":
        tests.append(
            {
                "method": "disk.file.get",
                "purpose": "NOT tested as primary: stored ID is CRM email fileId, not a disk file ID",
                "skipped": True,
            }
        )
        show = None
        node = payload.get("node") if isinstance(payload.get("node"), dict) else {}
        url = (node or {}).get("url")
        if url:
            tests.append({"method": "GET crm_show_file.php from payload url", "url_probe": probe_url(url, base)})
        elif file_id and source_id:
            origin = urllib.parse.urlunparse(urllib.parse.urlparse(base)[:2] + ("", "", "", ""))
            show = f"{origin}/bitrix/tools/crm_show_file.php?fileId={file_id}&ownerTypeId=6&ownerId={source_id}"
            tests.append({"method": "GET crm_show_file.php constructed", "url_probe": probe_url(show, base)})
    else:
        disk = call(base, "disk.file.get", {"id": file_id})
        tests.append(
            {
                "method": "disk.file.get",
                "purpose": "only because identifier type was not confirmed as disk; recorded for comparison",
                "error": disk.get("error"),
                "error_description": disk.get("error_description"),
            }
        )

    node = payload.get("node") if isinstance(payload.get("node"), dict) else None
    node_out = None
    if isinstance(node, dict):
        node_out = {
            k: node.get(k)
            for k in ("id", "ID", "name", "NAME", "type", "size", "image", "urlDownload", "urlShow", "url", "date")
            if k in node
        }

    report = {
        "person_name": row.get("person_name"),
        "document_category": row.get("document_category"),
        "original_filename": row.get("original_filename"),
        "source_type": row.get("source_type"),
        "source_record_id": row.get("source_record_id"),
        "bitrix_entity_type": entity_type,
        "bitrix_entity_id": entity_id,
        "stored_attachment_id": file_id,
        "identifier_type": id_type,
        "payload_match": payload.get("matched"),
        "payload_where": payload.get("where"),
        "payload_node": node_out,
        "payload_extra": {
            k: payload.get(k)
            for k in payload
            if k not in {"node", "files"}
        },
        "user.current": user_summary,
        "tests": redact(tests, base),
    }
    print(json.dumps(redact(report, base), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
