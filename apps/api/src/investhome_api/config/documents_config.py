"""Document engine configuration: allowed types, MIME validation, preview support."""

from __future__ import annotations

from investhome_api.models.document import (
    DocumentFileKind,
    DocumentType,
    DocumentWorkspaceFolder,
    ProcessingStatus,
)
from investhome_api.services.document_intelligence.extraction import is_processable
from investhome_api.services.drawing_intelligence.config import should_process_as_drawing

# Extension -> allowed MIME types (first is preferred for Content-Type responses)
ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    "doc": ("application/msword",),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    "xls": ("application/vnd.ms-excel",),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
    "ppt": ("application/vnd.ms-powerpoint",),
    "csv": ("text/csv", "application/csv", "text/plain"),
    "txt": ("text/plain",),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
    "gif": ("image/gif",),
    "mp4": ("video/mp4",),
    "webm": ("video/webm",),
    "mov": ("video/quicktime", "video/mp4"),
    "dwg": ("application/acad", "image/vnd.dwg"),
    "dxf": ("image/vnd.dxf", "application/dxf", "text/plain"),
    "zip": ("application/zip", "application/x-zip-compressed"),
}

# Extensions safe for inline browser preview
PREVIEWABLE_EXTENSIONS = frozenset({"pdf", "jpg", "jpeg", "png", "webp", "gif", "txt"})

# Blocked extensions (executables and unsafe types)
BLOCKED_EXTENSIONS = frozenset(
    {
        "exe",
        "bat",
        "cmd",
        "com",
        "msi",
        "dll",
        "scr",
        "ps1",
        "vbs",
        "js",
        "jar",
        "app",
        "deb",
        "rpm",
        "sh",
        "bash",
        "php",
        "asp",
        "aspx",
        "html",
        "htm",
        "svg",
        "xml",
    }
)

DEFAULT_MAX_UPLOAD_BYTES = 52_428_800  # 50 MB

# Flat workspace folders (no nesting)
WORKSPACE_FOLDERS = frozenset(folder.value for folder in DocumentWorkspaceFolder)

# Extension -> file kind (workspace type metrics)
EXTENSION_FILE_KIND: dict[str, DocumentFileKind] = {
    "pdf": DocumentFileKind.PDF,
    "jpg": DocumentFileKind.IMAGE,
    "jpeg": DocumentFileKind.IMAGE,
    "png": DocumentFileKind.IMAGE,
    "webp": DocumentFileKind.IMAGE,
    "gif": DocumentFileKind.IMAGE,
    "doc": DocumentFileKind.WORD,
    "docx": DocumentFileKind.WORD,
    "xls": DocumentFileKind.EXCEL,
    "xlsx": DocumentFileKind.EXCEL,
    "csv": DocumentFileKind.EXCEL,
    "ppt": DocumentFileKind.POWERPOINT,
    "pptx": DocumentFileKind.POWERPOINT,
    "mp4": DocumentFileKind.VIDEO,
    "webm": DocumentFileKind.VIDEO,
    "mov": DocumentFileKind.VIDEO,
    "txt": DocumentFileKind.TEXT,
    "zip": DocumentFileKind.ZIP,
}

# File kind -> additive DocumentType when upload leaves business type as OTHER
FILE_KIND_DOCUMENT_TYPE: dict[DocumentFileKind, DocumentType] = {
    DocumentFileKind.PDF: DocumentType.PDF,
    DocumentFileKind.IMAGE: DocumentType.IMAGE,
    DocumentFileKind.WORD: DocumentType.WORD,
    DocumentFileKind.EXCEL: DocumentType.EXCEL,
    DocumentFileKind.POWERPOINT: DocumentType.POWERPOINT,
    DocumentFileKind.VIDEO: DocumentType.VIDEO,
    DocumentFileKind.TEXT: DocumentType.TEXT,
    DocumentFileKind.ZIP: DocumentType.ZIP,
    DocumentFileKind.OTHER: DocumentType.OTHER,
}

# Entity types supported by DocumentLink (generic relations — no module hardcoding)
LINK_ENTITY_TYPES = frozenset(
    {
        "project",
        "investor",
        "lead",
        "contact",
        "crm_contact",
        "transaction",
        "financial_record",
        "user",
        "unit",
        "building",
        "contractor",
        "permit",
        "construction_milestone",
        "campaign",
        "marketing_campaign",
        "marketing_asset",
        "deal",
        "crm_agreement",
        "opportunity",
        "property",
        "task",
        "calendar_event",
        "capital_call",
        "company",
        "crm_company",
        "branch",
        "department",
        "team",
        "employee",
    }
)

# Workspace related-module filter → DocumentLink entity_type values (+ direct FKs)
RELATED_MODULE_ENTITY_TYPES: dict[str, frozenset[str]] = {
    "lead": frozenset({"lead"}),
    "contact": frozenset({"contact", "crm_contact"}),
    "company": frozenset({"company", "crm_company"}),
    "opportunity": frozenset({"opportunity", "deal"}),
    "investor": frozenset({"investor"}),
    "project": frozenset({"project"}),
    "marketing_campaign": frozenset({"campaign", "marketing_campaign"}),
    "marketing_asset": frozenset({"marketing_asset"}),
    "task": frozenset({"task"}),
    "calendar_event": frozenset({"calendar_event"}),
    "financial_record": frozenset({"transaction", "financial_record"}),
}

RELATED_MODULE_KEYS = frozenset(RELATED_MODULE_ENTITY_TYPES.keys())


def infer_file_kind(extension: str) -> DocumentFileKind:
    return EXTENSION_FILE_KIND.get(extension.lower().lstrip("."), DocumentFileKind.OTHER)


def is_previewable(extension: str) -> bool:
    return extension.lower().lstrip(".") in PREVIEWABLE_EXTENSIONS


def initial_processing_status(extension: str, document_type: str = "other") -> ProcessingStatus:
    ext = extension.lower().lstrip(".")
    if should_process_as_drawing(ext, document_type):
        return ProcessingStatus.UPLOADED
    if is_processable(ext):
        return ProcessingStatus.UPLOADED
    return ProcessingStatus.NOT_SUPPORTED
