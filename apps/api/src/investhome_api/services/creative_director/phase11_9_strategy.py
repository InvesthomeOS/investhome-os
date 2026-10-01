"""Phase 11.9 — text-only Hybrid V2 concepts. One selected campaign system.

Does not render alternatives. Does not reuse THE_LEDGER, Proofs, or Masters.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile

DAY009_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_009.jpg"
DAY009_ASSET_ID = "7696df34-0544-44b9-89f5-0d1b2523c412"
# Tight enough to keep lantern + inhabited brick; not Proof 03's portal crop.
DAY009_CROP = {"left": 0.20, "top": 0.00, "width": 0.58, "height": 0.86}

CONCEPT_NAME = "THE_REGISTER"
HEADLINE = "MERTEBE"
CONCEPT_SENTENCE = (
    "The Temple is the measuring instrument of the lansman: the lantern is the high mark, "
    "the inhabited 2+1 mass is the value, and %35 is the calibration the architecture crosses."
)
TWO_SECOND = "A real Temple standing inside a luminous register — %35 is the altitude the lantern occupies."
USER_REQUEST = (
    "The Temple için premium, yaratıcı ve gerçekten yayınlanabilecek bir lansman reklamı hazırla."
)

SELECTION_FLOORS = {
    "TEMPLE_SPECIFICITY": 9,
    "VISUAL_IDEA": 9,
    "HYBRID_CAPABILITY_USE": 9,
    "PHOTO_FIELD_RELATIONSHIP": 9,
    "COMMERCIAL_MECHANISM": 9,
    "TYPOGRAPHIC_POTENTIAL": 9,
    "PERSUASION": 9,
    "DISTINCTIVENESS": 9,
    "PUBLISHABILITY_POTENTIAL": 9,
}

BANNED_MECHANISMS = (
    "Proof 01 architecture-as-letter",
    "Proof 02 historic/new join lockup",
    "Proof 03 threshold/portal campaign",
    "THE_LEDGER paper collage",
    "THE_LEDGER R1 / R2",
    "Master 01 sky type on Day_003",
    "Master 02",
    "Master 03",
    "building cutout on background",
    "photo + typography",
    "editorial poster",
    "brochure cover",
    "property listing",
    "website hero",
    "sale poster",
    "luxury template",
    "split screen",
    "floating information system",
    "paper collage",
    "fact stack",
    "thermometer / ruler infographic",
    "independent left fact stack",
    "price card",
    "%35 badge",
    "website CTA button",
)

HARD_GATE_REDUCTIONS = (
    "building cutout on background",
    "photo + typography",
    "editorial poster",
    "brochure cover",
    "property listing",
    "website hero",
    "sale poster",
    "luxury template",
    "split screen",
    "floating information system",
    "paper collage",
    "fact stack",
)


def _scores(**kwargs: int) -> dict[str, int]:
    keys = (
        "TEMPLE_SPECIFICITY",
        "VISUAL_IDEA",
        "HYBRID_CAPABILITY_USE",
        "PHOTO_FIELD_RELATIONSHIP",
        "COMMERCIAL_MECHANISM",
        "TYPOGRAPHIC_POTENTIAL",
        "PERSUASION",
        "DEPTH",
        "DISTINCTIVENESS",
        "THUMBNAIL_POTENTIAL",
        "PUBLISHABILITY_POTENTIAL",
    )
    return {key: int(kwargs[key]) for key in keys}


def _meets_selection(scores: dict[str, int]) -> bool:
    return all(int(scores.get(axis, 0)) >= floor for axis, floor in SELECTION_FLOORS.items())


def hybrid_v2_concepts() -> list[dict[str, Any]]:
    """Seven text-only concepts. Only THE_REGISTER is eligible to render."""
    return [
        {
            "key": "C1",
            "name": "THE_REGISTER",
            "headline": HEADLINE,
            "big_idea": CONCEPT_SENTENCE,
            "why_temple_specific": (
                "Only this monument has a lantern-to-residence vertical that can act as a civic mertebe: "
                "the historic degree at the crown and the 2+1 at the inhabited mass."
            ),
            "real_photo_role": (
                "Day_009 extracted as a full monument object (lantern + arches + brick wing). "
                "Not Proof 03's portal crop. The architecture is the needle of the register."
            ),
            "generated_field_role": (
                "A vertical luminous mineral atmosphere — oxide/limestone dust light, not vellum. "
                "The field is the register chamber the monument occupies, not a backdrop behind a sticker."
            ),
            "typographic_role": (
                "Type is three altitudes of the same instrument: identity names the register, "
                "%35 is the high calibration, price/unit is the inhabited mark, CTA is the ground instruction."
            ),
            "commercial_mechanism": (
                "%35 lives in the field at lantern height and is occluded by stone. "
                "675.000 USD and 2+1 DAİRE sit at the residential mass. CTA sits at contact."
            ),
            "percent_role": "The calibration the lantern crosses — printed in the atmosphere, interrupted by real stone.",
            "price_role": "The inhabited mark — value of the 2+1 mass, not a footer.",
            "unit_role": "Paired on the same altitude as price; the product the mertebe measures.",
            "cta_role": "Ground instruction at the contact plane where the monument meets the field.",
            "depth_material": (
                "Monument in front of the luminous shaft; atmosphere wraps the feet; "
                "%35 behind stone; no full-silhouette drop shadow."
            ),
            "reading_path": [
                "Temple object occupying the luminous register",
                "%35 at lantern altitude, occluded by stone",
                "MERTEBE / THE TEMPLE as the instrument name",
                "675.000 USD + 2+1 DAİRE at the inhabited mass",
                "PROJEYİ KEŞFET at contact",
            ],
            "two_second_event": TWO_SECOND,
            "memorable_gesture": "Architecture as the lansman gauge — not a captioned building.",
            "persuasion_mechanism": (
                "Desirability from the real monument; meaning of %35 from its altitude on that monument; "
                "what you buy from price sitting on the 2+1 mass; next step from the ground CTA."
            ),
            "project_photo": DAY009_FILENAME,
            "asset_id": DAY009_ASSET_ID,
            "selected": True,
            "hard_gate": "PASS",
            "reject_reason": None,
            "scores": _scores(
                TEMPLE_SPECIFICITY=10,
                VISUAL_IDEA=9,
                HYBRID_CAPABILITY_USE=9,
                PHOTO_FIELD_RELATIONSHIP=9,
                COMMERCIAL_MECHANISM=9,
                TYPOGRAPHIC_POTENTIAL=9,
                PERSUASION=9,
                DEPTH=9,
                DISTINCTIVENESS=9,
                THUMBNAIL_POTENTIAL=9,
                PUBLISHABILITY_POTENTIAL=9,
            ),
        },
        {
            "key": "C2",
            "name": "THE_CIVIC_INSERT",
            "headline": "ARA KAT",
            "big_idea": "Day_001's modern brick mass is extracted as the insert between two historic civic walls.",
            "why_temple_specific": "The Temple is literally the new fabric keyed into a historic Washington block.",
            "real_photo_role": "Extract only the grey-brick volume from Day_001.",
            "generated_field_role": "Two generated limestone atmosphere flanks — invented civic stone. Forbidden.",
            "typographic_role": "Type as the mortar joint between flanks.",
            "commercial_mechanism": "Offer as the joint — reads as Proof 02's historic/new lockup.",
            "percent_role": "Joint numeral.",
            "price_role": "Caption on the insert.",
            "unit_role": "Caption on the insert.",
            "cta_role": "Footer under the block.",
            "depth_material": "Three slabs — collage / split screen.",
            "reading_path": ["insert", "flanks", "facts"],
            "two_second_event": "A new building between two old ones.",
            "memorable_gesture": "The join — already used and rejected as Proof 02.",
            "persuasion_mechanism": "Weak: identity is the neighbor buildings, not the offer.",
            "project_photo": "IH_DC_TMP_001_Render_Exterior_Day_001.jpg",
            "asset_id": "5d26caf3-c237-4a78-9f3a-91f05dd24fa2",
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Reduces to Proof 02 historic/new join and a building cutout between generated flanks.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=8,
                VISUAL_IDEA=7,
                HYBRID_CAPABILITY_USE=7,
                PHOTO_FIELD_RELATIONSHIP=6,
                COMMERCIAL_MECHANISM=6,
                TYPOGRAPHIC_POTENTIAL=6,
                PERSUASION=6,
                DEPTH=7,
                DISTINCTIVENESS=5,
                THUMBNAIL_POTENTIAL=7,
                PUBLISHABILITY_POTENTIAL=6,
            ),
        },
        {
            "key": "C3",
            "name": "THE_LANTERN_GAUGE",
            "headline": "İĞNE",
            "big_idea": "Day_002 spire isolated as a needle piercing a generated light field; %35 is the puncture.",
            "why_temple_specific": "The lantern is unique, but Day_002 is Master 03's photograph and THE_NEEDLE was already rejected.",
            "real_photo_role": "Spire-only extract from Day_002.",
            "generated_field_role": "Sheet or atmosphere the needle punctures.",
            "typographic_role": "Offer as puncture wound.",
            "commercial_mechanism": "Puncture is the offer — no 2+1 intimacy.",
            "percent_role": "The hole.",
            "price_role": "Label beside the needle.",
            "unit_role": "Detached.",
            "cta_role": "Detached.",
            "depth_material": "Needle on field — cutout risk.",
            "reading_path": ["needle", "puncture", "facts"],
            "two_second_event": "A spire sticker.",
            "memorable_gesture": "THE_NEEDLE leftover.",
            "persuasion_mechanism": "Iconic but not a residential sale.",
            "project_photo": "IH_DC_TMP_001_Render_Exterior_Day_002.jpg",
            "asset_id": "543aeb03-c4c9-46f9-9d9f-81bf53f45438",
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Master 03 photograph + previously rejected THE_NEEDLE. Building cutout on field.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=8,
                VISUAL_IDEA=7,
                HYBRID_CAPABILITY_USE=8,
                PHOTO_FIELD_RELATIONSHIP=7,
                COMMERCIAL_MECHANISM=6,
                TYPOGRAPHIC_POTENTIAL=7,
                PERSUASION=6,
                DEPTH=7,
                DISTINCTIVENESS=6,
                THUMBNAIL_POTENTIAL=8,
                PUBLISHABILITY_POTENTIAL=6,
            ),
        },
        {
            "key": "C4",
            "name": "THE_INHABITED_SLICE",
            "headline": "KAT",
            "big_idea": "Crop only Day_009's modern brick wing as the 2+1 product object on a color field.",
            "why_temple_specific": "Without the lantern the object is any new apartment building.",
            "real_photo_role": "Brick wing extract.",
            "generated_field_role": "Neutral editorial field.",
            "typographic_role": "Listing stack beside the wing.",
            "commercial_mechanism": "Price next to a façade crop — property listing.",
            "percent_role": "Badge.",
            "price_role": "Listing price.",
            "unit_role": "Listing unit.",
            "cta_role": "Website button.",
            "depth_material": "Photo card.",
            "reading_path": ["façade", "facts"],
            "two_second_event": "An apartment listing.",
            "memorable_gesture": "None.",
            "persuasion_mechanism": "Catalogue, not campaign.",
            "project_photo": DAY009_FILENAME,
            "asset_id": DAY009_ASSET_ID,
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Property listing / photo card. Temple identity lost without the lantern.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=4,
                VISUAL_IDEA=4,
                HYBRID_CAPABILITY_USE=5,
                PHOTO_FIELD_RELATIONSHIP=4,
                COMMERCIAL_MECHANISM=5,
                TYPOGRAPHIC_POTENTIAL=4,
                PERSUASION=5,
                DEPTH=4,
                DISTINCTIVENESS=3,
                THUMBNAIL_POTENTIAL=5,
                PUBLISHABILITY_POTENTIAL=4,
            ),
        },
        {
            "key": "C5",
            "name": "THE_CHAMBER_INTERVAL",
            "headline": "ODA",
            "big_idea": "Living_Room_001 extracted as a furnished object inside a generated mineral atmosphere.",
            "why_temple_specific": "Interior could be any luxury unit; window city is not Temple architecture we may invent around.",
            "real_photo_role": "Interior object.",
            "generated_field_role": "Dusk mineral field.",
            "typographic_role": "Caption to the chamber.",
            "commercial_mechanism": "Price as furniture label.",
            "percent_role": "Attached numeral.",
            "price_role": "Listing.",
            "unit_role": "Listing.",
            "cta_role": "Explore the room.",
            "depth_material": "Interior card in a void.",
            "reading_path": ["sofa", "facts"],
            "two_second_event": "A furniture ad.",
            "memorable_gesture": "THE_CHAMBER_CUT leftover.",
            "persuasion_mechanism": "Lifestyle, not lansman.",
            "project_photo": "IH_DC_TMP_001_Render_Living_Room_001.jpg",
            "asset_id": "c3d11c35-d8b7-485c-b216-0a4da68b751a",
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Interior listing / photo card. Previously rejected as THE_CHAMBER_CUT.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=6,
                VISUAL_IDEA=6,
                HYBRID_CAPABILITY_USE=7,
                PHOTO_FIELD_RELATIONSHIP=6,
                COMMERCIAL_MECHANISM=5,
                TYPOGRAPHIC_POTENTIAL=6,
                PERSUASION=5,
                DEPTH=7,
                DISTINCTIVENESS=5,
                THUMBNAIL_POTENTIAL=6,
                PUBLISHABILITY_POTENTIAL=5,
            ),
        },
        {
            "key": "C6",
            "name": "THE_CROSSWALK_PLANE",
            "headline": "EŞİK",
            "big_idea": "Generated shadow-floor as a civic plane; Day_009 monument stands on it like a website hero.",
            "why_temple_specific": "Street monument is Temple, but the mechanism is a 3D product shot.",
            "real_photo_role": "Full cutout on a generated ground plane.",
            "generated_field_role": "Horizonless floor + gradient.",
            "typographic_role": "Hero overlay.",
            "commercial_mechanism": "Facts float over the plane.",
            "percent_role": "Hero numeral.",
            "price_role": "Hero price.",
            "unit_role": "Hero unit.",
            "cta_role": "Website CTA.",
            "depth_material": "Sticker on a floor — floating building.",
            "reading_path": ["building", "floor", "overlay facts"],
            "two_second_event": "Luxury website hero.",
            "memorable_gesture": "None — template.",
            "persuasion_mechanism": "Generic prestige.",
            "project_photo": DAY009_FILENAME,
            "asset_id": DAY009_ASSET_ID,
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Website hero / building cutout on generated ground. Floating information system.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=7,
                VISUAL_IDEA=5,
                HYBRID_CAPABILITY_USE=6,
                PHOTO_FIELD_RELATIONSHIP=4,
                COMMERCIAL_MECHANISM=5,
                TYPOGRAPHIC_POTENTIAL=5,
                PERSUASION=5,
                DEPTH=5,
                DISTINCTIVENESS=4,
                THUMBNAIL_POTENTIAL=6,
                PUBLISHABILITY_POTENTIAL=5,
            ),
        },
        {
            "key": "C7",
            "name": "THE_GOLDEN_FINIAL",
            "headline": "TEPE",
            "big_idea": "Generated dusk atmosphere; type lives at the finial like leftover-sky poster work.",
            "why_temple_specific": "Finial is Temple, mechanism is cinematic poster.",
            "real_photo_role": "Silhouette or full monument in dusk field.",
            "generated_field_role": "Sunset color field — Master 02 / THE_DUSK_RELIQUARY family.",
            "typographic_role": "Sky type.",
            "commercial_mechanism": "Offer as glow — poster + sales.",
            "percent_role": "Sky numeral.",
            "price_role": "Attached.",
            "unit_role": "Attached.",
            "cta_role": "Attached.",
            "depth_material": "Poster melt.",
            "reading_path": ["sky", "silhouette", "facts"],
            "two_second_event": "A dusk poster.",
            "memorable_gesture": "Already rejected as THE_DUSK_RELIQUARY.",
            "persuasion_mechanism": "Mood without commercial system.",
            "project_photo": "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg",
            "asset_id": "65f68756-a006-43d4-9c86-2c0ec25ad229",
            "selected": False,
            "hard_gate": "REJECT",
            "reject_reason": "Editorial poster / leftover-sky type. Master 02 photograph family.",
            "scores": _scores(
                TEMPLE_SPECIFICITY=7,
                VISUAL_IDEA=6,
                HYBRID_CAPABILITY_USE=6,
                PHOTO_FIELD_RELATIONSHIP=6,
                COMMERCIAL_MECHANISM=5,
                TYPOGRAPHIC_POTENTIAL=6,
                PERSUASION=5,
                DEPTH=7,
                DISTINCTIVENESS=5,
                THUMBNAIL_POTENTIAL=7,
                PUBLISHABILITY_POTENTIAL=5,
            ),
        },
    ]


def selected_concept() -> dict[str, Any]:
    chosen = next(item for item in hybrid_v2_concepts() if item["selected"])
    if chosen.get("hard_gate") != "PASS":
        raise RuntimeError("Selected concept failed the hard gate")
    if not _meets_selection(dict(chosen.get("scores") or {})):
        raise RuntimeError("Selected concept failed selection floors")
    return chosen


def concept_selection_status() -> str:
    try:
        selected_concept()
    except RuntimeError:
        return "HYBRID_V2_CREATIVE_FAIL"
    eligible = [item for item in hybrid_v2_concepts() if item["selected"] and _meets_selection(item["scores"])]
    if len(eligible) != 1:
        return "HYBRID_V2_CREATIVE_FAIL"
    return "SELECTED"


def concept_evaluation_json() -> dict[str, Any]:
    concepts = hybrid_v2_concepts()
    status = concept_selection_status()
    return {
        "schema": "Phase119ConceptEvaluation",
        "engine": ENGINE_ID,
        "user_request": USER_REQUEST,
        "banned_mechanisms": list(BANNED_MECHANISMS),
        "hard_gate_reductions": list(HARD_GATE_REDUCTIONS),
        "rendered_alternatives": False,
        "selection_floors": dict(SELECTION_FLOORS),
        "concepts": concepts,
        "selected": CONCEPT_NAME if status == "SELECTED" else None,
        "status": status,
        "photo_profile": project_photo_profile(asset_id=DAY009_ASSET_ID),
        "why_not_day_003": "Day_003 is Master 01 and THE_LEDGER. Do not auto-select it.",
        "why_not_paper": "V1 already used archival vellum. V2 field must be a new non-project language.",
        "learning_applied": (
            "The relationship between project object, generated field, and commercial information "
            "must itself be the idea. Do not cut out a building, generate a background, and add text."
        ),
    }


def campaign_system_v2() -> dict[str, Any]:
    chosen = selected_concept()
    facts = {
        "project": "THE TEMPLE",
        "location": "WASHINGTON D.C.",
        "offer": f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "unit": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "cta": REQUIRED_FACTS["cta"],
        "closure": APPROVED_BOTTOM_COPY,
        "headline": HEADLINE,
    }
    return {
        "schema": "CampaignSystemV2",
        "engine": ENGINE_ID,
        "concept_name": CONCEPT_NAME,
        "headline": HEADLINE,
        "big_idea": CONCEPT_SENTENCE,
        "two_second": TWO_SECOND,
        "facts": facts,
        "elements": {
            "VISUAL_HERO": {
                "what": "Real Day_009 Temple monument occupying a generated luminous register",
                "real_project_object": "extracted lantern + arches + inhabited brick wing",
                "generated_field": "vertical mineral light shaft the monument stands inside",
                "other_typography": "object occludes %35; object is the scale the type measures",
                "reading_path": "first beat",
            },
            "BRAND": {
                "what": "THE TEMPLE / WASHINGTON D.C. as the instrument's name, plus real logo at contact",
                "real_project_object": "logo is the real Temple mark, not redrawn",
                "generated_field": "identity sits in the upper atmosphere, not on a header bar",
                "other_typography": "names the register that MERTEBE and %35 belong to",
                "reading_path": "with or immediately after the object",
            },
            "MESSAGE": {
                "what": HEADLINE,
                "real_project_object": "names the lantern-to-residence degree",
                "generated_field": "set in the atmosphere beside the shaft, not a poster title block",
                "other_typography": "smaller than %35; larger than location",
                "reading_path": "after identity, before or with the offer altitude",
            },
            "COMMERCIAL_HOOK": {
                "what": REQUIRED_FACTS["discount"],
                "real_project_object": "occluded by the lantern / upper stone",
                "generated_field": "printed into the luminous column at high altitude",
                "other_typography": "largest numeral; LANSMAN AVANTAJI is its caption at the same altitude",
                "reading_path": "second beat — why it is interesting",
            },
            "PRICE": {
                "what": REQUIRED_FACTS["list_price"],
                "real_project_object": "aligned to the inhabited brick / arched mass",
                "generated_field": "sits in the shaft at mid-low altitude, not a footer plate",
                "other_typography": "same baseline as unit",
                "reading_path": "third beat — what it costs",
            },
            "PRODUCT": {
                "what": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
                "real_project_object": "the brick residential wing is the 2+1 being sold",
                "generated_field": "shares PRICE altitude",
                "other_typography": "grouped with price; never an independent stack",
                "reading_path": "with price — what you are buying",
            },
            "ACTION": {
                "what": REQUIRED_FACTS["cta"],
                "real_project_object": "at the feet / contact of the monument",
                "generated_field": "on the contact atmosphere, with a hairline cue",
                "other_typography": "last commercial beat; not a button",
                "reading_path": "fourth beat — what to do",
            },
            "SUPPORTING_MESSAGE": {
                "what": APPROVED_BOTTOM_COPY,
                "real_project_object": "none — closure of the instrument",
                "generated_field": "quiet line under contact",
                "other_typography": "smallest; after CTA",
                "reading_path": "close",
            },
        },
        "no_independent_information_zones": True,
        "selected_real_assets": [
            {
                "filename": DAY009_FILENAME,
                "asset_id": DAY009_ASSET_ID,
                "role": "full monument register needle",
                "crop": dict(DAY009_CROP),
                "not": "Proof 03 portal crop; not Day_003 ledger object",
            }
        ],
        "generated_field": {
            "language": "vertical luminous mineral / oxide atmosphere",
            "not": "vellum, archival paper, document, sky with clouds, buildings",
        },
        "reading_path": list(chosen["reading_path"]),
        "banned_mechanisms": list(BANNED_MECHANISMS),
        "selected_concept": chosen,
    }
