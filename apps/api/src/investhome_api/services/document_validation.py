"""File validation helpers for document uploads.

Do not trust filename extension, browser Content-Type, or application/octet-stream.
Type is determined from magic bytes / file signatures, then matched to the extension.
"""

from __future__ import annotations

import hashlib
import re
import uuid
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

from investhome_api.config.documents_config import (
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    DEFAULT_MAX_UPLOAD_BYTES,
)
from investhome_api.config.settings import get_settings
from investhome_api.services.malware_scan import scan_upload_or_raise

_HTTP_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)

_UNTRUSTED_MIME = frozenset({"", "application/octet-stream", "binary/octet-stream"})

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_ELF_MAGIC = b"\x7fELF"
_MACHO_MAGICS = (
    b"\xca\xfe\xba\xbe",
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
)

_UNSAFE_MARKUP_PREFIXES = (
    b"<!doctype html",
    b"<html",
    b"<svg",
    b"<script",
)

_BLOCKED_ARCHIVE_SUFFIXES = (
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".com",
    ".js",
    ".vbs",
    ".ps1",
    ".scr",
    ".msi",
    ".html",
    ".htm",
    ".svg",
    ".php",
    ".jar",
)

_OFFICE_KIND_PREFIXES = (
    ("docx", "word/"),
    ("xlsx", "xl/"),
    ("pptx", "ppt/"),
)

_TEXT_EXTENSIONS = frozenset({"txt", "csv", "dxf"})
_OLE_EXTENSIONS = frozenset({"doc", "xls", "ppt"})
_JPEG_EXTENSIONS = frozenset({"jpg", "jpeg"})
_MP4_EXTENSIONS = frozenset({"mp4", "mov"})

_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\- ()]", re.UNICODE)


def sanitize_filename(name: str) -> str:
    """Return a safe display filename. Never use the result as a filesystem path."""
    raw = (name or "").replace("\x00", "")
    base = raw.replace("\\", "/").split("/")[-1]
    if ":" in base:
        base = base.split(":")[0]
    base = base.strip(" .")
    if not base or base in {".", ".."}:
        return "upload"
    base = base.replace("..", "_")
    base = _UNSAFE_FILENAME_CHARS.sub("_", base)
    return (base[:255] if base else "upload")


def extract_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return ""
    return parts[-1].lower()


def validate_extension(ext: str) -> None:
    if not ext:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.missing_extension")
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.unsupported_type")


def _normalize_declared_mime(mime_type: str | None) -> str:
    return (mime_type or "").split(";")[0].strip().lower()


def validate_mime_type(ext: str, mime_type: str | None) -> str:
    """Match declared MIME to extension. octet-stream / empty is ignored, not trusted."""
    allowed = ALLOWED_EXTENSIONS.get(ext, ())
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.unsupported_type")
    normalized = _normalize_declared_mime(mime_type)
    if normalized in _UNTRUSTED_MIME:
        return allowed[0]
    if normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.mime_mismatch")
    return allowed[0]


def _head(content: bytes, size: int = 512) -> bytes:
    return content[:size]


def _looks_like_executable(content: bytes) -> bool:
    head = _head(content, 8)
    if head.startswith(b"MZ") or head.startswith(_ELF_MAGIC):
        return True
    if any(head.startswith(magic) for magic in _MACHO_MAGICS):
        return True
    stripped = content.lstrip()[:16].lower()
    return stripped.startswith(b"#!") or stripped.startswith(b"<?php") or stripped.startswith(b"<%")


def _looks_like_markup(content: bytes) -> bool:
    head = content.lstrip(b"\xef\xbb\xbf \t\r\n")[:256].lower()
    return any(head.startswith(prefix) for prefix in _UNSAFE_MARKUP_PREFIXES)


def _looks_like_text(content: bytes) -> bool:
    if not content:
        return False
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    control = sum(1 for byte in sample if byte < 9 or 14 <= byte <= 31)
    return (control / max(len(sample), 1)) < 0.30


def _zip_names(content: bytes) -> list[str] | None:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return None
    normalized: list[str] = []
    for raw in names:
        path = raw.replace("\\", "/")
        if path.startswith("/") or any(part == ".." for part in path.split("/")):
            return None
        normalized.append(path)
    return normalized


def _archive_has_blocked_members(names: list[str]) -> bool:
    for name in names:
        lower = name.lower()
        if any(lower.endswith(suffix) for suffix in _BLOCKED_ARCHIVE_SUFFIXES):
            return True
    return False


def _office_kind_from_zip(names: list[str]) -> str | None:
    lower = [name.lower() for name in names]
    matched = [kind for kind, prefix in _OFFICE_KIND_PREFIXES if any(n.startswith(prefix) for n in lower)]
    if len(matched) > 1:
        return None
    if len(matched) == 1:
        return matched[0]
    return "zip"


def sniff_content_kind(content: bytes) -> str:
    """Return a sniffed kind key, or raise HTTPException for blocked/unknown content."""
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.empty_file")
    if _looks_like_executable(content):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")
    if _looks_like_markup(content):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")

    head = _head(content, 16)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(_JPEG_MAGIC):
        return "jpeg"
    if head.startswith(_PNG_MAGIC):
        return "png"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    if head.startswith(_OLE_MAGIC):
        return "ole"
    if head.startswith(b"AC10"):
        return "dwg"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return "mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    if any(head.startswith(magic) for magic in _ZIP_MAGICS):
        names = _zip_names(content)
        if names is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="documents.errors.content_mismatch",
            )
        if not names or _archive_has_blocked_members(names):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")
        kind = _office_kind_from_zip(names)
        if kind is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")
        return kind
    if _looks_like_text(content):
        return "text"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.unknown_type")


def _kind_matches_extension(kind: str, ext: str) -> bool:
    if kind == "pdf":
        return ext == "pdf"
    if kind == "jpeg":
        return ext in _JPEG_EXTENSIONS
    if kind == "png":
        return ext == "png"
    if kind == "gif":
        return ext == "gif"
    if kind == "webp":
        return ext == "webp"
    if kind == "docx":
        return ext == "docx"
    if kind == "xlsx":
        return ext == "xlsx"
    if kind == "pptx":
        return ext == "pptx"
    if kind == "zip":
        return ext == "zip"
    if kind == "ole":
        return ext in _OLE_EXTENSIONS
    if kind == "dwg":
        return ext == "dwg"
    if kind == "mp4":
        return ext in _MP4_EXTENSIONS
    if kind == "webm":
        return ext == "webm"
    if kind == "text":
        return ext in _TEXT_EXTENSIONS
    return False


def _max_upload_bytes() -> int:
    settings = get_settings()
    return settings.document_max_upload_bytes or DEFAULT_MAX_UPLOAD_BYTES


def validate_upload_content(
    content: bytes,
    *,
    filename: str,
    declared_mime: str | None = None,
    max_bytes: int | None = None,
) -> tuple[bytes, str, str, str, int]:
    """Validate bytes, extension, declared MIME, and magic. Returns content, ext, mime, name, size."""
    limit = max_bytes if max_bytes is not None else _max_upload_bytes()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.empty_file")
    if len(content) > limit:
        raise HTTPException(
            status_code=_HTTP_413,
            detail="documents.errors.file_too_large",
        )

    original_name = sanitize_filename(filename)
    ext = extract_extension(original_name)
    validate_extension(ext)
    mime_type = validate_mime_type(ext, declared_mime)
    kind = sniff_content_kind(content)
    if not _kind_matches_extension(kind, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="documents.errors.content_mismatch",
        )
    scan_upload_or_raise(content, filename=original_name)
    return content, ext, mime_type, original_name, len(content)


async def read_bytes_capped(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Read an upload, rejecting oversized payloads before the full body is buffered past the limit."""
    limit = max_bytes if max_bytes is not None else _max_upload_bytes()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=_HTTP_413,
                detail="documents.errors.file_too_large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def read_and_validate_upload(file: UploadFile) -> tuple[bytes, str, str, str, int]:
    """Read upload, validate size/type via magic bytes, return (content, ext, mime, original_name, size)."""
    content = await read_bytes_capped(file)
    return validate_upload_content(
        content,
        filename=file.filename or "upload",
        declared_mime=file.content_type,
    )


async def read_and_validate_csv_import(file: UploadFile) -> str:
    """CSV/text imports: size cap, reject executables/HTML, decode as UTF-8."""
    content = await read_bytes_capped(file)
    original_name = sanitize_filename(file.filename or "upload.csv")
    ext = extract_extension(original_name) or "csv"
    if ext not in {"csv", "txt"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.unsupported_type")
    if _looks_like_executable(content) or _looks_like_markup(content) or not _looks_like_text(content):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.blocked_type")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="documents.errors.unsupported_type",
        ) from exc


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def generate_storage_key(ext: str) -> tuple[str, str]:
    """Return (stored_file_name, storage_key) with safe unique names. Never uses the upload filename."""
    now = datetime.now(UTC)
    unique = uuid.uuid4().hex
    stored_name = f"{unique}.{ext}"
    storage_key = f"{now.year:04d}/{now.month:02d}/{stored_name}"
    return stored_name, storage_key


def content_stream(content: bytes) -> BinaryIO:
    return BytesIO(content)
