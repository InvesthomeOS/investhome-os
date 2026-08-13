"""Deterministic Design Ops → draft mutation (no LLM, no DB writes)."""

from __future__ import annotations

import copy
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from investhome_api.schemas.social_design_engine import SocialDesignOp
from investhome_api.services.social_design_engine.layout import (
    VISUAL_LAYOUT_VOCAB,
    align_element_geometry,
    apply_layout_grammar,
    apply_visual_layout_intent,
    auto_layout_text,
    clamp_safe_geometry,
    constrain_element,
    layout_cta_element,
    layout_metric_group,
    layout_text_element,
    reflow_for_format,
    resolve_layout,
    social_layout_slots,
)
from investhome_api.services.social_design_engine.ops import (
    FORMAT_PRESETS,
    canvas_size,
    clamp_int,
    find_element,
    find_post,
    sanitize_color,
    sanitize_creative_copy,
)

PRESET_TO_FORMAT = {
    "square": "feed",
    "portrait": "feed",
    "landscape": "post",
    "story": "story",
    "reelsCover": "reel",
    "carousel": "carousel",
}


def _new_element_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _ensure_elements(post: dict[str, Any]) -> list[dict[str, Any]]:
    elements = post.get("elements")
    if not isinstance(elements, list):
        post["elements"] = []
        return post["elements"]
    return elements


def _sync_copy_fields(post: dict[str, Any]) -> None:
    elements = _ensure_elements(post)
    headline = ""
    caption = ""
    for el in elements:
        if not isinstance(el, dict) or el.get("type") != "TEXT":
            continue
        role = el.get("role")
        content = str(el.get("content") or "")
        if role == "headline" and not headline:
            headline = content
        elif role == "body" and not caption:
            caption = content
    if headline:
        post["headline"] = headline
    if caption:
        post["caption"] = caption


def _strip_layout_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in payload.items()
        if not str(k).startswith("_") and k not in {"maxLines"}
    }


def apply_ops(
    posts: list[dict[str, Any]],
    ops: list[SocialDesignOp],
    *,
    linked_project_id: UUID,
    selected_post_id: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Apply validated ops to a deep-copied draft. Returns (posts, selected_post_id)."""
    working: list[dict[str, Any]] = copy.deepcopy(posts)
    current_selected = selected_post_id
    # Posts that need deterministic layout resolve (create/add/compound edit/format).
    layout_post_ids: set[str] = set()
    grammar_post_ids: set[str] = set()
    text_hints: dict[str, dict[str, dict[str, Any]]] = {}  # post_id -> el_id -> hints
    visual_intents: dict[str, list[str]] = {}  # post_id -> intents
    post_id_remap: dict[str, str] = {}

    for op in ops:
        if op.linked_project_id != linked_project_id:
            continue

        if op.op == "CREATE_POST":
            existing = find_post(working, op.post_id)
            preset = str(op.payload.get("formatPreset") or "square")
            w, h = FORMAT_PRESETS.get(preset, (1080, 1080))
            rebuild = bool(op.payload.get("rebuild"))
            stamp = datetime.now(UTC).isoformat()
            campaign_cid = op.payload.get("campaign_context_id") or op.payload.get("campaignContextId")
            generation_cid = op.payload.get("generation_context_id") or op.payload.get("generationContextId")
            if existing is not None and rebuild:
                # Explicit rebuild (EDIT regenerate) — keep id, replace elements after success.
                existing["elements"] = []
                existing["headline"] = ""
                existing["caption"] = ""
                existing["platform"] = op.payload.get("platform") or existing.get("platform") or "instagram"
                existing["format"] = PRESET_TO_FORMAT.get(preset, existing.get("format") or "feed")
                existing["formatPreset"] = preset
                existing["width"] = w
                existing["height"] = h
                if op.payload.get("name"):
                    existing["name"] = op.payload.get("name")
                if op.payload.get("description") is not None:
                    existing["description"] = str(op.payload.get("description") or "")
                existing["linked_project_id"] = str(linked_project_id)
                if op.payload.get("compositionStrategy"):
                    existing["compositionStrategy"] = op.payload.get("compositionStrategy")
                if op.payload.get("overlayStrategy"):
                    existing["overlayStrategy"] = op.payload.get("overlayStrategy")
                if op.payload.get("textAlign"):
                    existing["textAlign"] = op.payload.get("textAlign")
                if op.payload.get("safeTextZone"):
                    existing["safeTextZone"] = op.payload.get("safeTextZone")
                if op.payload.get("textDensity"):
                    existing["textDensity"] = op.payload.get("textDensity")
                existing["updatedAt"] = stamp
                if campaign_cid:
                    existing["campaignContextId"] = str(campaign_cid)
                    existing["campaign_context_id"] = str(campaign_cid)
                if generation_cid:
                    existing["generationContextId"] = str(generation_cid)
                    existing["generation_context_id"] = str(generation_cid)
                current_selected = op.post_id
                grammar_post_ids.add(op.post_id)
                continue
            if existing is not None and not rebuild:
                # CREATE must not mutate an existing sibling — mint a distinct post
                # and remap follow-on ops onto the new id.
                op_post_id = str(uuid4())
                post_id_remap[op.post_id] = op_post_id
            else:
                op_post_id = op.post_id
            working.append(
                {
                    "id": op_post_id,
                    "platform": op.payload.get("platform") or "instagram",
                    "format": PRESET_TO_FORMAT.get(preset, "feed"),
                    "formatPreset": preset,
                    "width": w,
                    "height": h,
                    "status": "draft",
                    "name": op.payload.get("name") or "AI social post",
                    "description": str(op.payload.get("description") or ""),
                    "headline": "",
                    "caption": "",
                    "coverAssetId": None,
                    "linked_project_id": str(linked_project_id),
                    "elements": [],
                    "compositionStrategy": op.payload.get("compositionStrategy"),
                    "overlayStrategy": op.payload.get("overlayStrategy"),
                    "textAlign": op.payload.get("textAlign"),
                    "safeTextZone": op.payload.get("safeTextZone"),
                    "textDensity": op.payload.get("textDensity"),
                    "campaignContextId": str(campaign_cid) if campaign_cid else None,
                    "campaign_context_id": str(campaign_cid) if campaign_cid else None,
                    "generationContextId": str(generation_cid) if generation_cid else None,
                    "generation_context_id": str(generation_cid) if generation_cid else None,
                    "createdAt": stamp,
                    "updatedAt": stamp,
                }
            )
            current_selected = op_post_id
            grammar_post_ids.add(op_post_id)
            continue

        post_id = post_id_remap.get(op.post_id, op.post_id)
        post = find_post(working, post_id)
        if post is None:
            continue

        post["linked_project_id"] = str(linked_project_id)
        payload = dict(op.payload or {})

        if op.op == "APPLY_LAYOUT_INTENT":
            intent = str(payload.get("intent") or "").upper()
            if intent in VISUAL_LAYOUT_VOCAB:
                visual_intents.setdefault(post_id, []).append(intent)
                layout_post_ids.add(post_id)
            continue

        if op.op == "SET_FORMAT":
            preset = str(payload.get("formatPreset") or "square")
            reflow_for_format(post, preset)
            post["format"] = PRESET_TO_FORMAT.get(preset, "feed")
            grammar_post_ids.add(post_id)
            _sync_copy_fields(post)
            continue

        if op.op == "SET_BACKGROUND":
            asset_id = payload.get("asset_id")
            post["coverAssetId"] = str(asset_id) if asset_id else None
            continue

        if op.op == "ADD_TEXT":
            cw, ch = canvas_size(post)
            role = str(payload.get("role") or "custom").lower()
            if role not in {"headline", "body", "custom", "eyebrow"}:
                role = "custom"
            eid = op.element_id or _new_element_id("text")
            content = sanitize_creative_copy(payload.get("content"), max_len=2000)
            if not content:
                continue
            draft = {
                "id": eid,
                "type": "TEXT",
                "role": role,
                "content": content,
                "fontSize": clamp_int(payload.get("fontSize"), 8, 200, 28),
                "fontWeight": payload.get("fontWeight") or ("bold" if role == "headline" else "normal"),
                "align": payload.get("align") or "center",
                "color": sanitize_color(payload.get("color"), "#ffffff"),
                "zIndex": clamp_int(payload.get("zIndex"), 0, 10_000, 2),
                "x": payload.get("x"),
                "y": payload.get("y"),
                "width": payload.get("width"),
                "height": payload.get("height"),
            }
            slots = social_layout_slots(cw, ch)
            slot = slots.get(role) if role in {"headline", "body"} else None
            if payload.get("x") is None or payload.get("y") is None:
                laid = layout_text_element(draft, canvas_w=cw, canvas_h=ch, slot=slot)
            else:
                geo = clamp_safe_geometry(
                    x=payload.get("x"),
                    y=payload.get("y"),
                    width=payload.get("width", int(cw * 0.84)),
                    height=payload.get("height", 120),
                    canvas_w=cw,
                    canvas_h=ch,
                    full_bleed=False,
                )
                draft.update(geo)
                laid = layout_text_element(
                    draft,
                    canvas_w=cw,
                    canvas_h=ch,
                    slot={
                        "x": geo["x"],
                        "y": geo["y"],
                        "width": geo["width"],
                        "max_height": geo["height"],
                    },
                )
            _ensure_elements(post).append(laid)
            grammar_post_ids.add(post_id)
            _sync_copy_fields(post)
            continue

        if op.op == "ADD_IMAGE":
            cw, ch = canvas_size(post)
            box = min(cw, ch) // 3
            geo = clamp_safe_geometry(
                x=payload.get("x", (cw - box) // 2),
                y=payload.get("y", (ch - box) // 2),
                width=payload.get("width", box),
                height=payload.get("height", box),
                canvas_w=cw,
                canvas_h=ch,
                full_bleed=True,
            )
            eid = op.element_id or _new_element_id("img")
            asset_id = payload.get("asset_id")
            _ensure_elements(post).append(
                {
                    "id": eid,
                    "type": "IMAGE",
                    "assetId": str(asset_id) if asset_id else None,
                    "zIndex": clamp_int(payload.get("zIndex"), 0, 10_000, 1),
                    **geo,
                }
            )
            layout_post_ids.add(post_id)
            continue

        if op.op == "ADD_CTA":
            cw, ch = canvas_size(post)
            eid = op.element_id or _new_element_id("cta")
            label = sanitize_creative_copy(
                payload.get("label") or "Learn more",
                fallback="Learn more",
                max_len=80,
            )
            draft = {
                "id": eid,
                "type": "BUTTON",
                "label": label or "Learn more",
                "backgroundColor": sanitize_color(payload.get("backgroundColor"), "#ffffff"),
                "textColor": sanitize_color(payload.get("textColor"), "#111827"),
                "zIndex": clamp_int(payload.get("zIndex"), 0, 10_000, 4),
                "x": payload.get("x"),
                "y": payload.get("y"),
                "width": payload.get("width"),
                "height": payload.get("height"),
            }
            if payload.get("x") is None or payload.get("y") is None:
                laid = layout_cta_element(draft, canvas_w=cw, canvas_h=ch)
            else:
                geo = constrain_element(
                    {
                        **draft,
                        "x": payload.get("x"),
                        "y": payload.get("y"),
                        "width": payload.get("width", min(cw, max(160, int(cw * 0.38)))),
                        "height": payload.get("height", max(36, int(ch * 0.045))),
                    },
                    canvas_w=cw,
                    canvas_h=ch,
                )
                draft.update(geo)
                laid = draft
            _ensure_elements(post).append(laid)
            grammar_post_ids.add(post_id)
            continue

        if op.op == "ADD_METRIC_GROUP":
            cw, ch = canvas_size(post)
            eid = op.element_id or _new_element_id("metrics")
            from investhome_api.services.social_design_engine.metrics import (
                METRIC_LAYOUTS,
                structured_metrics_from_dicts,
                structured_metrics_to_dicts,
            )

            layout = str(payload.get("layout") or "horizontal").lower()
            if layout not in METRIC_LAYOUTS:
                layout = "horizontal"
            metrics = structured_metrics_to_dicts(
                structured_metrics_from_dicts(payload.get("metrics") if isinstance(payload.get("metrics"), list) else [])
            )
            if not metrics:
                continue
            draft = {
                "id": eid,
                "type": "METRIC_GROUP",
                "role": "metric_group",
                "layout": layout,
                "metrics": metrics,
                "color": sanitize_color(payload.get("color"), "#ffffff"),
                "zIndex": clamp_int(payload.get("zIndex"), 0, 10_000, 4),
                "x": payload.get("x"),
                "y": payload.get("y"),
                "width": payload.get("width"),
                "height": payload.get("height"),
            }
            slots = social_layout_slots(cw, ch)
            slot = slots.get("metric_group") or slots.get("body")
            if payload.get("x") is not None and payload.get("y") is not None:
                slot = None
            laid = layout_metric_group(draft, canvas_w=cw, canvas_h=ch, slot=slot)
            _ensure_elements(post).append(laid)
            grammar_post_ids.add(post_id)
            continue

        if op.op == "DELETE_ELEMENT" and op.element_id:
            elements = _ensure_elements(post)
            post["elements"] = [
                el
                for el in elements
                if not (isinstance(el, dict) and str(el.get("id") or "") == op.element_id)
            ]
            layout_post_ids.add(post_id)
            _sync_copy_fields(post)
            continue

        # APPLY_LAYOUT_INTENT already handled; element-required ops below
        el = find_element(post, op.element_id or "") if op.element_id else None
        if el is None and op.op not in {"SET_BACKGROUND", "SET_FORMAT", "CREATE_POST", "APPLY_LAYOUT_INTENT"}:
            continue

        if op.op == "UPDATE_TEXT" and el is not None:
            if "content" in payload:
                content = sanitize_creative_copy(payload.get("content"), max_len=2000)
                if not content:
                    continue
                el["content"] = content
            if "role" in payload:
                el["role"] = payload["role"]
            if "fontSize" in payload:
                el["fontSize"] = clamp_int(payload.get("fontSize"), 8, 200, el.get("fontSize") or 28)
            if "fontWeight" in payload:
                el["fontWeight"] = (
                    "bold" if str(payload.get("fontWeight") or "").lower() == "bold" else "normal"
                )
            if "align" in payload:
                al = str(payload.get("align") or "").lower()
                if al in {"left", "center", "right"}:
                    el["align"] = al
            if "color" in payload:
                el["color"] = sanitize_color(payload.get("color"), el.get("color") or "#ffffff")
            # Refit box after content/style change — no silent clip
            cw, ch = canvas_size(post)
            fitted = auto_layout_text(
                el,
                canvas_w=cw,
                canvas_h=ch,
                preferred_font=int(el.get("fontSize") or 28),
                max_lines=int(payload["maxLines"]) if payload.get("maxLines") else None,
            )
            el.update(fitted)
            layout_post_ids.add(post_id)
            _sync_copy_fields(post)
            continue

        if op.op == "UPDATE_CTA" and el is not None:
            if el.get("type") not in {"BUTTON", "CTA"}:
                continue
            if "label" in payload:
                label = sanitize_creative_copy(
                    payload.get("label") or "",
                    fallback=str(el.get("label") or "Learn more"),
                    max_len=80,
                )
                if label:
                    el["label"] = label
            if "backgroundColor" in payload:
                el["backgroundColor"] = sanitize_color(payload.get("backgroundColor"))
            if "textColor" in payload:
                el["textColor"] = sanitize_color(payload.get("textColor"), "#111827")
            layout_post_ids.add(post_id)
            continue

        if op.op == "UPDATE_METRIC_GROUP" and el is not None:
            if str(el.get("type") or "").upper() != "METRIC_GROUP":
                continue
            from investhome_api.services.social_design_engine.metrics import (
                METRIC_LAYOUTS,
                apply_compact_currency,
                set_metric_emphasis,
                structured_metrics_from_dicts,
                structured_metrics_to_dicts,
                update_metric_raw_value,
            )

            metrics = structured_metrics_from_dicts(el.get("metrics") if isinstance(el.get("metrics"), list) else [])
            if "layout" in payload:
                layout = str(payload.get("layout") or "").lower()
                if layout in METRIC_LAYOUTS:
                    el["layout"] = layout
            if "metrics" in payload and isinstance(payload.get("metrics"), list):
                incoming = structured_metrics_from_dicts(payload.get("metrics"))
                if incoming:
                    # Preserve raw values unless an explicit raw_value patch is present.
                    if payload.get("allow_raw_update"):
                        metrics = incoming
                    else:
                        by_id = {m.id: m for m in metrics}
                        merged = []
                        for item in incoming:
                            prev = by_id.get(item.id)
                            if prev is None:
                                merged.append(item)
                            else:
                                merged.append(
                                    item.__class__(
                                        id=item.id,
                                        type=item.type,
                                        raw_value=prev.raw_value,
                                        display_value=item.display_value or prev.display_value,
                                        label=item.label or prev.label,
                                        unit=item.unit or prev.unit,
                                        locale=item.locale or prev.locale,
                                        emphasis=item.emphasis,
                                        source_token=prev.source_token,
                                    )
                                )
                        metrics = merged
            if payload.get("emphasis_id"):
                eid_m = str(payload.get("emphasis_id"))
                next_em = str(payload.get("emphasis") or "primary")
                if next_em not in {"primary", "secondary", "tertiary"}:
                    next_em = "primary"
                metrics = [
                    set_metric_emphasis(m, next_em) if m.id == eid_m else m  # type: ignore[arg-type]
                    for m in metrics
                ]
            if payload.get("allow_raw_update") and "raw_value" in payload and payload.get("metric_id"):
                mid = str(payload.get("metric_id"))
                new_raw = payload.get("raw_value")
                metrics = [
                    update_metric_raw_value(m, new_raw) if m.id == mid else m
                    for m in metrics
                ]
            compact = str(el.get("layout") or "") == "horizontal" and len(metrics) >= 3
            metrics = apply_compact_currency(metrics, compact=compact)
            el["metrics"] = structured_metrics_to_dicts(metrics)
            if "color" in payload:
                el["color"] = sanitize_color(payload.get("color"), el.get("color") or "#ffffff")
            cw, ch = canvas_size(post)
            laid = layout_metric_group(el, canvas_w=cw, canvas_h=ch)
            el.update(laid)
            layout_post_ids.add(post_id)
            continue

        if op.op == "REPLACE_IMAGE" and el is not None:
            if el.get("type") != "IMAGE":
                continue
            asset_id = payload.get("asset_id")
            el["assetId"] = str(asset_id) if asset_id else None
            continue

        if op.op == "MOVE_ELEMENT" and el is not None:
            cw, ch = canvas_size(post)
            moved = {
                **el,
                "x": payload.get("x", el.get("x", 0)),
                "y": payload.get("y", el.get("y", 0)),
            }
            geo = constrain_element(moved, canvas_w=cw, canvas_h=ch)
            el["x"] = geo["x"]
            el["y"] = geo["y"]
            if payload.get("_layout_resolve"):
                layout_post_ids.add(post_id)
            continue

        if op.op == "RESIZE_ELEMENT" and el is not None:
            cw, ch = canvas_size(post)
            resized = {
                **el,
                "width": payload.get("width", el.get("width", 100)),
                "height": payload.get("height", el.get("height", 40)),
            }
            geo = constrain_element(resized, canvas_w=cw, canvas_h=ch)
            el.update(geo)
            if el.get("type") == "TEXT":
                fitted = auto_layout_text(
                    el,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=int(el.get("fontSize") or 28),
                    allow_grow_width=False,
                    max_width=geo["width"],
                    max_height=geo["height"],
                )
                # Keep user-requested box; shrink font if needed to avoid clip
                el["fontSize"] = fitted["fontSize"]
                el["width"] = geo["width"]
                el["height"] = max(geo["height"], fitted["height"]) if fitted["height"] > geo["height"] else geo["height"]
                # If font had to shrink and height still overflows, use fitted height clamped
                el.update(constrain_element(el, canvas_w=cw, canvas_h=ch))
            layout_post_ids.add(post_id)
            continue

        if op.op == "ALIGN_ELEMENT" and el is not None:
            cw, ch = canvas_size(post)
            mode = str(payload.get("align") or "center")
            aligned = align_element_geometry(el, mode, canvas_w=cw, canvas_h=ch)
            el.update(aligned)
            layout_post_ids.add(post_id)
            continue

        if op.op == "UPDATE_STYLE" and el is not None:
            clean = _strip_layout_meta(payload)
            for key in ("color", "backgroundColor", "textColor", "fontSize", "fontWeight", "align"):
                if key in clean:
                    el[key] = clean[key]
            if "fontSize" in clean or payload.get("_compound_resize") or payload.get("_one_line"):
                cw, ch = canvas_size(post)
                preferred = clamp_int(el.get("fontSize"), 8, 200, 28)
                max_lines = int(payload["maxLines"]) if payload.get("maxLines") else None
                if payload.get("_one_line"):
                    max_lines = 1
                fitted = auto_layout_text(
                    el,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=preferred,
                    max_lines=max_lines,
                    allow_grow_width=True,
                    allow_grow_height=True,
                )
                el.update(fitted)
                text_hints.setdefault(post_id, {})[str(el.get("id"))] = {
                    "preferred_font": preferred,
                    "max_lines": max_lines,
                }
                layout_post_ids.add(post_id)
            continue

        if op.op == "SET_Z_INDEX" and el is not None:
            el["zIndex"] = clamp_int(payload.get("zIndex"), 0, 10_000, 1)
            continue

    if current_selected and find_post(working, current_selected) is None:
        current_selected = str(working[0]["id"]) if working else None
    elif current_selected is None and working:
        current_selected = str(working[0]["id"])

    # Compound resolve for edits first, then visual vocab so subject/sky placement wins.
    for post in working:
        pid = str(post.get("id") or "")
        if pid in grammar_post_ids:
            apply_layout_grammar(post)
            _sync_copy_fields(post)
        elif pid in layout_post_ids and pid not in visual_intents:
            resolve_layout(post, refit_text=True, text_hints=text_hints.get(pid))
            _sync_copy_fields(post)
        elif pid in layout_post_ids:
            # Resolve collisions/fonts, then apply validated visual language on top.
            resolve_layout(post, refit_text=True, text_hints=text_hints.get(pid))
            for intent in visual_intents.get(pid, []):
                apply_visual_layout_intent(post, intent)
            resolve_layout(post, refit_text=False)
            _sync_copy_fields(post)

    return working, current_selected
