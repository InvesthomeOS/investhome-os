"""Match a real Temple photograph to the extracted structure. Do not distort the photo."""

from __future__ import annotations

from typing import Any

DAY008_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_008.jpg"
DAY008_ASSET_ID = "2d44757b-079c-4a78-a4a9-5fe6370466c8"
# Tight historic tower fragment. Street, bike lane, and modern wing are not the page mass.
DAY008_CROP = {"left": 0.50, "top": 0.00, "width": 0.42, "height": 0.74}

CANDIDATES = (
    {
        "key": "Day_008",
        "filename": DAY008_FILENAME,
        "asset_id": DAY008_ASSET_ID,
        "fit": 9,
        "note": "Plaza looking toward the historic tower. Tight crop yields a stone fragment that can sit as a lower-left foundation without forcing a colonnade pose.",
        "selected": True,
    },
    {
        "key": "Day_002",
        "filename": "IH_DC_TMP_001_Render_Exterior_Day_002.jpg",
        "asset_id": "543aeb03-c4c9-46f9-9d9f-81bf53f45438",
        "fit": 7,
        "note": "Clean spire fragment, but it is the Master 03 photograph.",
        "selected": False,
    },
    {
        "key": "Day_009",
        "filename": "IH_DC_TMP_001_Render_Exterior_Day_009.jpg",
        "asset_id": "7696df34-0544-44b9-89f5-0d1b2523c412",
        "fit": 6,
        "note": "Strongest street monument, already THE_REGISTER. Do not force the same photo into a new structure first.",
        "selected": False,
    },
    {
        "key": "Day_001",
        "filename": "IH_DC_TMP_001_Render_Exterior_Day_001.jpg",
        "asset_id": "5d26caf3-c237-4a78-9f3a-91f05dd24fa2",
        "fit": 5,
        "note": "Complete street wall. Hard to become a fragment without dragging the modern wing.",
        "selected": False,
    },
    {
        "key": "Day_003",
        "filename": "IH_DC_TMP_001_Render_Exterior_Day_003.jpg",
        "asset_id": "7346e259-f999-4fbb-a8d5-63708d4e0c81",
        "fit": 3,
        "note": "Master 01 / THE_LEDGER sky plate. Incompatible with this structure.",
        "selected": False,
    },
    {
        "key": "Living_Room_001",
        "filename": "IH_DC_TMP_001_Render_Living_Room_001.jpg",
        "asset_id": "c3d11c35-d8b7-485c-b216-0a4da68b751a",
        "fit": 2,
        "note": "Interior. Selected reference is an exterior stone fragment.",
        "selected": False,
    },
)


def temple_asset_match() -> dict[str, Any]:
    chosen = next(item for item in CANDIDATES if item["selected"])
    return {
        "schema": "Phase1111TempleAssetMatch",
        "priority": ["PROJECT REALITY", "VISUAL QUALITY", "REFERENCE DNA"],
        "do_not_distort_photograph": True,
        "selected": chosen,
        "crop_box": dict(DAY008_CROP),
        "crop_reason": (
            "Day_008 is a square plaza frame. The transferable structure needs a stone fragment, "
            "not the bike lane or the modern wing. Crop isolates the historic tower. "
            "The photograph is not stretched to imitate a colonnade."
        ),
        "rejected": [item for item in CANDIDATES if not item["selected"]],
    }
