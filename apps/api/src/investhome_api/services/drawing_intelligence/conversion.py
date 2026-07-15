"""CAD and plan file conversion with read-only source access."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from investhome_api.services.drawing_intelligence.config import (
    CAD_EXTENSIONS,
    DRAWING_MAX_GEOMETRY_BYTES,
    DRAWING_MAX_PREVIEW_BYTES,
)
from investhome_api.services.drawing_intelligence.types import (
    ConversionResult,
    DrawingBounds,
    DrawingPoint,
    ParsedGeometry,
)

logger = logging.getLogger(__name__)

# Minimal valid DXF for tests and dev fixtures
SAMPLE_DXF = """0
SECTION
2
HEADER
0
ENDSEC
0
SECTION
2
ENTITIES
0
LINE
8
WALLS
10
0.0
20
0.0
11
5000.0
21
0.0
0
LINE
8
WALLS
10
5000.0
20
0.0
11
5000.0
21
3000.0
0
LINE
8
WALLS
10
5000.0
20
3000.0
11
0.0
21
3000.0
0
LINE
8
WALLS
10
0.0
20
3000.0
11
0.0
21
0.0
0
TEXT
8
ROOMS
10
2500.0
20
1500.0
40
250.0
1
LIVING ROOM
0
TEXT
8
DIMENSIONS
10
2500.0
20
-500.0
40
200.0
1
5.00 m
0
TEXT
8
TITLE
10
100.0
20
-800.0
40
150.0
1
A-101 FLOOR PLAN 1:100
0
INSERT
8
DOORS
2
DOOR_BLOCK
10
2500.0
20
0.0
0
INSERT
8
WINDOWS
2
WINDOW_BLOCK
10
5000.0
20
1500.0
0
ENDSEC
0
EOF
"""


def _bounds_from_points(points: list[DrawingPoint]) -> DrawingBounds | None:
    if not points:
        return None
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return DrawingBounds(min(xs), min(ys), max(xs), max(ys))


def _parse_dxf_text(content: str) -> ParsedGeometry:
    """Lightweight DXF parser for LINE, TEXT, INSERT entities."""
    lines = content.replace("\r\n", "\n").split("\n")
    paths: list[list[DrawingPoint]] = []
    texts: list[tuple[str, float, float]] = []
    entity_count = 0
    layers: set[str] = set()
    i = 0
    while i < len(lines) - 1:
        code = lines[i].strip()
        value = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if code == "0" and value == "LINE":
            entity_count += 1
            x1 = y1 = x2 = y2 = None
            layer = None
            j = i + 2
            while j < len(lines) - 1:
                c = lines[j].strip()
                v = lines[j + 1].strip()
                if c == "0":
                    break
                if c == "8":
                    layer = v
                    layers.add(v)
                elif c == "10":
                    x1 = float(v)
                elif c == "20":
                    y1 = float(v)
                elif c == "11":
                    x2 = float(v)
                elif c == "21":
                    y2 = float(v)
                j += 2
            if None not in (x1, y1, x2, y2):
                paths.append([DrawingPoint(x1, y1), DrawingPoint(x2, y2)])
            i = j
            continue
        if code == "0" and value in {"TEXT", "MTEXT"}:
            entity_count += 1
            x = y = None
            text = None
            layer = None
            j = i + 2
            while j < len(lines) - 1:
                c = lines[j].strip()
                v = lines[j + 1].strip()
                if c == "0":
                    break
                if c == "8":
                    layer = v
                    layers.add(v)
                elif c == "10":
                    x = float(v)
                elif c == "20":
                    y = float(v)
                elif c == "1":
                    text = v
                j += 2
            if text and x is not None and y is not None:
                texts.append((text, x, y))
            i = j
            continue
        if code == "0" and value == "INSERT":
            entity_count += 1
            x = y = None
            block = None
            layer = None
            j = i + 2
            while j < len(lines) - 1:
                c = lines[j].strip()
                v = lines[j + 1].strip()
                if c == "0":
                    break
                if c == "8":
                    layer = v
                    layers.add(v)
                elif c == "2":
                    block = v
                elif c == "10":
                    x = float(v)
                elif c == "20":
                    y = float(v)
                j += 2
            if block and x is not None and y is not None:
                texts.append((block, x, y))
            i = j
            continue
        i += 1

    all_points = [pt for path in paths for pt in path]
    return ParsedGeometry(
        bounds=_bounds_from_points(all_points),
        paths=paths,
        texts=texts,
        layer_count=len(layers),
        entity_count=entity_count,
    )


def _geometry_to_svg(geometry: ParsedGeometry, max_bytes: int = DRAWING_MAX_PREVIEW_BYTES) -> str:
    bounds = geometry.bounds
    if bounds is None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="10" y="50">No geometry</text></svg>'
        return svg

    pad = 200
    width = max(bounds.max_x - bounds.min_x + pad * 2, 100)
    height = max(bounds.max_y - bounds.min_y + pad * 2, 100)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{bounds.min_x - pad} {-bounds.max_y - pad} {width} {height}">',
        '<g stroke="#1e293b" stroke-width="20" fill="none">',
    ]
    for path in geometry.paths:
        if len(path) >= 2:
            coords = " ".join(f"{p.x},{-p.y}" for p in path)
            lines.append(f'<polyline points="{coords}"/>')
    lines.append("</g>")
    lines.append('<g fill="#334155" font-family="sans-serif" font-size="180">')
    for text, x, y in geometry.texts[:100]:
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f'<text x="{x}" y="{-y}">{safe}</text>')
    lines.append("</g></svg>")

    svg = "\n".join(lines)
    if len(svg.encode("utf-8")) > max_bytes:
        return svg[:max_bytes] + "\n<!-- truncated -->"
    return svg


def convert_dxf(source_path: Path) -> ConversionResult:
    """Convert DXF to preview SVG and geometry. Source file is read-only."""
    try:
        content = source_path.read_text(encoding="utf-8", errors="ignore")
        geometry = _parse_dxf_text(content)
        preview = _geometry_to_svg(geometry)
        return ConversionResult(
            success=True,
            method="dxf_parser_v1",
            preview_svg=preview,
            geometry=geometry,
            original_preserved=True,
        )
    except Exception as exc:
        logger.exception("DXF conversion failed for %s", source_path)
        return ConversionResult(
            success=False,
            method="dxf_parser_v1",
            error=str(exc),
            preview_unavailable=True,
            original_preserved=True,
        )


def convert_dwg(source_path: Path) -> ConversionResult:
    """DWG requires external converter; dev provider returns honest unavailable state."""
    _ = source_path.stat().st_size  # verify readable, no modification
    return ConversionResult(
        success=False,
        method="dwg_external_required",
        error="dwg_conversion_unavailable",
        preview_unavailable=True,
        original_preserved=True,
    )


def convert_vector_pdf(source_path: Path) -> ConversionResult:
    """Extract vector/text content from PDF floor plans."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(source_path))
        texts: list[tuple[str, float, float]] = []
        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            for line_no, line in enumerate(text.splitlines()):
                if line.strip():
                    texts.append((line.strip(), 100.0, float(page_index * 1000 + line_no * 120)))
        geometry = ParsedGeometry(
            bounds=DrawingBounds(0, 0, 5000, 3000) if texts else None,
            paths=[],
            texts=texts,
            layer_count=1,
            entity_count=len(texts),
        )
        preview = _geometry_to_svg(geometry) if texts else None
        return ConversionResult(
            success=bool(texts),
            method="pdf_vector_v1",
            preview_svg=preview,
            geometry=geometry,
            preview_unavailable=not texts,
            original_preserved=True,
        )
    except Exception as exc:
        logger.exception("PDF vector conversion failed for %s", source_path)
        return ConversionResult(
            success=False,
            method="pdf_vector_v1",
            error=str(exc),
            preview_unavailable=True,
            original_preserved=True,
        )


def convert_scanned_plan(source_path: Path, extension: str) -> ConversionResult:
    """Scanned plan via OCR placeholder with honest low-confidence metadata."""
    try:
        if extension in {"png", "jpg", "jpeg"}:
            from PIL import Image

            with Image.open(source_path) as img:
                width, height = img.size
        else:
            width, height = 2480, 3508

        geometry = ParsedGeometry(
            bounds=DrawingBounds(0, 0, float(width), float(height)),
            paths=[],
            texts=[("[scanned plan - OCR required]", width / 2, height / 2)],
            layer_count=1,
            entity_count=1,
        )
        preview = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
            f'<rect width="{width}" height="{height}" fill="#f8fafc"/>'
            f'<text x="{width/2}" y="{height/2}" text-anchor="middle" fill="#64748b" font-size="48">'
            "Scanned plan preview unavailable</text></svg>"
        )
        return ConversionResult(
            success=True,
            method="scanned_plan_ocr_placeholder",
            preview_svg=preview,
            geometry=geometry,
            preview_unavailable=True,
            original_preserved=True,
        )
    except Exception as exc:
        return ConversionResult(
            success=False,
            method="scanned_plan_ocr_placeholder",
            error=str(exc),
            preview_unavailable=True,
            original_preserved=True,
        )


def convert_drawing(source_path: Path, extension: str) -> ConversionResult:
    """Route conversion by extension. Never modifies source file."""
    ext = extension.lower().lstrip(".")
    if ext == "dxf":
        return convert_dxf(source_path)
    if ext == "dwg":
        return convert_dwg(source_path)
    if ext == "pdf":
        return convert_vector_pdf(source_path)
    if ext in {"png", "jpg", "jpeg"}:
        return convert_scanned_plan(source_path, ext)
    return ConversionResult(
        success=False,
        method="unsupported",
        error="unsupported_drawing_format",
        preview_unavailable=True,
        original_preserved=True,
    )


def detect_scale_from_texts(texts: list[tuple[str, float, float]]) -> tuple[str | None, str]:
    """Detect scale from title block text."""
    scale_pattern = re.compile(r"1\s*:\s*(\d+)", re.IGNORECASE)
    for text, _, _ in texts:
        match = scale_pattern.search(text)
        if match:
            return f"1:{match.group(1)}", "high"
        if "SCALE" in text.upper():
            return text, "medium"
    return None, "low"


def detect_discipline_from_texts(texts: list[tuple[str, float, float]], document_type: str) -> tuple[str, str]:
    joined = " ".join(t[0] for t in texts).upper()
    if "STRUCT" in joined:
        return "structural", "high"
    if "MECH" in joined or "HVAC" in joined:
        return "mechanical", "high"
    if "ELEC" in joined:
        return "electrical", "high"
    if "PLUMB" in joined:
        return "plumbing", "high"
    if document_type == "construction_drawing":
        return "structural", "medium"
    if document_type == "architectural_drawing":
        return "architectural", "high"
    return "architectural", "low"
