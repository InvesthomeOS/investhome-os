"""Phase 4.0 — Native Master Design Spec.

The Creative Director decides composition BEFORE raster execution.
The spec is a sibling of the visual, not an extraction from it.

This module does not reconstruct from PNG, does not revise approved v2,
and does not stamp production cover / version / MasterDesignSpec pointers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

SCHEMA = "NativeMasterDesignSpecV1"
SCHEMA_V1_1 = "NativeMasterDesignSpecV1.1"
SCHEMA_V2 = "NativeMasterDesignSpecV2"
SPEC_VERSION = 1
SPEC_VERSION_V1_1 = "1.1"
SPEC_VERSION_V2 = 2
CREATIVE_DIRECTION_VERSION = "native_cd_v1"
CREATIVE_DIRECTION_VERSION_V1_1 = "native_cd_v1.1"
PHASE4_TEST_KEY = "phase4_native_master_test"
PHASE4_PARENT_SPEC_ID = "874d47cb-ef69-4f74-8f87-526227463b3e"
PHASE4_MASTER_ID = "1798c25b-1185-4a03-ac85-b0efd134c7b6"
POLISH_REASON = "CREATIVE_QUALITY_POLISH"

APPLICATION_FONT_HINTS = (
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path("C:/Windows/Fonts"),
    Path("/app/apps/web/public/fonts"),
    Path("/usr/src/app/apps/web/public/fonts"),
)

CANVAS_WIDTH = 1088
CANVAS_HEIGHT = 1360
CANVAS_FORMAT = "instagram_feed"
CANVAS_ASPECT = "4:5"

LOCKED_HERO_ASSET_ID = "299bd265-a0ea-486d-866d-1947f103fd57"
LOCKED_LOGO_ASSET_ID = "7b58877e-efca-4e9a-9027-6fd18fb1b345"
TEMPLE_PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
HERO_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_004.jpg"

PRODUCTION_COVER_V2 = "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
PRODUCTION_CAMPAIGN_ID = "e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5"

FONT_ROOTS = (
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path("C:/Windows/Fonts"),
)

REQUIRED_CONTENT = {
    "headline": "ALIRKEN KAZAN",
    "headline_line_1": "ALIRKEN",
    "headline_line_2": "KAZAN",
    "supporting_copy": "The Temple'da yerinizi lansman döneminde alın.",
    "unit_value": "2+1",
    "unit_label": "DAİRE",
    "list_price": "675.000 USD",
    "discount_value": "%35",
    "discount_label": "LANSMAN AVANTAJI",
    "cta": "PROJEYİ KEŞFET",
}

SEMANTIC_ROLES = (
    "headline",
    "supporting_copy",
    "unit_value",
    "unit_label",
    "list_price",
    "discount_value",
    "discount_label",
    "cta",
    "logo",
)

IDENTITY_KEYS = (
    "current_version",
    "current_cover_asset_id",
    "current_edit_map_id",
    "source_visual_asset_id",
    "logo_asset_id",
    "revision_history_len",
    "latest_master_ad_asset_id",
    "finished_ad_raster_asset_id",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _box(x0: int, y0: int, x1: int, y1: int) -> dict[str, int]:
    return {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)}


def _norm_box(box: dict[str, int], width: int, height: int) -> dict[str, float]:
    w = max(1, int(width))
    h = max(1, int(height))
    return {
        "x0": round(box["x0"] / w, 6),
        "y0": round(box["y0"] / h, 6),
        "x1": round(box["x1"] / w, 6),
        "y1": round(box["y1"] / h, 6),
    }


def _geom(box: dict[str, int], width: int, height: int, *, anchor: str, align: str, z: int, parent: str) -> dict[str, Any]:
    return {
        "absolute": dict(box),
        "normalized": _norm_box(box, width, height),
        "anchor": anchor,
        "alignment": align,
        "z_order": int(z),
        "parent_group": parent,
    }


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _color(rgb: tuple[int, int, int], *, opacity: float, role: str) -> dict[str, Any]:
    return {
        "rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
        "hex": _hex(rgb),
        "opacity": float(opacity),
        "usage_role": role,
    }


def inspect_available_fonts() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in FONT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.ttf")) + list(root.rglob("*.otf"))):
            key = str(path).replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            name = path.stem
            lower = name.lower()
            serif = "serif" in lower and "sans" not in lower
            sans = "sans" in lower or lower.startswith("arial") or lower.startswith("segoe")
            mono = "mono" in lower
            bold = "bold" in lower or lower.endswith("bd")
            found.append(
                {
                    "path": str(path),
                    "family_guess": name,
                    "serif": bool(serif and not mono),
                    "sans": bool(sans or (not serif and not mono)),
                    "bold": bold,
                    "mono": mono,
                    "available": True,
                }
            )
    return found


def inspect_application_font_assets() -> dict[str, Any]:
    """Search installed fonts and known application font directories. Do not download."""
    bundled: list[str] = []
    for root in APPLICATION_FONT_HINTS:
        if not root.exists():
            continue
        for path in list(root.rglob("*.ttf")) + list(root.rglob("*.otf")) + list(root.rglob("*.woff2")):
            bundled.append(str(path))
    inventory = inspect_available_fonts()
    premium_tokens = ("georgia", "garamond", "didot", "playfair", "cormorant", "liberation")
    premium = [
        item
        for item in inventory
        if any(token in str(item.get("family_guess") or "").lower() for token in premium_tokens)
    ]
    return {
        "inventory_count": len(inventory),
        "bundled_application_font_files": bundled,
        "premium_faces_found": [item.get("family_guess") for item in premium],
        "frontend_css_only": [
            "Helvetica Neue / Arial via --font-display (no TTF in repo)",
            "SMB serif maps to Georgia CSS stack (not a file the API can load)",
        ],
        "usable_by_native_renderer": [item.get("path") for item in inventory],
        "decision": (
            "No licensed premium display face is available as a file. "
            "Continue with inspected local DejaVu and improve hierarchy, tracking, and contrast."
        ),
    }


def _pick_font(
    inventory: list[dict[str, Any]],
    *,
    want_serif: bool,
    want_bold: bool,
    preferred_family: str,
) -> dict[str, Any]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in inventory:
        score = 0
        if want_serif and item.get("serif"):
            score += 8
        if not want_serif and item.get("sans"):
            score += 8
        if want_bold and item.get("bold"):
            score += 4
        if not want_bold and not item.get("bold"):
            score += 3
        family = str(item.get("family_guess") or "").lower()
        if "dejavu" in family:
            score += 1
        if "georgia" in family or "liberation" in family:
            score += 3
        if "times" in family:
            score += 1
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    chosen = scored[0][1] if scored else {
        "path": None,
        "family_guess": "PIL-default",
        "serif": False,
        "sans": True,
        "bold": False,
        "available": False,
    }
    premium_present = any(
        any(token in str(item.get("family_guess") or "").lower() for token in ("georgia", "garamond", "didot", "playfair", "cormorant"))
        for item in inventory
    )
    return {
        "preferred_family": preferred_family,
        "actual_available_family": chosen.get("family_guess"),
        "actual_font_path": chosen.get("path"),
        "fallback_family": "DejaVu Serif" if want_serif else "DejaVu Sans",
        "premium_display_font_available": premium_present,
        "inventory_count": len(inventory),
        "invented": False,
    }


def direct_native_master_creative(*, brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """Creative Director decisions for this brief. Recorded before geometry or raster.

    This is art direction, not a fill-in template. The compiler later turns these
    named decisions into executable geometry.
    """
    _ = brief
    return {
        "creative_direction_version": CREATIVE_DIRECTION_VERSION,
        "campaign_concept": "ALIRKEN KAZAN",
        "visual_character": [
            "premium",
            "editorial",
            "luxury real estate",
            "Washington DC investment",
            "clean",
            "confident",
            "high-end",
        ],
        "brand_language": ["navy", "gold", "white"],
        "avoid": [
            "dashboard appearance",
            "KPI cards",
            "SaaS UI",
            "generic social-media template",
            "cheap real-estate flyer",
            "huge boxes",
            "random badges",
            "overcrowded metrics",
            "excessive gradients",
            "generic stock-ad aesthetics",
            "three equal KPI cards",
            "old v2 three-column row copy",
        ],
        "headline_hierarchy": "stacked_display_alirken_over_kazan",
        "hero_placement": "full_bleed_photograph",
        "copy_placement": "upper_photographic_overlay",
        "commercial_layout": "price_led_editorial_lockup",
        "commercial_emphasis": "price_leads_companions_are_quiet",
        "cta_placement": "lower_hero_material_bar",
        "logo_placement": "footer_quiet_center",
        "decorative_system": "headline_ornament_plus_hairline_facts_plus_photographic_fades",
        "spacing_strategy": "editorial_air",
        "image_crop_strategy": "cover_architecture_center",
        "image_treatment": "architectural_truth_with_editorial_grade",
        "typography_character": "editorial_serif_display_with_restrained_labels",
        "layout_model": "editorial_hero_led_overlay",
        "not_a_template_fill": True,
        "not_copied_from_v2_pixels": True,
        "rationale": (
            "Launch investment message needs a photograph-led composition: the building "
            "is the proof, type is the offer, commercial facts are companions rather than "
            "a dashboard. Stacked display headline carries ALIRKEN KAZAN. CTA sits on the "
            "architecture as a material gold bar. Logo remains identity, not decoration."
        ),
    }


def direct_native_master_creative_v11(*, brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """Phase 4.0A art-direction polish. Same brief, stronger division of type vs architecture."""
    _ = brief
    return {
        "creative_direction_version": CREATIVE_DIRECTION_VERSION_V1_1,
        "campaign_concept": "ALIRKEN KAZAN",
        "visual_character": [
            "premium",
            "editorial",
            "luxury real estate",
            "architectural campaign",
            "restrained",
            "confident",
        ],
        "brand_language": ["navy", "gold", "white"],
        "avoid": [
            "dashboard appearance",
            "KPI cards",
            "web-button CTA",
            "type on spire",
            "faint logo",
            "three equal columns",
        ],
        "headline_hierarchy": "kicker_alirken_display_kazan",
        "hero_placement": "architecture_field_below_editorial_plate",
        "copy_placement": "navy_editorial_field",
        "commercial_layout": "price_led_inline_companions",
        "commercial_emphasis": "price_anchor_companions_quiet_inline",
        "cta_placement": "seam_inscription_bar",
        "logo_placement": "footer_grounded_center",
        "decorative_system": "restrained_headline_rule_and_seam_only",
        "spacing_strategy": "editorial_air",
        "image_crop_strategy": "cover_architecture_in_lower_field",
        "image_treatment": "architectural_truth_clear_silhouette",
        "typography_character": "kicker_plus_display_plus_quiet_facts",
        "typography_profile": "v1.1_editorial",
        "layout_model": "editorial_field_above_architecture",
        "companion_presentation": "inline_lockup",
        "not_a_template_fill": True,
        "not_copied_from_v2_pixels": True,
        "polish_reason": POLISH_REASON,
        "rationale": (
            "Type on a full-bleed 4:5 cover crop collides with the spire. Split the canvas: "
            "a navy editorial field holds campaign and commercial reading; the architecture "
            "occupies a dedicated lower field with its own crop so the silhouette is intact. "
            "CTA is a seam inscription, not a UI button. Logo is grounded in the footer fade."
        ),
    }


def _cover_crop(
    source_w: int,
    source_h: int,
    dest_w: int,
    dest_h: int,
    *,
    focal: tuple[float, float],
) -> dict[str, Any]:
    src_aspect = source_w / max(1, source_h)
    dst_aspect = dest_w / max(1, dest_h)
    if src_aspect > dst_aspect:
        crop_h = source_h
        crop_w = max(1, int(round(source_h * dst_aspect)))
    else:
        crop_w = source_w
        crop_h = max(1, int(round(source_w / dst_aspect)))
    cx = source_w * float(focal[0])
    cy = source_h * float(focal[1])
    x0 = int(round(cx - crop_w / 2))
    y0 = int(round(cy - crop_h / 2))
    x0 = max(0, min(x0, source_w - crop_w))
    y0 = max(0, min(y0, source_h - crop_h))
    x1 = x0 + crop_w
    y1 = y0 + crop_h
    return {
        "source_width": int(source_w),
        "source_height": int(source_h),
        "crop_rectangle": _box(x0, y0, x1, y1),
        "normalized_crop": _norm_box(_box(x0, y0, x1, y1), source_w, source_h),
        "destination_geometry": _box(0, 0, dest_w, dest_h),
        "scale_mode": "cover",
        "focal_point": {"x": float(focal[0]), "y": float(focal[1])},
        "scale": round(dest_w / max(1, crop_w), 6),
    }


def _compile_geometry(direction: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    """Turn Creative Director decisions into absolute geometry.

    Ratios come from the named spacing strategy, not from a raster.
    """
    if str(direction.get("layout_model")) == "editorial_field_above_architecture":
        return _compile_geometry_v11(width, height)
    air = str(direction.get("spacing_strategy")) == "editorial_air"
    overlay_end = int(round(height * (0.34 if air else 0.38)))
    overlay_fade = int(round(height * 0.46))
    headline = _box(72, int(round(height * 0.042)), width - 72, int(round(height * 0.198)))
    line1 = _box(headline["x0"], headline["y0"], headline["x1"], headline["y0"] + 52)
    line2 = _box(headline["x0"], line1["y1"] + 16, headline["x1"], headline["y1"])
    ornament_y = line1["y1"] + 6
    ornament = _box(int(width * 0.30), ornament_y, int(width * 0.70), ornament_y + 10)
    supporting = _box(90, headline["y1"] + 14, width - 90, headline["y1"] + 52)
    commercial = _box(80, supporting["y1"] + 22, width - 80, overlay_end - 8)
    price = _box(commercial["x0"], commercial["y0"], commercial["x1"], commercial["y0"] + 52)
    meta = _box(commercial["x0"], price["y1"] + 6, commercial["x1"], commercial["y1"])
    unit = _box(meta["x0"], meta["y0"], meta["x0"] + (meta["x1"] - meta["x0"]) // 2 - 18, meta["y1"])
    discount = _box(unit["x1"] + 36, meta["y0"], meta["x1"], meta["y1"])
    cta = _box(int(width * 0.20), int(round(height * 0.812)), int(width * 0.80), int(round(height * 0.872)))
    logo = _box(int(width * 0.30), int(round(height * 0.898)), int(width * 0.70), int(round(height * 0.978)))
    footer_fade = _box(0, int(round(height * 0.78)), width, height)
    top_overlay = _box(0, 0, width, overlay_fade)
    hero = _box(0, 0, width, height)
    return {
        "canvas": _box(0, 0, width, height),
        "hero_visual": hero,
        "top_overlay": top_overlay,
        "footer_fade": footer_fade,
        "headline": headline,
        "headline_line_1": line1,
        "headline_line_2": line2,
        "headline_ornament": ornament,
        "supporting_copy": supporting,
        "commercial_group": commercial,
        "price_column": price,
        "commercial_meta": meta,
        "unit_column": unit,
        "discount_column": discount,
        "cta": cta,
        "logo": logo,
        "overlay_end": overlay_end,
        "editorial_field": _box(0, 0, width, overlay_end),
    }


def _compile_geometry_v11(width: int, height: int) -> dict[str, Any]:
    """Editorial field above architecture. Commercial never enters the hero field."""
    seam = 448
    cta_h = 50
    editorial = _box(0, 0, width, seam)
    hero = _box(0, seam, width, height)
    headline = _box(96, 52, width - 96, 214)
    line1 = _box(headline["x0"], headline["y0"], headline["x1"], headline["y0"] + 40)
    ornament = _box(int(width * 0.38), line1["y1"] + 8, int(width * 0.62), line1["y1"] + 16)
    line2 = _box(headline["x0"], ornament["y1"] + 6, headline["x1"], headline["y1"])
    supporting = _box(160, headline["y1"] + 18, width - 160, headline["y1"] + 50)
    commercial = _box(80, supporting["y1"] + 28, width - 80, seam - 24)
    price = _box(commercial["x0"], commercial["y0"], commercial["x1"], commercial["y0"] + 48)
    meta = _box(commercial["x0"], price["y1"] + 10, commercial["x1"], commercial["y1"])
    unit = _box(meta["x0"], meta["y0"], meta["x0"] + (meta["x1"] - meta["x0"]) // 2 - 20, meta["y1"])
    discount = _box(unit["x1"] + 40, meta["y0"], meta["x1"], meta["y1"])
    cta = _box(0, seam, width, seam + cta_h)
    logo = _box(int(width * 0.22), height - 132, int(width * 0.78), height - 28)
    footer_fade = _box(0, height - 220, width, height)
    return {
        "canvas": _box(0, 0, width, height),
        "hero_visual": hero,
        "editorial_field": editorial,
        "top_overlay": editorial,
        "footer_fade": footer_fade,
        "headline": headline,
        "headline_line_1": line1,
        "headline_line_2": line2,
        "headline_ornament": ornament,
        "supporting_copy": supporting,
        "commercial_group": commercial,
        "price_column": price,
        "commercial_meta": meta,
        "unit_column": unit,
        "discount_column": discount,
        "cta": cta,
        "logo": logo,
        "overlay_end": seam,
        "architecture_seam": seam,
    }


def _typography_plan(inventory: list[dict[str, Any]], *, profile: str = "v1") -> dict[str, Any]:
    display = _pick_font(inventory, want_serif=True, want_bold=True, preferred_family="editorial_serif_display")
    display_reg = _pick_font(inventory, want_serif=True, want_bold=False, preferred_family="editorial_serif_text")
    label = _pick_font(inventory, want_serif=True, want_bold=False, preferred_family="editorial_serif_label")
    limitation = None
    if not display.get("premium_display_font_available"):
        limitation = (
            "Application font inventory has no licensed premium display face "
            "(Georgia/Garamond/Didot/Playfair/Cormorant absent). "
            f"Phase 4 uses the best legally available local font: {display.get('actual_available_family')}."
        )
    roles = {
        "headline_line_1": {
            "font_role": "headline_line_1",
            "font_character": "tracked editorial display",
            **display_reg,
            "weight": "regular",
            "size": 46,
            "tracking": 10,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "white",
        },
        "headline_line_2": {
            "font_role": "headline_line_2",
            "font_character": "confident display serif",
            **display,
            "weight": "bold",
            "size": 82,
            "tracking": 6,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "gold_primary",
        },
        "supporting_copy": {
            "font_role": "supporting_copy",
            "font_character": "quiet editorial sentence",
            **display_reg,
            "weight": "regular",
            "size": 22,
            "tracking": 0.4,
            "line_height": 1.25,
            "alignment": "center",
            "case": "sentence",
            "color_role": "supporting_text",
        },
        "unit_value": {
            "font_role": "unit_value",
            "font_character": "quiet companion fact",
            **display,
            "weight": "bold",
            "size": 22,
            "tracking": 1.0,
            "line_height": 1.0,
            "alignment": "center",
            "case": "as_written",
            "color_role": "white",
        },
        "unit_label": {
            "font_role": "unit_label",
            "font_character": "small fact label",
            **label,
            "weight": "regular",
            "size": 13,
            "tracking": 2.4,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "gold_secondary",
        },
        "list_price": {
            "font_role": "list_price",
            "font_character": "primary commercial read, not a KPI card",
            **display,
            "weight": "bold",
            "size": 44,
            "tracking": 0.8,
            "line_height": 1.0,
            "alignment": "center",
            "case": "as_written",
            "color_role": "gold_primary",
        },
        "price_label": {
            "font_role": "price_label",
            "font_character": "small fact label",
            **label,
            "weight": "regular",
            "size": 13,
            "tracking": 2.4,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "gold_secondary",
        },
        "discount_value": {
            "font_role": "discount_value",
            "font_character": "quiet companion offer",
            **display,
            "weight": "bold",
            "size": 22,
            "tracking": 0.8,
            "line_height": 1.0,
            "alignment": "center",
            "case": "as_written",
            "color_role": "gold_primary",
        },
        "discount_label": {
            "font_role": "discount_label",
            "font_character": "small fact label",
            **label,
            "weight": "regular",
            "size": 12,
            "tracking": 1.8,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "gold_secondary",
        },
        "cta": {
            "font_role": "cta",
            "font_character": "material bar inscription",
            **display,
            "weight": "bold",
            "size": 20,
            "tracking": 3.2,
            "line_height": 1.0,
            "alignment": "center",
            "case": "upper",
            "color_role": "cta_text",
        },
    }
    if profile == "v1.1_editorial":
        roles["headline_line_1"].update({"size": 28, "tracking": 16, "font_character": "quiet tracked kicker"})
        roles["headline_line_2"].update({"size": 68, "tracking": 8, "font_character": "restrained display"})
        roles["supporting_copy"].update({"size": 17, "tracking": 0.8, "color_role": "supporting_text"})
        roles["list_price"].update({"size": 38, "tracking": 1.2})
        roles["unit_value"].update({"size": 16, "tracking": 1.2})
        roles["unit_label"].update({"size": 12, "tracking": 2.8})
        roles["discount_value"].update({"size": 16, "tracking": 1.2})
        roles["discount_label"].update({"size": 11, "tracking": 2.2})
        roles["cta"].update({"size": 15, "tracking": 5.5, "font_character": "seam inscription"})
        limitation = (
            (limitation or "")
            + " V1.1 does not claim a new typeface; hierarchy, tracking, and contrast carry the polish."
        ).strip()
    return {
        "roles": roles,
        "font_limitation": limitation,
        "inventory": [
            {"path": item["path"], "family_guess": item["family_guess"], "serif": item["serif"], "bold": item["bold"]}
            for item in inventory
        ],
        "actual_fonts_used": sorted(
            {
                str(role.get("actual_font_path") or role.get("actual_available_family"))
                for role in roles.values()
            }
        ),
    }


def _color_system() -> dict[str, Any]:
    navy = (10, 18, 40)
    navy2 = (14, 24, 48)
    gold = (201, 168, 92)
    gold2 = (168, 136, 74)
    white = (247, 243, 234)
    support = (230, 217, 184)
    cta_text = (18, 16, 12)
    sep = (201, 168, 92)
    return {
        "navy_primary": _color(navy, opacity=1.0, role="overlay_and_field"),
        "navy_secondary": _color(navy2, opacity=1.0, role="overlay_depth"),
        "gold_primary": _color(gold, opacity=1.0, role="headline_and_offer"),
        "gold_secondary": _color(gold2, opacity=0.92, role="labels_and_ornament"),
        "white": _color(white, opacity=1.0, role="primary_read"),
        "supporting_text": _color(support, opacity=0.92, role="supporting_copy"),
        "cta_fill_start": _color((214, 184, 110), opacity=1.0, role="cta_fill"),
        "cta_fill_end": _color((168, 132, 64), opacity=1.0, role="cta_fill"),
        "cta_text": _color(cta_text, opacity=1.0, role="cta_inscription"),
        "separator": _color(sep, opacity=0.55, role="commercial_separator"),
        "overlay_navy": _color(navy, opacity=0.78, role="hero_transition"),
        "footer_navy": _color(navy, opacity=0.72, role="footer_fade"),
    }


def _hero_treatment(crop: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_asset_id": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "architecture_lock": True,
        "ai_architecture_generation": False,
        "scale_mode": crop["scale_mode"],
        "source_dimensions": {"width": crop["source_width"], "height": crop["source_height"]},
        "source_crop_rectangle": crop["crop_rectangle"],
        "normalized_crop": crop["normalized_crop"],
        "destination_geometry": crop["destination_geometry"],
        "focal_point": crop["focal_point"],
        "brightness": 0.94,
        "contrast": 1.12,
        "saturation": 1.06,
        "temperature": {"red_gain": 1.04, "green_gain": 1.0, "blue_gain": 0.97},
        "overlay": "top_navy_gradient",
        "gradient": "navy_to_photograph",
        "fade": "footer_navy",
        "mask_clip_shape": "full_canvas_rect",
    }


def _cta_treatment(box: dict[str, int], typography: dict[str, Any], colors: dict[str, Any], *, seam: bool = False) -> dict[str, Any]:
    return {
        "text": REQUIRED_CONTENT["cta"],
        "geometry": box,
        "shape": "seam_inscription_bar" if seam else "editorial_material_bar",
        "fill": "vertical_gold_gradient",
        "gradient": {
            "start": colors["cta_fill_start"],
            "end": colors["cta_fill_end"],
            "direction": "vertical",
        },
        "border": None,
        "radius": 0 if seam else 2,
        "padding": {"x": 28, "y": 14},
        "font": typography["roles"]["cta"],
        "font_size": typography["roles"]["cta"]["size"],
        "tracking": typography["roles"]["cta"]["tracking"],
        "text_color": colors["cta_text"],
        "shadow": None if seam else {"opacity": 0.28, "offset": [0, 6], "blur": 14},
        "alignment": "center",
        "relationship_to_hero": "seams_editorial_field_to_architecture" if seam else "overlays_lower_photograph",
        "relationship_to_logo": "above_logo_with_air",
    }


def _decorations(boxes: dict[str, Any], colors: dict[str, Any], *, layout_model: str = "") -> list[dict[str, Any]]:
    if layout_model == "editorial_field_above_architecture":
        return [
            {
                "id": "editorial_field",
                "role": "hero_transition",
                "kind": "fill",
                "geometry": boxes["editorial_field"],
                "anchor": "top",
                "style": "solid_navy_editorial_field",
                "color": colors["navy_primary"],
                "thickness": None,
                "opacity": 1.0,
                "relationship": "holds_campaign_and_commercial_off_architecture",
            },
            {
                "id": "footer_fade",
                "role": "footer_fade",
                "kind": "linear_gradient",
                "geometry": boxes["footer_fade"],
                "anchor": "bottom",
                "style": "transparent_to_navy",
                "color": colors["footer_navy"],
                "thickness": None,
                "opacity": 0.88,
                "alpha_start": 0,
                "alpha_end": 230,
                "relationship": "grounds_logo_on_photograph",
            },
            {
                "id": "headline_ornament",
                "role": "headline_ornament",
                "kind": "rules_and_diamond",
                "geometry": boxes["headline_ornament"],
                "anchor": "center",
                "style": "gold_hairline_with_diamond",
                "color": colors["gold_secondary"],
                "thickness": 1,
                "opacity": 0.85,
                "relationship": "between_alirken_and_kazan",
            },
            {
                "id": "commercial_middot",
                "role": "commercial_separator",
                "kind": "diamond",
                "geometry": {
                    "x0": (boxes["unit_column"]["x1"] + boxes["discount_column"]["x0"]) // 2 - 3,
                    "y0": (boxes["commercial_meta"]["y0"] + boxes["commercial_meta"]["y1"]) // 2 - 3,
                    "x1": (boxes["unit_column"]["x1"] + boxes["discount_column"]["x0"]) // 2 + 3,
                    "y1": (boxes["commercial_meta"]["y0"] + boxes["commercial_meta"]["y1"]) // 2 + 3,
                },
                "anchor": "between_companions",
                "style": "gold_diamond",
                "color": colors["separator"],
                "thickness": 1,
                "opacity": 0.7,
                "relationship": "separates_quiet_companion_facts",
            },
        ]
    return [
        {
            "id": "top_overlay",
            "role": "hero_transition",
            "kind": "linear_gradient",
            "geometry": boxes["top_overlay"],
            "anchor": "top",
            "style": "navy_to_transparent",
            "color": colors["overlay_navy"],
            "thickness": None,
            "opacity": 0.66,
            "alpha_start": 168,
            "alpha_end": 0,
            "relationship": "sits_on_hero_for_type_readability",
        },
        {
            "id": "footer_fade",
            "role": "footer_fade",
            "kind": "linear_gradient",
            "geometry": boxes["footer_fade"],
            "anchor": "bottom",
            "style": "transparent_to_navy",
            "color": colors["footer_navy"],
            "thickness": None,
            "opacity": 0.78,
            "alpha_start": 0,
            "alpha_end": 210,
            "relationship": "grounds_logo_on_photograph",
        },
        {
            "id": "headline_ornament",
            "role": "headline_ornament",
            "kind": "rules_and_diamond",
            "geometry": boxes["headline_ornament"],
            "anchor": "center",
            "style": "gold_hairline_with_diamond",
            "color": colors["gold_secondary"],
            "thickness": 1,
            "opacity": 0.9,
            "relationship": "between_alirken_and_kazan",
        },
        {
            "id": "commercial_middot",
            "role": "commercial_separator",
            "kind": "diamond",
            "geometry": {
                "x0": (boxes["unit_column"]["x1"] + boxes["discount_column"]["x0"]) // 2 - 4,
                "y0": (boxes["commercial_meta"]["y0"] + boxes["commercial_meta"]["y1"]) // 2 - 4,
                "x1": (boxes["unit_column"]["x1"] + boxes["discount_column"]["x0"]) // 2 + 4,
                "y1": (boxes["commercial_meta"]["y0"] + boxes["commercial_meta"]["y1"]) // 2 + 4,
            },
            "anchor": "between_companions",
            "style": "gold_diamond",
            "color": colors["separator"],
            "thickness": 1,
            "opacity": 0.7,
            "relationship": "separates_quiet_companion_facts",
        },
        {
            "id": "logo_ground",
            "role": "footer_fade",
            "kind": "soft_rect",
            "geometry": {
                "x0": boxes["logo"]["x0"] - 24,
                "y0": boxes["logo"]["y0"] - 8,
                "x1": boxes["logo"]["x1"] + 24,
                "y1": boxes["logo"]["y1"] + 8,
            },
            "anchor": "logo",
            "style": "soft_navy_ground",
            "color": colors["footer_navy"],
            "thickness": None,
            "opacity": 0.35,
            "relationship": "keeps_real_logo_legible_on_photograph",
        },
    ]


def _flexibility() -> dict[str, Any]:
    return {
        "hero_asset": ["REPLACEABLE_ASSET", "PROJECT_LOCKED"],
        "hero_crop": ["FLEXIBLE_LAYOUT"],
        "headline_content": ["LOCKED_BY_DEFAULT"],
        "headline_geometry": ["FLEXIBLE_LAYOUT"],
        "supporting_copy_content": ["LOCKED_BY_DEFAULT"],
        "supporting_copy_geometry": ["FLEXIBLE_LAYOUT"],
        "commercial_content": ["FLEXIBLE_CONTENT"],
        "commercial_geometry": ["FLEXIBLE_LAYOUT"],
        "logo_asset": ["LOCKED_IDENTITY"],
        "logo_geometry": ["FLEXIBLE_LAYOUT"],
        "cta_content": ["LOCKED_BY_DEFAULT"],
        "cta_geometry": ["FLEXIBLE_LAYOUT"],
    }


def _content_capacity(*, split: bool = False) -> dict[str, Any]:
    return {
        "group": "commercial_group",
        "current_capacity": 3,
        "current_facts": ["unit", "list_price", "discount"],
        "preferred_growth_direction": "downward_into_editorial_field_then_type_scale" if split else "downward_into_overlay_then_type_scale",
        "max_before_reflow": 5,
        "future_facts_example": ["launch_price", "savings", "additional_investment_metric"],
        "reflow_strategy": (
            "Keep headline identity, logo, and architecture field. Expand commercial group "
            "downward inside the editorial field and push the seam if needed. Never overlay "
            "commercial type on the building. Never introduce KPI cards."
            if split
            else
            "Keep headline identity and logo. Expand commercial group downward into the "
            "photographic overlay, then reduce fact type size. Never introduce KPI cards."
        ),
        "neighboring_flexible_groups": ["supporting_copy", "editorial_field", "cta", "hero_visual"] if split else ["supporting_copy", "top_overlay", "cta"],
        "expansion_strategy": "add_fact_then_reflow",
    }


def _revision_policy() -> dict[str, Any]:
    return {
        "implemented": False,
        "capable": True,
        "notes": "Phase 4.0 stores capability only. Do not execute revisions.",
        "natural_language": {
            "Görseli değiştir.": {
                "action": "change_hero_asset",
                "preserve": ["headline", "supporting_copy", "commercial", "cta", "logo", "palette"],
                "recompute": ["hero_crop", "hero_treatment"],
            },
            "Fiyatı değiştir.": {
                "action": "change_commercial_semantic_content",
                "preserve": ["headline", "hero", "cta", "logo"],
                "recompute": ["commercial_group_reflow_if_needed"],
            },
            "Logoyu küçült.": {
                "action": "change_logo_geometry_only",
                "preserve": ["all_other_semantics"],
                "recompute": ["logo_geometry"],
            },
            "Başlığı değiştir.": {
                "action": "change_headline_content",
                "preserve": ["hero", "commercial", "cta", "logo"],
                "recompute": ["headline_group_reflow"],
            },
        },
    }


def _format_adaptation_policy() -> dict[str, Any]:
    return {
        "implemented": False,
        "master_format": CANVAS_FORMAT,
        "master_aspect_ratio": CANVAS_ASPECT,
        "do_not_create_now": ["9:16 Story", "1:1", "16:9", "Reel cover", "video"],
        "priority_order": ["4:5 master", "9:16 story", "1:1", "16:9", "reel_cover"],
        "anchoring": {
            "hero": "cover_crop_from_focal",
            "headline": "keep_upper_third_when_possible",
            "commercial": "keep_near_headline_in_portrait_formats",
            "cta": "keep_lower_third",
            "logo": "keep_footer",
        },
        "crop_policy": {
            "9:16": "tighten_hero_sides_keep_architecture_center",
            "1:1": "crop_vertical_air_keep_headline_and_hero_balance",
            "16:9": "letterbox_or_horizontal_crop_keep_architecture",
        },
        "group_flexibility": {
            "headline": "FLEXIBLE_LAYOUT",
            "commercial": "FLEXIBLE_LAYOUT",
            "cta": "FLEXIBLE_LAYOUT",
            "logo": "FLEXIBLE_LAYOUT",
            "hero": "FLEXIBLE_LAYOUT",
        },
        "content_preservation_rules": [
            "Never drop headline, price, discount, CTA, or real logo.",
            "Never invent architecture.",
            "Never switch canvas silently.",
        ],
    }


def materialize_native_master_spec(
    *,
    direction: dict[str, Any],
    source_size: tuple[int, int],
    project_id: str,
    campaign_id: str,
    hero_asset_id: str,
    logo_asset_id: str,
    inventory: list[dict[str, Any]] | None = None,
    phase4_master_id: str | None = None,
    spec_id: str | None = None,
    schema: str = SCHEMA,
    spec_version: Any = SPEC_VERSION,
    parent_spec_id: str | None = None,
    polish_reason: str | None = None,
) -> dict[str, Any]:
    if str(hero_asset_id) != LOCKED_HERO_ASSET_ID:
        raise ValueError(f"PROJECT_LOCKED hero mismatch: {hero_asset_id}")
    if str(logo_asset_id) != LOCKED_LOGO_ASSET_ID:
        raise ValueError(f"PROJECT_LOCKED logo mismatch: {logo_asset_id}")
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT
    inventory = inventory if inventory is not None else inspect_available_fonts()
    layout_model = str(direction.get("layout_model") or "")
    split = layout_model == "editorial_field_above_architecture"
    typography = _typography_plan(inventory, profile=str(direction.get("typography_profile") or "v1"))
    colors = _color_system()
    boxes = _compile_geometry(direction, width, height)
    hero_box = boxes["hero_visual"]
    dest_w = hero_box["x1"] - hero_box["x0"]
    dest_h = hero_box["y1"] - hero_box["y0"]
    focal = (0.50, 0.47) if split else (0.50, 0.48)
    crop = _cover_crop(source_size[0], source_size[1], dest_w, dest_h, focal=focal)
    crop["destination_geometry"] = dict(hero_box)
    hero_treatment = _hero_treatment(crop)
    if split:
        hero_treatment["brightness"] = 1.02
        hero_treatment["contrast"] = 1.10
        hero_treatment["overlay"] = "none_on_architecture_field"
        hero_treatment["mask_clip_shape"] = "architecture_field_rect"
    master_id = phase4_master_id or str(uuid4())
    native_id = spec_id or str(uuid4())
    elements = [
        {"id": "headline_line_1", "role": "headline", "kind": "text", "content_key": "headline_line_1", "geometry": _geom(boxes["headline_line_1"], width, height, anchor="top", align="center", z=40, parent="headline_group")},
        {"id": "headline_line_2", "role": "headline", "kind": "text", "content_key": "headline_line_2", "geometry": _geom(boxes["headline_line_2"], width, height, anchor="top", align="center", z=41, parent="headline_group")},
        {"id": "supporting_copy", "role": "supporting_copy", "kind": "text", "content_key": "supporting_copy", "geometry": _geom(boxes["supporting_copy"], width, height, anchor="top", align="center", z=42, parent="copy_group")},
        {"id": "unit_value", "role": "unit_value", "kind": "text", "content_key": "unit_value", "geometry": _geom(boxes["unit_column"], width, height, anchor="center", align="center", z=43, parent="commercial_group")},
        {"id": "unit_label", "role": "unit_label", "kind": "text", "content_key": "unit_label", "geometry": _geom(boxes["unit_column"], width, height, anchor="center", align="center", z=43, parent="commercial_group")},
        {"id": "list_price", "role": "list_price", "kind": "text", "content_key": "list_price", "geometry": _geom(boxes["price_column"], width, height, anchor="center", align="center", z=43, parent="commercial_group")},
        {"id": "discount_value", "role": "discount_value", "kind": "text", "content_key": "discount_value", "geometry": _geom(boxes["discount_column"], width, height, anchor="center", align="center", z=43, parent="commercial_group")},
        {"id": "discount_label", "role": "discount_label", "kind": "text", "content_key": "discount_label", "geometry": _geom(boxes["discount_column"], width, height, anchor="center", align="center", z=43, parent="commercial_group")},
        {"id": "cta", "role": "cta", "kind": "text_on_shape", "content_key": "cta", "geometry": _geom(boxes["cta"], width, height, anchor="bottom", align="center", z=50, parent="cta_group")},
        {"id": "logo", "role": "logo", "kind": "image_asset", "content_key": "logo", "geometry": _geom(boxes["logo"], width, height, anchor="bottom", align="center", z=55, parent="logo_group")},
        {"id": "hero_visual", "role": "hero_visual", "kind": "image_asset", "content_key": "hero_visual", "geometry": _geom(boxes["hero_visual"], width, height, anchor="canvas", align="cover", z=0, parent="hero_group")},
    ]
    groups = [
        {"id": "hero_group", "layout_model": "architecture_field" if split else "full_bleed", "children": ["hero_visual"], "geometry": boxes["hero_visual"]},
        {"id": "headline_group", "layout_model": "stacked_display", "children": ["headline_line_1", "headline_ornament", "headline_line_2"], "geometry": boxes["headline"]},
        {"id": "copy_group", "layout_model": "single_line", "children": ["supporting_copy"], "geometry": boxes["supporting_copy"]},
        {
            "id": "commercial_group",
            "layout_model": str(direction.get("commercial_layout") or "price_led_editorial_lockup"),
            "child_order": ["list_price", "unit", "discount"],
            "hierarchy": ["list_price", "discount_value", "unit_value"],
            "spacing": "editorial_air",
            "alignment": "center",
            "separators": ["commercial_middot"],
            "children": ["list_price", "unit_value", "unit_label", "discount_value", "discount_label"],
            "geometry": boxes["commercial_group"],
            "companion_presentation": str(direction.get("companion_presentation") or "stacked"),
            "not_kpi_cards": True,
            "not_v2_three_column_row": True,
        },
        {"id": "cta_group", "layout_model": "seam_inscription_bar" if split else "material_bar", "children": ["cta"], "geometry": boxes["cta"]},
        {"id": "logo_group", "layout_model": "contain_center", "children": ["logo"], "geometry": boxes["logo"]},
    ]
    render_instructions = [
        {"op": "place_hero", "id": "hero_visual"},
        {"op": "decoration", "id": "editorial_field" if split else "top_overlay"},
        {"op": "decoration", "id": "footer_fade"},
        {"op": "decoration", "id": "headline_ornament"},
        {"op": "decoration", "id": "commercial_middot"},
        {"op": "text", "id": "headline_line_1"},
        {"op": "text", "id": "headline_line_2"},
        {"op": "text", "id": "supporting_copy"},
        {"op": "commercial_facts", "id": "commercial_group"},
        {"op": "cta", "id": "cta"},
        {"op": "logo", "id": "logo"},
    ]
    spec: dict[str, Any] = {
        "schema": schema,
        "spec_version": spec_version,
        "native_master_design_spec_id": native_id,
        "phase4_master_id": master_id,
        "parent_native_master_design_spec_id": parent_spec_id,
        "polish_reason": polish_reason,
        "identity": {
            "native_master_design_spec_id": native_id,
            "spec_version": spec_version,
            "parent_native_master_design_spec_id": parent_spec_id,
            "project_id": str(project_id),
            "campaign_id": str(campaign_id),
            "test_identifier": PHASE4_TEST_KEY,
            "creative_type": "project_finished_advertisement",
            "format": CANVAS_FORMAT,
            "aspect_ratio": CANVAS_ASPECT,
            "created_at": _now(),
            "creative_direction_version": str(direction.get("creative_direction_version") or CREATIVE_DIRECTION_VERSION),
            "production": False,
        },
        "canvas": {
            "width": width,
            "height": height,
            "aspect_ratio": CANVAS_ASPECT,
            "format": CANVAS_FORMAT,
            "canonical": True,
            "do_not_switch": True,
        },
        "creative_direction": direction,
        "asset_policy": "PROJECT_LOCKED",
        "assets": {
            "hero_visual": {
                "asset_id": LOCKED_HERO_ASSET_ID,
                "role": "hero_visual",
                "project_id": str(project_id),
                "filename": HERO_FILENAME,
                "approval_state": "approved_project_asset",
                "architecture_lock": True,
                "replaceable": True,
                "replaceable_class": "REPLACEABLE_ASSET",
            },
            "logo": {
                "asset_id": LOCKED_LOGO_ASSET_ID,
                "role": "logo",
                "project_id": str(project_id),
                "identity_lock": True,
                "replaceable": False,
                "replaceable_class": "LOCKED_IDENTITY",
            },
        },
        "content": dict(REQUIRED_CONTENT),
        "regions": [
            {"id": name, "geometry": box}
            for name, box in boxes.items()
            if isinstance(box, dict) and "x0" in box
        ],
        "elements": elements,
        "groups": groups,
        "typography": typography,
        "colors": colors,
        "decorations": _decorations(boxes, colors, layout_model=layout_model),
        "image_treatments": {"hero": hero_treatment},
        "geometry": boxes,
        "relationships": [
            {"from": "headline_group", "to": "supporting_copy", "type": "above", "gap_strategy": "editorial_air"},
            {"from": "supporting_copy", "to": "commercial_group", "type": "above", "gap_strategy": "editorial_air"},
            {"from": "cta", "to": "logo", "type": "above", "gap_strategy": "footer_stack"},
            {"from": "commercial_group", "to": "hero_visual", "type": "above_not_overlapping" if split else "overlays"},
            {"from": "cta", "to": "hero_visual", "type": "seams_architecture_field" if split else "overlays_lower_third"},
        ],
        "constraints": [
            {"id": "architecture_lock", "rule": "Do not redraw or generate the building."},
            {"id": "logo_identity", "rule": "Use the real Temple logo asset only."},
            {"id": "canvas_lock", "rule": f"Canvas is {width}x{height}. Do not silently switch."},
            {"id": "no_kpi_cards", "rule": "Commercial facts are editorial, not dashboard cards."},
            {"id": "spec_drives_render", "rule": "Renderer executes this spec and invents no layout."},
            {"id": "architecture_collision", "rule": "Commercial typography must not enter the architecture field."},
        ],
        "flexibility": _flexibility(),
        "content_capacity": _content_capacity(split=split),
        "cta_treatment": _cta_treatment(boxes["cta"], typography, colors, seam=split),
        "logo_treatment": {
            "asset_id": LOCKED_LOGO_ASSET_ID,
            "fit": "contain",
            "geometry": boxes["logo"],
            "background": "footer_fade",
            "generated": False,
            "grade": {"brightness": 1.22, "contrast": 1.18} if split else {"brightness": 1.0, "contrast": 1.0},
        },
        "render_instructions": render_instructions,
        "provenance": {
            "spec_created_before_render": True,
            "extracted_from_raster": False,
            "legacy_master_design_spec": False,
            "native_renderer_template": False,
            "edit_map": False,
            "hybrid_revision": False,
            "ai_architecture_generation": False,
            "spec_finalized_at": _now(),
            "rendered_at": None,
            "pipeline": ["A_creative_direction", "B_validate", "C_resolve", "D_finalize"],
        },
        "revision_policy": _revision_policy(),
        "format_adaptation_policy": _format_adaptation_policy(),
        "rendered_master_visual_asset_id": None,
        "test_status": PHASE4_TEST_KEY,
        "validation_status": "pending",
    }
    spec["validation"] = validate_native_master_spec(spec)
    spec["validation_status"] = spec["validation"]["status"]
    if spec["validation_status"] != "pass":
        raise ValueError(f"NativeMasterDesignSpecV1 validation failed: {spec['validation']}")
    return spec


def validate_native_master_spec(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if spec.get("schema") not in {SCHEMA, SCHEMA_V1_1, SCHEMA_V2}:
        errors.append("schema")
    canvas = _as_dict(spec.get("canvas"))
    if int(canvas.get("width") or 0) != CANVAS_WIDTH or int(canvas.get("height") or 0) != CANVAS_HEIGHT:
        errors.append("canvas")
    assets = _as_dict(spec.get("assets"))
    hero = _as_dict(assets.get("hero_visual"))
    logo = _as_dict(assets.get("logo"))
    if str(hero.get("asset_id")) != LOCKED_HERO_ASSET_ID:
        errors.append("hero_asset_id")
    if str(logo.get("asset_id")) != LOCKED_LOGO_ASSET_ID:
        errors.append("logo_asset_id")
    if spec.get("asset_policy") != "PROJECT_LOCKED":
        errors.append("asset_policy")
    content = _as_dict(spec.get("content"))
    for key, value in REQUIRED_CONTENT.items():
        if str(content.get(key)) != value:
            errors.append(f"content:{key}")
    if spec.get("creative_direction", {}).get("layout_model") == "three_column_row":
        errors.append("layout_copied_v2")
    typography = _as_dict(spec.get("typography"))
    if not _as_dict(typography.get("roles")):
        errors.append("typography")
    for role in ("headline_line_1", "headline_line_2", "cta"):
        actual = _as_dict(_as_dict(typography.get("roles")).get(role)).get("actual_available_family")
        if not actual:
            errors.append(f"font:{role}")
    if not _as_dict(spec.get("colors")):
        errors.append("colors")
    if not _as_dict(_as_dict(spec.get("image_treatments")).get("hero")).get("source_crop_rectangle"):
        errors.append("hero_crop")
    if not spec.get("cta_treatment"):
        errors.append("cta_treatment")
    if not spec.get("decorations"):
        errors.append("decorations")
    if not spec.get("content_capacity"):
        errors.append("content_capacity")
    if not spec.get("flexibility"):
        errors.append("flexibility")
    if not spec.get("revision_policy"):
        errors.append("revision_policy")
    if not spec.get("format_adaptation_policy"):
        errors.append("format_adaptation_policy")
    if not spec.get("render_instructions"):
        errors.append("render_instructions")
    if spec.get("provenance", {}).get("extracted_from_raster"):
        errors.append("extracted_from_raster")
    if spec.get("provenance", {}).get("ai_architecture_generation"):
        errors.append("ai_architecture_generation")
    geometry = _as_dict(spec.get("geometry"))
    for name in ("headline", "cta", "logo", "hero_visual", "commercial_group"):
        box = _as_dict(geometry.get(name))
        if not box or box.get("x1", 0) <= box.get("x0", 0):
            errors.append(f"geometry:{name}")
    layout = str(_as_dict(spec.get("creative_direction")).get("layout_model") or "")
    if layout == "editorial_field_above_architecture":
        hero_box = _as_dict(geometry.get("hero_visual"))
        commercial = _as_dict(geometry.get("commercial_group"))
        if commercial.get("y1", 0) > hero_box.get("y0", 0):
            errors.append("architecture_collision")
        if spec.get("schema") == SCHEMA_V1_1 and not spec.get("parent_native_master_design_spec_id"):
            errors.append("parent_spec")
    protected = _as_dict(geometry.get("protected_architecture"))
    if protected and spec.get("schema") == SCHEMA_V2:
        for name in ("headline_line_2", "price_column", "commercial_group"):
            box = _as_dict(geometry.get(name))
            if box and _boxes_overlap(box, protected):
                errors.append(f"architecture_collision:{name}")
    return {"status": "pass" if not errors else "fail", "errors": errors}


def _boxes_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return not (
        int(a.get("x1") or 0) <= int(b.get("x0") or 0)
        or int(a.get("x0") or 0) >= int(b.get("x1") or 0)
        or int(a.get("y1") or 0) <= int(b.get("y0") or 0)
        or int(a.get("y0") or 0) >= int(b.get("y1") or 0)
    )


def mark_spec_rendered(spec: dict[str, Any]) -> dict[str, Any]:
    prov = _as_dict(spec.get("provenance"))
    if not prov.get("spec_finalized_at"):
        raise ValueError("spec must be finalized before render")
    if prov.get("extracted_from_raster"):
        raise ValueError("native spec cannot be extracted from raster")
    prov["rendered_at"] = _now()
    pipeline = list(prov.get("pipeline") or [])
    if "E_render_from_spec" not in pipeline:
        pipeline.append("E_render_from_spec")
    prov["pipeline"] = pipeline
    spec["provenance"] = prov
    return spec


def bind_rendered_visual(spec: dict[str, Any], visual_asset_id: str) -> dict[str, Any]:
    spec["rendered_master_visual_asset_id"] = str(visual_asset_id)
    prov = _as_dict(spec.get("provenance"))
    pipeline = list(prov.get("pipeline") or [])
    if "F_bind" not in pipeline:
        pipeline.append("F_bind")
    prov["pipeline"] = pipeline
    prov["bound_at"] = _now()
    spec["provenance"] = prov
    return spec


def build_finalized_native_master(
    *,
    source_size: tuple[int, int],
    project_id: str,
    campaign_id: str,
    hero_asset_id: str,
    logo_asset_id: str,
    brief: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Steps A–D: direction, validate, resolve, finalize. No raster yet."""
    direction = direct_native_master_creative(brief=brief)
    spec = materialize_native_master_spec(
        direction=direction,
        source_size=source_size,
        project_id=project_id,
        campaign_id=campaign_id,
        hero_asset_id=hero_asset_id,
        logo_asset_id=logo_asset_id,
    )
    if spec["provenance"].get("rendered_at"):
        raise RuntimeError("Spec must not be rendered during finalize.")
    return direction, spec


def polish_native_master_v1_1(
    parent: dict[str, Any],
    *,
    source_size: tuple[int, int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Steps A–D for Phase 4.0A. Does not mutate the parent V1 spec."""
    parent = dict(parent)
    if str(parent.get("native_master_design_spec_id")) != PHASE4_PARENT_SPEC_ID:
        raise ValueError("V1.1 polish requires the locked Phase 4.0 parent spec")
    if parent.get("schema") != SCHEMA:
        raise ValueError("parent must remain NativeMasterDesignSpecV1")
    direction = direct_native_master_creative_v11()
    spec = materialize_native_master_spec(
        direction=direction,
        source_size=source_size,
        project_id=str(_as_dict(parent.get("identity")).get("project_id") or TEMPLE_PROJECT_ID),
        campaign_id=str(_as_dict(parent.get("identity")).get("campaign_id") or PRODUCTION_CAMPAIGN_ID),
        hero_asset_id=LOCKED_HERO_ASSET_ID,
        logo_asset_id=LOCKED_LOGO_ASSET_ID,
        phase4_master_id=str(parent.get("phase4_master_id") or PHASE4_MASTER_ID),
        schema=SCHEMA_V1_1,
        spec_version=SPEC_VERSION_V1_1,
        parent_spec_id=str(parent["native_master_design_spec_id"]),
        polish_reason=POLISH_REASON,
    )
    if spec["provenance"].get("rendered_at"):
        raise RuntimeError("Polished spec must not be rendered during finalize.")
    if spec.get("content") != parent.get("content") and any(
        spec["content"][k] != parent["content"][k] for k in REQUIRED_CONTENT
    ):
        raise RuntimeError("Polish must not change semantic content.")
    return direction, spec


def persist_phase4_native_master(ctx: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Store the test master beside production. Never stamps v2 pointers."""
    spec_id = str(spec["native_master_design_spec_id"])
    master_id = str(spec["phase4_master_id"])
    visual_id = spec.get("rendered_master_visual_asset_id")
    masters = _as_dict(ctx.get("phase4_native_masters"))
    masters[spec_id] = spec
    ctx["phase4_native_masters"] = masters
    tests = _as_dict(ctx.get("phase4_native_master_tests"))
    tests[master_id] = {
        "phase4_master_id": master_id,
        "native_master_design_spec_id": spec_id,
        "master_visual_asset_id": visual_id,
        "test_identifier": PHASE4_TEST_KEY,
        "status": "test_master",
        "production": False,
        "schema": spec.get("schema"),
        "parent_native_master_design_spec_id": spec.get("parent_native_master_design_spec_id"),
    }
    ctx["phase4_native_master_tests"] = tests
    if spec.get("schema") == SCHEMA_V1_1:
        ctx["phase4a_native_master_spec_id"] = spec_id
        ctx["phase4_native_master_v1_spec_id"] = spec.get("parent_native_master_design_spec_id")
    ctx["phase4_native_master_current_test_id"] = master_id
    if spec.get("schema") == SCHEMA_V2:
        ctx["phase4b_native_master_spec_id"] = spec_id
        ctx["phase4b_native_master_id"] = master_id
        tests[master_id]["ai_art_direction_plan_id"] = spec.get("ai_art_direction_plan_id")
        tests[master_id]["test_identifier"] = spec.get("test_status") or "phase4b_generative_native_master_test"
        ctx["phase4_native_master_tests"] = tests
    # Explicit non-production: do not write current_cover / version / v1 spec pointer.
    return ctx


def production_pointers_unchanged(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    drifted = {k: (before.get(k), after.get(k)) for k in IDENTITY_KEYS if before.get(k) != after.get(k)}
    extra = {}
    for key in ("current_master_design_spec_id", "current_cover_asset_id"):
        if before.get(key) != after.get(key):
            extra[key] = (before.get(key), after.get(key))
    mc_before = _as_dict(before.get("master_creative"))
    mc_after = _as_dict(after.get("master_creative"))
    if mc_before.get("current_version") != mc_after.get("current_version"):
        extra["master_creative.current_version"] = (mc_before.get("current_version"), mc_after.get("current_version"))
    if mc_before.get("current_cover_asset_id") != mc_after.get("current_cover_asset_id"):
        extra["master_creative.current_cover_asset_id"] = (
            mc_before.get("current_cover_asset_id"),
            mc_after.get("current_cover_asset_id"),
        )
    if mc_before.get("current_master_design_spec_id") != mc_after.get("current_master_design_spec_id"):
        extra["master_creative.current_master_design_spec_id"] = (
            mc_before.get("current_master_design_spec_id"),
            mc_after.get("current_master_design_spec_id"),
        )
    return {**drifted, **extra}


def save_campaign_test_master_only(db: Session, campaign: Any, ctx: dict[str, Any], *, before_ctx: dict[str, Any]) -> None:
    from investhome_api.services.creative_director.master_design_spec import snapshot_identity

    drifted = production_pointers_unchanged(
        {**snapshot_identity(before_ctx), "master_creative": _as_dict(before_ctx.get("master_creative")), "current_master_design_spec_id": before_ctx.get("current_master_design_spec_id")},
        {**snapshot_identity(ctx), "master_creative": _as_dict(ctx.get("master_creative")), "current_master_design_spec_id": ctx.get("current_master_design_spec_id")},
    )
    if drifted:
        raise RuntimeError(f"Phase 4 persist would mutate production: {drifted}")
    if str(ctx.get("current_cover_asset_id") or _as_dict(ctx.get("master_creative")).get("current_cover_asset_id")) != PRODUCTION_COVER_V2:
        raise RuntimeError("Phase 4 persist refused: production cover is not approved v2")
    campaign.context_json = ctx
    flag_modified(campaign, "context_json")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)


def persist_native_master_visual(
    db: Session,
    *,
    actor: Any,
    linked_project_id: UUID,
    content: bytes,
    spec_id: str,
    master_id: str,
) -> Any:
    from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset, MediaAssetSourceType
    from investhome_api.services.creative_studio_media_service import MEDIA_STORAGE_PREFIX
    from investhome_api.services.document_validation import content_stream
    from investhome_api.services.storage.factory import get_storage_provider, provider_enum

    now = datetime.now(UTC)
    storage_key = f"{MEDIA_STORAGE_PREFIX}/{now.year:04d}/{now.month:02d}/{uuid4().hex}.png"
    storage = get_storage_provider()
    storage.save(storage_key, content_stream(content), content_length=len(content))
    width = height = None
    try:
        from PIL import Image

        with Image.open(BytesIO(content)) as img:
            width, height = int(img.size[0]), int(img.size[1])
    except Exception:
        pass
    asset = CreativeStudioMediaAsset(
        filename=f"phase4-native-master-{master_id[:8]}.png",
        content_type="image/png",
        file_size=len(content),
        width=width,
        height=height,
        storage_provider=provider_enum().value,
        storage_key=storage_key,
        linked_project_id=linked_project_id,
        uploaded_by_user_id=getattr(actor, "id", None),
        source_type=MediaAssetSourceType.UPLOAD.value,
        tags=[
            "phase4-native-master",
            PHASE4_TEST_KEY,
            f"spec:{spec_id}",
            f"master:{master_id}",
            "production:false",
        ],
    )
    db.add(asset)
    db.flush()
    return asset


def consistency_report(spec: dict[str, Any], drawn: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    content = _as_dict(spec.get("content"))
    drawn_text = " ".join(str(item) for item in (drawn.get("drawn_content") or []))
    for key in ("headline_line_1", "headline_line_2", "supporting_copy", "unit_value", "unit_label", "list_price", "discount_value", "discount_label", "cta"):
        token = str(content.get(key) or "")
        if token and token not in drawn_text:
            errors.append(f"missing_from_raster:{key}")
    canvas = _as_dict(spec.get("canvas"))
    size = drawn.get("canvas") or {}
    if int(size.get("width") or 0) != int(canvas.get("width") or 0):
        errors.append("canvas_width")
    if int(size.get("height") or 0) != int(canvas.get("height") or 0):
        errors.append("canvas_height")
    if str(drawn.get("hero_asset_id")) != LOCKED_HERO_ASSET_ID:
        errors.append("hero_asset")
    if str(drawn.get("logo_asset_id")) != LOCKED_LOGO_ASSET_ID:
        errors.append("logo_asset")
    if drawn.get("ai_architecture_generation"):
        errors.append("architecture_generated")
    spec_roles = {str(el.get("role")) for el in (spec.get("elements") or [])}
    drawn_roles = list(drawn.get("drawn_roles") or [])
    for role in drawn_roles:
        if role not in spec_roles and role not in {"decoration", "headline"}:
            errors.append(f"raster_without_spec:{role}")
    for role in SEMANTIC_ROLES:
        if role == "headline":
            if "headline" not in drawn_roles:
                errors.append("spec_missing_from_raster:headline")
            continue
        if role not in drawn_roles:
            errors.append(f"spec_missing_from_raster:{role}")
    fonts = drawn.get("fonts_used") or []
    planned = set(_as_dict(spec.get("typography")).get("actual_fonts_used") or [])
    if planned and fonts:
        for path in fonts:
            if path not in planned and path != "PIL-default":
                errors.append(f"unexpected_font:{path}")
    geometry = _as_dict(spec.get("geometry"))
    commercial = _as_dict(geometry.get("commercial_group"))
    hero_box = _as_dict(geometry.get("hero_visual"))
    layout = str(_as_dict(spec.get("creative_direction")).get("layout_model") or "")
    if layout == "editorial_field_above_architecture" and commercial.get("y1", 0) > hero_box.get("y0", 0):
        errors.append("architecture_collision")
    for box in drawn.get("drawn_boxes") or []:
        if int(box.get("x0") or 0) < 0 or int(box.get("y0") or 0) < 0:
            errors.append(f"clip:{box.get('id')}")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "drawn_content": drawn.get("drawn_content") or [],
        "architecture_collision": "RESOLVED" if layout == "editorial_field_above_architecture" and "architecture_collision" not in errors else (
            "N/A" if layout != "editorial_field_above_architecture" else "FAIL"
        ),
    }
