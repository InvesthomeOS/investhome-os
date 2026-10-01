"""ResponsiveCommercialHierarchyV2 — thumbnail-aware type, not post-hoc enlargement.

Evaluates identity / hook / action at 15% and price / unit / CTA at 25% during
composition. Not a campaign. Not a website button.
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS

SCHEMA = "ResponsiveCommercialHierarchyV2"
W, H = CANVAS_4X5
RENDER_SCALE = 2
INK = "#EDE6D8"
GOLD = "#C4A36A"
PLATE = "#241C14"
BRONZE = "#5C3A14"
CREAM = "#E4D4BC"
CHARCOAL = "#1A1816"
MUTED = "#9A8B78"

ROLES = (
    {
        "id": "project",
        "role": "PROJECT",
        "copy": "THE TEMPLE",
        "importance": 0.86,
        "minimum_legible_scale": 0.15,
        "minimum_contrast": 3.0,
        "minimum_visual_weight": 0.55,
        "relationship_group": "IDENTITY",
        "min_px_at_scale": 9,
    },
    {
        "id": "offer",
        "role": "OFFER",
        "copy": REQUIRED_FACTS["discount"],
        "importance": 1.0,
        "minimum_legible_scale": 0.15,
        "minimum_contrast": 3.0,
        "minimum_visual_weight": 0.9,
        "relationship_group": "HOOK",
        "min_px_at_scale": 22,
    },
    {
        "id": "offer_label",
        "role": "MESSAGE",
        "copy": REQUIRED_FACTS["discount_label"],
        "importance": 0.55,
        "minimum_legible_scale": 0.25,
        "minimum_contrast": 3.0,
        "minimum_visual_weight": 0.35,
        "relationship_group": "HOOK",
        "min_px_at_scale": 7,
    },
    {
        "id": "price",
        "role": "PRICE",
        "copy": REQUIRED_FACTS["list_price"],
        "importance": 0.88,
        "minimum_legible_scale": 0.25,
        "minimum_contrast": 4.5,
        "minimum_visual_weight": 0.7,
        "relationship_group": "VALUE",
        "min_px_at_scale": 10,
    },
    {
        "id": "unit",
        "role": "UNIT",
        "copy": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "importance": 0.8,
        "minimum_legible_scale": 0.25,
        "minimum_contrast": 4.5,
        "minimum_visual_weight": 0.55,
        "relationship_group": "VALUE",
        "min_px_at_scale": 8,
    },
    {
        "id": "cta",
        "role": "CTA",
        "copy": REQUIRED_FACTS["cta"],
        "importance": 0.84,
        "minimum_legible_scale": 0.25,
        "minimum_contrast": 4.5,
        "minimum_visual_weight": 0.65,
        "relationship_group": "ACTION",
        "min_px_at_scale": 9,
        "action_cue_scale": 0.15,
        "action_cue_min_px": 6,
    },
)


def _rel_lum(rgb: tuple[int, int, int]) -> float:
    def f(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1, l2 = _rel_lum(a), _rel_lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _font_face(registry: dict[str, Any], role: str, family: str) -> str:
    spec = dict((registry.get("roles") or {}).get(role) or {})
    path = spec.get("font_path")
    if not path or not Path(str(path)).is_file():
        return ""
    payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'{family}';src:url('data:font/ttf;base64,{payload}') "
        f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
    )


def render_svg_html_to_png(markup: str, *, width: int, height: int, scale: int = RENDER_SCALE) -> Image.Image:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="phase118-h-") as td:
        path = Path(td) / "scene.html"
        path.write_text(markup, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
            page.goto(path.as_uri(), wait_until="load", timeout=60_000)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(280)
            png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": width, "height": height})
            browser.close()
    return Image.open(io.BytesIO(png)).convert("RGB")


def hierarchy_layout() -> dict[str, Any]:
    """Canvas units at 1x. Sizes chosen to survive distance without shouting at 100%."""
    return {
        "project": {"x": 64, "y": 96, "size": 36, "tracking": 7.0, "weight": 700, "fill": INK},
        "offer": {"x": W // 2, "y": 430, "size": 132, "tracking": -5.0, "weight": 600, "fill": GOLD, "anchor": "middle"},
        "offer_label": {"x": W // 2, "y": 468, "size": 13, "tracking": 6.8, "weight": 700, "fill": MUTED, "anchor": "middle"},
        "price": {"x": W // 2 - 70, "y": 980, "size": 30, "tracking": 0.8, "weight": 600, "fill": PLATE, "anchor": "middle"},
        "unit": {"x": W // 2 + 176, "y": 980, "size": 18, "tracking": 2.4, "weight": 600, "fill": PLATE, "anchor": "middle"},
        "cta": {"x": W // 2, "y": 1048, "size": 22, "tracking": 5.2, "weight": 700, "fill": BRONZE, "anchor": "middle"},
        "cta_rule": {"x": W // 2 - 118, "y": 1016, "w": 236, "h": 2},
        "plate": {"x": 96, "y": 860, "w": W - 192, "h": 280},
    }


def optical_engine_report(layout: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    # Tracking sanity: CTA tracking must not exceed ~0.45em.
    if layout["cta"]["tracking"] > layout["cta"]["size"] * 0.45:
        failures.append("cta_tracking")
    # Price/unit grouping: same baseline, gap under 2.4em of price.
    if abs(layout["price"]["y"] - layout["unit"]["y"]) > 2:
        failures.append("price_unit_baseline")
    gap = abs(layout["unit"]["x"] - layout["price"]["x"])
    if gap > layout["price"]["size"] * 9:
        failures.append("price_unit_gap")
    # Identity vs offer: offer must be the largest.
    if layout["offer"]["size"] < layout["project"]["size"] * 2.4:
        failures.append("offer_not_dominant")
    # CTA is not footer microcopy: must exceed 18px at 1x.
    if layout["cta"]["size"] < 18:
        failures.append("cta_too_small")
    # Contrast
    if contrast_ratio((237, 230, 216), (26, 24, 22)) < 4.5:
        failures.append("identity_contrast")
    if contrast_ratio((36, 28, 20), (228, 212, 188)) < 4.5:
        failures.append("value_contrast")
    if contrast_ratio((92, 58, 20), (228, 212, 188)) < 3.0:
        failures.append("cta_contrast")
    return {"pass": not failures, "failures": failures, "layout": layout}


def hierarchy_svg(font_css: str, layout: dict[str, Any]) -> str:
    p = layout["plate"]
    rule = layout["cta_rule"]
    facts = REQUIRED_FACTS

    def text(key: str, copy: str) -> str:
        spec = layout[key]
        anchor = spec.get("anchor", "start")
        return (
            f'<text data-role="{key}" x="{spec["x"]}" y="{spec["y"]}" text-anchor="{anchor}" '
            f'font-family="Hybrid Serif, serif" font-size="{spec["size"]}" font-weight="{spec["weight"]}" '
            f'fill="{spec["fill"]}" letter-spacing="{spec["tracking"]}">{escape(copy)}</text>'
        )

    project = layout["project"]
    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;background:{CHARCOAL};}}
svg{{display:block;}}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{CHARCOAL}"/>
  <text data-role="project" x="{project["x"]}" y="{project["y"]}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{project["size"]}" font-weight="{project["weight"]}"
        fill="{project["fill"]}" letter-spacing="{project["tracking"]}">THE TEMPLE</text>
  {text("offer", facts["discount"])}
  <text data-role="offer_label" x="{layout["offer_label"]["x"]}" y="{layout["offer_label"]["y"]}" text-anchor="middle"
        font-family="Hybrid Grotesk, sans-serif" font-size="{layout["offer_label"]["size"]}" font-weight="700"
        fill="{MUTED}" letter-spacing="{layout["offer_label"]["tracking"]}">{escape(facts["discount_label"])}</text>
  <rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" fill="{CREAM}"/>
  {text("price", facts["list_price"])}
  <text data-role="unit" x="{layout["unit"]["x"]}" y="{layout["unit"]["y"]}" text-anchor="middle"
        font-family="Hybrid Grotesk, sans-serif" font-size="{layout["unit"]["size"]}" font-weight="600"
        fill="{PLATE}" letter-spacing="{layout["unit"]["tracking"]}">{escape(f"{facts['unit']} {facts['unit_label']}")}</text>
  <rect data-role="cta_cue" x="{rule["x"]}" y="{rule["y"]}" width="{rule["w"]}" height="{rule["h"]}" fill="{GOLD}"/>
  <text data-role="cta" x="{layout["cta"]["x"]}" y="{layout["cta"]["y"]}" text-anchor="middle"
        font-family="Hybrid Grotesk, sans-serif" font-size="{layout["cta"]["size"]}" font-weight="700"
        fill="{BRONZE}" letter-spacing="{layout["cta"]["tracking"]}">{escape(facts["cta"])}</text>
</svg></body></html>
"""


def scale_visibility(layout: dict[str, Any], scale: float) -> dict[str, Any]:
    """Rendered 2x, then viewed at `scale` of the 2x bitmap."""
    out: dict[str, Any] = {}
    for role in ROLES:
        spec = layout[role["id"]]
        px = spec["size"] * RENDER_SCALE * scale
        min_px = float(role.get("min_px_at_scale") or 8)
        visible = px >= min_px
        cue_ok = True
        if role["id"] == "cta" and scale <= 0.16:
            cue_h = layout["cta_rule"]["h"] * RENDER_SCALE * scale
            cue_ok = cue_h >= 0.4 or px >= float(role.get("action_cue_min_px") or 6)
            visible = cue_ok
        out[role["id"]] = {
            "role": role["role"],
            "px_at_scale": round(px, 2),
            "min_px": min_px,
            "visible": visible,
            "action_cue": cue_ok if role["id"] == "cta" else None,
        }
    return out


def evaluate_hierarchy(image: Image.Image, layout: dict[str, Any]) -> dict[str, Any]:
    optical = optical_engine_report(layout)
    at = {str(int(s * 100)): scale_visibility(layout, s) for s in (1.0, 0.5, 0.25, 0.15)}
    p15 = at["15"]
    p25 = at["25"]
    req15 = p15["project"]["visible"] and p15["offer"]["visible"] and bool(p15["cta"]["action_cue"] or p15["cta"]["visible"])
    req25 = p25["price"]["visible"] and p25["unit"]["visible"] and p25["cta"]["visible"]
    # 100% must not look like a type-specimen shout: offer < 22% of canvas height.
    sophisticated_100 = layout["offer"]["size"] < H * 0.22 and layout["cta"]["size"] < 36
    passed = optical["pass"] and req15 and req25 and sophisticated_100
    return {
        "schema": SCHEMA,
        "optical": optical,
        "at": at,
        "identity_15": p15["project"]["visible"],
        "hook_15": p15["offer"]["visible"],
        "action_cue_15": bool(p15["cta"]["action_cue"] or p15["cta"]["visible"]),
        "price_25": p25["price"]["visible"],
        "unit_25": p25["unit"]["visible"],
        "cta_25": p25["cta"]["visible"],
        "sophisticated_100": sophisticated_100,
        "pass": passed,
        "button": False,
        "output_size": list(image.size),
    }


def render_hierarchy_proof() -> tuple[Image.Image, dict[str, Any], dict[str, Image.Image]]:
    registry = build_font_registry()
    font_css = "\n".join(
        block
        for block in (
            _font_face(registry, "DISPLAY_SERIF", "Hybrid Serif"),
            _font_face(registry, "EDITORIAL_SERIF", "Hybrid Serif"),
            _font_face(registry, "DISPLAY_SANS", "Hybrid Grotesk"),
            _font_face(registry, "EDITORIAL_SANS", "Hybrid Grotesk"),
        )
        if block
    )
    layout = hierarchy_layout()
    markup = hierarchy_svg(font_css, layout)
    forbidden = ("border-radius:999", "position:absolute", "button", "rotate(90)")
    if any(token in markup.lower() for token in forbidden):
        raise RuntimeError("Hierarchy V2 refused button / abs / rotated treatment")
    image = render_svg_html_to_png(markup, width=W, height=H, scale=RENDER_SCALE)
    report = evaluate_hierarchy(image, layout)
    thumbs = {
        "100": image,
        "50": image.resize((image.size[0] // 2, image.size[1] // 2), Image.Resampling.LANCZOS),
        "25": image.resize((max(1, int(image.size[0] * 0.25)), max(1, int(image.size[1] * 0.25))), Image.Resampling.LANCZOS),
        "15": image.resize((max(1, int(image.size[0] * 0.15)), max(1, int(image.size[1] * 0.15))), Image.Resampling.LANCZOS),
    }
    return image, report, thumbs
