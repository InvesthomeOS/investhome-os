"""Phase 11.2 — new idea from Temple character. Not a Proof 01 revision."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_design_dna_v2 import grade_a_design_dna
from investhome_api.services.creative_director.creative_failure_learning_v1 import PHASE_11_1_LEARNING
from investhome_api.services.creative_director.creative_strategy_v1 import SCHEMA, STRATEGY_FIELDS, validate_creative_strategy
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID, no_copy_test, two_second_test
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile
from investhome_api.services.creative_director.reference_matching_v1 import match_design_dna

DAY008_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_008.jpg"
DAY008_ASSET_ID = "2d44757b-079c-4a78-a4a9-5fe6370466c8"

HEADLINE_LINE_1 = "İKİ ÇAĞ"
HEADLINE_LINE_2 = "BİR ADRES"
HEADLINE = f"{HEADLINE_LINE_1} {HEADLINE_LINE_2}"
CONCEPT_NAME = "THE_SEAM"
CONCEPT_SENTENCE = (
    "The Temple campaign is the photographed join of historic sanctuary stone and the new "
    "residential brick — two ages sharing one address, with the launch living on the new building."
)
TWO_SECOND = (
    "Historic stone and new brick meeting at one Washington address, with the launch inscribed "
    "on the modern volume like a cornerstone."
)
USER_REQUEST = "The Temple için gerçekten premium, kreatif bir lansman reklamı hazırla."

BANNED_DEVICES = (
    "architecture as a letter",
    "building replacing a glyph",
    "TARİH typography mechanism",
    "TYPE IN SKY",
    "EDITORIAL PAGE CUT",
    "LOOKING CHAMBER",
    "split screen",
    "photo card",
    "dark header",
    "brochure cover",
    "property listing",
    "website hero",
    "generic luxury editorial",
)

# All approved real Temple photographs. Do not favor previously used images.
OPPORTUNITY_ASSETS = (
    ("IH_DC_TMP_001_Render_Exterior_Day_001.jpg", "5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "civic sandwich: modern inserted between two historic masses — spire crown cropped"),
    ("IH_DC_TMP_001_Render_Exterior_Day_002.jpg", "543aeb03-c4c9-46f9-9d9f-81bf53f45438", "spire + modern neighbor + Scottish Rite — Master 03 view history"),
    ("IH_DC_TMP_001_Render_Exterior_Day_003.jpg", "7346e259-f999-4fbb-a8d5-63708d4e0c81", "quiet sky — Master 01 type-in-sky history"),
    ("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "299bd265-a0ea-486d-866d-1947f103fd57", "aerial block — cartographic, low intimacy"),
    ("IH_DC_TMP_001_Render_Exterior_Day_005.jpg", "07863b0f-22e8-43c6-a629-7ceca7651b16", "aerial neighborhood — location proof only"),
    ("IH_DC_TMP_001_Render_Exterior_Day_007.jpg", "c0afa1bf-b487-410c-be3d-91c31852550d", "high oblique: gardens on the sanctuary roof"),
    ("IH_DC_TMP_001_Render_Exterior_Day_008.jpg", "2d44757b-079c-4a78-a4a9-5fe6370466c8", "SELECTED — worm's-eye seam + arrival steps + full spire + modern brick"),
    ("IH_DC_TMP_001_Render_Exterior_Day_009.jpg", "7696df34-0544-44b9-89f5-0d1b2523c412", "street monument with modern neighbor — Master-used, strong seam, weaker steps"),
    ("IH_DC_TMP_001_Render_Exterior_Day_010.jpg", "f491ee6e-de7d-4258-a153-4104e326b736", "aerial intersection — diagram"),
    ("IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg", "65f68756-a006-43d4-9c86-2c0ec25ad229", "dusk silhouette — Master 02 page-cut history"),
    ("IH_DC_TMP_001_Render_Living_Room_001.jpg", "c3d11c35-d8b7-485c-b216-0a4da68b751a", "looking-out interior — LOOKING CHAMBER history"),
    ("IH_DC_TMP_001_Render_Living_Room_002.jpeg", "bcf7b360-7078-44b6-a5f3-0e52372cdca9", "premium interior volume — generic without Temple exterior"),
    ("IH_DC_TMP_001_Render_Living_Room_003.jpeg", "caf8eb97-c767-4aa1-841b-759cf3500062", "intimate living corner — material, not civic identity"),
    ("IH_DC_TMP_001_Render_Living_Room_004.jpeg", "81922792-e644-4752-a5dd-70923311d9bb", "open living/kitchen — residential catalog risk"),
    ("IH_DC_TMP_001_Render_Living_Room_005.jpg", "8837fa06-d71b-4c26-a5cb-9cb682748311", "supporting interior"),
    ("IH_DC_TMP_001_Render_Living_Room_006.jpg", "a27e3c70-995f-48fc-965c-49fde9917b3f", "dusk bedroom/living — material, weak Temple proof"),
    ("IH_DC_TMP_001_Render_Bedroom_007.jpg", "2635b01e-6580-4511-82fe-a16fba510b41", "terracotta chamber — unit story"),
    ("IH_DC_TMP_001_Render_Bathroom_008.jpeg", "518a295f-f76f-40d8-b4b3-9a11cfbc7791", "amenity still — not campaign"),
    ("01 Street Veiw.jpg", "376eeb12-5ef8-43d1-83a8-036c4ba0d1ac", "archival Washington Chapel — heritage, collage/split risk"),
)

DNA_USED = (
    {
        "filename": "ORNEK_00008.jpg",
        "reference_id": "1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2",
        "principle": "Type can live in the building's own shadow rather than on a header.",
        "not_copied": "dusk serif default, circular offer badges, Uniloft façade, gold luxury serif as default",
    },
    {
        "filename": "ORNEK_00013.jpg",
        "reference_id": "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57",
        "principle": "A photograph may be a structural page mass, not a backdrop.",
        "not_copied": "navy field, colonnade crop, DÜZENLİ/GÜVENLİ/PRESTİJLİ stack, UniLoft",
    },
    {
        "filename": "ORNEK_00015.jpg",
        "reference_id": "b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd",
        "principle": "A gradient is legitimate when it continues the photograph's own light, not when it is a UI overlay.",
        "not_copied": "kitchen still-life, top-down dark lid as a header, Uniloft interior",
    },
)


def character_study_markdown() -> str:
    return """# Temple character study

Observation from the real approved library, before concept.

## What is actually unique

The Temple is not a generic luxury façade. The library shows a **historic Washington sanctuary** (tan carved stone, Gothic arches, a full civic spire) **physically joined to a new residential volume** (grey brick, rectangular windows, terraces). The join is visible in Day_001, Day_002, Day_008, Day_009, and Day_007. That adjacency is the project.

Secondary truths, not all used:
- Vertical monumentality of the spire (Day_002, Day_008, Day_009)
- Arrival: plaza, lawn, steps, human scale (Day_008 strongest)
- Interior modern living that could belong to any premium unit unless the exterior is present
- Archival street photograph of Washington Chapel (heritage, but a second-photo collage risk)
- Aerial gardens planted on the historic roof (Day_007) — intimate living on sacred fabric, weak as a commercial launch canvas

## Strongest actual opportunity

**The seam.** One photograph already contains historic stone, new brick, arrival ground, people, and the spire. The campaign does not need to invent a graphic letter, a page cut, or a looking chamber. The project’s character is the join.

Day_008 is selected because it is the only unused-as-identity crop that still holds:
- full spire (Day_001 crops the crown)
- processional steps as foreground depth
- modern brick in the same frame
- street life as scale

Proof 01 used Day_008 as an isolated letter İ. Proof 02 uses the **other half of the same photograph**: the modern neighbor, the steps, the join. New idea, not a polish.

## What this is not

Not architecture-as-letter. Not TARİH. Not type in sky. Not editorial page cut. Not looking chamber. Not split screen (one photograph of a real adjacency). Not a luxury-interior catalog.
"""


CONCEPTS: tuple[dict[str, Any], ...] = (
    {
        "id": "C1_THE_SEAM",
        "name": "THE_SEAM",
        "visual_mechanism": (
            "One photograph of the real historic/modern join becomes the campaign spine. "
            "Headline and launch facts inhabit the new brick as a cornerstone; the stone sanctuary remains the civic proof."
        ),
        "why_temple_specific": "Only The Temple photographs a Gothic sanctuary fused to a new residential brick volume at one address.",
        "what_photo_does": "Day_008 supplies the join, the spire, the arrival steps, and human scale. No second picture is required.",
        "memorable_two_seconds": "Stone meeting brick. Two ages, one address.",
        "commercial_belongs": (
            "The modern volume is the product being launched. Offer, price, unit, and CTA are inscribed "
            "on its plinth from the beginning — not added as a later stack on a poster."
        ),
        "depth_from": "steps → street → lawn → two façades → spire → sky, plus a photographic plinth veil that continues ground shadow",
        "designed_without_copy": True,
        "why_not_template": "Not photo+headline, not a header slab, not a split of two pictures, not a listing card. One authored crop of a real adjacency.",
        "campaign_system_test": True,
        "scores": {
            "TEMPLE_SPECIFICITY": 10,
            "VISUAL_IDEA": 9,
            "PHOTO_INTEGRATION": 9,
            "DEPTH": 9,
            "COMMERCIAL_POTENTIAL": 9,
            "TYPOGRAPHIC_POTENTIAL": 8,
            "BRAND_CHARACTER": 9,
            "DISTINCTIVENESS": 9,
            "PUBLISHABILITY_POTENTIAL": 9,
        },
        "selected": True,
        "reject_reason": None,
    },
    {
        "id": "C2_THE_DEDICATION",
        "name": "THE_DEDICATION",
        "visual_mechanism": "Launch facts carved as a civic dedication across the arrival steps of Day_008.",
        "why_temple_specific": "Temples carry dedications; a residential launch written as an inscription is native to this conversion.",
        "what_photo_does": "Steps become the writing ground; the sanctuary rises behind.",
        "memorable_two_seconds": "Walking up inscribed steps into a church that is now a home.",
        "commercial_belongs": "The inscription IS the commercial message.",
        "depth_from": "foreground steps",
        "designed_without_copy": False,
        "why_not_template": "Could still collapse into photo + caption footer.",
        "campaign_system_test": False,
        "scores": {
            "TEMPLE_SPECIFICITY": 8,
            "VISUAL_IDEA": 7,
            "PHOTO_INTEGRATION": 7,
            "DEPTH": 8,
            "COMMERCIAL_POTENTIAL": 8,
            "TYPOGRAPHIC_POTENTIAL": 7,
            "BRAND_CHARACTER": 8,
            "DISTINCTIVENESS": 7,
            "PUBLISHABILITY_POTENTIAL": 7,
        },
        "selected": False,
        "reject_reason": "Campaign system fails: commercial likely becomes a footer stack on a property photo. Proof 01 learning.",
    },
    {
        "id": "C3_THE_INSERTION",
        "name": "THE_INSERTION",
        "visual_mechanism": "Vertical 4:5 slice of Day_001: the new brick volume sandwiched between two historic civic masses.",
        "why_temple_specific": "The residential product is literally inserted into Washington stone.",
        "what_photo_does": "Day_001 is the only frame that shows Scottish Rite + new fabric + Temple together.",
        "memorable_two_seconds": "A new building held by two monuments.",
        "commercial_belongs": "Facts live on the inserted modern volume.",
        "depth_from": "street, people, three masses",
        "designed_without_copy": True,
        "why_not_template": "One photograph of a real sandwich, not a split screen.",
        "campaign_system_test": True,
        "scores": {
            "TEMPLE_SPECIFICITY": 9,
            "VISUAL_IDEA": 8,
            "PHOTO_INTEGRATION": 8,
            "DEPTH": 7,
            "COMMERCIAL_POTENTIAL": 8,
            "TYPOGRAPHIC_POTENTIAL": 7,
            "BRAND_CHARACTER": 8,
            "DISTINCTIVENESS": 8,
            "PUBLISHABILITY_POTENTIAL": 7,
        },
        "selected": False,
        "reject_reason": "Day_001 crops the spire crown; 4:5 slice loses monumentality. Weaker depth than Day_008 steps.",
    },
    {
        "id": "C4_ARCHIVAL_THRESHOLD",
        "name": "ARCHIVAL_THRESHOLD",
        "visual_mechanism": "Archival Washington Chapel photograph as heritage mass meeting a color contemporary fragment.",
        "why_temple_specific": "The address has a photographed past.",
        "what_photo_does": "Street_View.jpg is heritage; a second photo would be 'now'.",
        "memorable_two_seconds": "Then and now.",
        "commercial_belongs": "Unclear — two pictures fight the offer.",
        "depth_from": "perspective street in the archive; not in the join",
        "designed_without_copy": False,
        "why_not_template": "Reads as split-screen / collage.",
        "campaign_system_test": False,
        "scores": {
            "TEMPLE_SPECIFICITY": 8,
            "VISUAL_IDEA": 7,
            "PHOTO_INTEGRATION": 5,
            "DEPTH": 6,
            "COMMERCIAL_POTENTIAL": 5,
            "TYPOGRAPHIC_POTENTIAL": 6,
            "BRAND_CHARACTER": 7,
            "DISTINCTIVENESS": 8,
            "PUBLISHABILITY_POTENTIAL": 5,
        },
        "selected": False,
        "reject_reason": "Banned split-screen risk and generic collage. Commercial has no native home.",
    },
    {
        "id": "C5_STONE_FRAGMENT",
        "name": "STONE_FRAGMENT",
        "visual_mechanism": "Extreme crop of arches as graphic material colliding with a designed color field.",
        "why_temple_specific": "Only if the stone is clearly this sanctuary.",
        "what_photo_does": "Fragment becomes page mass (ORNEK_00013 DNA).",
        "memorable_two_seconds": "A piece of temple as graphic.",
        "commercial_belongs": "Would live in the field — same trap as Proof 01 if the field is 'art' and facts are extra.",
        "depth_from": "weak — fragment flattens space",
        "designed_without_copy": True,
        "why_not_template": "Not a listing, but starts from a clever graphic device.",
        "campaign_system_test": False,
        "scores": {
            "TEMPLE_SPECIFICITY": 6,
            "VISUAL_IDEA": 8,
            "PHOTO_INTEGRATION": 6,
            "DEPTH": 4,
            "COMMERCIAL_POTENTIAL": 6,
            "TYPOGRAPHIC_POTENTIAL": 8,
            "BRAND_CHARACTER": 6,
            "DISTINCTIVENESS": 7,
            "PUBLISHABILITY_POTENTIAL": 5,
        },
        "selected": False,
        "reject_reason": "Starts from a graphic device, the Proof 01 failure mode. Depth collapses.",
    },
    {
        "id": "C6_TERRACOTTA_ROOM",
        "name": "TERRACOTTA_ROOM",
        "visual_mechanism": "Bedroom terracotta plaster as a material field for the launch, window as urban proof.",
        "why_temple_specific": "It is not. Any premium unit could hold this interior.",
        "what_photo_does": "Living_Room_006 / Bedroom_007 supply atmosphere, not Temple identity.",
        "memorable_two_seconds": "A nice bedroom.",
        "commercial_belongs": "Would sit on the plaster wall as catalog type.",
        "depth_from": "window dusk",
        "designed_without_copy": False,
        "why_not_template": "Generic luxury interior editorial — banned.",
        "campaign_system_test": False,
        "scores": {
            "TEMPLE_SPECIFICITY": 3,
            "VISUAL_IDEA": 4,
            "PHOTO_INTEGRATION": 6,
            "DEPTH": 6,
            "COMMERCIAL_POTENTIAL": 6,
            "TYPOGRAPHIC_POTENTIAL": 6,
            "BRAND_CHARACTER": 4,
            "DISTINCTIVENESS": 3,
            "PUBLISHABILITY_POTENTIAL": 4,
        },
        "selected": False,
        "reject_reason": "Not Temple-specific. Banned generic luxury editorial.",
    },
    {
        "id": "C7_ROOF_GARDEN",
        "name": "ROOF_GARDEN",
        "visual_mechanism": "Aerial Day_007: planted terraces on the historic sanctuary roof — living on sacred fabric.",
        "why_temple_specific": "Gardens sit on this church, not beside a generic tower.",
        "what_photo_does": "Day_007 shows roof gardens, spire, modern neighbor from altitude.",
        "memorable_two_seconds": "People will live on a temple roof.",
        "commercial_belongs": "Aerial canvases push facts to a diagram margin.",
        "depth_from": "city ring, weak human scale",
        "designed_without_copy": True,
        "why_not_template": "Not a listing if cropped into the gardens, but reads as an overview.",
        "campaign_system_test": False,
        "scores": {
            "TEMPLE_SPECIFICITY": 8,
            "VISUAL_IDEA": 8,
            "PHOTO_INTEGRATION": 7,
            "DEPTH": 6,
            "COMMERCIAL_POTENTIAL": 5,
            "TYPOGRAPHIC_POTENTIAL": 6,
            "BRAND_CHARACTER": 7,
            "DISTINCTIVENESS": 8,
            "PUBLISHABILITY_POTENTIAL": 6,
        },
        "selected": False,
        "reject_reason": "Campaign system fails: commercial facts have no natural home on an aerial. Weak intimacy.",
    },
)


def selected_concept() -> dict[str, Any]:
    return next(item for item in CONCEPTS if item.get("selected"))


def concept_evaluation_json() -> dict[str, Any]:
    chosen = selected_concept()
    return {
        "schema": "Phase112ConceptEvaluationV1",
        "policy": (
            "Do not select merely the cleverest concept. Select the strongest combined score. "
            "PUBLISHABILITY_POTENTIAL must be >= 9 before render. Campaign system test must pass."
        ),
        "banned_devices": list(BANNED_DEVICES),
        "selection_rule": "TEMPLE SPECIFICITY + visual idea + photo + depth + commercial + type + brand + distinctiveness + publishability",
        "concepts": [
            {
                "id": item["id"],
                "name": item["name"],
                "answers": {
                    "1_visual_mechanism": item["visual_mechanism"],
                    "2_why_temple_specific": item["why_temple_specific"],
                    "3_what_the_real_photo_does": item["what_photo_does"],
                    "4_memorable_in_two_seconds": item["memorable_two_seconds"],
                    "5_how_commercial_belongs": item["commercial_belongs"],
                    "6_where_depth_comes_from": item["depth_from"],
                    "7_designed_without_copy": item["designed_without_copy"],
                    "8_why_not_a_template": item["why_not_template"],
                },
                "campaign_system_test": item["campaign_system_test"],
                "scores": item["scores"],
                "selected": item["selected"],
                "reject_reason": item["reject_reason"],
            }
            for item in CONCEPTS
        ],
        "selected_id": chosen["id"],
        "publishability_potential": chosen["scores"]["PUBLISHABILITY_POTENTIAL"],
        "campaign_system_test": chosen["campaign_system_test"],
        "not_shown_as_ABC": True,
        "r1_created": False,
    }


def selected_design_dna_text() -> str:
    return (
        "Principles only: type in the building's own shadow (00008); photograph as structural page mass (00013); "
        "photographic veil only when it continues the scene's own ground light (00015). "
        "No navy colonnade, no parchment page-cut, no looking-chamber lid."
    )


def creative_strategy() -> dict[str, Any]:
    profile = project_photo_profile(asset_id=DAY008_ASSET_ID) or {}
    matching = match_design_dna(
        photo_profile=profile,
        campaign_objective="civic prestige residential launch for The Temple in Washington D.C.",
        target_emotion="two ages sharing one address — inhabited monument, not generic luxury calm",
        visual_opportunity="historic stone and new brick joined as one photographed campaign spine",
    )
    strategy = {
        "schema": SCHEMA,
        "status": "SET",
        "layout_forbidden_until_strategy_exists": False,
        "pipeline_id": PIPELINE_ID,
        "user_request": USER_REQUEST,
        "project_story": (
            "The Temple is a historic Washington sanctuary given a second life as a home. "
            "The new residential brick is fused to the old stone. That join is the project."
        ),
        "campaign_objective": "Launch The Temple as a premium Washington D.C. residence with a %35 lansman advantage.",
        "target_emotion": "Quiet awe at inhabiting a monument — two centuries in one address.",
        "primary_message": "You live at the join of historic sanctuary and new residential fabric.",
        "commercial_message": (
            f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']} · "
            f"{REQUIRED_FACTS['list_price']} · {REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']} · "
            f"{REQUIRED_FACTS['cta']}"
        ),
        "available_real_assets": [
            {"filename": name, "asset_id": aid, "note": note} for name, aid, note in OPPORTUNITY_ASSETS
        ],
        "strongest_project_characteristic": (
            "The real historic sanctuary and the new residential brick share one photographed seam. "
            "No other Temple idea is this specific, and no other asset holds join + spire + arrival steps together."
        ),
        "selected_design_dna": selected_design_dna_text(),
        "creative_tension": "Dead stone holding living brick — heritage is the proof, the new volume is the offer.",
        "visual_idea": CONCEPT_SENTENCE,
        "why_this_idea_fits_this_project": (
            "The Temple's character is conversion, not a clever letter. The campaign can only feel right "
            "if the real join of sanctuary and residence is the picture, and the launch belongs to the new building."
        ),
        "selected_real_assets": [
            {
                "filename": DAY008_FILENAME,
                "asset_id": DAY008_ASSET_ID,
                "role": "full-frame seam — historic stone, modern brick, arrival steps, spire, human scale",
            }
        ],
        "relevant_design_dna": list(DNA_USED),
        "memorable_gesture": "The real join of tan sanctuary stone and grey residential brick, with the launch on the new plinth.",
        "two_second_impression": TWO_SECOND,
        "headline": HEADLINE,
        "headline_origin": "NEW — project-character headline, not a description of a graphic trick; no financial claims",
        "closure": APPROVED_BOTTOM_COPY,
        "brand": "Temple logo only",
        "typography_reason": (
            "Contemporary grotesque, not inherited luxury serif. The new brick is a modern insertion; "
            "type is the voice of that building. The historic stone already supplies ornament. "
            "Scale and weight contrast do the craft: İKİ ÇAĞ heavy, BİR ADRES lighter, %35 as a cornerstone numeral."
        ),
        "reference_match": matching,
        "not_reused": list(BANNED_DEVICES),
        "proof_01": "PRESERVED AS REJECTED LEARNING",
        "learning": PHASE_11_1_LEARNING,
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
    used_names = {row["filename"] for row in DNA_USED}
    return {
        "schema": "Phase112DesignDNASelectionV1",
        "policy": "Retrieve transferable principles. Do not reproduce a reference layout. Do not collage styles.",
        "used": records,
        "unused_grade_a": [
            {
                "filename": item["filename"],
                "reference_id": item["reference_id"],
                "reason": "not the primary mechanism for a photographed historic/modern join",
            }
            for item in grade_a_design_dna()
            if item["filename"] not in used_names
        ],
    }
