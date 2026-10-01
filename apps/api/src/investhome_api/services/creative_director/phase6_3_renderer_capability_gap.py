"""Phase 6.3 — production renderer capability gap.

Diagnoses why GraphicDesignCompositorV4 cannot reproduce Concept 3 craft.
Selects one renderer architecture. Runs isolated micro-proofs.
Does not create a new Temple Master. GPT Image = 0.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    _vision,
    font_face_css,
    inline_logo_svg,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, cover_fit_canvas
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    analyze_concept3_pixels,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _pair, _score_board
from investhome_api.services.creative_director.phase6_2_real_photo_native import _HISTORY_KEYS as _H62
from investhome_api.services.creative_director.phase6_2_real_photo_native import _preserve as _preserve_62
from investhome_api.services.creative_director.phase6_3_scene_graph import (
    format_compatibility,
    proof_a_html,
    proof_b_html,
    proof_c_html,
    proof_d_html,
    proof_e_html,
    render_proof,
    revision_compatibility,
    scene_object_model,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_63 = "phase6_3_renderer_capability_gap"
SELECTED_RENDERER = "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
_HISTORY_KEYS = _H62 + (("real_photo_native_62_tests", "quality62"),)

PROOF_KEYS = ("CRAFT_FIDELITY", "DEPTH", "TYPOGRAPHIC_QUALITY", "GRAPHIC_PRECISION", "REFERENCE_BEHAVIOR_MATCH")
PROOF_RELEVANT = {
    "A": ("CRAFT_FIDELITY", "DEPTH", "GRAPHIC_PRECISION", "REFERENCE_BEHAVIOR_MATCH"),
    "B": ("CRAFT_FIDELITY", "GRAPHIC_PRECISION", "REFERENCE_BEHAVIOR_MATCH"),
    "C": ("CRAFT_FIDELITY", "TYPOGRAPHIC_QUALITY", "REFERENCE_BEHAVIOR_MATCH"),
    "D": ("CRAFT_FIDELITY", "DEPTH", "TYPOGRAPHIC_QUALITY", "GRAPHIC_PRECISION", "REFERENCE_BEHAVIOR_MATCH"),
    "E": ("CRAFT_FIDELITY", "TYPOGRAPHIC_QUALITY", "GRAPHIC_PRECISION", "REFERENCE_BEHAVIOR_MATCH"),
}

CAPABILITY_MAP = {
    "schema": "ProductionVisualCapabilityMapV1",
    "gold_standard": "Phase 6.0 Concept 3",
    "behaviors": {
        "PHOTO_TREATMENT": "Full-bleed photograph remains source pixels. Grade/vignette only. Architecture is never redrawn.",
        "GRAPHIC_FIELDS": "Left charcoal mass is a curved aperture: concave elliptical edge, not a rectangle, with photographic detail still perceptible inside the field.",
        "MASKING": "Field is a feathered alpha mask whose right boundary is a continuous curve sampled from an off-canvas ellipse.",
        "BLENDING": "Field uses multiply/darken over the photo so trees/street remain readable through charcoal.",
        "GRADIENTS": "Gold stroke is a metallic 3-stop gradient along the path, not a flat #C9A85C fill.",
        "CURVED_GEOMETRY": "Primary edge is one large-radius elliptical arc occupying most of the canvas height.",
        "VECTOR_DECORATION": "Radial tick sequence on the outer normal of the arc plus one precision node with a horizontal hairline.",
        "TYPOGRAPHIC_COMPOSITION": "Two-line campaign serif with optical tracking; %35 is the largest commercial numeral; price is second mass; labels are tracked sans.",
        "TYPE_IMAGE_INTERACTION": "Type sits inside the dark aperture, never on raw light stone. Contrast is a property of the field, not of local drop shadows.",
        "DEPTH": "At least two overlay densities (core + feather) plus the photo, so the aperture has thickness.",
        "OVERLAYS": "Stacked SVG groups: multiply charcoal, inner density, gold path, ticks, marker.",
        "TRANSPARENCY": "Field alpha ~0.78 multiply + 0.34 inner. Not an opaque sidebar.",
        "CLIPPING": "Field geometry is a closed SVG path; vectors can clip to the field if needed.",
        "COMPOSITING": "Scene graph rasterized once by Chromium. Objects remain addressable before flatten.",
        "LOGO_INTEGRATION": "Real SVG logo as a DOM node, gold-colored, opening the editorial column.",
        "OFFER_COMPOSITION": "Vertical commercial narrative with a gold rule as the shared graphic device.",
        "CTA_TREATMENT": "Hairline gold rectangle, tracked sans, no fill, no pill, no UI button chrome.",
        "NEGATIVE_SPACE_CONTROL": "Left breathing margin inside the field; right photograph stays open around the spire.",
        "CANVAS_LEVEL_ART_DIRECTION": "Whole canvas is one aperture relationship, not a classified 3-mode template.",
    },
}

V4_AUDIT = [
    {"capability": "PHOTO_TREATMENT", "concept3": "source photo full-bleed behind field", "v4": "PARTIAL", "impl": "cover crop + photographic grade", "failure": "cannot bind photo to a curved aperture relationship", "need": "photo as scene object under SVG mask"},
    {"capability": "GRAPHIC_FIELDS", "concept3": "concave charcoal aperture", "v4": "PARTIAL", "impl": "polyline L-mask + charcoal mix", "failure": "reads as a vertical sidebar; edge is a sampled column not an ellipse", "need": "closed SVG path + feather filter"},
    {"capability": "MASKING", "concept3": "soft elliptical alpha", "v4": "PARTIAL", "impl": "PIL GaussianBlur on a polygon mask", "failure": "blur fattens the edge instead of following the curve", "need": "SVG mask/filter along the path"},
    {"capability": "BLENDING", "concept3": "multiply charcoal over photo", "v4": "MISSING", "impl": "Image.composite to a mixed RGB", "failure": "photo is replaced, not multiplied, so depth dies", "need": "CSS/SVG mix-blend-mode"},
    {"capability": "GRADIENTS", "concept3": "metallic gold on stroke", "v4": "PARTIAL", "impl": "flat GOLD tuple", "failure": "arc looks printed, not inscribed", "need": "gradient-on-stroke"},
    {"capability": "CURVED_GEOMETRY", "concept3": "one dominant ellipse", "v4": "PARTIAL", "impl": "vertical polyline / ImageDraw arc", "failure": "polyline quantization + extra rings in 6.1", "need": "true SVG path / elliptical arc"},
    {"capability": "VECTOR_DECORATION", "concept3": "ticks + precision node", "v4": "PARTIAL", "impl": "1px lines on raster overlay", "failure": "ticks detach from the arc; node is a blob", "need": "vector ticks in the same path space"},
    {"capability": "TYPOGRAPHIC_COMPOSITION", "concept3": "campaign-scale OpenType serif", "v4": "PARTIAL", "impl": "PIL ImageDraw + tracking loop", "failure": "no kerning pairs, no optical size, letterspaces look mechanical", "need": "browser text engine + @font-face"},
    {"capability": "TYPE_IMAGE_INTERACTION", "concept3": "type lives in the aperture", "v4": "WRONG_ABSTRACTION", "impl": "draw text after flattening fielded RGB", "failure": "6.2 put ivory type on light stone", "need": "type as DOM over a live field"},
    {"capability": "DEPTH", "concept3": "layered multiply + feather", "v4": "MISSING", "impl": "single composite", "failure": "field is a stain, not an aperture", "need": "stacked blend groups"},
    {"capability": "OVERLAYS", "concept3": "ordered SVG groups", "v4": "PARTIAL", "impl": "one field then one vector overlay", "failure": "cannot restack without a new raster pass", "need": "z-ordered scene graph"},
    {"capability": "TRANSPARENCY", "concept3": "photo visible through charcoal", "v4": "PARTIAL", "impl": "Image.blend then mask", "failure": "either too opaque (sidebar) or too weak (6.2 C)", "need": "independent alpha + blend mode"},
    {"capability": "CLIPPING", "concept3": "arc clipped to field", "v4": "MISSING", "impl": "multiply vector alpha by dilated mask", "failure": "ticks leak onto architecture", "need": "clipPath"},
    {"capability": "COMPOSITING", "concept3": "non-destructive layers", "v4": "WRONG_ABSTRACTION", "impl": "flatten to RGB at every engine", "failure": "revision requires a full redraw of a baked image", "need": "edit the scene, then rasterize"},
    {"capability": "LOGO_INTEGRATION", "concept3": "real SVG in the column", "v4": "PARTIAL", "impl": "cairosvg/svglib raster paste", "failure": "logo becomes pixels; gold treatment is a fill hack", "need": "inline SVG node"},
    {"capability": "OFFER_COMPOSITION", "concept3": "one vertical commercial story", "v4": "PARTIAL", "impl": "CommercialOfferComposerV2 boxes", "failure": "scale ratios survive; material and alignment to the arc do not", "need": "CSS type + shared rule in the scene"},
    {"capability": "CTA_TREATMENT", "concept3": "hairline inscribed frame", "v4": "PARTIAL", "impl": "PIL rectangle or rule", "failure": "reads as a UI button or a caption", "need": "CSS border on a TEXT node"},
    {"capability": "NEGATIVE_SPACE_CONTROL", "concept3": "left margin is designed", "v4": "MISSING", "impl": "origin x=0.055 hardcoded", "failure": "no constraint that protects the aperture interior", "need": "group relationships in the scene graph"},
    {"capability": "CANVAS_LEVEL_ART_DIRECTION", "concept3": "one aperture idea", "v4": "WRONG_ABSTRACTION", "impl": "SKY_VEIL / GROUND_PLANE / CORNER_INGRESS classifier", "failure": "unknown modes fall back to SKY_VEIL", "need": "unclassified scene graph"},
]

RENDERER_COMPARISON = {
    "schema": "RendererArchitectureComparisonV1",
    "candidates": {
        "A_pillow_v4": {
            "name": "Current raster/Pillow compositor (V4)",
            "visual_sophistication": 4,
            "structured_editability": 7,
            "typography_quality": 5,
            "curved_geometry": 4,
            "masking": 5,
            "gradients": 3,
            "blend_modes": 2,
            "photo_treatment": 6,
            "responsive_format_adaptation": 5,
            "deterministic_rendering": 8,
            "revision_safety": 7,
            "performance": 8,
            "implementation_complexity": 3,
            "maintainability": 5,
            "already_in_repo": True,
            "verdict": "Keeps data. Loses craft. 6.1/6.1-R1/6.2 are the evidence.",
        },
        "B_svg_cairo": {
            "name": "SVG scene via CairoSVG",
            "visual_sophistication": 6,
            "structured_editability": 8,
            "typography_quality": 6,
            "curved_geometry": 8,
            "masking": 6,
            "gradients": 7,
            "blend_modes": 4,
            "photo_treatment": 6,
            "responsive_format_adaptation": 7,
            "deterministic_rendering": 7,
            "revision_safety": 8,
            "performance": 7,
            "implementation_complexity": 5,
            "maintainability": 7,
            "already_in_repo": True,
            "verdict": "Good paths. Weak CSS blend/feather and @font-face versus Chromium.",
        },
        "C_html_chromium": {
            "name": "HTML/CSS + Chromium (Playwright)",
            "visual_sophistication": 9,
            "structured_editability": 9,
            "typography_quality": 9,
            "curved_geometry": 9,
            "masking": 9,
            "gradients": 9,
            "blend_modes": 9,
            "photo_treatment": 8,
            "responsive_format_adaptation": 9,
            "deterministic_rendering": 8,
            "revision_safety": 8,
            "performance": 6,
            "implementation_complexity": 6,
            "maintainability": 8,
            "already_in_repo": True,
            "verdict": "Phase 5.3 already rasterizes design scenes this way. Best craft/editability overlap.",
        },
        "D_canvas_webgl": {
            "name": "Canvas / WebGL",
            "visual_sophistication": 8,
            "structured_editability": 6,
            "typography_quality": 6,
            "curved_geometry": 8,
            "masking": 8,
            "gradients": 8,
            "blend_modes": 8,
            "photo_treatment": 7,
            "responsive_format_adaptation": 7,
            "deterministic_rendering": 6,
            "revision_safety": 5,
            "performance": 8,
            "implementation_complexity": 8,
            "maintainability": 4,
            "already_in_repo": False,
            "verdict": "Not installed. Text quality worse than Chromium. New stack.",
        },
        "E_hybrid_scene_graph": {
            "name": "Hybrid vector + raster scene graph (SVG/HTML objects, Chromium raster)",
            "visual_sophistication": 9,
            "structured_editability": 9,
            "typography_quality": 9,
            "curved_geometry": 9,
            "masking": 9,
            "gradients": 9,
            "blend_modes": 9,
            "photo_treatment": 8,
            "responsive_format_adaptation": 9,
            "deterministic_rendering": 8,
            "revision_safety": 9,
            "performance": 6,
            "implementation_complexity": 6,
            "maintainability": 8,
            "already_in_repo": True,
            "verdict": "This is C plus an explicit object model. Selected.",
        },
        "F_other": {
            "name": "Skia / Sharp / Fabric / Konva / Pixi",
            "visual_sophistication": 8,
            "structured_editability": 7,
            "already_in_repo": False,
            "verdict": "None are production dependencies. Do not add for fame.",
        },
    },
    "selected": SELECTED_RENDERER,
    "selected_candidate": "E_hybrid_scene_graph",
    "why": (
        "Concept 3 craft is a curved masked aperture + metallic vector stroke + OpenType type "
        "sitting in that aperture. V4 flattens those into Pillow pixels. Chromium already exists "
        "in Phase 5.3 and can keep PHOTO/TEXT/LOGO/PATH as live objects while matching the medium "
        "that produced the gold-standard look (a designed scene, not a stamped template)."
    ),
}


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_62(blob)
    preserved["quality62"] = list(blob.get("real_photo_native_62_tests") or [])
    return preserved


def runtime_dependency_audit() -> dict[str, Any]:
    found: dict[str, bool] = {}
    for mod in ("PIL", "cairosvg", "playwright", "svglib", "reportlab"):
        try:
            __import__(mod if mod != "PIL" else "PIL")
            found[mod] = True
        except Exception:
            found[mod] = False
    chromium = False
    if found.get("playwright"):
        try:
            from playwright.sync_api import sync_playwright

            p = sync_playwright().start()
            b = p.chromium.launch(headless=True)
            chromium = True
            b.close()
            p.stop()
        except Exception:
            chromium = False
    return {
        "schema": "RuntimeDependencyAuditV1",
        "installed": found,
        "chromium_launchable": chromium,
        "skia": False,
        "sharp": False,
        "fabric": False,
        "konva": False,
        "pixi": False,
        "cairo_native_lib": True,
        "new_packages_added_this_phase": [],
        "note": "Playwright Chromium is used by Phase 5.3 render_html_to_png. Pillow is V4. cairosvg is logo rasterization.",
    }


def request_proof_critic(concept: Image.Image, proofs: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            "Gold standard is APPROVED Concept 3 (image 1). Images 2-6 are ISOLATED renderer micro-proofs, "
            "not full ads. Score 0-10 each proof for: " + ", ".join(PROOF_KEYS) + ". "
            "A=dark curved aperture on real photo, no type. B=gold arc+ticks+marker on charcoal. "
            "C=typographic mass on charcoal. D=photo+aperture+headline+offer. E=real logo+CTA+closure. "
            "Ask whether the RENDERER reproduces Concept 3's rendering behavior for that slice. "
            "Do not penalize missing commercial content in A/B/E. Do not inflate. "
            "JSON {A:{scores:{...}},B:{...},C:{...},D:{...},E:{...},notes}."
        ),
        _text("IMAGE 1 — CONCEPT 3 GOLD STANDARD"),
        _img(concept, quality=84),
        _text("IMAGE 2 — PROOF A DARK APERTURE"),
        _img(proofs["A"], quality=84),
        _text("IMAGE 3 — PROOF B ARC SYSTEM"),
        _img(proofs["B"], quality=84),
        _text("IMAGE 4 — PROOF C TYPOGRAPHIC MASS"),
        _img(proofs["C"], quality=84),
        _text("IMAGE 5 — PROOF D PHOTO+TYPE+FIELD"),
        _img(proofs["D"], quality=84),
        _text("IMAGE 6 — PROOF E BRAND+CTA+CLOSURE"),
        _img(proofs["E"], quality=84),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Renderer critic. Score isolated capabilities against Concept 3. JSON only. Do not redesign."},
                {"role": "user", "content": content},
            ],
        }
    )
    out: dict[str, Any] = {}
    for key in ("A", "B", "C", "D", "E"):
        block = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
        raw = block.get("scores") if isinstance(block.get("scores"), dict) else block
        scores = {k: round(_num(raw.get(k), 0), 2) for k in PROOF_KEYS}
        relevant = list(PROOF_RELEVANT[key])
        failed = [k for k in relevant if scores.get(k, 0) < 9]
        out[key] = {
            "scores": scores,
            "relevant": relevant,
            "failed": failed,
            "pass": not failed,
            "notes": str(block.get("notes") or parsed.get("notes") or ""),
        }
    return {"schema": "MicroProofScoresV1", "proofs": out, "all_pass": all(v["pass"] for v in out.values())}, calls


def _matrix_board(title: str, rows: list[dict[str, Any]]) -> Image.Image:
    image = Image.new("RGB", (1920, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(image)
    draw.text((36, 20), title, font=_font(20), fill=(201, 168, 92))
    y = 64
    draw.text((36, y), "capability".ljust(28) + "V4".ljust(18) + "failure", font=_font(14), fill=(180, 176, 168))
    y += 28
    for row in rows:
        line = f"{row['capability'][:26]:<28}{row['v4']:<18}{str(row['failure'])[:88]}"
        draw.text((36, y), line, font=_font(14), fill=(226, 222, 214))
        y += 26
        if y > 1620:
            break
    return image


def _compare_board(comp: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (1920, 1400), (12, 14, 20))
    draw = ImageDraw.Draw(image)
    draw.text((36, 20), "03  RENDERER ARCHITECTURE COMPARISON", font=_font(20), fill=(201, 168, 92))
    y = 64
    for key, item in (comp.get("candidates") or {}).items():
        mark = "  SELECTED" if key == comp.get("selected_candidate") else ""
        draw.text((36, y), f"{item.get('name')}{mark}", font=_font(16), fill=(201, 168, 92) if mark else (226, 222, 214))
        y += 26
        draw.text((56, y), str(item.get("verdict") or "")[:110], font=_font(14), fill=(180, 176, 168))
        y += 36
    draw.text((36, y + 12), str(comp.get("why") or "")[:220], font=_font(14), fill=(226, 222, 214))
    return image


def _annotate_concept(concept: Image.Image) -> Image.Image:
    image = concept.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 36), fill=(12, 14, 20))
    draw.text((16, 8), "01  CONCEPT 3 CAPABILITY MAP  —  gold standard, not a layout to copy", font=_font(16), fill=(201, 168, 92))
    labels = [
        (40, 80, "CHARCOAL APERTURE"),
        (40, 420, "TYPE IN FIELD"),
        (40, 700, "GOLD ARC + TICKS"),
        (int(image.width * 0.58), 80, "PHOTO APERTURE"),
        (int(image.width * 0.22), int(image.height * 0.90), "EDITORIAL CLOSURE"),
    ]
    for x, y, label in labels:
        draw.text((x, y), label, font=_font(14), fill=(201, 168, 92))
    return image


def generate_phase6_3_capability_gap(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    vision_calls = 0
    _ = user

    concept = load_approved_concept3(db)
    if concept.size != CANVAS_4X5:
        concept = ImageOps.fit(concept, CANVAS_4X5, method=Image.Resampling.LANCZOS)
    source = load_day007(db)
    photo, _transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.68, 0.20))
    structure = analyze_concept3_pixels(concept)
    fonts = build_font_registry()
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)))
    photo_uri = _jpeg_data_uri(photo, quality=92)
    deps = runtime_dependency_audit()

    proofs = {
        "A": render_proof(proof_a_html(photo_uri, structure, font_css)),
        "B": render_proof(proof_b_html(structure, font_css)),
        "C": render_proof(proof_c_html(font_css)),
        "D": render_proof(proof_d_html(photo_uri, structure, font_css)),
        "E": render_proof(proof_e_html(logo_markup, font_css)),
    }
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3 forbids GPT Image production calls")

    scores, n = request_proof_critic(concept, proofs)
    vision_calls += n
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3 forbids GPT Image production calls")

    objects = scene_object_model()
    rev = revision_compatibility()
    fmt = format_compatibility()
    ready = bool(scores.get("all_pass")) and bool(deps.get("chromium_launchable"))
    status = "RENDERER_ARCHITECTURE_READY" if ready else "RENDERER_ARCHITECTURE_NOT_READY"
    blocker = None if ready else "Micro-proofs did not all reach >=9 on relevant capabilities" if not scores.get("all_pass") else "Chromium is not launchable"
    v4_counts = {
        "FULL": sum(1 for r in V4_AUDIT if r["v4"] == "FULL"),
        "PARTIAL": sum(1 for r in V4_AUDIT if r["v4"] == "PARTIAL"),
        "MISSING": sum(1 for r in V4_AUDIT if r["v4"] == "MISSING"),
        "WRONG_ABSTRACTION": sum(1 for r in V4_AUDIT if r["v4"] == "WRONG_ABSTRACTION"),
    }
    critic_rows = []
    for key in ("A", "B", "C", "D", "E"):
        item = (scores.get("proofs") or {}).get(key) or {}
        critic_rows.append(f"PROOF {key}  pass={item.get('pass')}  failed={item.get('failed')}")
        critic_rows.extend([f"  {k}: {v}" for k, v in (item.get("scores") or {}).items()])

    images = {
        "map": _annotate_concept(concept),
        "matrix": _matrix_board("02  V4 CAPABILITY MATRIX  —  FULL / PARTIAL / MISSING / WRONG_ABSTRACTION", V4_AUDIT),
        "compare": _compare_board(RENDERER_COMPARISON),
        "A": proofs["A"],
        "B": proofs["B"],
        "C": proofs["C"],
        "D": proofs["D"],
        "E": proofs["E"],
        "critic": _text_board("09  MICRO-PROOF CRITIC  —  Concept 3 is the reference", critic_rows, size=(1280, 1700)),
        "objects": _text_board("10  STRUCTURED OBJECT MODEL", [f"{o['id']}  {o['kind']}" for o in objects["objects"]] + [f"invariants {objects['invariants']}"]),
        "revision": _text_board("11  REVISION COMPATIBILITY  —  architectural, not executed", [f"{k}: {v.get('status') if isinstance(v, dict) else v}" for k, v in rev.items() if k != "schema"]),
        "format": _text_board("12  FORMAT COMPATIBILITY  —  not implemented", [f"{k}: {v}" for k, v in (fmt.get("formats") or {}).items()] + [f"status {fmt.get('status')}"]),
        "decision": _text_board(
            "13  FINAL ARCHITECTURE DECISION",
            [
                f"STATUS {status}",
                f"SELECTED {SELECTED_RENDERER}",
                f"NEW MASTER CREATED NO",
                f"GPT IMAGE {provider_call_count()}",
                f"BLOCKER {blocker}",
                RENDERER_COMPARISON["why"],
            ],
            size=(1600, 1100),
        ),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_63,
        "created_at": _now(),
        "status": status,
        "current_bottleneck": "PRODUCTION_RENDERING_CAPABILITY",
        "gold_standard": CONCEPT3_ASSET_ID,
        "capability_map": CAPABILITY_MAP,
        "v4_audit": V4_AUDIT,
        "v4_counts": v4_counts,
        "renderer_comparison": RENDERER_COMPARISON,
        "selected_renderer": SELECTED_RENDERER,
        "runtime_dependencies": deps,
        "new_dependencies_required": False,
        "micro_proof_scores": scores,
        "structured_object_model": objects,
        "revision_compatibility": rev,
        "format_compatibility": fmt,
        "blocker": blocker,
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "new_master_created": False,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "day007_asset_id": DAY007_ASSET_ID,
        "language": language,
        "next_decision": "STOP",
    }
    tests = list(blob.get("renderer_capability_63_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["renderer_capability_63_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    blob["new_premium_master_58_tests"] = preserved.get("quality58")
    blob["ai_draft_structured_master_59_tests"] = preserved.get("quality59")
    blob["pure_creative_director_60_tests"] = preserved.get("quality60")
    blob["concept3_production_master_61_tests"] = preserved.get("quality61")
    blob["concept3_r1_61_tests"] = preserved.get("quality61r1")
    blob["real_photo_native_62_tests"] = preserved.get("quality62")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.3 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
