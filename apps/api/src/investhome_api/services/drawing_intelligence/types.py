"""Drawing intelligence data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DrawingPoint:
    x: float
    y: float


@dataclass
class DrawingBounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass
class ParsedGeometry:
    bounds: DrawingBounds | None
    paths: list[list[DrawingPoint]] = field(default_factory=list)
    texts: list[tuple[str, float, float]] = field(default_factory=list)
    layer_count: int = 0
    entity_count: int = 0


@dataclass
class DetectedElement:
    element_type: str
    label: str | None = None
    value_text: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    confidence: str = "medium"
    geometry: dict | None = None
    metadata: dict | None = None


@dataclass
class DetectedSheet:
    sheet_index: int
    sheet_name: str | None = None
    sheet_number: str | None = None
    sheet_type: str = "unknown"
    confidence: str = "medium"
    width: float | None = None
    height: float | None = None


@dataclass
class ConversionResult:
    success: bool
    method: str
    preview_svg: str | None = None
    geometry: ParsedGeometry | None = None
    error: str | None = None
    preview_unavailable: bool = False
    original_preserved: bool = True
