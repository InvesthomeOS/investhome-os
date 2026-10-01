"""Phase 11.6 concept set — designed for hybrid capabilities, not the old overlay compiler."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.commercial_design_dna_v1 import SCHEMA as COMMERCIAL_DNA_SCHEMA
from investhome_api.services.creative_director.creative_design_dna_v2 import SCHEMA as CREATIVE_DNA_SCHEMA
from investhome_api.services.creative_director.hybrid_premium_engine_v1 import ENGINE_ID
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.stage3_failure_learning_v2 import SCHEMA as LEARNING_SCHEMA

DAY003_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_003.jpg"
DAY003_ASSET_ID = "7346e259-f999-4fbb-a8d5-63708d4e0c81"

CONCEPT_NAME = "THE_LEDGER"
HEADLINE = "TAŞ TEMİNAT"
CONCEPT_SENTENCE = (
    "The Temple is isolated as a real stone object and set onto a generated archival paper field "
    "as collateral; the lansman numeral is printed into the paper and the building occludes it."
)
TWO_SECOND = "A real Temple standing on a printed %35 — stone as collateral, not a captioned poster."
USER_REQUEST = (
    "Hybrid premium engine quality proof. Do not use the old overlay compiler. "
    "Do not create Proof 04 on the old method."
)

BANNED_MECHANISMS = (
    "Proof 01 architecture-as-letter",
    "Proof 02 historic/new join lockup",
    "Proof 03 threshold/portal campaign",
    "Master 01 type-in-sky on Day_003 as full-bleed plate",
    "Master 02",
    "Master 03",
    "independent left fact stack",
    "independent right fact stack",
    "footer fact row",
    "floating information box",
    "price card",
    "%35 badge",
    "website CTA button",
    "poster + sales information",
)


def _concept(
    *,
    key: str,
    name: str,
    sentence: str,
    photo: str,
    why_hybrid: str,
    commercial_mechanism: str,
    selected: bool,
    reject_reason: str | None,
    scores: dict[str, int],
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "sentence": sentence,
        "project_photo": photo,
        "why_this_needs_hybrid": why_hybrid,
        "commercial_mechanism": commercial_mechanism,
        "selected": selected,
        "reject_reason": reject_reason,
        "scores": scores,
    }


def hybrid_concepts() -> list[dict[str, Any]]:
    """Five text-only concepts. Only THE_LEDGER is rendered."""
    return [
        _concept(
            key="C1",
            name="THE_LEDGER",
            sentence=CONCEPT_SENTENCE,
            photo=f"{DAY003_FILENAME} isolated as an object (not Master 01 full-bleed sky type)",
            why_hybrid=(
                "Requires a generated paper field as a page actor, a non-rectangular real Temple object, "
                "and typography that lives in the paper and is occluded by the building."
            ),
            commercial_mechanism=(
                "%35 is a printed plate mark in the paper. The Temple stands in front of it. "
                "Price is the vertical spine of the instrument. CTA is the document instruction."
            ),
            selected=True,
            reject_reason=None,
            scores={
                "TEMPLE_SPECIFICITY": 9,
                "VISUAL_MECHANISM": 9,
                "PHOTO_OPPORTUNITY": 8,
                "COMMERCIAL_MECHANISM": 9,
                "TYPOGRAPHIC_OPPORTUNITY": 9,
                "DEPTH_POTENTIAL": 9,
                "READING_PATH": 9,
                "HYBRID_FIT": 10,
            },
        ),
        _concept(
            key="C2",
            name="THE_NEEDLE",
            sentence="Day_002 spire isolated as a needle piercing generated vellum; the offer is the sheet the needle punctures.",
            photo="Day_002",
            why_hybrid="Object piercing a generated sheet — impossible on a flattened plate.",
            commercial_mechanism="The puncture is the offer.",
            selected=False,
            reject_reason="Day_002 is Master 03's photograph. Do not reproduce Master 03.",
            scores={
                "TEMPLE_SPECIFICITY": 8,
                "VISUAL_MECHANISM": 8,
                "PHOTO_OPPORTUNITY": 8,
                "COMMERCIAL_MECHANISM": 8,
                "TYPOGRAPHIC_OPPORTUNITY": 8,
                "DEPTH_POTENTIAL": 8,
                "READING_PATH": 8,
                "HYBRID_FIT": 9,
            },
        ),
        _concept(
            key="C3",
            name="THE_CHAMBER_CUT",
            sentence="Living_Room_001 clipped as a real interior object into a generated dusk field; windows remain real Temple glass.",
            photo="Living_Room_001",
            why_hybrid="Interior as an object in a generated atmosphere, not a room photograph with type on the wall.",
            commercial_mechanism="Price as a caption to the chamber cut — weak, listing-adjacent.",
            selected=False,
            reject_reason="Too close to a photo-card / interior listing. Commercial mechanism is not the cut.",
            scores={
                "TEMPLE_SPECIFICITY": 7,
                "VISUAL_MECHANISM": 7,
                "PHOTO_OPPORTUNITY": 8,
                "COMMERCIAL_MECHANISM": 6,
                "TYPOGRAPHIC_OPPORTUNITY": 7,
                "DEPTH_POTENTIAL": 8,
                "READING_PATH": 6,
                "HYBRID_FIT": 8,
            },
        ),
        _concept(
            key="C4",
            name="THE_ROOF_SPECIMEN",
            sentence="Day_007 aerial mass isolated on generated map-paper as a specimen.",
            photo="Day_007",
            why_hybrid="Cartographic object on a generated sheet (ORNEK_00011 family).",
            commercial_mechanism="Specimen label as offer — reads as a diagram, not a residential sale.",
            selected=False,
            reject_reason="Cartographic, weak residential intimacy, weak persuasion for 2+1 / price.",
            scores={
                "TEMPLE_SPECIFICITY": 7,
                "VISUAL_MECHANISM": 7,
                "PHOTO_OPPORTUNITY": 7,
                "COMMERCIAL_MECHANISM": 6,
                "TYPOGRAPHIC_OPPORTUNITY": 7,
                "DEPTH_POTENTIAL": 6,
                "READING_PATH": 6,
                "HYBRID_FIT": 8,
            },
        ),
        _concept(
            key="C5",
            name="THE_DUSK_RELIQUARY",
            sentence="Sunset_001 silhouette isolated onto generated atmosphere; type as luminous field language.",
            photo="Sunset_001",
            why_hybrid="Silhouette object + generated dusk field instead of type-on-photographic-sky.",
            commercial_mechanism="Offer as glow in the field — high poster risk.",
            selected=False,
            reject_reason="Too close to cinematic poster and leftover-sky type history.",
            scores={
                "TEMPLE_SPECIFICITY": 8,
                "VISUAL_MECHANISM": 7,
                "PHOTO_OPPORTUNITY": 8,
                "COMMERCIAL_MECHANISM": 6,
                "TYPOGRAPHIC_OPPORTUNITY": 7,
                "DEPTH_POTENTIAL": 8,
                "READING_PATH": 6,
                "HYBRID_FIT": 8,
            },
        ),
    ]


def selected_concept() -> dict[str, Any]:
    chosen = next(item for item in hybrid_concepts() if item["selected"])
    return chosen


def concept_evaluation_json() -> dict[str, Any]:
    return {
        "schema": "Phase116ConceptEvaluation",
        "engine": ENGINE_ID,
        "dna": [CREATIVE_DNA_SCHEMA, COMMERCIAL_DNA_SCHEMA, LEARNING_SCHEMA],
        "banned_mechanisms": list(BANNED_MECHANISMS),
        "rendered_alternatives": False,
        "concepts": hybrid_concepts(),
        "selected": CONCEPT_NAME,
        "learning_applied": (
            "Do not design a clever visual then attach facts. "
            "The commercial numeral must be the paper the object stands in."
        ),
    }


def creative_strategy() -> dict[str, Any]:
    chosen = selected_concept()
    return {
        "schema": "HybridCreativeStrategyV1",
        "engine": ENGINE_ID,
        "concept_name": CONCEPT_NAME,
        "concept": CONCEPT_SENTENCE,
        "headline": HEADLINE,
        "two_second": TWO_SECOND,
        "selected_real_assets": [
            {"filename": DAY003_FILENAME, "asset_id": DAY003_ASSET_ID, "role": "isolated Temple object"}
        ],
        "why_this_idea_fits_this_project": (
            "The Temple is literally stone that can be treated as collateral. "
            "Day_003 supplies a complete spire that can be lifted off the street and city without inventing architecture."
        ),
        "why_not_old_compiler": (
            "The old compiler can only wash a flattened plate and park facts in boxes. "
            "This idea requires a generated paper actor, object isolation, and occlusion."
        ),
        "why_not_proof_01_02_03": (
            "Not a letter İ, not a historic/new seam lockup, not portals as a commercial grid."
        ),
        "commercial_facts": {
            "project": "THE TEMPLE",
            "location": "WASHINGTON D.C.",
            "offer": f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
            "price": REQUIRED_FACTS["list_price"],
            "unit": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
            "cta": REQUIRED_FACTS["cta"],
            "closure": APPROVED_BOTTOM_COPY,
        },
        "reading_path": [
            "isolated Temple object on paper",
            "printed %35 in the paper, occluded by the building",
            "price as the vertical spine of the instrument",
            "unit as the legal line of that spine",
            "headline as the paper's title",
            "CTA as the document instruction",
        ],
        "hierarchy": "OBJECT_ON_PRINTED_OFFER",
        "banned_mechanisms": list(BANNED_MECHANISMS),
        "proof_01": "PRESERVED / REJECTED",
        "proof_02": "PRESERVED / REJECTED",
        "proof_03": "PRESERVED / REJECTED",
        "selected_concept": chosen,
        "master_01": "UNCHANGED",
        "master_02": "UNCHANGED",
        "master_03": "UNCHANGED",
    }
