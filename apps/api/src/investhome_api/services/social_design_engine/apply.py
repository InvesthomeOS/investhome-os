"""Deterministic Design Ops → draft mutation (no LLM, no DB writes)."""

from __future__ import annotations

import copy
import time
from typing import Any
from uuid import UUID

from investhome_api.schemas.social_design_engine import SocialDesignOp
from investhome_api.services.social_design_engine.ops import (
    FORMAT_PRESETS,
    canvas_size,
    clamp_geometry,
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
    return f"{prefix}-{int(time.time() * 1000)}-{abs(hash(prefix)) % 100000}"


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

    for op in ops:
        if op.linked_project_id != linked_project_id:
            continue

        if op.op == "CREATE_POST":
            existing = find_post(working, op.post_id)
            if existing is not None:
                current_selected = op.post_id
                continue
            preset = str(op.payload.get("formatPreset") or "square")
            w, h = FORMAT_PRESETS.get(preset, (1080, 1080))
            working.append(
                {
                    "id": op.post_id,
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
                }
            )
            current_selected = op.post_id
            continue

        post = find_post(working, op.post_id)
        if post is None:
            continue

        post["linked_project_id"] = str(linked_project_id)

        if op.op == "SET_FORMAT":
            preset = str(op.payload.get("formatPreset") or "square")
            w, h = FORMAT_PRESETS.get(preset, (1080, 1080))
            post["formatPreset"] = preset
            post["width"] = w
            post["height"] = h
            post["format"] = PRESET_TO_FORMAT.get(preset, "feed")
            continue

        if op.op == "SET_BACKGROUND":
            asset_id = op.payload.get("asset_id")
            post["coverAssetId"] = str(asset_id) if asset_id else None
            continue

        if op.op == "ADD_TEXT":
            cw, ch = canvas_size(post)
            geo = clamp_geometry(
                x=op.payload.get("x", int(cw * 0.08)),
                y=op.payload.get("y", int(ch * 0.68)),
                width=op.payload.get("width", int(cw * 0.84)),
                height=op.payload.get("height", 120),
                canvas_w=cw,
                canvas_h=ch,
            )
            eid = op.element_id or _new_element_id("text")
            content = sanitize_creative_copy(op.payload.get("content"), max_len=2000)
            if not content:
                continue
            _ensure_elements(post).append(
                {
                    "id": eid,
                    "type": "TEXT",
                    "role": op.payload.get("role") or "custom",
                    "content": content,
                    "fontSize": clamp_int(op.payload.get("fontSize"), 8, 200, 28),
                    "fontWeight": op.payload.get("fontWeight") or "normal",
                    "align": op.payload.get("align") or "center",
                    "color": sanitize_color(op.payload.get("color"), "#ffffff"),
                    "zIndex": clamp_int(op.payload.get("zIndex"), 0, 10_000, 2),
                    **geo,
                }
            )
            _sync_copy_fields(post)
            continue

        if op.op == "ADD_IMAGE":
            cw, ch = canvas_size(post)
            box = min(cw, ch) // 3
            geo = clamp_geometry(
                x=op.payload.get("x", (cw - box) // 2),
                y=op.payload.get("y", (ch - box) // 2),
                width=op.payload.get("width", box),
                height=op.payload.get("height", box),
                canvas_w=cw,
                canvas_h=ch,
            )
            eid = op.element_id or _new_element_id("img")
            asset_id = op.payload.get("asset_id")
            _ensure_elements(post).append(
                {
                    "id": eid,
                    "type": "IMAGE",
                    "assetId": str(asset_id) if asset_id else None,
                    "zIndex": clamp_int(op.payload.get("zIndex"), 0, 10_000, 1),
                    **geo,
                }
            )
            continue

        if op.op == "ADD_CTA":
            cw, ch = canvas_size(post)
            btn_w = min(cw, max(160, int(cw * 0.38)))
            btn_h = max(36, int(ch * 0.045))
            geo = clamp_geometry(
                x=op.payload.get("x", (cw - btn_w) // 2),
                y=op.payload.get("y", int(ch * 0.88)),
                width=op.payload.get("width", btn_w),
                height=op.payload.get("height", btn_h),
                canvas_w=cw,
                canvas_h=ch,
            )
            eid = op.element_id or _new_element_id("cta")
            label = sanitize_creative_copy(
                op.payload.get("label") or "Learn more",
                fallback="Learn more",
                max_len=80,
            )
            _ensure_elements(post).append(
                {
                    "id": eid,
                    "type": "BUTTON",
                    "label": label or "Learn more",
                    "backgroundColor": sanitize_color(
                        op.payload.get("backgroundColor"), "#ffffff"
                    ),
                    "textColor": sanitize_color(op.payload.get("textColor"), "#111827"),
                    "zIndex": clamp_int(op.payload.get("zIndex"), 0, 10_000, 4),
                    **geo,
                }
            )
            continue

        if op.op == "DELETE_ELEMENT" and op.element_id:
            elements = _ensure_elements(post)
            post["elements"] = [
                el
                for el in elements
                if not (isinstance(el, dict) and str(el.get("id") or "") == op.element_id)
            ]
            _sync_copy_fields(post)
            continue

        el = find_element(post, op.element_id or "") if op.element_id else None
        if el is None:
            continue

        if op.op == "UPDATE_TEXT":
            if "content" in op.payload:
                content = sanitize_creative_copy(op.payload.get("content"), max_len=2000)
                if not content:
                    continue
                el["content"] = content
            if "role" in op.payload:
                el["role"] = op.payload["role"]
            _sync_copy_fields(post)
            continue

        if op.op == "UPDATE_CTA":
            if el.get("type") not in {"BUTTON", "CTA"}:
                continue
            if "label" in op.payload:
                label = sanitize_creative_copy(
                    op.payload.get("label") or "",
                    fallback=str(el.get("label") or "Learn more"),
                    max_len=80,
                )
                if label:
                    el["label"] = label
            if "backgroundColor" in op.payload:
                el["backgroundColor"] = sanitize_color(op.payload.get("backgroundColor"))
            if "textColor" in op.payload:
                el["textColor"] = sanitize_color(op.payload.get("textColor"), "#111827")
            continue

        if op.op == "REPLACE_IMAGE":
            if el.get("type") != "IMAGE":
                # Allow SET_BACKGROUND-like replacement when targeting cover via REPLACE on IMAGE only
                continue
            asset_id = op.payload.get("asset_id")
            el["assetId"] = str(asset_id) if asset_id else None
            continue

        if op.op == "MOVE_ELEMENT":
            cw, ch = canvas_size(post)
            geo = clamp_geometry(
                x=op.payload.get("x", el.get("x", 0)),
                y=op.payload.get("y", el.get("y", 0)),
                width=el.get("width", 100),
                height=el.get("height", 40),
                canvas_w=cw,
                canvas_h=ch,
            )
            el["x"] = geo["x"]
            el["y"] = geo["y"]
            continue

        if op.op == "RESIZE_ELEMENT":
            cw, ch = canvas_size(post)
            geo = clamp_geometry(
                x=el.get("x", 0),
                y=el.get("y", 0),
                width=op.payload.get("width", el.get("width", 100)),
                height=op.payload.get("height", el.get("height", 40)),
                canvas_w=cw,
                canvas_h=ch,
            )
            el.update(geo)
            continue

        if op.op == "ALIGN_ELEMENT":
            cw, ch = canvas_size(post)
            mode = str(op.payload.get("align") or "center")
            w = clamp_int(el.get("width"), 8, cw, 100)
            h = clamp_int(el.get("height"), 8, ch, 40)
            if mode == "left":
                el["x"] = 0
                if el.get("type") == "TEXT":
                    el["align"] = "left"
            elif mode == "right":
                el["x"] = max(0, cw - w)
                if el.get("type") == "TEXT":
                    el["align"] = "right"
            elif mode == "center":
                el["x"] = max(0, (cw - w) // 2)
                if el.get("type") == "TEXT":
                    el["align"] = "center"
            elif mode == "vcenter":
                el["y"] = max(0, (ch - h) // 2)
            continue

        if op.op == "UPDATE_STYLE":
            for key in ("color", "backgroundColor", "textColor", "fontSize", "fontWeight", "align"):
                if key in op.payload:
                    el[key] = op.payload[key]
            continue

        if op.op == "SET_Z_INDEX":
            el["zIndex"] = clamp_int(op.payload.get("zIndex"), 0, 10_000, 1)
            continue

    if current_selected and find_post(working, current_selected) is None:
        current_selected = str(working[0]["id"]) if working else None
    elif current_selected is None and working:
        current_selected = str(working[0]["id"])

    return working, current_selected
