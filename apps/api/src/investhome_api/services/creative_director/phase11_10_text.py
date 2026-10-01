"""Factual text validation + minimum typographic repair that follows the AI master."""

from __future__ import annotations

import json
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image

from investhome_api.services.creative_director.phase5_design_scene import _jpeg_b64, _vision
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_10_strategy import HEADLINE
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

REQUIRED_STRINGS = (
    "THE TEMPLE",
    "WASHINGTON D.C.",
    REQUIRED_FACTS["discount"],
    REQUIRED_FACTS["discount_label"],
    REQUIRED_FACTS["list_price"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["cta"],
)


def _normalize(text: str) -> str:
    up = (text or "").replace("\u00a0", " ").upper()
    up = up.replace("İ", "I").replace("İ", "I").replace("ı", "I")
    return " ".join(up.split())
    return " ".join((text or "").replace("\u00a0", " ").upper().split())


def validate_campaign_text(image: Image.Image) -> dict[str, Any]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Transcribe every visible text string in the advertisement. JSON only. Do not praise.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "return": {
                                    "visible_strings": ["exact strings as seen"],
                                    "regions": [
                                        {
                                            "copy": "string",
                                            "x": "0-1",
                                            "y": "0-1",
                                            "w": "0-1",
                                            "h": "0-1",
                                            "fill": "hex if obvious",
                                            "role": "project|location|headline|offer|price|unit|cta|closure|other",
                                        }
                                    ],
                                    "invented_claims": ["any ROI/date/other project names"],
                                    "spelling_errors": ["wrong Temple facts"],
                                }
                            }
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image, 90)}", "detail": "high"},
                    },
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    blob = dict(parsed or {})
    visible = [str(item) for item in (blob.get("visible_strings") or [])]
    joined = _normalize(" | ".join(visible))
    missing = []
    for token in REQUIRED_STRINGS:
        if _normalize(token) not in joined and token.replace(" ", "") not in joined.replace(" ", ""):
            # allow split across strings
            parts = token.split()
            if not all(_normalize(p) in joined for p in parts if len(p) > 1):
                missing.append(token)
    invented = [str(item) for item in (blob.get("invented_claims") or [])]
    errors = [str(item) for item in (blob.get("spelling_errors") or [])]
    ok = not missing and not invented and not errors
    return {
        "schema": "Phase1110TextValidation",
        "visible_strings": visible,
        "regions": blob.get("regions") or [],
        "missing": missing,
        "invented_claims": invented,
        "spelling_errors": errors,
        "pass": ok,
        "vision_calls": calls,
        "headline_seen": HEADLINE in " ".join(visible),
        "closure_seen": APPROVED_BOTTOM_COPY.split(",")[0] in " ".join(visible),
    }


def apply_factual_text_repair(image: Image.Image, validation: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    """Rebuild only missing/wrong facts, following the master's existing type territories."""
    if validation.get("pass"):
        return image, {"required": False, "changed": False}
    missing = list(validation.get("missing") or [])
    if not missing:
        return image, {"required": False, "changed": False, "note": "invented/spelling only — repair refused without missing facts"}
    # Follow AI regions when present; otherwise use the master's dark lower/upper field, not a new layout system.
    regions = list(validation.get("regions") or [])
    W, H = image.size
    from investhome_api.services.creative_director.phase11_7_compose import render_svg_html_to_png
    from investhome_api.services.creative_director.creative_font_registry import build_font_registry
    import base64
    from pathlib import Path

    registry = build_font_registry()

    def face(role: str, family: str) -> str:
        spec = dict((registry.get("roles") or {}).get(role) or {})
        path = spec.get("font_path")
        if not path or not Path(str(path)).is_file():
            return ""
        payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
        return (
            f"@font-face{{font-family:'{family}';src:url('data:font/ttf;base64,{payload}') "
            f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
        )

    font_css = "\n".join(
        block
        for block in (
            face("DISPLAY_SERIF", "Hybrid Serif"),
            face("DISPLAY_SANS", "Hybrid Grotesk"),
        )
        if block
    )
    nodes = []
    used = set()
    for token in missing:
        match = next((r for r in regions if token.split()[0].upper() in _normalize(str(r.get("copy") or ""))), None)
        if match:
            x = float(match.get("x") or 0.08) * W
            y = float(match.get("y") or 0.12) * H + float(match.get("h") or 0.04) * H
            size = max(18, int(float(match.get("h") or 0.04) * H * 0.7))
        else:
            # Follow a single existing commercial altitude: lower-left climate, not a new column system.
            idx = len(used)
            x, y, size = 64, H - 220 + idx * 36, 22 if idx else 28
        used.add(token)
        fill = "#EDE6D8"
        nodes.append(
            f'<text x="{int(x)}" y="{int(y)}" font-family="Hybrid Serif, serif" font-size="{size}" '
            f'font-weight="600" fill="{fill}">{escape(token)}</text>'
        )
    import io as _io
    import base64 as _b64

    buf = _io.BytesIO()
    image.save(buf, format="PNG")
    href = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")
    markup = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><style>{font_css}html,body{{margin:0}}</style></head>
<body><svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<image href="{href}" x="0" y="0" width="{W}" height="{H}"/>
{''.join(nodes)}
</svg></body></html>"""
    repaired = render_svg_html_to_png(markup, width=W, height=H, scale=1)
    return repaired, {"required": True, "changed": True, "repaired": missing, "followed_regions": bool(regions)}
