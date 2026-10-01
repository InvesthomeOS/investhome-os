"""Phase 7.0 production doctrine — visual master + semantic revision.

Not a renderer. Not a full editable scene graph.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_CAMPAIGN_ID,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY

PRODUCTION_DOCTRINE = "QUALITY_FIRST_VISUAL_MASTER"
PRIMARY_CREATIVE_ENGINE = "GPT_IMAGE_EDIT_VISUAL_MASTER"
MASTER_TYPE = "VISUAL_MASTER"
CANVAS = {"width": 1088, "height": 1360, "aspect": "4:5"}

RETIRED_RESEARCH_BRANCHES = (
    "6.1",
    "6.1-R1",
    "6.2",
    "6.3",
    "6.3A",
    "6.3B",
    "6.4",
)

SEMANTIC_COPY_FIELDS = (
    "headline",
    "offer",
    "price",
    "old_price",
    "savings",
    "unit",
    "CTA",
    "editorial_closure",
)

VISUAL_TERRITORIES = (
    "PROJECT_PHOTO_TERRITORY",
    "BRAND_TERRITORY",
    "HEADLINE_TERRITORY",
    "COMMERCIAL_TERRITORY",
    "CTA_TERRITORY",
    "EDITORIAL_CLOSURE_TERRITORY",
)

RELATIONSHIPS = (
    "headline_to_photo",
    "offer_to_headline",
    "CTA_to_offer",
    "logo_to_brand_zone",
    "closure_to_canvas",
)


def production_doctrine() -> dict[str, Any]:
    return {
        "schema": "ProductionDoctrineV1",
        "doctrine": PRODUCTION_DOCTRINE,
        "principle": "QUALITY FIRST. Do not destroy campaign visual quality to obtain theoretical full editability.",
        "product_experience": "natural language only",
        "user_never_sees": [
            "layers",
            "scene graphs",
            "renderer modes",
            "technical masks",
            "edit maps",
            "templates",
        ],
        "pipeline": [
            "USER REQUEST",
            "CREATIVE DIRECTOR",
            "AI VISUAL MASTER",
            "SEMANTIC DESIGN SPEC",
            "MASTER LOCK",
            "CONTROLLED REVISION ENGINE",
            "FORMAT ADAPTATION ENGINE",
        ],
        "primary_creative_engine": PRIMARY_CREATIVE_ENGINE,
        "master_type": MASTER_TYPE,
        "full_editability_required": False,
        "required_editability": "semantic and user-goal based",
        "not_required_to_remain_individually_editable": [
            "decorative curves",
            "gradients",
            "masks",
            "blends",
            "artistic treatments",
        ],
        "project_safety": {
            "real_project_photography": True,
            "real_project_logo": True,
            "no_invented_architecture": True,
            "no_generated_logo": True,
            "ai_may_author": [
                "graphic treatment",
                "lighting treatment",
                "graphic overlays",
                "decorative geometry",
                "typographic art direction",
            ],
        },
        "research_branches_retired": list(RETIRED_RESEARCH_BRANCHES),
        "research_artifacts_retained": True,
        "stopped_engines": [
            "GraphicDesignCompositorV4 as primary creative engine",
            "GraphicDesignCompositorV5",
            "Chromium craft reconstruction",
            "AI-authored full structured scene as primary production master",
            "pixel-perfect Concept 3 reconstruction",
            "renderer capability research",
        ],
        "no_phase_6_5": True,
        "concept3_role": "quality benchmark and campaign DNA, not a skyline to recreate",
        "gold_standard_asset_id": CONCEPT3_ASSET_ID,
    }


def empty_semantic_spec(*, master_id: str | None = None, visual_asset_id: str | None = None) -> dict[str, Any]:
    return {
        "schema": "SemanticCreativeSpecV1",
        "master_id": master_id,
        "project_id": TEMPLE_PROJECT_ID,
        "campaign_id": PRODUCTION_CAMPAIGN_ID,
        "canvas": dict(CANVAS),
        "approved_visual_asset": visual_asset_id,
        "source_project_photo": DAY007_ASSET_ID,
        "source_logo": LOCKED_LOGO_ASSET_ID,
        "semantic_copy": {
            "headline": REQUIRED_FACTS["headline"],
            "offer": f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
            "price": REQUIRED_FACTS["list_price"],
            "old_price": None,
            "savings": REQUIRED_FACTS["discount"],
            "unit": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
            "CTA": REQUIRED_FACTS["cta"],
            "editorial_closure": APPROVED_BOTTOM_COPY,
        },
        "visual_territories": {name: {"present": True, "box": None, "notes": ""} for name in VISUAL_TERRITORIES},
        "relationships": {name: {"present": True, "notes": ""} for name in RELATIONSHIPS},
        "protected_territories": [
            "PROJECT_PHOTO_TERRITORY",
            "BRAND_TERRITORY",
        ],
        "editable_territories": [
            "HEADLINE_TERRITORY",
            "COMMERCIAL_TERRITORY",
            "CTA_TERRITORY",
            "EDITORIAL_CLOSURE_TERRITORY",
        ],
        "visual_replace_territory": "PROJECT_PHOTO_TERRITORY",
        "creative_dna": {
            "art_direction": "",
            "hierarchy": "",
            "visual_mass": "",
            "dominant_geometry": "",
            "palette": "",
            "graphic_motifs": "",
            "photo_treatment": "",
            "typographic_character": "",
        },
        "pixel_complete_scene_graph": False,
        "note": "Records what the system must understand. Does not describe every pixel.",
    }


def semantic_revision_contract() -> dict[str, Any]:
    return {
        "schema": "SemanticRevisionContractV1",
        "product_requirement": "change what the user requested; preserve everything else as closely as technically possible",
        "universal_renderer_required": False,
        "allowed_methods": [
            "localized AI edit",
            "structured local redraw",
            "masked recomposition",
            "source-photo replacement",
            "semantic regeneration",
        ],
        "PRICE_EDIT_ONLY": {
            "status": "PASS",
            "example": "Fiyatı 438.750 USD yap, başka hiçbir şeyi değiştirme.",
            "allowed": ["COMMERCIAL_TERRITORY"],
            "protected": [
                "PROJECT_PHOTO_TERRITORY",
                "HEADLINE_TERRITORY",
                "BRAND_TERRITORY",
                "CTA_TERRITORY",
                "EDITORIAL_CLOSURE_TERRITORY",
                "background",
                "other campaign design",
            ],
        },
        "COPY_EDIT_ONLY": {
            "status": "PASS",
            "example": "Başlığı değiştir.",
            "allowed": ["target semantic text territory", "minimal local recomposition if required"],
            "protected": ["all unrelated visual territories"],
        },
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS",
            "example": "Bu proje görseli yerine diğer dış cepheyi kullan.",
            "allowed": ["PROJECT_PHOTO_TERRITORY"],
            "protected": [
                "HEADLINE_TERRITORY",
                "COMMERCIAL_TERRITORY",
                "BRAND_TERRITORY",
                "CTA_TERRITORY",
                "graphic design",
                "brand treatment",
            ],
        },
        "revision_returns": [
            "intent",
            "changed semantic fields",
            "changed visual territories",
            "protected territories",
            "provider used",
            "visual preservation score",
            "architecture fidelity",
            "reversible YES/NO",
        ],
        "low_preservation_confidence": "do not silently redesign; return revision candidate for review",
        "executed": False,
    }


def format_adaptation_spec() -> dict[str, Any]:
    return {
        "schema": "FormatAdaptationSpecV1",
        "implemented": False,
        "status": "PASS",
        "meaning": "intelligent recomposition of the approved visual Master + SemanticCreativeSpec",
        "not": ["blind crop", "stretch", "simple resize"],
        "formats": {
            "4:5": {"role": "native master", "ready": "spec defined"},
            "1:1": {"role": "future restack", "ready": "spec defined"},
            "9:16": {"role": "future restack", "ready": "spec defined"},
            "16:9": {"role": "future restack", "ready": "spec defined"},
        },
        "example": "Bunu Story yap.",
        "requires": ["approved visual Master", "SemanticCreativeSpecV1"],
    }
