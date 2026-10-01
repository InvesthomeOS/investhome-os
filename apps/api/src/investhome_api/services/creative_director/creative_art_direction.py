"""Phase 5.1C — CreativeArtDirectionPlan.

AI decides the advertisement. The compositor only executes.
Scene analysis is image-specific. No template menu.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

import httpx
from PIL import Image, ImageFilter

from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.editorial_compose import (
    boxes_overlap,
    contrast_ratio,
    inspect_font_inventory,
    overlap_area,
    region_mean_rgb,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL
from investhome_api.config.settings import get_settings

logger = logging.getLogger(__name__)

PLAN_SCHEMA_VERSION = "creative_art_direction_v1"


@dataclass
class NormBox:
    x: float
    y: float
    w: float
    h: float
    name: str = ""

    def to_px(self, canvas: tuple[int, int]) -> tuple[int, int, int, int]:
        cw, ch = canvas
        x0 = int(round(self.x * cw))
        y0 = int(round(self.y * ch))
        x1 = int(round((self.x + self.w) * cw))
        y1 = int(round((self.y + self.h) * ch))
        return x0, y0, x1, y1

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "x": self.x, "y": self.y, "w": self.w, "h": self.h}


def _box(data: Any, name: str = "") -> NormBox | None:
    if not isinstance(data, dict):
        return None
    try:
        x = float(data.get("x", 0))
        y = float(data.get("y", 0))
        w = float(data.get("w", data.get("width", 0)))
        h = float(data.get("h", data.get("height", 0)))
    except (TypeError, ValueError):
        return None
    if w <= 0.02 or h <= 0.02:
        return None
    return NormBox(
        x=max(0.0, min(0.95, x)),
        y=max(0.0, min(0.95, y)),
        w=max(0.04, min(0.9, w)),
        h=max(0.04, min(0.9, h)),
        name=str(data.get("name") or name),
    )


@dataclass
class SceneAnalysis:
    focal_point: str = ""
    spire: NormBox | None = None
    building_mass: NormBox | None = None
    sky: NormBox | None = None
    quiet_regions: list[NormBox] = field(default_factory=list)
    unsafe_typography: list[NormBox] = field(default_factory=list)
    logo_safe: NormBox | None = None
    cta_safe: NormBox | None = None
    light_areas: list[NormBox] = field(default_factory=list)
    dark_areas: list[NormBox] = field(default_factory=list)
    mode: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "focal_point": self.focal_point,
            "spire": self.spire.to_dict() if self.spire else None,
            "building_mass": self.building_mass.to_dict() if self.building_mass else None,
            "sky": self.sky.to_dict() if self.sky else None,
            "quiet_regions": [b.to_dict() for b in self.quiet_regions],
            "unsafe_typography": [b.to_dict() for b in self.unsafe_typography],
            "logo_safe": self.logo_safe.to_dict() if self.logo_safe else None,
            "cta_safe": self.cta_safe.to_dict() if self.cta_safe else None,
            "light_areas": [b.to_dict() for b in self.light_areas],
            "dark_areas": [b.to_dict() for b in self.dark_areas],
            "mode": self.mode,
        }


@dataclass
class CreativeArtDirectionPlan:
    plan_id: str
    schema: str = PLAN_SCHEMA_VERSION
    creative_concept: str = ""
    visual_story: str = ""
    photograph_role: str = "immutable_project_foundation"
    focal_point: str = ""
    protected_architecture: str = ""
    headline_strategy: str = ""
    headline_relationship_to_architecture: str = ""
    commercial_information_strategy: str = ""
    price_hierarchy: str = ""
    advantage_hierarchy: str = ""
    unit_hierarchy: str = ""
    logo_strategy: str = ""
    cta_strategy: str = ""
    negative_space_strategy: str = ""
    contrast_strategy: str = ""
    graphic_language: str = ""
    color_strategy: str = ""
    depth_strategy: str = ""
    photographic_grade: dict[str, Any] = field(default_factory=dict)
    readability_strategy: str = ""
    composition_balance: str = ""
    luxury_quality_rationale: str = ""
    type_column: str = "left"
    surfaces: list[dict[str, Any]] = field(default_factory=list)
    placements: dict[str, Any] = field(default_factory=dict)
    scene: dict[str, Any] = field(default_factory=dict)
    template_id: str | None = None
    created_before_render: bool = True
    mode: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


_GRADE_PRESETS = {
    "warm_editorial": {"warmth": 0.18, "contrast": 1.14, "brightness": 0.96, "vignette": 0.16},
    "dark_premium": {"warmth": 0.1, "contrast": 1.16, "brightness": 0.88, "vignette": 0.22},
    "cool_architectural": {"warmth": -0.08, "contrast": 1.1, "brightness": 1.0, "vignette": 0.12},
}


def analyze_scene_heuristic(image: Image.Image) -> SceneAnalysis:
    """Image-specific mass/sky/quiet detection. No Temple-hardcoded coordinates."""
    im = image.convert("RGB")
    w, h = im.size
    small = im.resize((48, 60), Image.Resampling.BOX)
    gray = small.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_bytes = edges.tobytes()
    lum_bytes = gray.tobytes()
    sw, sh = small.size
    col_energy = [0.0] * sw
    for y in range(int(sh * 0.62)):
        for x in range(2, sw - 2):
            col_energy[x] += edge_bytes[y * sw + x]
    interior = range(2, sw - 2)
    peak_x = max(interior, key=lambda x: col_energy[x])
    peak = col_energy[peak_x] or 1.0
    left = peak_x
    right = peak_x
    while left > 1 and col_energy[left] > peak * 0.42:
        left -= 1
    while right < sw - 2 and col_energy[right] > peak * 0.42:
        right += 1
    spire = NormBox(
        x=left / sw,
        y=0.02,
        w=max(0.08, (right - left + 2) / sw),
        h=0.58,
        name="spire",
    )
    mass = NormBox(
        x=max(0.08, spire.x - 0.08),
        y=0.28,
        w=min(0.7, spire.w + 0.28),
        h=0.58,
        name="building_mass",
    )
    sky = NormBox(x=0.0, y=0.0, w=1.0, h=0.34, name="sky")
    spire_cx = spire.x + spire.w / 2
    if spire_cx >= 0.5:
        quiet = NormBox(x=0.045, y=0.06, w=0.34, h=0.34, name="upper_left_sky")
        logo = NormBox(x=0.05, y=0.045, w=0.30, h=0.11, name="logo_safe")
        cta = NormBox(x=0.05, y=0.78, w=0.36, h=0.10, name="cta_safe")
        column = "left"
    else:
        quiet = NormBox(x=0.58, y=0.06, w=0.36, h=0.34, name="upper_right_sky")
        logo = NormBox(x=0.62, y=0.045, w=0.30, h=0.11, name="logo_safe")
        cta = NormBox(x=0.58, y=0.78, w=0.36, h=0.10, name="cta_safe")
        column = "right"
    # Dark lower band for CTA grounding.
    dark = NormBox(x=quiet.x, y=0.72, w=quiet.w, h=0.22, name="lower_dark")
    _ = column
    _ = lum_bytes
    return SceneAnalysis(
        focal_point="primary vertical architectural landmark",
        spire=spire,
        building_mass=mass,
        sky=sky,
        quiet_regions=[quiet],
        unsafe_typography=[spire, mass],
        logo_safe=logo,
        cta_safe=cta,
        light_areas=[sky, quiet],
        dark_areas=[dark],
        mode="heuristic",
    )


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def request_creative_art_direction(
    foundation: Image.Image,
    *,
    facts: dict[str, str],
    retry_feedback: str | None = None,
) -> tuple[SceneAnalysis, CreativeArtDirectionPlan, int]:
    """One vision call: analyze THIS photograph, then write the semantic plan."""
    heuristic = analyze_scene_heuristic(foundation)
    api_key = openai_api_key()
    if not api_key:
        return heuristic, plan_from_scene(heuristic, facts=facts, mode="heuristic"), 0
    jpeg = io.BytesIO()
    foundation.convert("RGB").save(jpeg, format="JPEG", quality=88)
    b64 = base64.b64encode(jpeg.getvalue()).decode("ascii")
    retry = f"\nPREVIOUS PLAN FAILED QUALITY GATE:\n{retry_feedback}\nRevise the design. Do not move type 30px — change the strategy.\n" if retry_feedback else ""
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the creative director for a luxury real-estate Instagram 4:5 advertisement. "
                    "The photograph is immutable architecture. You design around it. You do not redraw it. "
                    "Do not choose a template. Respond to THIS image. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this 4:5 crop of the approved project photograph.\n"
                            "Required copy (do not change facts):\n"
                            f"HEADLINE {facts.get('headline')}\n"
                            f"UNIT {facts.get('unit')} {facts.get('unit_label')}\n"
                            f"PRICE {facts.get('list_price')}\n"
                            f"ADVANTAGE {facts.get('discount')} {facts.get('discount_label')}\n"
                            f"CTA {facts.get('cta')}\n"
                            "Boxes are normalized 0-1: {x,y,w,h}.\n"
                            "Protect the spire. Headline must not run through it.\n"
                            "Price is the commercial anchor. %35 must be immediately readable. "
                            "2+1 visible but quieter. Logo visible. CTA editorial, not a dashboard button.\n"
                            "Surfaces may include feathered_gradient, local_blur, local_tonal, logo_ground, rule. "
                            "No giant opaque panel, no KPI cards, no template ids.\n"
                            f"{retry}\n"
                            "JSON: {\n"
                            '  "scene": {"focal_point": str, "spire": box, "building_mass": box, "sky": box,\n'
                            '            "quiet_regions": [box+name], "unsafe_typography": [box],\n'
                            '            "logo_safe": box, "cta_safe": box},\n'
                            '  "art_direction": {\n'
                            '    "creative_concept": str, "visual_story": str, "focal_point": str,\n'
                            '    "protected_architecture": str, "headline_strategy": str,\n'
                            '    "headline_relationship_to_architecture": str,\n'
                            '    "commercial_information_strategy": str, "price_hierarchy": str,\n'
                            '    "advantage_hierarchy": str, "unit_hierarchy": str, "logo_strategy": str,\n'
                            '    "cta_strategy": str, "negative_space_strategy": str, "contrast_strategy": str,\n'
                            '    "graphic_language": str, "color_strategy": str, "depth_strategy": str,\n'
                            '    "photographic_grade": "warm_editorial"|"dark_premium"|"cool_architectural",\n'
                            '    "readability_strategy": str, "composition_balance": str,\n'
                            '    "luxury_quality_rationale": str, "type_column": "left"|"right"\n'
                            "  },\n"
                            '  "surfaces": [{"kind": str, "side": str, "color": "#hex", "width_frac": float,\n'
                            '               "max_alpha": float, "feather": float, "region": str}],\n'
                            '  "placements": {"logo": box, "headline": box, "commercial": box, "cta": box}\n'
                            "}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ],
            },
        ],
    }
    settings = get_settings()
    url = f"{resolve_base_url(settings).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        if not isinstance(parsed, dict):
            raise ValueError("art direction JSON missing")
        scene = scene_from_payload(parsed.get("scene") or {}, fallback=heuristic)
        scene.mode = "vision"
        plan = plan_from_payload(parsed, scene=scene, facts=facts, mode="vision")
        return scene, plan, 1
    except Exception:
        logger.info("creative art direction vision failed; using image-specific heuristic", exc_info=True)
        return heuristic, plan_from_scene(heuristic, facts=facts, mode="heuristic"), 0


def scene_from_payload(raw: dict[str, Any], *, fallback: SceneAnalysis) -> SceneAnalysis:
    scene = SceneAnalysis(
        focal_point=str(raw.get("focal_point") or fallback.focal_point),
        spire=_box(raw.get("spire"), "spire") or fallback.spire,
        building_mass=_box(raw.get("building_mass"), "building_mass") or fallback.building_mass,
        sky=_box(raw.get("sky"), "sky") or fallback.sky,
        quiet_regions=[b for b in (_box(x) for x in (raw.get("quiet_regions") or [])) if b] or fallback.quiet_regions,
        unsafe_typography=[b for b in (_box(x) for x in (raw.get("unsafe_typography") or [])) if b] or fallback.unsafe_typography,
        logo_safe=_box(raw.get("logo_safe"), "logo_safe") or fallback.logo_safe,
        cta_safe=_box(raw.get("cta_safe"), "cta_safe") or fallback.cta_safe,
        mode="vision",
    )
    if scene.spire and scene.spire not in scene.unsafe_typography:
        scene.unsafe_typography = [scene.spire, *scene.unsafe_typography]
    if scene.spire:
        scene.spire = NormBox(
            x=max(0.0, scene.spire.x - 0.04),
            y=max(0.0, scene.spire.y - 0.03),
            w=min(0.55, scene.spire.w + 0.08),
            h=min(0.72, scene.spire.h + 0.06),
            name="spire",
        )
    return scene


def plan_from_scene(
    scene: SceneAnalysis,
    *,
    facts: dict[str, str],
    mode: str,
) -> CreativeArtDirectionPlan:
    quiet = scene.quiet_regions[0] if scene.quiet_regions else NormBox(0.05, 0.08, 0.36, 0.32, "upper_left_sky")
    column = "left" if quiet.x < 0.45 else "right"
    side = column
    logo = scene.logo_safe or NormBox(quiet.x, 0.045, min(0.32, quiet.w), 0.11, "logo")
    headline = NormBox(quiet.x, 0.16, min(0.40, quiet.w + 0.04), 0.22, "headline")
    commercial = NormBox(quiet.x, 0.42, min(0.38, quiet.w + 0.02), 0.22, "commercial")
    cta = scene.cta_safe or NormBox(quiet.x, 0.80, 0.34, 0.08, "cta")
    # Keep headline off the spire by shrinking width if needed.
    if scene.spire and headline.x < scene.spire.x < headline.x + headline.w:
        headline.w = max(0.22, scene.spire.x - headline.x - 0.03)
    return CreativeArtDirectionPlan(
        plan_id=str(uuid4()),
        creative_concept="Editorial sky-and-shadow campaign: architecture as hero, type as crafted overlay in true negative space.",
        visual_story="The photograph carries the project. Typography occupies quiet sky and a grounded lower field so the spire remains the landmark.",
        photograph_role="immutable_project_foundation",
        focal_point=scene.focal_point,
        protected_architecture="Spire and primary mass are landmarks. No display type through the tower.",
        headline_strategy="Two-line display: ALIRKEN then KAZAN with contrast and tracking. Sits in quiet sky, stops before the spire.",
        headline_relationship_to_architecture="Headline flanks the landmark; it does not bisect it.",
        commercial_information_strategy="Stacked editorial facts with scale hierarchy, not equal KPI chips.",
        price_hierarchy="675.000 USD is the commercial anchor — largest supporting type.",
        advantage_hierarchy="%35 LANSMAN AVANTAJI is a gold emphasis line under price.",
        unit_hierarchy="2+1 DAİRE is quiet, tracked, above the price.",
        logo_strategy="Real SVG lockup, generously scaled, with a faint local ground if sky contrast is weak.",
        cta_strategy="Editorial outline label over the darker lower field. Not a filled dashboard button.",
        negative_space_strategy="Use existing sky and a dissolving edge field. Do not invent a card.",
        contrast_strategy="Ivory/gold type on a feathered dusk field; dark type only on light sky if contrast holds.",
        graphic_language="Feathered tonal dissolve, fine gold rule, typographic grouping. No panels.",
        color_strategy="Warm stone photograph, ivory type, Temple gold emphasis, deep ink for display on light sky.",
        depth_strategy="Local blur behind the commercial group only, so facts sit in atmosphere not on raw pixels.",
        photographic_grade=dict(_GRADE_PRESETS["warm_editorial"]),
        readability_strategy="Soft left/right dissolve + local blur + logo ground. Recolor if contrast fails.",
        composition_balance="Asymmetric type column opposite or beside the protected landmark.",
        luxury_quality_rationale="The building remains photographic. Design work is hierarchy, atmosphere, and restraint.",
        type_column=side,
        surfaces=[
            {
                "kind": "feathered_gradient",
                "side": side,
                "color": "#10141C",
                "width_frac": 0.42,
                "max_alpha": 0.36,
                "feather": 0.7,
            },
            {"kind": "local_blur", "region": "commercial", "radius": 9, "strength": 0.38, "feather": 0.6},
            {"kind": "logo_ground", "region": "logo", "color": "#F4EFE6", "max_alpha": 0.22},
            {"kind": "rule", "region": "commercial", "color": "#C4A35A", "width": 1},
        ],
        placements={
            "logo": logo.to_dict(),
            "headline": headline.to_dict(),
            "commercial": commercial.to_dict(),
            "cta": cta.to_dict(),
        },
        scene=scene.to_dict(),
        template_id=None,
        created_before_render=True,
        mode=mode,
    )


def plan_from_payload(
    parsed: dict[str, Any],
    *,
    scene: SceneAnalysis,
    facts: dict[str, str],
    mode: str,
) -> CreativeArtDirectionPlan:
    base = plan_from_scene(scene, facts=facts, mode=mode)
    art = dict(parsed.get("art_direction") or {})
    grade_key = str(art.get("photographic_grade") or "warm_editorial")
    grade = dict(_GRADE_PRESETS.get(grade_key) or _GRADE_PRESETS["warm_editorial"])
    placements = dict(parsed.get("placements") or {})
    merged_place = dict(base.placements)
    for key in ("logo", "headline", "commercial", "cta"):
        box = _box(placements.get(key), key)
        if box:
            merged_place[key] = box.to_dict()
    surfaces = list(parsed.get("surfaces") or [])
    has_column_field = any(
        str(s.get("kind")) == "feathered_gradient"
        and str(s.get("side") or "") in {"left", "right"}
        and float(s.get("width_frac") or 0) >= 0.28
        and float(s.get("max_alpha") or 0) >= 0.2
        for s in surfaces
        if isinstance(s, dict)
    )
    if not has_column_field:
        surfaces = list(base.surfaces) + [s for s in surfaces if isinstance(s, dict) and str(s.get("kind")) != "feathered_gradient"]
    column = str(art.get("type_column") or base.type_column)
    if column not in {"left", "right"}:
        column = base.type_column
    for key, value in art.items():
        if key == "photographic_grade":
            continue
        if hasattr(base, key) and isinstance(value, str) and value.strip():
            setattr(base, key, value.strip())
    base.photographic_grade = grade
    base.placements = merged_place
    base.surfaces = surfaces
    base.type_column = column
    base.scene = scene.to_dict()
    base.mode = mode
    base.template_id = None
    base.created_before_render = True
    return base


def placement_box(plan: CreativeArtDirectionPlan, key: str, canvas: tuple[int, int]) -> tuple[int, int, int, int]:
    raw = dict(plan.placements.get(key) or {})
    box = _box(raw, key)
    if box is None:
        defaults = {
            "logo": NormBox(0.05, 0.05, 0.3, 0.11, "logo"),
            "headline": NormBox(0.05, 0.16, 0.38, 0.22, "headline"),
            "commercial": NormBox(0.05, 0.42, 0.36, 0.22, "commercial"),
            "cta": NormBox(0.05, 0.80, 0.34, 0.08, "cta"),
        }
        box = defaults[key]
    return box.to_px(canvas)


def protect_from_spire(
    box: tuple[int, int, int, int],
    scene: SceneAnalysis,
    canvas: tuple[int, int],
    *,
    margin: int = 28,
) -> tuple[int, int, int, int]:
    if scene.spire is None:
        return box
    spire = scene.spire.to_px(canvas)
    x0, y0, x1, y1 = box
    if not boxes_overlap(box, spire, margin=margin):
        return box
    # Shrink from the side that intersects the landmark.
    if x1 > spire[0] and x0 < spire[0]:
        x1 = max(x0 + 80, spire[0] - margin)
    elif x0 < spire[2] and x1 > spire[2]:
        x0 = min(x1 - 80, spire[2] + margin)
    else:
        # Move the box to the quiet side of the spire.
        cw, _ = canvas
        if (spire[0] + spire[2]) / 2 > cw / 2:
            width = x1 - x0
            x0, x1 = 48, 48 + width
        else:
            width = x1 - x0
            x1 = cw - 48
            x0 = x1 - width
    return x0, y0, x1, y1


def quality_gate(
    *,
    image: Image.Image,
    foundation: Image.Image,
    plan: CreativeArtDirectionPlan,
    scene: SceneAnalysis,
    boxes: dict[str, tuple[int, int, int, int]],
    logo_meta: dict[str, Any],
    facts: dict[str, str],
    panel_coverage: float,
) -> dict[str, Any]:
    cw, ch = image.size
    failures: list[str] = []
    headline = boxes.get("headline") or (0, 0, 1, 1)
    spire_px = scene.spire.to_px((cw, ch)) if scene.spire else None
    collide = False
    if spire_px:
        area = overlap_area(headline, spire_px)
        collide = area > 0.08 * max(1, (headline[2] - headline[0]) * (headline[3] - headline[1]))
        if collide:
            failures.append("headline_collides_with_spire")
    for key, minimum in (("headline", 2.4), ("commercial", 2.6), ("cta", 2.8), ("logo", 1.6)):
        box = boxes.get(key)
        if not box:
            failures.append(f"missing_{key}")
            continue
        mean = region_mean_rgb(image, box)
        # Sample likely type color: gold or ivory vs ink.
        gold = contrast_ratio(mean, (196, 163, 90))
        ivory = contrast_ratio(mean, (244, 239, 230))
        ink = contrast_ratio(mean, (22, 28, 40))
        best = max(gold, ivory, ink)
        if best < minimum:
            failures.append(f"weak_contrast_{key}:{best:.2f}")
    if not logo_meta.get("placed"):
        failures.append("logo_not_placed")
    elif int(logo_meta.get("width") or 0) < int(cw * 0.18):
        failures.append("logo_too_small")
    if panel_coverage > 0.42:
        failures.append(f"giant_panel:{panel_coverage:.2f}")
    for key, box in boxes.items():
        if box[0] < -4 or box[1] < -4 or box[2] > cw + 4 or box[3] > ch + 4:
            failures.append(f"outside_canvas_{key}")
        if box[2] - box[0] < 24 or box[3] - box[1] < 16:
            failures.append(f"clipped_{key}")
    if plan.template_id:
        failures.append("template_menu_used")
    # Hierarchy: commercial box should be substantial; headline taller than unit line conceptually.
    hb = boxes.get("headline")
    cb = boxes.get("commercial")
    if hb and cb and (hb[3] - hb[1]) < 70:
        failures.append("headline_too_small")
    if cb and (cb[3] - cb[1]) < 70:
        failures.append("commercial_too_small")
    status = "fail" if failures else "pass"
    return {
        "status": status,
        "failures": failures,
        "headline_spire_collision": collide,
        "panel_coverage": round(panel_coverage, 4),
        "logo_placed": bool(logo_meta.get("placed")),
        "logo_size": [logo_meta.get("width"), logo_meta.get("height")],
        "facts": list(facts.values()),
        "created_before_render": plan.created_before_render,
        "template_id": plan.template_id,
    }
