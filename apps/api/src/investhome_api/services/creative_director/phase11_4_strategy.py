"""Phase 11.4 — integrated commercial campaign concept. Not a Proof 01/02 revision."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.campaign_reading_path_v1 import SCHEMA as READING_PATH_SCHEMA
from investhome_api.services.creative_director.campaign_reading_path_v1 import validate_reading_path
from investhome_api.services.creative_director.commercial_design_dna_v1 import commercial_design_dna_library
from investhome_api.services.creative_director.commercial_system_gate import visual_idea_gate
from investhome_api.services.creative_director.creative_design_dna_v2 import grade_a_design_dna
from investhome_api.services.creative_director.creative_strategy_v1 import SCHEMA, STRATEGY_FIELDS, validate_creative_strategy
from investhome_api.services.creative_director.integrated_campaign_concept import (
    RENDER_FLOORS,
    score_concept_evaluation,
    validate_campaign_skeleton,
    validate_integrated_concept,
)
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID
from investhome_api.services.creative_director.numeric_art_direction import assign_numeric_functions
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile
from investhome_api.services.creative_director.reference_matching_v1 import match_design_dna
from investhome_api.services.creative_director.stage3_failure_learning_v2 import stage3_failure_learning_v2

DAY009_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_009.jpg"
DAY009_ASSET_ID = "7696df34-0544-44b9-89f5-0d1b2523c412"

HEADLINE_LINE_1 = "GİRİNCE"
HEADLINE_LINE_2 = "EV"
HEADLINE = f"{HEADLINE_LINE_1} {HEADLINE_LINE_2}"
CONCEPT_NAME = "THE_THRESHOLD"
CONCEPT_SENTENCE = (
    "The Temple campaign is the photographed civic doorway: three Gothic portals of the "
    "Washington sanctuary become the commercial architecture — the offer inhabits a real opening, "
    "the price stands on the street you arrive from, and the CTA is the threshold itself."
)
TWO_SECOND = "A Washington temple door you can live through, with the launch inside the architecture."
USER_REQUEST = "The Temple için gerçekten premium, kreatif bir lansman reklamı hazırla."
HIERARCHY = "ARCHITECTURE_LED"

BANNED_DEVICES = (
    "PHOTO + TEXT",
    "PHOTO + LEFT COLUMN",
    "PHOTO + RIGHT COLUMN",
    "DARK HEADER + PHOTO",
    "PHOTO CARD",
    "SPLIT SCREEN",
    "BROCHURE COVER",
    "PROPERTY LISTING",
    "WEBSITE HERO",
    "INSTAGRAM TEMPLATE",
    "GENERIC LUXURY EDITORIAL",
    "FLOATING FACT PANEL",
    "GIANT PROMO BADGE",
    "SALE POSTER",
    "TYPE IN SKY",
    "Day_008 automatic reuse",
    "architecture as a letter",
    "TARİH typography mechanism",
    "LOOKING CHAMBER",
    "THE_SEAM left information column",
)

OPPORTUNITY_ASSETS = (
    ("IH_DC_TMP_001_Render_Exterior_Day_001.jpg", "5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "civic sandwich — insertion; crown cropped"),
    ("IH_DC_TMP_001_Render_Exterior_Day_002.jpg", "543aeb03-c4c9-46f9-9d9f-81bf53f45438", "spire + sky — Master 03; leftover-sky type trap"),
    ("IH_DC_TMP_001_Render_Exterior_Day_003.jpg", "7346e259-f999-4fbb-a8d5-63708d4e0c81", "quiet sky — Master 01 type-in-sky history"),
    ("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "299bd265-a0ea-486d-866d-1947f103fd57", "aerial block — cartographic"),
    ("IH_DC_TMP_001_Render_Exterior_Day_005.jpg", "07863b0f-22e8-43c6-a629-7ceca7651b16", "aerial neighborhood — location only"),
    ("IH_DC_TMP_001_Render_Exterior_Day_007.jpg", "c0afa1bf-b487-410c-be3d-91c31852550d", "roof gardens on sanctuary — aerial, weak commercial home"),
    ("IH_DC_TMP_001_Render_Exterior_Day_008.jpg", "2d44757b-079c-4a78-a4a9-5fe6370466c8", "NOT AUTO-REUSED — Proof 01 and 02 both used this"),
    ("IH_DC_TMP_001_Render_Exterior_Day_009.jpg", "7696df34-0544-44b9-89f5-0d1b2523c412", "SELECTED — three Gothic portals + full spire + street threshold"),
    ("IH_DC_TMP_001_Render_Exterior_Day_010.jpg", "f491ee6e-de7d-4258-a153-4104e326b736", "aerial intersection — diagram"),
    ("IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg", "65f68756-a006-43d4-9c86-2c0ec25ad229", "dusk — Master 02 page-cut history"),
    ("IH_DC_TMP_001_Render_Living_Room_001.jpg", "c3d11c35-d8b7-485c-b216-0a4da68b751a", "interior looking-out — LOOKING CHAMBER history"),
    ("IH_DC_TMP_001_Render_Living_Room_002.jpeg", "bcf7b360-7078-44b6-a5f3-0e52372cdca9", "premium interior — generic without Temple exterior"),
    ("IH_DC_TMP_001_Render_Living_Room_003.jpeg", "caf8eb97-c767-4aa1-841b-759cf3500062", "intimate living — material, not civic"),
    ("IH_DC_TMP_001_Render_Living_Room_004.jpeg", "81922792-e644-4752-a5dd-70923311d9bb", "open living/kitchen — catalog risk"),
    ("IH_DC_TMP_001_Render_Living_Room_005.jpg", "8837fa06-d71b-4c26-a5cb-9cb682748311", "supporting interior"),
    ("IH_DC_TMP_001_Render_Living_Room_006.jpg", "a27e3c70-995f-48fc-965c-49fde9917b3f", "dusk interior — weak Temple proof"),
    ("IH_DC_TMP_001_Render_Bedroom_007.jpg", "2635b01e-6580-4511-82fe-a16fba510b41", "unit story"),
    ("IH_DC_TMP_001_Render_Bathroom_008.jpeg", "518a295f-f76f-40d8-b4b3-9a11cfbc7791", "amenity still"),
    ("01 Street Veiw.jpg", "376eeb12-5ef8-43d1-83a8-036c4ba0d1ac", "archival chapel — collage/split risk"),
)

DNA_USED = (
    {
        "filename": "ORNEK_00008.jpg",
        "principle": "Type may occupy darkness that already belongs to the photograph — never as a sticker.",
        "not_copied": "circle badges, Uniloft façade, gold serif luxury default",
    },
    {
        "filename": "ORNEK_00011.jpg",
        "principle": "A fact can be a graphic act attached to architecture, not a caption parked beside the building.",
        "not_copied": "Uniloft brick, Capitol walking-time pins, listing infographic",
    },
    {
        "filename": "ORNEK_00013.jpg",
        "principle": "Architecture is a page mass. A commercial proposition may occupy a designed field that is an actor.",
        "not_copied": "navy void, colonnade crop, UniLoft three-word stack, absence of price",
    },
    {
        "filename": "ORNEK_00015.jpg",
        "principle": "Headline weight contrast can live inside photographic material rather than on a UI plate.",
        "not_copied": "kitchen still-life, invented header veil, Uniloft interior",
    },
)


def _scores(**kwargs: int) -> dict[str, int]:
    base = {axis: 0 for axis in (
        "TEMPLE_SPECIFICITY",
        "VISUAL_MECHANISM",
        "PHOTO_OPPORTUNITY",
        "COMMERCIAL_MECHANISM",
        "TYPOGRAPHIC_OPPORTUNITY",
        "DEPTH_POTENTIAL",
        "READING_PATH",
        "BRAND_CHARACTER",
        "DISTINCTIVENESS",
        "PUBLISHABILITY_POTENTIAL",
    )}
    base.update(kwargs)
    return base


CONCEPTS: tuple[dict[str, Any], ...] = (
    {
        "id": "C1_THE_THRESHOLD",
        "name": "THE_THRESHOLD",
        "visual_mechanism": (
            "A tight 4:5 crop of Day_009 makes the three Gothic portals and the full spire the page. "
            "The building is not a backdrop; the openings are the campaign architecture."
        ),
        "project_photo_role": "Day_009 supplies the civic doorway, the lantern, street depth, and a sliver of the modern neighbor as conversion proof.",
        "primary_message": HEADLINE,
        "commercial_mechanism": (
            "%35 inhabits the left portal's own photographic dark. Price stands on the arrival street. "
            "CTA sits at the center threshold. The lockup cannot be lifted onto another property photo."
        ),
        "typographic_mechanism": (
            "One grotesque system. Headline as a dedication on the stone band above the arches. "
            "%35 as a monumental numeral scaled to one opening. Price as a ground-line proof. CTA as a door inscription."
        ),
        "offer_role": "Hero numeral inside the left Gothic void — the launch lives in the architecture.",
        "price_role": "Proof point on the civic pavement you stand on before entering.",
        "unit_role": "Supporting product line bound to price, not a third badge.",
        "cta_role": "Typographic close at the center door — the action is crossing the threshold.",
        "reading_path": "ARCHITECTURAL EVENT → GİRİNCE EV → %35 IN THE PORTAL → PRICE/UNIT ON THE STREET → PROJEYİ KEŞFET AT THE DOOR",
        "depth_mechanism": "Street and lawn → fence → three portals → tower → lantern → sky, with type occupying real architectural depths.",
        "memorable_gesture": "You do not read a listing. You see a temple door that is now a home, with the offer inside it.",
        "why_temple_specific": "Only The Temple photographs three Gothic sanctuary portals fused to a new Washington residence under a full civic spire.",
        "generic_offer_swap_test": "FAILS — another project's %35 would not belong in these openings; another façade has no such portals.",
        "designed_without_copy": True,
        "campaign_system_test": True,
        "scores": _scores(
            TEMPLE_SPECIFICITY=10,
            VISUAL_MECHANISM=9,
            PHOTO_OPPORTUNITY=9,
            COMMERCIAL_MECHANISM=9,
            TYPOGRAPHIC_OPPORTUNITY=9,
            DEPTH_POTENTIAL=9,
            READING_PATH=9,
            BRAND_CHARACTER=9,
            DISTINCTIVENESS=9,
            PUBLISHABILITY_POTENTIAL=9,
        ),
        "selected": True,
        "reject_reason": None,
    },
    {
        "id": "C2_THE_INSERTION",
        "name": "THE_INSERTION",
        "visual_mechanism": "Vertical slice of Day_001: new brick sandwiched between Scottish Rite and the Temple.",
        "project_photo_role": "Day_001 is the civic sandwich. The spire crown is already cropped.",
        "primary_message": "The residence is inserted into Washington stone.",
        "commercial_mechanism": "Facts would live on the inserted modern volume.",
        "typographic_mechanism": "Type on the grey brick as a cornerstone.",
        "offer_role": "On the new building.",
        "price_role": "On the new building.",
        "unit_role": "On the new building.",
        "cta_role": "On the new building.",
        "reading_path": "Three masses → facts on the middle mass.",
        "depth_mechanism": "Street, people, three civic masses.",
        "memorable_gesture": "A new building held by two monuments.",
        "why_temple_specific": "The product is literally inserted into Washington stone.",
        "generic_offer_swap_test": "PASSES — a left/center stack on the brick would still work on another modern façade.",
        "designed_without_copy": True,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=9,
            VISUAL_MECHANISM=8,
            PHOTO_OPPORTUNITY=7,
            COMMERCIAL_MECHANISM=6,
            TYPOGRAPHIC_OPPORTUNITY=7,
            DEPTH_POTENTIAL=7,
            READING_PATH=6,
            BRAND_CHARACTER=8,
            DISTINCTIVENESS=8,
            PUBLISHABILITY_POTENTIAL=6,
        ),
        "selected": False,
        "reject_reason": "Commercial collapses onto the modern volume as a portable stack — Proof 02 failure. Crown already cropped.",
    },
    {
        "id": "C3_THE_SPIRE_MEASURE",
        "name": "THE_SPIRE_MEASURE",
        "visual_mechanism": "Day_002 spire as a vertical measuring stick for value.",
        "project_photo_role": "Spire against large sky; Master 03 view history.",
        "primary_message": "This height is the product.",
        "commercial_mechanism": "Numbers as scale marks beside the shaft.",
        "typographic_mechanism": "Type in leftover sky.",
        "offer_role": "Sky numeral.",
        "price_role": "Sky or base caption.",
        "unit_role": "Caption.",
        "cta_role": "Caption.",
        "reading_path": "Spire → sky type.",
        "depth_mechanism": "Looking up; weak ground stage.",
        "memorable_gesture": "A needle in the sky.",
        "why_temple_specific": "The lantern is this sanctuary's.",
        "generic_offer_swap_test": "PASSES — sky type beside a tower is generic prestige.",
        "designed_without_copy": True,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=8,
            VISUAL_MECHANISM=7,
            PHOTO_OPPORTUNITY=7,
            COMMERCIAL_MECHANISM=5,
            TYPOGRAPHIC_OPPORTUNITY=6,
            DEPTH_POTENTIAL=6,
            READING_PATH=5,
            BRAND_CHARACTER=7,
            DISTINCTIVENESS=6,
            PUBLISHABILITY_POTENTIAL=5,
        ),
        "selected": False,
        "reject_reason": "Banned TYPE IN SKY. Commercial has no architectural home except leftover air.",
    },
    {
        "id": "C4_ROOF_LIVING",
        "name": "ROOF_LIVING",
        "visual_mechanism": "Day_007 aerial: gardens planted on the historic sanctuary roof.",
        "project_photo_role": "Altitude proof that people will live on this church.",
        "primary_message": "Inhabit the roof of a temple.",
        "commercial_mechanism": "Facts would sit in sky corners or as a diagram margin.",
        "typographic_mechanism": "Overview captions.",
        "offer_role": "Margin.",
        "price_role": "Margin.",
        "unit_role": "Margin.",
        "cta_role": "Margin.",
        "reading_path": "Spire from above → city ring → leftover labels.",
        "depth_mechanism": "City context ring, weak human threshold.",
        "memorable_gesture": "Gardens on a church.",
        "why_temple_specific": "These gardens sit on this sanctuary.",
        "generic_offer_swap_test": "PASSES — aerial + caption is portable.",
        "designed_without_copy": True,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=8,
            VISUAL_MECHANISM=8,
            PHOTO_OPPORTUNITY=7,
            COMMERCIAL_MECHANISM=5,
            TYPOGRAPHIC_OPPORTUNITY=5,
            DEPTH_POTENTIAL=7,
            READING_PATH=5,
            BRAND_CHARACTER=7,
            DISTINCTIVENESS=8,
            PUBLISHABILITY_POTENTIAL=6,
        ),
        "selected": False,
        "reject_reason": "Aerial canvases push commercial facts to a diagram. Not a lansman doorway.",
    },
    {
        "id": "C5_DUSK_MASS",
        "name": "DUSK_MASS",
        "visual_mechanism": "Sunset_001 silhouette as cinematic monument.",
        "project_photo_role": "Warm sky and dark mass — Master 02 page-cut history.",
        "primary_message": "Evening prestige.",
        "commercial_mechanism": "Type in sunset sky; facts on wet asphalt.",
        "typographic_mechanism": "Sky field + road footer.",
        "offer_role": "Sky.",
        "price_role": "Road.",
        "unit_role": "Road.",
        "cta_role": "Road.",
        "reading_path": "Glow → caption.",
        "depth_mechanism": "Dusk atmosphere.",
        "memorable_gesture": "A beautiful dusk.",
        "why_temple_specific": "The silhouette is this spire.",
        "generic_offer_swap_test": "PASSES — dusk poster + sales footer.",
        "designed_without_copy": True,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=8,
            VISUAL_MECHANISM=7,
            PHOTO_OPPORTUNITY=7,
            COMMERCIAL_MECHANISM=5,
            TYPOGRAPHIC_OPPORTUNITY=6,
            DEPTH_POTENTIAL=7,
            READING_PATH=5,
            BRAND_CHARACTER=7,
            DISTINCTIVENESS=6,
            PUBLISHABILITY_POTENTIAL=5,
        ),
        "selected": False,
        "reject_reason": "Repeats Master 02 sky-field logic. Poster + sales information.",
    },
    {
        "id": "C6_LOOKING_CHAMBER",
        "name": "LOOKING_CHAMBER",
        "visual_mechanism": "Living_Room_001 interior as the inhabited chamber.",
        "project_photo_role": "Furnished room looking to a generic city, not the Temple façade.",
        "primary_message": "Live here.",
        "commercial_mechanism": "Facts on a quiet wall.",
        "typographic_mechanism": "Interior editorial type.",
        "offer_role": "Wall.",
        "price_role": "Wall.",
        "unit_role": "Wall.",
        "cta_role": "Wall.",
        "reading_path": "Sofa → wall type.",
        "depth_mechanism": "Room to glass.",
        "memorable_gesture": "A nice apartment.",
        "why_temple_specific": "It is not. The Temple is not in the view.",
        "generic_offer_swap_test": "PASSES — any unit listing would fit.",
        "designed_without_copy": False,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=3,
            VISUAL_MECHANISM=4,
            PHOTO_OPPORTUNITY=5,
            COMMERCIAL_MECHANISM=4,
            TYPOGRAPHIC_OPPORTUNITY=6,
            DEPTH_POTENTIAL=7,
            READING_PATH=4,
            BRAND_CHARACTER=4,
            DISTINCTIVENESS=3,
            PUBLISHABILITY_POTENTIAL=3,
        ),
        "selected": False,
        "reject_reason": "Banned LOOKING CHAMBER. Not Temple-specific. Generic luxury editorial.",
    },
    {
        "id": "C7_DAY008_AGAIN",
        "name": "DAY008_AGAIN",
        "visual_mechanism": "Reuse Day_008 worm's-eye seam / plaza.",
        "project_photo_role": "Proof 01 letter and Proof 02 seam both used this asset.",
        "primary_message": "Arrival at the join.",
        "commercial_mechanism": "History of this photo is a left commercial column.",
        "typographic_mechanism": "Would be pulled toward the same plinth stack.",
        "offer_role": "Left stack.",
        "price_role": "Left stack.",
        "unit_role": "Left stack.",
        "cta_role": "Left stack.",
        "reading_path": "Seam → column.",
        "depth_mechanism": "Steps and upward thrust — strong, but already spent.",
        "memorable_gesture": "The join, again.",
        "why_temple_specific": "Yes, but it is the already-failed canvas.",
        "generic_offer_swap_test": "PASSES in practice — Proof 01 and 02 proved the lockup was portable.",
        "designed_without_copy": True,
        "campaign_system_test": False,
        "scores": _scores(
            TEMPLE_SPECIFICITY=9,
            VISUAL_MECHANISM=8,
            PHOTO_OPPORTUNITY=8,
            COMMERCIAL_MECHANISM=5,
            TYPOGRAPHIC_OPPORTUNITY=6,
            DEPTH_POTENTIAL=9,
            READING_PATH=5,
            BRAND_CHARACTER=8,
            DISTINCTIVENESS=6,
            PUBLISHABILITY_POTENTIAL=5,
        ),
        "selected": False,
        "reject_reason": "Do not automatically reuse Day_008. Proof 01 and Proof 02 already failed on this photograph.",
    },
)


def selected_concept() -> dict[str, Any]:
    return next(item for item in CONCEPTS if item.get("selected"))


def concept_passes_render_floors(concept: dict[str, Any]) -> bool:
    return bool(score_concept_evaluation(dict(concept.get("scores") or {})).get("pass"))


def concept_evaluation_json() -> dict[str, Any]:
    chosen = selected_concept()
    scored = [
        {
            "id": item["id"],
            "name": item["name"],
            "visual_mechanism": item["visual_mechanism"],
            "project_photo_role": item["project_photo_role"],
            "primary_message": item["primary_message"],
            "commercial_mechanism": item["commercial_mechanism"],
            "typographic_mechanism": item["typographic_mechanism"],
            "offer_role": item["offer_role"],
            "price_role": item["price_role"],
            "unit_role": item["unit_role"],
            "cta_role": item["cta_role"],
            "reading_path": item["reading_path"],
            "depth_mechanism": item["depth_mechanism"],
            "memorable_gesture": item["memorable_gesture"],
            "why_temple_specific": item["why_temple_specific"],
            "generic_offer_swap_test": item["generic_offer_swap_test"],
            "designed_without_copy": item["designed_without_copy"],
            "campaign_system_test": item["campaign_system_test"],
            "scores": item["scores"],
            "floor_check": score_concept_evaluation(item["scores"]),
            "selected": item["selected"],
            "reject_reason": item["reject_reason"],
        }
        for item in CONCEPTS
    ]
    return {
        "schema": "Phase114ConceptEvaluationV1",
        "pipeline": INTEGRATED_PIPELINE_ID,
        "hierarchy_starting_point": HIERARCHY,
        "floors": dict(RENDER_FLOORS),
        "policy": (
            "Do not create a visual idea and then ask where commercial information fits. "
            "Reject any concept whose commercial block would still work on another property photograph."
        ),
        "banned_devices": list(BANNED_DEVICES),
        "day_008_automatically_reused": False,
        "concepts": scored,
        "selected_id": chosen["id"],
        "selected_passes_floors": concept_passes_render_floors(chosen),
        "not_shown_as_ABC": True,
        "r1_created": False,
        "rendered_alternatives": False,
    }


def campaign_skeleton() -> dict[str, Any]:
    skeleton = {
        "schema": "CampaignSkeletonV1",
        "note": "Relationships, not coordinates. Editability follows art direction.",
        "elements": {
            "PRIMARY_HERO": {
                "ROLE": "The three Gothic portals and the full spire of The Temple — the civic doorway.",
                "VISUAL_WEIGHT": "dominant architectural mass",
                "RELATIONSHIP_TO_PHOTO": "Is the photograph. Day_009 crop is authored so the openings occupy the page.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "The stone band above the arches is the dedication ground for the headline.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "The viewer must meet the Temple as a door before any sales line.",
            },
            "PROJECT_BRAND": {
                "ROLE": "Real Temple logotype as civic signature.",
                "VISUAL_WEIGHT": "quiet, late",
                "RELATIONSHIP_TO_PHOTO": "Sits on the arrival lawn/street as a ground mark, not in leftover sky.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Hands the eye back to the portals, not into a lockup stack.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "Brand confirms whose door this is after the architecture has spoken.",
            },
            "PRIMARY_MESSAGE": {
                "ROLE": "GİRİNCE EV — the conversion thesis inscribed as a dedication.",
                "VISUAL_WEIGHT": "secondary hero, typographic",
                "RELATIONSHIP_TO_PHOTO": "Lives on the stone frieze / cornice band above the three openings, as if the building carries the line.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Sends the eye down into the left portal where the offer waits.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "A temple already writes on its lintel. The campaign message occupies that architectural job.",
            },
            "OFFER": {
                "ROLE": "%35 LANSMAN AVANTAJI as the commercial reveal inside a real opening.",
                "VISUAL_WEIGHT": "numeric hero",
                "RELATIONSHIP_TO_PHOTO": "Occupies the left Gothic void's own photographic dark. Not a badge. Not a leftover box.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "After the offer is seen in the architecture, value is confirmed on the ground.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "The launch is inside the Temple, not beside it.",
            },
            "PRICE": {
                "ROLE": "675.000 USD as the value you stand on before you enter.",
                "VISUAL_WEIGHT": "proof point",
                "RELATIONSHIP_TO_PHOTO": "Set on the street/pavement plane, aligned to arrival, not stacked under the offer.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Unit is bound to price as product confirmation.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "Price is the ground of the monument — what the threshold costs.",
            },
            "UNIT": {
                "ROLE": "2+1 DAİRE as the product of crossing the door.",
                "VISUAL_WEIGHT": "supporting",
                "RELATIONSHIP_TO_PHOTO": "Companion to price on the ground plane, not a third arch panel.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Hands the last step to the CTA at the center door.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "Names the residence that exists behind the sanctuary door.",
            },
            "CTA": {
                "ROLE": "PROJEYİ KEŞFET as the door inscription.",
                "VISUAL_WEIGHT": "action close",
                "RELATIONSHIP_TO_PHOTO": "Sits at the foot of the center portal — the threshold you would actually cross.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Closure may whisper at the base if the composition still has air.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "The action is entering. The CTA must complete that path, not sit in a column.",
            },
            "SUPPORTING_MESSAGE": {
                "ROLE": "WASHINGTON D.C. plus optional TARİHİN RUHU, GELECEĞİN DEĞERİ.",
                "VISUAL_WEIGHT": "micro / civic",
                "RELATIONSHIP_TO_PHOTO": "Location as a street-level civic line. Closure as a ground whisper, not a second headline.",
                "RELATIONSHIP_TO_NEXT_ELEMENT": "Ends the sequence.",
                "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "Places the door in Washington after the commercial path has resolved.",
            },
        },
        "status": "SET",
    }
    check = validate_campaign_skeleton(skeleton)
    if not check.get("pass"):
        raise RuntimeError(f"campaign skeleton immature: {check}")
    return skeleton


def reading_path() -> dict[str, Any]:
    path = {
        "schema": READING_PATH_SCHEMA,
        "stages": {
            "ENTRY_POINT": "The three Gothic portals and the rising spire of The Temple — architectural event.",
            "SECONDARY_ATTENTION": "GİRİNCE EV on the stone band — campaign message of conversion.",
            "COMMERCIAL_REVEAL": "%35 LANSMAN AVANTAJI inhabiting the left portal.",
            "VALUE_CONFIRMATION": "675.000 USD and 2+1 DAİRE on the arrival street.",
            "ACTION": "PROJEYİ KEŞFET at the center threshold.",
        },
        "abstract_flow": [
            "ARCHITECTURAL EVENT",
            "CAMPAIGN MESSAGE",
            "COMMERCIAL HOOK",
            "PRICE / PRODUCT",
            "ACTION",
        ],
        "forbidden_beat": "now here is the information column",
        "status": "SET",
    }
    check = validate_reading_path(path)
    if not check.get("pass"):
        raise RuntimeError(f"reading path incomplete: {check}")
    return path


def integrated_concept_record() -> dict[str, Any]:
    chosen = selected_concept()
    concept = {
        "schema": "IntegratedCampaignConceptV1",
        "status": "SET",
        "hierarchy": HIERARCHY,
        "name": CONCEPT_NAME,
        "answers": {
            "WHAT IS THE VISUAL IDEA?": chosen["visual_mechanism"],
            "WHAT DOES THE PROJECT PHOTO DO?": chosen["project_photo_role"],
            "WHAT IS THE PRIMARY SALES MESSAGE?": f"{HEADLINE} — enter, and it is a home. {REQUIRED_FACTS['discount']} lansman.",
            "HOW DOES THE SALES MESSAGE PARTICIPATE IN THE VISUAL IDEA?": chosen["commercial_mechanism"],
            "WHAT DOES THE VIEWER READ FIRST?": "The Temple doorway and spire.",
            "WHAT DOES THE VIEWER READ SECOND?": HEADLINE,
            "WHERE DOES THE OFFER LIVE AND WHY?": chosen["offer_role"],
            "HOW ARE PRICE AND UNIT DESIGNED INTO THE COMPOSITION?": f"{chosen['price_role']} {chosen['unit_role']}",
            "HOW DOES THE CTA complete the reading path?": chosen["cta_role"],
            "WHAT remains memorable after two seconds?": chosen["memorable_gesture"],
        },
        "evaluation": chosen["scores"],
        "skeleton": campaign_skeleton(),
        "render_allowed": False,
    }
    check = validate_integrated_concept(concept)
    concept["render_allowed"] = bool(check.get("pass"))
    concept["validation"] = check
    if not check.get("pass"):
        raise RuntimeError("integrated concept failed render gate")
    return concept


def numeric_direction() -> dict[str, Any]:
    assigned = assign_numeric_functions(hierarchy=HIERARCHY)
    # This concept honestly makes %35 a portal hero, not a rhythmic leftover.
    assigned = dict(assigned)
    assigned["assignment"] = {"%35": "hero", "675.000 USD": "proof_point", "2+1": "supporting_information"}
    assigned["why"] = (
        "Architecture-led here means the building authors the hierarchy. The left portal can carry a heroic %35 "
        "without becoming a sticker because the number occupies a real Gothic void. Price remains ground proof. "
        "2+1 must not compete as a third arch panel."
    )
    assigned["rendered"] = False
    return assigned


def selected_design_dna_text() -> str:
    return (
        "Principles only: type in photographic dark (00008); facts as acts attached to architecture (00011); "
        "building as page mass (00013); weight contrast inside photographic material (00015). "
        "No navy colonnade, no walking-time pins, no circle badges, no kitchen veil."
    )


def creative_strategy() -> dict[str, Any]:
    profile = project_photo_profile(asset_id=DAY009_ASSET_ID) or {}
    matching = match_design_dna(
        photo_profile=profile,
        campaign_objective="civic prestige residential launch for The Temple in Washington D.C.",
        target_emotion="crossing a sanctuary door into a home",
        visual_opportunity="three Gothic portals as commercial architecture",
    )
    strategy = {
        "schema": SCHEMA,
        "status": "SET",
        "layout_forbidden_until_strategy_exists": False,
        "pipeline_id": INTEGRATED_PIPELINE_ID,
        "hierarchy": HIERARCHY,
        "user_request": USER_REQUEST,
        "project_story": (
            "The Temple is a historic Washington sanctuary given a second life as a residence. "
            "The street still meets three Gothic doors under a civic spire. That doorway is the product."
        ),
        "campaign_objective": "Launch The Temple as a premium Washington D.C. residence with a %35 lansman advantage.",
        "target_emotion": "The awe of entering a monument that is now a home.",
        "primary_message": "Girince ev — once you cross this temple door, it is a residence.",
        "commercial_message": (
            f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']} · "
            f"{REQUIRED_FACTS['list_price']} · {REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']} · "
            f"{REQUIRED_FACTS['cta']}"
        ),
        "available_real_assets": [
            {"filename": name, "asset_id": aid, "note": note} for name, aid, note in OPPORTUNITY_ASSETS
        ],
        "strongest_project_characteristic": (
            "The Temple still presents a real sanctuary doorway at street level. "
            "No other Washington residential lansman owns three Gothic portals under a full spire."
        ),
        "selected_design_dna": selected_design_dna_text(),
        "creative_tension": "A church door that sells a 2+1 — monumentality holding a contemporary offer without becoming a sticker.",
        "visual_idea": CONCEPT_SENTENCE,
        "why_this_idea_fits_this_project": (
            "Architecture-led cannot mean a large building photo plus a text column. "
            "The Temple's actual doors must author brand, headline, offer, price, unit, and CTA as one path."
        ),
        "selected_real_assets": [
            {
                "filename": DAY009_FILENAME,
                "asset_id": DAY009_ASSET_ID,
                "role": "full-frame civic doorway — three portals, lantern, street threshold, conversion neighbor as sliver",
            }
        ],
        "relevant_design_dna": list(DNA_USED),
        "commercial_design_dna": commercial_design_dna_library()["note"],
        "memorable_gesture": TWO_SECOND,
        "two_second_impression": TWO_SECOND,
        "headline": HEADLINE,
        "headline_origin": "NEW — short Turkish conversion line required by the doorway concept; no invented financial claims",
        "closure": APPROVED_BOTTOM_COPY,
        "brand": "Temple logo only — fulfills THE TEMPLE",
        "typography_reason": (
            "One civic grotesque system, not inherited Master serif and not Proof 02 Source-on-plinth. "
            "Scale is assigned by architectural job: dedication, portal numeral, ground proof, door action."
        ),
        "numeric_art_direction": numeric_direction(),
        "reference_match": matching,
        "not_reused": list(BANNED_DEVICES),
        "proof_01": "PRESERVED / REJECTED",
        "proof_02": "PRESERVED / REJECTED",
        "learning": stage3_failure_learning_v2(),
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


def visual_idea_record(*, feels_designed: bool) -> dict[str, Any]:
    return visual_idea_gate(
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
                "reference_id": dna["reference_id"],
                "media_asset_id": dna["media_asset_id"],
                "transferable_principle": item["principle"],
                "not_copied": item["not_copied"],
                "strength_score": dna["strength_score"],
            }
        )
    used = {row["filename"] for row in DNA_USED}
    return {
        "schema": "Phase114DesignDNASelectionV1",
        "policy": "Transferable commercial and visual principles only. Do not reproduce a reference layout.",
        "used": records,
        "unused_grade_a": [
            {
                "filename": item["filename"],
                "reference_id": item["reference_id"],
                "reason": "not the primary mechanism for a doorway-as-campaign-grid",
            }
            for item in grade_a_design_dna()
            if item["filename"] not in used
        ],
    }
