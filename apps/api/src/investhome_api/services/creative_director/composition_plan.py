"""Full Composition Plan — Creative Director decides layout before editable render.

EDITABILITY is a rendering property. This plan is the design; Design Spec encodes it.
"""

from __future__ import annotations

from typing import Any


GOLDEN_PRINCIPLES: dict[str, Any] = {
    "composition": (
        "Photograph-led full-bleed with intentional negative space; text rides dark/light "
        "contrast zones — never a flat top-stack of logo→headline→CTA."
    ),
    "hierarchy": (
        "ONE primary message; headline or price leads by intent; support quieter; single CTA."
    ),
    "typography": (
        "Display/serif for hero line; restrained sans for support/price/CTA; deliberate size jumps."
    ),
    "image_treatment": (
        "Preserve master asset quality; add editable gradient/overlay contrast — do not AI-regrade."
    ),
    "negative_space": "Let the photograph breathe; premium ≠ more elements.",
    "overlays": "Localized dark or light gradients for text-safe zones as editable layers.",
    "logo": "One real project logo; top-left or top-center by intent; never invent.",
    "cta": "Single clear actionable CTA; proportionate pill/button — not tiny footer text.",
    "spacing": "Safe margins ~6–8% width; consistent rhythm between eyebrow→headline→support→CTA.",
    "density": "Sparse for lifestyle/location; medium only when price/offer requires it.",
    "alignment": "Intent-specific: left price stack, center brand/lifestyle, split location.",
    "focal_point": "Image focal zone reserved; type sits in planned text-safe areas.",
}


def _intent_family(intent: str) -> str:
    kind = (intent or "general_awareness").strip().lower()
    if kind in {"price_campaign", "sales_offer", "launch", "launch_price"}:
        return "price"
    if kind in {"location"}:
        return "location"
    if kind in {"lifestyle", "amenities"}:
        return "lifestyle"
    if kind in {"project_brand", "architecture", "general_awareness"}:
        return "project_brand"
    return "general"


def build_composition_plan(
    *,
    campaign_intent: str,
    production_brief: dict[str, Any] | None = None,
    texts: dict[str, str] | None = None,
    design_direction: dict[str, Any] | None = None,
    message_strategy: dict[str, Any] | None = None,
    aspect_ratio: str = "4:5",
    language: str = "tr",
) -> dict[str, Any]:
    """Emit a full composition plan from CD brief + intent (no pixel inventing beyond plan)."""
    pb = production_brief or {}
    tx = texts or {}
    dd = design_direction or pb.get("design_direction") or {}
    ms = message_strategy or pb.get("message_strategy") or {}
    intent = (campaign_intent or pb.get("campaign_intent") or "general_awareness").strip().lower()
    family = _intent_family(intent)

    primary = (
        str(ms.get("primary_message") or ms.get("hero_headline") or tx.get("headline") or pb.get("hero") or "")
        .strip()
    )
    secondary = ""
    supporting = pb.get("supporting") if isinstance(pb.get("supporting"), list) else []
    if supporting:
        secondary = str(supporting[0]).strip()
    elif ms.get("supporting_messages"):
        secondary = str((ms.get("supporting_messages") or [""])[0]).strip()

    margin_x = 0.07
    margin_y = 0.045

    if family == "price":
        plan = {
            "layout_family": "price_lower_third",
            "focal_point": {
                "zone": "upper_mid_image",
                "description": "Living/interior subject stays clear above the offer stack",
            },
            "image": {
                "crop": "cover",
                "position": "center",
                "treatment": "bottom_dark_gradient",
            },
            "zones": {
                "dark": [{"anchor": "bottom", "height_pct": 0.48}],
                "light": [],
                "text_safe": [{"anchor": "bottom", "y_pct": 0.48, "height_pct": 0.46}],
            },
            "typography": {
                "headline": {
                    "placement": "lower_third_left",
                    "scale": "hero",
                    "align": "left",
                    "color": "#F7F3EB",
                    "font_family": "serif",
                },
                "eyebrow": {
                    "placement": "above_headline",
                    "scale": "small_caps",
                    "align": "left",
                    "color": "#C4A35A",
                    "font_family": "sans",
                },
                "secondary": {
                    "placement": "below_headline",
                    "scale": "body",
                    "align": "left",
                    "color": "#E8E0D4",
                    "font_family": "sans",
                },
                "price": {
                    "placement": "mid_lower_stack",
                    "scale": "price_hero",
                    "align": "left",
                    "color": "#C4A35A",
                    "font_family": "sans",
                },
                "cta": {
                    "placement": "bottom_left",
                    "scale": "action",
                    "align": "center",
                    "color": "#1A1510",
                    "font_family": "sans",
                },
            },
            "logo": {"placement": "top_left", "scale": 0.20, "align": "left"},
            "cta": {"placement": "bottom_left", "style": "gold_pill", "width_pct": 0.62},
            "decorative": [
                "bottom_dark_gradient",
                "eyebrow_pill",
                "price_frame",
                "discount_badge",
                "gold_divider",
            ],
            "density": "medium",
            "alignment": "left",
            "balance": "image_above_offer_stack",
        }
    elif family == "location":
        plan = {
            "layout_family": "location_place_led",
            "focal_point": {
                "zone": "right_architecture",
                "description": "Architecture/street reads on the open side; type on quieter side",
            },
            "image": {
                "crop": "cover",
                "position": "center",
                "treatment": "top_dark_gradient",
            },
            "zones": {
                "dark": [
                    {"anchor": "top", "height_pct": 0.22},
                    {"anchor": "left_mid", "height_pct": 0.35},
                ],
                "light": [],
                "text_safe": [
                    {"anchor": "upper_center", "y_pct": 0.10, "height_pct": 0.28},
                    {"anchor": "mid_left", "y_pct": 0.42, "height_pct": 0.28},
                ],
            },
            "typography": {
                "headline": {
                    "placement": "upper_center",
                    "scale": "hero",
                    "align": "center",
                    "color": "#FFFFFF",
                    "accent_color": "#C4A35A",
                    "font_family": "serif",
                },
                "eyebrow": {
                    "placement": "below_logo",
                    "scale": "small_caps",
                    "align": "center",
                    "color": "#C4A35A",
                    "font_family": "sans",
                },
                "secondary": {
                    "placement": "mid_left",
                    "scale": "body",
                    "align": "left",
                    "color": "#F7F3EB",
                    "font_family": "sans",
                },
                "cta": {
                    "placement": "bottom_left",
                    "scale": "action",
                    "align": "center",
                    "color": "#1A1510",
                    "font_family": "sans",
                },
            },
            "logo": {"placement": "top_center", "scale": 0.18, "align": "center"},
            "cta": {"placement": "bottom_left", "style": "gold_pill", "width_pct": 0.48},
            "decorative": ["top_dark_gradient", "eyebrow_pill", "gold_divider"],
            "density": "sparse",
            "alignment": "center_then_left",
            "balance": "place_headline_over_architecture",
        }
    elif family == "lifestyle":
        plan = {
            "layout_family": "lifestyle_editorial",
            "focal_point": {
                "zone": "center_interior",
                "description": "Interior lifestyle dominates mid-frame; type in light top + soft bottom",
            },
            "image": {
                "crop": "cover",
                "position": "center",
                "treatment": "top_light_bottom_dark",
            },
            "zones": {
                "dark": [{"anchor": "bottom", "height_pct": 0.28}],
                "light": [{"anchor": "top", "height_pct": 0.32}],
                "text_safe": [
                    {"anchor": "top", "y_pct": 0.06, "height_pct": 0.28},
                    {"anchor": "bottom", "y_pct": 0.74, "height_pct": 0.22},
                ],
            },
            "typography": {
                "headline": {
                    "placement": "upper_center",
                    "scale": "editorial_hero",
                    "align": "center",
                    "color": "#2A241C",
                    "accent_color": "#C4A35A",
                    "font_family": "serif",
                },
                "eyebrow": {
                    "placement": "below_logo",
                    "scale": "small_caps",
                    "align": "center",
                    "color": "#8A7355",
                    "font_family": "sans",
                },
                "secondary": {
                    "placement": "bottom_row",
                    "scale": "caption",
                    "align": "center",
                    "color": "#F7F3EB",
                    "font_family": "sans",
                },
                "cta": {
                    "placement": "bottom_center",
                    "scale": "action",
                    "align": "center",
                    "color": "#1A1510",
                    "font_family": "sans",
                },
            },
            "logo": {"placement": "top_center", "scale": 0.17, "align": "center"},
            "cta": {"placement": "bottom_center", "style": "soft_gold_pill", "width_pct": 0.46},
            "decorative": ["top_light_gradient", "bottom_soft_dark", "feature_dots"],
            "density": "sparse",
            "alignment": "center",
            "balance": "image_dominant_editorial",
        }
    else:
        plan = {
            "layout_family": "project_brand_minimal",
            "focal_point": {
                "zone": "center_architecture",
                "description": "Brand mark + architecture; minimal editorial",
            },
            "image": {
                "crop": "cover",
                "position": "center",
                "treatment": "soft_vignette",
            },
            "zones": {
                "dark": [{"anchor": "bottom", "height_pct": 0.22}],
                "light": [{"anchor": "top", "height_pct": 0.18}],
                "text_safe": [{"anchor": "upper_center", "y_pct": 0.08, "height_pct": 0.22}],
            },
            "typography": {
                "headline": {
                    "placement": "upper_center",
                    "scale": "brand",
                    "align": "center",
                    "color": "#F7F3EB",
                    "font_family": "serif",
                },
                "secondary": {
                    "placement": "below_headline",
                    "scale": "body",
                    "align": "center",
                    "color": "#E8E0D4",
                    "font_family": "sans",
                },
                "cta": {
                    "placement": "bottom_center",
                    "scale": "action",
                    "align": "center",
                    "color": "#1A1510",
                    "font_family": "sans",
                },
            },
            "logo": {"placement": "top_center", "scale": 0.24, "align": "center"},
            "cta": {"placement": "bottom_center", "style": "gold_pill", "width_pct": 0.44},
            "decorative": ["soft_vignette", "bottom_soft_dark"],
            "density": "sparse",
            "alignment": "center",
            "balance": "logo_architecture_minimal",
        }

    return {
        "version": 2,
        "campaign_intent": intent,
        "layout_family": plan["layout_family"],
        "language": language,
        "aspect_ratio": aspect_ratio,
        "primary_message": primary,
        "secondary_message": secondary,
        "focal_point": plan["focal_point"],
        "image": plan["image"],
        "zones": plan["zones"],
        "typography": plan["typography"],
        "logo": plan["logo"],
        "cta": plan["cta"],
        "decorative_elements": plan["decorative"],
        "badges": family == "price",
        "dividers": "gold_divider" in plan["decorative"],
        "overlays": [d for d in plan["decorative"] if "gradient" in d or "vignette" in d or "dark" in d or "light" in d],
        "gradients": [d for d in plan["decorative"] if "gradient" in d or "vignette" in d],
        "content_density": plan["density"],
        "alignment_system": plan["alignment"],
        "safe_margins": {"x_pct": margin_x, "y_pct": margin_y},
        "visual_balance": plan["balance"],
        "design_direction_echo": {
            "visual_mood": dd.get("visual_mood"),
            "hierarchy": dd.get("hierarchy"),
            "information_density": dd.get("information_density") or plan["density"],
        },
        "golden_principles": GOLDEN_PRINCIPLES,
    }
