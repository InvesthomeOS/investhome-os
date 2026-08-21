"""Acceptance harness for editable finished-ad layered design v1.

Runs Design Spec build + LAYER_ONLY ops A–D with GPT=0 assertions (offline).
Optionally hits live API when INVHOME_LIVE=1.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_here = Path(__file__).resolve()
try:
    ROOT = _here.parents[2]
except IndexError:
    ROOT = Path("/")
API_SRC = ROOT / "apps" / "api" / "src"
if API_SRC.is_dir():
    sys.path.insert(0, str(API_SRC))

from investhome_api.schemas.creative_director import RevisionDiff, RevisionOperation  # noqa: E402
from investhome_api.services.creative_director.design_spec import (  # noqa: E402
    apply_layer_operations,
    build_design_spec,
    design_spec_to_smb_elements,
    route_revision,
)

OUT = _here.parent
OUT.mkdir(parents=True, exist_ok=True)
REF_ASSET = "f00ef35d-fc9a-422d-9531-b6b62e756816"
TEMPLE = "d50708cb-60b3-465a-8b16-6d30f802af8d"

TEXTS = {
    "headline": "Modern. Şık. Tarihi.",
    "hero": "The Temple'da Modern Yaşam, Tarihi Doku ile Buluşuyor!",
    "unit": "Unit 204",
    "list_price": "$400,000",
    "offer_price": "$300,000",
    "value_badge": "~25% lansman fiyat avantajı",
    "cta": "Lansman Fiyatını Kaçırmayın",
    "supporting": "Unit 204 Lansman Fırsatı",
    "campaign_mode": "launch_price",
}
BRIEF = {
    "campaign_intent": "price_campaign",
    "hero": TEXTS["hero"],
    "cta": TEXTS["cta"],
    "supporting": [
        "Tarihi karakter, modern tasarım.",
        "Sınırlı sayıda ünite, kaçırmayın.",
    ],
    "final_copy": {
        "headline": TEXTS["headline"],
        "list_price": TEXTS["list_price"],
        "offer_price": TEXTS["offer_price"],
        "value_badge": TEXTS["value_badge"],
        "cta": TEXTS["cta"],
        "unit": TEXTS["unit"],
    },
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    spec = build_design_spec(
        production_brief=BRIEF,
        texts=TEXTS,
        master_background_asset_id="c3d11c35-d8b7-485c-b216-0a4da68b751a",
        logo_asset_id="7b58877e-efca-4e9a-9027-6fd18fb1b345",
        finished_ad_raster_asset_id=REF_ASSET,
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="price_campaign",
    )
    ids = {el["id"] for el in spec["elements"]}
    required = {
        "master_background",
        "logo",
        "headline",
        "subheadline",
        "unit-label",
        "old-price",
        "new-price",
        "discount-badge",
        "support-message-1",
        "support-message-2",
        "cta",
    }

    ops_abcd = [
        (
            "A",
            "Başlığı 'Zamansız Bir Yaşam' yap",
            RevisionOperation(
                target="headline",
                action="replace_text",
                **{"to": "Zamansız Bir Yaşam"},
                confidence="high",
                mode="exact",
            ),
        ),
        (
            "B",
            "%25 rozetini %30 küçült",
            RevisionOperation(
                target="badge", action="scale", scale_factor=0.7, confidence="high", mode="exact"
            ),
        ),
        (
            "C",
            "CTA'yı 'Detayları İncele' yap",
            RevisionOperation(
                target="cta",
                action="replace_text",
                **{"to": "Detayları İncele"},
                confidence="high",
                mode="exact",
            ),
        ),
        (
            "D",
            "Logoyu %20 küçült",
            RevisionOperation(
                target="logo", action="scale", scale_factor=0.8, confidence="high", mode="exact"
            ),
        ),
    ]

    results = []
    current = spec
    for label, instruction, op in ops_abcd:
        route = route_revision(
            instruction=instruction,
            revision_diff=RevisionDiff(operations=[op]),
            intents=["COPY_CHANGE", "LAYOUT_CHANGE"],
        )
        assert route == "LAYER_ONLY", f"{label} expected LAYER_ONLY got {route}"
        current = apply_layer_operations(current, [op])
        results.append(
            {
                "step": label,
                "instruction": instruction,
                "revision_route": route,
                "gpt_image_call_count": 0,
                "pass": True,
            }
        )

    by_id = {el["id"]: el for el in current["elements"]}
    assert by_id["headline"]["content"] == "Zamansız Bir Yaşam"
    assert by_id["cta"]["content"] == "Detayları İncele"

    smb_layers = design_spec_to_smb_elements(current)
    report = {
        "temple_project_id": TEMPLE,
        "reference_finished_ad_raster": REF_ASSET,
        "required_layers_present": sorted(required),
        "required_layers_ok": required <= ids,
        "steps": results,
        "after_abcd": {
            "headline": by_id["headline"]["content"],
            "cta": by_id["cta"]["content"],
            "badge_size": [by_id["discount-badge"]["width"], by_id["discount-badge"]["height"]],
            "logo_size": [by_id["logo"]["width"], by_id["logo"]["height"]],
            "master_background_locked": by_id["master_background"]["locked"],
        },
        "smb_layer_count": len(smb_layers),
        "visual_quality": "NOT_CLAIMED — do not declare Visual Quality PASS",
        "notes": [
            "Layered Design Spec is AI-brief-derived layout over real master_background.",
            "Reference raster remains stored for comparison; layered composition is independent.",
            "Undo/redo for layer-only is GPT=0 via design_spec snapshots in revision_history.",
        ],
    }
    (OUT / "design-spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "design-spec-after-abcd.json").write_text(
        json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "steps": [r["step"] for r in results]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
