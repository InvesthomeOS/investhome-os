"""Structured reconstruction — execute a Master Design Spec into a raster.

The spec is the creative input. This module composites locked project assets
and typesets semantic elements. It is not the Native Renderer, not DesignSpec
templates, and not raster surgery.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.creative_director.edit_map import _as_dict
from investhome_api.services.creative_director.price_block_revision import _load_font
from investhome_api.services.gpt_image_design.compose import _fit_logo, resolve_turkish_font

NAVY = (10, 16, 36)
GOLD = (201, 168, 92)
WHITE = (246, 241, 232)
CTA_INK = (18, 16, 12)


def _abs(item: dict[str, Any] | None) -> dict[str, int] | None:
    box = _as_dict(_as_dict(item).get("geometry")).get("absolute")
    if not box:
        return None
    return {k: int(box[k]) for k in ("x0", "y0", "x1", "y1")}


def region(spec: dict[str, Any], role: str) -> dict[str, Any] | None:
    for item in spec.get("regions") or []:
        if item.get("semantic_role") == role:
            return item
    return None


def element(spec: dict[str, Any], role: str) -> dict[str, Any] | None:
    for item in spec.get("elements") or []:
        if item.get("semantic_role") == role:
            return item
    return None


def serif(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    try:
        font = resolve_turkish_font(bold=bold, size=size, family="serif")
        if font is not None:
            return font
    except Exception:
        pass
    return _load_font(size, bold=bold, serif=True)


def fit_serif(text: str, max_w: int, max_h: int, *, bold: bool = True) -> ImageFont.ImageFont:
    hi = max(11, min(96, max_h))
    for size in range(hi, 10, -1):
        font = serif(size, bold=bold)
        tw, th = text_size(font, text)
        if tw <= max(8, max_w) and th <= max(8, max_h):
            return font
    return serif(11, bold=bold)


def text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    bbox = font.getbbox(text or "")
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def cover_crop(
    source: Image.Image,
    tw: int,
    th: int,
    *,
    fx: float = 0.5,
    fy: float = 0.42,
) -> tuple[Image.Image, dict[str, Any]]:
    src = source.convert("RGB")
    sw, sh = src.size
    scale = max(tw / max(1, sw), th / max(1, sh))
    nw, nh = max(tw, int(round(sw * scale))), max(th, int(round(sh * scale)))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = int(round((nw - tw) * fx))
    y0 = int(round((nh - th) * fy))
    x0 = max(0, min(nw - tw, x0))
    y0 = max(0, min(nh - th, y0))
    crop = resized.crop((x0, y0, x0 + tw, y0 + th))
    return crop, {"scale": round(scale, 5), "x0": x0, "y0": y0, "fx": fx, "fy": fy, "method": "object_fit_cover"}


def refine_crop_to_reference(
    source: Image.Image,
    reference: Image.Image,
    *,
    samples: int = 7,
) -> tuple[Image.Image, dict[str, Any]]:
    """Choose cover-crop offsets so Day_004 matches the approved hero appearance.

    Reference pixels are a crop guide only. Output pixels come from source.
    """
    tw, th = reference.size
    best = None
    best_score = 1e18
    best_meta: dict[str, Any] = {}
    ref = reference.convert("RGB").resize((tw // 4, th // 4), Image.Resampling.BILINEAR)
    rp = ref.load()
    rw, rh = ref.size
    for iy, fy in enumerate([i / (samples - 1) * 0.55 + 0.15 for i in range(samples)]):
        for fx in (0.42, 0.5, 0.58):
            crop, meta = cover_crop(source, tw, th, fx=fx, fy=fy)
            small = crop.resize((rw, rh), Image.Resampling.BILINEAR)
            sp = small.load()
            total = 0
            n = 0
            for y in range(0, rh, 2):
                for x in range(0, rw, 2):
                    a = rp[x, y]
                    b = sp[x, y]
                    total += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
                    n += 1
            score = total / 3.0 / max(1, n)
            if score < best_score:
                best_score = score
                best = crop
                best_meta = {**meta, "reference_mad": round(score, 3)}
    assert best is not None
    return best, best_meta


def _center_text(
    draw: ImageDraw.ImageDraw,
    box: dict[str, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    *,
    y: int | None = None,
) -> dict[str, int]:
    tw, th = text_size(font, text)
    x = box["x0"] + (box["x1"] - box["x0"] - tw) // 2
    if y is None:
        y = box["y0"] + (box["y1"] - box["y0"] - th) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return {"x0": x, "y0": y, "x1": x + tw, "y1": y + th}


def _diamond(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int]) -> None:
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def _gold_rule(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, *, diamond: bool = True) -> None:
    draw.line([(x0, y), (x1, y)], fill=GOLD, width=2)
    if diamond:
        _diamond(draw, (x0 + x1) // 2, y, 6, GOLD)


def sample_palette(reference: Image.Image | None, spec: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    palette = {"navy": NAVY, "gold": GOLD, "white": WHITE}
    if reference is None:
        return palette
    px = reference.convert("RGB").load()
    navy_box = _abs(region(spec, "navy_field")) or {"x0": 8, "y0": 8, "x1": 40, "y1": 40}
    rs, gs, bs, n = 0, 0, 0, 0
    for y in range(navy_box["y0"] + 4, min(navy_box["y0"] + 40, navy_box["y1"]), 3):
        for x in range(8, 48, 3):
            r, g, b = px[x, y]
            rs += r
            gs += g
            bs += b
            n += 1
    if n:
        palette["navy"] = (rs // n, gs // n, bs // n)
    return palette


def reconstruct_from_spec(
    spec: dict[str, Any],
    *,
    source_visual: Image.Image,
    logo: Image.Image,
    reference_cover: Image.Image | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    if spec.get("visual_fidelity_profile") and spec.get("schema") == "MasterDesignSpecV1.1":
        from investhome_api.services.creative_director.visual_fidelity import reconstruct_same_design

        return reconstruct_same_design(spec, source_visual=source_visual, logo=logo)
    canvas = _as_dict(spec.get("canvas"))
    width = int(canvas.get("width") or 1088)
    height = int(canvas.get("height") or 1360)
    colors = sample_palette(reference_cover, spec)
    navy, gold, white = colors["navy"], colors["gold"], colors["white"]
    out = Image.new("RGB", (width, height), navy)
    draw = ImageDraw.Draw(out)
    drawn: list[str] = []
    fonts_used: dict[str, Any] = {}

    hero_box = _abs(region(spec, "hero_visual")) or {"x0": 0, "y0": 554, "x1": width, "y1": 1209}
    hw, hh = hero_box["x1"] - hero_box["x0"], hero_box["y1"] - hero_box["y0"]
    ref_hero = None
    if reference_cover is not None:
        ref_hero = reference_cover.convert("RGB").crop(
            (hero_box["x0"], hero_box["y0"], hero_box["x1"], hero_box["y1"])
        )
    if ref_hero is not None:
        hero, hero_meta = refine_crop_to_reference(source_visual, ref_hero)
    else:
        focal = _as_dict(_as_dict(spec.get("hero_treatment")).get("approximate_focal_point")).get("value") or {}
        hero, hero_meta = cover_crop(
            source_visual,
            hw,
            hh,
            fx=float(focal.get("normalized_x") or 0.5),
            fy=0.42,
        )
    out.paste(hero, (hero_box["x0"], hero_box["y0"]))

    footer = _abs(region(spec, "bottom_brand_treatment")) or {"x0": 0, "y0": hero_box["y1"], "x1": width, "y1": height}
    draw.rectangle([footer["x0"], footer["y0"], footer["x1"], footer["y1"]], fill=navy)
    fade_h = min(140, hh // 4)
    fade = Image.new("RGBA", (width, fade_h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    nr, ng, nb = navy
    for i in range(fade_h):
        a = int(255 * (i / max(1, fade_h - 1)) ** 1.35)
        fd.line([(0, i), (width, i)], fill=(nr, ng, nb, a))
    out.paste(Image.alpha_composite(out.crop((0, hero_box["y1"] - fade_h, width, hero_box["y1"])).convert("RGBA"), fade).convert("RGB"), (0, hero_box["y1"] - fade_h))

    head = element(spec, "headline")
    head_box = _abs(head) or {"x0": 130, "y0": 28, "x1": width - 130, "y1": 168}
    words = str((head or {}).get("exact_content") or "ALIRKEN KAZAN").split()
    line1 = words[0] if words else "ALIRKEN"
    line2 = " ".join(words[1:]) if len(words) > 1 else ""
    bw = max(40, head_box["x1"] - head_box["x0"] - 8)
    bh = max(40, head_box["y1"] - head_box["y0"])
    f1 = fit_serif(line1, bw, max(16, int(bh * 0.32)), bold=True)
    f2 = fit_serif(line2 or line1, bw, max(20, int(bh * 0.48)), bold=True)
    fonts_used["headline"] = {
        "family": "DejaVu Serif",
        "fallback_reason": "exact campaign font files are unknown in Phase 3.0",
        "confidence": 0.55,
    }
    a_box = _center_text(draw, head_box, line1, f1, white, y=head_box["y0"] + 2)
    if line2:
        k_box = _center_text(draw, head_box, line2, f2, gold, y=a_box["y1"] + 2)
        rule_y = k_box["y0"] + (k_box["y1"] - k_box["y0"]) // 2
        _gold_rule(draw, head_box["x0"] + 40, k_box["x0"] - 16, rule_y)
        _gold_rule(draw, k_box["x1"] + 16, head_box["x1"] - 40, rule_y, diamond=False)
    drawn.append(str((head or {}).get("exact_content")))

    support = element(spec, "supporting_copy")
    support_box = _abs(support) or {"x0": 130, "y0": 188, "x1": width - 130, "y1": 222}
    sf = fit_serif(str((support or {}).get("exact_content") or ""), max(40, support_box["x1"] - support_box["x0"] - 8), max(14, support_box["y1"] - support_box["y0"] - 4), bold=False)
    fonts_used["supporting"] = {"family": "DejaVu Serif", "size": 18, "confidence": 0.55}
    _center_text(draw, support_box, str((support or {}).get("exact_content") or ""), sf, white)
    drawn.append(str((support or {}).get("exact_content") or ""))
    _gold_rule(draw, width // 2 - 120, width // 2 + 120, support_box["y1"] + 6)

    def pair(box: dict[str, int], label: str, value: str, *, primary: bool, struck: bool = False, value_color=gold) -> None:
        bw = max(24, box["x1"] - box["x0"] - 8)
        bh = max(24, box["y1"] - box["y0"] - 4)
        label_h = max(12, int(bh * 0.22))
        value_h = max(16, int(bh * (0.58 if primary else 0.48)))
        lf = fit_serif(label, bw, label_h, bold=False)
        vf = fit_serif(value, bw, value_h, bold=True)
        gap = 3 if primary else 2
        lw, lh = text_size(lf, label)
        vw, vh = text_size(vf, value)
        total = lh + gap + vh
        y = box["y0"] + max(0, (box["y1"] - box["y0"] - total) // 2)
        _center_text(draw, box, label, lf, white, y=y)
        vb = _center_text(draw, box, value, vf, value_color, y=y + lh + gap)
        if struck:
            mid = (vb["y0"] + vb["y1"]) // 2
            draw.line([(vb["x0"] - 4, mid), (vb["x1"] + 4, mid)], fill=gold, width=max(2, vh // 10))
        drawn.extend([label, value])

    launch = element(spec, "launch_price")
    if launch:
        pair(
            _abs(launch) or {"x0": 130, "y0": 236, "x1": width - 130, "y1": 360},
            str((element(spec, "launch_price_label") or {}).get("exact_content") or "LANSMAN FİYATI"),
            str(launch.get("exact_content") or ""),
            primary=True,
            value_color=gold,
        )
        fonts_used["launch_price"] = {"family": "DejaVu Serif", "size": 44, "confidence": 0.55}

    list_el = element(spec, "list_price")
    if list_el:
        pair(
            _abs(list_el) or {"x0": 130, "y0": 370, "x1": width // 2 - 16, "y1": 470},
            str((element(spec, "list_price_label") or {}).get("exact_content") or "LİSTE FİYATI"),
            str(list_el.get("exact_content") or ""),
            primary=False,
            struck=bool(list_el.get("strikethrough")),
            value_color=white,
        )
    save_el = element(spec, "savings")
    if save_el:
        pair(
            _abs(save_el) or {"x0": width // 2 + 16, "y0": 370, "x1": width - 130, "y1": 470},
            str((element(spec, "savings_label") or {}).get("exact_content") or "KAZANCINIZ"),
            str(save_el.get("exact_content") or ""),
            primary=False,
            value_color=gold,
        )
    disc = element(spec, "discount")
    if disc:
        pair(
            _abs(disc) or {"x0": width // 3, "y0": 478, "x1": 2 * width // 3, "y1": 540},
            str((element(spec, "discount_label") or {}).get("exact_content") or "LANSMAN AVANTAJI"),
            str(disc.get("exact_content") or ""),
            primary=False,
            value_color=gold,
        )
    unit = element(spec, "unit_type")
    if unit:
        pair(
            _abs(unit) or {"x0": 2 * width // 3, "y0": 478, "x1": width - 130, "y1": 540},
            str((element(spec, "unit_label") or {}).get("exact_content") or "DAİRE"),
            str(unit.get("exact_content") or ""),
            primary=False,
            value_color=gold,
        )

    cta = element(spec, "cta")
    cta_box = _abs(cta) or _abs(_as_dict(spec.get("cta_treatment"))) or {"x0": 260, "y0": 1129, "x1": 828, "y1": 1200}
    radius = 10
    draw.rounded_rectangle(
        [cta_box["x0"], cta_box["y0"], cta_box["x1"] - 1, cta_box["y1"] - 1],
        radius=radius,
        fill=gold,
    )
    cta_font = fit_serif(
        str((cta or {}).get("exact_content") or "PROJEYİ KEŞFET"),
        max(40, cta_box["x1"] - cta_box["x0"] - 24),
        max(16, cta_box["y1"] - cta_box["y0"] - 12),
        bold=True,
    )
    fonts_used["cta"] = {"family": "DejaVu Serif", "size": 28, "confidence": 0.55}
    _center_text(draw, cta_box, str((cta or {}).get("exact_content") or "PROJEYİ KEŞFET"), cta_font, CTA_INK)
    drawn.append(str((cta or {}).get("exact_content") or "PROJEYİ KEŞFET"))

    logo_box = _abs(element(spec, "logo")) or _abs(_as_dict(spec.get("logo_treatment"))) or {
        "x0": 417,
        "y0": 1214,
        "x1": 666,
        "y1": 1340,
    }
    fitted = _fit_logo(logo, logo_box["x1"] - logo_box["x0"], logo_box["y1"] - logo_box["y0"])
    lx = logo_box["x0"] + (logo_box["x1"] - logo_box["x0"] - fitted.width) // 2
    ly = logo_box["y0"] + (logo_box["y1"] - logo_box["y0"] - fitted.height) // 2
    if fitted.mode == "RGBA":
        base = out.convert("RGBA")
        base.paste(fitted, (lx, ly), fitted)
        out = base.convert("RGB")
    else:
        out.paste(fitted, (lx, ly))

    report = {
        "reconstruction_engine": "structured_reconstruction.reconstruct_from_spec",
        "hero_method": "cover_crop_from_source_visual" + ("+reference_alignment" if ref_hero is not None else ""),
        "hero_meta": hero_meta,
        "logo_method": "real_logo_asset_contain_fit",
        "typography": fonts_used,
        "palette": {k: list(v) for k, v in colors.items()},
        "drawn_content": [d for d in drawn if d],
        "provider_image_calls": 0,
        "native_renderer": False,
        "design_spec_templates": False,
        "raster_surgery": False,
    }
    return out, report


def validate_render(
    image: Image.Image,
    spec: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    same_design = spec.get("schema") == "MasterDesignSpecV1.1" or str(spec.get("spec_revision") or "") == "1.1"
    if same_design:
        required = [
            "ALIRKEN KAZAN",
            "The Temple'da yerinizi lansman döneminde alın.",
            "2+1",
            "DAİRE",
            "675.000",
            "%35",
            "LANSMAN AVANTAJI",
            "PROJEYİ KEŞFET",
        ]
        forbidden = ["438.750", "236.250", "LANSMAN FİYATI", "KAZANCINIZ"]
    else:
        required = [
            "ALIRKEN KAZAN",
            "The Temple'da yerinizi lansman döneminde alın.",
            "2+1",
            "DAİRE",
            "675.000",
            "LİSTE FİYATI",
            "438.750",
            "LANSMAN FİYATI",
            "236.250",
            "KAZANCINIZ",
            "%35",
            "LANSMAN AVANTAJI",
            "PROJEYİ KEŞFET",
        ]
        forbidden = []
    blob = " ".join(report.get("drawn_content") or [])
    missing = [item for item in required if item not in blob]
    if missing:
        failures.append(f"missing_drawn:{','.join(missing)}")
    leaked = [item for item in forbidden if item in blob]
    if leaked:
        failures.append(f"forbidden_drawn:{','.join(leaked)}")
    if image.size[0] != int(_as_dict(spec.get("canvas")).get("width") or 0):
        failures.append("canvas_width_mismatch")
    if image.size[1] != int(_as_dict(spec.get("canvas")).get("height") or 0):
        failures.append("canvas_height_mismatch")
    boxes = []
    for role in ("launch_price", "list_price", "savings", "discount", "unit_type"):
        box = _abs(element(spec, role))
        if box:
            boxes.append((role, box))
            if box["y1"] > (_abs(region(spec, "hero_visual")) or {"y0": 10**9})["y0"] + 2:
                failures.append(f"commercial_invades_hero:{role}")
    overlaps = 0
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1 :]:
            ix0, iy0 = max(a["x0"], b["x0"]), max(a["y0"], b["y0"])
            ix1, iy1 = min(a["x1"], b["x1"]), min(a["y1"], b["y1"])
            if ix1 - ix0 > 12 and iy1 - iy0 > 12 and {ra, rb} != {"discount", "unit_type"}:
                # launch label shares bbox with launch value by design
                if "label" in ra or "label" in rb:
                    continue
                overlaps += 1
    if overlaps:
        failures.append(f"slot_overlap:{overlaps}")
    return {"status": "fail" if failures else "pass", "failures": failures, "missing_drawn": missing}


def region_mad(a: Image.Image, b: Image.Image, box: dict[str, int]) -> float:
    ar = a.convert("RGB").crop((box["x0"], box["y0"], box["x1"], box["y1"]))
    br = b.convert("RGB").crop((box["x0"], box["y0"], box["x1"], box["y1"]))
    if br.size != ar.size:
        br = br.resize(ar.size, Image.Resampling.LANCZOS)
    pa, pb = ar.load(), br.load()
    w, h = ar.size
    total = 0.0
    n = 0
    step = 2 if w * h > 80_000 else 1
    for y in range(0, h, step):
        for x in range(0, w, step):
            ca, cb = pa[x, y], pb[x, y]
            total += abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) + abs(ca[2] - cb[2])
            n += 1
    return total / 3.0 / max(1, n)


def similarity_report(reference: Image.Image, preview: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    def band(mad: float) -> str:
        if mad < 12:
            return "high"
        if mad < 28:
            return "medium"
        return "low"

    hero = _abs(region(spec, "hero_visual"))
    head = _abs(element(spec, "headline")) or _abs(region(spec, "headline_area"))
    cta = _abs(element(spec, "cta"))
    logo = _abs(element(spec, "logo"))
    navy = _abs(region(spec, "navy_field"))
    out = {
        "hero": {"mad": round(region_mad(reference, preview, hero), 3), "note": "crop/source composite; not pixel-identical"} if hero else {},
        "headline": {"mad": round(region_mad(reference, preview, head), 3), "note": "identity preserved, geometry flexible"} if head else {},
        "cta": {"mad": round(region_mad(reference, preview, cta), 3)} if cta else {},
        "logo": {"mad": round(region_mad(reference, preview, logo), 3)} if logo else {},
        "navy_palette_proxy": {"mad": round(region_mad(reference, preview, {"x0": 8, "y0": 8, "x1": 80, "y1": 40}), 3)} if navy else {},
        "commercial_intentionally_changed": spec.get("schema") != "MasterDesignSpecV1.1",
    }
    for key in ("hero", "headline", "cta", "logo"):
        if out.get(key) and "mad" in out[key]:
            out[key]["similarity"] = band(float(out[key]["mad"]))
    if out.get("navy_palette_proxy"):
        out["navy_palette_proxy"]["similarity"] = band(float(out["navy_palette_proxy"]["mad"]))
        out["palette_similarity"] = out["navy_palette_proxy"]["similarity"]
    return out
