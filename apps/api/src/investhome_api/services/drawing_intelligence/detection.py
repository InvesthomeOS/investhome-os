"""Drawing element detection heuristics."""

from __future__ import annotations

import re

from investhome_api.services.drawing_intelligence.types import (
    DetectedElement,
    DetectedSheet,
    ParsedGeometry,
)


def detect_sheets(geometry: ParsedGeometry, texts: list[tuple[str, float, float]]) -> list[DetectedSheet]:
    sheets: list[DetectedSheet] = []
    sheet_numbers = [t for t in texts if re.match(r"^[A-Z]-\d+", t[0].strip(), re.IGNORECASE)]
    if sheet_numbers:
        for index, (text, _, _) in enumerate(sheet_numbers[:50]):
            sheet_type = "floor_plan"
            upper = text.upper()
            if "ELEV" in upper:
                sheet_type = "elevation"
            elif "SECT" in upper:
                sheet_type = "section"
            elif "SITE" in upper:
                sheet_type = "site_plan"
            elif "DETAIL" in upper:
                sheet_type = "detail"
            sheets.append(
                DetectedSheet(
                    sheet_index=index,
                    sheet_name=text,
                    sheet_number=text.split()[0] if text else None,
                    sheet_type=sheet_type,
                    confidence="high" if re.match(r"^[A-Z]-\d+", text.strip(), re.IGNORECASE) else "medium",
                )
            )
    else:
        sheets.append(
            DetectedSheet(
                sheet_index=0,
                sheet_name="Sheet 1",
                sheet_number="S1",
                sheet_type="floor_plan",
                confidence="low",
            )
        )
    return sheets


def detect_elements(
    geometry: ParsedGeometry,
    texts: list[tuple[str, float, float]],
    *,
    layer_hints: dict[str, str] | None = None,
) -> list[DetectedElement]:
    elements: list[DetectedElement] = []
    layer_hints = layer_hints or {}

    for text, x, y in texts:
        upper = text.upper().strip()
        if not upper or upper.startswith("[SCANNED"):
            continue

        if re.match(r"^\d+(\.\d+)?\s*(M|MM|CM|FT|IN)?$", upper):
            numeric = float(re.match(r"^(\d+(?:\.\d+)?)", upper).group(1))  # type: ignore[union-attr]
            unit_match = re.search(r"(M|MM|CM|FT|IN)$", upper)
            elements.append(
                DetectedElement(
                    element_type="dimension",
                    label=text,
                    value_text=text,
                    numeric_value=numeric,
                    unit=unit_match.group(1).lower() if unit_match else "m",
                    confidence="high",
                    geometry={"x": x, "y": y},
                )
            )
            continue

        if "DOOR" in upper or upper.endswith("_BLOCK") and "DOOR" in upper:
            elements.append(
                DetectedElement(
                    element_type="door",
                    label=text,
                    confidence="medium",
                    geometry={"x": x, "y": y},
                )
            )
            continue

        if "WINDOW" in upper or upper.endswith("_BLOCK") and "WINDOW" in upper:
            elements.append(
                DetectedElement(
                    element_type="window",
                    label=text,
                    confidence="medium",
                    geometry={"x": x, "y": y},
                )
            )
            continue

        if re.search(r"\b(ROOM|BED|BATH|KITCHEN|LIVING|OFFICE|UNIT)\b", upper):
            confidence = "high" if "ROOM" in upper or "UNIT" in upper else "medium"
            elements.append(
                DetectedElement(
                    element_type="room" if "UNIT" not in upper else "unit",
                    label=text,
                    confidence=confidence,
                    geometry={"x": x, "y": y},
                )
            )
            continue

        if "FLOOR PLAN" in upper or re.match(r"^[A-Z]-\d+", upper):
            elements.append(
                DetectedElement(
                    element_type="title_block",
                    label=text,
                    confidence="high" if "FLOOR PLAN" in upper else "medium",
                    geometry={"x": x, "y": y},
                )
            )
            continue

        if "SCHEDULE" in upper:
            elements.append(
                DetectedElement(
                    element_type="schedule",
                    label=text,
                    confidence="medium",
                    geometry={"x": x, "y": y},
                )
            )

    wall_segments = len(geometry.paths)
    for index in range(min(wall_segments, 200)):
        path = geometry.paths[index]
        if len(path) >= 2:
            length = ((path[1].x - path[0].x) ** 2 + (path[1].y - path[0].y) ** 2) ** 0.5
            confidence = "high" if length > 500 else "low"
            elements.append(
                DetectedElement(
                    element_type="wall",
                    label=f"Wall {index + 1}",
                    numeric_value=round(length / 1000, 2),
                    unit="m",
                    confidence=confidence,
                    geometry={"start": {"x": path[0].x, "y": path[0].y}, "end": {"x": path[1].x, "y": path[1].y}},
                )
            )

    rooms = [e for e in elements if e.element_type == "room"]
    for room in rooms[:50]:
        elements.append(
            DetectedElement(
                element_type="area",
                label=f"Area: {room.label}",
                value_text="estimated",
                numeric_value=15.0,
                unit="sqm",
                confidence="low",
                metadata={"room_label": room.label},
            )
        )

    return elements[:500]
