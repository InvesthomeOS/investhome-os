"""Recover 9 live Bitrix UF files on Lale B08 deal 116. Bitrix is read-only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.documents_config import ALLOWED_EXTENSIONS, infer_file_kind
from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    DocumentVisibility,
    DocumentWorkspaceFolder,
    ProcessingStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.agreement_service import get_purchase_card
from investhome_api.services.document_service import create_document_analysis
from investhome_api.services.document_validation import compute_checksum, generate_storage_key
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

OUT = Path("/tmp/LALE_B08_DOCUMENTS")
CANONICAL = UUID("0f966583-13c5-4ca4-a90b-2763383973ae")
B08_ID = UUID("fadfc360-2900-4673-80d0-ffdc88b6763a")
DEAL_ID = "116"
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
HTML_HEAD = re.compile(br"^\s*<(!doctype|html|head|script|body)\b", re.I)
KNOWN_IDS = [
    "42558",
    "42560",
    "42562",
    "42798",
    "42800",
    "42802",
    "42804",
    "42806",
    "42808",
]
TYPE_MAP = {
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


def webhook_base(raw: str) -> str:
    value = (raw or "").strip().strip('"').strip("'")
    marker = "BURAYA_BITRIX_URL="
    if marker in value:
        value = value.split(marker, 1)[1].strip()
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
        last_error = "unknown"
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
                time.sleep(min(20, 2**attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            parsed["error_description"] = redact(str(parsed.get("error_description") or ""), self.base)
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                time.sleep(min(30, 2 ** (attempt + 1)))
                last_error = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last_error}

    def download(self, url: str) -> tuple[bytes | None, str | None, str | None, str | None]:
        if not url:
            return None, None, None, "no_url"
        if url.startswith("/"):
            url = self.origin + url
        last_err = "download_failed"
        candidates = [url]
        auth_url = with_auth(self, url)
        if auth_url != url:
            candidates.append(auth_url)
        for candidate in candidates:
            self._wait()
            self.call_count += 1
            req = urllib.request.Request(candidate, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    disp = resp.headers.get("Content-Disposition") or ""
                    data = resp.read()
                self._last = time.time()
            except urllib.error.HTTPError as exc:
                self._last = time.time()
                last_err = f"HTTP {exc.code}"
                continue
            except Exception as exc:  # noqa: BLE001
                last_err = redact(str(exc), self.base)[:160]
                continue
            if not data:
                last_err = "empty_body"
                continue
            if HTML_HEAD.search(data[:200]) or "text/html" in (ctype or ""):
                last_err = "html_login_or_error_page"
                continue
            if data.lstrip()[:1] == b"{" and b'"error"' in data[:400]:
                last_err = "json_error_body"
                continue
            fname = None
            match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disp, re.I)
            if match:
                fname = urllib.parse.unquote(match.group(1).strip())
            return data, ctype, fname, None
        return None, None, None, last_err


def with_auth(client: BitrixClient, url: str) -> str:
    token = webhook_token(client.base)
    if not token:
        return url
    if url.startswith("/"):
        url = client.origin + url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if not query.get("auth") or query.get("auth") == [""]:
        query["auth"] = [token]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))


def notes_of(document: Document | None) -> dict[str, Any]:
    raw = document.notes if document is not None else None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def collect_file_nodes(value: Any, field: str, acc: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, dict) and (value.get("id") or value.get("ID") or value.get("fileId")):
        fid = str(value.get("id") or value.get("ID") or value.get("fileId") or "")
        if fid.isdigit():
            node = acc.setdefault(fid, {"id": fid, "fields": []})
            if field not in node["fields"]:
                node["fields"].append(field)
            node["node"] = value
            name = value.get("name") or value.get("NAME") or value.get("fileName")
            if name:
                node["name"] = name
            size = value.get("size") or value.get("SIZE") or value.get("fileSize")
            if size:
                node["size"] = size
            mime = value.get("type") or value.get("contentType") or value.get("CONTENT_TYPE")
            if mime:
                node["mime"] = mime
    elif isinstance(value, list):
        for item in value:
            collect_file_nodes(item, field, acc)
    elif isinstance(value, (str, int)) and str(value).isdigit() and len(str(value)) >= 4:
        fid = str(value)
        node = acc.setdefault(fid, {"id": fid, "fields": []})
        if field not in node["fields"]:
            node["fields"].append(field)


def mime_of(filename: str | None, detected: str | None, content: bytes | None) -> str:
    if detected and detected not in {"application/octet-stream", "binary/octet-stream"} and "html" not in (detected or ""):
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
        if ext == "jpeg":
            return "jpg"
    for ext, mimes in ALLOWED_EXTENSIONS.items():
        if mime in mimes:
            return ext
    if content_ext := {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}.get(mime):
        return content_ext
    return ""


def safe_filename(name: str | None, file_id: str) -> str:
    raw = (name or "").strip() or f"bitrix-file-{file_id}"
    raw = raw.replace("\\", "_").replace("/", "_").replace("\x00", "")
    raw = re.sub(r"[^\w.\- ()]+", "_", raw).strip(" .")
    return (raw or f"bitrix-file-{file_id}")[:180]


def existing_for_file(db: Session, file_id: str) -> Document | None:
    rows = list(
        db.scalars(select(Document).where(Document.notes.is_not(None), Document.notes.ilike(f"%{file_id}%"))).all()
    )
    for document in rows:
        if str(notes_of(document).get("bitrix_file_id") or "") == file_id:
            return document
    return None


def link_agreement(db: Session, document_id: UUID, agreement_id: UUID) -> bool:
    exists = db.scalar(
        select(DocumentLink.id).where(
            DocumentLink.document_id == document_id,
            DocumentLink.entity_type == "crm_agreement",
            DocumentLink.entity_id == agreement_id,
        )
    )
    if exists:
        return False
    db.add(
        DocumentLink(
            document_id=document_id,
            entity_type="crm_agreement",
            entity_id=agreement_id,
            relationship_type="bitrix_deal_file",
        )
    )
    return True


def link_contact(db: Session, document_id: UUID, contact_id: UUID) -> None:
    for entity_type in ("crm_contact", "contact"):
        exists = db.scalar(
            select(DocumentLink.id).where(
                DocumentLink.document_id == document_id,
                DocumentLink.entity_type == entity_type,
                DocumentLink.entity_id == contact_id,
            )
        )
        if exists:
            continue
        db.add(
            DocumentLink(
                document_id=document_id,
                entity_type=entity_type,
                entity_id=contact_id,
                relationship_type="bitrix_source",
            )
        )


def user_label(client: BitrixClient, user_id: str | None) -> str | None:
    if not user_id or not str(user_id).isdigit():
        return None
    body = client.call("user.get", {"ID": user_id})
    rows = body.get("result") if isinstance(body.get("result"), list) else []
    if not rows:
        return f"Bitrix user {user_id}"
    row = rows[0] if isinstance(rows[0], dict) else {}
    name = " ".join(str(part) for part in (row.get("NAME"), row.get("LAST_NAME")) if part).strip()
    email = str(row.get("EMAIL") or "").strip()
    return " · ".join(item for item in (name or None, email or None, f"user {user_id}") if item)


def try_disk(client: BitrixClient, file_id: str) -> dict[str, Any]:
    info: dict[str, Any] = {"methods": {}}
    for method, payload in (
        ("disk.file.get", {"id": file_id}),
        ("disk.attachedObject.get", {"id": file_id}),
        ("im.disk.file.get", {"id": file_id}),
    ):
        body = client.call(method, payload)
        result = body.get("result") if not body.get("error") else None
        info["methods"][method] = {
            "error": body.get("error"),
            "error_description": body.get("error_description"),
            "ok": isinstance(result, dict),
        }
        if not isinstance(result, dict):
            continue
        info["name"] = result.get("NAME") or result.get("name") or info.get("name")
        info["size"] = result.get("SIZE") or result.get("size") or info.get("size")
        info["type"] = result.get("TYPE") or result.get("type") or info.get("type")
        info["created_by"] = str(result.get("CREATED_BY") or result.get("createdBy") or "") or info.get("created_by")
        inner = result.get("FILE") if isinstance(result.get("FILE"), dict) else {}
        urls = [
            result.get("DOWNLOAD_URL") or result.get("downloadUrl") or "",
            inner.get("DOWNLOAD_URL") or inner.get("downloadUrl") or "",
        ]
        for url in urls:
            content, mime, fname, err = client.download(str(url) if url else "")
            if content:
                info["content"] = content
                info["mime"] = mime
                info["name"] = fname or info.get("name")
                info["download_via"] = method
                return info
            info["methods"][method]["download_error"] = err
    return info


def recover_one(
    client: BitrixClient,
    file_id: str,
    field: str,
    node: dict[str, Any],
    assigned_id: str | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "bitrix_file_id": file_id,
        "source_field": field,
        "original_filename": node.get("name"),
        "type": node.get("mime") or node.get("type"),
        "size": node.get("size"),
        "download_url_status": None,
        "access_status": "pending",
        "required_bitrix_user": None,
        "reason": None,
        "sha256": None,
        "local_archive_path": None,
        "crm_document_id": None,
        "reused_existing": False,
        "recovered": False,
    }
    reasons: list[str] = []
    content = None
    mime = None
    fname = node.get("name")

    live_node = node.get("node") if isinstance(node.get("node"), dict) else {}
    for url_key in ("urlMachine", "urlDownload", "DOWNLOAD_URL", "downloadUrl", "url"):
        url = str(live_node.get(url_key) or "")
        if not url:
            continue
        data, detected, downloaded_name, err = client.download(url)
        row["download_url_status"] = "ok" if data else redact(err or f"{url_key}_failed", client.base)
        if data:
            content, mime, fname = data, detected, downloaded_name or fname
            row["access_status"] = f"downloaded_via_crm.item.{url_key}"
            break
        reasons.append(f"{url_key}:{err}")

    disk = try_disk(client, file_id)
    row["original_filename"] = fname or disk.get("name") or row["original_filename"]
    row["type"] = mime or disk.get("type") or row["type"]
    row["size"] = disk.get("size") or row["size"]
    if not content and disk.get("content"):
        content = disk["content"]
        mime = disk.get("mime") or mime
        fname = disk.get("name") or fname
        row["access_status"] = f"downloaded_via_{disk.get('download_via')}"
        row["download_url_status"] = "ok"
    else:
        for method, payload in (disk.get("methods") or {}).items():
            if payload.get("error"):
                reasons.append(f"{method}:{payload.get('error')}:{payload.get('error_description') or ''}".strip(":"))
            elif payload.get("download_error"):
                reasons.append(f"{method}:{payload.get('download_error')}")

    show_urls = [
        f"{client.origin}/bitrix/tools/crm_show_file.php?fileId={file_id}&ownerTypeId=2&ownerId={DEAL_ID}",
        f"{client.origin}/bitrix/components/bitrix/crm.field.file/show_file.php?ownerId={DEAL_ID}&ownerType=DEAL&fileId={file_id}",
        f"{client.origin}/bitrix/tools/disk/uf.php?attachedId={file_id}",
    ]
    if not content:
        for url in show_urls:
            data, detected, downloaded_name, err = client.download(url)
            if data:
                content, mime, fname = data, detected, downloaded_name or fname
                row["access_status"] = "downloaded_via_crm_show_file"
                row["download_url_status"] = "ok"
                break
            reasons.append(f"show_file:{err}")

    if content:
        row["original_filename"] = fname or row["original_filename"] or f"bitrix-file-{file_id}"
        row["type"] = mime_of(row["original_filename"], mime, content)
        row["size"] = len(content)
        row["content"] = content
        row["recovered"] = True
        return row

    created_by = disk.get("created_by")
    required = user_label(client, created_by) or user_label(client, assigned_id)
    row["access_status"] = "inaccessible"
    row["required_bitrix_user"] = required
    row["reason"] = "; ".join(dict.fromkeys(r for r in reasons if r))[:500] or "authorized_webhook_cannot_read_file"
    if not row["download_url_status"]:
        row["download_url_status"] = "no_usable_url"
    return row


def import_or_reuse(
    db: Session,
    actor: User,
    file_id: str,
    filename: str,
    mime: str,
    content: bytes,
    field: str,
    archive_path: str,
    checksum: str,
) -> tuple[Document, bool]:
    existing = existing_for_file(db, file_id)
    if existing is not None:
        notes = notes_of(existing)
        notes.update(
            {
                "source": "bitrix_live",
                "bitrix_file_id": file_id,
                "bitrix_entity_type": "deal",
                "bitrix_entity_id": DEAL_ID,
                "source_type": "deal_uf",
                "source_record_id": field,
                "archive_path": archive_path,
                "sha256": checksum,
                "import_key": f"bitrix_deal:{DEAL_ID}:file:{file_id}",
            }
        )
        existing.notes = json.dumps(notes, ensure_ascii=False)
        return existing, True

    ext = ext_of(filename, mime)
    if not ext:
        if content.startswith(b"%PDF"):
            ext = "pdf"
            filename = filename if filename.lower().endswith(".pdf") else f"{filename}.pdf"
            mime = "application/pdf"
        elif content[:3] == b"\xff\xd8\xff":
            ext = "jpg"
            filename = filename if filename.lower().endswith((".jpg", ".jpeg")) else f"{filename}.jpg"
            mime = "image/jpeg"
        elif content.startswith(b"\x89PNG"):
            ext = "png"
            filename = filename if filename.lower().endswith(".png") else f"{filename}.png"
            mime = "image/png"
        else:
            raise ValueError(f"unsupported_type:{mime}:{filename}")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported_extension:{ext}")
    stored_name, storage_key = generate_storage_key(ext)
    storage = get_storage_provider()
    storage.save(storage_key, BytesIO(content), content_length=len(content))
    notes = json.dumps(
        {
            "source": "bitrix_live",
            "bitrix_file_id": file_id,
            "bitrix_entity_type": "deal",
            "bitrix_entity_id": DEAL_ID,
            "source_type": "deal_uf",
            "source_record_id": field,
            "archive_path": archive_path,
            "sha256": checksum,
            "import_key": f"bitrix_deal:{DEAL_ID}:file:{file_id}",
        },
        ensure_ascii=False,
    )
    document = Document(
        title=(filename.rsplit(".", 1)[0] if "." in filename else filename)[:500],
        original_file_name=filename[:500],
        stored_file_name=stored_name,
        file_extension=ext[:20],
        mime_type=mime[:120],
        file_size=len(content),
        storage_provider=provider_enum(),
        storage_key=storage_key,
        checksum=checksum,
        document_type=TYPE_MAP.get(ext, DocumentType.OTHER),
        category="bitrix",
        folder=DocumentWorkspaceFolder.CONTRACTS,
        file_kind=infer_file_kind(ext),
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.ORGANIZATION,
        confidentiality_level=ConfidentialityLevel.INTERNAL,
        version_number=1,
        uploaded_by_user_id=actor.id,
        owner_user_id=actor.id,
        description=f"Bitrix deal {DEAL_ID} UF file {file_id}",
        notes=notes,
        tags=f"bitrix_file:{file_id}"[:1000],
        is_latest_version=True,
        processing_status=ProcessingStatus.UPLOADED,
    )
    db.add(document)
    db.flush()
    create_document_analysis(db, document.id)
    return document, False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "binaries").mkdir(parents=True, exist_ok=True)
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    if not raw:
        raise SystemExit("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
    client = BitrixClient(webhook_base(raw))
    admin = client.call("user.admin", {})
    current = client.call("user.current", {})
    user = current.get("result") if isinstance(current.get("result"), dict) else {}
    webhook_user = " ".join(str(part) for part in (user.get("NAME"), user.get("LAST_NAME")) if part).strip()
    report: dict[str, Any] = {
        "scope": "Lale Şenyol · 1812 H Place B08 · Bitrix deal 116",
        "bitrix_modified": False,
        "webhook_user": webhook_user,
        "webhook_admin": admin.get("result"),
        "files": [],
    }
    db = SessionLocal()
    try:
        agreement = db.get(CrmAgreement, B08_ID)
        if agreement is None:
            raise RuntimeError("B08 agreement missing")
        actor = db.scalar(select(User).order_by(User.created_at.asc()))
        if actor is None:
            raise RuntimeError("no actor user")

        existing_before = []
        for link in db.scalars(
            select(DocumentLink).where(
                DocumentLink.entity_type == "crm_agreement",
                DocumentLink.entity_id == B08_ID,
            )
        ).all():
            document = db.get(Document, link.document_id)
            notes = notes_of(document)
            existing_before.append(
                {
                    "id": str(document.id) if document else None,
                    "filename": document.original_file_name if document else None,
                    "bitrix_file_id": notes.get("bitrix_file_id"),
                    "source_type": notes.get("source_type") or notes.get("source"),
                }
            )
        report["existing_b08_documents_before"] = existing_before

        deal = client.call("crm.deal.get", {"id": DEAL_ID}).get("result") or {}
        fields = client.call("crm.deal.fields", {}).get("result") or {}
        item_body = client.call("crm.item.get", {"entityTypeId": 2, "id": DEAL_ID})
        item = (item_body.get("result") or {}).get("item") if isinstance(item_body.get("result"), dict) else {}
        assigned_id = str(deal.get("ASSIGNED_BY_ID") or item.get("assignedById") or "")
        assigned_name = user_label(client, assigned_id)
        report["deal"] = {
            "id": str(deal.get("ID") or DEAL_ID),
            "title": deal.get("TITLE"),
            "assigned_by_id": assigned_id,
            "assigned_name": assigned_name,
            "crm_item_error": item_body.get("error") or item_body.get("error_description"),
        }

        file_fields = {
            key: str((meta or {}).get("formLabel") or (meta or {}).get("title") or (meta or {}).get("listLabel") or key)
            for key, meta in (fields.items() if isinstance(fields, dict) else [])
            if isinstance(meta, dict) and str(meta.get("type") or "").lower() == "file"
        }
        collected: dict[str, dict[str, Any]] = {}
        for key, value in (deal.items() if isinstance(deal, dict) else []):
            if key in file_fields or str(key).startswith("UF_"):
                collect_file_nodes(value, key, collected)
        for key, value in (item.items() if isinstance(item, dict) else []):
            collect_file_nodes(value, key, collected)
        for fid in KNOWN_IDS:
            collected.setdefault(fid, {"id": fid, "fields": []})

        expected_ids = []
        for fid in KNOWN_IDS:
            if fid not in expected_ids:
                expected_ids.append(fid)
        for fid in collected:
            if fid.isdigit() and fid not in expected_ids:
                expected_ids.append(fid)

        recovered = 0
        inaccessible = 0
        reused = 0
        newly_created = 0
        for file_id in expected_ids:
            node = collected.get(file_id) or {"id": file_id, "fields": []}
            field_keys = node.get("fields") or []
            field = field_keys[0] if field_keys else ""
            field_label = file_fields.get(field) or field or "deal UF file"
            row = recover_one(client, file_id, field, node, assigned_id)
            row["source_field_label"] = field_label
            content = row.pop("content", None)
            if content:
                filename = safe_filename(row.get("original_filename"), file_id)
                checksum = hashlib.sha256(content).hexdigest()
                dest = OUT / "binaries" / f"{file_id}__{filename}"
                dest.write_bytes(content)
                rel = str(dest)
                try:
                    document, was_existing = import_or_reuse(
                        db,
                        actor,
                        file_id,
                        filename,
                        row.get("type") or "application/octet-stream",
                        content,
                        field,
                        rel,
                        checksum,
                    )
                except ValueError as exc:
                    row["recovered"] = False
                    row["access_status"] = "downloaded_but_not_imported"
                    row["reason"] = str(exc)
                    inaccessible += 1
                    report["files"].append(row)
                    continue
                link_agreement(db, document.id, B08_ID)
                link_contact(db, document.id, CANONICAL)
                row["sha256"] = checksum
                row["local_archive_path"] = rel
                row["crm_document_id"] = str(document.id)
                row["reused_existing"] = was_existing
                row["original_filename"] = document.original_file_name
                row["type"] = document.mime_type
                row["size"] = document.file_size
                recovered += 1
                if was_existing:
                    reused += 1
                else:
                    newly_created += 1
            else:
                inaccessible += 1
            report["files"].append(row)

        db.commit()
        card = get_purchase_card(db, B08_ID, viewer_contact_id=CANONICAL)
        visible = [
            {
                "id": str(item.id),
                "filename": item.original_file_name or item.title,
                "bitrix_file_id": item.bitrix_file_id,
                "source": item.source,
            }
            for item in (card.documents if card else [])
        ]
        report.update(
            {
                "expected_count": len(expected_ids),
                "expected_file_ids": expected_ids,
                "recovered_count": recovered,
                "newly_created_count": newly_created,
                "reused_existing_count": reused,
                "inaccessible_count": inaccessible,
                "final_visible_unique_document_count": card.document_count if card else len(visible),
                "visible_documents": visible,
                "unresolved": [
                    {
                        "bitrix_file_id": item["bitrix_file_id"],
                        "source_field": item.get("source_field"),
                        "source_field_label": item.get("source_field_label"),
                        "reason": item.get("reason"),
                        "required_bitrix_user": item.get("required_bitrix_user"),
                        "access_status": item.get("access_status"),
                    }
                    for item in report["files"]
                    if not item.get("recovered")
                ],
                "bitrix_calls": client.call_count,
            }
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    (OUT / "reports" / "LALE_B08.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "expected": report.get("expected_count"),
                "recovered": report.get("recovered_count"),
                "visible": report.get("final_visible_unique_document_count"),
                "inaccessible": report.get("inaccessible_count"),
                "unresolved": report.get("unresolved"),
                "files": [
                    {
                        "id": item.get("bitrix_file_id"),
                        "name": item.get("original_filename"),
                        "field": item.get("source_field_label") or item.get("source_field"),
                        "status": item.get("access_status"),
                        "recovered": item.get("recovered"),
                    }
                    for item in report.get("files") or []
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
