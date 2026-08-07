"""Text extractors for AI Index — MD/JSON/TXT/DOCX/PDF text layer only. No OCR."""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from typing import Any

import chardet
from docx import Document as DocxDocument
from pypdf import PdfReader

from investhome_api.models.ai_index import AiDocumentType
from investhome_api.services.ai_index.eligibility import extension_of, is_metadata_file, is_readme

MIN_PDF_PAGE_CHARS = 40


@dataclass
class ExtractResult:
    text: str
    document_type: str
    method: str
    structured: dict[str, Any] | None = None
    skipped: bool = False
    skip_reason: str | None = None


def detect_document_type(filename: str) -> str:
    if is_readme(filename):
        return AiDocumentType.README.value
    if is_metadata_file(filename):
        return AiDocumentType.METADATA.value
    ext = extension_of(filename)
    mapping = {
        "md": AiDocumentType.MD.value,
        "txt": AiDocumentType.TXT.value,
        "json": AiDocumentType.JSON.value,
        "docx": AiDocumentType.DOCX.value,
        "pdf": AiDocumentType.PDF.value,
    }
    return mapping.get(ext, AiDocumentType.UNSUPPORTED.value)


def extract_bytes(content: bytes, filename: str) -> ExtractResult:
    """Extract text from bytes. Unsupported formats are skipped gracefully."""
    doc_type = detect_document_type(filename)
    ext = extension_of(filename)

    if doc_type == AiDocumentType.UNSUPPORTED.value and ext not in {
        "md",
        "txt",
        "json",
        "docx",
        "pdf",
    }:
        return ExtractResult(
            text="",
            document_type=AiDocumentType.UNSUPPORTED.value,
            method="unsupported",
            skipped=True,
            skip_reason=f"unsupported_format:{ext or 'unknown'}",
        )

    if doc_type in {AiDocumentType.README.value, AiDocumentType.MD.value} or ext == "md":
        text = _decode_text(content)
        return ExtractResult(text=text, document_type=doc_type, method="markdown")

    if doc_type == AiDocumentType.METADATA.value or ext == "json":
        return _extract_json(content, document_type=doc_type)

    if ext == "txt" or doc_type == AiDocumentType.TXT.value:
        return ExtractResult(text=_decode_text(content), document_type=AiDocumentType.TXT.value, method="txt")

    if ext == "docx":
        return _extract_docx(content)

    if ext == "pdf":
        return _extract_pdf(content)

    return ExtractResult(
        text="",
        document_type=AiDocumentType.UNSUPPORTED.value,
        method="unsupported",
        skipped=True,
        skip_reason=f"unsupported_format:{ext or 'unknown'}",
    )


def _decode_text(content: bytes, *, limit: int = 500_000) -> str:
    detected = chardet.detect(content[:10000]) if content else {}
    encoding = detected.get("encoding") or "utf-8"
    return content.decode(encoding, errors="replace")[:limit]


def _extract_json(content: bytes, *, document_type: str) -> ExtractResult:
    raw = _decode_text(content, limit=1_000_000)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ExtractResult(
            text=raw,
            document_type=document_type,
            method="json_raw",
            structured=None,
        )
    if isinstance(data, dict):
        lines = [f"{key}: {_stringify_json_value(value)}" for key, value in data.items()]
        text = "\n".join(lines)
        return ExtractResult(
            text=text,
            document_type=document_type,
            method="json_structured",
            structured=data,
        )
    return ExtractResult(
        text=json.dumps(data, ensure_ascii=False, indent=2)[:500_000],
        document_type=document_type,
        method="json_value",
        structured={"value": data} if not isinstance(data, dict) else data,
    )


def _stringify_json_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _extract_docx(content: bytes) -> ExtractResult:
    doc = DocxDocument(io.BytesIO(content))
    parts: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return ExtractResult(
        text="\n".join(parts),
        document_type=AiDocumentType.DOCX.value,
        method="docx",
    )


def _extract_pdf(content: bytes) -> ExtractResult:
    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        # No OCR — keep text layer only (empty pages stay empty)
        if len(re.sub(r"\s+", "", text)) >= MIN_PDF_PAGE_CHARS or text:
            pages.append(text)
    return ExtractResult(
        text="\n\n".join(pages),
        document_type=AiDocumentType.PDF.value,
        method="pdf_text_layer",
    )
