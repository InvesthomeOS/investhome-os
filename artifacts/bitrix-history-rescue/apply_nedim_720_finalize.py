"""Scoped Nedim/İzzet Uniloft 403 metadata + document filename cleanup. Does not touch other customers."""
from __future__ import annotations

import json
import re
import urllib.parse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document

NEDIM = UUID("811c6aed-5f58-4c89-a9b1-0eebed64b9cf")
IZZET = UUID("339559ed-0d11-4e7c-a021-a07b388a817b")
AGREEMENT_720 = UUID("444f6517-595a-4067-9c0c-3521708d2223")
FILE_IDS = {"96546", "96552", "96548", "96748", "96750", "96752", "96754", "96554"}
FILENAME_STAR = re.compile(r"filename\*=(?:UTF-8''|utf-8'')([^;]+)", re.I)


def decode_filename(raw: str | None) -> str | None:
    text = str(raw or "")
    match = FILENAME_STAR.search(text)
    if not match:
        return None
    decoded = urllib.parse.unquote(match.group(1)).strip()
    return decoded or None


def merge_live(row: CrmContact | CrmAgreement, payload: dict) -> None:
    meta = dict(row.metadata_json or {}) if isinstance(row.metadata_json, dict) else {}
    live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
    live.update(payload)
    meta["bitrix_live"] = live
    row.metadata_json = meta
    flag_modified(row, "metadata_json")


def main() -> None:
    db = SessionLocal()
    try:
        nedim = db.get(CrmContact, NEDIM)
        izzet = db.get(CrmContact, IZZET)
        agreement = db.get(CrmAgreement, AGREEMENT_720)
        if nedim is None or izzet is None or agreement is None:
            raise SystemExit("missing locked entities")
        merge_live(
            nedim,
            {
                "contact_id": "588",
                "assigned_by_id": "1",
                "assigned_name": "Erman Devay",
                "source_id": "UC_37VR5B",
                "source_name": "Acenta Müşterisi",
            },
        )
        merge_live(
            izzet,
            {
                "contact_id": "1160",
                "assigned_by_id": "92",
                "assigned_name": "Beyza Karakuş",
                "source_id": "UC_LPEQFO",
                "source_name": "Genel",
            },
        )
        merge_live(
            agreement,
            {
                "bitrix_deal_id": "720",
                "purchase_card_verified": True,
                "opportunity": "470000.00",
                "currency": "USD",
                "stage_id": "C26:FINAL_INVOICE",
                "stage_label": "Ev Teslim Süreci",
                "begin_date": "2026-03-17",
                "close_date": "2026-03-24",
                "assigned_by_id": "92",
                "assigned_name": "Beyza Karakuş",
                "comments": "Nedim Bey ve İzzet Bey Uniloft daire 403'ü erken teslim kampanyası peşin alım ile $470.000'a %50 %50 hisseli alım yaptılar.",
            },
        )
        renamed = 0
        for document in db.scalars(select(Document).where(Document.notes.is_not(None))).all():
            notes = {}
            if document.notes:
                try:
                    parsed = json.loads(document.notes)
                    notes = parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    continue
            if str(notes.get("bitrix_file_id") or "") not in FILE_IDS:
                continue
            if str(notes.get("bitrix_entity_id") or "") != "720":
                continue
            decoded = decode_filename(document.original_file_name) or decode_filename(document.title)
            if not decoded:
                continue
            document.title = decoded[:500]
            document.original_file_name = decoded[:500]
            renamed += 1
        db.commit()
        print(f"updated_nedim_izzet_720 renamed_docs={renamed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
