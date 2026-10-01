"""Phase 7.2 — immutable project photograph as a creative object."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE, format_adaptation_spec, semantic_revision_contract

PROJECT_CREATIVE_RULE = "IMMUTABLE_PROJECT_PHOTO_OBJECT"
PHOTO_MIN_MASS = 0.35
PHOTO_MAX_MASS = 0.70

TERRITORIES_72 = (
    "PROJECT_PHOTO_OBJECT",
    "CREATIVE_BACKGROUND",
    "BRAND",
    "HEADLINE",
    "OFFER",
    "PRICE",
    "UNIT",
    "CTA",
    "EDITORIAL_CLOSURE",
    "DECORATIVE_GRAPHICS",
)

PHOTO_ROLES = (
    "full_height_photographic_plane",
    "architectural_window",
    "curved_photographic_aperture",
    "offset_photographic_cutout",
    "layered_architectural_frame",
)

ALLOWED_PHOTO_TRANSFORMS = (
    "uniform_scale",
    "crop",
    "position",
    "mask",
    "clip",
    "border_radius",
    "color_grade",
    "brightness",
    "contrast",
    "temperature",
    "controlled_shadow_glow_outside",
)

FORBIDDEN_PHOTO_TRANSFORMS = (
    "ai_edit_inside_photograph",
    "generative_fill_inside_photograph",
    "outpaint",
    "inpaint",
    "architectural_modification",
    "window_modification",
    "spire_modification",
    "facade_modification",
    "generated_people_or_objects_inside_project_photo",
)


def project_photo_object_rule() -> dict[str, Any]:
    return {
        "schema": "ImmutableProjectPhotoObjectV1",
        "rule": PROJECT_CREATIVE_RULE,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "principle": "Real project photography does not have to be the full-canvas background.",
        "ai_may_design": [
            "background",
            "graphic environment",
            "editorial fields",
            "typography",
            "geometry",
            "decorative systems",
            "atmosphere",
            "campaign framing",
            "negative space",
            "commercial storytelling",
            "CTA",
            "brand environment",
        ],
        "photograph_immutable": True,
        "source_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "allowed_transformations": list(ALLOWED_PHOTO_TRANSFORMS),
        "forbidden_transformations": list(FORBIDDEN_PHOTO_TRANSFORMS),
        "visual_mass": {"min": PHOTO_MIN_MASS, "max": PHOTO_MAX_MASS},
        "not": [
            "generic property card",
            "listing card",
            "web UI",
            "dashboard panel",
            "small thumbnail",
            "brochure grid",
            "boxed photo with ordinary caption",
        ],
    }


def empty_semantic_spec_72(*, visual_asset_id: str | None = None, candidate_id: str | None = None) -> dict[str, Any]:
    spec = {
        "schema": "SemanticCreativeSpecV1",
        "master_id": None,
        "candidate_id": candidate_id,
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
        "visual_territories": {name: {"present": True, "box": None, "notes": ""} for name in TERRITORIES_72},
        "protected_territories": ["PROJECT_PHOTO_OBJECT", "BRAND"],
        "editable_territories": ["HEADLINE", "OFFER", "PRICE", "UNIT", "CTA", "EDITORIAL_CLOSURE"],
        "visual_replace_territory": "PROJECT_PHOTO_OBJECT",
        "PROJECT_PHOTO_OBJECT": {"immutable": True, "source": "REAL_DAY_007"},
        "pixel_complete_scene_graph": False,
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
    }
    return spec


def revision_readiness_72() -> dict[str, Any]:
    rev = semantic_revision_contract()
    rev["VISUAL_REPLACE_ONLY"] = {
        "status": "PASS",
        "example": "Bu proje görseli yerine diğer dış cepheyi kullan.",
        "allowed": ["PROJECT_PHOTO_OBJECT"],
        "protected": [
            "CREATIVE_BACKGROUND",
            "HEADLINE",
            "OFFER",
            "PRICE",
            "UNIT",
            "BRAND",
            "CTA",
            "EDITORIAL_CLOSURE",
            "DECORATIVE_GRAPHICS",
            "campaign design",
        ],
        "note": "Replace the immutable photo object, then adjust crop/position/scale. Do not regenerate the master.",
    }
    rev["executed"] = False
    return rev


def format_readiness_72() -> dict[str, Any]:
    fmt = format_adaptation_spec()
    fmt["note"] = "Concept structure only. No adaptations executed."
    return fmt
