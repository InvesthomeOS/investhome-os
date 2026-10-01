"""Phase 9.1 — Premium Campaign 03 compositor.

LOOKING CHAMBER: a dark designed lid and a photographic aperture turn a
real Temple interior into a looking chamber. Historic architecture is the view.
"""

from __future__ import annotations

import os
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
LID = 0.40
SEAM = int(H * LID)
INK_LIGHT = "#F3E6D4"
INK_MUTED = "#C9B79A"

ORNEK_FILENAME = "ORNEK_00006.jpg"
ORNEK_ASSET_ID = "be3741ba-bd2a-4d10-87bd-e91e80d12af7"
INTERIOR_FILENAME = "IH_DC_TMP_001_Render_Living_Room_001.jpg"
INTERIOR_ASSET_ID = "c3d11c35-d8b7-485c-b216-0a4da68b751a"
ARCHITECTURE_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_002.jpg"
ARCHITECTURE_ASSET_ID = "543aeb03-c4c9-46f9-9d9f-81bf53f45438"

INTERIOR_CENTERING = (0.40, 0.42)
ARCHITECTURE_CENTERING = (0.62, 0.34)
INTERIOR_GRADE = {"warmth": 0.08, "contrast": 1.04, "brightness": 0.96, "vignette": 0.12}
ARCHITECTURE_GRADE = {"warmth": 0.04, "contrast": 1.06, "brightness": 0.98, "vignette": 0.08}

APERTURE = {"left": 0.655, "top": 0.125, "width": 0.305, "height": 0.42}

CONCEPT = {
    "schema": "CreativeConceptMaster03",
    "concept_name": "LOOKING_CHAMBER",
    "concept_sentence": (
        "The campaign uses a dark designed lid and a photographic aperture to transform "
        "a real Temple interior into a looking chamber, so historic architecture becomes "
        "the view the room opens onto."
    ),
    "visual_gesture": (
        "Warm charcoal lid occupies the upper canvas as a designed ceiling. "
        "A real Temple interior holds the lower canvas as the chamber. "
        "A framed photographic aperture of real Temple architecture bites through the seam."
    ),
    "photo_graphic_relationship": (
        "Two real photographs. The interior is the world. The architecture is the view. "
        "The lid is graphic design, not fake rooms. The aperture is a designed window, not a badge."
    ),
    "why_not_master_01": "Not full-canvas exterior. Not type in photographic sky.",
    "why_not_master_02": "Not parchment. Not L-shaped page-cut. Not Sunset_001. Not spire as page division.",
    "why_not_ornek_copy": "Does not copy Uniloft, people, Investhome, or a centered header stack.",
}

SHORTLIST = (
    (INTERIOR_FILENAME, INTERIOR_ASSET_ID, "CHAMBER — looking-out windows, depth"),
    (ARCHITECTURE_FILENAME, ARCHITECTURE_ASSET_ID, "VIEW — street spire for the aperture"),
    ("IH_DC_TMP_001_Render_Living_Room_005.jpg", "8837fa06-d71b-4c26-a5cb-9cb682748311", "interior depth, balcony doors"),
    ("IH_DC_TMP_001_Render_Bedroom_007.jpg", "2635b01e-6580-4511-82fe-a16fba510b41", "dusk chamber, window plane"),
    ("IH_DC_TMP_001_Render_Living_Room_004.jpeg", "81922792-e644-4752-a5dd-70923311d9bb", "layered interior volume"),
    ("IH_DC_TMP_001_Render_Exterior_Day_007.jpg", "c0afa1bf-b487-410c-be3d-91c31852550d", "aerial temple mass — not selected"),
)

PHOTO_SELECTION = {
    "schema": "PhotoSelectionMaster03",
    "reference": ORNEK_FILENAME,
    "selected": [
        {
            "filename": INTERIOR_FILENAME,
            "asset_id": INTERIOR_ASSET_ID,
            "role": "CHAMBER — the room the campaign lives inside",
        },
        {
            "filename": ARCHITECTURE_FILENAME,
            "asset_id": ARCHITECTURE_ASSET_ID,
            "role": "VIEW — historic architecture seen through the aperture",
        },
    ],
    "reason": (
        "Living_Room_001 has the strongest looking-out windows and interior depth for ORNEK_00006's "
        "chamber DNA. Day_002 has the strongest street-level spire to become the view, without "
        "reusing Master 01's Day_003 or Master 02's Sunset_001."
    ),
}

DISTINCTNESS_PRE = {
    "IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_01": "YES",
    "IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_02": "YES",
    "DOES_THE_CONCEPT_EXIST_WITHOUT_COPY": "YES",
    "IS_THERE_A_CLEAR_VISUAL_MECHANISM": "YES",
}


def crop_interior(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, (W, H - SEAM), centering=INTERIOR_CENTERING)
    graded = apply_photographic_grade(crop, dict(INTERIOR_GRADE))
    transform = dict(transform)
    transform["centering"] = list(INTERIOR_CENTERING)
    transform["role"] = "chamber"
    return graded, transform


def crop_architecture(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    aw, ah = int(W * APERTURE["width"]), int(H * APERTURE["height"])
    crop, transform = cover_fit_canvas(source, (aw, ah), centering=ARCHITECTURE_CENTERING)
    graded = apply_photographic_grade(crop, dict(ARCHITECTURE_GRADE))
    transform = dict(transform)
    transform["centering"] = list(ARCHITECTURE_CENTERING)
    transform["role"] = "aperture_view"
    return graded, transform


def _lid(size: tuple[int, int]) -> Image.Image:
    width, height = size
    band = Image.new("RGB", (1, height))
    pix = band.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        pix[0, y] = (
            int(28 + t * 10),
            int(22 + t * 8),
            int(16 + t * 6),
        )
    image = band.resize((width, height), Image.Resampling.BILINEAR)
    noise = Image.frombytes("L", (width, height), os.urandom(width * height))
    return Image.blend(image, Image.merge("RGB", (noise, noise, noise)), 0.05)


def _aperture_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    inset = 10
    draw.rounded_rectangle((inset, inset, size[0] - inset, size[1] - inset), radius=5, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=1.4))


def _aperture_frame(size: tuple[int, int]) -> Image.Image:
    frame = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    inset = 10
    draw.rounded_rectangle((inset, inset, size[0] - inset, size[1] - inset), radius=5, outline=(243, 230, 212, 210), width=2)
    return frame


def designed_chamber(*, interior: Image.Image, architecture: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Dark lid + real interior + photographic aperture. Must read as design without type."""
    canvas = Image.new("RGB", CANVAS_4X5, (24, 18, 14))
    lid = _lid((W, SEAM + 6))
    canvas.paste(lid, (0, 0))
    canvas.paste(interior.convert("RGB"), (0, SEAM))
    draw = ImageDraw.Draw(canvas)
    draw.line((0, SEAM, int(W * APERTURE["left"]) - 8, SEAM), fill=(198, 176, 148), width=1)

    view = architecture.convert("RGB")
    ax = int(W * APERTURE["left"])
    ay = int(H * APERTURE["top"])
    mask = _aperture_mask(view.size)
    canvas.paste(view, (ax, ay), mask)
    frame = _aperture_frame(view.size)
    canvas.paste(frame, (ax, ay), frame)

    meta = {
        "lid": LID,
        "seam": SEAM,
        "aperture": dict(APERTURE),
        "interior": INTERIOR_FILENAME,
        "architecture": ARCHITECTURE_FILENAME,
        "concept": CONCEPT["concept_name"],
    }
    return canvas, meta


def master_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#1c1612;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.brand{{position:absolute;left:5.0%;top:2.8%;width:268px;height:64px;}}
.brand svg{{width:268px;height:64px;display:block;filter:brightness(0) invert(1);opacity:.92;}}
.loc{{position:absolute;left:5.2%;top:9.4%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.38em;font-weight:500;}}
.line1,.line2{{position:absolute;left:5.0%;margin:0;padding:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-weight:500;font-size:76px;line-height:.94;letter-spacing:.04em;}}
.line1{{top:12.2%;}}
.line2{{top:19.4%;}}
.commercial{{position:absolute;left:5.2%;top:28.4%;display:flex;align-items:center;gap:16px;color:{INK_LIGHT};}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:52px;font-weight:500;line-height:.9;letter-spacing:.02em;}}
.offer{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.22em;font-weight:600;line-height:1.35;}}
.price{{position:absolute;left:5.2%;top:34.6%;margin:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:500;letter-spacing:.06em;}}
.unit{{margin-left:14px;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.18em;font-weight:600;opacity:.88;}}
.cta{{position:absolute;left:5.2%;top:37.2%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.30em;font-weight:600;}}
.ed{{position:absolute;left:5.2%;top:38.8%;margin:0;color:{INK_MUTED};
  font-family:'Cormorant Garamond',serif;font-size:13px;letter-spacing:.08em;font-weight:500;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="brand">{logo_markup}</div>
  <p class="loc">WASHINGTON D.C.</p>
  <p class="line1">ALIRKEN</p>
  <p class="line2">KAZAN</p>
  <div class="commercial">
    <div class="pct">%35</div>
    <div class="offer">LANSMAN<br>AVANTAJI</div>
  </div>
  <p class="price">675.000 USD<span class="unit">{unit}</span></p>
  <p class="cta">{REQUIRED_FACTS["cta"]}</p>
  <p class="ed">{APPROVED_BOTTOM_COPY}</p>
</div>
</body>
</html>
"""


def compose_master_03(*, interior: Image.Image, architecture: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str, dict[str, Any]]:
    chamber, meta = designed_chamber(interior=interior, architecture=architecture)
    registry = build_font_registry()
    html = master_html(
        scene_uri=_jpeg_data_uri(chamber, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    return image, chamber, html, meta


def html_copy_ok(html: str) -> bool:
    needed = (
        "ALIRKEN",
        "KAZAN",
        "%35",
        "LANSMAN",
        "AVANTAJI",
        "675.000 USD",
        "2+1",
        "DAİRE",
        "PROJEYİ KEŞFET",
        APPROVED_BOTTOM_COPY,
        "WASHINGTON D.C.",
    )
    return (
        all(token in html for token in needed)
        and "THE TEMPLE" not in html
        and "investhome" not in html.lower()
        and "uniloft" not in html.lower()
        and "text-align:center" not in html
        and "#ead3b3" not in html
        and "border-radius:999" not in html
    )


def render_shortlist(items: list[tuple[str, Image.Image, str]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "03  TEMPLE PHOTO SHORTLIST  —  scored for ORNEK_00006 looking-chamber", font=_font(18), fill=GOLD)
    x, y = 36, 56
    for i, (label, image, note) in enumerate(items[:6]):
        tile = image.copy()
        tile.thumbnail((580, 420), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + 430), label[:42], font=_font(13), fill=IVORY)
        draw.text((x, y + 450), note[:48], font=_font(13), fill=GOLD)
        x += 620
        if i == 2:
            x, y = 36, 540
    return canvas


def render_assets(interior: Image.Image, architecture: Image.Image, logo_rgba: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1760, 1080), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "04  SELECTED PROJECT ASSETS  —  chamber + view + real Temple logo", font=_font(18), fill=GOLD)
    x = 36
    for title, image in (("CHAMBER  Living_Room_001", interior), ("VIEW  Exterior_Day_002", architecture)):
        tile = image.copy()
        tile.thumbnail((720, 780), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 860), title, font=_font(16), fill=IVORY)
        x += 760
    logo = logo_rgba.convert("RGBA")
    logo.thumbnail((280, 140), Image.Resampling.LANCZOS)
    plate = Image.new("RGB", (340, 180), (243, 230, 212))
    px = (340 - logo.size[0]) // 2
    py = (180 - logo.size[1]) // 2
    plate.paste(logo, (px, py), logo)
    canvas.paste(plate, (36, 900))
    draw.text((400, 960), "LOCKED LOGO  7b58877e-efca-4e9a-9027-6fd18fb1b345", font=_font(14), fill=GOLD)
    return canvas


def render_triple(m01: Image.Image, m02: Image.Image, m03: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1980, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "07  MASTER 01 / 02 / 03  —  three campaign families", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (
        ("MASTER 01  sky typography  LOCKED", m01),
        ("MASTER 02  spire page-cut  LOCKED", m02),
        ("MASTER 03  looking chamber  DRAFT", m03),
    ):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1100), label[:48], font=_font(15), fill=IVORY)
        x += 640
    return canvas


def render_labeled(image: Image.Image, title: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1128, 1360), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    draw.text((36, 1436), caption[:70], font=_font(14), fill=IVORY)
    return canvas
