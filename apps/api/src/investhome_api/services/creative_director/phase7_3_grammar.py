"""Phase 7.3 — ReferenceCampaignGrammarV1 from Grade-A pixels. Relationships, not coordinates."""

from __future__ import annotations

from typing import Any

from PIL import Image

from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES, _img, _num, _text
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME, WRONG_PREFIX_NAMES
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase7_2_photo_object import _box, clamp_photo_mass
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

GRAMMAR_FIELDS = (
    "COMPOSITIONAL_GRAVITY",
    "PHOTO_ROLE",
    "PHOTO_GEOMETRY",
    "PHOTO_TO_GRAPHIC_RELATIONSHIP",
    "HEADLINE_GEOMETRY",
    "TYPOGRAPHIC_SCALE_CONTRAST",
    "COMMERCIAL_INFORMATION_HIERARCHY",
    "BRAND_PLACEMENT_LOGIC",
    "CTA_BEHAVIOR",
    "NEGATIVE_SPACE_STRUCTURE",
    "GRAPHIC_MOTIFS",
    "DEPTH_METHOD",
    "EDGE_BEHAVIOR",
    "READING_FLOW",
    "VISUAL_TENSION",
    "CANVAS_CLOSURE",
    "PREMIUM_CRAFT_SIGNATURE",
)

SUITABILITY_KEYS = (
    "architectural_focal_compatibility",
    "available_negative_space",
    "crop_compatibility",
    "visual_gravity",
    "commercial_content_capacity",
    "brand_capacity",
    "photo_prominence",
    "campaign_drama",
)

FIDELITY_KEYS = (
    "COMPOSITION_GRAMMAR_TRANSFER",
    "VISUAL_GRAVITY_TRANSFER",
    "TYPOGRAPHIC_HIERARCHY_TRANSFER",
    "PHOTO_GRAPHIC_RELATIONSHIP_TRANSFER",
    "NEGATIVE_SPACE_LOGIC_TRANSFER",
    "COMMERCIAL_HIERARCHY_TRANSFER",
    "DEPTH_BEHAVIOR_TRANSFER",
    "CRAFT_SOPHISTICATION_TRANSFER",
)

FORBIDDEN_SIMPLIFICATIONS = (
    "left panel",
    "right photo",
    "top logo",
    "bottom CTA",
)

CANDIDATE_IDS = ("A", "B", "C")
MAX_IMAGE_CALLS = 3
DAY007_CENTERING = (0.68, 0.18)


def locked_grade_a() -> tuple[tuple[str, str], ...]:
    assert CANONICAL_FOLDER_NAME == "DESIGN_REFERENCES"
    assert "12_DESIGN_REFERENCES" in WRONG_PREFIX_NAMES
    return GRADE_A_REFERENCES


def _s(value: Any, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    return text


def normalize_grammar(raw: Any, *, filename: str, asset_id: str, media_asset_id: str) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("grammar") if isinstance(src.get("grammar"), dict) else src
    fields = {key: _s(nested.get(key) or nested.get(key.lower())) for key in GRAMMAR_FIELDS}
    strategy = _s(nested.get("composition_strategy") or src.get("composition_strategy") or "unspecified")
    return {
        "schema": "ReferenceCampaignGrammarV1",
        "filename": filename,
        "reference_id": asset_id,
        "media_asset_id": media_asset_id,
        "composition_strategy": strategy,
        "fields": fields,
        "coordinates_forbidden": True,
    }


def request_reference_grammars(references: list[tuple[str, Image.Image, str, str]]) -> tuple[dict[str, dict[str, Any]], int]:
    content: list[Any] = [
        _text(
            "You are extracting DESIGN GRAMMAR from finished advertising craft. "
            "Analyze ACTUAL PIXELS. Do not use filenames as evidence. "
            "A grammar describes RELATIONSHIPS, not coordinates. "
            "Forbidden simplifications: " + ", ".join(FORBIDDEN_SIMPLIFICATIONS) + ". "
            "Example of GOOD: 'headline forms dominant upper-left mass, photo pushes against headline field, "
            "commercial offer forms secondary counterweight, brand anchors visual entry, CTA closes lower rhythm.' "
            "Example of BAD: 'headline x=92 y=180' or 'left panel / right photo / top logo / bottom CTA'. "
            "For EACH reference return composition_strategy (short unique tag) and fields: "
            + ", ".join(GRAMMAR_FIELDS)
            + ". JSON {grammars:{FILENAME:{composition_strategy, ...fields}}}."
        )
    ]
    for filename, image, _rid, _mid in references:
        content.append(_text(f"REFERENCE PIXELS — {filename}"))
        content.append(_img(image, quality=78))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.2,
            "max_tokens": 4200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Design-grammar analyst. Relationships only. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    block = parsed.get("grammars") if isinstance(parsed.get("grammars"), dict) else parsed
    out: dict[str, dict[str, Any]] = {}
    for filename, _image, rid, mid in references:
        raw = {}
        if isinstance(block, dict):
            raw = block.get(filename) or block.get(filename.replace(".jpg", "")) or {}
        out[filename] = normalize_grammar(raw, filename=filename, asset_id=rid, media_asset_id=mid)
    return out, calls


def request_suitability_and_selection(
    *,
    day007: Image.Image,
    references: list[tuple[str, Image.Image, str, str]],
    grammars: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Judge which Grade-A grammars can be TRANSLATED around the REAL Day_007 photograph. "
            "Do not require Day_007 to imitate the reference photograph. "
            "Ask: can this RELATIONSHIP SYSTEM live around this architecture? "
            "Score 0-10: " + ", ".join(SUITABILITY_KEYS) + ". "
            "Then select exactly THREE meaningfully DIFFERENT composition strategies. "
            "Do not pick three near-identical grammars. "
            "Do not pick because the photo is merely clean. "
            "JSON {suitability:{FILENAME:{scores:{...}, why, composition_strategy}}, "
            'selected:[{slot:"A"|"B"|"C", filename, why, composition_strategy}]}.'
        ),
        _text("REAL DAY_007 — immutable project photograph:"),
        _img(day007, quality=80),
    ]
    for filename, image, _rid, _mid in references:
        grammar = grammars.get(filename) or {}
        content.append(_text(f"{filename} PIXELS"))
        content.append(_img(image, quality=58))
        content.append(_text(f"{filename} GRAMMAR: {grammar.get('fields')} strategy={grammar.get('composition_strategy')}"))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.15,
            "max_tokens": 2800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Suitability critic. Relationship translation only. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    suitability: dict[str, Any] = {}
    raw_s = parsed.get("suitability") if isinstance(parsed.get("suitability"), dict) else {}
    for filename, _image, rid, mid in references:
        item = raw_s.get(filename) if isinstance(raw_s.get(filename), dict) else {}
        scores = item.get("scores") if isinstance(item.get("scores"), dict) else item
        suitability[filename] = {
            "filename": filename,
            "reference_id": rid,
            "media_asset_id": mid,
            "composition_strategy": _s(item.get("composition_strategy") or (grammars.get(filename) or {}).get("composition_strategy")),
            "why": _s(item.get("why")),
            "scores": {k: round(_num((scores or {}).get(k), 0), 2) for k in SUITABILITY_KEYS},
            "average": round(
                sum(_num((scores or {}).get(k), 0) for k in SUITABILITY_KEYS) / max(len(SUITABILITY_KEYS), 1),
                2,
            ),
        }
    selected = _unique_selection(parsed.get("selected"), suitability, grammars)
    return {"schema": "ReferenceSuitabilityV1", "suitability": suitability, "selected": selected}, calls


def _unique_selection(raw: Any, suitability: dict[str, Any], grammars: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    seen_strategies: set[str] = set()
    rows = raw if isinstance(raw, list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        filename = _s(row.get("filename"))
        if filename not in suitability or filename in seen_files:
            continue
        strategy = _s(row.get("composition_strategy") or suitability[filename]["composition_strategy"] or filename)
        if strategy in seen_strategies and len(chosen) < 3:
            continue
        slot = _s(row.get("slot") or CANDIDATE_IDS[len(chosen)]).upper()
        if slot not in CANDIDATE_IDS:
            slot = CANDIDATE_IDS[len(chosen)]
        chosen.append(
            {
                "slot": slot,
                "filename": filename,
                "reference_id": suitability[filename]["reference_id"],
                "media_asset_id": suitability[filename]["media_asset_id"],
                "composition_strategy": strategy,
                "why": _s(row.get("why") or suitability[filename].get("why")),
                "grammar": grammars.get(filename),
                "suitability": suitability[filename],
            }
        )
        seen_files.add(filename)
        seen_strategies.add(strategy)
        if len(chosen) == 3:
            break
    if len(chosen) < 3:
        ranked = sorted(suitability.values(), key=lambda item: float(item.get("average") or 0), reverse=True)
        for item in ranked:
            filename = item["filename"]
            if filename in seen_files:
                continue
            strategy = _s(item.get("composition_strategy") or filename)
            if strategy in seen_strategies:
                continue
            chosen.append(
                {
                    "slot": CANDIDATE_IDS[len(chosen)],
                    "filename": filename,
                    "reference_id": item["reference_id"],
                    "media_asset_id": item["media_asset_id"],
                    "composition_strategy": strategy,
                    "why": _s(item.get("why")),
                    "grammar": grammars.get(filename),
                    "suitability": item,
                }
            )
            seen_files.add(filename)
            seen_strategies.add(strategy)
            if len(chosen) == 3:
                break
    for i, item in enumerate(chosen[:3]):
        item["slot"] = CANDIDATE_IDS[i]
    return chosen[:3]


def infer_photo_shape(grammar: dict[str, Any]) -> str:
    blob = " ".join(str(v) for v in (grammar.get("fields") or {}).values()).casefold()
    if any(word in blob for word in ("ellipse", "oval", "circular aperture", "round aperture")):
        return "ellipse"
    if any(word in blob for word in ("window", "rounded", "soft frame", "arch", "aperture")):
        return "rounded"
    return "rect"


def infer_alignment(grammar: dict[str, Any]) -> str:
    blob = " ".join(str(v) for v in (grammar.get("fields") or {}).values()).casefold()
    if "center" in blob and "left" not in blob:
        return "center"
    if "right" in blob and "left" not in blob:
        return "right"
    return "left"


def request_layout_translation(
    *,
    day007: Image.Image,
    selected: list[dict[str, Any]],
    reference_images: dict[str, Image.Image],
) -> tuple[dict[str, dict[str, Any]], int]:
    content: list[Any] = [
        _text(
            "Translate each selected DESIGN GRAMMAR onto The Temple / Day_007 as an ORIGINAL campaign. "
            "Return execution boxes in 0-1 for photo_box, brand_box, headline, offer, price, unit, cta, closure. "
            "photo_shape must come from the grammar (rect|rounded|ellipse) — do NOT default to ellipse, "
            "left half, right half, full-bleed background, or a property card. "
            "The photograph is a designed visual mass (about 35–70%). "
            "Commercial reading must be one hierarchy: ALIRKEN KAZAN → %35 LANSMAN AVANTAJI (one offer identity) "
            "→ 675.000 USD → 2+1 DAİRE → PROJEYİ KEŞFET. "
            "Brand is the real Temple logo only. CTA is editorial, not a web button. "
            "centering is Day_007 crop focus [cx,cy]. alignment is left|right|center. "
            'JSON {layouts:{A:{...},B:{...},C:{...}}}.'
        ),
        _text("REAL DAY_007:"),
        _img(day007, quality=76),
    ]
    for item in selected:
        filename = item["filename"]
        content.append(_text(f"SELECTED {item['slot']} — {filename} — {item.get('composition_strategy')}"))
        if filename in reference_images:
            content.append(_img(reference_images[filename], quality=70))
        content.append(_text("GRAMMAR RELATIONSHIPS: " + str((item.get("grammar") or {}).get("fields"))))
        content.append(_text("WHY IT FITS DAY_007: " + _s(item.get("why"))))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.25,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Grammar translator. Original Temple campaign. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    layouts = parsed.get("layouts") if isinstance(parsed.get("layouts"), dict) else parsed
    out: dict[str, dict[str, Any]] = {}
    for item in selected:
        slot = item["slot"]
        raw = layouts.get(slot) if isinstance(layouts, dict) and isinstance(layouts.get(slot), dict) else {}
        out[slot] = finalize_layout(raw, item.get("grammar") or {})
    return out, calls


def finalize_layout(raw: dict[str, Any], grammar: dict[str, Any]) -> dict[str, Any]:
    shape = _s(raw.get("photo_shape")).lower()
    if shape not in {"rect", "rounded", "ellipse"}:
        shape = infer_photo_shape(grammar)
    align = _s(raw.get("alignment") or infer_alignment(grammar)).lower()
    if align not in {"left", "right", "center"}:
        align = infer_alignment(grammar)
    centering = raw.get("centering") or raw.get("crop_centering") or list(DAY007_CENTERING)
    if isinstance(centering, dict):
        centering = (float(centering.get("x", 0.68)), float(centering.get("y", 0.18)))
    elif isinstance(centering, (list, tuple)) and len(centering) >= 2:
        centering = (float(centering[0]), float(centering[1]))
    else:
        centering = DAY007_CENTERING
    photo_default = {"x": 0.22, "y": 0.08, "w": 0.72, "h": 0.62}
    if align == "left":
        photo_default = {"x": 0.28, "y": 0.06, "w": 0.68, "h": 0.78}
    elif align == "right":
        photo_default = {"x": 0.04, "y": 0.06, "w": 0.62, "h": 0.80}
    photo = clamp_photo_mass(_box(raw.get("photo_box"), photo_default))
    type_x = 0.06 if photo["x"] >= 0.28 else 0.58
    if align == "center":
        type_x = 0.10
    fallbacks = {
        "brand_box": {"x": type_x, "y": 0.055, "w": 0.30, "h": 0.09},
        "headline": {"x": type_x, "y": 0.18, "w": 0.36, "h": 0.08},
        "offer": {"x": type_x, "y": 0.30, "w": 0.36, "h": 0.14},
        "price": {"x": type_x, "y": 0.48, "w": 0.34, "h": 0.08},
        "unit": {"x": type_x, "y": 0.58, "w": 0.28, "h": 0.05},
        "cta": {"x": type_x, "y": 0.72, "w": 0.28, "h": 0.045},
        "closure": {"x": 0.14, "y": 0.925, "w": 0.72, "h": 0.04},
    }
    layout = {
        "photo_role": _s(raw.get("photo_role") or (grammar.get("fields") or {}).get("PHOTO_ROLE") or "designed_photographic_mass"),
        "photo_shape": shape,
        "photo_box": photo,
        "centering": centering,
        "alignment": align,
        "cta_style": "hairline",
        "grade": {"warmth": 0.14, "contrast": 1.04, "brightness": 0.99},
        "composition_strategy": _s(grammar.get("composition_strategy")),
    }
    for key, fallback in fallbacks.items():
        layout[key] = _box(raw.get(key), fallback)
    return layout
