"""Drawing intelligence configuration and resource limits."""

from __future__ import annotations

DRAWING_EXTENSIONS = frozenset({"dwg", "dxf", "pdf", "png", "jpg", "jpeg"})
CAD_EXTENSIONS = frozenset({"dwg", "dxf"})
VECTOR_PLAN_EXTENSIONS = frozenset({"pdf", "dxf"})
SCANNED_PLAN_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "pdf"})

DRAWING_DOCUMENT_TYPES = frozenset({"architectural_drawing", "construction_drawing"})

# Worker isolation limits
DRAWING_CONVERSION_TIMEOUT_SECONDS = 120
DRAWING_PROCESSING_TIMEOUT_SECONDS = 300
DRAWING_MAX_GEOMETRY_BYTES = 5_242_880  # 5 MB
DRAWING_MAX_PREVIEW_BYTES = 2_097_152  # 2 MB
DRAWING_MAX_ELEMENTS = 500
DRAWING_MAX_SHEETS = 50

# Subdirectories under document storage root
DRAWING_PREVIEW_SUBDIR = "drawing-previews"
DRAWING_GEOMETRY_SUBDIR = "drawing-geometry"


def is_drawing_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in DRAWING_EXTENSIONS


def is_drawing_document_type(document_type: str) -> bool:
    return document_type.lower() in DRAWING_DOCUMENT_TYPES


def should_process_as_drawing(extension: str, document_type: str) -> bool:
    ext = extension.lower().lstrip(".")
    if ext in CAD_EXTENSIONS:
        return True
    if is_drawing_document_type(document_type):
        return ext in DRAWING_EXTENSIONS
    return False
