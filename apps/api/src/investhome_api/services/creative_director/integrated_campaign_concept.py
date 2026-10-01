"""Integrated campaign concept — visual + photo + commercial + type as one system."""

from __future__ import annotations

from typing import Any

SCHEMA = "IntegratedCampaignConceptV1"

CONCEPT_QUESTIONS = (
    "WHAT IS THE VISUAL IDEA?",
    "WHAT DOES THE PROJECT PHOTO DO?",
    "WHAT IS THE PRIMARY SALES MESSAGE?",
    "HOW DOES THE SALES MESSAGE PARTICIPATE IN THE VISUAL IDEA?",
    "WHAT DOES THE VIEWER READ FIRST?",
    "WHAT DOES THE VIEWER READ SECOND?",
    "WHERE DOES THE OFFER LIVE AND WHY?",
    "HOW ARE PRICE AND UNIT DESIGNED INTO THE COMPOSITION?",
    "HOW DOES THE CTA complete the reading path?",
    "WHAT remains memorable after two seconds?",
)

EVALUATION_AXES = (
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
)

RENDER_FLOORS = {
    "TEMPLE_SPECIFICITY": 8,
    "VISUAL_MECHANISM": 8,
    "PHOTO_OPPORTUNITY": 8,
    "COMMERCIAL_MECHANISM": 9,
    "TYPOGRAPHIC_OPPORTUNITY": 8,
    "DEPTH_POTENTIAL": 8,
    "READING_PATH": 9,
    "PUBLISHABILITY_POTENTIAL": 9,
}

SKELETON_ELEMENTS = (
    "PRIMARY_HERO",
    "PRIMARY_MESSAGE",
    "PROJECT_BRAND",
    "OFFER",
    "PRICE",
    "UNIT",
    "CTA",
    "SUPPORTING_MESSAGE",
)

SKELETON_FIELDS = (
    "ROLE",
    "VISUAL_WEIGHT",
    "RELATIONSHIP_TO_PHOTO",
    "RELATIONSHIP_TO_NEXT_ELEMENT",
    "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH",
)

CAMPAIGN_HIERARCHIES = (
    "PROJECT_LED",
    "OFFER_LED",
    "PRICE_LED",
    "ARCHITECTURE_LED",
    "LIFESTYLE_LED",
    "LOCATION_LED",
    "HERITAGE_LED",
)

REQUIRED_COMMERCIAL = (
    "THE TEMPLE",
    "WASHINGTON D.C.",
    "HEADLINE",
    "%35 LANSMAN AVANTAJI",
    "675.000 USD",
    "2+1 DAİRE",
    "PROJEYİ KEŞFET",
)

PLACED_IN_NEGATIVE_SPACE = "placed in available negative space"


def empty_campaign_skeleton() -> dict[str, Any]:
    return {
        "schema": "CampaignSkeletonV1",
        "note": "Relationships, not coordinates. Editability follows art direction.",
        "elements": {
            name: {field: None for field in SKELETON_FIELDS}
            for name in SKELETON_ELEMENTS
        },
        "status": "UNSET",
    }


def validate_campaign_skeleton(skeleton: dict[str, Any]) -> dict[str, Any]:
    elements = dict((skeleton or {}).get("elements") or {})
    missing: list[str] = []
    immature: list[str] = []
    for name in SKELETON_ELEMENTS:
        item = dict(elements.get(name) or {})
        for field in SKELETON_FIELDS:
            value = str(item.get(field) or "").strip()
            if not value:
                missing.append(f"{name}.{field}")
            elif value.casefold() == PLACED_IN_NEGATIVE_SPACE:
                immature.append(name)
    ready = not missing and not immature
    return {
        "schema": "CampaignSkeletonValidationV1",
        "pass": ready,
        "missing_fields": missing,
        "immature_elements": immature,
        "reason": None if ready else "Every element needs a role, weight, photo relationship, next-element relationship, and a reading-path reason that is not leftover space.",
    }


def empty_integrated_concept() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNSET",
        "answers": {question: None for question in CONCEPT_QUESTIONS},
        "evaluation": {axis: None for axis in EVALUATION_AXES},
        "hierarchy": None,
        "skeleton": empty_campaign_skeleton(),
        "render_allowed": False,
    }


def score_concept_evaluation(scores: dict[str, int]) -> dict[str, Any]:
    normalized = {axis: int(scores.get(axis) or 0) for axis in EVALUATION_AXES}
    floor_fail = [axis for axis, floor in RENDER_FLOORS.items() if normalized.get(axis, 0) < floor]
    return {
        "schema": "IntegratedConceptEvaluationV1",
        "scores": normalized,
        "floors": dict(RENDER_FLOORS),
        "floor_failures": floor_fail,
        "pass": not floor_fail,
        "action_if_fail": "REJECT CONCEPT BEFORE RENDER",
    }


def concept_answers_complete(answers: dict[str, Any] | None) -> bool:
    payload = answers or {}
    return all(str(payload.get(question) or "").strip() for question in CONCEPT_QUESTIONS)


def validate_integrated_concept(concept: dict[str, Any]) -> dict[str, Any]:
    answers_ok = concept_answers_complete((concept or {}).get("answers"))
    evaluation = score_concept_evaluation(dict((concept or {}).get("evaluation") or {}))
    skeleton = validate_campaign_skeleton(dict((concept or {}).get("skeleton") or {}))
    hierarchy = str((concept or {}).get("hierarchy") or "")
    hierarchy_ok = hierarchy in CAMPAIGN_HIERARCHIES
    passed = answers_ok and evaluation["pass"] and skeleton["pass"] and hierarchy_ok
    return {
        "schema": "IntegratedCampaignConceptValidationV1",
        "pass": passed,
        "answers_complete": answers_ok,
        "evaluation": evaluation,
        "skeleton": skeleton,
        "hierarchy_ok": hierarchy_ok,
        "render_allowed": passed,
        "action_if_fail": "REJECT CONCEPT BEFORE RENDER",
    }


def integrated_campaign_concept_schema() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "questions": list(CONCEPT_QUESTIONS),
        "evaluation_axes": list(EVALUATION_AXES),
        "render_floors": dict(RENDER_FLOORS),
        "skeleton_elements": list(SKELETON_ELEMENTS),
        "skeleton_fields": list(SKELETON_FIELDS),
        "campaign_hierarchies": list(CAMPAIGN_HIERARCHIES),
        "required_commercial": list(REQUIRED_COMMERCIAL),
        "immature_if": PLACED_IN_NEGATIVE_SPACE,
        "rule": (
            "A concept is not valid merely because it has a visual mechanism, a memorable gesture, "
            "and a no-copy proof. Visual idea + project photography + commercial message + typography "
            "must be conceived as one system."
        ),
        "status": "READY",
    }


def temple_current_campaign_hierarchy_evaluation() -> dict[str, Any]:
    """Text-only. Do not render. Determines which hierarchy has the greatest premium advertising potential."""
    options = (
        {
            "hierarchy": "ARCHITECTURE_LED",
            "fit": (
                "The Temple's distinctive product is the building: sanctuary stone fused to new residence. "
                "Architecture can be the hero; %35 and price must be designed as architectural actors, not a caption."
            ),
            "premium_advertising_potential": 9,
            "risk": "Repeating Proof 01/02: architecture as poster, facts as a later column.",
        },
        {
            "hierarchy": "HERITAGE_LED",
            "fit": (
                "Conversion is the emotional thesis — history you can inhabit. "
                "Heritage can author the headline; the offer is the contemporary invitation into that history."
            ),
            "premium_advertising_potential": 8,
            "risk": "Heritage copy without a commercial mechanism becomes a clever poster again.",
        },
        {
            "hierarchy": "OFFER_LED",
            "fit": (
                "The live request is a lansman with %35. Offer-led is commercially honest. "
                "It only stays premium if %35 is a typographic/architectural event, not a sticker."
            ),
            "premium_advertising_potential": 7,
            "risk": "Overcorrection into badge, burst, or portal sale aesthetic.",
        },
    )
    selected = max(options, key=lambda item: item["premium_advertising_potential"])
    return {
        "schema": "TempleCampaignHierarchyEvaluationV1",
        "evaluated": list(options),
        "selected": selected["hierarchy"],
        "why": (
            "Architecture-led has the greatest premium potential because the project is unrepeatable as a building. "
            "The offer must participate inside that architecture. Heritage-led is close. Offer-led is available "
            "but more exposed to cheap-promo overcorrection."
        ),
        "rendered": False,
        "status": "READY",
    }
