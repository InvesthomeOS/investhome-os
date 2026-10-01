"""Phase 5.9 disposable AI visual drafts + structure interpretation.

GPT Image is allowed only for disposable drafts. Production uses V4 + real assets.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.visual_composition_draft import (
    _contact_sheet,
    _img,
    _jpeg_bytes,
    _num,
    _png_bytes,
    _text,
)
from investhome_api.services.gpt_image_design.client import GptImageProviderError, decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import DEFAULT_MODEL, openai_api_key, provider_availability, resolve_base_url, resolve_model
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

DRAFT_THESES = (
    {
        "id": "A",
        "concept_name": "Sky Monument Editorial",
        "reconstruction_mode": "SKY_VEIL",
        "visual_thesis": (
            "Campaign-scale display lives in a designed sky veil as one editorial column; "
            "architecture remains the monument beneath. Graphic fields, type mass, and negative "
            "space compose the whole 4:5 frame — not a caption parked in leftover sky."
        ),
    },
    {
        "id": "B",
        "concept_name": "Grounded Campaign Lockup",
        "reconstruction_mode": "GROUND_PLANE",
        "visual_thesis": (
            "Architecture soars unobstructed. The commercial story is one designed ground lockup "
            "bound by a tonal plane and editorial rules. Offer, brand, and CTA share one relationship, "
            "not a footer caption row."
        ),
    },
    {
        "id": "C",
        "concept_name": "Asymmetric Ingress",
        "reconstruction_mode": "CORNER_INGRESS",
        "visual_thesis": (
            "A directional graphic field lets the campaign enter the photograph as an L-lockup. "
            "Type mass, brand, and CTA share the ingress. Photography continues. No split navy column."
        ),
    },
)

DRAFT_POSITIVE = (
    "AGENCY_CAMPAIGN_FEEL",
    "ART_DIRECTION",
    "ORIGINALITY",
    "WHOLE_CANVAS_DESIGN",
    "PHOTO_GRAPHIC_INTEGRATION",
    "TYPOGRAPHIC_MASS",
    "COMMERCIAL_STORYTELLING",
    "VISUAL_RHYTHM",
    "PREMIUM_CHARACTER",
    "BRAND_PRESENCE",
    "CTA_RELATIONSHIP",
)

DRAFT_BAD = (
    "PHOTO_PLUS_TEXT",
    "CORNER_TEXT",
    "PROPERTY_LISTING",
    "TEMPLATE",
    "SIDEBAR",
    "CARD",
    "CAPTION_ROW",
    "COMMERCIAL_ISLANDS",
    "DEAD_SPACE",
    "UI_FEEL",
)

FIDELITY_V1 = (
    "composition_fidelity",
    "visual_mass_fidelity",
    "group_relationship_fidelity",
    "graphic_depth_fidelity",
    "typographic_mass_fidelity",
    "reading_flow_fidelity",
    "commercial_story_fidelity",
    "brand_role_fidelity",
    "CTA_role_fidelity",
    "whole_canvas_fidelity",
)

STRUCTURE_FIELDS = (
    "dominant_axis",
    "visual_mass_map",
    "graphic_fields",
    "campaign_group",
    "offer_group",
    "brand_group",
    "action_group",
    "group_geometry",
    "group_relationships",
    "type_mass",
    "type_scale_ratios",
    "alignment_system",
    "graphic_rules",
    "tonal_fields",
    "photo_interaction",
    "negative_space_roles",
    "reading_flow",
    "visual_gravity",
    "CTA_closure",
    "brand_relationship",
    "commercial_relationship",
)

V4_CAPABILITY_NOTES = {
    "graphic_depth_fidelity": "GraphicFieldEngineV1 has a fixed field vocabulary per mode; painterly layered depth in the draft may flatten.",
    "typographic_mass_fidelity": "TypographicCompositionEngineV1 clamps display scale; campaign-scale draft type may shrink.",
    "whole_canvas_fidelity": "V4 is group-column reconstruction; drafts that paint across the full frame as one graphic object cannot be cloned pixel-for-pixel.",
    "visual_mass_fidelity": "V4 places a relational lockup; it does not sculpt custom type-as-architecture silhouettes.",
    "group_relationship_fidelity": "CreativeGroupV2 encodes campaign/offer/brand/action; novel extra groups in the draft are collapsed.",
}


def _box(raw: Any) -> dict[str, float]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    return {
        "x": round(max(0.0, min(1.0, _num(data.get("x"), 0.06))), 4),
        "y": round(max(0.0, min(1.0, _num(data.get("y")))), 4),
        "w": round(max(0.0, min(1.0, _num(data.get("w") or data.get("width"), 0.28))), 4),
        "h": round(max(0.0, min(1.0, _num(data.get("h") or data.get("height"), 0.08))), 4),
    }


def advertising_photo_score(item: dict[str, Any]) -> float:
    sky = float(item.get("sky_area") or 0)
    hard = float(item.get("hard_coverage") or 0)
    cx = float(item.get("architecture_centroid_x") or 0.5)
    return sky * 1.2 + (1.0 - hard) * 0.5 + abs(cx - 0.5) * 0.4


def select_advertising_photo(catalog: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not catalog:
        return None
    best = max(catalog, key=advertising_photo_score)
    return {
        "photo_asset_id": best["asset_id"],
        "filename": best["filename"],
        "selection_reason": (
            "Strongest integrated-advertising potential: usable sky/ground pocket, "
            "architecture not filling the frame, side mass for a campaign lockup."
        ),
        "sky_area": best.get("sky_area"),
        "architecture_centroid_x": best.get("architecture_centroid_x"),
        "hard_coverage": best.get("hard_coverage"),
        "item": best,
    }


def draft_prompt(thesis: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create ONE 4:5 (1088x1360) HIGH-FIDELITY VISUAL COMPOSITION DRAFT for a premium real-estate campaign.",
            "This draft is a DISPOSABLE ART-DIRECTION BLUEPRINT. It will never be published.",
            "Imperfect text spelling is acceptable. Approximate logo is acceptable.",
            "First input image = the REAL Temple exterior. Keep the building recognizably that photograph.",
            "Other inputs = Grade-A design-reference PIXELS (craft only) and the real Temple logo as visual reference.",
            "Do NOT copy reference buildings, logos, or project names.",
            f"CONCEPT {thesis['id']}: {thesis['concept_name']}.",
            thesis["visual_thesis"],
            "LOCKED COPY as visual mass: ALIRKEN KAZAN / %35 LANSMAN AVANTAJI / 675.000 USD / 2+1 DAİRE / PROJEYİ KEŞFET / THE TEMPLE.",
            "Feel like a finished agency campaign: integrated tonal fields, typographic mass interacting with photography,",
            "designed negative space, graphic transitions, sophisticated offer lockup, CTA closing the reading flow.",
            "WHOLE-CANVAS DESIGN is mandatory — photo, type, graphic field, offer, brand, CTA, and negative space must relate.",
            "HARD REJECT: photo + text upper-left; photo + text lower-left; four corner labels; sidebar; card; caption row;",
            "property listing; website hero; social template; navy information column; pills; badges; dashboard.",
            "No extra marketing copy. No invented facts. Navy/ivory/restrained gold. Editorial serif display.",
        ]
    )


def generate_visual_draft(
    *,
    photo: Image.Image,
    logo: Image.Image,
    references: list[tuple[str, Image.Image]],
    thesis: dict[str, Any],
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"schema": "VisualCompositionDraftV2", "ok": False, "reason": avail.reason, "image_calls": 0, **thesis}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    sheet = _contact_sheet(references)
    attempts: list[tuple[list[tuple[bytes, str, str]], str]] = [
        (
            [
                (_png_bytes(photo), "temple-exterior.png", "image/png"),
                (_png_bytes(logo.convert("RGB")), "temple-logo.png", "image/png"),
                (_jpeg_bytes(sheet, 78), "grade-a-contact-sheet.jpg", "image/jpeg"),
            ],
            "1088x1360",
        ),
        (
            [
                (_png_bytes(photo), "temple-exterior.png", "image/png"),
                (_jpeg_bytes(sheet, 78), "grade-a-contact-sheet.jpg", "image/jpeg"),
            ],
            "1088x1360",
        ),
        (
            [(_png_bytes(photo), "temple-exterior.png", "image/png"), (_jpeg_bytes(sheet, 78), "grade-a.jpg", "image/jpeg")],
            "1024x1536",
        ),
    ]
    last_error = "draft generation failed"
    calls = 0
    for images, size in attempts:
        try:
            remote = edit_image(
                api_key=openai_api_key(),
                model=model,
                prompt=draft_prompt(thesis),
                images=images,
                size=size,
                quality="high",
                base_url=resolve_base_url(settings),
                variant=f"phase5_9_draft_{thesis['id']}",
                timeout=300.0,
            )
            calls += 1
            draft = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
            if draft.size != (1088, 1360):
                draft = draft.resize((1088, 1360), Image.Resampling.LANCZOS)
            return {
                "schema": "VisualCompositionDraftV2",
                "ok": True,
                "image": draft,
                "disposable": True,
                "not_production": True,
                "architecture_untrusted": True,
                "logo_untrusted": True,
                "typography_untrusted": True,
                "image_calls": calls,
                "model": model,
                "requested_size": size,
                **thesis,
            }
        except GptImageProviderError as exc:
            calls += 1
            last_error = str(exc.detail)[:240]
    return {"schema": "VisualCompositionDraftV2", "ok": False, "reason": last_error, "image_calls": calls, **thesis}


def draft_critic_pass(scores: dict[str, Any]) -> bool:
    if not scores:
        return False
    if any(_num(scores.get(key)) < 8 for key in DRAFT_POSITIVE):
        return False
    if any(_num(scores.get(key), 0) > 2 for key in DRAFT_BAD):
        return False
    return True


def request_draft_critic_v2(
    draft: Image.Image,
    photo: Image.Image,
    references: list[tuple[str, Image.Image]],
    thesis: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Critique this DISPOSABLE visual art-direction draft. Ignore spelling and logo accuracy. "
            "Hard-reject photo+text corners, listings, sidebars, cards, caption rows, templates, UI. "
            "Score 0-10: "
            + ", ".join(DRAFT_POSITIVE)
            + ". Undesirable <=2: "
            + ", ".join(DRAFT_BAD)
            + ". Do not inflate. JSON only."
        ),
        _text(json.dumps({"concept": thesis.get("concept_name"), "thesis": thesis.get("visual_thesis")}, ensure_ascii=False)),
        _text("DRAFT"),
        _img(draft, quality=84),
        _text("SOURCE PHOTO"),
        _img(photo, quality=62),
    ]
    for name, image in references[:4]:
        content.append(_text(f"Grade-A {name}"))
        content.append(_img(image, quality=56))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Honest agency art director. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    parsed = parsed if isinstance(parsed, dict) else {}
    blobs: list[Any] = [parsed, parsed.get("scores"), parsed.get("positives"), parsed.get("undesirable")]
    out: dict[str, Any] = {}
    for key in DRAFT_POSITIVE:
        out[key] = 0.0
        for blob in blobs:
            if isinstance(blob, dict) and blob.get(key) is not None:
                out[key] = _num(blob.get(key))
                break
    vision_hit = any(out[key] > 0 for key in DRAFT_POSITIVE)
    for key in DRAFT_BAD:
        found = None
        for blob in blobs:
            if isinstance(blob, dict) and blob.get(key) is not None:
                found = _num(blob.get(key))
                break
        out[key] = found if found is not None else (1.0 if vision_hit else 10.0)
    out["pass"] = draft_critic_pass(out)
    out["schema"] = "VisualDraftCriticV2"
    out["mode"] = "vision" if vision_hit else "unavailable"
    out["concept_name"] = thesis.get("concept_name")
    return out, calls


def extract_structure_map_v1(draft: Image.Image, thesis: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "VisualDraftStructureMapV1. Extract RELATIONSHIPS, not a caption inventory. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Map this art-direction draft into VisualDraftStructureMapV1. "
                            "Groups: campaign_group, offer_group, brand_group, action_group as {x,y,w,h,role,relationship}. "
                            "Also: "
                            + ", ".join(STRUCTURE_FIELDS)
                            + ". reconstruction_mode one of SKY_VEIL, GROUND_PLANE, CORNER_INGRESS. "
                            "Do not collapse into adjectives. Measure relationships: mass, alignment, reading flow, gravity, CTA closure."
                        ),
                        _img(draft, quality=84),
                    ],
                },
            ],
        }
    )
    data = dict(parsed or {}) if isinstance(parsed, dict) else {}
    groups = {}
    for key in ("campaign_group", "offer_group", "brand_group", "action_group"):
        blob = data.get(key) if isinstance(data.get(key), dict) else {}
        groups[key] = {**_box(blob), "role": str(blob.get("role") or key), "relationship": str(blob.get("relationship") or "")}
    campaign = groups["campaign_group"]
    mode = str(data.get("reconstruction_mode") or thesis.get("reconstruction_mode") or "").upper()
    if mode not in {"SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"}:
        if campaign["y"] > 0.50:
            mode = "GROUND_PLANE"
        elif campaign["x"] < 0.18 and 0.12 < campaign["y"] < 0.40:
            mode = "CORNER_INGRESS"
        else:
            mode = "SKY_VEIL"
    if not data:
        mode = str(thesis.get("reconstruction_mode") or "SKY_VEIL")
        y = 0.64 if mode == "GROUND_PLANE" else 0.20 if mode == "CORNER_INGRESS" else 0.046
        groups["campaign_group"] = {**_box({"x": 0.055, "y": y, "w": 0.42, "h": 0.10}), "role": "campaign", "relationship": "leads"}
        campaign = groups["campaign_group"]
    ok = campaign["w"] >= 0.12 and campaign["h"] >= 0.04
    out = {
        "schema": "VisualDraftStructureMapV1",
        "structure_id": str(uuid4()),
        "concept_name": thesis.get("concept_name"),
        "reconstruction_mode": mode,
        "pass": ok,
        "mode": "vision" if parsed else "unavailable",
        **groups,
    }
    for key in STRUCTURE_FIELDS:
        if key not in groups:
            out[key] = data.get(key)
    out["dominant_axis"] = str(data.get("dominant_axis") or "vertical")
    out["reading_flow"] = data.get("reading_flow") or ["campaign", "offer", "brand", "action"]
    out["group_relationships"] = data.get("group_relationships") or "CAMPAIGN_GROUP CONNECTED_TO OFFER_GROUP; BRAND_GROUP SHARES_BAND; ACTION_GROUP CLOSES"
    ratios = data.get("type_scale_ratios") if isinstance(data.get("type_scale_ratios"), dict) else {}
    out["type_scale_ratios"] = {
        "headline": _num(ratios.get("headline"), campaign["h"]),
        "discount": _num(ratios.get("discount"), 0.04),
        "price": _num(ratios.get("price"), 0.035),
    }
    return out, calls


def infer_mode_from_structure(structure: dict[str, Any]) -> str:
    mode = str(structure.get("reconstruction_mode") or "").upper()
    if mode in {"SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"}:
        return mode
    y = _num((structure.get("campaign_group") or {}).get("y"))
    if y > 0.50:
        return "GROUND_PLANE"
    if y > 0.14:
        return "CORNER_INGRESS"
    return "SKY_VEIL"


def plan_from_structure(structure: dict[str, Any], *, photo: dict[str, Any]) -> dict[str, Any]:
    mode = infer_mode_from_structure(structure)
    campaign = structure.get("campaign_group") or {}
    ratios = structure.get("type_scale_ratios") or {}
    headline_h = _num(ratios.get("headline"), _num(campaign.get("h"), 0.08))
    scale = min(1.22, max(0.88, headline_h / 0.08))
    return {
        "schema": "RelationalCompositionPlanV1",
        "plan_id": str(uuid4()),
        "source": "VisualDraftStructureMapV1",
        "structure_id": structure.get("structure_id"),
        "concept_name": structure.get("concept_name"),
        "reconstruction_mode": mode,
        "scale": round(scale, 4),
        "origin": {"x": round(_num(campaign.get("x"), 0.055), 4), "y": round(_num(campaign.get("y"), 0.05), 4)},
        "selected_photo_asset_id": photo.get("asset_id"),
        "selected_photo_filename": photo.get("filename"),
        "groups": ["CAMPAIGN_GROUP", "OFFER_GROUP", "BRAND_GROUP", "ACTION_GROUP"],
        "group_relationships": structure.get("group_relationships"),
        "graphic_field_strategy": structure.get("graphic_fields") or structure.get("tonal_fields"),
        "reading_flow": structure.get("reading_flow"),
        "brand_anchor": {"reason": structure.get("brand_relationship")},
        "split_panel": False,
    }


def request_reconstruction_fidelity_v1(draft: Image.Image, reconstruction: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "VisualDraftReconstructionFidelityV1. Ignore spelling and architecture pixels. JSON 0-10."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Compare DRAFT (image 1) vs V4 STRUCTURED RECONSTRUCTION (image 2). "
                            "Ignore misspellings and whether building pixels match. Score: "
                            + ", ".join(FIDELITY_V1)
                            + ". Require >=8. Do not inflate. List capabilities V4 failed to reproduce."
                        ),
                        _text("DRAFT"),
                        _img(draft, quality=80),
                        _text("RECONSTRUCTION"),
                        _img(reconstruction, quality=80),
                    ],
                },
            ],
        }
    )
    nested = parsed.get("scores") if isinstance((parsed or {}).get("scores"), dict) else parsed
    scores = {key: _num((nested or {}).get(key)) for key in FIDELITY_V1}
    missing = [key for key, value in scores.items() if value < 8]
    gaps = [V4_CAPABILITY_NOTES[key] for key in missing if key in V4_CAPABILITY_NOTES]
    extra = parsed.get("v4_could_not_reproduce") if isinstance(parsed, dict) else None
    if extra:
        gaps.append(str(extra)[:400])
    return {
        "schema": "VisualDraftReconstructionFidelityV1",
        "scores": scores,
        "pass": bool(scores) and all(value >= 8 for value in scores.values()),
        "missing_keys": missing,
        "v4_could_not_reproduce": gaps,
        "mode": "vision" if parsed else "unavailable",
    }, calls


def rank_drafts(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def mean(item: dict[str, Any]) -> float:
        critic = item.get("critic") or {}
        return sum(_num(critic.get(key)) for key in DRAFT_POSITIVE) / max(1, len(DRAFT_POSITIVE))

    passed = [item for item in drafts if (item.get("critic") or {}).get("pass")]
    pool = passed or []
    return sorted(pool, key=mean, reverse=True)


def _board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2100)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=_font(22), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > size[1] - 36:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def render_reference_board(references: list[tuple[str, Image.Image]], logo: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1880, 980), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "01  GRADE-A DESIGN_REFERENCES  +  REAL TEMPLE LOGO", font=_font(20), fill=(232, 214, 170))
    x = 36
    for name, image in references:
        thumb = image.copy()
        thumb.thumbnail((280, 360), Image.Resampling.LANCZOS)
        canvas.paste(thumb.convert("RGB"), (x, 70))
        draw.text((x, 70 + thumb.size[1] + 6), name[:28], font=_font(12), fill=(180, 176, 168))
        x += 300
    mark = logo.copy()
    mark.thumbnail((220, 120), Image.Resampling.LANCZOS)
    canvas.paste(mark.convert("RGB"), (36, 520))
    draw.text((36, 660), "Logo is visual reference for drafts only. Production uses the exact SVG asset.", font=_font(14), fill=(201, 168, 92))
    return canvas


def render_draft_strip(title: str, rows: list[tuple[str, Image.Image | None]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 36
    for label, image in rows[:3]:
        if image is not None:
            tile = image.copy()
            tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label[:48], font=_font(14), fill=(180, 176, 168))
        x += 620
    return canvas


def render_draft_vs(draft: Image.Image, reconstruction: Image.Image, label: str) -> Image.Image:
    canvas = Image.new("RGB", (1600, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), f"{label}  DRAFT vs V4 MASTER  —  draft is not production", font=_font(18), fill=(201, 168, 92))
    a = draft.copy()
    a.thumbnail((720, 900), Image.Resampling.LANCZOS)
    b = reconstruction.copy()
    b.thumbnail((720, 900), Image.Resampling.LANCZOS)
    canvas.paste(a.convert("RGB"), (36, 56))
    canvas.paste(b.convert("RGB"), (820, 56))
    draw.text((36, 940), "AI DRAFT  disposable", font=_font(14), fill=(180, 176, 168))
    draw.text((820, 940), "V4  real photo + real logo + production type", font=_font(14), fill=(180, 176, 168))
    return canvas
