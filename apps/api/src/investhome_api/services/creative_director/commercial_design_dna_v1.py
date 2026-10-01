"""CommercialDesignDNAV1 — how Grade-A references DESIGN commercial information.

Ignore general visual beauty. Transferable commercial craft only.
Never copy another project's pixels, logo, or facts.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_design_dna_v2 import grade_a_design_dna

SCHEMA = "CommercialDesignDNAV1"

# Analyzed from the same six Grade-A DESIGN_REFERENCES as CreativeDesignDNAV2.
COMMERCIAL_DNA: tuple[dict[str, Any], ...] = (
    {
        "filename": "ORNEK_00013.jpg",
        "read_first": "Three period-stopped civic words in the navy void.",
        "read_second": "A small supporting paragraph, then a gold closing word.",
        "commercial_proposition_enters": "As language, not as a price. Location prestige is the offer.",
        "typography_vs_imagery": "Type never sits on the photograph. Architecture is one mass; the navy field is the message mass.",
        "facts_as_graphic_objects": "YES — the headline stack is a graphic object. Numeric facts are absent.",
        "cta_action": "Brand mark only. No button.",
        "information_density": "Very low. Persuasion is verbal scarcity of words.",
        "thumbnail_hierarchy_survives": "YES — stone silhouette + three-word stack still reads.",
        "transferable_commercial_principle": (
            "A commercial proposition may be a verbal chant occupying a designed field that is an actor, "
            "not leftover space beside a photo."
        ),
        "do_not_copy": "navy field, colonnade, UniLoft copy, absence-of-price as a Temple excuse when a lansman price exists",
        "warning": "Temple's current brief REQUIRES price and offer. Do not hide them because this reference has none.",
    },
    {
        "filename": "ORNEK_00001.jpg",
        "read_first": "The terrace ritual against the landmark.",
        "read_second": "Three-line lifestyle headline in bleached sky, then a quieter offer line.",
        "commercial_proposition_enters": "After the scene has sold location. Offer is a spoken secondary line, not a badge.",
        "typography_vs_imagery": "Type occupies real photographic quiet (pale sky), not a manufactured header.",
        "facts_as_graphic_objects": "PARTIAL — headline weight contrast is graphic; the offer is still a caption-like line.",
        "cta_action": "Brand at top. No button.",
        "information_density": "Low. One offer line.",
        "thumbnail_hierarchy_survives": "PARTIAL — scene survives; offer line may vanish at 15%.",
        "transferable_commercial_principle": (
            "An offer may enter after a visual proof of place, as a line in the same type system, never as a medallion."
        ),
        "do_not_copy": "Uniloft terrace, Capitol-as-someone-else's-asset, sky-as-default-type-slot",
        "warning": "Sky type is a Temple-banned default. Transfer 'offer as spoken line', not 'type in leftover sky'.",
    },
    {
        "filename": "ORNEK_00006.jpg",
        "read_first": "Centered scarcity headline on a taupe proposition field.",
        "read_second": "The lived interior as proof.",
        "commercial_proposition_enters": "Immediately, as the entire upper field. The photo confirms it.",
        "typography_vs_imagery": "Type does not enter the room. Field and photograph are two sequential acts.",
        "facts_as_graphic_objects": "NO numeric facts. The headline IS the proposition object.",
        "cta_action": "Brand on the photograph footer.",
        "information_density": "Medium in the field, none in the room.",
        "thumbnail_hierarchy_survives": "YES — field vs interior split still reads, at the risk of 'header + photo'.",
        "transferable_commercial_principle": (
            "A message field is legitimate only when the photograph still has its own mechanism. "
            "Do not use this as a dark-header template."
        ),
        "do_not_copy": "horizontal split, centered stack, ornamental swirl, Uniloft interior",
        "warning": "Nearest banned template. Transfer sequence (claim then proof), never the split.",
    },
    {
        "filename": "ORNEK_00015.jpg",
        "read_first": "Weight-contrasted headline inside a photographic ceiling veil.",
        "read_second": "Foreground stools and the fruit still-life as lived proof.",
        "commercial_proposition_enters": "Inside the scene's own darkness. No price. Product world is implied.",
        "typography_vs_imagery": "Type rides a gradient harvested from the photograph, not a UI overlay.",
        "facts_as_graphic_objects": "NO. Hierarchy is typographic weight inside one line.",
        "cta_action": "Brand on the floor / in-scene logotype on architecture.",
        "information_density": "Low.",
        "thumbnail_hierarchy_survives": "YES — stools + still-life + dark veil remain an event.",
        "transferable_commercial_principle": (
            "Commercial type may occupy darkness that already belongs to the photograph. "
            "Headline weight contrast can replace a second font."
        ),
        "do_not_copy": "kitchen still-life, Uniloft interior, veil-as-header-slab",
        "warning": "A veil that is only a type plate is the Proof 02 wash. Harvest light; do not invent a column.",
    },
    {
        "filename": "ORNEK_00011.jpg",
        "read_first": "The isolated building as a hero object.",
        "read_second": "Proximity headline, then walking-time pointers as evidence.",
        "commercial_proposition_enters": "Location IS the product. Proof lines are the commercial facts as graphic objects.",
        "typography_vs_imagery": "Type in the drained paper field; pointers physically leave the roofline.",
        "facts_as_graphic_objects": "YES — walking times are drawn, not listed.",
        "cta_action": "Brand only.",
        "information_density": "Controlled only if labels stay sparse.",
        "thumbnail_hierarchy_survives": "YES — isolated building remains. Pointers may collapse into noise if multiplied.",
        "transferable_commercial_principle": (
            "A fact can be a graphic act attached to architecture (a line, a cut, a numeral as mass), "
            "not a caption parked beside the building."
        ),
        "do_not_copy": "Uniloft brick, Capitol pointers, pin-listing UI",
        "warning": "Infographic overgrowth becomes a listing. Sparse proof only.",
    },
    {
        "filename": "ORNEK_00008.jpg",
        "read_first": "Gold serif headline in the building's own unlit air.",
        "read_second": "White sans body, then brand at the ground line.",
        "commercial_proposition_enters": "As delivery timing — currently encoded as banned circular badges.",
        "typography_vs_imagery": "Type lives in photographic dark. The photograph remains the page.",
        "facts_as_graphic_objects": "The circles are graphic but FORBIDDEN. Transfer type-in-shadow, never badges.",
        "cta_action": "Brand footer. No button.",
        "information_density": "Headline + body. Circles are excess.",
        "thumbnail_hierarchy_survives": "YES — façade + grasses. Circles become junk at 15%.",
        "transferable_commercial_principle": (
            "Delivery and offer facts must be art-directed as type inside the architecture, "
            "never as stickers on the photograph."
        ),
        "do_not_copy": "circle badges, Uniloft façade, gold serif as a luxury default",
        "warning": "This reference shows BOTH the craft (type in shadow) and the defect (promo circles).",
    },
)

OVERCORRECTION_BANS = (
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


def commercial_design_dna_library() -> dict[str, Any]:
    visual = {item["filename"]: item for item in grade_a_design_dna()}
    records = []
    for item in COMMERCIAL_DNA:
        dna = visual[item["filename"]]
        records.append(
            {
                "schema": SCHEMA,
                **item,
                "reference_id": dna["reference_id"],
                "media_asset_id": dna["media_asset_id"],
            }
        )
    return {
        "schema": "CommercialDesignDNALibraryV1",
        "grade_a_count": len(records),
        "records": records,
        "overcorrection_bans": list(OVERCORRECTION_BANS),
        "note": (
            "Most Grade-A references have weak or absent numeric offers. "
            "Temple's lansman REQUIRES %35, price, unit, and CTA. "
            "Transfer how information is designed, not the absence of numbers."
        ),
        "status": "READY" if len(records) == 6 else "FAIL",
    }
