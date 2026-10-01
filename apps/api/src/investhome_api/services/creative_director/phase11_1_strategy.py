"""Phase 11.1 — creative strategy and concept selection. Strategy before layout."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_design_dna_v2 import grade_a_design_dna
from investhome_api.services.creative_director.creative_strategy_v1 import SCHEMA, STRATEGY_FIELDS, validate_creative_strategy
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID, no_copy_test, two_second_test
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile
from investhome_api.services.creative_director.reference_matching_v1 import match_design_dna

DAY008_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_008.jpg"
DAY008_ASSET_ID = "2d44757b-079c-4a78-a4a9-5fe6370466c8"

HEADLINE = "TARİH"
CONCEPT_NAME = "PHOTOGRAPHIC_I"
CONCEPT_SENTENCE = (
    "The Temple spire is printed as the letter İ in TARİH, so the real building completes the word."
)
TWO_SECOND = (
    "A monumental stone spire standing in for the letter İ, finishing the word TARİH on a stone-paper page."
)
USER_REQUEST = "The Temple için gerçekten premium, kreatif bir lansman reklamı hazırla."

BANNED_MASTER_PHOTOS = {
    "IH_DC_TMP_001_Render_Exterior_Day_003.jpg",
    "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg",
    "IH_DC_TMP_001_Render_Living_Room_001.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_002.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_009.jpg",
}

OPPORTUNITY_ASSETS = (
    ("IH_DC_TMP_001_Render_Exterior_Day_008.jpg", "2d44757b-079c-4a78-a4a9-5fe6370466c8", "SELECTED — full historic spire, plaza, human scale"),
    ("IH_DC_TMP_001_Render_Exterior_Day_001.jpg", "5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "street monument — spire crown cropped"),
    ("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "299bd265-a0ea-486d-866d-1947f103fd57", "aerial object — map risk"),
    ("IH_DC_TMP_001_Render_Exterior_Day_007.jpg", "c0afa1bf-b487-410c-be3d-91c31852550d", "high oblique roof/spire — weaker as a letter"),
    ("IH_DC_TMP_001_Render_Exterior_Day_010.jpg", "f491ee6e-de7d-4258-a153-4104e326b736", "aerial intersection — diagram, not civic letter"),
    ("IH_DC_TMP_001_Render_Living_Room_004.jpeg", "81922792-e644-4752-a5dd-70923311d9bb", "interior still-life — not Temple identity"),
    ("IH_DC_TMP_001_Render_Living_Room_006.jpg", "a27e3c70-995f-48fc-965c-49fde9917b3f", "supporting interior"),
    ("IH_DC_TMP_001_Render_Bedroom_007.jpg", "2635b01e-6580-4511-82fe-a16fba510b41", "private unit story — not flagship"),
)

DNA_USED = (
    {
        "filename": "ORNEK_00013.jpg",
        "reference_id": "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57",
        "principle": "A photograph may be a structural page mass, not a backdrop.",
        "not_copied": "navy field, colonnade crop, DÜZENLİ/GÜVENLİ/PRESTİJLİ stack, UniLoft",
    },
    {
        "filename": "ORNEK_00011.jpg",
        "reference_id": "a1046460-04ad-5ef1-bd42-88042c4d9760",
        "principle": "A building can be an object on a designed page, not wallpaper.",
        "not_copied": "pointer lines, walking-time UI, centered brick isolation",
    },
    {
        "filename": "ORNEK_00008.jpg",
        "reference_id": "1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2",
        "principle": "Type can collide with architecture instead of sitting in a leftover box.",
        "not_copied": "dusk serif default, circular offer badges, Uniloft façade",
    },
)


def selected_design_dna_text() -> str:
    return (
        "Compatible principles only, not a style collage: "
        "architecture as graphic material (00013), building as printed object on paper (00011), "
        "type colliding with the building rather than parked in leftover sky (00008)."
    )


def creative_strategy() -> dict[str, Any]:
    profile = project_photo_profile(asset_id=DAY008_ASSET_ID) or {}
    matching = match_design_dna(
        photo_profile=profile,
        campaign_objective="civic prestige launch for The Temple in Washington D.C.",
        target_emotion="architectural authority with living civic presence",
        visual_opportunity="historic spire as a vertical letterform on a designed page",
    )
    strategy = {
        "schema": SCHEMA,
        "status": "SET",
        "layout_forbidden_until_strategy_exists": False,
        "pipeline_id": PIPELINE_ID,
        "user_request": USER_REQUEST,
        "project_story": (
            "The Temple is a historic Washington sanctuary given a second life as a home. "
            "The campaign must make that civic fact felt, not merely stated."
        ),
        "campaign_objective": "Launch The Temple as a premium Washington D.C. residence with a %35 lansman advantage.",
        "target_emotion": "Quiet civic awe — history standing in the present, not luxury-generic calm.",
        "primary_message": "This place is history you can inhabit.",
        "commercial_message": (
            f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']} · "
            f"{REQUIRED_FACTS['list_price']} · {REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']} · "
            f"{REQUIRED_FACTS['cta']}"
        ),
        "available_real_assets": [
            {"filename": name, "asset_id": aid, "note": note} for name, aid, note in OPPORTUNITY_ASSETS
        ],
        "strongest_project_characteristic": (
            "The historic stone spire is a complete, readable civic letter — a vertical monument "
            "that no other Temple photograph isolates as cleanly at human scale."
        ),
        "selected_design_dna": selected_design_dna_text(),
        "creative_tension": "A living word completed by dead stone — language needs the building to finish itself.",
        "visual_idea": CONCEPT_SENTENCE,
        "why_this_idea_fits_this_project": (
            "The Temple is named as a civic monument. Using its real spire as the İ in TARİH "
            "makes the name, the architecture, and the campaign idea the same object. "
            "No other Temple asset can be a letter without inventing architecture."
        ),
        "selected_real_assets": [
            {
                "filename": DAY008_FILENAME,
                "asset_id": DAY008_ASSET_ID,
                "role": "photographic letter İ — historic spire, plaza foot, human scale",
            }
        ],
        "relevant_design_dna": list(DNA_USED),
        "memorable_gesture": "The real Temple spire standing in for the dotted İ, towering over TAR and H.",
        "two_second_impression": TWO_SECOND,
        "headline": HEADLINE,
        "headline_origin": "NEW — required by the visual concept; no financial claims",
        "closure": APPROVED_BOTTOM_COPY,
        "brand": "Temple logo only",
        "reference_match": matching,
        "not_reused": ["TYPE IN SKY", "EDITORIAL PAGE CUT", "LOOKING CHAMBER"],
        "project_reality": {
            "architecture_invented": False,
            "interior_invented": False,
            "exterior_invented": False,
            "logo_invented": False,
            "facts_invented": False,
        },
    }
    check = validate_creative_strategy(strategy)
    if not check.get("pass"):
        raise RuntimeError(f"strategy incomplete: {check.get('missing_fields')}")
    missing = [field for field in STRATEGY_FIELDS if not strategy.get(field)]
    if missing:
        raise RuntimeError(f"strategy missing {missing}")
    return strategy


def concept_selection_markdown() -> str:
    return "\n".join(
        [
            "# Concept selection",
            "",
            "Internal directions were evaluated in text only. Four were discarded.",
            "They are not shown as A/B/C. One concept proceeds.",
            "",
            f"**Selected concept:** {CONCEPT_NAME}",
            "",
            f"**Visual mechanism:** {CONCEPT_SENTENCE}",
            "",
            "**Why this one:** Day_008 is unused, shows the full historic spire, and can act as a letter without generating architecture. It is not type-in-sky, not a page-cut, not a looking chamber.",
            "",
            "**Discarded internally:** plaza processional line; aerial object-on-paper; unused interior still-life; historic/modern split-screen.",
            "",
            f"**Headline:** {HEADLINE} (new, concept-required, Turkish, non-factual)",
            "",
            f"**Asset:** `{DAY008_FILENAME}` / `{DAY008_ASSET_ID}`",
        ]
    )


def two_second_record() -> dict[str, Any]:
    return two_second_test(TWO_SECOND)


def no_copy_record(*, feels_designed: bool) -> dict[str, Any]:
    return no_copy_test(
        visual_mechanism=CONCEPT_SENTENCE,
        photography_participates=True,
        feels_designed_without_copy=feels_designed,
    )


def dna_selection_json() -> dict[str, Any]:
    library = {item["filename"]: item for item in grade_a_design_dna()}
    records = []
    for item in DNA_USED:
        dna = library[item["filename"]]
        records.append(
            {
                "filename": item["filename"],
                "reference_id": item["reference_id"],
                "media_asset_id": dna["media_asset_id"],
                "transferable_principle": item["principle"],
                "not_copied": item["not_copied"],
                "strength_score": dna["strength_score"],
                "photography_role": dna["photography_role"],
            }
        )
    return {
        "schema": "Phase111DesignDNASelectionV1",
        "policy": "Retrieve transferable principles. Do not reproduce a reference layout. Do not collage styles.",
        "used": records,
        "unused_grade_a": [
            {
                "filename": item["filename"],
                "reference_id": item["reference_id"],
                "reason": "not the primary mechanism for a letterform monument",
            }
            for item in grade_a_design_dna()
            if item["filename"] not in {row["filename"] for row in DNA_USED}
        ],
    }
