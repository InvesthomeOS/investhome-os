"""Recover agreement-contact Bitrix files via admin webhook and link to CRM Documents.

Read-only against Bitrix. Does not modify contacts or agreements.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.config.documents_config import ALLOWED_EXTENSIONS, infer_file_kind
from investhome_api.db.session import SessionLocal
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    DocumentVisibility,
    DocumentWorkspaceFolder,
    ProcessingStatus,
    StorageProvider,
)
from investhome_api.models.user_auth import User
from investhome_api.services.document_service import create_document_analysis
from investhome_api.services.document_validation import compute_checksum, generate_storage_key
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

EXISTING_MANIFEST = Path(
    "/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports/BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
)
OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS")
ENV_PATH = Path("/tmp/.env")
HTML_HEAD = re.compile(br"^\s*<(!doctype|html|head|script|body)\b", re.I)
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
NON_DIGIT = re.compile(r"[^\w.\- ()]+")
MANIFEST_FIELDS = [
    "canonical_crm_contact_id",
    "person_name",
    "agreement_id",
    "project_group",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "source_type",
    "source_record_id",
    "bitrix_file_id",
    "original_filename",
    "mime_type",
    "file_size",
    "downloaded",
    "local_archive_path",
    "sha256",
    "ownership_verified",
    "ownership_method",
    "crm_imported",
    "crm_document_id",
    "failure_reason",
]
SAMPLE_NAMES = ["Kaan Kalyon", "Berk Çimen"]


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
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(segs) + "/", "", "", ""))


def webhook_token(base: str) -> str:
    segs = [s for s in urllib.parse.urlparse(base).path.split("/") if s]
    return segs[-1] if segs else ""


def redact(text: str, webhook: str) -> str:
    cleaned = (text or "").replace(webhook, "[REDACTED]")
    token = webhook_token(webhook)
    if token:
        cleaned = cleaned.replace(token, "[REDACTED]")
    return WEBHOOK_RE.sub("[REDACTED_URL]", cleaned)


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.origin = urllib.parse.urlunparse(urllib.parse.urlparse(self.base)[:2] + ("", "", "", ""))
        self.min_interval = 0.3
        self._last = 0.0
        self.call_count = 0

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def call(self, method: str, payload: dict | None = None) -> dict:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last_error = None
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
                    parsed = {"error": f"HTTP {exc.code}", "error_description": redact(raw, self.base)[:400]}
            except Exception as exc:  # noqa: BLE001
                last_error = redact(str(exc), self.base)
                time.sleep(min(20, 2 ** attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            parsed["error_description"] = redact(str(parsed.get("error_description") or ""), self.base)
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                time.sleep(min(30, 2 ** (attempt + 1)))
                last_error = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last_error or "unknown"}

    def download(self, url: str) -> tuple[bytes | None, str | None, str | None]:
        if not url:
            return None, None, "no_url"
        if url.startswith("/"):
            url = self.origin + url
        self._wait()
        self.call_count += 1
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=90) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                data = resp.read()
            self._last = time.time()
            if not data:
                return None, ctype, "empty_body"
            if HTML_HEAD.search(data[:200]) or "text/html" in (ctype or ""):
                return None, ctype, "html_login_or_error_page"
            if data.lstrip()[:1] == b"{" and b'"error"' in data[:400]:
                return None, ctype, "json_error_body"
            return data, ctype, None
        except urllib.error.HTTPError as exc:
            self._last = time.time()
            return None, None, f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            return None, None, redact(str(exc), self.base)[:200]


def log(path: Path, message: str) -> None:
    line = f"{utc_now()} {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def safe_filename(name: str | None, file_id: str) -> str:
    raw = (name or "").strip() or f"bitrix-file-{file_id}"
    raw = raw.replace("\\", "_").replace("/", "_").replace("\x00", "")
    raw = NON_DIGIT.sub("_", raw).strip(" .")
    if not raw:
        raw = f"bitrix-file-{file_id}"
    if len(raw) > 180:
        stem, dot, ext = raw.rpartition(".")
        raw = (stem[: 170 - len(ext)] + "." + ext) if dot and len(ext) <= 8 else raw[:180]
    return raw


def unique_dest(folder: Path, filename: str, file_id: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem, dot, ext = filename.rpartition(".")
    if dot and ext:
        return folder / f"{stem}__bitrix-{file_id}.{ext}"
    return folder / f"{filename}__bitrix-{file_id}"


def import_tag(contact_id: str, file_id: str) -> str:
    return f"bitrix:{file_id}:{contact_id}"


def load_agreement_contacts(db: Session) -> dict[str, dict]:
    rows = db.execute(
        text(
            """
            select a.id::text as agreement_id,
                   coalesce(a.project_group, '') as project_group,
                   a.contact_id::text as cid,
                   c.display_name
            from crm_agreements a
            join crm_contacts c on c.id = a.contact_id
            order by c.display_name, a.project_group
            """
        )
    ).mappings().all()
    contacts: dict[str, dict] = {}
    for row in rows:
        rec = contacts.setdefault(
            row["cid"],
            {"cid": row["cid"], "name": row["display_name"], "agreements": [], "entities": set()},
        )
        rec["agreements"].append({"id": row["agreement_id"], "project_group": row["project_group"]})
    for rec in contacts.values():
        rec["agreement_id"] = " | ".join(item["id"] for item in rec["agreements"])
        rec["project_group"] = " | ".join(item["project_group"] for item in rec["agreements"])
    return contacts


def load_manifest_rows() -> list[dict]:
    with EXISTING_MANIFEST.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def recover_binary(client: BitrixClient, row: dict) -> tuple[bytes | None, str | None, str | None, str | None]:
    """Return (content, filename, mime, error)."""
    file_id = str(row.get("bitrix_file_id") or "").strip()
    source = row.get("source_type") or ""
    source_id = str(row.get("source_record_id") or "")
    filename = (row.get("original_filename") or "").strip() or None
    if not file_id:
        return None, filename, None, "missing_file_id"

    disk = client.call("disk.file.get", {"id": file_id})
    result = disk.get("result") if not disk.get("error") else None
    if isinstance(result, dict):
        filename = result.get("NAME") or result.get("name") or filename
        url = result.get("DOWNLOAD_URL") or result.get("downloadUrl")
        content, mime, err = client.download(str(url) if url else "")
        if content:
            return content, filename, mime, None
        return None, filename, mime, err or redact(
            str(disk.get("error") or disk.get("error_description") or "disk_download_failed"),
            client.base,
        )

    reasons = [f"disk.file.get:{disk.get('error') or disk.get('error_description') or 'failed'}"]
    if source == "email" and source_id:
        activity = client.call("crm.activity.get", {"id": source_id})
        payload = activity.get("result") if not activity.get("error") else None
        if isinstance(payload, dict):
            files = payload.get("FILES") or []
            if not isinstance(files, list):
                files = [files]
            for item in files:
                if not isinstance(item, dict):
                    continue
                if str(item.get("id") or item.get("ID") or "") != file_id:
                    continue
                url = item.get("url") or item.get("DOWNLOAD_URL") or item.get("urlDownload")
                content, mime, err = client.download(str(url) if url else "")
                if content:
                    return content, filename, mime, None
                reasons.append(err or "email_url_failed")
        else:
            reasons.append(f"crm.activity.get:{activity.get('error') or activity.get('error_description')}")
        show = (
            f"{client.origin}/bitrix/tools/crm_show_file.php"
            f"?fileId={file_id}&ownerTypeId=6&ownerId={source_id}"
        )
        content, mime, err = client.download(show)
        if content:
            return content, filename, mime, None
        reasons.append(err or "crm_show_file_failed")
    return None, filename, None, "; ".join(str(r) for r in reasons if r)[:400]


def mime_of(filename: str | None, detected: str | None, content: bytes | None) -> str:
    if detected and detected not in {"application/octet-stream", "binary/octet-stream"} and "html" not in detected:
        return detected
    if content:
        if content.startswith(b"%PDF"):
            return "application/pdf"
        if content[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if content.startswith(b"\x89PNG"):
            return "image/png"
    name = (filename or "").lower()
    if "." in name:
        ext = name.rsplit(".", 1)[-1]
        allowed = ALLOWED_EXTENSIONS.get(ext)
        if allowed:
            return allowed[0]
    return detected or "application/octet-stream"


def ext_of(filename: str | None, mime: str) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext
    for ext, mimes in ALLOWED_EXTENSIONS.items():
        if mime in mimes:
            return ext
    return ""


def assign_ownership(rows: list[dict], contacts: dict[str, dict]) -> None:
    owners_by_file: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        cid = (row.get("canonical_contact_id") or row.get("canonical_crm_contact_id") or "").strip()
        fid = str(row.get("bitrix_file_id") or "").strip()
        if cid and fid:
            owners_by_file[fid].add(cid)
    for row in rows:
        cid = (row.get("canonical_contact_id") or row.get("canonical_crm_contact_id") or "").strip()
        fid = str(row.get("bitrix_file_id") or "").strip()
        if not cid or cid not in contacts:
            row["ownership_verified"] = "no"
            row["ownership_method"] = ""
            row["_own_reason"] = "canonical_contact_not_in_agreement_set"
            continue
        owners = owners_by_file.get(fid) or set()
        agreement_owners = {item for item in owners if item in contacts}
        if len(agreement_owners) > 1:
            row["ownership_verified"] = "no"
            row["ownership_method"] = ""
            row["_own_reason"] = "ambiguous_multiple_canonical_owners:" + ",".join(sorted(agreement_owners))
            continue
        if agreement_owners != {cid}:
            row["ownership_verified"] = "no"
            row["ownership_method"] = ""
            row["_own_reason"] = "canonical_uuid_does_not_uniquely_own_file"
            continue
        row["ownership_verified"] = "yes"
        row["ownership_method"] = "manifest_canonical_uuid"
        row["_own_reason"] = ""


def existing_document(db: Session, tag: str) -> Document | None:
    return db.scalar(select(Document).where(Document.tags == tag).limit(1))


def link_exists(db: Session, document_id: UUID, entity_type: str, entity_id: UUID) -> bool:
    return db.scalar(
        select(DocumentLink.id).where(
            DocumentLink.document_id == document_id,
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
        )
    ) is not None


def import_document(
    db: Session,
    actor: User,
    row: dict,
    content: bytes,
    local_path: str,
) -> tuple[str, str | None, str]:
    contact_id = row["canonical_crm_contact_id"]
    file_id = str(row["bitrix_file_id"])
    tag = import_tag(contact_id, file_id)
    filename = row.get("original_filename") or f"bitrix-file-{file_id}"
    mime = row.get("mime_type") or "application/octet-stream"
    ext = ext_of(filename, mime)
    if not ext or ext not in ALLOWED_EXTENSIONS:
        return "no", None, f"unsupported_extension:{ext or 'missing'}"

    existing = existing_document(db, tag)
    if existing:
        skipped = 0
        created = 0
        uid = UUID(contact_id)
        for entity_type in ("crm_contact", "contact"):
            if link_exists(db, existing.id, entity_type, uid):
                skipped += 1
            else:
                db.add(
                    DocumentLink(
                        document_id=existing.id,
                        entity_type=entity_type,
                        entity_id=uid,
                        relationship_type="bitrix_source",
                    )
                )
                created += 1
        if created:
            db.flush()
            return "yes", str(existing.id), ""
        return "skipped_duplicate", str(existing.id), ""

    stored_name, storage_key = generate_storage_key(ext)
    checksum = compute_checksum(content)
    storage = get_storage_provider()
    storage.save(storage_key, BytesIO(content), content_length=len(content))
    file_kind = infer_file_kind(ext)
    doc_type = DocumentType.OTHER
    mapping = {
        "pdf": DocumentType.PDF,
        "jpg": DocumentType.IMAGE,
        "jpeg": DocumentType.IMAGE,
        "png": DocumentType.IMAGE,
        "webp": DocumentType.IMAGE,
        "gif": DocumentType.IMAGE,
        "doc": DocumentType.WORD,
        "docx": DocumentType.WORD,
        "xls": DocumentType.EXCEL,
        "xlsx": DocumentType.EXCEL,
    }
    doc_type = mapping.get(ext, DocumentType.OTHER)
    doc_date = None
    raw_dt = str(row.get("datetime") or "")[:10]
    try:
        if raw_dt and raw_dt[0].isdigit():
            doc_date = date.fromisoformat(raw_dt)
    except ValueError:
        doc_date = None
    notes = json.dumps(
        {
            "source": "bitrix",
            "canonical_contact_id": contact_id,
            "bitrix_file_id": file_id,
            "bitrix_entity_type": row.get("bitrix_entity_type"),
            "bitrix_entity_id": row.get("bitrix_entity_id"),
            "source_type": row.get("source_type"),
            "source_record_id": row.get("source_record_id"),
            "archive_path": local_path,
            "sha256": checksum,
            "import_key": tag,
        },
        ensure_ascii=False,
    )
    document = Document(
        title=(filename.rsplit(".", 1)[0] if "." in filename else filename)[:500],
        original_file_name=filename[:500],
        stored_file_name=stored_name,
        file_extension=ext,
        mime_type=mime[:120],
        file_size=len(content),
        storage_provider=provider_enum(),
        storage_key=storage_key,
        checksum=checksum,
        document_type=doc_type,
        category="bitrix",
        folder=DocumentWorkspaceFolder.GENERAL,
        file_kind=file_kind,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.ORGANIZATION,
        confidentiality_level=ConfidentialityLevel.INTERNAL,
        version_number=1,
        uploaded_by_user_id=actor.id,
        owner_user_id=actor.id,
        description="Bitrix recovered file for agreement contact",
        notes=notes,
        tags=tag[:1000],
        document_date=doc_date,
        is_latest_version=True,
        processing_status=ProcessingStatus.UPLOADED,
    )
    db.add(document)
    db.flush()
    create_document_analysis(db, document.id)
    uid = UUID(contact_id)
    for entity_type in ("crm_contact", "contact"):
        db.add(
            DocumentLink(
                document_id=document.id,
                entity_type=entity_type,
                entity_id=uid,
                relationship_type="bitrix_source",
            )
        )
    db.flush()
    return "yes", str(document.id), ""


def sample_names(contacts: dict[str, dict]) -> list[tuple[str, str]]:
    wanted = []
    by_name = {rec["name"].casefold(): rec for rec in contacts.values()}
    for name in SAMPLE_NAMES:
        rec = by_name.get(name.casefold())
        if rec:
            wanted.append((rec["cid"], rec["name"]))
        else:
            wanted.append(("", name))
    extras = [rec for rec in contacts.values() if rec["name"].casefold() not in {n.casefold() for n in SAMPLE_NAMES}]
    extras.sort(key=lambda rec: rec["name"])
    for rec in extras[:5]:
        wanted.append((rec["cid"], rec["name"]))
    return wanted


def main() -> None:
    progress = OUT / "reports" / "link_progress.log"
    env = load_env(ENV_PATH)
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    if not raw:
        print("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
        return
    client = BitrixClient(webhook_base(raw))
    admin = client.call("user.admin", {})
    current = client.call("user.current", {})
    user = current.get("result") if isinstance(current.get("result"), dict) else {}
    log(progress, f"ADMIN_USER {user.get('NAME')} {user.get('LAST_NAME')} admin={admin.get('result')}")
    if admin.get("result") is not True:
        log(progress, "REFUSING_NON_ADMIN_WEBHOOK")
        return

    db = SessionLocal()
    try:
        contacts = load_agreement_contacts(db)
        rows = load_manifest_rows()
        assign_ownership(rows, contacts)
        log(progress, f"CONTACTS {len(contacts)} MANIFEST {len(rows)}")

        binaries: dict[tuple[str, str], bytes] = {}
        out_rows: list[dict] = []
        for idx, src in enumerate(rows, start=1):
            cid = (src.get("canonical_contact_id") or src.get("canonical_crm_contact_id") or "").strip()
            rec = contacts.get(cid) or {}
            file_id = str(src.get("bitrix_file_id") or "")
            owned = src.get("ownership_verified") == "yes"
            content = None
            filename = src.get("original_filename") or None
            mime = None
            err = src.get("_own_reason") if not owned else None
            local = ""
            digest = ""
            size = ""
            if owned:
                content, filename, mime, err = recover_binary(client, src)
            if content:
                mime = mime_of(filename, mime, content)
                folder = OUT / "by_contact" / cid
                folder.mkdir(parents=True, exist_ok=True)
                dest = unique_dest(folder, safe_filename(filename, file_id), file_id)
                dest.write_bytes(content)
                digest = hashlib.sha256(content).hexdigest()
                local = str(dest.relative_to(OUT)).replace("\\", "/")
                size = str(len(content))
                binaries[(cid, file_id)] = content
            out_rows.append(
                {
                    "canonical_crm_contact_id": cid,
                    "person_name": rec.get("name") or src.get("person_name") or "",
                    "agreement_id": rec.get("agreement_id") or src.get("agreement_id") or "",
                    "project_group": rec.get("project_group") or src.get("project_group") or "",
                    "bitrix_entity_type": src.get("bitrix_entity_type") or "",
                    "bitrix_entity_id": src.get("bitrix_entity_id") or "",
                    "source_type": src.get("source_type") or "",
                    "source_record_id": src.get("source_record_id") or "",
                    "bitrix_file_id": file_id,
                    "original_filename": filename or "",
                    "mime_type": mime or "",
                    "file_size": size,
                    "downloaded": "yes" if content else "no",
                    "local_archive_path": local,
                    "sha256": digest,
                    "ownership_verified": src.get("ownership_verified") or "no",
                    "ownership_method": src.get("ownership_method") or "",
                    "crm_imported": "no",
                    "crm_document_id": "",
                    "failure_reason": err or ("" if content else "not_downloaded"),
                    "_datetime": src.get("datetime") or src.get("date/time") or "",
                }
            )
            if idx % 10 == 0 or content:
                log(progress, f"FILE {idx}/{len(rows)} downloaded={'yes' if content else 'no'} owned={src.get('ownership_verified')}")

        downloaded = [r for r in out_rows if r["downloaded"] == "yes"]
        inaccessible = [r for r in out_rows if r["downloaded"] != "yes"]
        deterministic = [r for r in out_rows if r["ownership_verified"] == "yes"]
        ambiguous = [r for r in out_rows if r["ownership_verified"] != "yes"]
        to_link = [r for r in downloaded if r["ownership_verified"] == "yes"]

        actor = db.scalars(select(User).limit(1)).first()
        already = 0
        for row in to_link:
            if actor and existing_document(db, import_tag(row["canonical_crm_contact_id"], row["bitrix_file_id"])):
                already += 1
        dry = {
            "downloaded_files": len(downloaded),
            "files_with_deterministic_canonical_owner": len(deterministic),
            "files_without_deterministic_owner": len(ambiguous),
            "files_already_linked_to_crm": already,
            "files_that_would_be_newly_linked": max(0, len(to_link) - already),
            "duplicate_file_links_skipped": already,
            "conflicts": [r["failure_reason"] for r in ambiguous if r.get("failure_reason")],
        }
        log(progress, f"DRY_RUN {json.dumps(dry)}")

        linked = 0
        skipped_dup = 0
        import_errors = []
        if actor is None:
            import_errors.append("no_actor_user")
        else:
            for row in to_link:
                key = (row["canonical_crm_contact_id"], row["bitrix_file_id"])
                content = binaries.get(key)
                if not content:
                    continue
                row["datetime"] = row.get("_datetime")
                status, doc_id, reason = import_document(db, actor, row, content, row["local_archive_path"])
                row["crm_document_id"] = doc_id or ""
                if status == "yes":
                    row["crm_imported"] = "yes"
                    row["failure_reason"] = ""
                    linked += 1
                elif status == "skipped_duplicate":
                    row["crm_imported"] = "skipped_duplicate"
                    skipped_dup += 1
                    row["failure_reason"] = ""
                else:
                    row["crm_imported"] = "no"
                    row["failure_reason"] = reason
                    import_errors.append(reason)
            db.commit()

        reports = OUT / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        manifest_path = reports / "BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
        with manifest_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in out_rows:
                writer.writerow(row)

        crm_count = db.execute(
            text(
                """
                select count(distinct d.id)
                from documents d
                join document_links l on l.document_id = d.id
                where d.tags like 'bitrix:%'
                  and l.entity_type in ('crm_contact', 'contact')
                """
            )
        ).scalar()

        samples = []
        for cid, name in sample_names(contacts):
            if not cid:
                samples.append({"person": name, "in_agreement_set": False, "match": "not_in_target_population"})
                continue
            person_rows = [r for r in out_rows if r["canonical_crm_contact_id"] == cid]
            linked_rows = [r for r in person_rows if r["crm_imported"] in {"yes", "skipped_duplicate"}]
            crm_owners = db.execute(
                text(
                    """
                    select distinct l.entity_id::text
                    from documents d
                    join document_links l on l.document_id = d.id
                    where d.tags like :prefix
                      and l.entity_type in ('crm_contact', 'contact')
                    """
                ),
                {"prefix": f"bitrix:%:{cid}"},
            ).scalars().all()
            wrong = [oid for oid in crm_owners if oid != cid]
            samples.append(
                {
                    "person": name,
                    "canonical_crm_contact_id": cid,
                    "archive_rows": len(person_rows),
                    "downloaded": sum(1 for r in person_rows if r["downloaded"] == "yes"),
                    "crm_linked": len(linked_rows),
                    "crm_owners": crm_owners,
                    "bitrix_entities": sorted({(r["bitrix_entity_type"], r["bitrix_entity_id"]) for r in person_rows}),
                    "ownership_match": (not wrong) and all(r["canonical_crm_contact_id"] == cid for r in person_rows),
                }
            )

        summary = {
            "agreement_contacts_checked": len(contacts),
            "total_file_references": len(out_rows),
            "files_downloaded": len(downloaded),
            "files_inaccessible": len(inaccessible),
            "deterministic_ownership_matches": len(deterministic),
            "ambiguous_ownership_rows": len(ambiguous),
            "dry_run_files_to_link": len(to_link),
            "files_linked_to_crm": linked,
            "duplicate_links_skipped": skipped_dup,
            "sample_ownership_verification": samples,
            "crm_document_count_after_import": int(crm_count or 0),
            "archive_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/",
            "manifest_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports/BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv",
            "conflicts_errors": sorted(set(import_errors + [r["failure_reason"] for r in ambiguous if r.get("failure_reason")]))[:40],
            "dry_run": dry,
            "bitrix_calls": client.call_count,
            "generated_at": utc_now(),
        }
        (reports / "BITRIX_AGREEMENT_FILES_LINK_SUMMARY.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
