"""ProjectRealityFirewallV1 — generated fields may not contain project architecture."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageFilter, ImageStat

from investhome_api.services.creative_director.phase5_design_scene import VISION_MODEL, _jpeg_b64, _vision

SCHEMA = "ProjectRealityFirewallV1"
MAX_FIELD_ATTEMPTS = 3

FORBIDDEN_FLAGS = (
    "contains_building",
    "contains_interior",
    "contains_exterior_architecture",
    "contains_project_logo",
    "contains_project_facts",
    "contains_readable_text",
    "contains_numbers",
    "contains_windows_or_facade",
    "contains_spire_or_tower",
)


def _heuristic_architecture_suspicion(image: Image.Image) -> dict[str, Any]:
    """Conservative extra check. Vision is authoritative; this catches obvious city photos."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    small = rgb.resize((96, max(8, int(round(96 * h / max(w, 1))))), Image.Resampling.BOX)
    lum = small.convert("L")
    edges = lum.filter(ImageFilter.FIND_EDGES)
    edge_mean = float(ImageStat.Stat(edges).mean[0])
    sw, sh = small.size
    sp, lp = small.load(), lum.load()
    skyish = 0
    windowish = 0
    n = sw * sh
    for y in range(sh):
        yn = y / max(sh - 1, 1)
        for x in range(sw):
            r, g, b = sp[x, y]
            sat = max(r, g, b) - min(r, g, b)
            if yn < 0.42 and int(lp[x, y]) > 150 and sat < 40 and b >= r - 4:
                skyish += 1
            if 0.18 < yn < 0.78 and sat < 28 and 70 < int(lp[x, y]) < 170:
                if x + 1 < sw and abs(int(lp[x, y]) - int(lp[x + 1, y])) > 28:
                    windowish += 1
    return {
        "edge_mean": round(edge_mean, 3),
        "skyish_ratio": round(skyish / max(n, 1), 4),
        "windowish_ratio": round(windowish / max(n, 1), 4),
        "suspect_city_photo": edge_mean > 28 and skyish / max(n, 1) > 0.18 and windowish / max(n, 1) > 0.04,
    }


def inspect_generated_field(field: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You inspect a candidate advertising FIELD, not a finished ad. "
                    "The field must contain NO architecture, NO interior, NO exterior building, "
                    "NO logo, NO letters, NO numbers. JSON only. Be literal."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Does this image contain any building, interior room, exterior architecture, "
                            "façade, windows, spire, tower, city, logo, readable text, or numbers? "
                            "JSON booleans: contains_building, contains_interior, contains_exterior_architecture, "
                            "contains_project_logo, contains_project_facts, contains_readable_text, contains_numbers, "
                            "contains_windows_or_facade, contains_spire_or_tower, looks_like_photograph_of_a_place. "
                            "Also notes (short)."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(field)}", "detail": "high"},
                    },
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    flags = {key: bool(parsed.get(key)) for key in FORBIDDEN_FLAGS}
    flags["looks_like_photograph_of_a_place"] = bool(parsed.get("looks_like_photograph_of_a_place"))
    return {
        "schema": "GeneratedFieldInspectV1",
        "mode": "vision" if parsed else "unavailable",
        "flags": flags,
        "notes": str(parsed.get("notes") or ""),
        "raw": parsed,
    }, calls


def evaluate_firewall(
    inspect: dict[str, Any],
    *,
    heuristic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flags = dict((inspect or {}).get("flags") or {})
    mode = str((inspect or {}).get("mode") or "unavailable")
    hits = [key for key, on in flags.items() if on]
    if mode != "vision":
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "reason": "vision_unavailable_fail_closed",
            "hits": hits,
            "inspect": inspect,
            "heuristic": heuristic or {},
        }
    if hits:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "reason": "generated_field_contains_forbidden_imagery",
            "hits": hits,
            "inspect": inspect,
            "heuristic": heuristic or {},
        }
    if heuristic and heuristic.get("suspect_city_photo"):
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "reason": "heuristic_city_photo_suspicion",
            "hits": ["heuristic_city_photo"],
            "inspect": inspect,
            "heuristic": heuristic,
        }
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "reason": None,
        "hits": [],
        "inspect": inspect,
        "heuristic": heuristic or {},
    }


def run_project_reality_firewall(field: Image.Image) -> dict[str, Any]:
    inspect, calls = inspect_generated_field(field)
    heuristic = _heuristic_architecture_suspicion(field)
    result = evaluate_firewall(inspect, heuristic=heuristic)
    result["vision_calls"] = calls
    return result
