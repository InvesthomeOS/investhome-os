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

PROMPT_VERSION = "social-design-ops-v3"

SYSTEM_INSTRUCTIONS = """You are the InvestHome OS Social Media Builder AI Design Planner.
You output ONLY a JSON object with a Design Ops array. Never mutate a database.
Never invent Unsplash/stock/mock media. Use only provided Asset UUIDs.

Rules:
- Reply with JSON only: {"ops":[...], "summary":"..."}
- Each op must include: op, linked_project_id, post_id, element_id (null if creating), payload
- ADD_TEXT/UPDATE_TEXT payload: content, role (headline|body|custom), optional fontSize/color/fontWeight/align.
  Do NOT invent unrestricted x/y/width/height pixels — the server applies a safe layout grammar.
- ADD_CTA/UPDATE_CTA payload: label, optional backgroundColor/textColor. Do NOT invent free pixel geometry.
- Allowed ops: {ops}
- CREATE mode: build a complete social post (format, background Asset ID if available, headline TEXT, body TEXT, CTA).
  Layout grammar (server): full-bleed background → overlay → HEADLINE upper/middle → BODY below → CTA lower safe region.
- EDIT mode: emit ONLY the minimal ops requested. Do not full-regenerate.
- EDIT COPY PROTECTION (critical):
  Existing headline, body, and CTA label are IMMUTABLE by default.
  NEVER emit UPDATE_TEXT with new content or UPDATE_CTA with a new label unless the user
  EXPLICITLY asks to change wording/copy (e.g. "başlığı şuna çevir", "rewrite headline", "CTA olsun …").
  Spatial language is MOVE, not copy: "üste/aşağı/sola/sağa/ortala/mavi buluta al/taşı" → MOVE_ELEMENT only.
  "küçült/büyüt" → UPDATE_STYLE fontSize or RESIZE_ELEMENT — keep existing text unchanged.
  "başka görsel/exterior/render" → REPLACE_IMAGE / SET_BACKGROUND — keep all copy unchanged.
- Target mapping: başlık→headline TEXT, body/açıklama→body TEXT, CTA/buton→BUTTON, görsel/arka plan→IMAGE.
  Do not ADD duplicate headline/body/CTA when the target already exists — UPDATE/MOVE existing element_id.
- If builder_context.selected_element (or selectedElementId) is present and the user says
  "bunu/this/şunu/onu" or does not name another element, edit ONLY that selected element_id.
- linked_project_id must equal the given project id on every op.
- Asset fields must be real Asset UUIDs from media_candidates or selected_assets.
- If brand_context.available is false, use neutral premium styling (white/dark text) and do not invent brand voice.
- Canvas is format-canonical pixels (square=1080×1080, portrait=1080×1350, story=1080×1920, etc.). Never use browser CSS pixels.
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


def _cta_label(language: str | None, instruction: str = "") -> str:
    instr = (instruction or "").lower()
    invest = any(k in instr for k in ("yatırım", "invest", "investor", "opportunity", "fırsat"))
    if invest:
        if (language or "").lower().startswith("tr"):
            return "Yatırım fırsatını incele"
        return "Explore the investment"
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
    cta = _cta_label(language, instruction)
    instr = (instruction or "").lower()

    # -------- EDIT MODE --------
    if mode == "edit":
        from investhome_api.services.social_design_engine.intent import (
            build_ops_from_intent_plan,
            classify_edit_intents,
            enrich_color_intents,
        )

        post = None
        if selected_post_id:
            post = find_post(draft_posts, selected_post_id)
        if post is None and draft_posts:
            post = draft_posts[0]
        if post is None:
            mode = "create"
        else:
            post_id = str(post.get("id"))
            plan = enrich_color_intents(classify_edit_intents(instruction), instruction)
            ops = build_ops_from_intent_plan(
                plan=plan,
                linked_project_id=pid,
                post=post,
                picked_asset_id=picked_asset_id,
            )

            # Explicit copy intents only — never refresh wording as a fallback.
            if plan.allow_copy_rewrite:
                elements = post.get("elements") if isinstance(post.get("elements"), list) else []
                for item in plan.intents:
                    if item.intent != "CHANGE_TEXT":
                        continue
                    for el in elements:
                        if not isinstance(el, dict) or el.get("type") != "TEXT":
                            continue
                        role = el.get("role")
                        if item.target == "headline" and role == "headline":
                            ops.append(
                                {
                                    "op": "UPDATE_TEXT",
                                    "linked_project_id": pid,
                                    "post_id": post_id,
                                    "element_id": el.get("id"),
                                    "payload": {"content": headline},
                                    "_intent": "CHANGE_TEXT",
                                    "_target": "headline",
                                }
                            )
                        elif item.target == "body" and role == "body":
                            ops.append(
                                {
                                    "op": "UPDATE_TEXT",
                                    "linked_project_id": pid,
                                    "post_id": post_id,
                                    "element_id": el.get("id"),
                                    "payload": {"content": body},
                                    "_intent": "CHANGE_TEXT",
                                    "_target": "body",
                                }
                            )
            if plan.allow_cta_rewrite:
                elements = post.get("elements") if isinstance(post.get("elements"), list) else []
                for el in elements:
                    if isinstance(el, dict) and el.get("type") in {"BUTTON", "CTA"}:
                        ops.append(
                            {
                                "op": "UPDATE_CTA",
                                "linked_project_id": pid,
                                "post_id": post_id,
                                "element_id": el.get("id"),
                                "payload": {"label": cta},
                                "_intent": "CHANGE_CTA_TEXT",
                                "_target": "cta",
                            }
                        )
                        break

            # Format change (explicit)
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

            return ops

    # -------- CREATE MODE --------
    post_id = str(uuid4())
    preset = _detect_format(instruction, None)

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

    # Content + style intent only — server layout grammar owns safe geometry / text fit.
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
                    "fontWeight": "bold",
                    "align": "center",
                    "color": "#ffffff",
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
                    "fontWeight": "normal",
                    "align": "center",
                    "color": "#ffffff",
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
                    "zIndex": 4,
                },
            },
        ]
    )
    return ops
