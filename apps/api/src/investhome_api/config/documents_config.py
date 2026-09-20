"""Document engine configuration: allowed types, MIME validation, preview support."""

from investhome_api.models.document import ProcessingStatus

# Extension -> allowed MIME types (first is preferred for Content-Type responses)
ALLOWED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    ),
    "csv": ("text/csv", "application/csv", "text/plain", "application/octet-stream"),
    "txt": ("text/plain", "application/octet-stream"),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
    "dwg": ("application/acad", "image/vnd.dwg", "application/octet-stream"),
    "dxf": ("image/vnd.dxf", "application/dxf", "application/octet-stream"),
    "zip": ("application/zip", "application/x-zip-compressed", "application/octet-stream"),
}

# Extensions safe for inline browser preview
PREVIEWABLE_EXTENSIONS = frozenset({"pdf", "jpg", "jpeg", "png", "webp", "txt"})

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

# Entity types supported by DocumentLink
LINK_ENTITY_TYPES = frozenset(
    {
        "project",
        "investor",
        "lead",
        "contact",
        "crm_contact",
        "transaction",
        "user",
        # Future-ready
        "unit",
        "building",
        "contractor",
        "permit",
        "construction_milestone",
        "campaign",
        "deal",
        "crm_agreement",
        "opportunity",
        "property",
        "task",
        "capital_call",
    }
)


def is_previewable(extension: str) -> bool:
    return extension.lower().lstrip(".") in PREVIEWABLE_EXTENSIONS


from investhome_api.services.document_intelligence.extraction import is_processable
from investhome_api.services.drawing_intelligence.config import should_process_as_drawing


def initial_processing_status(extension: str, document_type: str = "other") -> ProcessingStatus:
    ext = extension.lower().lstrip(".")
    if should_process_as_drawing(ext, document_type):
        return ProcessingStatus.UPLOADED
    if is_processable(ext):
        return ProcessingStatus.UPLOADED
    return ProcessingStatus.NOT_SUPPORTED
