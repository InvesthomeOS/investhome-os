"""AI Design Planner — LLM structured Design Ops + deterministic fallback."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID, uuid4

from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.schemas.social_design_engine import DESIGN_OP_TYPES, SocialDesignMediaCandidate
from investhome_api.services.project_assistant.llm_provider import INSUFFICIENT_EVIDENCE_MESSAGE
from investhome_api.services.social_design_engine.ops import (
    FORMAT_PRESETS,
    find_post,
    looks_like_rag_or_debug_copy,
)

PROMPT_VERSION = "social-design-ops-v1"

SYSTEM_INSTRUCTIONS = """You are the InvestHome OS Social Media Builder AI Design Planner.
You output ONLY a JSON object with a Design Ops array. Never mutate a database.
Never invent Unsplash/stock/mock media. Use only provided Asset UUIDs.

Rules:
- Reply with JSON only: {"ops":[...], "summary":"..."}
- Each op must include: op, linked_project_id, post_id, element_id (null if creating), payload
- ADD_TEXT/UPDATE_TEXT payload must use flat fields: content, role, fontSize, color, x, y, width, height (pixels). Do not nest text under payload.text/style/position.
- ADD_CTA/UPDATE_CTA payload must use label, backgroundColor, textColor, x, y, width, height.
- Allowed ops: {ops}
- CREATE mode: build a complete social post (format, background Asset ID if available, headline TEXT, body TEXT, CTA).
- EDIT mode: emit minimal ops against CURRENT draft (UPDATE_STYLE, UPDATE_TEXT, MOVE_ELEMENT, REPLACE_IMAGE, etc.). Do not full-regenerate unless needed.
- linked_project_id must equal the given project id on every op.
- Asset fields must be real Asset UUIDs from media_candidates or selected_assets.
- If brand_context.available is false, use neutral premium styling (white/dark text) and do not invent brand voice.
- Coordinates are absolute pixels within the post canvas.
- If evidence is insufficient and you cannot ground copy, still return valid structural ops with conservative placeholder copy from verified facts only, or empty ops with summary noting insufficiency.
- CRITICAL — creative copy only: ADD_TEXT/UPDATE_TEXT content and CTA labels must be short human marketing copy (headline/body/CTA).
- NEVER put retrieval/RAG diagnostics into canvas text: no citations, Sources:, metadata.json, chunk IDs, searchable, index, asset_type, versioning, builders, provider/model, Asset ID lists, selection reasoning, document filenames, or evidence JSON keys.
- Evidence and citations stay in the planner context / response meta only — never as on-canvas TEXT/CTA.

Marker for structured output: DESIGN_OPS_JSON
""".replace("{ops}", ", ".join(sorted(DESIGN_OP_TYPES)))

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)
OPS_ARRAY_RE = re.compile(r"\{[\s\S]*\"ops\"\s*:\s*\[[\s\S]*\][\s\S]*\}")


def _clip_facts(facts: list[str], limit: int = 6) -> list[str]:
    out: list[str] = []
    for f in facts:
        text = (f or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        # Convert project_identity key=value rows into readable phrases when present.
        if "=" in text and re.match(
            r"^(project_name|project_code|city|country|address|total_units|project_type|project_status)\s*=",
            text,
            re.I,
        ):
            key, _, val = text.partition("=")
            val = val.strip()
            if not val:
                continue
            key_l = key.strip().lower()
            if key_l == "project_name":
                text = val
            elif key_l == "city":
                text = val
            elif key_l == "address":
                text = val
            elif key_l == "total_units":
                text = f"{val} units"
            else:
                continue
        out.append(text[:280])
        if len(out) >= limit:
            break
    return out


def _marketing_excerpts(retrieved: list[Any], limit: int = 4) -> list[str]:
    """Pull prose snippets from evidence; skip metadata.json / diagnostic blobs."""
    out: list[str] = []
    for row in retrieved:
        if not isinstance(row, dict):
            continue
        name = str(row.get("document_name") or "").lower()
        if "metadata.json" in name or name.endswith(".json"):
            continue
        text = str(row.get("text") or row.get("excerpt") or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        # Prefer sentences that look like marketing prose
        sentence = text.split(".")[0].strip()
        if len(sentence) < 12:
            continue
        out.append(sentence[:280])
        if len(out) >= limit:
            break
    return out


def _headline_from_facts(facts: list[str], project_name: str, language: str | None) -> str:
    for fact in facts:
        if looks_like_rag_or_debug_copy(fact):
            continue
        sentence = fact.split(".")[0].strip()
        if 12 <= len(sentence) <= 90 and not sentence.lower().startswith("project_"):
            return sentence
        if sentence and sentence != project_name and len(sentence) <= 90:
            # Prefer project name over key dumps
            if fact.strip() == project_name or sentence == project_name:
                break
    if (language or "").lower().startswith("tr"):
        return f"{project_name} — özel lansman"
    return f"Discover {project_name}"


def _body_from_facts(facts: list[str], project_name: str, language: str | None) -> str:
    for fact in facts[1:] if len(facts) > 1 else facts:
        if looks_like_rag_or_debug_copy(fact):
            continue
        text = fact.strip()
        if text and text != project_name and len(text) >= 20:
            return text[:320]
    if (language or "").lower().startswith("tr"):
        return f"{project_name} için doğrulanmış proje bilgisiyle hazırlanmış sosyal medya tasarımı."
    return f"Social creative grounded in verified {project_name} project knowledge."


def build_design_prompt(
    *,
    instruction: str,
    mode: str,
    linked_project_id: UUID,
    context: CreativeStudioGenerationContext,
    draft_posts: list[dict[str, Any]],
    selected_post_id: str | None,
    media_candidates: list[SocialDesignMediaCandidate],
    builder_context: dict[str, Any] | None,
    max_prompt_chars: int = 14_000,
) -> tuple[str, str, str]:
    """Return (system, user, prompt_version)."""
    brand = (
        {
            "available": True,
            "excerpts": context.brand_context.excerpts[:5],
            "source_categories": context.brand_context.source_categories,
        }
        if context.brand_context.available
        else {
            "available": False,
            "reason": context.brand_context.reason or "brand_context_unavailable",
            "neutral_premium": True,
        }
    )
    media = [
        {
            "asset_id": str(c.asset_id),
            "filename": c.filename,
            "content_type": c.content_type,
            "folder_category": c.folder_category,
            "score": c.score,
            "tags": c.tags[:8],
        }
        for c in media_candidates[:12]
    ]
    selected = [a.model_dump(mode="json") for a in context.selected_assets]
    # Compact draft for edit mode
    draft_view: list[dict[str, Any]] = []
    for post in draft_posts[:8]:
        draft_view.append(
            {
                "id": post.get("id"),
                "formatPreset": post.get("formatPreset") or post.get("format_preset"),
                "width": post.get("width"),
                "height": post.get("height"),
                "platform": post.get("platform"),
                "name": post.get("name"),
                "coverAssetId": post.get("coverAssetId") or post.get("cover_asset_id"),
                "elements": post.get("elements") if isinstance(post.get("elements"), list) else [],
            }
        )

    evidence = list(context.retrieved_content)[:8]
    user_obj = {
        "mode": mode,
        "linked_project_id": str(linked_project_id),
        "language": context.language,
        "selected_post_id": selected_post_id,
        "instruction": instruction.strip(),
        "project_identity": context.project_identity.model_dump(mode="json"),
        "verified_facts": _clip_facts(context.verified_facts),
        "brand_context": brand,
        "selected_assets": selected,
        "media_candidates": media,
        "builder_context": builder_context or {},
        "current_draft": draft_view,
        "allowed_ops": sorted(DESIGN_OP_TYPES),
    }
    user = (
        "DESIGN_OPS_JSON\n"
        f"{json.dumps(user_obj, ensure_ascii=False)}\n\n"
        f"--- EVIDENCE_START ---\n{json.dumps(evidence, ensure_ascii=False)}\n--- EVIDENCE_END ---\n\n"
        "Return JSON only with ops grounded in the context above."
    )
    system = SYSTEM_INSTRUCTIONS
    while evidence and len(system) + len(user) > max_prompt_chars:
        evidence = evidence[:-1]
        user_obj_trim = dict(user_obj)
        user = (
            "DESIGN_OPS_JSON\n"
            f"{json.dumps(user_obj_trim, ensure_ascii=False)}\n\n"
            f"--- EVIDENCE_START ---\n{json.dumps(evidence, ensure_ascii=False)}\n--- EVIDENCE_END ---\n\n"
            "Return JSON only with ops grounded in the context above."
        )
    return system, user, PROMPT_VERSION


def parse_ops_from_llm(text: str) -> tuple[list[dict[str, Any]], str]:
    """Extract ops array from LLM response. Returns (ops, summary)."""
    raw = (text or "").strip()
    if not raw or raw == INSUFFICIENT_EVIDENCE_MESSAGE:
        return [], "insufficient_context"

    candidates: list[str] = [raw]
    fence = JSON_FENCE_RE.search(raw)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    match = OPS_ARRAY_RE.search(raw)
    if match:
        candidates.insert(0, match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            ops = [o for o in data if isinstance(o, dict)]
            return ops, ""
        if isinstance(data, dict):
            ops_raw = data.get("ops")
            if isinstance(ops_raw, list):
                ops = [o for o in ops_raw if isinstance(o, dict)]
                summary = str(data.get("summary") or "")
                return ops, summary
    return [], "ops_parse_failed"


def _cta_label(language: str | None) -> str:
    if (language or "").lower().startswith("tr"):
        return "Özel tur planla"
    return "Schedule a private tour"


def _detect_format(instruction: str, current: str | None) -> str:
    text = (instruction or "").lower()
    if any(k in text for k in ("story", "hikaye", "hikayesi")):
        return "story"
    if any(k in text for k in ("reel", "reels")):
        return "reelsCover"
    if any(k in text for k in ("landscape", "yatay", "cover")):
        return "landscape"
    if any(k in text for k in ("portrait", "dikey", "4:5", "4/5")):
        return "portrait"
    if any(k in text for k in ("carousel", "karusel")):
        return "carousel"
    if current in FORMAT_PRESETS:
        return current
    return "square"


def build_heuristic_ops(
    *,
    instruction: str,
    mode: str,
    linked_project_id: UUID,
    context: CreativeStudioGenerationContext,
    draft_posts: list[dict[str, Any]],
    selected_post_id: str | None,
    picked_asset_id: UUID | None,
) -> list[dict[str, Any]]:
    """Deterministic create/edit ops when LLM JSON is unavailable (local/mock or parse fail)."""
    pid = str(linked_project_id)
    project_name = context.project_identity.project_name or "Project"
    facts = _clip_facts(context.verified_facts)
    marketing = _marketing_excerpts(list(context.retrieved_content or []))
    # Prefer marketing prose for body; keep identity facts for grounding.
    copy_facts = marketing + [f for f in facts if f not in marketing]
    language = context.language
    headline = _headline_from_facts(copy_facts, project_name, language)
    body = _body_from_facts(copy_facts, project_name, language)
    if looks_like_rag_or_debug_copy(headline):
        headline = (
            f"{project_name} — özel lansman"
            if (language or "").lower().startswith("tr")
            else f"Discover {project_name}"
        )
    if looks_like_rag_or_debug_copy(body):
        body = (
            f"{project_name} için doğrulanmış proje bilgisiyle hazırlanmış sosyal medya tasarımı."
            if (language or "").lower().startswith("tr")
            else f"Social creative grounded in verified {project_name} project knowledge."
        )
    cta = _cta_label(language)
    instr = (instruction or "").lower()

    # -------- EDIT MODE --------
    if mode == "edit":
        post = None
        if selected_post_id:
            post = find_post(draft_posts, selected_post_id)
        if post is None and draft_posts:
            post = draft_posts[0]
        if post is None:
            mode = "create"
        else:
            post_id = str(post.get("id"))
            ops: list[dict[str, Any]] = []
            elements = post.get("elements") if isinstance(post.get("elements"), list) else []

            # Style color change
            color_match = re.search(r"#([0-9a-fA-F]{3,8})\b", instruction or "")
            wants_white = any(k in instr for k in ("beyaz", "white", "açık"))
            wants_dark = any(k in instr for k in ("siyah", "dark", "black"))
            target_color = None
            if color_match:
                target_color = f"#{color_match.group(1)}"
            elif wants_white:
                target_color = "#ffffff"
            elif wants_dark:
                target_color = "#0f172a"

            if target_color:
                for el in elements:
                    if isinstance(el, dict) and el.get("type") == "TEXT":
                        ops.append(
                            {
                                "op": "UPDATE_STYLE",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"color": target_color},
                            }
                        )

            # Replace / set background image
            if any(k in instr for k in ("görsel", "image", "foto", "photo", "background", "arka plan", "değiştir", "replace")):
                if picked_asset_id:
                    ops.append(
                        {
                            "op": "SET_BACKGROUND",
                            "linked_project_id": pid,
                            "post_id": post_id,
                            "element_id": None,
                            "payload": {"asset_id": str(picked_asset_id)},
                        }
                    )
                    for el in elements:
                        if isinstance(el, dict) and el.get("type") == "IMAGE":
                            ops.append(
                                {
                                    "op": "REPLACE_IMAGE",
                                    "linked_project_id": pid,
                                    "post_id": post_id,
                                    "element_id": el.get("id"),
                                    "payload": {"asset_id": str(picked_asset_id)},
                                }
                            )
                            break

            # Text updates
            if any(k in instr for k in ("başlık", "headline", "title", "metin", "caption", "yazı", "cta", "buton")):
                for el in elements:
                    if not isinstance(el, dict):
                        continue
                    if el.get("type") == "TEXT" and el.get("role") == "headline" and any(
                        k in instr for k in ("başlık", "headline", "title")
                    ):
                        ops.append(
                            {
                                "op": "UPDATE_TEXT",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"content": headline},
                            }
                        )
                    if el.get("type") == "TEXT" and el.get("role") == "body" and any(
                        k in instr for k in ("caption", "metin", "body", "açıklama")
                    ):
                        ops.append(
                            {
                                "op": "UPDATE_TEXT",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"content": body},
                            }
                        )
                    if el.get("type") in {"BUTTON", "CTA"} and any(
                        k in instr for k in ("cta", "buton", "button")
                    ):
                        ops.append(
                            {
                                "op": "UPDATE_CTA",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"label": cta},
                            }
                        )

            # Move / align
            if any(k in instr for k in ("ortala", "center", "align")):
                for el in elements:
                    if isinstance(el, dict) and el.get("type") == "TEXT" and el.get("role") == "headline":
                        ops.append(
                            {
                                "op": "ALIGN_ELEMENT",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"align": "center"},
                            }
                        )
                        break

            if any(k in instr for k in ("yukarı", "up", "aşağı", "down", "taşı", "move")):
                for el in elements:
                    if isinstance(el, dict) and el.get("type") == "TEXT" and el.get("role") == "headline":
                        y = int(el.get("y") or 0)
                        dy = -40 if any(k in instr for k in ("yukarı", "up")) else 40
                        ops.append(
                            {
                                "op": "MOVE_ELEMENT",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"x": el.get("x", 0), "y": max(0, y + dy)},
                            }
                        )
                        break

            # Format change
            new_format = _detect_format(instruction, str(post.get("formatPreset") or "square"))
            if new_format != str(post.get("formatPreset") or "") and any(
                k in instr for k in ("format", "story", "portrait", "landscape", "square", "reel")
            ):
                ops.append(
                    {
                        "op": "SET_FORMAT",
                        "linked_project_id": pid,
                        "post_id": post_id,
                        "element_id": None,
                        "payload": {"formatPreset": new_format},
                    }
                )

            if ops:
                return ops
            # Fallback edit: refresh copy on existing elements
            for el in elements:
                if not isinstance(el, dict):
                    continue
                if el.get("type") == "TEXT" and el.get("role") == "headline":
                    ops.append(
                        {
                            "op": "UPDATE_TEXT",
                            "linked_project_id": pid,
                            "post_id": post_id,
                            "element_id": el.get("id"),
                            "payload": {"content": headline},
                        }
                    )
                elif el.get("type") == "TEXT" and el.get("role") == "body":
                    ops.append(
                        {
                            "op": "UPDATE_TEXT",
                            "linked_project_id": pid,
                            "post_id": post_id,
                            "element_id": el.get("id"),
                            "payload": {"content": body},
                        }
                    )
            return ops

    # -------- CREATE MODE --------
    post_id = str(uuid4())
    preset = _detect_format(instruction, None)
    w, h = FORMAT_PRESETS[preset]
    pad_x = int(w * 0.08)
    content_w = max(40, w - pad_x * 2)
    headline_size = max(22, int(w * 0.055))
    body_size = max(14, int(w * 0.028))
    cta_h = max(36, int(h * 0.045))
    cta_w = min(content_w, max(160, int(w * 0.38)))

    ops = [
        {
            "op": "CREATE_POST",
            "linked_project_id": pid,
            "post_id": post_id,
            "element_id": None,
            "payload": {
                "formatPreset": preset,
                "platform": "instagram",
                "name": f"AI {preset}",
                "description": instruction[:240],
            },
        },
        {
            "op": "SET_FORMAT",
            "linked_project_id": pid,
            "post_id": post_id,
            "element_id": None,
            "payload": {"formatPreset": preset},
        },
    ]
    if picked_asset_id:
        ops.append(
            {
                "op": "SET_BACKGROUND",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {"asset_id": str(picked_asset_id)},
            }
        )
        ops.append(
            {
                "op": "ADD_IMAGE",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {
                    "asset_id": str(picked_asset_id),
                    "x": int((w - min(w, h) * 0.35) / 2),
                    "y": int(h * 0.12),
                    "width": int(min(w, h) * 0.35),
                    "height": int(min(w, h) * 0.35),
                    "zIndex": 1,
                },
            }
        )

    ops.extend(
        [
            {
                "op": "ADD_TEXT",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {
                    "role": "headline",
                    "content": headline,
                    "fontSize": headline_size,
                    "fontWeight": "bold",
                    "align": "center",
                    "color": "#ffffff",
                    "x": pad_x,
                    "y": int(h * 0.68),
                    "width": content_w,
                    "height": int(headline_size * 2.4),
                    "zIndex": 2,
                },
            },
            {
                "op": "ADD_TEXT",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {
                    "role": "body",
                    "content": body,
                    "fontSize": body_size,
                    "fontWeight": "normal",
                    "align": "center",
                    "color": "#ffffff",
                    "x": pad_x,
                    "y": int(h * 0.78),
                    "width": content_w,
                    "height": int(body_size * 3.2),
                    "zIndex": 3,
                },
            },
            {
                "op": "ADD_CTA",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {
                    "label": cta,
                    "backgroundColor": "#ffffff",
                    "textColor": "#111827",
                    "x": int((w - cta_w) / 2),
                    "y": int(h * 0.88),
                    "width": cta_w,
                    "height": cta_h,
                    "zIndex": 4,
                },
            },
        ]
    )
    return ops
