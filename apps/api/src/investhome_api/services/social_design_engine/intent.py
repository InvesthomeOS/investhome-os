"""Edit-intent classification + target resolution for Social Design Engine.

Separates DESIGN intents (move/resize/style/image) from COPY intents
(change wording). Structural edits must never rewrite headline/body/CTA
unless the user explicitly asks for a wording change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from investhome_api.services.social_design_engine.layout import (
    VISUAL_LAYOUT_VOCAB,
    align_element_geometry,
    clamp_safe_geometry,
    role_font_prefs,
    safe_content_box,
    subject_safe_regions,
)
from investhome_api.services.social_design_engine.ops import canvas_size, clamp_int

EditIntent = Literal[
    "MOVE",
    "RESIZE",
    "ALIGN",
    "REPLACE_IMAGE",
    "CHANGE_STYLE",
    "CHANGE_COLOR",
    "CHANGE_TEXT",
    "CHANGE_CTA_TEXT",
    "DELETE",
    "DUPLICATE",
    "INCREASE_WHITESPACE",
    "REDUCE_TEXT_DENSITY",
    "EMPHASIZE_HEADLINE",
    "DEEMPHASIZE_BODY",
    "MOVE_TEXT_AWAY_FROM_SUBJECT",
    "INCREASE_IMAGE_PROMINENCE",
    "SIMPLIFY_LAYOUT",
]

ElementTarget = Literal["headline", "body", "cta", "image", "background", "unknown"]

COPY_INTENTS: frozenset[str] = frozenset({"CHANGE_TEXT", "CHANGE_CTA_TEXT"})
VISUAL_INTENTS: frozenset[str] = frozenset(VISUAL_LAYOUT_VOCAB)
STRUCTURAL_INTENTS: frozenset[str] = frozenset(
    {
        "MOVE",
        "RESIZE",
        "ALIGN",
        "REPLACE_IMAGE",
        "CHANGE_STYLE",
        "CHANGE_COLOR",
        "DELETE",
        "DUPLICATE",
        *VISUAL_LAYOUT_VOCAB,
    }
)

# Ops that rewrite creative copy fields
COPY_REWRITE_OPS: frozenset[str] = frozenset({"UPDATE_TEXT", "UPDATE_CTA", "ADD_TEXT", "ADD_CTA"})


@dataclass
class ClassifiedIntent:
    intent: EditIntent
    target: ElementTarget
    raw_span: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentPlan:
    intents: list[ClassifiedIntent] = field(default_factory=list)
    allow_copy_rewrite: bool = False
    allow_cta_rewrite: bool = False
    structural_only: bool = False

    @property
    def intent_names(self) -> list[str]:
        return [i.intent for i in self.intents]

    @property
    def targets(self) -> list[str]:
        return [i.target for i in self.intents]


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def resolve_target(instruction_fragment: str, *, default: ElementTarget = "unknown") -> ElementTarget:
    """Map NL references to element roles on the CURRENT selected post."""
    t = _norm(instruction_fragment)
    if any(k in t for k in ("başlık", "baslik", "headline", "title", "başlığı", "basligi")):
        return "headline"
    if any(k in t for k in ("cta", "buton", "button", "call to action", "çağrı", "cagri")):
        return "cta"
    if any(
        k in t
        for k in (
            "body",
            "açıklama",
            "aciklama",
            "caption",
            "metin",
            "gövde",
            "govde",
            "paragraf",
        )
    ):
        return "body"
    if any(k in t for k in ("arka plan", "background", "bg")):
        return "background"
    if any(k in t for k in ("görsel", "gorsel", "image", "foto", "photo", "render", "exterior")):
        return "image"
    return default


def target_from_element(el: dict[str, Any] | None) -> ElementTarget:
    if not isinstance(el, dict):
        return "unknown"
    typ = str(el.get("type") or "").upper()
    role = str(el.get("role") or "").lower()
    if typ == "TEXT":
        if role == "headline":
            return "headline"
        if role == "body":
            return "body"
        return "body" if role == "custom" else "headline"
    if typ in {"BUTTON", "CTA"}:
        return "cta"
    if typ == "IMAGE":
        return "image"
    return "unknown"


def selected_element_from_builder_context(
    builder_context: dict[str, Any] | None,
    post: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    ctx = builder_context if isinstance(builder_context, dict) else {}
    sel = ctx.get("selected_element") or ctx.get("selectedElement")
    eid = (
        (sel.get("id") if isinstance(sel, dict) else None)
        or ctx.get("selected_element_id")
        or ctx.get("selectedElementId")
    )
    eid_s = str(eid).strip() if eid else ""
    if post and eid_s:
        from investhome_api.services.social_design_engine.ops import find_element

        found = find_element(post, eid_s)
        if found is not None:
            return found
    if isinstance(sel, dict) and sel.get("id"):
        return sel
    return None


def default_target_from_builder_context(
    builder_context: dict[str, Any] | None,
    post: dict[str, Any] | None = None,
) -> ElementTarget:
    return target_from_element(selected_element_from_builder_context(builder_context, post))


def instruction_refers_to_selection(instruction: str) -> bool:
    t = _norm(instruction)
    pronouns = ("bunu", "şunu", "sunu", "onu", "this", "that", "seçili", "secili")
    if any(k in t for k in pronouns):
        return True
    if t == "it" or t.startswith("it ") or " it " in f" {t} ":
        return True
    return False


def apply_selected_element_targets(
    plan: IntentPlan,
    *,
    builder_context: dict[str, Any] | None,
    post: dict[str, Any] | None = None,
    instruction: str = "",
) -> IntentPlan:
    """Prefer canvas selection when NL is ambiguous or uses pronouns (bunu/this)."""
    default = default_target_from_builder_context(builder_context, post)
    if default == "unknown":
        return plan
    force = instruction_refers_to_selection(instruction)
    sel = selected_element_from_builder_context(builder_context, post)
    sel_id = str(sel.get("id") or "") if isinstance(sel, dict) else ""
    next_intents: list[ClassifiedIntent] = []
    for item in plan.intents:
        target = item.target
        if force or target == "unknown":
            target = default
        meta = dict(item.meta or {})
        if sel_id:
            meta["selected_element_id"] = sel_id
        next_intents.append(ClassifiedIntent(item.intent, target, item.raw_span, meta))
    return IntentPlan(
        intents=next_intents,
        allow_copy_rewrite=plan.allow_copy_rewrite,
        allow_cta_rewrite=plan.allow_cta_rewrite,
        structural_only=plan.structural_only,
    )



def _explicit_copy_change(instr: str) -> bool:
    """True only when the user clearly asks to change wording/content."""
    t = _norm(instr)
    copy_verbs = (
        "yaz",
        "yeniden yaz",
        "rewrite",
        "rephrase",
        "değiştir metin",
        "metni değiştir",
        "metni guncelle",
        "metni güncelle",
        "change text",
        "change headline",
        "change the headline",
        "change title",
        "change the title",
        "update text",
        "update headline",
        "update the headline",
        "update caption",
        "new headline",
        "yeni başlık",
        "yeni baslik",
        "başlığı yap",
        "basligi yap",
        "başlık olsun",
        "baslik olsun",
        "headline to",
        "headline:",
        "şu olsun",
        "su olsun",
        "olarak değiştir",
        "olarak degistir",
        "copy",
        "wording",
        "metni",
    )
    # Quoted replacement is an explicit copy request
    if re.search(r"[\"“”'][^\"“”']{2,}[\"“”']", instr or ""):
        if any(k in t for k in ("başlık", "baslik", "headline", "title", "cta", "buton", "body", "metin")):
            return True
    return any(v in t for v in copy_verbs)


def _explicit_cta_label_change(instr: str) -> bool:
    t = _norm(instr)
    if not any(k in t for k in ("cta", "buton", "button")):
        return False
    return _explicit_copy_change(instr) or any(
        k in t
        for k in (
            "etiket",
            "label",
            "yazısını",
            "yazisini",
            "metnini",
            "adı",
            "adi",
            "olsun",
        )
    )


def _classify_visual_language(t: str, raw: str) -> list[ClassifiedIntent]:
    """Map NL premium/spacing/subject phrases → validated visual vocab (not freeform)."""
    found: list[ClassifiedIntent] = []
    # Subject / sky / don't cover building
    if any(
        k in t
        for k in (
            "binayı kapatma",
            "binayi kapatma",
            "kapatma",
            "don't cover",
            "do not cover",
            "gökyüzüne",
            "gokyuzune",
            "gökyüzü",
            "gokyuzu",
            "sky",
            "buluta",
            "away from subject",
            "konuyu kapatma",
        )
    ) and any(
        k in t
        for k in (
            "bina",
            "building",
            "gökyüz",
            "gokyuz",
            "sky",
            "bulut",
            "yazı",
            "yazi",
            "metin",
            "başlık",
            "baslik",
            "cover",
            "kapat",
        )
    ):
        found.append(
            ClassifiedIntent("MOVE_TEXT_AWAY_FROM_SUBJECT", "headline", raw.strip(), {"region": "sky"})
        )

    if any(k in t for k in ("ferahlat", "ferah", "nefes aldır", "nefes aldir", "whitespace", "spacing", "sıkışık", "sikisik", "rahatlat")):
        if any(k in t for k in ("cta", "buton", "button")):
            found.append(ClassifiedIntent("INCREASE_WHITESPACE", "cta", raw.strip(), {}))
        else:
            found.append(ClassifiedIntent("INCREASE_WHITESPACE", "unknown", raw.strip(), {}))

    if any(k in t for k in ("daha sade", "sadeleştir", "sadelestir", "simplify", "basitleştir", "basitlestir", "more minimal")):
        found.append(ClassifiedIntent("SIMPLIFY_LAYOUT", "unknown", raw.strip(), {}))
        found.append(ClassifiedIntent("REDUCE_TEXT_DENSITY", "body", raw.strip(), {}))

    if any(k in t for k in ("daha premium", "premium yap", "daha güçlü", "daha guclu", "güçlü göster", "guclu goster", "more premium")):
        found.append(ClassifiedIntent("EMPHASIZE_HEADLINE", "headline", raw.strip(), {}))
        found.append(ClassifiedIntent("INCREASE_WHITESPACE", "unknown", raw.strip(), {}))

    if any(k in t for k in ("metin yoğun", "yoğunluğu azalt", "yogunlugu azalt", "reduce density", "deemphasize body", "gövdeyi küçült", "govdeyi kucult")):
        found.append(ClassifiedIntent("REDUCE_TEXT_DENSITY", "body", raw.strip(), {}))

    if any(k in t for k in ("görseli daha", "gorseli daha", "image prominence", "ön plana", "on plana", "görsel öne", "gorsel one", "show more photo", "show more of the photo", "show more of the image")):
        found.append(ClassifiedIntent("INCREASE_IMAGE_PROMINENCE", "image", raw.strip(), {}))

    if any(k in t for k in ("body küçült", "body kucult", "açıklamayı küçült", "aciklamayi kucult", "deemphasize")):
        found.append(ClassifiedIntent("DEEMPHASIZE_BODY", "body", raw.strip(), {}))

    return found


def classify_edit_intents(
    instruction: str,
    *,
    default_target: ElementTarget = "unknown",
) -> IntentPlan:
    """Classify P0 edit intents from a natural-language instruction."""
    raw = instruction or ""
    t = _norm(raw)
    found: list[ClassifiedIntent] = []
    fallback: ElementTarget = default_target if default_target != "unknown" else "headline"

    # Higher-level visual language (validated vocab only)
    found.extend(_classify_visual_language(t, raw))

    # Spatial / move — skip pure visual-subject phrases already classified
    move_markers = (
        "taşı",
        "tasi",
        "move",
        "al.",
        " al ",
        "üste",
        "uste",
        "yukarı",
        "yukari",
        "aşağı",
        "asagi",
        "sola",
        "sağa",
        "saga",
        "buluta",
        "bulut",
        "sky",
        "gökyüz",
        "gokyuz",
        "put ",
        "shift",
    )
    # Trailing "al" / "al." without copy verbs → move
    trailing_al = bool(re.search(r"\b(al|alın|alin)\b\.?$", t))
    if any(m in t for m in move_markers) or trailing_al:
        # Split multi-clause moves: "Başlığı sola al, CTA'yı yukarı taşı"
        clauses = re.split(r"[,\n;]| ve | and ", raw)
        move_hits = 0
        for clause in clauses:
            cl = _norm(clause)
            if not cl:
                continue
            is_move = (
                any(
                    m in cl
                    for m in (
                        "taşı",
                        "tasi",
                        "move",
                        "üste",
                        "uste",
                        "yukarı",
                        "yukari",
                        "aşağı",
                        "asagi",
                        "sola",
                        "sağa",
                        "saga",
                        "bulut",
                        "sky",
                        "gökyüz",
                        "gokyuz",
                        "shift",
                    )
                )
                or bool(re.search(r"\b(al|alın|alin)\b\.?$", cl))
                or " al " in f" {cl} "
            )
            if not is_move:
                continue
            target = resolve_target(clause, default=fallback)
            meta = _spatial_meta(cl)
            found.append(ClassifiedIntent("MOVE", target, clause.strip(), meta))
            move_hits += 1
        if move_hits == 0 and (any(m in t for m in move_markers) or trailing_al):
            target = resolve_target(raw, default=fallback)
            found.append(ClassifiedIntent("MOVE", target, raw.strip(), _spatial_meta(t)))

    # Resize / shrink / grow (compound: font + box resolved by layout engine)
    if any(
        k in t
        for k in (
            "küçült",
            "kucult",
            "büyüt",
            "buyut",
            "shrink",
            "enlarge",
            "resize",
            "smaller",
            "bigger",
            "font size",
            "punto",
            "büyük yap",
            "buyuk yap",
            "daha büyük",
            "daha buyuk",
        )
    ):
        target = resolve_target(raw, default=fallback)
        shrink = any(k in t for k in ("küçült", "kucult", "shrink", "smaller", "biraz küçült", "biraz kucult"))
        grow = any(
            k in t
            for k in (
                "büyüt",
                "buyut",
                "enlarge",
                "bigger",
                "büyük yap",
                "buyuk yap",
                "daha büyük",
                "daha buyuk",
            )
        )
        one_line = any(
            k in t
            for k in (
                "tek satır",
                "tek satir",
                "tek satırda",
                "tek satirda",
                "one line",
                "single line",
                "bir satır",
                "bir satir",
            )
        )
        amount = "slight" if ("biraz" in t or "slightly" in t or "a bit" in t) else "normal"
        found.append(
            ClassifiedIntent(
                "RESIZE",
                target,
                raw.strip(),
                {
                    "direction": "shrink" if shrink and not grow else "grow" if grow else "shrink",
                    "one_line": one_line,
                    "amount": amount,
                    "compound": True,
                },
            )
        )

    # Align
    if any(k in t for k in ("ortala", "center", "align", "hizala", "ortadan", "left-align", "left align")):
        target = resolve_target(raw, default=fallback)
        align = "center"
        if "sola" in t or "left" in t:
            align = "left"
        elif "sağa" in t or "saga" in t or "right" in t:
            align = "right"
        elif "safe" in t or "güvenli" in t or "guvenli" in t:
            align = "safe-area"
        found.append(ClassifiedIntent("ALIGN", target, raw.strip(), {"align": align}))

    # Replace image / background
    if any(
        k in t
        for k in (
            "başka",
            "baska",
            "değiştir",
            "degistir",
            "replace",
            "kullan",
            "görsel",
            "gorsel",
            "exterior",
            "render",
            "arka plan",
            "background",
            "image",
            "photo",
            "another",
        )
    ) and any(
        k in t
        for k in (
            "görsel",
            "gorsel",
            "image",
            "foto",
            "photo",
            "render",
            "exterior",
            "arka plan",
            "background",
            "asset",
        )
    ):
        target: ElementTarget = (
            "background" if any(k in t for k in ("arka plan", "background")) else "image"
        )
        # "kullan" alone with exterior → replace image
        found.append(ClassifiedIntent("REPLACE_IMAGE", target, raw.strip(), {}))

    # Color / style
    if re.search(r"#([0-9a-fA-F]{3,8})\b", raw) or any(
        k in t for k in ("renk", "color", "beyaz", "white", "siyah", "black", "dark")
    ):
        # Avoid treating "mavi bulut" spatial phrase as CHANGE_COLOR
        if "bulut" not in t and "sky" not in t:
            target = resolve_target(raw, default=fallback)
            found.append(ClassifiedIntent("CHANGE_COLOR", target, raw.strip(), {}))

    if any(k in t for k in ("kalın", "kalin", "bold", "italic", "stil", "style", "font")):
        target = resolve_target(raw, default=fallback)
        found.append(ClassifiedIntent("CHANGE_STYLE", target, raw.strip(), {}))

    # Delete / duplicate
    if any(k in t for k in ("sil", "delete", "remove", "kaldır", "kaldir", "remove cta", "remove the cta")):
        target = resolve_target(raw, default="unknown")
        found.append(ClassifiedIntent("DELETE", target, raw.strip(), {}))
    if any(k in t for k in ("kopyala", "duplicate", "çoğalt", "cogalt", "clone")):
        target = resolve_target(raw, default="unknown")
        found.append(ClassifiedIntent("DUPLICATE", target, raw.strip(), {}))

    allow_copy = _explicit_copy_change(raw)
    allow_cta = _explicit_cta_label_change(raw)
    if allow_copy:
        target = resolve_target(raw, default=fallback)
        if target == "cta" or allow_cta:
            found.append(ClassifiedIntent("CHANGE_CTA_TEXT", "cta", raw.strip(), {}))
        else:
            found.append(ClassifiedIntent("CHANGE_TEXT", target if target != "unknown" else "headline", raw.strip(), {}))
    elif allow_cta:
        found.append(ClassifiedIntent("CHANGE_CTA_TEXT", "cta", raw.strip(), {}))

    # Deduplicate by (intent, target)
    dedup: list[ClassifiedIntent] = []
    seen: set[tuple[str, str]] = set()
    for item in found:
        key = (item.intent, item.target)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)

    names = {i.intent for i in dedup}
    structural_only = bool(dedup) and not (names & COPY_INTENTS)
    return IntentPlan(
        intents=dedup,
        allow_copy_rewrite=allow_copy,
        allow_cta_rewrite=allow_cta or (allow_copy and "CHANGE_CTA_TEXT" in names),
        structural_only=structural_only,
    )


def _spatial_meta(cl: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if any(
        k in cl
        for k in (
            "mavi bulut",
            "bulut",
            "sky",
            "gökyüz",
            "gokyuz",
            "üste",
            "uste",
            "yukarı",
            "yukari",
            "up",
        )
    ):
        if any(k in cl for k in ("bulut", "sky", "gökyüz", "gokyuz")):
            meta["region"] = "sky"
            meta["direction"] = "up"
        else:
            meta["direction"] = "up"
    if any(k in cl for k in ("aşağı", "asagi", "down")):
        meta["direction"] = "down"
    if "sola" in cl or "left" in cl:
        meta["direction"] = "left" if "direction" not in meta else meta["direction"]
        meta["horizontal"] = "left"
    if any(k in cl for k in ("sağa", "saga", "right")):
        meta["horizontal"] = "right"
    if any(k in cl for k in ("ortala", "center", "ortaya")):
        meta["horizontal"] = "center"
    if any(
        k in cl
        for k in (
            "kenara yapıştırma",
            "kenara yapistirma",
            "kenara değdirme",
            "safe margin",
            "kenardan uzak",
        )
    ):
        meta["keep_safe_margin"] = True
    if "biraz" in cl or "slightly" in cl or "a bit" in cl:
        meta["amount"] = "slight"
    else:
        meta["amount"] = "normal"
    return meta


def find_target_element(
    post: dict[str, Any],
    target: ElementTarget,
) -> dict[str, Any] | None:
    """Resolve NL target against CURRENT post elements — never duplicate if exists."""
    elements = post.get("elements") if isinstance(post.get("elements"), list) else []
    if target == "headline":
        for el in elements:
            if isinstance(el, dict) and el.get("type") == "TEXT" and el.get("role") == "headline":
                return el
        for el in elements:
            if isinstance(el, dict) and el.get("type") == "TEXT":
                return el
        return None
    if target == "body":
        for el in elements:
            if isinstance(el, dict) and el.get("type") == "TEXT" and el.get("role") == "body":
                return el
        return None
    if target == "cta":
        for el in elements:
            if isinstance(el, dict) and el.get("type") in {"BUTTON", "CTA"}:
                return el
        return None
    if target in {"image", "background"}:
        for el in elements:
            if isinstance(el, dict) and el.get("type") == "IMAGE":
                return el
        return None
    return None


def sky_region_geometry(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, int]:
    """Safe upper sky region heuristic (no CV) — keep element in safe bounds."""
    regions = subject_safe_regions(canvas_w, canvas_h)
    sky = regions["sky"]
    w = clamp_int(el.get("width"), 8, sky["width"], min(400, sky["width"]))
    h = clamp_int(el.get("height"), 8, sky["height"], min(120, sky["height"]))
    y = sky["y"] + max(0, int(round(sky["height"] * 0.12)))
    x = sky["x"] + max(0, (sky["width"] - w) // 2)
    return clamp_safe_geometry(
        x=x,
        y=y,
        width=w,
        height=h,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        full_bleed=False,
    )


def move_geometry_for_intent(
    el: dict[str, Any],
    intent: ClassifiedIntent,
    *,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, int]:
    meta = intent.meta or {}
    if meta.get("region") == "sky":
        return sky_region_geometry(el, canvas_w=canvas_w, canvas_h=canvas_h)

    # BUTTON/CTA lives in the lower band by design — use edge pad, not text safe-box,
    # otherwise "aşağı taşı" near the bottom gets clamped upward.
    is_button = el.get("type") in {"BUTTON", "CTA"}
    pad = 24
    max_w = max(8, canvas_w - pad * 2)
    max_h = max(8, canvas_h - pad * 2)
    w = clamp_int(el.get("width"), 8, max_w, min(200, max_w))
    h = clamp_int(el.get("height"), 8, max_h, min(80, max_h))
    # Do NOT pre-clamp into the text safe box — apply delta from the current position.
    x = int(round(float(el.get("x") or 0)))
    y = int(round(float(el.get("y") or 0)))
    step = 56 if meta.get("amount") == "slight" else 96
    direction = meta.get("direction")
    horizontal = meta.get("horizontal")

    if direction == "up":
        y = y - step
    elif direction == "down":
        y = y + step
    if horizontal == "left":
        x = x - step
    elif horizontal == "right":
        x = x + step
    elif horizontal == "center":
        x = pad + max(0, (canvas_w - pad * 2 - w) // 2)

    if is_button:
        # "kenara yapıştırma" — keep a healthier inset than absolute pad when requested
        edge_pad = 48 if meta.get("keep_safe_margin") else pad
        x = max(edge_pad, min(canvas_w - w - edge_pad, x))
        y = max(edge_pad, min(canvas_h - h - edge_pad, y))
        return {"x": x, "y": y, "width": w, "height": h}

    return clamp_safe_geometry(
        x=x,
        y=y,
        width=w,
        height=h,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        full_bleed=el.get("type") == "IMAGE",
    )


def build_ops_from_intent_plan(
    *,
    plan: IntentPlan,
    linked_project_id: str,
    post: dict[str, Any],
    picked_asset_id: Any = None,
) -> list[dict[str, Any]]:
    """Deterministic Design Ops from classified intents — no copy rewrite."""
    post_id = str(post.get("id"))
    cw, ch = canvas_size(post)
    ops: list[dict[str, Any]] = []
    pid = str(linked_project_id)

    for item in plan.intents:
        if item.intent in COPY_INTENTS:
            continue

        # Visual language → validated vocab applied deterministically in apply_ops
        if item.intent in VISUAL_INTENTS:
            ops.append(
                {
                    "op": "APPLY_LAYOUT_INTENT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": None,
                    "payload": {"intent": item.intent},
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            if item.intent == "MOVE_TEXT_AWAY_FROM_SUBJECT":
                for role in ("headline", "body"):
                    target_el = find_target_element(post, role)  # type: ignore[arg-type]
                    if target_el is None:
                        continue
                    geo = sky_region_geometry(target_el, canvas_w=cw, canvas_h=ch)
                    # Stagger body under headline in sky band
                    if role == "body":
                        geo = dict(geo)
                        geo["y"] = min(
                            geo["y"] + max(48, int(round(ch * 0.08))),
                            int(round(ch * 0.34)),
                        )
                    ops.append(
                        {
                            "op": "MOVE_ELEMENT",
                            "linked_project_id": pid,
                            "post_id": post_id,
                            "element_id": target_el.get("id"),
                            "payload": {
                                "x": geo["x"],
                                "y": geo["y"],
                                "_layout_resolve": True,
                            },
                            "_intent": item.intent,
                            "_target": role,
                        }
                    )
            continue

        sel_id = str((item.meta or {}).get("selected_element_id") or "").strip()
        el = None
        if sel_id:
            from investhome_api.services.social_design_engine.ops import find_element

            el = find_element(post, sel_id)
        if el is None:
            el = find_target_element(post, item.target)
        if item.intent == "MOVE":
            if el is None:
                continue
            meta = dict(item.meta or {})
            # CTA down but not flush to edge
            if item.target == "cta" and meta.get("direction") == "down":
                meta["keep_safe_margin"] = True
                item = ClassifiedIntent(item.intent, item.target, item.raw_span, meta)
            geo = move_geometry_for_intent(el, item, canvas_w=cw, canvas_h=ch)
            ops.append(
                {
                    "op": "MOVE_ELEMENT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": el.get("id"),
                    "payload": {"x": geo["x"], "y": geo["y"], "_layout_resolve": True},
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            continue

        if item.intent == "RESIZE":
            if el is None:
                continue
            meta = item.meta or {}
            if el.get("type") == "TEXT":
                prefs = role_font_prefs(str(el.get("role") or "custom"), cw)
                current = clamp_int(el.get("fontSize"), prefs["min"], prefs["max"], prefs["preferred"])
                direction = meta.get("direction", "shrink")
                delta = 4 if meta.get("amount") == "slight" else 8
                next_size = (
                    max(prefs["min"], current - delta)
                    if direction == "shrink"
                    else min(prefs["max"], current + delta)
                )
                payload: dict[str, Any] = {
                    "fontSize": next_size,
                    "_layout_resolve": True,
                    "_compound_resize": True,
                }
                if meta.get("one_line"):
                    payload["maxLines"] = 1
                    payload["_one_line"] = True
                ops.append(
                    {
                        "op": "UPDATE_STYLE",
                        "linked_project_id": pid,
                        "post_id": post_id,
                        "element_id": el.get("id"),
                        "payload": payload,
                        "_intent": item.intent,
                        "_target": item.target,
                    }
                )
            else:
                factor = 0.9 if meta.get("direction") == "shrink" else 1.1
                w = max(24, int(round(clamp_int(el.get("width"), 8, cw, 100) * factor)))
                h = max(24, int(round(clamp_int(el.get("height"), 8, ch, 40) * factor)))
                ops.append(
                    {
                        "op": "RESIZE_ELEMENT",
                        "linked_project_id": pid,
                        "post_id": post_id,
                        "element_id": el.get("id"),
                        "payload": {"width": w, "height": h, "_layout_resolve": True},
                        "_intent": item.intent,
                        "_target": item.target,
                    }
                )
            continue

        if item.intent == "ALIGN":
            if el is None:
                continue
            aligned = align_element_geometry(
                el,
                str((item.meta or {}).get("align") or "center"),
                canvas_w=cw,
                canvas_h=ch,
            )
            ops.append(
                {
                    "op": "ALIGN_ELEMENT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": el.get("id"),
                    "payload": {
                        "align": (item.meta or {}).get("align") or "center",
                        "x": aligned["x"],
                        "y": aligned["y"],
                        "_layout_resolve": True,
                    },
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            continue

        if item.intent == "REPLACE_IMAGE":
            if not picked_asset_id:
                continue
            aid = str(picked_asset_id)
            ops.append(
                {
                    "op": "SET_BACKGROUND",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": None,
                    "payload": {"asset_id": aid},
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            if el is not None and el.get("type") == "IMAGE":
                ops.append(
                    {
                        "op": "REPLACE_IMAGE",
                        "linked_project_id": pid,
                        "post_id": post_id,
                        "element_id": el.get("id"),
                        "payload": {"asset_id": aid},
                        "_intent": item.intent,
                        "_target": item.target,
                    }
                )
            continue

        if item.intent == "CHANGE_COLOR":
            if el is None or el.get("type") != "TEXT":
                continue
            color = (item.meta or {}).get("color")
            if not color:
                continue
            ops.append(
                {
                    "op": "UPDATE_STYLE",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": el.get("id"),
                    "payload": {"color": color},
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            continue

        if item.intent == "DELETE" and el is not None:
            ops.append(
                {
                    "op": "DELETE_ELEMENT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": el.get("id"),
                    "payload": {},
                    "_intent": item.intent,
                    "_target": item.target,
                }
            )
            continue

    return ops


def op_rewrites_copy(op: dict[str, Any]) -> bool:
    name = str(op.get("op") or "").upper()
    if name not in COPY_REWRITE_OPS:
        return False
    payload = op.get("payload") if isinstance(op.get("payload"), dict) else {}
    if name == "UPDATE_TEXT":
        return "content" in payload or "text" in payload
    if name == "UPDATE_CTA":
        return "label" in payload or "text" in payload or "content" in payload
    if name in {"ADD_TEXT", "ADD_CTA"}:
        return True
    return False


def filter_ops_for_copy_protection(
    raw_ops: list[dict[str, Any]],
    plan: IntentPlan,
    *,
    mode: str,
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]]]:
    """Drop unauthorized copy rewrites in EDIT mode. Returns (kept, rejected)."""
    if mode != "edit":
        return raw_ops, []

    kept: list[dict[str, Any]] = []
    rejected: list[tuple[dict[str, Any], str]] = []

    for op in raw_ops:
        if not isinstance(op, dict):
            continue
        name = str(op.get("op") or "").upper()
        payload = dict(op.get("payload") or {}) if isinstance(op.get("payload"), dict) else {}

        if name == "UPDATE_TEXT" and ("content" in payload or "text" in payload):
            if not plan.allow_copy_rewrite:
                # Style-only fields may ride along — keep them, drop content rewrite.
                style_only = {
                    k: v
                    for k, v in payload.items()
                    if k in {"fontSize", "fontWeight", "align", "color"}
                }
                rejected.append((op, "copy_rewrite_rejected:UPDATE_TEXT"))
                if style_only:
                    kept.append({**op, "op": "UPDATE_STYLE", "payload": style_only})
                continue

        if name == "UPDATE_CTA" and any(k in payload for k in ("label", "text", "content")):
            if not plan.allow_cta_rewrite:
                style_only = {
                    k: v
                    for k, v in payload.items()
                    if k in {"backgroundColor", "textColor"}
                }
                rejected.append((op, "copy_rewrite_rejected:UPDATE_CTA"))
                if style_only:
                    kept.append({**op, "op": "UPDATE_STYLE", "payload": style_only})
                continue

        if name in {"ADD_TEXT", "ADD_CTA"} and plan.structural_only:
            rejected.append((op, f"unrelated_create_rejected:{name}"))
            continue

        # CREATE_POST in edit with structural intents → reject full regenerate
        if name == "CREATE_POST" and plan.intents:
            rejected.append((op, "full_regenerate_rejected_in_edit"))
            continue

        kept.append(op)

    return kept, rejected


def enrich_color_intents(plan: IntentPlan, instruction: str) -> IntentPlan:
    """Attach resolved color hex onto CHANGE_COLOR intents."""
    raw = instruction or ""
    t = _norm(raw)
    color = None
    m = re.search(r"#([0-9a-fA-F]{3,8})\b", raw)
    if m:
        color = f"#{m.group(1)}"
    elif any(k in t for k in ("beyaz", "white")):
        color = "#ffffff"
    elif any(k in t for k in ("siyah", "black", "dark")):
        color = "#0f172a"
    if not color:
        return plan
    for item in plan.intents:
        if item.intent == "CHANGE_COLOR":
            item.meta["color"] = color
    return plan
