"""Phase 11.11 — score Grade-A DESIGN_REFERENCES. Select one. Not ORNEK_00001 by default."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES
from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA, grade_a_design_dna

AXES = (
    "COMPOSITIONAL_STRENGTH",
    "COMMERCIAL_HIERARCHY",
    "PHOTO_TYPE_RELATIONSHIP",
    "TRANSFERABILITY_TO_TEMPLE",
    "BRAND_COMPATIBILITY",
    "ASSET_COMPATIBILITY",
    "PERSUASIVE_STRUCTURE",
    "FINISH_QUALITY",
)

# Pixel-honest after inspecting all six Grade-A files. Do not auto-pick ORNEK_00001.
SCORES: dict[str, dict[str, int]] = {
    "ORNEK_00013.jpg": {
        "COMPOSITIONAL_STRENGTH": 9,
        "COMMERCIAL_HIERARCHY": 8,
        "PHOTO_TYPE_RELATIONSHIP": 10,
        "TRANSFERABILITY_TO_TEMPLE": 8,
        "BRAND_COMPATIBILITY": 8,
        "ASSET_COMPATIBILITY": 8,
        "PERSUASIVE_STRUCTURE": 8,
        "FINISH_QUALITY": 9,
    },
    "ORNEK_00001.jpg": {
        "COMPOSITIONAL_STRENGTH": 8,
        "COMMERCIAL_HIERARCHY": 6,
        "PHOTO_TYPE_RELATIONSHIP": 8,
        "TRANSFERABILITY_TO_TEMPLE": 4,
        "BRAND_COMPATIBILITY": 6,
        "ASSET_COMPATIBILITY": 3,
        "PERSUASIVE_STRUCTURE": 7,
        "FINISH_QUALITY": 8,
    },
    "ORNEK_00006.jpg": {
        "COMPOSITIONAL_STRENGTH": 6,
        "COMMERCIAL_HIERARCHY": 5,
        "PHOTO_TYPE_RELATIONSHIP": 5,
        "TRANSFERABILITY_TO_TEMPLE": 4,
        "BRAND_COMPATIBILITY": 5,
        "ASSET_COMPATIBILITY": 6,
        "PERSUASIVE_STRUCTURE": 6,
        "FINISH_QUALITY": 7,
    },
    "ORNEK_00015.jpg": {
        "COMPOSITIONAL_STRENGTH": 8,
        "COMMERCIAL_HIERARCHY": 5,
        "PHOTO_TYPE_RELATIONSHIP": 8,
        "TRANSFERABILITY_TO_TEMPLE": 5,
        "BRAND_COMPATIBILITY": 7,
        "ASSET_COMPATIBILITY": 6,
        "PERSUASIVE_STRUCTURE": 6,
        "FINISH_QUALITY": 8,
    },
    "ORNEK_00011.jpg": {
        "COMPOSITIONAL_STRENGTH": 7,
        "COMMERCIAL_HIERARCHY": 8,
        "PHOTO_TYPE_RELATIONSHIP": 7,
        "TRANSFERABILITY_TO_TEMPLE": 7,
        "BRAND_COMPATIBILITY": 7,
        "ASSET_COMPATIBILITY": 8,
        "PERSUASIVE_STRUCTURE": 7,
        "FINISH_QUALITY": 7,
    },
    "ORNEK_00008.jpg": {
        "COMPOSITIONAL_STRENGTH": 8,
        "COMMERCIAL_HIERARCHY": 4,
        "PHOTO_TYPE_RELATIONSHIP": 8,
        "TRANSFERABILITY_TO_TEMPLE": 6,
        "BRAND_COMPATIBILITY": 6,
        "ASSET_COMPATIBILITY": 7,
        "PERSUASIVE_STRUCTURE": 6,
        "FINISH_QUALITY": 7,
    },
}

REASONS: dict[str, str] = {
    "ORNEK_00013.jpg": (
        "Strongest two-mass page: architecture as structural material, designed field as the message actor, "
        "type never on the photograph. Hybrid V2 can reconstruct this without inventing Temple architecture. "
        "Temple has a real stone fragment that can occupy the foundation role."
    ),
    "ORNEK_00001.jpg": (
        "Not selected. No Temple terrace/Capitol lifestyle equivalent. Sky-as-type-slot is a Temple ban. "
        "Do not auto-select because it is first in the library."
    ),
    "ORNEK_00006.jpg": "Nearest banned header+photo split. Transferring it would reconstruct a template.",
    "ORNEK_00015.jpg": "Interior depth tunnel. Temple lansman needs the monument, not a kitchen still-life.",
    "ORNEK_00011.jpg": (
        "Object-on-paper + proof lines already used by THE_LEDGER / THE_REGISTER. "
        "Selecting it would re-test the plateaued family, not a new human-proven structure."
    ),
    "ORNEK_00008.jpg": (
        "Type-in-shadow is craft; circular badges are a defect. Full-bleed photo+overlay is the old compiler path."
    ),
}

SELECTED_FILENAME = "ORNEK_00013.jpg"
SELECTED_MEDIA_ID = GRADE_A_MEDIA[SELECTED_FILENAME]
SELECTED_REFERENCE_ID = next(rid for rid, name in GRADE_A_REFERENCES if name == SELECTED_FILENAME)
WHY_SELECTED = REASONS[SELECTED_FILENAME]


def _total(filename: str) -> int:
    return sum(int(SCORES[filename][axis]) for axis in AXES)


def reference_score_table() -> dict[str, Any]:
    dna = {item["filename"]: item for item in grade_a_design_dna()}
    rows = []
    for rid, filename in GRADE_A_REFERENCES:
        scores = dict(SCORES[filename])
        rows.append(
            {
                "filename": filename,
                "reference_id": rid,
                "media_asset_id": GRADE_A_MEDIA[filename],
                "scores": scores,
                "total": _total(filename),
                "selected": filename == SELECTED_FILENAME,
                "reason": REASONS[filename],
                "visual_idea": dna[filename]["visual_idea"],
            }
        )
    rows.sort(key=lambda item: (-int(item["total"]), item["filename"]))
    selected = next(item for item in rows if item["selected"])
    assert selected["filename"] != "ORNEK_00001.jpg"
    return {
        "schema": "Phase1111ReferenceScore",
        "axes": list(AXES),
        "auto_select_orneK_00001": False,
        "selected": selected["filename"],
        "selected_reference_id": SELECTED_REFERENCE_ID,
        "selected_media_asset_id": SELECTED_MEDIA_ID,
        "why_selected": WHY_SELECTED,
        "records": rows,
    }
