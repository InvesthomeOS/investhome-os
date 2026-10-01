"""CreativeExecutionTokensV1 — family-owned craft tokens. No generic fallback when present."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, INK, IVORY, _hex


def execution_tokens(family: dict[str, Any]) -> dict[str, Any]:
    typo = dict(family.get("typography") or {})
    spacing = dict(family.get("spacing") or {})
    devices = dict(family.get("graphic_devices") or {})
    brand = dict(family.get("brand") or {})
    headline = dict(family.get("headline") or {})
    family_id = str(family.get("family_id") or "")
    return {
        "schema": "CreativeExecutionTokensV1",
        "family_id": family_id,
        "display_font": str(typo.get("display_role") or "DISPLAY_SERIF"),
        "display_weight": "regular",
        "display_scale": float(typo.get("display_scale") or 0.07),
        "display_tracking": float(typo.get("tracking_display") or 20),
        "display_leading": 0.92,
        "body_font": str(typo.get("support_role") or "EDITORIAL_SANS"),
        "body_weight": "regular",
        "commercial_font": str(typo.get("number_role") or "COMMERCIAL_NUMBER"),
        "commercial_number_scale": float(typo.get("number_scale") or 0.046),
        "commercial_label_scale": float(typo.get("secondary_scale") or 0.02),
        "primary_color": _hex(str(typo.get("text_hex") or devices.get("text_hex") or ""), IVORY),
        "secondary_color": _hex(str(typo.get("ink_hex") or ""), INK),
        "accent_color": _hex(str(typo.get("accent_hex") or devices.get("accent_hex") or ""), GOLD),
        "rule_weight": 2 if str(devices.get("rule") or "") != "none" else 0,
        "rule_length_behavior": "match_last_display_line",
        "group_spacing_ratio": {
            "headline_internal": float(spacing.get("column_gap") or 0.008),
            "headline_to_unit": float(spacing.get("after_headline") or 0.022),
            "unit_to_commercial": float(spacing.get("after_unit") or 0.016),
            "price_to_advantage": float(spacing.get("after_price") or 0.012),
            "commercial_to_cta": float(spacing.get("after_offer") or 0.046),
            "logo_clear": float(brand.get("clear_space") or 0.04),
        },
        "logo_scale_ratio": float(brand.get("relative_scale") or 0.16),
        "cta_scale_ratio": 0.018,
        "alignment": str(headline.get("alignment") or "right"),
        "split_last_line_gold": bool(headline.get("split_last_line_gold")),
        "image_field_behavior": str((family.get("photo") or {}).get("crop_philosophy") or "architecture_as_material"),
        "graphic_field_behavior": str(devices.get("overlay") or "local_plane_darken"),
        "field_hex": str(devices.get("field_hex") or "#14181E"),
        "scale_min": float((family.get("flexibility") or {}).get("scale_min") or 0.78),
        "scale_max": float((family.get("flexibility") or {}).get("scale_max") or 1.08),
        "source": "CreativeMasterFamilySpecV1",
    }
