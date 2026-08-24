"""Revision Intelligence v3 — instruction execution lock.

Parse NL into a structured Revision Plan, resolve targets spatially, then apply
only requested layer/property ops. Never send raw NL to an image provider.
"""

from __future__ import annotations

import re
from typing import Any

from investhome_api.schemas.creative_director import RevisionDiff, RevisionOperation
from investhome_api.services.creative_director.revision_intelligence import (
    PRIORITY_RANK,
    _canvas_size,
    _find_by_target,
    _op,
    detect_strict_preserve,
    element_box,
    find_element,
    normalize_tr,
    parse_common_ops,
    parse_exact_numeric_ops,
    parse_geometric_ops,
    parse_percentage_ops,
    parse_relative_nl_ops,
    parse_subjective_ops,
    snapshot_elements,
)

PRESERVE_ONLY_MARKERS = (
    "başka hiçbir",
    "baska hicbir",
    "diğer tüm",
    "diger tum",
    "diğer her şeyi",
    "diger her seyi",
    "geri kalan",
    "görsele dokunma",
    "gorsele dokunma",
    "mevcut yerleşimi kesinlikle",
    "mevcut yerlesimi kesinlikle",
    "kesinlikle değiştirme",
    "kesinlikle degistirme",
    "do not change anything else",
    "don't change anything else",
    "unmentioned",
)

SURGICAL_HINTS = (
    "kaldır",
    "kaldir",
    "sil",
    "gizle",
    "büyüt",
    "buyut",
    "küçült",
    "kucult",
    "taşı",
    "tasi",
    "indir",
    "hizala",
    "ortala",
    "yap",
    "değiştir",
    "degistir",
    "remove",
    "grow",
    "shrink",
    "move",
    "align",
    "okunabilir",
    "kontrast",
    "belirgin",
    "boşluk",
    "bosluk",
)

LOCKED_BG_IDS = {"master_background", "background", "background-gpt-image"}
SKIP_ROLES = {"background", "cover"}


def extract_working_instruction(instruction: str) -> tuple[str, bool]:
    """Drop preserve-only clauses so logo/CTA mentions cannot pollute targeting."""
    strict = detect_strict_preserve(instruction)
    clauses = _split_clauses(instruction)
    working: list[str] = []
    for clause in clauses:
        head, preserve_tail = _split_preserve_tail(clause)
        if preserve_tail:
            strict = True
        if head and not _is_preserve_only(head):
            working.append(head)
        elif not head:
            continue
        elif _is_preserve_only(clause) and not _has_surgical_hint(normalize_tr(clause)):
            continue
        elif head:
            working.append(head)
    return " ".join(working).strip() or (instruction or "").strip(), strict


def _split_clauses(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", raw)
    return [p.strip() for p in parts if p.strip()]


def _has_surgical_hint(low: str) -> bool:
    """True when the clause contains a real edit verb.

    'değiştirme' / 'dokunma' must not count as 'değiştir' — they are preserve verbs.
    """
    cleaned = low
    for token in (
        "değiştirme",
        "degistirme",
        "dokunma",
        "koru",
        "koruyun",
        "aynı bırak",
        "ayni birak",
    ):
        cleaned = cleaned.replace(token, " ")
    return any(h in cleaned for h in SURGICAL_HINTS)


def _is_preserve_only(clause: str) -> bool:
    low = normalize_tr(clause)
    if not any(m in low for m in PRESERVE_ONLY_MARKERS):
        return False
    # "sadece logoyu değiştir" is surgical + strict, not preserve-only.
    if low.strip().startswith("sadece ") and _has_surgical_hint(low):
        return False
    starts_preserve = any(low.startswith(m) for m in PRESERVE_ONLY_MARKERS)
    has_action = _has_surgical_hint(low)
    if starts_preserve and not has_action:
        return True
    if any(m in low for m in PRESERVE_ONLY_MARKERS) and not has_action:
        return True
    return starts_preserve and not has_action


def _split_preserve_tail(clause: str) -> tuple[str, bool]:
    low = normalize_tr(clause)
    cut_at: int | None = None
    for marker in PRESERVE_ONLY_MARKERS:
        idx = low.find(marker)
        if idx >= 0 and (cut_at is None or idx < cut_at):
            cut_at = idx
    if cut_at is None:
        return clause.strip(), False
    if cut_at == 0:
        return "", True
    return clause[:cut_at].strip(" ,;."), True


def _font_size(el: dict[str, Any] | None) -> float:
    if not isinstance(el, dict):
        return 0.0
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    for bag in (typo, style, el):
        raw = bag.get("font_size") if bag is not el else el.get("fontSize")
        if raw is None and bag is el:
            raw = el.get("font_size")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return float(el.get("height") or 0)


def _font_weight(el: dict[str, Any] | None) -> str:
    if not isinstance(el, dict):
        return "normal"
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    return str(typo.get("font_weight") or style.get("font_weight") or el.get("fontWeight") or "normal")


def _color(el: dict[str, Any] | None) -> str:
    if not isinstance(el, dict):
        return ""
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    return str(typo.get("color") or style.get("text_color") or el.get("color") or "")


def _is_overlay_text(el: dict[str, Any]) -> bool:
    eid = str(el.get("id") or "").lower()
    role = str(el.get("role") or "").lower()
    etype = str(el.get("type") or "").lower()
    if eid in LOCKED_BG_IDS or role in SKIP_ROLES:
        return False
    if etype in {"image", "logo", "cta", "button", "shape", "rectangle", "line", "divider", "gradient", "overlay"}:
        return etype in {"badge"} or role in {"discount_badge", "badge"}
    if role in {"logo", "cta", "background"}:
        return False
    if etype in {"text", "badge"}:
        return True
    if role in {
        "headline",
        "subheadline",
        "support_message",
        "unit_label",
        "eyebrow",
        "body",
        "old_price",
        "new_price",
        "discount_badge",
    }:
        return True
    return bool(el.get("content") and etype not in {"image", "logo"})


def _overlay_texts(spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(spec, dict):
        return []
    out: list[dict[str, Any]] = []
    for el in spec.get("elements") or []:
        if isinstance(el, dict) and _is_overlay_text(el):
            out.append(el)
    return out


def _ids_of(els: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for el in els:
        eid = str(el.get("id") or "")
        if eid and eid not in ids:
            ids.append(eid)
    return ids


def _paired_frame_ids(spec: dict[str, Any] | None, text_ids: list[str]) -> list[str]:
    """Include eyebrow-pill / feature dots that exist only as frames for deleted text."""
    extra: list[str] = []
    lowered = {i.lower() for i in text_ids}
    if any(i in {"unit-label", "subheadline", "eyebrow", "top-description"} for i in lowered):
        if find_element(spec, "eyebrow-pill"):
            extra.append("eyebrow-pill")
    for eid in list(text_ids):
        m = re.match(r"(?:feature|support-message)-(\d+)$", eid.lower())
        if m and find_element(spec, f"feature-dot-{m.group(1)}", f"shape-feature-{m.group(1)}"):
            for cand in (f"feature-dot-{m.group(1)}", f"shape-feature-{m.group(1)}"):
                if find_element(spec, cand):
                    extra.append(cand)
    return extra


def resolve_spatial_targets(
    spec: dict[str, Any] | None,
    phrase: str,
    *,
    selected_element_id: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Map a NL noun phrase to (semantic_target, elements). Never pick at random."""
    low = normalize_tr(phrase)
    if not spec:
        return _semantic_from_phrase(low, selected_element_id), []

    cw, ch = _canvas_size(spec)
    texts = _overlay_texts(spec)

    if "logo" in low:
        el = _find_by_target(spec, "logo")
        return "logo", [el] if el else []
    if "cta" in low or "buton" in low or "düğme" in low or "dugme" in low:
        el = _find_by_target(spec, "cta")
        return "cta", [el] if el else []
    if any(tok in low for tok in ("rozet", "badge", "%25", "25%")):
        el = _find_by_target(spec, "badge")
        return "badge", [el] if el else []
    if any(tok in low for tok in ("eski fiyat", "old price", "üstü çizili")):
        el = find_element(spec, "old-price", "old_price")
        return "price", [el] if el else []
    if "fiyat" in low or "price" in low:
        el = _find_by_target(spec, "price")
        return "price", [el] if el else []

    if any(
        tok in low
        for tok in (
            "üstteki küçük",
            "ustteki kucuk",
            "üstteki yazı",
            "ustteki yazi",
            "küçük açıklama",
            "kucuk aciklama",
            "üstteki açıklama",
            "ustteki aciklama",
            "küçük metin",
            "kucuk metin",
            "üstteki metin",
        )
    ):
        headline = _find_by_target(spec, "headline")
        hl_id = str(headline.get("id") or "") if headline else ""
        ranked = [
            e
            for e in texts
            if str(e.get("id") or "") != hl_id
            and str(e.get("role") or "").lower() not in {
                "headline",
                "discount_badge",
                "badge",
                "cta",
                "logo",
            }
            and not str(e.get("id") or "").lower().startswith("discount")
        ]
        ranked.sort(key=lambda e: (float(e.get("y") or 0), _font_size(e)))
        top = [e for e in ranked if float(e.get("y") or 0) <= ch * 0.50]
        preferred_ids = {"top-description", "subheadline", "unit-label", "eyebrow"}
        preferred_roles = {"subheadline", "unit_label", "eyebrow"}
        preferred = [
            e
            for e in (top or ranked)
            if str(e.get("id") or "").lower() in preferred_ids
            or str(e.get("role") or "").lower() in preferred_roles
        ]
        pick = (preferred or top or ranked)[:1]
        return "top_small_description", pick

    if any(
        tok in low
        for tok in (
            "özellik",
            "ozellik",
            "feature",
            "soldaki iki",
            "sol taraftaki",
            "iki açıklama",
            "iki aciklama",
            "soldaki iki açıklama",
            "soldaki iki aciklama",
        )
    ):
        feats: list[dict[str, Any]] = []
        for e in texts:
            eid = str(e.get("id") or "").lower()
            role = str(e.get("role") or "").lower()
            if (
                eid.startswith("feature-")
                or eid.startswith("support-message")
                or role in {"support_message", "body"}
            ):
                if role == "headline":
                    continue
                feats.append(e)
        n = 2 if ("iki" in low or "2" in low) else min(2, len(feats) or 1)
        if "üç" in low or "uc " in low or "3" in low:
            n = min(3, len(feats))
        left = [
            e
            for e in feats
            if (float(e.get("x") or 0) + float(e.get("width") or 0) / 2.0) < cw * 0.55
        ]
        pool = left if ("sol" in low and len(left) >= n) or len(left) >= n else feats
        pool = sorted(pool, key=lambda e: (float(e.get("x") or 0), float(e.get("y") or 0)))
        return "left_feature_texts", pool[: max(1, n)] if pool else []

    if any(tok in low for tok in ("ikinci madde", "ikinci açıklama", "ikinci aciklama", "2. madde")):
        supports = [
            e
            for e in texts
            if str(e.get("role") or "").lower() == "support_message"
            or str(e.get("id") or "").lower().startswith("support-message")
            or str(e.get("id") or "").lower().startswith("feature-")
        ]
        supports.sort(key=lambda e: (float(e.get("y") or 0), float(e.get("x") or 0)))
        if len(supports) >= 2:
            return "support_message", [supports[1]]
        return "support_message", supports[-1:]

    if "ana başl" in low or "ana basl" in low or (
        ("başl" in low or "basl" in low or "headline" in low)
        and "küçük" not in low
        and "alt başl" not in low
    ):
        el = _find_by_target(spec, "headline")
        return "primary_headline", [el] if el else []

    if selected_element_id:
        el = find_element(spec, selected_element_id)
        if el:
            return str(el.get("role") or selected_element_id), [el]

    return _semantic_from_phrase(low, selected_element_id), []


def _semantic_from_phrase(low: str, selected: str | None) -> str:
    if "logo" in low:
        return "logo"
    if "cta" in low:
        return "cta"
    if "rozet" in low or "badge" in low or "%25" in low:
        return "badge"
    if "özellik" in low or "ozellik" in low or "feature" in low:
        return "left_feature_texts"
    if "ana başl" in low or "başl" in low or "headline" in low:
        return "primary_headline"
    if "açıklama" in low or "aciklama" in low or "üstteki" in low:
        return "top_small_description"
    if selected:
        return selected
    return "overall"


def _bind_op(
    *,
    semantic: str,
    action: str,
    elements: list[dict[str, Any]],
    **kwargs: Any,
) -> RevisionOperation:
    ids = _ids_of(elements)
    schema_target = {
        "primary_headline": "headline",
        "top_small_description": "top_small_description",
        "left_feature_texts": "left_feature_texts",
        "feature_text": "feature_text",
        "headline": "headline",
        "cta": "cta",
        "badge": "badge",
        "logo": "logo",
        "support_message": "support_message",
        "price": "price",
        "subheadline": "subheadline",
        "eyebrow": "eyebrow",
    }.get(semantic, "overall")
    if schema_target == "overall" and semantic in {"headline", "primary_headline"}:
        schema_target = "headline"
    payload_ids = ids
    extra: dict[str, Any] = dict(kwargs)
    if payload_ids:
        extra["element_id"] = payload_ids[0]
        extra["element_ids"] = payload_ids
    extra["semantic_target"] = semantic
    return _op(target=schema_target, action=action, **extra)


def parse_v3_clause_ops(
    clause: str,
    *,
    design_spec: dict[str, Any] | None,
    selected_element_id: str | None,
) -> list[RevisionOperation]:
    instr = (clause or "").strip()
    if not instr:
        return []
    low = normalize_tr(instr)
    ops: list[RevisionOperation] = []
    semantic, elements = resolve_spatial_targets(
        design_spec, instr, selected_element_id=selected_element_id
    )

    # ── delete / hide ──────────────────────────────────────────────────────
    if any(tok in low for tok in ("kaldır", "kaldir", "sil", "gizle", "remove", "hide")):
        ids = _ids_of(elements)
        ids.extend(_paired_frame_ids(design_spec, ids))
        bound = list(elements)
        for fid in ids:
            found = find_element(design_spec, fid)
            if found and found not in bound:
                bound.append(found)
        if bound or semantic != "overall":
            ops.append(
                _bind_op(
                    semantic=semantic,
                    action="delete",
                    elements=bound,
                    note=f"delete {semantic}",
                    priority="exact_numeric",
                )
            )

    # ── percentage resize (all matches in the clause) ───────────────────────
    for m in re.finditer(
        r"%\s*(\d+)\s*(?:['’]?[uıi]?)?\s*(?:kadar\s+)?(büyüt|buyut|küçült|kucult|grow|larger|smaller)",
        low,
    ):
        pct = float(m.group(1))
        shrink = any(tok in m.group(2) for tok in ("küç", "kucult", "smaller"))
        factor = max(0.05, (1.0 - pct / 100.0) if shrink else (1.0 + pct / 100.0))
        if elements or semantic != "overall":
            ops.append(
                _bind_op(
                    semantic=semantic,
                    action="scale",
                    elements=elements,
                    scale_factor=round(factor, 4),
                    value=round(factor, 4),
                    note=f"{semantic} ×{factor:.2f}",
                    priority="percentage",
                )
            )

    # ── self-relative move: "kendi yüksekliği kadar yukarı" ─────────────────
    self_rel = re.search(
        r"kendi\s+(yüksekli\w*|geni[sş]li\w*)(?:nin)?\s+(?:(yar[ıi]s[ıi])\s+)?"
        r"kadar\s+(yukarı|yukari|aşağı|asagi|indir|sağa|saga|sola)",
        low,
    )
    if self_rel and elements:
        box = element_box(elements[0])
        use_h = "yüksek" in self_rel.group(1)
        amount = box["height"] if use_h else box["width"]
        if self_rel.group(2):
            amount *= 0.5
        direction = self_rel.group(3)
        dx = dy = 0.0
        if direction in ("yukarı", "yukari"):
            dy = -amount
        elif direction in ("aşağı", "asagi", "indir"):
            dy = amount
        elif direction in ("sağa", "saga"):
            dx = amount
        else:
            dx = -amount
        ops.append(
            _bind_op(
                semantic=semantic,
                action="translate",
                elements=elements,
                dx=dx,
                dy=dy,
                note=f"{semantic} self-relative ({dx:g},{dy:g})",
                priority="relational_geometric",
            )
        )

    # ── exact px move ───────────────────────────────────────────────────────
    px_move = re.search(
        r"(\d+)\s*px\s*(yukarı|yukari|aşağı|asagi|sola|sağa|saga)",
        low,
    )
    if px_move:
        amount = float(px_move.group(1))
        direction = px_move.group(2)
        dx = dy = 0.0
        if direction in ("yukarı", "yukari"):
            dy = -amount
        elif direction in ("aşağı", "asagi"):
            dy = amount
        elif direction == "sola":
            dx = -amount
        else:
            dx = amount
        if elements or semantic != "overall":
            ops.append(
                _bind_op(
                    semantic=semantic,
                    action="translate",
                    elements=elements,
                    dx=dx,
                    dy=dy,
                    note=f"{semantic} ({dx:g},{dy:g})",
                    priority="exact_numeric",
                )
            )

    # ── "biraz sola/sağa/yukarı/aşağı" ──────────────────────────────────────
    cw, ch = _canvas_size(design_spec)
    if "biraz sola" in low:
        ops.append(
            _bind_op(
                semantic=semantic,
                action="translate",
                elements=elements,
                dx=-0.025 * cw,
                note="biraz sola",
                priority="relative_nl",
            )
        )
    if "biraz sağa" in low or "biraz saga" in low:
        ops.append(
            _bind_op(
                semantic=semantic,
                action="translate",
                elements=elements,
                dx=0.025 * cw,
                note="biraz sağa",
                priority="relative_nl",
            )
        )

    # ── alignment ───────────────────────────────────────────────────────────
    if "ortala" in low or "ortasına" in low or "ortasina" in low:
        el = elements[0] if elements else None
        if el:
            box = element_box(el)
            ops.append(
                _bind_op(
                    semantic=semantic,
                    action="align",
                    elements=elements,
                    align_edge="centerX",
                    reference_element="canvas",
                    x=(cw - box["width"]) / 2,
                    note=f"{semantic} centerX",
                    priority="relational_geometric",
                )
            )
    if re.search(r"sağa\s+hizala|saga\s+hizala", low):
        el = elements[0] if elements else None
        if el:
            box = element_box(el)
            ops.append(
                _bind_op(
                    semantic=semantic,
                    action="align",
                    elements=elements,
                    align_edge="right",
                    reference_element="canvas",
                    x=cw - 48 - box["width"],
                    note=f"{semantic} right",
                    priority="relational_geometric",
                )
            )
    same_align = re.search(
        r"(cta|logo|başl\w*|headline).{0,24}(başl\w*|headline|cta|logo).{0,16}ayn[ıi]\s+hiz",
        low,
    )
    if same_align:
        moving_s, moving_els = resolve_spatial_targets(
            design_spec, same_align.group(1), selected_element_id=selected_element_id
        )
        ref_s, ref_els = resolve_spatial_targets(
            design_spec, same_align.group(2), selected_element_id=selected_element_id
        )
        if moving_els and ref_els:
            ops.append(
                _bind_op(
                    semantic=moving_s,
                    action="align",
                    elements=moving_els,
                    align_edge="left",
                    reference_element=ref_s,
                    x=element_box(ref_els[0])["x"],
                    note=f"{moving_s}.x = {ref_s}.x",
                    priority="relational_geometric",
                )
            )

    # ── gap between two named elements % ────────────────────────────────────
    gap = re.search(
        r"(logo|başl\w*|headline|cta).{0,8}ile.{0,8}(logo|başl\w*|headline|cta)"
        r".{0,36}mesafe.{0,16}%\s*(\d+)\s*(artır|artir|azalt)",
        low,
    )
    if gap and design_spec:
        a_s, a_els = resolve_spatial_targets(design_spec, gap.group(1), selected_element_id=None)
        b_s, b_els = resolve_spatial_targets(design_spec, gap.group(2), selected_element_id=None)
        if a_els and b_els:
            aa, bb = element_box(a_els[0]), element_box(b_els[0])
            if aa["top"] <= bb["top"]:
                upper, lower, lower_s, lower_els = aa, bb, b_s, b_els
            else:
                upper, lower, lower_s, lower_els = bb, aa, a_s, a_els
            current_gap = lower["top"] - upper["bottom"]
            pct = float(gap.group(3)) / 100.0
            grow = "azalt" not in gap.group(4)
            new_gap = current_gap * (1.0 + pct) if grow else current_gap * max(0.05, 1.0 - pct)
            dy = new_gap - current_gap
            ops.append(
                _bind_op(
                    semantic=lower_s,
                    action="translate",
                    elements=lower_els,
                    dy=dy,
                    note=f"gap {a_s}→{b_s} {gap.group(4)} {gap.group(3)}%",
                    priority="relational_geometric",
                )
            )

    # ── "sağ ve soldaki boşluk kadar aşağıda da boşluk bırak" ────────────────
    if re.search(
        r"(sağ|sag).{0,12}(sol).{0,24}boşluk.{0,24}aşağı|asagi",
        low,
    ) or re.search(r"sağ ve soldaki boşluk kadar aşağı", low):
        if design_spec:
            overlays = [
                e
                for e in (design_spec.get("elements") or [])
                if isinstance(e, dict)
                and str(e.get("id") or "").lower() not in LOCKED_BG_IDS
                and str(e.get("role") or "").lower() not in SKIP_ROLES
            ]
            if overlays:
                left_m = min(float(e.get("x") or 0) for e in overlays)
                right_m = min(
                    cw - (float(e.get("x") or 0) + float(e.get("width") or 0)) for e in overlays
                )
                h_margin = min(left_m, right_m)
                lowest = max(overlays, key=lambda e: float(e.get("y") or 0) + float(e.get("height") or 0))
                box = element_box(lowest)
                new_y = ch - h_margin - box["height"]
                lowest_sem, lowest_els = resolve_spatial_targets(
                    design_spec,
                    str(lowest.get("role") or lowest.get("id") or "cta"),
                    selected_element_id=None,
                )
                ops.append(
                    _bind_op(
                        semantic=lowest_sem if lowest_els else "cta",
                        action="set_position",
                        elements=lowest_els or [lowest],
                        y=new_y,
                        note=f"bottom_margin={h_margin:g} from L/R",
                        priority="relational_geometric",
                    )
                )

    # ── CTA / bottom gap reduce ─────────────────────────────────────────────
    if re.search(r"cta.{0,36}alt.{0,20}mesafe.{0,16}azalt", low) and design_spec:
        cta = _find_by_target(design_spec, "cta")
        if cta:
            box = element_box(cta)
            gap_now = ch - box["bottom"]
            ops.append(
                _bind_op(
                    semantic="cta",
                    action="set_position",
                    elements=[cta],
                    y=box["y"] + gap_now * 0.5,
                    note="reduce CTA bottom gap by 50%",
                    priority="relational_geometric",
                )
            )

    # ── text replace: başlığı X yap ─────────────────────────────────────────
    quoted = re.search(
        r"(?:başl[ıi][gğ][ıi]|headline)[^\n]*?['\"“”‘’](.+?)['\"“”‘’]",
        instr,
        re.IGNORECASE,
    )
    unquoted = re.search(
        r"(?:ana\s+)?(?:başl[ıi][gğ][ıi]|headline)\s+(.+?)\s+yap",
        instr,
        re.IGNORECASE,
    )
    replacement = None
    if quoted:
        replacement = quoted.group(1).strip()
    elif unquoted:
        candidate = unquoted.group(1).strip().strip("'\"“”‘’")
        cl = normalize_tr(candidate)
        if candidate and not any(
            tok in cl for tok in ("büyüt", "küçült", "taşı", "kaldır", "%", "okunabilir")
        ):
            replacement = candidate
    if replacement:
        hl = elements if semantic in {"primary_headline", "headline"} else (
            [_find_by_target(design_spec, "headline")] if design_spec else []
        )
        hl = [e for e in hl if e]
        ops.append(
            _bind_op(
                semantic="primary_headline",
                action="replace_text",
                elements=hl,
                **{"to": replacement},
                note="headline replace",
                priority="exact_numeric",
            )
        )

    desc_quoted = re.search(
        r"(?:açıklama|aciklama|description)[^\n]*?['\"“”‘’](.+?)['\"“”‘’]",
        instr,
        re.IGNORECASE,
    )
    if desc_quoted:
        ops.append(
            _bind_op(
                semantic=semantic if semantic != "overall" else "top_small_description",
                action="replace_text",
                elements=elements,
                **{"to": desc_quoted.group(1).strip()},
                note="description replace",
                priority="exact_numeric",
            )
        )

    # ── readability ─────────────────────────────────────────────────────────
    if any(
        tok in low
        for tok in (
            "okunabilir",
            "kontrastı artır",
            "kontrasti artir",
            "daha belirgin",
            "biraz daha belirgin",
        )
    ):
        ops.append(
            _bind_op(
                semantic=semantic,
                action="improve_readability",
                elements=elements,
                note=f"improve_readability {semantic}",
                priority="exact_numeric",
            )
        )

    return ops


def dump_semantic_plan(diff: RevisionDiff) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    for op in diff.operations:
        if op.action in {"minimum_change", "preserve"}:
            continue
        action = {
            "remove": "delete",
            "hide": "delete",
            "scale": "resize",
        }.get(op.action, op.action)
        row: dict[str, Any] = {
            "action": action,
            "target": op.semantic_target or op.target,
        }
        if op.scale_factor is not None or op.value is not None:
            row["mode"] = "relative"
            row["value"] = op.value if op.value is not None else op.scale_factor
        if op.element_ids:
            row["element_ids"] = list(op.element_ids)
        elif op.element_id:
            row["element_ids"] = [op.element_id]
        if op.dx or op.dy:
            row["dx"] = op.dx
            row["dy"] = op.dy
        if op.to_value:
            row["to"] = op.to_value
        operations.append(row)
    preserve = list(diff.preserve)
    return {"operations": operations, "preserve": preserve}


def validate_execution(
    *,
    before: dict[str, dict[str, Any]],
    after_spec: dict[str, Any],
    revision_diff: RevisionDiff | dict[str, Any],
) -> dict[str, Any]:
    """Every requested op must be observable on the after spec."""
    after = snapshot_elements(after_spec)
    if isinstance(revision_diff, RevisionDiff):
        ops = [o for o in revision_diff.operations if o.action not in {"minimum_change", "preserve"}]
    else:
        ops = [
            RevisionOperation.model_validate(o) if isinstance(o, dict) else o
            for o in (revision_diff.get("operations") or [])
            if str(getattr(o, "action", None) or (o.get("action") if isinstance(o, dict) else ""))
            not in {"minimum_change", "preserve"}
        ]

    checks: list[dict[str, Any]] = []

    def _target_ids(op: RevisionOperation) -> list[str]:
        ids: list[str] = []
        for i in op.element_ids or []:
            if i:
                ids.append(str(i))
        if op.element_id and str(op.element_id) not in ids:
            ids.append(str(op.element_id))
        if not ids:
            aliases = {
                "primary_headline": ["headline"],
                "headline": ["headline"],
                "cta": ["cta"],
                "logo": ["logo"],
                "badge": ["discount-badge", "badge"],
            }.get(op.target, [op.target])
            ids.extend(aliases)
        return ids

    for op in ops:
        action = op.action
        ids = _target_ids(op)
        passed = True
        detail: dict[str, Any] = {"action": action, "target": op.semantic_target or op.target, "ids": ids}

        if action in {"delete", "remove", "hide"}:
            passed = all(i not in after for i in ids if i in before or True) and all(
                i not in after for i in ids
            )
            detail["exists"] = {i: i in after for i in ids}
        elif action in {"resize", "scale"} and op.scale_factor:
            factor = float(op.scale_factor)
            for i in ids:
                b, a = before.get(i), after.get(i)
                if not b or not a:
                    passed = False
                    continue
                bfs, afs = _font_size(b), _font_size(a)
                if bfs > 0:
                    if abs(afs - bfs * factor) > 1.5:
                        passed = False
                else:
                    bw = float(b.get("width") or 0)
                    aw = float(a.get("width") or 0)
                    if bw > 0 and abs(aw - bw * factor) > 2:
                        passed = False
            detail["scale_factor"] = factor
        elif action == "translate":
            for i in ids:
                b, a = before.get(i), after.get(i)
                if not b or not a:
                    passed = False
                    continue
                exp_x = float(b.get("x") or 0) + float(op.dx or 0)
                exp_y = float(b.get("y") or 0) + float(op.dy or 0)
                if abs(float(a.get("x") or 0) - exp_x) > 1.5 or abs(float(a.get("y") or 0) - exp_y) > 1.5:
                    passed = False
        elif action in {"set_position", "align"}:
            for i in ids:
                a = after.get(i)
                b = before.get(i)
                if not a or not b:
                    passed = False
                    continue
                if op.x is not None and abs(float(a.get("x") or 0) - float(op.x)) > 1.5:
                    passed = False
                if op.y is not None and abs(float(a.get("y") or 0) - float(op.y)) > 1.5:
                    passed = False
                if op.x is None and op.y is None:
                    if _el_box_tuple(b) == _el_box_tuple(a):
                        passed = False
        elif action == "replace_text":
            expected = op.to_value
            found = False
            for i in ids:
                a = after.get(i)
                if a and expected and str(a.get("content") or "") == str(expected):
                    found = True
            passed = found
        elif action == "improve_readability":
            for i in ids:
                b, a = before.get(i), after.get(i)
                if not b or not a:
                    passed = False
                    continue
                weight_up = _weight_rank(_font_weight(a)) > _weight_rank(_font_weight(b))
                color_changed = _color(a) != _color(b)
                if not (weight_up or color_changed):
                    passed = False
        elif action == "set_font_size" and op.font_size is not None:
            for i in ids:
                a = after.get(i)
                if not a or abs(_font_size(a) - float(op.font_size)) > 1:
                    passed = False
        detail["pass"] = passed
        checks.append(detail)

    status = "pass" if checks and all(c["pass"] for c in checks) else (
        "pass" if not checks else "fail"
    )
    return {
        "status": status,
        "checks": checks,
        "requested_operation_count": len(ops),
        "passed_operation_count": sum(1 for c in checks if c["pass"]),
    }


def _el_box_tuple(el: dict[str, Any]) -> tuple[Any, ...]:
    return (el.get("x"), el.get("y"), el.get("width"), el.get("height"))


def _weight_rank(weight: str) -> int:
    order = {"normal": 0, "regular": 0, "medium": 1, "semibold": 2, "semi-bold": 2, "bold": 3}
    return order.get((weight or "normal").lower(), 0)


def interpret_revision_plan_v3(
    *,
    instruction: str,
    production_brief: dict[str, Any] | None = None,
    design_spec: dict[str, Any] | None = None,
    selected_element_id: str | None = None,
) -> RevisionDiff:
    instr = (instruction or "").strip()
    working, strict = extract_working_instruction(instr)
    if detect_strict_preserve(instr):
        strict = True

    preserve = [
        "background",
        "image",
        "logo",
        "cta",
        "colors",
        "layout",
        "all_unmentioned_elements",
        "exposure",
        "brightness",
        "white_balance",
        "contrast",
        "sharpness",
        "resolution",
        "architectural_interior_details",
        "composition_unless_requested",
        "logo_quality",
        "unaffected_typography",
        "verified_prices",
        "project_logo",
        "background_photograph",
        "unaffected_elements",
        "positions_unless_requested",
        "colors_unless_requested",
        "layout_unless_requested",
        "image_crop",
        "image_brightness",
        "image_contrast",
        "image_quality",
        "aspect_ratio",
    ]
    forbidden = [
        "darkening",
        "recoloring",
        "cinematic_grading",
        "contrast_increase",
        "vignette",
        "blur_changes",
        "sharpening_changes",
        "crop_changes",
        "lighting_changes",
        "full_redesign",
        "generation_from_prior_revision_raster",
        "unexpected_mutations",
        "image_provider_for_layer_ops",
    ]
    if strict:
        for item in ("prices", "logo", "cta", "background", "image_treatment", "unaffected_elements"):
            if item not in preserve:
                preserve.append(item)
        forbidden.append("any_mutation_outside_plan")

    buckets: list[RevisionOperation] = []
    clauses = _split_clauses(working) or [working]
    for clause in clauses:
        v3_ops = parse_v3_clause_ops(
            clause, design_spec=design_spec, selected_element_id=selected_element_id
        )
        if v3_ops:
            # v3 owned this clause — do not let legacy parsers duplicate scales.
            buckets.extend(v3_ops)
            continue
        buckets.extend(
            parse_exact_numeric_ops(
                clause, design_spec=design_spec, selected_element_id=selected_element_id
            )
        )
        buckets.extend(
            parse_geometric_ops(
                clause, design_spec=design_spec, selected_element_id=selected_element_id
            )
        )
        buckets.extend(parse_percentage_ops(clause, selected_element_id=selected_element_id))
        buckets.extend(
            parse_relative_nl_ops(
                clause, design_spec=design_spec, selected_element_id=selected_element_id
            )
        )
        buckets.extend(
            parse_common_ops(
                clause,
                production_brief=production_brief,
                selected_element_id=selected_element_id,
            )
        )
    buckets.extend(parse_subjective_ops(working, existing=buckets))

    seen: set[str] = set()
    ops: list[RevisionOperation] = []

    def _canon_target(op: RevisionOperation) -> str:
        if op.element_ids:
            return ",".join(sorted(op.element_ids))
        if op.element_id:
            return str(op.element_id)
        return {
            "primary_headline": "headline",
            "headline": "headline",
            "top_small_description": "subheadline",
            "left_feature_texts": "support_message",
            "feature_text": "support_message",
        }.get(op.target, op.target)

    def _action_family(action: str) -> str:
        if action in {"scale", "resize"}:
            return "resize"
        if action in {"hide", "remove", "delete"}:
            return "delete"
        if action in {"translate", "set_position", "align"}:
            return "move"
        return action

    for op in sorted(buckets, key=lambda o: PRIORITY_RANK.get(o.priority or "exact_numeric", 9)):
        family = _action_family(op.action)
        canon = _canon_target(op)
        if family in {"resize", "delete", "improve_readability"}:
            key = f"{canon}:{family}"
        elif family == "replace_text":
            key = f"{canon}:{family}:{op.to_value}"
        else:
            key = (
                f"{canon}:{family}:"
                f"{op.to_value}:{op.scale_factor}:{op.dx}:{op.dy}:{op.x}:{op.y}"
            )
        if key in seen:
            continue
        seen.add(key)
        ops.append(op)

    exactish = [o for o in ops if o.mode != "subjective"]
    subjective = [o for o in ops if o.mode == "subjective"][:3]
    ops = exactish + subjective

    low = normalize_tr(working)
    if not ops:
        if "biraz" in low and not selected_element_id:
            ops.append(
                RevisionOperation(
                    target="overall",
                    action="minimum_change",
                    confidence="low",
                    mode="ambiguous",
                    priority="ambiguous",
                    note="Ambiguous without selected element — no whole-design rewrite",
                )
            )
        else:
            ops.append(
                RevisionOperation(
                    target="overall",
                    action="minimum_change",
                    confidence="low",
                    mode="ambiguous",
                    priority="ambiguous",
                    note="Ambiguous instruction — apply minimum visible change only",
                )
            )

    if any(o.mode == "exact" for o in ops) and not any(o.mode == "subjective" for o in ops):
        command_mode: str = "exact"
    elif any(o.mode == "subjective" for o in ops) and not any(o.mode == "exact" for o in ops):
        command_mode = "subjective"
    elif any(o.mode == "exact" for o in ops) and any(o.mode == "subjective" for o in ops):
        command_mode = "mixed"
    else:
        command_mode = "ambiguous"

    geometry_ops = [
        o.model_dump(by_alias=True, exclude_none=True)
        for o in ops
        if o.action in {"translate", "set_position", "align", "set_geometry"}
        or (o.priority == "relational_geometric")
    ]

    return RevisionDiff(
        operations=ops,
        preserve=preserve,
        forbidden_changes=forbidden,
        command_mode=command_mode,  # type: ignore[arg-type]
        max_subjective_ops=3,
        quality_lock={
            "preserve": list(preserve),
            "forbidden_unless_explicitly_requested": list(forbidden),
            "rule": "MINIMUM CHANGE BY DEFAULT. Anything not in requested_changes = PRESERVE.",
            "image_provider_calls_for_layer_ops": 0,
        },
        strict_preserve=strict,
        selected_element_id=selected_element_id,
        geometry_operations=geometry_ops,
        requested_changes=[
            o.model_dump(by_alias=True, exclude_none=True)
            for o in ops
            if o.action != "minimum_change"
        ],
    )
