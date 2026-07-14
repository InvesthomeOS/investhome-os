"""File validation helpers for document uploads."""

from __future__ import annotations

import hashlib
import re
import uuid
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


def sanitize_filename(name: str) -> str:
    """Return a safe display filename without path components."""
    base = name.replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^\w.\- ()]", "_", base)
    return base[:255] if base else "upload"


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


def validate_mime_type(ext: str, mime_type: str | None) -> str:
    allowed = ALLOWED_EXTENSIONS.get(ext, ())
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.unsupported_type")
    normalized = (mime_type or "application/octet-stream").split(";")[0].strip().lower()
    if normalized not in allowed and normalized != "application/octet-stream":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.mime_mismatch")
    return allowed[0]


async def read_and_validate_upload(file: UploadFile) -> tuple[bytes, str, str, str, int]:
    """Read upload, validate size/type, return (content, ext, mime, original_name, size)."""
    settings = get_settings()
    max_bytes = settings.document_max_upload_bytes or DEFAULT_MAX_UPLOAD_BYTES
    original_name = sanitize_filename(file.filename or "upload")
    ext = extract_extension(original_name)
    validate_extension(ext)
    mime_type = validate_mime_type(ext, file.content_type)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="documents.errors.file_too_large",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.empty_file")

    content = b"".join(chunks)
    return content, ext, mime_type, original_name, total


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def generate_storage_key(ext: str) -> tuple[str, str]:
    """Return (stored_file_name, storage_key) with safe unique names."""
    now = datetime.now(UTC)
    unique = uuid.uuid4().hex
    stored_name = f"{unique}.{ext}"
    storage_key = f"{now.year:04d}/{now.month:02d}/{stored_name}"
    return stored_name, storage_key


def content_stream(content: bytes) -> BinaryIO:
    return BytesIO(content)
