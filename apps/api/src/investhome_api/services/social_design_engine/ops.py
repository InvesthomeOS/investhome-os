"""Design Ops validation and geometry/style clamping (P0)."""

from __future__ import annotations

import re
import time
from typing import Any
from uuid import UUID

from investhome_api.schemas.social_design_engine import DESIGN_OP_TYPES, SocialDesignOp

FORMAT_PRESETS: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "landscape": (1920, 1080),
    "story": (1080, 1920),
    "reelsCover": (1080, 1920),
    "carousel": (1080, 1080),
}

OPS_REQUIRING_ELEMENT = frozenset(
    {
        "UPDATE_TEXT",
        "DELETE_ELEMENT",
        "REPLACE_IMAGE",
        "UPDATE_CTA",
        "MOVE_ELEMENT",
        "RESIZE_ELEMENT",
        "ALIGN_ELEMENT",
        "UPDATE_STYLE",
        "SET_Z_INDEX",
    }
)

OPS_CREATING_ELEMENT = frozenset({"ADD_TEXT", "ADD_IMAGE", "ADD_CTA"})

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)

HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def clamp_float(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def sanitize_color(value: Any, default: str = "#ffffff") -> str:
    if isinstance(value, str) and HEX_COLOR_RE.match(value.strip()):
        return value.strip()
    return default


def is_uuid_str(value: Any) -> bool:
    return isinstance(value, str) and bool(UUID_RE.match(value.strip()))


def parse_asset_id(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if is_uuid_str(value):
        return UUID(str(value).strip())
    return None


def find_post(posts: list[dict[str, Any]], post_id: str) -> dict[str, Any] | None:
    for post in posts:
        if str(post.get("id") or "") == post_id:
            return post
    return None


def find_element(post: dict[str, Any], element_id: str) -> dict[str, Any] | None:
    elements = post.get("elements")
    if not isinstance(elements, list):
        return None
    for el in elements:
        if isinstance(el, dict) and str(el.get("id") or "") == element_id:
            return el
    return None


def canvas_size(post: dict[str, Any]) -> tuple[int, int]:
    preset = str(post.get("formatPreset") or post.get("format_preset") or "square")
    if preset in FORMAT_PRESETS:
        return FORMAT_PRESETS[preset]
    w = clamp_int(post.get("width"), 1, 4096, 1080)
    h = clamp_int(post.get("height"), 1, 4096, 1080)
    return w, h


def clamp_geometry(
    *,
    x: Any,
    y: Any,
    width: Any,
    height: Any,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, int]:
    w = clamp_int(width, 8, canvas_w, min(200, canvas_w))
    h = clamp_int(height, 8, canvas_h, min(80, canvas_h))
    max_x = max(0, canvas_w - w)
    max_y = max(0, canvas_h - h)
    return {
        "x": clamp_int(x, 0, max_x, 0),
        "y": clamp_int(y, 0, max_y, 0),
        "width": w,
        "height": h,
    }


class OpValidationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_op(
    raw: Any,
    *,
    linked_project_id: UUID,
    posts: list[dict[str, Any]],
    allowed_asset_ids: set[UUID],
) -> SocialDesignOp:
    if not isinstance(raw, dict):
        raise OpValidationError("op_must_be_object")

    op_name = str(raw.get("op") or "").strip().upper()
    if op_name not in DESIGN_OP_TYPES:
        raise OpValidationError(f"unknown_op:{op_name or 'missing'}")

    op_project = raw.get("linked_project_id")
    try:
        op_linked = UUID(str(op_project)) if op_project is not None else None
    except (TypeError, ValueError) as exc:
        raise OpValidationError("invalid_linked_project_id") from exc
    if op_linked is None or op_linked != linked_project_id:
        raise OpValidationError("linked_project_id_mismatch")

    post_id = str(raw.get("post_id") or "").strip()
    if not post_id:
        raise OpValidationError("post_id_required")

    if op_name != "CREATE_POST":
        post = find_post(posts, post_id)
        if post is None:
            raise OpValidationError(f"post_not_found:{post_id}")
    else:
        post = find_post(posts, post_id)

    element_id_raw = raw.get("element_id")
    element_id = (
        str(element_id_raw).strip()
        if isinstance(element_id_raw, str) and element_id_raw.strip()
        else None
    )

    if op_name in OPS_REQUIRING_ELEMENT:
        if not element_id:
            raise OpValidationError("element_id_required")
        assert post is not None
        if find_element(post, element_id) is None:
            raise OpValidationError(f"element_not_found:{element_id}")

    payload_raw = raw.get("payload")
    payload: dict[str, Any] = dict(payload_raw) if isinstance(payload_raw, dict) else {}

    # Reject raw media URLs in asset fields
    for key in ("asset_id", "assetId", "cover_asset_id", "coverAssetId"):
        if key in payload:
            val = payload[key]
            if isinstance(val, str) and (
                val.startswith("http://")
                or val.startswith("https://")
                or "unsplash" in val.lower()
                or "drive.google" in val.lower()
            ):
                raise OpValidationError("forbidden_media_url")
            aid = parse_asset_id(val)
            if val is not None and aid is None:
                raise OpValidationError("invalid_asset_id")
            if aid is not None and aid not in allowed_asset_ids:
                raise OpValidationError(f"asset_not_allowed:{aid}")
            if aid is not None:
                payload["asset_id"] = str(aid)
                payload.pop("assetId", None)
                payload.pop("coverAssetId", None)
                payload.pop("cover_asset_id", None)

    if op_name == "SET_FORMAT":
        preset = str(payload.get("formatPreset") or payload.get("format_preset") or "").strip()
        if preset not in FORMAT_PRESETS:
            raise OpValidationError("invalid_format_preset")
        payload["formatPreset"] = preset

    if op_name == "ALIGN_ELEMENT":
        mode = str(payload.get("align") or payload.get("mode") or "").strip().lower()
        if mode not in {"left", "center", "right", "vcenter"}:
            raise OpValidationError("invalid_align_mode")
        payload["align"] = mode

    if op_name == "UPDATE_STYLE":
        if "color" in payload:
            payload["color"] = sanitize_color(payload.get("color"), "#ffffff")
        if "backgroundColor" in payload:
            payload["backgroundColor"] = sanitize_color(payload.get("backgroundColor"), "#ffffff")
        if "textColor" in payload:
            payload["textColor"] = sanitize_color(payload.get("textColor"), "#111827")
        if "fontSize" in payload:
            payload["fontSize"] = clamp_int(payload.get("fontSize"), 8, 200, 24)
        if "fontWeight" in payload:
            fw = str(payload.get("fontWeight") or "").lower()
            payload["fontWeight"] = "bold" if fw == "bold" else "normal"
        if "align" in payload:
            al = str(payload.get("align") or "").lower()
            if al not in {"left", "center", "right"}:
                raise OpValidationError("invalid_text_align")
            payload["align"] = al

    if op_name in {"MOVE_ELEMENT", "RESIZE_ELEMENT", "ADD_TEXT", "ADD_IMAGE", "ADD_CTA"}:
        assert post is not None or op_name == "CREATE_POST"
        target = post or {"width": 1080, "height": 1080, "formatPreset": "square"}
        cw, ch = canvas_size(target)
        geo = clamp_geometry(
            x=payload.get("x", 0),
            y=payload.get("y", 0),
            width=payload.get("width", min(400, cw)),
            height=payload.get("height", min(80, ch)),
            canvas_w=cw,
            canvas_h=ch,
        )
        payload.update(geo)

    if op_name == "SET_Z_INDEX":
        payload["zIndex"] = clamp_int(payload.get("zIndex", payload.get("z_index", 1)), 0, 10_000, 1)

    if op_name == "ADD_TEXT":
        role = str(payload.get("role") or "custom").lower()
        if role not in {"headline", "body", "custom"}:
            role = "custom"
        payload["role"] = role
        payload["content"] = str(payload.get("content") or "")[:2000]
        payload["fontSize"] = clamp_int(payload.get("fontSize"), 8, 200, 28)
        payload["fontWeight"] = (
            "bold" if str(payload.get("fontWeight") or "").lower() == "bold" else "normal"
        )
        al = str(payload.get("align") or "center").lower()
        payload["align"] = al if al in {"left", "center", "right"} else "center"
        payload["color"] = sanitize_color(payload.get("color"), "#ffffff")

    if op_name == "UPDATE_TEXT":
        if "content" in payload:
            payload["content"] = str(payload.get("content") or "")[:2000]
        if "role" in payload:
            role = str(payload.get("role") or "").lower()
            if role in {"headline", "body", "custom"}:
                payload["role"] = role

    if op_name in {"ADD_CTA", "UPDATE_CTA"}:
        if "label" in payload or op_name == "ADD_CTA":
            payload["label"] = str(payload.get("label") or "Learn more")[:80]
        if "backgroundColor" in payload or op_name == "ADD_CTA":
            payload["backgroundColor"] = sanitize_color(
                payload.get("backgroundColor"), "#ffffff"
            )
        if "textColor" in payload or op_name == "ADD_CTA":
            payload["textColor"] = sanitize_color(payload.get("textColor"), "#111827")

    if op_name == "CREATE_POST":
        preset = str(payload.get("formatPreset") or payload.get("format_preset") or "square")
        if preset not in FORMAT_PRESETS:
            preset = "square"
        payload["formatPreset"] = preset
        platform = str(payload.get("platform") or "instagram").lower()
        if platform not in {"instagram", "facebook", "linkedin", "x"}:
            platform = "instagram"
        payload["platform"] = platform
        payload["name"] = str(payload.get("name") or "AI social post")[:120]

    if op_name in OPS_CREATING_ELEMENT and not element_id:
        # element_id optional on create — apply layer will mint one
        pass

    return SocialDesignOp(
        op=op_name,
        linked_project_id=linked_project_id,
        post_id=post_id,
        element_id=element_id,
        payload=payload,
    )


def normalize_raw_ops(
    raw_ops: list[Any],
    *,
    linked_project_id: UUID,
    fallback_asset_id: UUID | None,
    default_post_id: str | None = None,
) -> list[dict[str, Any]]:
    """Best-effort sanitize LLM ops before strict validation (no inventing media)."""
    out: list[dict[str, Any]] = []
    minted_post_id = default_post_id or f"ai-post-{int(time.time() * 1000)}"
    for raw in raw_ops:
        if not isinstance(raw, dict):
            continue
        op = dict(raw)
        op["op"] = str(op.get("op") or "").strip().upper()
        if not op.get("linked_project_id"):
            op["linked_project_id"] = str(linked_project_id)
        else:
            try:
                if UUID(str(op["linked_project_id"])) != linked_project_id:
                    op["linked_project_id"] = str(linked_project_id)
            except (TypeError, ValueError):
                op["linked_project_id"] = str(linked_project_id)

        # Accept camelCase aliases from LLM JSON
        if not op.get("post_id") and op.get("postId"):
            op["post_id"] = op.get("postId")
        if not op.get("element_id") and op.get("elementId"):
            op["element_id"] = op.get("elementId")
        if not op.get("post_id"):
            op["post_id"] = minted_post_id

        payload = op.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        else:
            payload = dict(payload)

        for key in ("asset_id", "assetId", "cover_asset_id", "coverAssetId"):
            if key not in payload:
                continue
            val = payload.get(key)
            if isinstance(val, str) and (
                val.startswith("http://")
                or val.startswith("https://")
                or "unsplash" in val.lower()
            ):
                if fallback_asset_id is not None:
                    payload["asset_id"] = str(fallback_asset_id)
                    payload.pop("assetId", None)
                    payload.pop("coverAssetId", None)
                    payload.pop("cover_asset_id", None)
                break
            aid = parse_asset_id(val)
            if aid is None and fallback_asset_id is not None and op["op"] in {
                "SET_BACKGROUND",
                "ADD_IMAGE",
                "REPLACE_IMAGE",
            }:
                payload["asset_id"] = str(fallback_asset_id)
                payload.pop("assetId", None)
                payload.pop("coverAssetId", None)
                payload.pop("cover_asset_id", None)
        op["payload"] = payload
        out.append(op)
    return out


def validate_ops(
    raw_ops: list[Any],
    *,
    linked_project_id: UUID,
    posts: list[dict[str, Any]],
    allowed_asset_ids: set[UUID],
) -> tuple[list[SocialDesignOp], list[tuple[dict[str, Any], str]]]:
    """Validate ops sequentially, mutating a working copy so later ops see creates."""
    working = [dict(p) for p in posts]
    accepted: list[SocialDesignOp] = []
    rejected: list[tuple[dict[str, Any], str]] = []

    for raw in raw_ops:
        try:
            op = validate_op(
                raw,
                linked_project_id=linked_project_id,
                posts=working,
                allowed_asset_ids=allowed_asset_ids,
            )
        except OpValidationError as exc:
            rejected.append((raw if isinstance(raw, dict) else {"op": raw}, exc.reason))
            continue

        # Soft-apply CREATE_POST / ADD_* onto working copy for subsequent validation
        if op.op == "CREATE_POST" and find_post(working, op.post_id) is None:
            w, h = FORMAT_PRESETS.get(str(op.payload.get("formatPreset")), (1080, 1080))
            working.append(
                {
                    "id": op.post_id,
                    "formatPreset": op.payload.get("formatPreset"),
                    "width": w,
                    "height": h,
                    "elements": [],
                    "linked_project_id": str(linked_project_id),
                }
            )
        elif op.op in OPS_CREATING_ELEMENT:
            post = find_post(working, op.post_id)
            if post is not None:
                elements = post.setdefault("elements", [])
                if not isinstance(elements, list):
                    post["elements"] = []
                    elements = post["elements"]
                eid = op.element_id or f"pending-{len(elements)}"
                elements.append({"id": eid, "type": "TEXT"})
                if op.element_id is None:
                    op = op.model_copy(update={"element_id": eid})

        accepted.append(op)

    return accepted, rejected
