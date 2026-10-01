"""ReferenceQualityFilterV1 — Grade A only for 5.4E art direction."""

from __future__ import annotations

from typing import Any

# Locked from Phase 5.4D CreativeReferenceQualityRankingV1. Do not promote B/C.
GRADE_A = {
    "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57": "ORNEK_00013.jpg",
    "3a3c4832-a8c1-5a43-a518-d895ee78fbe1": "ORNEK_00001.jpg",
    "15e71ec3-ff92-5604-84aa-2582510d0615": "ORNEK_00006.jpg",
    "b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd": "ORNEK_00015.jpg",
    "a1046460-04ad-5ef1-bd42-88042c4d9760": "ORNEK_00011.jpg",
    "1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2": "ORNEK_00008.jpg",
}

GRADE_B = {
    "578f0688-d613-5c8b-9f82-30b096e02057": "ORNEK_00004.jpg",
    "6d190e1f-3a23-5057-ba72-66694e4a4e05": "ORNEK_00010.jpg",
    "ee24610e-af0e-5f95-934b-d0842237d929": "ORNEK_00012.jpg",
    "6e537e9c-84d4-52fe-91f8-ea954f18ba0a": "ORNEK_00014.jpg",
    "22aed5e1-b4ad-53ad-a389-bb628fe4da2a": "ORNEK_00002.jpg",
}

GRADE_C = {
    "e08494d1-dd09-5dc3-a3ea-c10e89322f13": "ORNEK_00003.jpg",
    "bc0f8eb4-c5f1-5328-99a9-bb3b6c02e6a7": "ORNEK_00005.jpg",
    "3778b4a3-0126-5574-ab9e-4ac8d8d32a09": "ORNEK_00007.jpg",
    "002d4391-a9c0-55a5-be86-f73f08163e40": "ORNEK_00009.jpg",
}

MINIMUM_GRADE = "A"


def grade_for(reference_id: str | None, filename: str | None = None) -> str | None:
    rid = str(reference_id or "")
    name = str(filename or "")
    if rid in GRADE_A or name in GRADE_A.values():
        return "A"
    if rid in GRADE_B or name in GRADE_B.values():
        return "B"
    if rid in GRADE_C or name in GRADE_C.values():
        return "C"
    return None


def filter_references(entries: list[dict[str, Any]], *, minimum_grade: str = MINIMUM_GRADE) -> dict[str, Any]:
    allowed = []
    stored_b = []
    excluded_c = []
    unknown = []
    for entry in entries:
        grade = grade_for(entry.get("reference_id"), entry.get("filename"))
        blob = dict(entry)
        blob["quality_grade"] = grade
        if grade == "A":
            allowed.append(blob)
        elif grade == "B":
            stored_b.append(blob)
        elif grade == "C":
            excluded_c.append(blob)
        else:
            unknown.append(blob)
    return {
        "schema": "ReferenceQualityFilterV1",
        "minimum_grade": minimum_grade,
        "allowed": allowed if minimum_grade == "A" else allowed,
        "stored_not_used": stored_b,
        "excluded": excluded_c + unknown,
        "a_count": len(allowed),
        "b_count": len(stored_b),
        "c_count": len(excluded_c),
    }
