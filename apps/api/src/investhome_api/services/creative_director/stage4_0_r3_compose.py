"""Stage 4.0-R3 — composition polish of the CLEAN Story. No adapter changes."""

from __future__ import annotations

from typing import Any

from PIL import Image

from investhome_api.services.creative_director.premium_story_recomposer_v1 import (
    CANVAS,
    CANVAS_H,
    CANVAS_W,
    _crop_frac,
    _scale,
    knock_navy,
    sample_navy,
)
from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import (
    refuse_if_unclean,
    strip_source_typography_from_photo,
    validate_semantic_exclusivity,
)
from investhome_api.services.creative_director.stage4_0_r2_compose import (
    HEADLINE,
    LASTLINE,
    LOGO,
    PHOTO,
    SUBHEAD,
    isolate_type,
    trim_alpha,
)

# Same CLEAN crops. Placement only.
R3_HEADLINE_TOP = 0.142
R3_BODY_TOP = 0.352
R3_BODY_SCALE = 1.08
R3_PHOTO_TOP = 0.268
R3_LOGO_RIGHT = 0.07


def compose_story_r3(original: Image.Image) -> dict[str, Any]:
    if original.size[0] < 1000 or original.size[1] < 1200:
        raise RuntimeError("Stage 4.0-R3 requires the original 4:5 master")
    navy = sample_navy(original)
    canvas = Image.new("RGBA", CANVAS, navy + (255,))

    type_boxes = (HEADLINE, SUBHEAD, LASTLINE, LOGO)
    photo = strip_source_typography_from_photo(
        original,
        _scale(_crop_frac(original, PHOTO), PHOTO["scale"]),
        PHOTO,
        type_boxes,
        navy,
    )
    photo_x = int(PHOTO["x_px"])
    photo_y = int(R3_PHOTO_TOP * CANVAS_H)
    canvas.alpha_composite(photo, (photo_x, max(0, photo_y)))
    photo_right = photo_x + photo.size[0]

    headline = trim_alpha(isolate_type(_scale(_crop_frac(original, HEADLINE), HEADLINE["scale"]), navy))
    subhead = trim_alpha(isolate_type(_scale(_crop_frac(original, SUBHEAD), R3_BODY_SCALE), navy))
    lastline = knock_navy(_scale(_crop_frac(original, LASTLINE), R3_BODY_SCALE), navy, tol=18)
    logo = trim_alpha(isolate_type(_scale(_crop_frac(original, LOGO), LOGO["scale"]), navy, min_lum=145))

    def paste_right(layer: Image.Image, *, right: float, top: float) -> tuple[int, int]:
        x = int(CANVAS_W - right * CANVAS_W - layer.size[0])
        y = int(top * CANVAS_H)
        x = min(max(24, x), CANVAS_W - layer.size[0] - 24)
        y = max(0, y)
        canvas.alpha_composite(layer, (x, y))
        return (x, y)

    head_xy = paste_right(headline, right=HEADLINE["right"], top=R3_HEADLINE_TOP)
    sub_xy = paste_right(subhead, right=SUBHEAD["right"], top=R3_BODY_TOP)
    last_top = (sub_xy[1] + int((LASTLINE["y"] - SUBHEAD["y"]) * original.size[1] * R3_BODY_SCALE)) / CANVAS_H
    last_xy = paste_right(lastline, right=LASTLINE["right"], top=last_top)

    logo_x = int(CANVAS_W - R3_LOGO_RIGHT * CANVAS_W - logo.size[0])
    logo_x = max(logo_x, photo_right + 36)
    logo_x = min(logo_x, CANVAS_W - logo.size[0] - 40)
    copy_end = last_xy[1] + lastline.size[1]
    logo_y = photo_y + int(0.62 * photo.size[1])
    logo_y = max(logo_y, copy_end + 56)
    logo_y = min(logo_y, photo_y + photo.size[1] - logo.size[1] - 72)
    canvas.alpha_composite(logo, (max(0, logo_x), max(0, logo_y)))

    story = canvas.convert("RGB")
    if story.size != CANVAS:
        raise RuntimeError("R3 Story is not 1080×1920")
    placements = {
        "PHOTO": {"xy": [photo_x, photo_y], "size": list(photo.size), "crop": PHOTO, "scale": PHOTO["scale"]},
        "HEADLINE": {"xy": list(head_xy), "size": list(headline.size)},
        "SUBHEAD": {"xy": list(sub_xy), "size": list(subhead.size)},
        "LASTLINE": {"xy": list(last_xy), "size": list(lastline.size)},
        "LOGO": {"xy": [logo_x, logo_y], "size": list(logo.size)},
    }
    validation = validate_semantic_exclusivity(
        story=story,
        placements=placements,
        navy=navy,
        photo_pastes=1,
        layer_roles=["PROJECT_PHOTO", "HEADLINE", "BODY_COPY", "HIGHLIGHT", "LOGO"],
    )
    refuse_if_unclean(validation)
    return {
        "story": story,
        "navy": navy,
        "photo_pastes": 1,
        "placements": placements,
        "validation": validation,
    }
