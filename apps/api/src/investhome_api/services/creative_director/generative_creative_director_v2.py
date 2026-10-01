"""GenerativeCreativeDirectorV2 — compose original Temple ads from doctrine + reference DNA.

Requires real DESIGN_REFERENCES analysis. Does not select a coordinate template.
Does not call GPT Image as the project designer.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4, uuid5, NAMESPACE_URL

from PIL import Image

from investhome_api.services.creative_director.creative_reference_library import DesignReferencesNotFound
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_b64,
    _vision,
    assemble_scene,
    validate_scene,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

DIRECTIONS = (
    {
        "key": "A",
        "concept": "ARCHITECTURAL_EDITORIAL",
        "intent": (
            "Architecture-forward, sophisticated typography, editorial composition, "
            "intelligent negative space, premium restraint, elegant commercial information. "
            "Must still feel like advertising."
        ),
    },
    {
        "key": "B",
        "concept": "PREMIUM_CAMPAIGN",
        "intent": (
            "Stronger advertising impact, strong price visibility, strong launch advantage, "
            "clear commercial hierarchy, premium visual character, photo and graphics integrated. "
            "Must not resemble a real-estate listing card."
        ),
    },
    {
        "key": "C",
        "concept": "CONTEMPORARY_LUXURY",
        "intent": (
            "Strongest art direction, modern image/type relationship, more experimental composition, "
            "distinctive graphic intervention, restrained luxury, publishable professional result. "
            "Avoid luxury clichés."
        ),
    },
)

SEMANTIC_ROLES = (
    "project_photo",
    "project_logo",
    "headline",
    "unit_type",
    "price",
    "discount",
    "discount_label",
    "cta",
)


def _dna_brief(retrieved: list[dict[str, Any]]) -> str:
    rows = []
    for item in retrieved[:8]:
        dna = dict(item.get("dna") or {})
        rows.append(
            {
                "reference_id": item.get("reference_id"),
                "filename": item.get("filename"),
                "project_affinity": item.get("project_affinity"),
                "why_it_works": dna.get("WHY_IT_WORKS"),
                "reusable": dna.get("REUSABLE_PRINCIPLES"),
                "do_not_copy": dna.get("DO_NOT_COPY"),
                "composition_philosophy": dna.get("composition_philosophy"),
                "typography_hierarchy": dna.get("typography_hierarchy"),
                "graphic_intervention_style": dna.get("graphic_intervention_style"),
            }
        )
    return json.dumps(rows, ensure_ascii=True)[:8000]


def request_reference_dna(image: Image.Image, *, filename: str) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior art director extracting reusable design DNA from an approved "
                    "advertising reference. Inspect the actual image. Do not guess from the filename. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Filename is metadata only ({filename}). Analyze the design you see. "
                            "JSON keys: composition_philosophy, focal_hierarchy, visual_balance, image_dominance, "
                            "negative_space_strategy, text_image_integration, typography_hierarchy, headline_behavior, "
                            "price_behavior, commercial_information_strategy, logo_integration, cta_integration, "
                            "grid_behavior, asymmetry, spacing_rhythm, contrast, color_relationships, information_density, "
                            "premium_character, editorial_character, graphic_restraint, visual_movement, reading_order, "
                            "subject_protection, graphic_intervention_style, WHY_IT_WORKS, REUSABLE_PRINCIPLES (array), "
                            "DO_NOT_COPY (array). Never output coordinates to clone."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["visual_analysis_status"] = "ANALYZED" if parsed.get("WHY_IT_WORKS") or parsed.get("composition_philosophy") else "FAILED"
    return parsed, calls


def request_photo_composition_analysis(foundation: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Analyze one locked architectural photograph for advertising composition. JSON only.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is the exact 1088×1360 Day_004 crop. Detect architecture silhouette, spire/tower, "
                            "façade, entrance, architectural focal regions, sky, foreground, street, visual noise, "
                            "quiet areas, negative space, contrast regions, possible typography/logo/commercial regions, "
                            "protected architecture regions, perspective direction, visual flow. "
                            "JSON schema ProjectPhotoCompositionAnalysisV1. Boxes 0-1 {x,y,w,h} if used. "
                            "Do not recommend inventing panels over the building."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["schema"] = "ProjectPhotoCompositionAnalysisV1"
    parsed["mode"] = "vision" if parsed.get("visual_flow") or parsed.get("spire") or parsed.get("regions") else "unavailable"
    return parsed, calls


def request_concept_set(
    *,
    foundation: Image.Image,
    photo_analysis: dict[str, Any],
    doctrine: dict[str, Any],
    retrieved: list[dict[str, Any]],
    fonts: dict[str, Any],
    facts: dict[str, str],
    logo_preview: Image.Image | None = None,
) -> tuple[dict[str, Any], int]:
    if not retrieved:
        raise DesignReferencesNotFound("GenerativeCreativeDirectorV2 requires retrieved ReferenceDesignDNA")
    roles = fonts.get("roles") or {}
    font_note = (
        f"DISPLAY {(roles.get('DISPLAY_SERIF') or {}).get('font_file')} / "
        f"SUPPORT {(roles.get('EDITORIAL_SANS') or {}).get('font_file')} / "
        f"optional DISPLAY_SANS {(roles.get('DISPLAY_SANS') or {}).get('font_file')}. "
        "Decide typography per concept. Do not clone one treatment across A/B/C. Never DejaVu."
    )
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "You are GenerativeCreativeDirectorV2. Reason about visual composition BEFORE writing markup.\n"
                "Output exactly three genuinely different art-direction concepts for The Temple. "
                "Moving type slightly is not a different concept.\n"
                "Learn design logic from references. Do NOT clone them. Do NOT copy buildings, logos, or copywriting.\n"
                "The photograph MUST remain a real <img data-semantic=\"project_photo\" src=\"{{PHOTO_SRC}}\">. "
                "Insert {{LOGO_MARKUP}} and {{FONT_CSS}}. Canvas 1088×1360.\n"
                f"Exact copy only: {facts['headline']} / {facts['unit']} {facts['unit_label']} / "
                f"{facts['list_price']} / {facts['discount']} {facts['discount_label']} / {facts['cta']}.\n"
                "Semantic tags required: " + ", ".join(SEMANTIC_ROLES) + ".\n"
                f"Doctrine: {json.dumps(doctrine.get('core_rules') or {}, ensure_ascii=True)[:2500]}\n"
                f"Failure lessons: {json.dumps(doctrine.get('failure_lessons') or [], ensure_ascii=True)[:1200]}\n"
                f"Photo analysis: {json.dumps(photo_analysis, default=str)[:2400]}\n"
                f"Reference DNA: {_dna_brief(retrieved)}\n"
                f"Fonts: {font_note}\n"
                "Forbidden: cards, pills, ribbons, medallions, KPI tiles, web buttons, giant opaque panels, "
                "gold swooshes, architecture generation, invented prices/savings/yields.\n"
                "JSON: {reasoning, candidates:[{key, concept, art_direction_reasoning, visual_story, "
                "typography_decision, reference_influences, markup, semantic_elements}]}"
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
    ]
    for item in retrieved[:6]:
        preview = item.get("_preview")
        if isinstance(preview, Image.Image):
            content.append(
                {
                    "type": "text",
                    "text": f"Reference (DNA only, do not copy): {item.get('filename')} / {item.get('reference_id')}",
                }
            )
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(preview)}", "detail": "high"}}
            )
    if logo_preview is not None:
        content.append({"type": "text", "text": "Real Temple logo preview. Insert {{LOGO_MARKUP}}, do not redraw."})
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo_preview)}", "detail": "low"}}
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.55,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Senior art director. Write finished executable HTML/SVG advertisements. "
                    "Three distinct concepts. JSON only. No GPT Image. No architecture invention."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["schema"] = "CreativeConceptSetV2"
    return parsed, calls


def normalize_candidates(concept_set: dict[str, Any], facts: dict[str, str], photo_uri: str) -> list[dict[str, Any]]:
    raw = list(concept_set.get("candidates") or [])
    out: list[dict[str, Any]] = []
    for spec, item in zip(DIRECTIONS, raw + [{}, {}, {}]):
        markup = str(item.get("markup") or "")
        assembled_ok = "{{PHOTO_SRC}}" in markup or "data-semantic=\"project_photo\"" in markup
        scene_id = str(uuid5(NAMESPACE_URL, f"investhome:phase54b:scene:{spec['key']}"))
        gate = validate_scene(assemble_scene(markup, photo_uri=photo_uri, logo_markup="", font_css=""), facts, photo_uri) if markup else {
            "pass": False,
            "flags": ["missing_markup"],
        }
        out.append(
            {
                "key": spec["key"],
                "concept": spec["concept"],
                "intent": spec["intent"],
                "scene_id": scene_id,
                "art_direction_reasoning": item.get("art_direction_reasoning") or concept_set.get("reasoning"),
                "visual_story": item.get("visual_story"),
                "typography_decision": item.get("typography_decision"),
                "reference_influences": item.get("reference_influences") or [],
                "markup": markup,
                "semantic_elements": item.get("semantic_elements") or [],
                "assembled_ok": assembled_ok,
                "scene_gate": gate,
                "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
            }
        )
    return out[:3]


def request_critic_v2(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    concept: str,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1700,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Independent luxury real-estate art director. Score honestly. "
                    "Do not inflate scores to force a pass. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Candidate concept: {concept}. Image 1 is the 4:5 candidate. Image 2 is locked Day_004.\n"
                            "Scores 0-10: professional_art_direction, image_design_integration, composition, typography, "
                            "hierarchy, commercial_clarity, brand_integration, cta_integration, premium_character, "
                            "originality, readability, architecture_respect, visual_restraint, publishability, "
                            "TEXT_ON_PHOTO_FEEL (0 integrated / 10 dumped), TEMPLATE_FEEL (0 bespoke / 10 template), "
                            "UI_FEEL (0 advertising / 10 dashboard), CLUTTER (0 controlled / 10 overloaded). "
                            "Also: anti_patterns (array), critique, notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["mode"] = "vision" if parsed.get("professional_art_direction") is not None else "unavailable"
    return parsed, calls


def critic_targets_met(scores: dict[str, Any]) -> tuple[bool, list[str]]:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key, default))
        except (TypeError, ValueError):
            return default

    reasons: list[str] = []
    mins = {
        "professional_art_direction": 8,
        "image_design_integration": 8,
        "composition": 8,
        "typography": 8,
        "hierarchy": 8,
        "commercial_clarity": 8,
        "brand_integration": 8,
        "premium_character": 8,
        "architecture_respect": 9,
        "publishability": 8,
    }
    maxes = {"TEXT_ON_PHOTO_FEEL": 3, "TEMPLATE_FEEL": 3, "UI_FEEL": 2, "CLUTTER": 4}
    for key, minimum in mins.items():
        if g(key) < minimum:
            reasons.append(f"{key}={g(key)} < {minimum}")
    for key, maximum in maxes.items():
        if g(key, 10) > maximum:
            reasons.append(f"{key}={g(key, 10)} > {maximum}")
    return not reasons, reasons


def scene_id_for(key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"investhome:phase54b:scene:{key}"))


def new_test_id() -> str:
    return str(uuid4())


R1_DIRECTIONS = (
    {
        "key": "A2",
        "concept": "ARCHITECTURAL_EDITORIAL",
        "intent": (
            "Reference-driven editorial art direction. Architecture curated, not covered. "
            "Strong typography. Sophisticated image/empty-space relationship. Readable commerce. "
            "No magazine-cover cliché."
        ),
    },
    {
        "key": "B2",
        "concept": "PREMIUM_CAMPAIGN",
        "intent": (
            "Strongest sales creative. Immediate hierarchy: ALIRKEN KAZAN then the offer. "
            "675.000 USD and %35 LANSMAN AVANTAJI as a designed offer system. "
            "Premium campaign. No white card. No property listing language."
        ),
    },
    {
        "key": "C2",
        "concept": "CONTEMPORARY_LUXURY",
        "intent": (
            "Most contemporary direction. Bolder art direction with professional restraint. "
            "Crop relationships, type scale, controlled graphic fields, asymmetric composition. "
            "Architecture remains recognizable and unchanged."
        ),
    },
)

FORBIDDEN_LAYOUT_PATTERNS = (
    (r"rgba\(\s*255\s*,\s*255\s*,\s*255", "translucent_white_information_rectangle"),
    (r"hsla\(\s*0\s*,\s*0%\s*,\s*100%", "translucent_white_information_rectangle"),
    (r"background(?:-color)?:\s*(?:white|#fff(?:fff)?|#f[5-9a-f]{5})\b", "opaque_information_card"),
    (r"border-radius:\s*(?:[8-9]|\d{2,})", "floating_property_card"),
    (r"box-shadow:", "floating_property_card"),
    (r"bottom:\s*(?:0|[12]?\d)px[^.]{0,120}left:\s*(?:0|[12]?\d)px", "bottom_left_information_dump"),
    (r"<a[\s>]", "web_style_cta"),
    (r"href\s*=", "web_style_cta"),
    (r"text-align:\s*center[\s\S]{0,400}text-align:\s*center", "default_centered_typography"),
)

MOODBOARD_ROLES = ("composition", "typography", "commercial_hierarchy", "image_integration")


def markup_forbidden_reasons(markup: str) -> list[str]:
    text = markup or ""
    folded = text.casefold()
    hits: list[str] = []
    for pattern, code in FORBIDDEN_LAYOUT_PATTERNS:
        if re.search(pattern, folded, flags=re.I | re.S):
            hits.append(code)
    if folded.count("position: absolute") <= 1 and "top: 20px" in folded and "left: 20px" in folded:
        hits.append("stacked_ui_information")
    if "filter:" in folded and "blur(" in folded:
        hits.append("generic_lower_third")
    return sorted(set(hits))


def audit_phase54b_reference_influence(
    candidates: list[dict[str, Any]],
    retrieved: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """ReferenceInfluenceAuditV1 for the rejected 5.4B A/B/C run."""
    retrieved = retrieved or []
    dna_principles: list[str] = []
    for item in retrieved:
        dna = dict(item.get("dna") or {})
        dna_principles.extend(list(dna.get("REUSABLE_PRINCIPLES") or [])[:3])
    human = {
        "A": (
            "logo/headline collide with architecture; tiny unreadable commerce; text placed over photograph"
        ),
        "B": (
            "generic translucent white rectangle / listing card; photo and graphics as separate layers"
        ),
        "C": (
            "weak bottom-left dump; logo loses authority; hierarchy collapses; unused canvas without purpose"
        ),
    }
    rows: list[dict[str, Any]] = []
    for item in candidates:
        key = str(item.get("key") or "")
        claimed = list(item.get("reference_influences") or [])
        markup = str(item.get("markup") or "")
        forbidden = markup_forbidden_reasons(markup)
        actual = "generic overlay layout; claimed DNA not observable in composition"
        if key == "B" or "translucent_white_information_rectangle" in forbidden:
            actual = "white/translucent information card covering negative space"
        elif key == "C" or "bottom_left_information_dump" in forbidden:
            actual = "bottom-left stacked copy dump"
        elif key == "A":
            actual = "top-left stacked type over sky/architecture; commerce collapsed to one line"
        for claim in claimed or ["unspecified generic principle"]:
            rows.append(
                {
                    "reference": "shared DESIGN_REFERENCE pool (same set for A/B/C)",
                    "observed_principle": claim,
                    "planned_application": claim,
                    "actual_application": actual,
                    "result": "FAILURE",
                    "human_verdict": human.get(key, "REJECT"),
                    "forbidden_detected": forbidden,
                }
            )
    return {
        "schema": "ReferenceInfluenceAuditV1",
        "status": "REFERENCES_REDUCED_TO_GENERIC_TEXT_THEN_LOST",
        "visual_conditioning_in_54b": "partial_images_attached_but_three_concepts_generated_in_one_text_dump",
        "retrieved_count": len(retrieved),
        "dna_principles_excerpt": dna_principles[:12],
        "finding": (
            "Design DNA was summarized as generic principles (balance, negative space, hierarchy) "
            "and passed as text. Visual references were attached to a single three-concept call. "
            "Rendered markups ignored those visuals and used default overlay recipes. "
            "Claimed influence is not observable in A/B/C."
        ),
        "rows": rows,
        "human_review": {"A": "REJECT", "B": "REJECT", "C": "REJECT", "promoted": False},
    }


def assign_moodboards(retrieved: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """CreativeMoodboardV1 — distinct 3–5 reference sets per concept."""
    usable = [item for item in retrieved if item.get("reference_id")]
    if len(usable) < 3:
        raise DesignReferencesNotFound("Moodboards require retrieved DESIGN_REFERENCES")
    boards: dict[str, dict[str, Any]] = {}
    offsets = {"A2": 0, "B2": 2, "C2": 4}
    for spec in R1_DIRECTIONS:
        key = spec["key"]
        start = offsets[key] % len(usable)
        picked: list[dict[str, Any]] = []
        seen: set[str] = set()
        i = start
        while len(picked) < min(4, len(usable)):
            item = usable[i % len(usable)]
            rid = str(item.get("reference_id"))
            i += 1
            if rid in seen:
                if i - start > len(usable) * 2:
                    break
                continue
            seen.add(rid)
            role = MOODBOARD_ROLES[len(picked) % len(MOODBOARD_ROLES)]
            blob = dict(item)
            blob["moodboard_role"] = role
            picked.append(blob)
        boards[key] = {
            "schema": "CreativeMoodboardV1",
            "candidate_key": key,
            "concept": spec["concept"],
            "references": picked,
            "roles": {
                item.get("moodboard_role"): item.get("reference_id")
                for item in picked
            },
        }
    sets = [tuple(str(r.get("reference_id")) for r in boards[k]["references"]) for k in ("A2", "B2", "C2")]
    if len(set(sets)) < 2 and len(usable) >= 6:
        raise RuntimeError("Moodboards must not reuse the identical reference set")
    return boards


def request_composition_blueprint(
    *,
    foundation: Image.Image,
    protection: Image.Image,
    photo_analysis: dict[str, Any],
    moodboard: dict[str, Any],
    concept: str,
    intent: str,
    critique: str = "",
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "You are composing WITHOUT advertising copy. Output CompositionBlueprintV2 JSON only.\n"
                f"Concept {concept}: {intent}\n"
                "Image 1 = locked Temple Day_004 photograph. Image 2 = architecture protection map.\n"
                "Following images = DESIGN_REFERENCES. Compare reference design language to Temple photo opportunities.\n"
                "Decide: primary_visual_axis, architecture_protection, negative_space_usage, "
                "graphic_intervention_zones, brand_zone, commercial_zone, cta_relationship, "
                "visual_balance, reading_direction, crop_framing, graphic_fields "
                "(edge extensions / tonal zones — never over the building).\n"
                "Zones as 0-1 boxes {x,y,w,h}. Do NOT place type. Do NOT invent architecture.\n"
                "FORBIDDEN: white cards, listing cards, bottom-left dumps, logo/headline over the spire, "
                "giant empty leftover, generic lower third.\n"
                f"Photo analysis: {json.dumps(photo_analysis, default=str)[:1800]}\n"
                f"{('PREVIOUS COMPOSITION REJECTED: ' + critique) if critique else ''}\n"
                "JSON keys: primary_visual_axis, architecture_protection, negative_space_usage, "
                "graphic_intervention_zones, brand_zone, commercial_zone, cta_relationship, "
                "visual_balance, reading_direction, crop_framing, zones, "
                "reference_applications ([{reference_id, principle, planned_application}]), "
                "why_this_is_not_text_on_photo."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection)}", "detail": "low"}},
    ]
    for item in list(moodboard.get("references") or [])[:5]:
        preview = item.get("_preview")
        if not isinstance(preview, Image.Image):
            continue
        content.append(
            {
                "type": "text",
                "text": (
                    f"REFERENCE VISUAL role={item.get('moodboard_role')} "
                    f"id={item.get('reference_id')} file={item.get('filename')}. "
                    f"DNA: {json.dumps(dict(item.get('dna') or {}), default=str)[:900]}"
                ),
            }
        )
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(preview)}", "detail": "high"}}
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.35,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Senior art director. Solve composition before copy. "
                    "Learn from reference IMAGES, not slogans. JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["schema"] = "CompositionBlueprintV2"
    parsed["concept"] = concept
    return parsed, calls


def request_directed_markup(
    *,
    foundation: Image.Image,
    composition_preview: Image.Image,
    protection: Image.Image,
    logo_preview: Image.Image,
    moodboard: dict[str, Any],
    blueprint: dict[str, Any],
    fonts: dict[str, Any],
    facts: dict[str, str],
    concept: str,
    intent: str,
    critique: str = "",
) -> tuple[dict[str, Any], int]:
    roles = fonts.get("roles") or {}
    font_note = (
        f"DISPLAY {(roles.get('DISPLAY_SERIF') or {}).get('font_file')} / "
        f"COMMERCIAL {(roles.get('COMMERCIAL_NUMBER') or roles.get('DISPLAY_SANS') or {}).get('font_file')} / "
        f"SUPPORT {(roles.get('EDITORIAL_SANS') or {}).get('font_file')} / "
        f"CTA {(roles.get('CTA') or {}).get('font_file')}. "
        "Design DISPLAY, INFORMATION, COMMERCIAL NUMBER, and CTA as four systems. Never DejaVu."
    )
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Insert campaign copy INTO the already-approved composition. Do not restart from a text box.\n"
                f"Concept {concept}: {intent}\n"
                "Images: 1 Temple photo, 2 composition blueprint overlay (no copy), 3 protection map, 4 Temple logo, then references.\n"
                "Photograph MUST remain <img data-semantic=\"project_photo\" src=\"{{PHOTO_SRC}}\">. "
                "Insert {{LOGO_MARKUP}} and {{FONT_CSS}}. Canvas 1088×1360.\n"
                f"Exact copy: {facts['headline']} / {facts['unit']} {facts['unit_label']} / "
                f"{facts['list_price']} / {facts['discount']} {facts['discount_label']} / {facts['cta']}. "
                "Never write $675. Use 675.000 USD. Price is a designed commercial number, not a sentence.\n"
                "CTA is a composed type lockup, not an <a href> or button.\n"
                f"Fonts: {font_note}\n"
                f"Blueprint: {json.dumps({k: blueprint.get(k) for k in ('primary_visual_axis','zones','reference_applications','graphic_intervention_zones','brand_zone','commercial_zone')}, default=str)[:2200]}\n"
                "FORBIDDEN: translucent white rectangle, opaque card, listing card, bottom-left dump, "
                "headline or logo over the Temple spire, tiny commerce, generic lower third, "
                "text dropped on photo, giant unused leftover, web CTA, stacked UI, default centered stack, "
                "automatic logo-in-corner.\n"
                f"{('PREVIOUS DRAFT REJECTED: ' + critique) if critique else ''}\n"
                "JSON: {typography_systems:{display,information,commercial_number,cta}, "
                "reference_applications:[{reference_id,principle,planned_application}], "
                "markup, semantic_elements, why_references_are_visible}."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(composition_preview)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection)}", "detail": "low"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo_preview)}", "detail": "low"}},
    ]
    for item in list(moodboard.get("references") or [])[:5]:
        preview = item.get("_preview")
        if not isinstance(preview, Image.Image):
            continue
        content.append(
            {
                "type": "text",
                "text": f"REFERENCE {item.get('moodboard_role')} {item.get('filename')} {item.get('reference_id')}",
            }
        )
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(preview)}", "detail": "high"}}
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.4,
        "max_tokens": 7000,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "GenerativeCreativeDirectorV2 R1. Reference-grounded art direction. "
                    "Write executable HTML/SVG. JSON only. No GPT Image. No architecture invention."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["schema"] = "DirectedMarkupV2"
    return parsed, calls


def inspect_art_direction_draft(
    *,
    draft: Image.Image,
    foundation: Image.Image,
    moodboard: dict[str, Any],
    concept: str,
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Inspect this {concept} draft. Image 1 = draft. Image 2 = locked photo. Later images = references.\n"
                "Reject if ANY: text collides with architecture; logo collides with architecture; "
                "commercial copy hard to read; listing card; dashboard; mechanically placed type; "
                "image and graphics unrelated; hierarchy not readable in ~2 seconds; "
                "reference influence not visually evident; white/translucent info rectangle; "
                "bottom-left dump; tiny commerce; unused leftover canvas without purpose.\n"
                "JSON: {reject:boolean, reasons:array, hierarchy_ok, architecture_clear, "
                "commerce_readable, reference_influence_visible, notes}."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(draft)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
    ]
    for item in list(moodboard.get("references") or [])[:4]:
        preview = item.get("_preview")
        if isinstance(preview, Image.Image):
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(preview)}", "detail": "low"}}
            )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Strict art-direction inspector. Do not be polite. JSON only."},
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["schema"] = "ArtDirectionInspectV1"
    parsed["reject"] = bool(parsed.get("reject"))
    parsed["reasons"] = list(parsed.get("reasons") or [])
    return parsed, calls

