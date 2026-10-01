"""Phase 11.10 — AI-native premium master feasibility. Text-only concepts.

Not Hybrid V3. Not THE_REGISTER R1. Not a canonical pipeline.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile

DAY001_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_001.jpg"
DAY001_ASSET_ID = "5d26caf3-c237-4a78-9f3a-91f05dd24fa2"
# Vertical cover crop of the unused street monument — Temple mass, not Day_009 lantern crop.
DAY001_CENTERING = (0.58, 0.38)

CONCEPT_NAME = "THE_CAPITAL"
HEADLINE = "BAŞKENTTE"
CONCEPT_SENTENCE = (
    "The Temple is a Washington civic fact: the street monument is the campaign, "
    "and the lansman is the condition of occupying that capital stone."
)
TWO_SECOND = "A real Washington Temple under civic light — %35 as the terms of the address, not a badge."

BANNED = (
    "Proof 01 architecture-as-letter",
    "Proof 02 historic/new join lockup",
    "Proof 03 threshold/portal",
    "THE_LEDGER paper collateral",
    "THE_REGISTER measuring register",
    "Master 01 Day_003 sky type plate",
    "Master 02",
    "Master 03",
    "HTML sales overlay on AI background",
    "cutout plus generated field plus compositor",
)


def ai_native_concepts() -> list[dict[str, Any]]:
    return [
        {
            "key": "C1",
            "name": CONCEPT_NAME,
            "headline": HEADLINE,
            "big_idea": CONCEPT_SENTENCE,
            "temple_specificity": (
                "Day_001 is the unused complete street monument in Washington fabric — "
                "flags, pavement, and Temple mass as one civic address."
            ),
            "photo_role": "Protected factual architecture. Atmosphere, street climate, and type are designed around it.",
            "commercial_idea": "%35 is the launch term of occupying this Washington address. Price/unit is the residential right.",
            "typographic_idea": "Type participates in civic light and ground darkness as one composition, not a fact column.",
            "percent_role": "The atmospheric condition of the lansman — large, in the designed climate, related to the monument.",
            "price_unit": "675.000 USD and 2+1 DAİRE as one inhabited claim, not a listing pair.",
            "cta_role": "A quiet instruction at the street's contact, not a button.",
            "depth": "Monument in real space; designed climate around it; type in that climate.",
            "two_second_event": TWO_SECOND,
            "persuasion": "Desirability from the real civic Temple; meaning from %35 as address terms; next step at the street.",
            "photo": DAY001_FILENAME,
            "selected": True,
            "reject_reason": None,
        },
        {
            "key": "C2",
            "name": "THE_CHAMBER_CLAIM",
            "headline": "ODA",
            "big_idea": "Living_Room_001 as the 2+1 product world; commercial language lives in the room's light.",
            "temple_specificity": "Weak — the window shows city, not Temple architecture.",
            "photo_role": "Interior object.",
            "commercial_idea": "Price as room caption.",
            "typographic_idea": "Type on walls.",
            "percent_role": "Attached numeral.",
            "price_unit": "Listing.",
            "cta_role": "Explore the room.",
            "depth": "Interior card.",
            "two_second_event": "A furniture ad.",
            "persuasion": "Lifestyle, not lansman.",
            "photo": "IH_DC_TMP_001_Render_Living_Room_001.jpg",
            "selected": False,
            "reject_reason": "Property listing / interior card. Temple identity not in the frame.",
        },
        {
            "key": "C3",
            "name": "THE_NEEDLE_WEATHER",
            "headline": "İĞNE",
            "big_idea": "Day_002 lantern as weather vane in generated dusk.",
            "temple_specificity": "Lantern is Temple, photograph is Master 03.",
            "photo_role": "Spire hero.",
            "commercial_idea": "Offer as sky weather.",
            "typographic_idea": "Sky type.",
            "percent_role": "Sky numeral.",
            "price_unit": "Attached.",
            "cta_role": "Attached.",
            "depth": "Poster.",
            "two_second_event": "Master 03 leftover.",
            "persuasion": "Icon, not sale.",
            "photo": "IH_DC_TMP_001_Render_Exterior_Day_002.jpg",
            "selected": False,
            "reject_reason": "Master 03 photograph. Do not repeat.",
        },
        {
            "key": "C4",
            "name": "THE_DUSK_TITLE",
            "headline": "ALACAKARANLIK",
            "big_idea": "Sunset_001 silhouette as cinematic title.",
            "temple_specificity": "Dusk mass is Temple; mechanism is poster.",
            "photo_role": "Silhouette.",
            "commercial_idea": "Glow as offer.",
            "typographic_idea": "Sky title.",
            "percent_role": "Glow.",
            "price_unit": "Attached.",
            "cta_role": "Attached.",
            "depth": "Poster melt.",
            "two_second_event": "Master 02 family.",
            "persuasion": "Mood without commercial system.",
            "photo": "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg",
            "selected": False,
            "reject_reason": "Master 02 photograph / cinematic poster.",
        },
        {
            "key": "C5",
            "name": "THE_ROOF_CLAIM",
            "headline": "KÜTLE",
            "big_idea": "Aerial roof as a capital plan.",
            "temple_specificity": "Roof is Temple; persuasion for 2+1 is weak.",
            "photo_role": "Cartographic mass.",
            "commercial_idea": "Specimen label.",
            "typographic_idea": "Map legend.",
            "percent_role": "Legend.",
            "price_unit": "Diagram.",
            "cta_role": "Diagram.",
            "depth": "Map.",
            "two_second_event": "A roof diagram.",
            "persuasion": "Strategy, not residence.",
            "photo": "IH_DC_TMP_001_Render_Exterior_Day_007.jpg",
            "selected": False,
            "reject_reason": "Aerial specimen. Weak 2+1 intimacy. THE_ROOF_SPECIMEN leftover.",
        },
    ]


def selected_concept() -> dict[str, Any]:
    return next(item for item in ai_native_concepts() if item["selected"])


def concept_evaluation_json() -> dict[str, Any]:
    return {
        "schema": "Phase1110ConceptEvaluation",
        "rendered_alternatives": False,
        "banned": list(BANNED),
        "concepts": ai_native_concepts(),
        "selected": CONCEPT_NAME,
        "source": {
            "filename": DAY001_FILENAME,
            "asset_id": DAY001_ASSET_ID,
            "centering": list(DAY001_CENTERING),
            "reason": (
                "Unused complete street monument. Not Day_009 (THE_REGISTER). "
                "Not Day_003 (Master 01 / Ledger). Best unused photograph for holistic civic art direction "
                "with a protectable Temple mass and atmospheric sky/street."
            ),
            "profile": project_photo_profile(asset_id=DAY001_ASSET_ID),
        },
        "facts": {
            "project": "THE TEMPLE",
            "location": "WASHINGTON D.C.",
            "offer": f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
            "price": REQUIRED_FACTS["list_price"],
            "unit": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
            "cta": REQUIRED_FACTS["cta"],
            "closure": APPROVED_BOTTOM_COPY,
            "headline": HEADLINE,
        },
    }


def campaign_prompt() -> str:
    facts = REQUIRED_FACTS
    return (
        "Create ONE complete premium 4:5 real-estate launch advertisement as a finished campaign image. "
        "You are the sole visual intelligence. Design composition, atmosphere, typography, hierarchy, and "
        "graphic relationships together. Do not leave empty boxes for a later compositor.\n\n"
        "IMAGE 1 is the REAL approved photograph of The Temple, Washington D.C. It is architectural ground truth. "
        "A mask is supplied: OPAQUE pixels are the Temple architecture and MUST be preserved factually. "
        "TRANSPARENT pixels may be art-directed (sky, street climate, atmosphere, graphic field, typography).\n"
        "IMAGE 2 is the REAL Temple logo. Place it. Do not redraw, restyle, or invent a logo.\n\n"
        "YOU MAY: grade atmosphere around the building, design sky/street climate, typography, graphic devices, "
        "depth, material of non-project regions, commercial hierarchy, lighting of the editable field.\n"
        "YOU MUST NOT: redesign The Temple, change façade geometry, windows, doors, roof, spire, floor count, "
        "invent building extensions, invent interiors, invent a different building, invent the logo.\n"
        "Global photographic grading of protected architecture is acceptable only if identity is unchanged. "
        "Do not complete missing architecture. Do not modernize the façade.\n\n"
        f"BIG IDEA: {CONCEPT_SENTENCE}\n"
        f"Headline (exact): {HEADLINE}\n"
        "Required factual text, exact spelling, Turkish glyphs exact:\n"
        "THE TEMPLE\n"
        "WASHINGTON D.C.\n"
        f"{facts['discount']} {facts['discount_label']}\n"
        f"{facts['list_price']}\n"
        f"{facts['unit']} {facts['unit_label']}\n"
        f"{facts['cta']}\n"
        f"Optional closure: {APPROVED_BOTTOM_COPY}\n"
        "No invented numbers, ROI, dates, or other project names. No UniLoft. No Investhome wordmark.\n\n"
        "Commercial information must participate in image, material, space, scale, rhythm, depth, and type. "
        "Do not park a left information column. Do not make a website hero, listing, brochure cover, "
        "sale sticker, badge, or button. No split screen. No paper collage. No measuring register.\n"
        "Premium international real-estate agency finish. Confident, restrained, campaign-complete."
    )
