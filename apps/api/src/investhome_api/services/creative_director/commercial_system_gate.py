"""Commercial system gate — no-copy is necessary, not sufficient.

Two independent gates:
A. VISUAL IDEA GATE — remove all copy; does the mechanism remain designed?
B. COMMERCIAL SYSTEM GATE — restore required commercial information; does the
   composition become stronger rather than merely busier?
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.idea_first_pipeline import no_copy_test
from investhome_api.services.creative_director.integrated_campaign_concept import REQUIRED_COMMERCIAL

SCHEMA = "CommercialSystemGateV1"

RELATIONSHIP_AXES = (
    "architecture",
    "photography",
    "graphic_structure",
    "scale",
    "negative_space",
    "reading_direction",
    "depth",
)

OVERCORRECTION = (
    "giant %35 badge",
    "giant price box",
    "sale sticker",
    "promo burst",
    "banner",
    "property listing layout",
    "card grid",
    "UI panel",
    "brochure facts",
    "real-estate portal aesthetic",
)


def visual_idea_gate(*, visual_mechanism: str, photography_participates: bool, feels_designed_without_copy: bool) -> dict[str, Any]:
    base = no_copy_test(
        visual_mechanism=visual_mechanism,
        photography_participates=photography_participates,
        feels_designed_without_copy=feels_designed_without_copy,
    )
    return {
        "schema": "VisualIdeaGateV1",
        "also_known_as": "NO_COPY_TEST",
        "pass": bool(base.get("pass")),
        "detail": base,
        "note": "Necessary. Insufficient. Proof 01 and Proof 02 passed no-copy and still failed as advertising.",
    }


def commercial_system_gate(
    *,
    composition_stronger_with_copy: bool,
    elements_have_intentional_relationships: bool,
    occupies_leftover_space_only: bool,
    overcorrection_device: str | None = None,
) -> dict[str, Any]:
    cheap = str(overcorrection_device or "").strip()
    cheap_hit = cheap.casefold() in {item.casefold() for item in OVERCORRECTION} if cheap else False
    passed = (
        composition_stronger_with_copy
        and elements_have_intentional_relationships
        and not occupies_leftover_space_only
        and not cheap_hit
    )
    return {
        "schema": SCHEMA,
        "required_information": list(REQUIRED_COMMERCIAL),
        "optional": "closure if composition supports it",
        "relationship_axes": list(RELATIONSHIP_AXES),
        "composition_stronger_with_copy": composition_stronger_with_copy,
        "elements_have_intentional_relationships": elements_have_intentional_relationships,
        "occupies_leftover_space_only": occupies_leftover_space_only,
        "overcorrection_device": cheap or None,
        "pass": passed,
        "action_if_fail": "REJECT CONCEPT BEFORE RENDER",
        "note": "Elements must have intentional visual relationships. They cannot simply occupy an available empty area.",
    }


def thumbnail_test(
    *,
    scale: float = 0.15,
    one_clear_visual_event: bool,
    one_clear_message: bool,
    one_clear_commercial_hook: bool,
) -> dict[str, Any]:
    equal_noise = not (one_clear_visual_event and one_clear_message and one_clear_commercial_hook)
    return {
        "schema": "ThumbnailTestV1",
        "scale": scale,
        "one_clear_visual_event": one_clear_visual_event,
        "one_clear_message": one_clear_message,
        "one_clear_commercial_hook": one_clear_commercial_hook,
        "pass": not equal_noise,
        "fail_if": "everything becomes equal noise",
        "status": "READY",
    }


def advertisement_vs_poster_test(answer: str | None) -> dict[str, Any]:
    text = str(answer or "").strip().casefold()
    designed = text in {"designed advertisement", "advertisement designed to persuade"}
    poster = text in {"poster + sales information", "beautiful poster with sales information added"}
    return {
        "schema": "AdvertisementVsPosterTestV1",
        "question": "Does this look like an advertisement designed to persuade, or a beautiful poster with sales information added?",
        "allowed_answer": "DESIGNED ADVERTISEMENT",
        "fail_answer": "POSTER + SALES INFORMATION",
        "answer": answer,
        "pass": designed and not poster,
        "proof_01": "POSTER + SALES INFORMATION",
        "proof_02": "POSTER + SALES INFORMATION",
        "status": "READY",
    }


def commercial_system_gate_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "gates": ("VISUAL_IDEA_GATE", "COMMERCIAL_SYSTEM_GATE"),
        "required_information": list(REQUIRED_COMMERCIAL),
        "relationship_axes": list(RELATIONSHIP_AXES),
        "overcorrection_bans": list(OVERCORRECTION),
        "thumbnail_test": "READY",
        "advertisement_vs_poster_test": "READY",
        "status": "READY",
    }
