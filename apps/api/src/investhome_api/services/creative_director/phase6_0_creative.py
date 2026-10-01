"""Phase 6.0 Stage A — pure creative direction and concept generation.

This module must not mention production engines, reconstruction, or editability.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.visual_composition_draft import _contact_sheet, _jpeg_bytes, _png_bytes
from investhome_api.services.gpt_image_design.client import GptImageProviderError, decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import DEFAULT_MODEL, openai_api_key, provider_availability, resolve_base_url, resolve_model
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

CAMPAIGN_COPY = (
    "ALIRKEN KAZAN",
    "%35 LANSMAN AVANTAJI",
    "675.000 USD",
    "2+1 DAİRE",
    "PROJEYİ KEŞFET",
    "THE TEMPLE",
)

CREATIVE_OBJECTIVE = (
    "Create a premium real-estate advertising campaign for The Temple, Washington DC. "
    "The building is architecturally distinctive and must feel iconic. "
    "Communicate heritage, prestige, investment opportunity, contemporary luxury, and architectural character. "
    "The advertisement must feel designed by a top independent creative agency, not assembled by software. "
    "It should have a strong visual idea and remain memorable even if the text were removed. "
    "Typography, photography, graphic treatment and brand should feel like one art-directed visual language."
)

CRITIC_KEYS = (
    "CREATIVE_IDEA",
    "ART_DIRECTION",
    "COMPOSITION",
    "TYPOGRAPHIC_CHARACTER",
    "PHOTO_GRAPHIC_INTEGRATION",
    "VISUAL_DEPTH",
    "BRAND_CHARACTER",
    "COMMERCIAL_STORYTELLING",
    "PREMIUM_FEEL",
    "MEMORABILITY",
    "REFERENCE_QUALITY_LEVEL",
    "OVERALL_DESIGN_QUALITY",
)

MAX_IMAGE_CALLS = 6


def request_six_creative_briefs(
    *,
    photos: list[dict[str, Any]],
    references: list[tuple[str, Image.Image]],
    logo: Image.Image,
) -> tuple[list[dict[str, Any]], int]:
    names = [str(item.get("filename") or "") for item in photos]
    content: list[dict[str, Any]] = [
        _text(
            "You are an independent advertising Creative Director. "
            "Inspect the Temple photographs, the real project logo, and the quality references first. "
            "Then invent SIX genuinely different campaign concepts. Each concept chooses its own photograph. "
            "Do not repeat one layout. Do not make A/B variations of a single idea. "
            "References are quality references, not templates. Study confidence, visual sophistication, "
            "typographic drama, composition, layering, image treatment, graphic depth, commercial storytelling, "
            "brand presence, negative space, and visual rhythm. Create original work at or above this quality. "
            "Avoid generic real-estate listing templates and ordinary website-style layouts. "
            "Campaign copy (do not invent facts): "
            + " / ".join(CAMPAIGN_COPY)
            + ". Objective: "
            + CREATIVE_OBJECTIVE
            + " For each concept return selected_project_image (must be one of: "
            + ", ".join(names)
            + "), why_this_photograph, visual_idea, creative_brief (a concise brief for an image artist). "
            "JSON {\"concepts\":[...]} exactly six."
        ),
        _text("REAL PROJECT LOGO"),
        _img(logo, quality=90),
    ]
    for item in photos:
        content.append(_text(f"APPROVED PROJECT PHOTOGRAPH: {item['filename']}"))
        content.append(_img(item["preview"], quality=58))
    for name, image in references:
        content.append(_text(f"QUALITY REFERENCE (inspiration, not a template): {name}"))
        content.append(_img(image, quality=62))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.7,
            "max_tokens": 4500,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Independent advertising Creative Director. Invent visual ideas. JSON only.",
                },
                {"role": "user", "content": content},
            ],
        }
    )
    raw = parsed.get("concepts") if isinstance(parsed.get("concepts"), list) else []
    briefs = []
    for i, item in enumerate(raw[:6]):
        data = dict(item) if isinstance(item, dict) else {}
        briefs.append(
            {
                "index": i + 1,
                "selected_project_image": str(data.get("selected_project_image") or data.get("photograph") or "").strip(),
                "why_this_photograph": str(data.get("why_this_photograph") or "").strip(),
                "visual_idea": str(data.get("visual_idea") or data.get("idea") or "").strip(),
                "creative_brief": str(data.get("creative_brief") or data.get("brief") or "").strip(),
            }
        )
    return briefs, calls


def image_artist_prompt(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create one 4:5 premium real-estate campaign advertisement.",
            "The first image is the chosen project photograph. The logo image is the real brand mark. Other images are quality references, not templates.",
            "Study their confidence, visual sophistication, typographic drama, composition, layering, image treatment, graphic depth, commercial storytelling, brand presence, negative space, and visual rhythm.",
            "Create original work at or above this quality. Do not copy a reference.",
            CREATIVE_OBJECTIVE,
            "Visual idea: " + (brief.get("visual_idea") or ""),
            "Creative brief: " + (brief.get("creative_brief") or ""),
            "Required copy only: " + " / ".join(CAMPAIGN_COPY) + ".",
            "Avoid generic real-estate listing templates and ordinary website-style layouts.",
        ]
    )


def generate_concept_image(
    *,
    photo: Image.Image,
    logo: Image.Image,
    references: list[tuple[str, Image.Image]],
    brief: dict[str, Any],
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"ok": False, "reason": avail.reason, "image_calls": 0}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images = [
        (_png_bytes(photo), "project-photo.png", "image/png"),
        (_png_bytes(logo.convert("RGB")), "project-logo.png", "image/png"),
        (_jpeg_bytes(_contact_sheet(references), 80), "quality-references.jpg", "image/jpeg"),
    ]
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=model,
            prompt=image_artist_prompt(brief),
            images=images,
            size="1088x1360",
            quality="high",
            base_url=resolve_base_url(settings),
            variant=f"phase6_0_concept_{brief.get('index')}",
            timeout=300.0,
        )
        concept = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
        if concept.size != (1088, 1360):
            concept = concept.resize((1088, 1360), Image.Resampling.LANCZOS)
        return {"ok": True, "image": concept, "image_calls": 1, "model": model}
    except GptImageProviderError as exc:
        return {"ok": False, "reason": str(exc.detail)[:240], "image_calls": 1, "model": model}


def request_fresh_visual_critic(
    *,
    concepts: list[dict[str, Any]],
    references: list[tuple[str, Image.Image]],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "You are a senior advertising / design-studio critic seeing these images for the first time. "
            "Which look like work from a strong professional studio? "
            "Judge the creative idea, not letter-perfect type or logo tracing. "
            "Score each candidate 0-10: "
            + ", ".join(CRITIC_KEYS)
            + ". Then rank all six 1=best. JSON {\"scores\": {\"1\": {...}}, \"ranking\": [1,2,3,4,5,6], \"notes\": \"\"}."
        ),
        _text("CREATIVE OBJECTIVE: " + CREATIVE_OBJECTIVE),
        _text("COPY: " + " / ".join(CAMPAIGN_COPY)),
    ]
    for item in concepts:
        content.append(_text(f"CANDIDATE {item.get('index')}"))
        if isinstance(item.get("image"), Image.Image):
            content.append(_img(item["image"], quality=82))
        else:
            content.append(_text("(missing image)"))
    for name, image in references:
        content.append(_text(f"QUALITY REFERENCE {name}"))
        content.append(_img(image, quality=56))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 3500,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    raw_scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    scores: dict[str, dict[str, float]] = {}
    for item in concepts:
        key = str(item.get("index"))
        blob = raw_scores.get(key) if isinstance(raw_scores, dict) else None
        if blob is None and isinstance(raw_scores, dict):
            blob = raw_scores.get(f"CANDIDATE {key}") or raw_scores.get(item.get("name"))
        bucket = blob if isinstance(blob, dict) else {}
        scores[key] = {field: _num(bucket.get(field)) for field in CRITIC_KEYS}
    ranking = parsed.get("ranking") if isinstance(parsed.get("ranking"), list) else []
    ranking = [int(_num(v)) for v in ranking if _num(v) >= 1]
    if len(ranking) < 6:
        ranking = sorted(
            [int(item.get("index") or 0) for item in concepts],
            key=lambda idx: -sum(scores.get(str(idx), {}).values()),
        )
    return {
        "schema": "FreshVisualCriticV1",
        "scores": scores,
        "ranking": ranking[:6],
        "notes": str(parsed.get("notes") or ""),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def overall(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return round(sum(_num(v) for v in scores.values()) / max(1, len(CRITIC_KEYS)), 3)


def resolve_photo(catalog: list[dict[str, Any]], requested: str, used: set[str]) -> dict[str, Any]:
    needle = (requested or "").lower()
    unused = [item for item in catalog if item["asset_id"] not in used]
    if needle:
        for item in unused or catalog:
            name = item["filename"].lower()
            if needle in name or name in needle:
                return item
    pool = unused or catalog
    return max(
        pool,
        key=lambda it: float(it.get("sky_area") or 0) + abs(float(it.get("architecture_centroid_x") or 0.5) - 0.5),
    )


def render_six_board(concepts: list[dict[str, Any]], title: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1480), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(20), fill=(201, 168, 92))
    for i, item in enumerate(concepts[:6]):
        gx, gy = i % 3, i // 3
        x, y = 36 + gx * 620, 70 + gy * 700
        image = item.get("image")
        if isinstance(image, Image.Image):
            tile = image.copy()
            tile.thumbnail((580, 620), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, y))
        label = f"{item.get('index')}  {str(item.get('name') or '')[:36]}"
        draw.text((x, y + 630), label, font=_font(14), fill=(226, 222, 214))
    return canvas


def render_critic_board(critic: dict[str, Any], concepts: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1600, 2100), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 28), "10  FRESH VISUAL CRITIC", font=_font(22), fill=(232, 214, 170))
    draw.text((40, 70), f"ranking  {critic.get('ranking')}", font=_font(18), fill=(201, 168, 92))
    y = 120
    for item in concepts:
        idx = str(item.get("index"))
        scores = (critic.get("scores") or {}).get(idx) or {}
        draw.text((40, y), f"CONCEPT {idx}  {item.get('name')}  overall={overall(scores)}", font=_font(16), fill=(236, 230, 218))
        y += 28
        for line in _wrap("  ".join(f"{k}:{scores.get(k)}" for k in CRITIC_KEYS), 92):
            draw.text((40, y), line, font=_font(14), fill=(180, 176, 168))
            y += 22
        y += 12
        if y > 2000:
            break
    return canvas


def name_concepts(concepts: list[dict[str, Any]]) -> None:
    for item in concepts:
        idea = str(item.get("visual_idea") or item.get("creative_brief") or f"Concept {item.get('index')}").strip()
        item["name"] = " ".join(idea.split()[:5]) or f"Concept {item.get('index')}"
        item["concept_id"] = str(uuid4())
