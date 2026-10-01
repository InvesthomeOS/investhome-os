"""PremiumFormatRecomposerV1 — target-format art direction of an approved campaign.

The HUMAN_APPROVED Premium Master remains the Creative Director.
The system acts as a FORMAT ART DIRECTOR, not an autonomous Premium Designer.

This is not resize + reposition of semantic layers.
This is not a new campaign.
Stage 4.0 closed without executing another Story. Stage 4.1 is the visual proof.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from investhome_api.services.creative_director.creative_master_router_v2 import FORMAT_ADAPTATION
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    ADAPTER_ID,
    CANONICAL_FORMAT,
    PROOF_TARGET_FORMAT,
    STORY_CANVAS,
    select_production_premium_master,
    story_safe_zone_v1,
)
from investhome_api.services.creative_director.premium_story_recomposer_v1 import (
    CANVAS,
    CANVAS_H,
    CANVAS_W,
    _crop_frac,
    _scale,
    is_simple_resize,
    knock_navy,
    sample_navy,
)
from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import (
    FINAL_SEMANTIC_ROLES,
    refuse_if_unclean,
    strip_source_typography_from_photo,
    validate_semantic_exclusivity,
)
from investhome_api.services.creative_director.stage4_0_r2_compose import isolate_type, trim_alpha

RECOMPOSER_ID = "PremiumFormatRecomposerV1"
ROLE = "FORMAT ART DIRECTOR"
CREATIVE_DIRECTOR = "HUMAN_APPROVED Premium Master"
ACTION = "RECOMPOSE_PREMIUM_FORMAT"
STATUS = "FORMAT_ADAPTATION_METHOD_REQUIRES_RECOMPOSITION"
DEPRECATED_MODEL = "PremiumFormatAdapterV1 REPOSITION"
NEXT_STAGE = "STAGE 4.1 — ONE-SHOT 9:16 RECOMPOSITION VISUAL PROOF"

LOCK_FROM_MASTER = (
    "campaign idea",
    "copy",
    "brand identity",
    "approved imagery",
    "logo",
    "color system",
    "typographic personality",
    "graphic language",
    "semantic hierarchy",
    "visual relationships",
)

ALLOW_TARGET_FORMAT_ART_DIRECTION = (
    "composition",
    "layout geometry",
    "negative-space distribution",
    "image crop and scale",
    "text block dimensions",
    "line breaks",
    "relative placement",
    "visual balance",
    "logo placement",
    "reading path",
)

DO_NOT = (
    "generate a new campaign concept",
    "invent content",
    "invent imagery",
    "AI-redraw architecture",
    "change brand language",
    "change campaign message",
)

STRICT_FIDELITY = (
    "CONTENT FIDELITY",
    "CAMPAIGN IDENTITY",
    "PROJECT REALITY",
)

NOT_REQUIRED_FIDELITY = (
    "PIXEL POSITION FIDELITY",
    "LAYOUT GEOMETRY FIDELITY",
)

PRESERVED_TECHNICAL_FIXES = (
    "ONE PHOTO OBJECT",
    "NO DUPLICATE SEMANTIC LAYERS",
    "NO ORPHAN TEXT",
    "NO SOURCE-TYPE LEAKAGE",
)

ARCHIVED_STORY_TESTS = (
    {
        "revision": "RETRY",
        "status": "REJECTED",
        "reason": "upper half strong; lower half unfinished",
    },
    {
        "revision": "R1",
        "status": "REJECTED",
        "reason": "broken photo composition",
    },
    {
        "revision": "R2",
        "status": "REJECTED",
        "reason": "duplicate/orphan typography",
    },
    {
        "revision": "CLEAN",
        "status": "REJECTED",
        "reason": "weak vertical composition",
    },
    {
        "revision": "R3",
        "status": "REJECTED",
        "reason": "technically clean but professionally weak composition",
        "technical_integrity": "PASS",
        "design_quality": "FAIL",
    },
)


def permanent_format_adaptation_rule() -> dict[str, Any]:
    return {
        "schema": "PermanentPremiumFormatAdaptationRuleV1",
        "must_not_mean": "resize + reposition semantic layers",
        "must_mean": "RECOMPOSE THE APPROVED CAMPAIGN FOR THE TARGET FORMAT",
        "DESIGN_IDENTITY": "LOCKED",
        "LAYOUT_COORDINATES": "NOT LOCKED",
        "lock_from_master": list(LOCK_FROM_MASTER),
        "allow_target_format_art_direction": list(ALLOW_TARGET_FORMAT_ART_DIRECTION),
        "fidelity": {
            "STRICT": list(STRICT_FIDELITY),
            "NOT_REQUIRED": list(NOT_REQUIRED_FIDELITY),
        },
        "do_not": list(DO_NOT),
        "result_must_remain": "unmistakably the SAME CAMPAIGN",
    }


def preserved_technical_integrity() -> dict[str, Any]:
    return {
        "schema": "FormatRecomposerTechnicalIntegrityV1",
        "source": "semantic_layer_exclusivity_v1",
        "gates": list(PRESERVED_TECHNICAL_FIXES),
        "PHOTO_OBJECT_COUNT": 1,
        "SEMANTIC_LAYER_DUPLICATION_COUNT": 0,
        "ORPHAN_TEXT_FRAGMENT_COUNT": 0,
        "source_type_inside_PROJECT_PHOTO": "FORBIDDEN",
        "final_semantic_roles": list(FINAL_SEMANTIC_ROLES),
        "note": (
            "Stage 4.0 Story tests proved these gates are necessary and insufficient. "
            "Technical integrity is mandatory. Design quality requires recomposition."
        ),
    }


def archived_story_proof() -> dict[str, Any]:
    return {
        "schema": "Stage40StoryTestArchiveV1",
        "campaign": "ORNEK_00013",
        "source_format": CANONICAL_FORMAT,
        "target_format": PROOF_TARGET_FORMAT,
        "current_story": "REJECTED",
        "method": DEPRECATED_MODEL,
        "technical_fidelity": "PASS",
        "design_fidelity": "FAIL",
        "revisions": [dict(item) for item in ARCHIVED_STORY_TESTS],
        "do_not_create": "R4",
        "production_route": False,
        "preserved_fixes": list(PRESERVED_TECHNICAL_FIXES),
        "learned": {
            "adapter_can_preserve": [
                "semantic content",
                "brand identity",
                "photo integrity",
                "typography identity",
                "layer integrity",
            ],
            "adapter_cannot_yet": (
                "create a professionally art-directed composition "
                "when the aspect ratio changes substantially"
            ),
            "failure_is": "COMPOSITIONAL ADAPTATION",
            "failure_is_not": [
                "rendering",
                "duplicate layers",
                "project reality",
                "photo integrity",
                "semantic extraction",
            ],
        },
    }


def recomposer_contract() -> dict[str, Any]:
    return {
        "schema": RECOMPOSER_ID,
        "role": ROLE,
        "creative_director": CREATIVE_DIRECTOR,
        "is_not": [
            "autonomous Premium creative generation",
            "a new campaign",
            "resize + reposition semantic layers",
            "GPT Image redesign",
        ],
        "input": ["HUMAN_APPROVED Premium Master", "PremiumSemanticMapV1", "target format"],
        "output": "Format Child pending human visual review",
        "permanent_rule": permanent_format_adaptation_rule(),
        "technical_integrity": preserved_technical_integrity(),
        "safe_zones": story_safe_zone_v1(),
        "deprecated_model": DEPRECATED_MODEL,
        "deprecated_adapter": ADAPTER_ID,
        "executed": False,
        "story_generated": False,
        "gpt_image_calls": 0,
        "status": STATUS,
        "next": NEXT_STAGE,
    }


def prepare_format_recomposition(
    library: dict[str, Any] | None,
    *,
    target_format: str = PROOF_TARGET_FORMAT,
    project_id: str | None = None,
    scope: str | None = None,
    brand_id: str | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    """Route and plan only. Stage 4.0 does not execute a Story. Stage 4.1 is next."""
    if execute:
        raise RuntimeError(
            "PremiumFormatRecomposerV1 must not execute a Story in Stage 4.0. "
            f"Next: {NEXT_STAGE}"
        )
    selected = select_production_premium_master(
        library,
        project_id=project_id,
        scope=scope,
        brand_id=brand_id,
    )
    return {
        "schema": RECOMPOSER_ID,
        "action": ACTION,
        "status": STATUS,
        "executed": False,
        "story_generated": False,
        "format_child": None,
        "target_format": target_format,
        "source_master_id": None if selected is None else selected.get("master_id"),
        "source_master_present": selected is not None,
        "deprecated_model": DEPRECATED_MODEL,
        "contract": recomposer_contract(),
        "archive": archived_story_proof(),
        "gpt_image_calls": 0,
        "next": NEXT_STAGE,
        "note": (
            "Design identity is locked. Layout coordinates are not locked. "
            "Reposition model is deprecated. Visual proof waits for Stage 4.1."
        ),
    }


def route_format_adaptation(*, current_master_id: str | None = None) -> dict[str, Any]:
    return {
        "revision_intent": FORMAT_ADAPTATION,
        "action": ACTION,
        "engine": RECOMPOSER_ID,
        "role": ROLE,
        "selected_master_id": current_master_id,
        "regenerate": False,
        "executed": False,
        "deprecated_model": DEPRECATED_MODEL,
        "reason": (
            "Recompose the approved campaign for the target format. "
            "Do not resize-and-reposition semantic layers. "
            f"Visual proof is {NEXT_STAGE}."
        ),
        "next": NEXT_STAGE,
    }


# Source crops measured from ORNEK_00013 4:5 pixels. Not inherited from Stage 4.0 Stories.
SRC_PHOTO = {"x": 0.0, "y": 0.20, "w": 0.43, "h": 0.80}
SRC_HEADLINE = {"x": 0.50, "y": 0.168, "w": 0.45, "h": 0.242}
SRC_BODY = {"x": 0.49, "y": 0.452, "w": 0.47, "h": 0.118}
SRC_HIGHLIGHT = {"x": 0.55, "y": 0.568, "w": 0.41, "h": 0.030}
SRC_LOGO = {"x": 0.64, "y": 0.858, "w": 0.34, "h": 0.128}

STORY_HEADLINE_TOP = 0.122
STORY_HEADLINE_RIGHT = 0.055
STORY_HEADLINE_SCALE = 1.18
STORY_BODY_SCALE = 1.22
STORY_BODY_GAP_PX = 44
STORY_HIGHLIGHT_GAP_PX = 8
STORY_LOGO_RIGHT = 0.065
STORY_LOGO_SCALE = 1.08
STORY_PHOTO_TOP = 0.198
PHOTO_RIGHT_FADE = 0.34


def _fade_right(layer: Image.Image, *, frac: float) -> Image.Image:
    """Dissolve the photo's right edge into the navy field. Not a second photo."""
    layer = layer.convert("RGBA")
    w, h = layer.size
    fade_w = max(1, int(w * frac))
    start = w - fade_w
    pix = layer.load()
    for y in range(h):
        for x in range(start, w):
            t = (x - start) / fade_w
            r, g, b, a = pix[x, y]
            pix[x, y] = (r, g, b, int(a * (1.0 - t * t)))
    return layer


def _paste_right(canvas: Image.Image, layer: Image.Image, *, right: float, y: int) -> tuple[int, int]:
    x = int(CANVAS_W - right * CANVAS_W - layer.size[0])
    x = min(max(28, x), CANVAS_W - layer.size[0] - 28)
    y = max(0, y)
    canvas.alpha_composite(layer, (x, y))
    return (x, y)


def execute_ornek_00013_story(original: Image.Image) -> dict[str, Any]:
    """One-shot native 9:16 recomposition from the approved 4:5 master."""
    if original.size[0] < 1000 or original.size[1] < 1200:
        raise RuntimeError("PremiumFormatRecomposerV1 requires the original 4:5 master pixels")
    navy = sample_navy(original)
    canvas = Image.new("RGBA", CANVAS, navy + (255,))
    type_boxes = (SRC_HEADLINE, SRC_BODY, SRC_HIGHLIGHT, SRC_LOGO)

    photo_h = CANVAS_H - int(STORY_PHOTO_TOP * CANVAS_H)
    src_h = max(1, int(SRC_PHOTO["h"] * original.size[1]))
    photo_scale = photo_h / src_h
    photo = strip_source_typography_from_photo(
        original,
        _scale(_crop_frac(original, SRC_PHOTO), photo_scale),
        SRC_PHOTO,
        type_boxes,
        navy,
    )
    photo = _fade_right(photo, frac=PHOTO_RIGHT_FADE)
    photo_x = 0
    photo_y = CANVAS_H - photo.size[1]
    canvas.alpha_composite(photo, (photo_x, max(0, photo_y)))

    headline = trim_alpha(
        isolate_type(_scale(_crop_frac(original, SRC_HEADLINE), STORY_HEADLINE_SCALE), navy)
    )
    body = trim_alpha(isolate_type(_scale(_crop_frac(original, SRC_BODY), STORY_BODY_SCALE), navy))
    highlight = trim_alpha(
        knock_navy(_scale(_crop_frac(original, SRC_HIGHLIGHT), STORY_BODY_SCALE), navy, tol=18)
    )
    logo = trim_alpha(
        isolate_type(_scale(_crop_frac(original, SRC_LOGO), STORY_LOGO_SCALE), navy, min_lum=145)
    )

    head_xy = _paste_right(
        canvas, headline, right=STORY_HEADLINE_RIGHT, y=int(STORY_HEADLINE_TOP * CANVAS_H)
    )
    body_y = head_xy[1] + headline.size[1] + STORY_BODY_GAP_PX
    body_xy = _paste_right(canvas, body, right=STORY_HEADLINE_RIGHT, y=body_y)
    highlight_y = body_xy[1] + body.size[1] + STORY_HIGHLIGHT_GAP_PX
    highlight_xy = _paste_right(canvas, highlight, right=STORY_HEADLINE_RIGHT, y=highlight_y)

    logo_x = int(CANVAS_W - STORY_LOGO_RIGHT * CANVAS_W - logo.size[0])
    copy_end = highlight_xy[1] + highlight.size[1]
    logo_y = photo_y + int(0.64 * photo.size[1])
    logo_y = max(logo_y, copy_end + 72)
    logo_y = min(logo_y, int(0.82 * CANVAS_H) - logo.size[1])
    logo_x = min(max(28, logo_x), CANVAS_W - logo.size[0] - 36)
    canvas.alpha_composite(logo, (logo_x, max(0, logo_y)))

    story = canvas.convert("RGB")
    if tuple(story.size) != CANVAS:
        raise RuntimeError("Recomposed Story is not 1080×1920")
    if is_simple_resize(original, story):
        raise RuntimeError("PREMIUM_RECOMPOSITION_FAIL simple resize")

    placements = {
        "PHOTO": {
            "xy": [photo_x, photo_y],
            "size": list(photo.size),
            "crop": dict(SRC_PHOTO),
            "scale": photo_scale,
        },
        "HEADLINE": {"xy": list(head_xy), "size": list(headline.size)},
        "SUBHEAD": {"xy": list(body_xy), "size": list(body.size)},
        "LASTLINE": {"xy": list(highlight_xy), "size": list(highlight.size)},
        "LOGO": {"xy": [logo_x, logo_y], "size": list(logo.size)},
    }
    validation = validate_semantic_exclusivity(
        story=story,
        placements=placements,
        navy=navy,
        photo_pastes=1,
        layer_roles=["PROJECT_PHOTO", "HEADLINE", "BODY_COPY", "HIGHLIGHT", "LOGO"],
    )
    validation["GENERATED_ARCHITECTURE_PIXELS"] = 0
    refuse_if_unclean(validation)
    if validation.get("SOURCE_TYPE_LEAKAGE", 0) != 0:
        raise RuntimeError("PREMIUM_RECOMPOSITION_FAIL source type leakage")
    return {
        "story": story,
        "navy": navy,
        "photo_pastes": 1,
        "simple_resize": False,
        "generated_architecture_pixels": 0,
        "placements": placements,
        "validation": validation,
        "engine": RECOMPOSER_ID,
        "canvas": dict(STORY_CANVAS),
    }
