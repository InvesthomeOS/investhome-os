"""AI Revision Intelligence v2 — structured plan + geometric command engine.

Never send raw NL to an image provider. Interpret → plan → resolve geometry →
locks → route → validate change diff → apply.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from investhome_api.schemas.creative_director import RevisionDiff, RevisionOperation

# ── Central relative-NL constants (Turkish) ─────────────────────────────────
RELATIVE_NL = {
    "biraz_scale": 0.10,  # ±10%
    "biraz_up_frac": 0.025,  # −0.025 * canvasH
    "biraz_down_frac": 0.025,
    "biraz_left_frac": 0.025,
    "biraz_right_frac": 0.025,
    "cok_scale": 0.20,
}

PROJECT_GOLD = "#C4A35A"
SAFE_MARGIN_DEFAULT = 48

STRICT_PRESERVE_PHRASES = (
    "başka hiçbir şeye dokunma",
    "baska hicbir seye dokunma",
    "sadece bunu değiştir",
    "sadece bunu degistir",
    "diğer her şeyi aynen koru",
    "diger her seyi aynen koru",
    "başka hiçbir şeyi değiştirme",
    "baska hicbir seyi degistirme",
    "başka hiçbir şey değiştirme",
    "kesinlikle değiştirme",
    "kesinlikle degistirme",
    "diğer tüm tasarım",
    "diger tum tasarim",
    "geri kalan tasarımı koru",
    "geri kalan tasarimi koru",
    "geri kalan hiçbir şeyini değiştirme",
    "geri kalan hicbir seyini degistirme",
    "tasarımın geri kalan",
    "tasarimin geri kalan",
    "görsele dokunma",
    "gorsele dokunma",
    "sadece logoyu değiştir",
    "sadece logoyu degistir",
)

ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "headline": ("headline", "başlık", "baslik", "primary_headline", "text-headline"),
    "primary_headline": ("headline", "primary_headline", "text-headline"),
    "cta": ("cta", "cta-primary"),
    "badge": ("discount-badge", "discount_badge", "badge", "rozet"),
    "logo": ("logo", "logo-project"),
    "support_message": ("support-message-1", "support_message", "support-message-2"),
    "left_feature_texts": (
        "feature-1",
        "feature-2",
        "support-message-1",
        "support-message-2",
        "left_feature_texts",
    ),
    "feature_text": ("feature-1", "feature-2", "feature-3", "support-message-1"),
    "price": ("new-price", "new_price", "old-price", "old_price", "savings-price", "savings_price", "fiyat"),
    "old_price": ("old-price", "old_price"),
    "new_price": ("new-price", "new_price"),
    "subheadline": ("subheadline", "alt başlık", "alt baslik"),
    "eyebrow": ("eyebrow", "unit-label", "eyebrow-pill"),
    "top_small_description": (
        "subheadline",
        "unit-label",
        "eyebrow",
        "top-description",
        "top_small_description",
    ),
}

TARGET_LABELS_TR = {
    "headline": "Başlık",
    "primary_headline": "Başlık",
    "cta": "CTA",
    "badge": "Rozet",
    "logo": "Logo",
    "support_message": "Destek metni",
    "left_feature_texts": "Özellik metinleri",
    "feature_text": "Özellik metni",
    "top_small_description": "Üst açıklama",
    "subheadline": "Alt başlık",
    "eyebrow": "Üst etiket",
    "price": "Fiyat",
    "old_price": "Eski fiyat",
    "background": "Arka plan",
    "layout": "Düzen",
    "overall": "Tasarım",
}


def normalize_tr(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def detect_strict_preserve(instruction: str) -> bool:
    low = normalize_tr(instruction)
    return any(p in low for p in STRICT_PRESERVE_PHRASES)


def _canvas_size(spec: dict[str, Any] | None) -> tuple[int, int]:
    if not isinstance(spec, dict):
        return 1080, 1350
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    return int(canvas.get("width") or 1080), int(canvas.get("height") or 1350)


def _safe_margin(spec: dict[str, Any] | None) -> int:
    if not isinstance(spec, dict):
        return SAFE_MARGIN_DEFAULT
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    return int(canvas.get("safe_margin") or canvas.get("margin") or SAFE_MARGIN_DEFAULT)


def element_box(el: dict[str, Any]) -> dict[str, float]:
    x = float(el.get("x") or 0)
    y = float(el.get("y") or 0)
    w = float(el.get("width") or 0)
    h = float(el.get("height") or 0)
    return {
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "left": x,
        "top": y,
        "right": x + w,
        "bottom": y + h,
        "centerX": x + w / 2,
        "centerY": y + h / 2,
    }


def find_element(
    spec: dict[str, Any] | None,
    *ids_or_roles: str,
) -> dict[str, Any] | None:
    if not isinstance(spec, dict):
        return None
    elements = spec.get("elements")
    if not isinstance(elements, list):
        return None
    wanted = {str(x).lower() for x in ids_or_roles if x}
    for el in elements:
        if not isinstance(el, dict):
            continue
        eid = str(el.get("id") or "").lower()
        role = str(el.get("role") or "").lower()
        if eid in wanted or role in wanted:
            return el
    return None


def resolve_target_from_selection(
    selected_element_id: str | None,
    instruction: str,
) -> str | None:
    """Selected element is strongest target for vague commands."""
    if selected_element_id:
        sid = selected_element_id.lower()
        for target, aliases in ROLE_ALIASES.items():
            if sid in {a.lower() for a in aliases} or sid == target:
                return target
            if sid.replace("_", "-") in {a.lower() for a in aliases}:
                return target
        if "badge" in sid or "rozet" in sid:
            return "badge"
        if sid in {"headline", "cta", "logo"}:
            return sid
        if "price" in sid or "fiyat" in sid:
            return "price"
        if "support" in sid:
            return "support_message"
        if "headline" in sid or sid.startswith("başl") or sid.startswith("basl"):
            return "headline"
        if sid == "subheadline":
            return "subheadline"
        return selected_element_id

    low = normalize_tr(instruction)
    # Inflected Turkish stems (başlığı/logoyu/rozeti/fiyatın…)
    stem_map = (
        ("logo", "logo"),
        ("cta", "cta"),
        ("rozet", "badge"),
        ("badge", "badge"),
        ("%25", "badge"),
        ("25%", "badge"),
        ("fiyat", "price"),
        ("price", "price"),
        ("eski fiyat", "old_price"),
        ("old price", "old_price"),
        ("üstü çizili", "old_price"),
        ("başl", "headline"),
        ("basl", "headline"),
        ("headline", "headline"),
        ("destek", "support_message"),
        ("support", "support_message"),
        ("mesaj", "support_message"),
    )
    hits: list[str] = []
    for stem, target in stem_map:
        if stem in low and target not in hits:
            hits.append(target)
    if len(hits) == 1:
        return hits[0]
    return None


def _op(
    *,
    target: str,
    action: str,
    mode: str = "exact",
    confidence: str = "high",
    note: str | None = None,
    priority: str = "exact_numeric",
    **kwargs: Any,
) -> RevisionOperation:
    payload = {
        "target": target if target in {
            "headline", "cta", "badge", "logo", "support_message",
            "price", "background", "layout", "style", "overall",
            "subheadline", "eyebrow", "top_small_description",
            "primary_headline", "left_feature_texts", "feature_text",
        } else ("price" if "price" in target else "overall"),
        "action": action if action in {
            "replace_text", "scale", "resize", "remove", "delete", "tone_adjust", "preserve",
            "minimum_change", "translate", "set_position", "align",
            "set_font_size", "set_color", "hide", "set_geometry",
            "improve_readability",
        } else "minimum_change",
        "mode": mode,
        "confidence": confidence,
        "note": note,
        "priority": priority,
        **kwargs,
    }
    # Allow raw element id via note when target is non-standard
    if target not in {
        "headline", "cta", "badge", "logo", "support_message",
        "price", "background", "layout", "style", "overall",
        "subheadline", "eyebrow", "top_small_description",
        "primary_headline", "left_feature_texts", "feature_text",
    }:
        payload["element_id"] = target
        if payload["target"] == "overall" and action in {
            "translate", "scale", "resize", "set_position", "align", "set_font_size", "set_color",
            "hide", "delete", "remove", "improve_readability",
        }:
            # Prefer price bucket only for price ids; else map text-ish to headline
            if "logo" in target:
                payload["target"] = "logo"
            elif "cta" in target:
                payload["target"] = "cta"
            elif "badge" in target or "rozet" in target:
                payload["target"] = "badge"
            elif "price" in target:
                payload["target"] = "price"
            elif "support" in target:
                payload["target"] = "support_message"
            else:
                payload["target"] = "headline"
    return RevisionOperation.model_validate(payload)


def _strip_quotes(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] in "'\"“”‘’" and v[-1] in "'\"“”‘’":
        return v[1:-1].strip()
    return v


def parse_exact_numeric_ops(
    instruction: str,
    *,
    design_spec: dict[str, Any] | None,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    """Highest priority: font_size=52, logo.y-=40, x=60, cta.y=price.bottom+30."""
    instr = instruction or ""
    low = normalize_tr(instr)
    ops: list[RevisionOperation] = []
    target = resolve_target_from_selection(selected_element_id, instruction) or "headline"

    # font_size=N / font size N / yazı boyutu N
    fs = re.search(
        r"(?:font[_ ]?size|yaz[ıi]\s*boyutu|punto)\s*[=:]?\s*(\d{1,3})",
        low,
    )
    if fs:
        ops.append(
            _op(
                target=target if target != "overall" else "headline",
                action="set_font_size",
                font_size=int(fs.group(1)),
                note=f"font_size={fs.group(1)}",
                priority="exact_numeric",
            )
        )

    # logo.y-=40 / y -= 40 / x=60
    for m in re.finditer(
        r"(logo|başlık|baslik|headline|cta|rozet|badge|fiyat|price)?\s*"
        r"(?:\.|\s)?"
        r"([xy])\s*(?:\-=|\+=|=)\s*(-?\d+(?:\.\d+)?)",
        low,
    ):
        who = m.group(1)
        axis = m.group(2)
        raw = m.group(0)
        val = float(m.group(3))
        t = target
        if who:
            t = resolve_target_from_selection(None, who) or target
        if "-=" in raw.replace(" ", ""):
            dx = -val if axis == "x" else 0.0
            dy = -val if axis == "y" else 0.0
            ops.append(
                _op(
                    target=t,
                    action="translate",
                    dx=dx,
                    dy=dy,
                    note=f"{t}.{axis}-={val:g}",
                    priority="exact_numeric",
                )
            )
        elif "+=" in raw.replace(" ", ""):
            dx = val if axis == "x" else 0.0
            dy = val if axis == "y" else 0.0
            ops.append(
                _op(
                    target=t,
                    action="translate",
                    dx=dx,
                    dy=dy,
                    note=f"{t}.{axis}+={val:g}",
                    priority="exact_numeric",
                )
            )
        else:
            kwargs = {"x": val} if axis == "x" else {"y": val}
            ops.append(
                _op(
                    target=t,
                    action="set_position",
                    note=f"{t}.{axis}={val:g}",
                    priority="exact_numeric",
                    **kwargs,
                )
            )

    # cta.y = price.bottom + 30
    rel = re.search(
        r"(cta|logo|başlık|baslik|headline|rozet|badge)\s*\.?\s*([xy])\s*=\s*"
        r"(fiyat|price|new-?price|old-?price|başlık|baslik|headline|logo|cta|rozet|badge)"
        r"\s*\.?\s*(bottom|top|left|right|centerx|centery|x|y)\s*([+-])\s*(\d+)",
        low,
    )
    if rel and design_spec:
        moving = resolve_target_from_selection(None, rel.group(1)) or "cta"
        ref_name = resolve_target_from_selection(None, rel.group(3)) or "price"
        ref_el = _find_by_target(design_spec, ref_name)
        if ref_el:
            box = element_box(ref_el)
            edge = rel.group(4)
            sign = 1 if rel.group(5) == "+" else -1
            delta = sign * float(rel.group(6))
            edge_map = {
                "bottom": box["bottom"],
                "top": box["top"],
                "left": box["left"],
                "right": box["right"],
                "centerx": box["centerX"],
                "centery": box["centerY"],
                "x": box["x"],
                "y": box["y"],
            }
            base = edge_map.get(edge, box["bottom"])
            axis = rel.group(2)
            abs_val = base + delta
            kwargs = {"y": abs_val} if axis == "y" else {"x": abs_val}
            ops.append(
                _op(
                    target=moving,
                    action="set_position",
                    note=f"{moving}.{axis}={ref_name}.{edge}{rel.group(5)}{rel.group(6)}",
                    priority="exact_numeric",
                    reference_element=ref_name,
                    **kwargs,
                )
            )

    return ops


def _find_by_target(spec: dict[str, Any], target: str) -> dict[str, Any] | None:
    if target == "price":
        return find_element(spec, "new-price", "new_price") or find_element(
            spec, "old-price", "old_price", "price"
        )
    aliases = ROLE_ALIASES.get(target, (target,))
    return find_element(spec, target, *aliases)


def parse_geometric_ops(
    instruction: str,
    *,
    design_spec: dict[str, Any] | None,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    """Relational / self-relative geometric commands (LAYER_ONLY, GPT=0)."""
    if not design_spec:
        return []
    low = normalize_tr(instruction)
    ops: list[RevisionOperation] = []
    cw, ch = _canvas_size(design_spec)
    margin = _safe_margin(design_spec)

    def _who(token: str) -> str:
        t = normalize_tr(token or "")
        if t.startswith("cta"):
            return "cta"
        if t.startswith("logo"):
            return "logo"
        if t.startswith("rozet") or t.startswith("badge") or "25" in t:
            return "badge"
        if t.startswith("fiyat") or t.startswith("price"):
            return "price"
        if t.startswith("başl") or t.startswith("basl") or t.startswith("headline"):
            return "headline"
        return resolve_target_from_selection(None, token) or "logo"

    # Self-relative move: "Logoyu kendi yüksekliği kadar yukarı"
    # and "Başlığı kendi yüksekliğinin yarısı kadar aşağı"
    self_move = re.search(
        r"(logo|başl\w*|basl\w*|headline|cta|rozet\w*|badge|fiyat\w*)\w*.{0,12}"
        r"kendi\s+(yüksekli\w*|geni[sş]li\w*)\s+"
        r"(?:(yar[ıi]s[ıi]|üçte\s*biri|1/2|0\.5)\s+)?"
        r"kadar\s+(yukarı|yukari|aşağı|asagi|sağa|saga|sola)",
        low,
    )
    if self_move:
        target = _who(self_move.group(1))
        el = _find_by_target(design_spec, target)
        if el:
            box = element_box(el)
            dim_token = self_move.group(2)
            use_h = "yüksek" in dim_token
            amount = box["height"] if use_h else box["width"]
            frac = 0.5 if self_move.group(3) else 1.0
            direction = self_move.group(4)
            dx = dy = 0.0
            delta = amount * frac
            if direction in ("yukarı", "yukari"):
                dy = -delta
            elif direction in ("aşağı", "asagi"):
                dy = delta
            elif direction in ("sağa", "saga"):
                dx = delta
            elif direction == "sola":
                dx = -delta
            ops.append(
                _op(
                    target=target,
                    action="translate",
                    dx=dx,
                    dy=dy,
                    note=f"{target} self-{('h' if use_h else 'w')}*{frac} → ({dx:g},{dy:g})",
                    priority="relational_geometric",
                )
            )

    # Logoyu başlıkla sola hizala
    left_align = re.search(
        r"(logo|başl\w*|basl\w*|headline|cta|rozet\w*|badge)\w*.{0,28}"
        r"(başl\w*|basl\w*|headline|fiyat\w*|price|cta|logo|rozet\w*|badge)\w*.{0,16}sola\s+hizala",
        low,
    )
    if left_align:
        moving = _who(left_align.group(1))
        ref = resolve_target_from_selection(None, left_align.group(2)) or "headline"
        ref_el = _find_by_target(design_spec, ref)
        if ref_el:
            ops.append(
                _op(
                    target=moving,
                    action="align",
                    align_edge="left",
                    reference_element=ref,
                    x=element_box(ref_el)["x"],
                    note=f"{moving}.x = {ref}.x",
                    priority="relational_geometric",
                )
            )

    # Rozeti fiyatın sağ kenarına hizala
    right_edge = re.search(
        r"(logo|rozet\w*|badge|cta|başl\w*).{0,36}?"
        r"(fiyat\w*|price|başl\w*|headline|cta|logo).{0,24}?"
        r"sağ\s+kenar",
        low,
    )
    if right_edge:
        moving = _who(right_edge.group(1))
        if "rozet" in right_edge.group(1) or "badge" in right_edge.group(1):
            moving = "badge"
        ref = resolve_target_from_selection(None, right_edge.group(2)) or "price"
        ref_el = _find_by_target(design_spec, ref)
        mov_el = _find_by_target(design_spec, moving)
        if ref_el and mov_el:
            rb = element_box(ref_el)
            mb = element_box(mov_el)
            new_x = rb["right"] - mb["width"]
            ops.append(
                _op(
                    target=moving,
                    action="align",
                    align_edge="right",
                    reference_element=ref,
                    x=new_x,
                    note=f"{moving}.right = {ref}.right",
                    priority="relational_geometric",
                )
            )

    # CTA'yı fiyatın 30 px altına
    below = re.search(
        r"(cta|logo|başl\w*|rozet\w*|badge).{0,36}?"
        r"(fiyat\w*|price|başl\w*|headline|logo).{0,20}?"
        r"(\d+)\s*px\s*(alt[ıi]na|üstüne|ustune|sağ[ıi]na|soluna)",
        low,
    )
    if below:
        moving = _who(below.group(1))
        if below.group(1).startswith("cta"):
            moving = "cta"
        ref = resolve_target_from_selection(None, below.group(2)) or "price"
        px = float(below.group(3))
        where = below.group(4)
        ref_el = _find_by_target(design_spec, ref)
        if ref_el:
            rb = element_box(ref_el)
            if "alt" in where:
                ops.append(
                    _op(
                        target=moving,
                        action="set_position",
                        dy=px,
                        reference_element=ref,
                        note=f"{moving}.y = {ref}.bottom+{px:g}",
                        priority="relational_geometric",
                    )
                )
            elif "üst" in where or "ust" in where:
                mov = _find_by_target(design_spec, moving)
                mh = element_box(mov)["height"] if mov else 0
                ops.append(
                    _op(
                        target=moving,
                        action="set_position",
                        y=rb["top"] - px - mh,
                        reference_element=ref,
                        note=f"{moving}.y = {ref}.top-{px:g}",
                        priority="relational_geometric",
                    )
                )

    # Başlığı canvas'ın tam ortasına
    if ("tam ortas" in low or "ortasına" in low or "ortasina" in low) and (
        "başl" in low or "headline" in low or "canvas" in low
    ):
        target = resolve_target_from_selection(selected_element_id, instruction) or "headline"
        if "başl" in low or "headline" in low:
            target = "headline"
        el = _find_by_target(design_spec, target)
        if el:
            box = element_box(el)
            ops.append(
                _op(
                    target=target,
                    action="align",
                    align_edge="centerX",
                    reference_element="canvas",
                    x=(cw - box["width"]) / 2,
                    note=f"{target} centerX on canvas",
                    priority="relational_geometric",
                )
            )

    # Logoyu sağ üst köşeye ama kenar boşluğunu koru
    if ("sağ üst" in low or "sag ust" in low) and ("köşe" in low or "kose" in low or "logo" in low):
        target = "logo" if "logo" in low else (
            resolve_target_from_selection(selected_element_id, instruction) or "logo"
        )
        el = _find_by_target(design_spec, target)
        if el:
            box = element_box(el)
            ops.append(
                _op(
                    target=target,
                    action="set_position",
                    x=cw - margin - box["width"],
                    y=margin,
                    note=f"{target} top-right safe_margin={margin}",
                    priority="relational_geometric",
                )
            )

    # equalize left/right margins
    if "kenar boşluğunu eşitle" in low or "kenar boslugunu esitle" in low or (
        "sol" in low and "sağ" in low and "eşitle" in low
    ):
        target = resolve_target_from_selection(selected_element_id, instruction) or "headline"
        el = _find_by_target(design_spec, target)
        if el:
            box = element_box(el)
            avg = (box["x"] + (cw - box["right"])) / 2
            # equal L/R → x such that left margin == right margin
            new_x = (cw - box["width"]) / 2
            ops.append(
                _op(
                    target=target,
                    action="set_position",
                    x=new_x,
                    note=f"equalize L/R margins → x={new_x:g} (avg_margin={avg:g})",
                    priority="relational_geometric",
                )
            )

    # bottom margin = horizontal margin
    if "alt boşluk" in low and ("yatay" in low or "kenar" in low):
        target = resolve_target_from_selection(selected_element_id, instruction) or "cta"
        el = _find_by_target(design_spec, target)
        if el:
            box = element_box(el)
            h_margin = min(box["x"], cw - box["right"])
            ops.append(
                _op(
                    target=target,
                    action="set_position",
                    y=ch - h_margin - box["height"],
                    note=f"bottom_margin = horizontal_margin ({h_margin:g})",
                    priority="relational_geometric",
                )
            )

    # halve gap between price and CTA
    if ("yarıya" in low or "yarısına" in low or "halve" in low) and "boşluk" in low and (
        "fiyat" in low or "price" in low
    ) and "cta" in low:
        price = _find_by_target(design_spec, "price")
        cta = _find_by_target(design_spec, "cta")
        if price and cta:
            pb = element_box(price)
            cb = element_box(cta)
            gap = cb["top"] - pb["bottom"]
            ops.append(
                _op(
                    target="cta",
                    action="set_position",
                    y=pb["bottom"] + gap / 2,
                    note=f"halve gap price→cta (was {gap:g})",
                    priority="relational_geometric",
                    reference_element="price",
                )
            )

    # equalize gaps between three elements
    if "boşlukları eşitle" in low or "bosluklari esitle" in low:
        ids = ["logo", "headline", "price"]
        els = [_find_by_target(design_spec, t) for t in ids]
        if all(els):
            boxes = [element_box(e) for e in els]  # type: ignore[arg-type]
            top = boxes[0]["top"]
            bottom = boxes[-1]["bottom"]
            heights = sum(b["height"] for b in boxes)
            free = max(0.0, bottom - top - heights)
            gap = free / 2
            y1 = boxes[0]["bottom"] + gap
            ops.append(
                _op(
                    target="headline",
                    action="set_position",
                    y=y1,
                    note=f"equalize gaps between 3 elements gap={gap:g}",
                    priority="relational_geometric",
                )
            )
            y2 = y1 + boxes[1]["height"] + gap
            ops.append(
                _op(
                    target="price",
                    action="set_position",
                    y=y2,
                    note=f"equalize gaps between 3 elements gap={gap:g}",
                    priority="relational_geometric",
                )
            )

    return ops


def parse_percentage_ops(
    instruction: str,
    *,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    low = normalize_tr(instruction)
    ops: list[RevisionOperation] = []

    # explicit ×1.20
    mult = re.search(
        r"(logo|cta|rozet|badge|başl[ıi][gğ]\w*|headline)?\w*\s*[×x*]\s*(\d+(?:[.,]\d+)?)",
        low,
    )
    if mult:
        t = resolve_target_from_selection(None, mult.group(1) or "") or (
            resolve_target_from_selection(selected_element_id, instruction) or "logo"
        )
        factor = float(mult.group(2).replace(",", "."))
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=factor,
                note=f"{t} ×{factor}",
                priority="percentage",
            )
        )
        return ops

    # "%20 büyüt" / "Logoyu %20 büyüt"
    grow = re.search(
        r"(?:(logo|başl[ıi][gğ]\w*|headline|cta|rozet|badge|fiyat)\w*.{0,20})?"
        r"%\s*(\d+)\s*(?:['’]?[uıi]?)?\s*(?:kadar\s+)?(büyüt|buyut|larger|grow)",
        low,
    )
    shrink = re.search(
        r"(?:(logo|başl[ıi][gğ]\w*|headline|cta|rozet|badge|%25|25\s*%|fiyat)\w*.{0,40})?"
        r"%\s*(\d+)\s*(?:['’]?[uıi]?)?\s*(?:kadar\s+)?(küçült|kucult|smaller)",
        low,
    )
    # also without leading %: "20 büyüt"
    if not grow:
        grow = re.search(
            r"(logo|başl[ıi][gğ]\w*|headline|cta|rozet|badge)\w*.{0,20}"
            r"(\d+)\s*%?\s*(?:['’]?[uıi]?)?\s*(?:kadar\s+)?(büyüt|buyut)",
            low,
        )
    if grow:
        who = grow.group(1) or ""
        t = resolve_target_from_selection(None, who) or (
            resolve_target_from_selection(selected_element_id, instruction) or "logo"
        )
        if "logo" in who:
            t = "logo"
        pct = float(grow.group(2))
        factor = 1.0 + pct / 100.0
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=round(factor, 4),
                note=f"{t} ×{factor:.2f}",
                priority="percentage",
            )
        )
    elif shrink:
        who = shrink.group(1) or ""
        t = resolve_target_from_selection(None, who) or (
            resolve_target_from_selection(selected_element_id, instruction) or "badge"
        )
        if any(x in who for x in ("%25", "25", "rozet", "badge")):
            t = "badge"
        if "logo" in who:
            t = "logo"
        pct = float(shrink.group(2))
        factor = max(0.05, 1.0 - pct / 100.0)
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=round(factor, 4),
                note=f"{t} ×{factor:.2f}",
                priority="percentage",
            )
        )

    # font ×0.80
    font_pct = re.search(
        r"(?:font|yaz[ıi]|punto).{0,20}%?\s*(\d+)\s*(küçült|kucult|büyüt|buyut)",
        low,
    )
    if font_pct:
        pct = float(font_pct.group(1))
        shrink_v = "küç" in font_pct.group(2) or "kucult" in font_pct.group(2)
        factor = (1.0 - pct / 100.0) if shrink_v else (1.0 + pct / 100.0)
        t = resolve_target_from_selection(selected_element_id, instruction) or "headline"
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=round(factor, 4),
                note=f"font ×{factor:.2f}",
                priority="percentage",
            )
        )

    return ops


def parse_relative_nl_ops(
    instruction: str,
    *,
    design_spec: dict[str, Any] | None,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    low = normalize_tr(instruction)
    ops: list[RevisionOperation] = []
    cw, ch = _canvas_size(design_spec)

    # Phrase-local target: "rozetini biraz küçült" beats global ambiguity
    local_target: str | None = None
    local = re.search(
        r"(logo|başl[ıi][gğ][ıi]|headline|cta|rozet|badge|%25|25\s*%|fiyat)\w*.{0,12}"
        r"biraz\s+(küçült|kucult|büyüt|buyut|yukarı|yukari|aşağı|asagi|sağa|saga|sola)",
        low,
    )
    if local:
        local_target = resolve_target_from_selection(None, local.group(1)) or (
            "badge" if any(x in local.group(1) for x in ("rozet", "badge", "25")) else None
        )

    target = local_target or resolve_target_from_selection(selected_element_id, instruction)

    if not target and "biraz" in low:
        # Ambiguous without selection — do not redesign
        return []

    t = target or "headline"

    if "biraz küçült" in low or "biraz kucult" in low:
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=round(1.0 - RELATIVE_NL["biraz_scale"], 4),
                mode="exact",
                confidence="high",
                note=f"biraz küçült → ×{1.0 - RELATIVE_NL['biraz_scale']:.2f}",
                priority="relative_nl",
            )
        )
    elif "biraz büyüt" in low or "biraz buyut" in low:
        ops.append(
            _op(
                target=t,
                action="scale",
                scale_factor=round(1.0 + RELATIVE_NL["biraz_scale"], 4),
                note=f"biraz büyüt → ×{1.0 + RELATIVE_NL['biraz_scale']:.2f}",
                priority="relative_nl",
            )
        )

    if "biraz yukarı" in low or "biraz yukari" in low:
        ops.append(
            _op(
                target=t,
                action="translate",
                dy=-RELATIVE_NL["biraz_up_frac"] * ch,
                note="biraz yukarı",
                priority="relative_nl",
            )
        )
    if "biraz aşağı" in low or "biraz asagi" in low:
        ops.append(
            _op(
                target=t,
                action="translate",
                dy=RELATIVE_NL["biraz_down_frac"] * ch,
                note="biraz aşağı",
                priority="relative_nl",
            )
        )
    if "biraz sağa" in low or "biraz saga" in low:
        ops.append(
            _op(
                target=t,
                action="translate",
                dx=RELATIVE_NL["biraz_right_frac"] * cw,
                note="biraz sağa",
                priority="relative_nl",
            )
        )
    if "biraz sola" in low:
        ops.append(
            _op(
                target=t,
                action="translate",
                dx=-RELATIVE_NL["biraz_left_frac"] * cw,
                note="biraz sola",
                priority="relative_nl",
            )
        )

    return ops


def parse_common_ops(
    instruction: str,
    *,
    production_brief: dict[str, Any] | None,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    """Text replace, hide CTA/old-price, color to project gold — non-geometry commons."""
    instr = instruction or ""
    low = normalize_tr(instr)
    ops: list[RevisionOperation] = []
    pb = production_brief or {}
    final = pb.get("final_copy") if isinstance(pb.get("final_copy"), dict) else {}

    # Headline replace
    quoted_headline = re.search(
        r"(?:başl[ıi][gğ][ıi]|headline)[^\n]*?['\"“”‘’](.+?)['\"“”‘’]",
        instr,
        re.IGNORECASE,
    )
    if quoted_headline:
        headline_to = _strip_quotes(quoted_headline.group(1).strip())
        if headline_to and "daha" not in normalize_tr(headline_to)[:8]:
            ops.append(
                _op(
                    target="headline",
                    action="replace_text",
                    **{"from": str(final.get("headline") or pb.get("hero") or "") or None, "to": headline_to},
                    note="headline replace",
                    priority="exact_numeric",
                )
            )

    # CTA replace
    cta_quoted = re.search(
        r"cta['’]?y?[ıi]?\s*['\"“”‘’](.+?)['\"“”‘’]\s*yap",
        instr,
        re.IGNORECASE,
    )
    if cta_quoted:
        ops.append(
            _op(
                target="cta",
                action="replace_text",
                **{"from": str(final.get("cta") or pb.get("cta") or "") or None, "to": cta_quoted.group(1).strip()},
                note="cta replace",
                priority="exact_numeric",
            )
        )
    elif "cta" in low and "detayları incele" in low and "yap" in low:
        ops.append(
            _op(
                target="cta",
                action="replace_text",
                **{"to": "Detayları İncele"},
                note="cta replace",
                priority="exact_numeric",
            )
        )

    # Hide / remove CTA or old price
    if any(tok in low for tok in ("kaldır", "remove", "gizle", "hide", "sil")):
        if "cta" in low:
            ops.append(
                _op(target="cta", action="hide", note="hide CTA", priority="exact_numeric")
            )
        if any(tok in low for tok in ("eski fiyat", "old price", "üstü çizili", "old-price")):
            ops.append(
                _op(
                    target="price",
                    action="hide",
                    element_id="old-price",
                    note="hide old-price",
                    priority="exact_numeric",
                )
            )
        if any(tok in low for tok in ("rozet", "badge", "%25", "25%")):
            ops.append(
                _op(
                    target="badge",
                    action="delete",
                    element_id="discount-badge",
                    note="hide badge",
                    priority="exact_numeric",
                )
            )
        if any(tok in low for tok in ("sınırlı", "scarcity", "destek", "support")):
            ops.append(
                _op(
                    target="support_message",
                    action="remove",
                    note="remove support/scarcity",
                    priority="exact_numeric",
                )
            )

    # Color to project gold
    if any(tok in low for tok in ("proje altını", "project gold", "altın rengi", "gold")) and any(
        tok in low for tok in ("renk", "color", "yap", "boya")
    ):
        t = resolve_target_from_selection(selected_element_id, instruction) or "cta"
        ops.append(
            _op(
                target=t,
                action="set_color",
                color=PROJECT_GOLD,
                note=f"color → project gold {PROJECT_GOLD}",
                priority="exact_numeric",
            )
        )

    return ops


def parse_subjective_ops(instruction: str, *, existing: list[RevisionOperation]) -> list[RevisionOperation]:
    low = normalize_tr(instruction)
    markers = (
        "daha premium",
        "premium",
        "sade",
        "sadeleştir",
        "kalabalık",
        "satış odaklı",
        "daha modern",
    )
    if not any(m in low for m in markers):
        return []
    if any(o.mode == "exact" and o.action == "replace_text" for o in existing):
        return []
    ops: list[RevisionOperation] = []
    if any(m in low for m in ("premium", "modern")):
        ops.append(
            _op(
                target="headline",
                action="tone_adjust",
                mode="subjective",
                confidence="medium",
                **{"to": "more_premium_tone_same_meaning"},
                note="subjective tone; no bg/logo/price/fact/grade",
                priority="subjective",
            )
        )
    if any(m in low for m in ("sade", "sadeleştir", "kalabalık")):
        ops.append(
            _op(
                target="support_message",
                action="remove",
                mode="subjective",
                confidence="medium",
                note="simplify: remove secondary support",
                priority="subjective",
            )
        )
    if "satış" in low:
        ops.append(
            _op(
                target="cta",
                action="tone_adjust",
                mode="subjective",
                confidence="medium",
                **{"to": "more_sales_focused"},
                priority="subjective",
            )
        )
    return ops[:3]


PRIORITY_RANK = {
    "exact_numeric": 0,
    "relational_geometric": 1,
    "percentage": 2,
    "relative_nl": 3,
    "subjective": 4,
    "ambiguous": 5,
}


def interpret_revision_plan(
    *,
    instruction: str,
    production_brief: dict[str, Any] | None = None,
    design_spec: dict[str, Any] | None = None,
    selected_element_id: str | None = None,
) -> RevisionDiff:
    """Revision Interpreter → Structured Revision Plan (v3 execution lock)."""
    from investhome_api.services.creative_director.revision_intelligence_v3 import (
        interpret_revision_plan_v3,
    )

    return interpret_revision_plan_v3(
        instruction=instruction,
        production_brief=production_brief,
        design_spec=design_spec,
        selected_element_id=selected_element_id,
    )


def snapshot_elements(spec: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(spec, dict):
        return out
    for el in spec.get("elements") or []:
        if isinstance(el, dict) and el.get("id"):
            out[str(el["id"])] = deepcopy(el)
    return out


def _el_fingerprint(el: dict[str, Any]) -> tuple[Any, ...]:
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    return (
        el.get("content"),
        el.get("x"),
        el.get("y"),
        el.get("width"),
        el.get("height"),
        el.get("asset_id"),
        el.get("opacity"),
        typo.get("font_size"),
        typo.get("font_weight"),
        typo.get("color"),
        style.get("background_color"),
        style.get("font_size"),
        style.get("font_weight"),
    )


def validate_change_diff(
    *,
    before: dict[str, dict[str, Any]],
    after_spec: dict[str, Any],
    revision_diff: RevisionDiff | dict[str, Any],
) -> dict[str, Any]:
    """requested vs actual; unexpected mutation → fail for layer-only."""
    after = snapshot_elements(after_spec)
    if isinstance(revision_diff, RevisionDiff):
        ops = revision_diff.operations
        strict = revision_diff.strict_preserve
        requested = revision_diff.requested_changes
    else:
        ops = [
            RevisionOperation.model_validate(o) if isinstance(o, dict) else o
            for o in (revision_diff.get("operations") or [])
        ]
        strict = bool(revision_diff.get("strict_preserve"))
        requested = list(revision_diff.get("requested_changes") or [])

    allowed_targets: set[str] = set()
    for op in ops:
        if op.action in {"minimum_change", "preserve"}:
            continue
        allowed_targets.add(op.target)
        aliases = ROLE_ALIASES.get(op.target, ())
        allowed_targets.update(aliases)
        if op.element_id:
            allowed_targets.add(op.element_id)
        for eid in op.element_ids or []:
            if eid:
                allowed_targets.add(str(eid))

    changed: list[dict[str, Any]] = []
    unexpected: list[str] = []

    all_ids = set(before) | set(after)
    for eid in sorted(all_ids):
        b = before.get(eid)
        a = after.get(eid)
        if b is None and a is not None:
            changed.append({"id": eid, "change": "added"})
            continue
        if a is None and b is not None:
            changed.append({"id": eid, "change": "removed", "previous": b.get("content")})
            roleish = {eid, str(b.get("role") or "")}
            if not (roleish & allowed_targets) and not any(
                eid.startswith(t) or t in eid for t in allowed_targets
            ):
                unexpected.append(eid)
            continue
        if b is None or a is None:
            continue
        if _el_fingerprint(b) != _el_fingerprint(a):
            changed.append(
                {
                    "id": eid,
                    "previous": {
                        "content": b.get("content"),
                        "x": b.get("x"),
                        "y": b.get("y"),
                        "width": b.get("width"),
                        "height": b.get("height"),
                    },
                    "new": {
                        "content": a.get("content"),
                        "x": a.get("x"),
                        "y": a.get("y"),
                        "width": a.get("width"),
                        "height": a.get("height"),
                    },
                }
            )
            roleish = {eid, str(b.get("role") or ""), str(a.get("role") or "")}
            allowed = bool(roleish & allowed_targets) or any(
                t in eid for t in allowed_targets
            )
            # master_background must never mutate on layer-only
            if eid == "master_background":
                unexpected.append("master_background")
            elif not allowed and ops and not all(
                o.action == "minimum_change" for o in ops
            ):
                unexpected.append(eid)

    # Background asset must stay identical
    bg_before = before.get("master_background", {})
    bg_after = after.get("master_background", {})
    bg_unchanged = bg_before.get("asset_id") == bg_after.get("asset_id")

    status = "pass"
    if unexpected and (strict or True):  # always fail unexpected on layer-only path
        # For non-strict, still fail unexpected — ANA KURAL
        status = "fail"
    if not bg_unchanged:
        status = "fail"
        if "master_background" not in unexpected:
            unexpected.append("master_background_asset")

    return {
        "status": status,
        "strict_preserve": strict,
        "changed_elements": changed,
        "unexpected_mutations": unexpected,
        "unexpected_mutation_count": len(unexpected),
        "background_asset_unchanged": bg_unchanged,
        "requested_change_count": len(requested),
        "actual_change_count": len(changed),
    }


def build_user_feedback(
    revision_diff: RevisionDiff | dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> str:
    """Short Turkish user-facing messages — never raw JSON."""
    if isinstance(revision_diff, RevisionDiff):
        ops = revision_diff.operations
        strict = revision_diff.strict_preserve
    else:
        ops = [
            RevisionOperation.model_validate(o) if isinstance(o, dict) else o
            for o in (revision_diff.get("operations") or [])
        ]
        strict = bool(revision_diff.get("strict_preserve"))

    if validation and validation.get("status") == "fail":
        return "Beklenmeyen değişiklik tespit edildi; düzenleme uygulanmadı."

    parts: list[str] = []
    for op in ops:
        if op.action == "minimum_change":
            continue
        label = TARGET_LABELS_TR.get(op.target, op.target)
        if op.action == "replace_text":
            parts.append(f"{label} güncellendi.")
        elif op.action in {"scale", "resize"}:
            parts.append(f"{label} boyutu güncellendi.")
        elif op.action in {"translate", "set_position", "align", "set_geometry"}:
            parts.append(f"{label} konumu güncellendi.")
        elif op.action in {"remove", "hide", "delete"}:
            parts.append(f"{label} kaldırıldı.")
        elif op.action == "improve_readability":
            parts.append(f"{label} okunabilirliği artırıldı.")
        elif op.action == "set_font_size":
            parts.append(f"{label} yazı boyutu güncellendi.")
        elif op.action == "set_color":
            parts.append(f"{label} rengi güncellendi.")
        elif op.action == "tone_adjust":
            parts.append(f"{label} tonu hafifçe güncellendi.")
        else:
            parts.append(f"{label} güncellendi.")

    # Dedupe while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)

    if not uniq:
        if any(o.action == "minimum_change" for o in ops):
            return "Komut belirsiz; tasarım olduğu gibi bırakıldı."
        return "Düzenleme uygulandı."

    msg = " ".join(uniq[:3])
    if strict:
        msg += " Diğer öğeler korundu."
    return msg
