"""Reference matching by opportunity, not by similar colors or similar buildings."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_design_dna_v2 import grade_a_design_dna

MATCH_AXES = (
    "visual_opportunity",
    "photo_geometry",
    "campaign_objective",
    "emotional_character",
    "commercial_hierarchy",
    "creative_mechanism_compatibility",
)

FORBIDDEN_PRIMARY_MATCH = (
    "similar colors",
    "similar building",
    "same orientation",
)


def match_design_dna(
    *,
    photo_profile: dict[str, Any],
    campaign_objective: str,
    target_emotion: str,
    visual_opportunity: str,
) -> dict[str, Any]:
    ranked: list[dict[str, Any]] = []
    emotion = (target_emotion or "").casefold()
    objective = (campaign_objective or "").casefold()
    opportunity = (visual_opportunity or "").casefold()
    geometry = " ".join(
        str(photo_profile.get(key) or "")
        for key in ("subject_geometry", "architectural_anchor", "campaign_suitability", "boundary_interaction_opportunities")
    ).casefold()
    for dna in grade_a_design_dna():
        score = 0
        reasons: list[str] = []
        role = str(dna.get("photography_role") or "").casefold()
        if "spire" in geometry or "chamber" in geometry or "looking-out" in geometry:
            if "graphic material" in role or "architectural" in role or "hero object" in role:
                score += 3
                reasons.append("photo geometry can carry an architectural mechanism")
        if any(token in emotion for token in str(dna.get("emotional_character") or "").casefold().split(";")):
            score += 2
            reasons.append("emotional character overlap")
        if opportunity and any(token in str(dna.get("visual_idea") or "").casefold() for token in opportunity.split() if len(token) > 4):
            score += 3
            reasons.append("visual opportunity aligns with DNA mechanism")
        if objective and any(token in " ".join(dna.get("suitable_campaign_types") or []).casefold() for token in objective.split() if len(token) > 4):
            score += 2
            reasons.append("campaign type fit")
        ranked.append(
            {
                "filename": dna["filename"],
                "reference_id": dna["reference_id"],
                "score": score,
                "reasons": reasons,
                "visual_idea": dna["visual_idea"],
                "strength_score": dna["strength_score"],
            }
        )
    ranked.sort(key=lambda item: (item["score"], item["strength_score"]), reverse=True)
    return {
        "schema": "ReferenceMatchV1",
        "primary_match_forbidden": list(FORBIDDEN_PRIMARY_MATCH),
        "axes": list(MATCH_AXES),
        "ranked": ranked,
        "selected": ranked[0] if ranked else None,
        "note": (
            "A reference using subject-boundary interruption may be relevant to a Temple "
            "photograph with a strong spire even if the reference contains no building."
        ),
        "status": "READY",
    }


def reference_matching_contract() -> dict[str, Any]:
    return {
        "schema": "ReferenceMatchingV1",
        "axes": list(MATCH_AXES),
        "do_not_match_primarily_on": list(FORBIDDEN_PRIMARY_MATCH),
        "status": "READY",
    }
