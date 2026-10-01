"""Phase 4.0 native master renderer — executor only.

Draws exactly what NativeMasterDesignSpecV1 specifies.
Does not select templates, does not call an image provider,
does not invent layout, does not alter architecture.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from investhome_api.services.creative_director.native_master import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    mark_spec_rendered,
    validate_native_master_spec,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _rgb(color: dict[str, Any] | None, default: tuple[int, int, int] = (255, 255, 255)) -> tuple[int, int, int]:
    if not color:
        return default
    rgb = color.get("rgb") if isinstance(color, dict) else None
    if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    return default


def _opacity(color: dict[str, Any] | None, default: float = 1.0) -> float:
    if isinstance(color, dict) and color.get("opacity") is not None:
        return float(color["opacity"])
    return default


def _load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path:
        try:
            return ImageFont.truetype(path, int(size))
        except Exception:
            pass
    return ImageFont.load_default()


def _text_width(font: ImageFont.ImageFont, text: str, tracking: float) -> int:
    if not text:
        return 0
    base = font.getbbox(text)
    extra = tracking * max(0, len(text) - 1)
    return int(round((base[2] - base[0]) + extra))


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: float,
) -> None:
    x, y = xy
    if tracking <= 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        box = font.getbbox(ch)
        x += (box[2] - box[0]) + tracking


def _wrap_line(font: ImageFont.ImageFont, text: str, tracking: float, max_width: int) -> list[str]:
    words = str(text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if _text_width(font, trial, tracking) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _place_tracked(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: float,
    *,
    align: str = "center",
    y: int | None = None,
) -> None:
    width = _text_width(font, text, tracking)
    if align == "left":
        x = box["x0"] + 2
    else:
        x = box["x0"] + max(0, ((box["x1"] - box["x0"]) - width) // 2)
    if y is None:
        bb = font.getbbox(text or "A")
        text_h = bb[3] - bb[1]
        y = box["y0"] + max(0, ((box["y1"] - box["y0"]) - text_h) // 2) - bb[1]
    _draw_tracked(draw, (x, y), text, font, fill, tracking)


def _center_tracked(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: float,
    *,
    y: int | None = None,
) -> None:
    _place_tracked(draw, box, text, font, fill, tracking, align="center", y=y)


def _vertical_gradient(size: tuple[int, int], start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    w, h = max(1, size[0]), max(1, size[1])
    band = Image.new("RGB", (1, h))
    px = band.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = (
            int(start[0] + (end[0] - start[0]) * t),
            int(start[1] + (end[1] - start[1]) * t),
            int(start[2] + (end[2] - start[2]) * t),
        )
    return band.resize((w, h), Image.Resampling.BILINEAR)


def _alpha_gradient(size: tuple[int, int], *, top_alpha: int, bottom_alpha: int) -> Image.Image:
    w, h = max(1, size[0]), max(1, size[1])
    mask = Image.new("L", (1, h))
    px = mask.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = int(top_alpha + (bottom_alpha - top_alpha) * t)
    return mask.resize((w, h), Image.Resampling.BILINEAR)


def _horizontal_alpha_gradient(size: tuple[int, int], *, left_alpha: int, right_alpha: int) -> Image.Image:
    w, h = max(1, size[0]), max(1, size[1])
    mask = Image.new("L", (w, 1))
    px = mask.load()
    for x in range(w):
        t = x / max(1, w - 1)
        px[x, 0] = int(left_alpha + (right_alpha - left_alpha) * t)
    return mask.resize((w, h), Image.Resampling.BILINEAR)


def _apply_hero_treatment(source: Image.Image, treatment: dict[str, Any], canvas: tuple[int, int]) -> Image.Image:
    crop = _as_dict(treatment.get("source_crop_rectangle"))
    src = source.convert("RGB")
    cropped = src.crop((crop["x0"], crop["y0"], crop["x1"], crop["y1"]))
    dest = cropped.resize(canvas, Image.Resampling.LANCZOS)
    dest = ImageEnhance.Brightness(dest).enhance(float(treatment.get("brightness") or 1.0))
    dest = ImageEnhance.Contrast(dest).enhance(float(treatment.get("contrast") or 1.0))
    dest = ImageEnhance.Color(dest).enhance(float(treatment.get("saturation") or 1.0))
    temp = _as_dict(treatment.get("temperature"))
    if temp:
        r, g, b = dest.split()
        r = r.point(lambda v: min(255, int(v * float(temp.get("red_gain") or 1.0))))
        g = g.point(lambda v: min(255, int(v * float(temp.get("green_gain") or 1.0))))
        b = b.point(lambda v: min(255, int(v * float(temp.get("blue_gain") or 1.0))))
        dest = Image.merge("RGB", (r, g, b))
    return dest


def _overlay_rect(base: Image.Image, box: dict[str, int], color: tuple[int, int, int], mask: Image.Image) -> None:
    layer = Image.new("RGB", (box["x1"] - box["x0"], box["y1"] - box["y0"]), color)
    base.paste(layer, (box["x0"], box["y0"]), mask)


def _role_font(spec: dict[str, Any], role: str) -> tuple[ImageFont.ImageFont, dict[str, Any]]:
    plan = _as_dict(_as_dict(spec.get("typography")).get("roles")).get(role) or {}
    font = _load_font(plan.get("actual_font_path"), int(plan.get("size") or 16))
    return font, plan


def render_native_master(
    spec: dict[str, Any],
    *,
    source_image: Image.Image,
    logo_image: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    """Execute the finalized spec. No layout invention."""
    validation = validate_native_master_spec(spec)
    if validation.get("status") != "pass":
        raise ValueError(f"Cannot render invalid spec: {validation}")
    if spec.get("rendered_master_visual_asset_id"):
        raise ValueError("Spec already bound to a visual; create a new spec to render.")
    prov = _as_dict(spec.get("provenance"))
    if not prov.get("spec_finalized_at") or prov.get("rendered_at"):
        raise ValueError("Spec must be finalized and not yet rendered.")
    if prov.get("extracted_from_raster"):
        raise ValueError("Native renderer refuses extracted specs.")

    canvas = _as_dict(spec.get("canvas"))
    width, height = int(canvas["width"]), int(canvas["height"])
    colors = _as_dict(spec.get("colors"))
    boxes = _as_dict(spec.get("geometry"))
    content = _as_dict(spec.get("content"))
    treatment = _as_dict(_as_dict(spec.get("image_treatments")).get("hero"))
    dest = _as_dict(treatment.get("destination_geometry")) or boxes.get("hero_visual") or {"x0": 0, "y0": 0, "x1": width, "y1": height}
    drawn_content: list[str] = []
    drawn_roles: list[str] = []
    fonts_used: list[str] = []
    drawn_boxes: list[dict[str, Any]] = []

    navy = _rgb(colors.get("navy_primary"), (10, 18, 40))
    image = Image.new("RGB", (width, height), navy)
    treated = _apply_hero_treatment(
        source_image,
        treatment,
        (max(1, dest["x1"] - dest["x0"]), max(1, dest["y1"] - dest["y0"])),
    )
    image.paste(treated, (int(dest["x0"]), int(dest["y0"])))
    drawn_roles.append("hero_visual")
    drawn_boxes.append({"id": "hero_visual", **boxes["hero_visual"]})

    for deco in spec.get("decorations") or []:
        kind = deco.get("kind")
        box = _as_dict(deco.get("geometry"))
        color = _rgb(deco.get("color"))
        if kind == "fill":
            ImageDraw.Draw(image).rectangle([box["x0"], box["y0"], box["x1"] - 1, box["y1"] - 1], fill=color)
        elif kind == "linear_gradient" and deco.get("role") == "hero_transition":
            size = (box["x1"] - box["x0"], box["y1"] - box["y0"])
            start_a = int(deco.get("alpha_start") or 168)
            end_a = int(deco.get("alpha_end") or 0)
            axis = str(deco.get("fade_axis") or "top_to_bottom")
            if axis == "left_to_right":
                mask = _horizontal_alpha_gradient(size, left_alpha=start_a, right_alpha=end_a)
            elif axis == "left_dissolve":
                mask = ImageChops.multiply(
                    _horizontal_alpha_gradient(size, left_alpha=start_a, right_alpha=end_a),
                    _alpha_gradient(size, top_alpha=start_a, bottom_alpha=max(0, end_a // 2)),
                )
            else:
                mask = _alpha_gradient(size, top_alpha=start_a, bottom_alpha=end_a)
            _overlay_rect(image, box, color, mask)
        elif kind == "linear_gradient" and deco.get("role") == "footer_fade":
            mask = _alpha_gradient(
                (box["x1"] - box["x0"], box["y1"] - box["y0"]),
                top_alpha=int(deco.get("alpha_start") or 0),
                bottom_alpha=int(deco.get("alpha_end") or 200),
            )
            _overlay_rect(image, box, color, mask)
        elif kind == "rules_and_diamond":
            draw = ImageDraw.Draw(image)
            mid_y = (box["y0"] + box["y1"]) // 2
            mid_x = (box["x0"] + box["x1"]) // 2
            draw.line([(box["x0"], mid_y), (mid_x - 14, mid_y)], fill=color, width=int(deco.get("thickness") or 1))
            draw.line([(mid_x + 14, mid_y), (box["x1"], mid_y)], fill=color, width=int(deco.get("thickness") or 1))
            d = 5
            draw.polygon([(mid_x, mid_y - d), (mid_x + d, mid_y), (mid_x, mid_y + d), (mid_x - d, mid_y)], outline=color)
        elif kind == "diamond":
            draw = ImageDraw.Draw(image)
            mid_x = (box["x0"] + box["x1"]) // 2
            mid_y = (box["y0"] + box["y1"]) // 2
            d = max(3, (box["x1"] - box["x0"]) // 2)
            draw.polygon([(mid_x, mid_y - d), (mid_x + d, mid_y), (mid_x, mid_y + d), (mid_x - d, mid_y)], outline=color)
        elif kind == "soft_rect":
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            alpha = int(255 * float(deco.get("opacity") or 0.35))
            od.rounded_rectangle([box["x0"], box["y0"], box["x1"], box["y1"]], radius=18, fill=(*color, alpha))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        elif kind == "vertical_hairline":
            draw = ImageDraw.Draw(image)
            draw.line([(box["x0"], box["y0"]), (box["x1"], box["y1"])], fill=color, width=int(deco.get("thickness") or 1))
        drawn_roles.append("decoration")

    draw = ImageDraw.Draw(image)

    def paint_text(role: str, box_name: str, text: str, *, y_frac: float | None = None, color_role: str | None = None) -> None:
        font, plan = _role_font(spec, role)
        path = plan.get("actual_font_path")
        if path and path not in fonts_used:
            fonts_used.append(path)
        fill = _rgb(colors.get(color_role or plan.get("color_role") or "white"))
        box = boxes[box_name]
        align = str(plan.get("alignment") or "center")
        tracking = float(plan.get("tracking") or 0)
        max_w = max(8, box["x1"] - box["x0"] - 4)
        if align == "left" and _text_width(font, text, tracking) > max_w and role == "supporting_copy":
            lines = _wrap_line(font, text, tracking, max_w)
            y = box["y0"] + 2
            for line in lines:
                _place_tracked(draw, box, line, font, fill, tracking, align=align, y=y)
                y += int((font.getbbox(line or "A")[3] - font.getbbox(line or "A")[1]) * 1.25)
        else:
            y = None
            if y_frac is not None:
                bb = font.getbbox(text or "A")
                y = int(box["y0"] + (box["y1"] - box["y0"]) * y_frac) - bb[1]
            _place_tracked(draw, box, text, font, fill, tracking, align=align, y=y)
        drawn_content.append(text)
        drawn_roles.append(role if role not in {"headline_line_1", "headline_line_2"} else "headline")
        drawn_boxes.append({"id": role, **box})

    paint_text("headline_line_1", "headline_line_1", content["headline_line_1"])
    paint_text("headline_line_2", "headline_line_2", content["headline_line_2"])
    drawn_content.append(content["headline"])
    paint_text("supporting_copy", "supporting_copy", content["supporting_copy"])
    paint_text("list_price", "price_column", content["list_price"])
    commercial_group = next((g for g in (spec.get("groups") or []) if g.get("id") == "commercial_group"), {})
    inline = str(commercial_group.get("companion_presentation") or "") == "inline_lockup"

    def paint_inline_pair(box_name: str, value_role: str, value: str, label_role: str, label: str) -> None:
        box = boxes[box_name]
        vfont, vplan = _role_font(spec, value_role)
        lfont, lplan = _role_font(spec, label_role)
        for path in (vplan.get("actual_font_path"), lplan.get("actual_font_path")):
            if path and path not in fonts_used:
                fonts_used.append(path)
        vfill = _rgb(colors.get(vplan.get("color_role") or "white"))
        lfill = _rgb(colors.get(lplan.get("color_role") or "gold_secondary"))
        gap = 12
        vw = _text_width(vfont, value, float(vplan.get("tracking") or 0))
        lw = _text_width(lfont, label, float(lplan.get("tracking") or 0))
        total = vw + gap + lw
        x = box["x0"] + 2 if str(vplan.get("alignment") or "center") == "left" else box["x0"] + max(0, ((box["x1"] - box["x0"]) - total) // 2)
        mid = (box["y0"] + box["y1"]) // 2
        vbb = vfont.getbbox(value or "A")
        lbb = lfont.getbbox(label or "A")
        vy = mid - (vbb[3] - vbb[1]) // 2 - vbb[1]
        ly = mid - (lbb[3] - lbb[1]) // 2 - lbb[1]
        _draw_tracked(draw, (x, vy), value, vfont, vfill, float(vplan.get("tracking") or 0))
        _draw_tracked(draw, (x + vw + gap, ly), label, lfont, lfill, float(lplan.get("tracking") or 0))
        drawn_content.extend([value, label])
        drawn_roles.extend([value_role, label_role])
        drawn_boxes.append({"id": value_role, **box})

    if inline or str(commercial_group.get("companion_presentation") or "") == "stacked_left_inline":
        paint_inline_pair("unit_column", "unit_value", content["unit_value"], "unit_label", content["unit_label"])
        paint_inline_pair("discount_column", "discount_value", content["discount_value"], "discount_label", content["discount_label"])
    else:
        paint_text("unit_value", "unit_column", content["unit_value"], y_frac=0.05)
        paint_text("unit_label", "unit_column", content["unit_label"], y_frac=0.52)
        paint_text("discount_value", "discount_column", content["discount_value"], y_frac=0.05)
        paint_text("discount_label", "discount_column", content["discount_label"], y_frac=0.52)

    cta = _as_dict(spec.get("cta_treatment"))
    cta_box = _as_dict(cta.get("geometry")) or boxes["cta"]
    cta_font, cta_plan = _role_font(spec, "cta")
    if cta_plan.get("actual_font_path") and cta_plan["actual_font_path"] not in fonts_used:
        fonts_used.append(cta_plan["actual_font_path"])
    shape = str(cta.get("shape") or "")
    if shape not in {"underlined_action", "editorial_text_action"}:
        grad = _as_dict(cta.get("gradient"))
        bar = _vertical_gradient(
            (cta_box["x1"] - cta_box["x0"], cta_box["y1"] - cta_box["y0"]),
            _rgb(grad.get("start"), (214, 184, 110)),
            _rgb(grad.get("end"), (168, 132, 64)),
        )
        shadow = _as_dict(cta.get("shadow"))
        if shadow:
            shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(shade)
            ox, oy = (shadow.get("offset") or [0, 6])
            sd.rounded_rectangle(
                [cta_box["x0"] + int(ox), cta_box["y0"] + int(oy), cta_box["x1"] + int(ox), cta_box["y1"] + int(oy)],
                radius=int(cta.get("radius") or 2),
                fill=(0, 0, 0, int(255 * float(shadow.get("opacity") or 0.28))),
            )
            shade = shade.filter(ImageFilter.GaussianBlur(int(shadow.get("blur") or 8)))
            image = Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")
            draw = ImageDraw.Draw(image)
        mask = Image.new("L", bar.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, bar.size[0] - 1, bar.size[1] - 1], radius=int(cta.get("radius") or 2), fill=255)
        image.paste(bar, (cta_box["x0"], cta_box["y0"]), mask)
        draw = ImageDraw.Draw(image)
    _place_tracked(
        draw,
        cta_box,
        content["cta"],
        cta_font,
        _rgb(cta.get("text_color") or colors.get("cta_text")),
        float(cta_plan.get("tracking") or 0),
        align=str(cta.get("alignment") or cta_plan.get("alignment") or "center"),
    )
    drawn_content.append(content["cta"])
    drawn_roles.append("cta")
    drawn_boxes.append({"id": "cta", **cta_box})

    logo_box = boxes["logo"]
    fitted = _fit_logo(logo_image, logo_box["x1"] - logo_box["x0"], logo_box["y1"] - logo_box["y0"])
    grade = _as_dict(_as_dict(spec.get("logo_treatment")).get("grade"))
    if fitted.mode != "RGBA":
        fitted = fitted.convert("RGBA")
    if grade:
        rgb = Image.merge("RGB", fitted.split()[:3])
        rgb = ImageEnhance.Brightness(rgb).enhance(float(grade.get("brightness") or 1.0))
        rgb = ImageEnhance.Contrast(rgb).enhance(float(grade.get("contrast") or 1.0))
        a = fitted.split()[-1]
        fitted = Image.merge("RGBA", (*rgb.split(), a))
    logo_align = str(_as_dict(spec.get("logo_treatment")).get("alignment") or "center")
    if logo_align == "left":
        lx = logo_box["x0"]
    elif logo_align == "right":
        lx = logo_box["x1"] - fitted.width
    else:
        lx = logo_box["x0"] + (logo_box["x1"] - logo_box["x0"] - fitted.width) // 2
    ly = logo_box["y0"] + (logo_box["y1"] - logo_box["y0"] - fitted.height) // 2
    image.paste(fitted, (lx, ly), fitted)
    drawn_roles.append("logo")
    drawn_boxes.append({"id": "logo", **logo_box})

    mark_spec_rendered(spec)
    report = {
        "canvas": {"width": width, "height": height},
        "hero_asset_id": LOCKED_HERO_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "drawn_content": drawn_content,
        "drawn_roles": drawn_roles,
        "drawn_boxes": drawn_boxes,
        "fonts_used": fonts_used,
        "ai_architecture_generation": False,
        "image_provider_calls": 0,
        "layout_invented": False,
        "render_method": "native_master_spec_executor",
        "native_renderer_template": False,
    }
    return image, report


def png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
