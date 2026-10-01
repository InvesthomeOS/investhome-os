"""Render Phase 11.8 capability proofs. No campaign. No image generation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import _read_bytes
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID
from investhome_api.services.creative_director.phase11_8_boards import (
    contact_test_board,
    edge_test_board,
    hierarchy_scale_board,
    material_test_board,
)
from investhome_api.services.creative_director.project_object_extraction_v2 import (
    EDGE_BACKGROUNDS,
    extract_project_object_v2,
    inspect_fringe,
    spire_preserved,
)
from investhome_api.services.creative_director.responsive_commercial_hierarchy_v2 import render_hierarchy_proof
from investhome_api.services.creative_director.scene_material_integration_v2 import (
    analyze_field,
    contact_occlusion_model,
    integrate_object_into_field,
    match_object_to_field,
    object_layout,
    paper_luminance_mask,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

FIELD = Path("/tmp/phase11-6-hybrid-premium-engine/06-generated-field.png")
OUT = Path("/tmp/phase11-8-hybrid-engine-v2")


def main() -> None:
    reset_provider_call_count()
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    field = Image.open(FIELD).convert("RGB")
    obj, meta = extract_project_object_v2(source)
    mapping = {}
    names = {"white": "03", "black": "04", "charcoal": "05", "paper": "06", "gray": "07"}
    for key, color in EDGE_BACKGROUNDS.items():
        mapping[f"{names[key]}-object-edge-test-{key}.png"] = edge_test_board(obj, color, key.upper())
        print(key, inspect_fringe(obj, color))
    print("spire", spire_preserved(obj))
    fused, _imeta = integrate_object_into_field(field, obj)
    paper = paper_luminance_mask(field)
    layout = object_layout(obj, paper, field.size)
    matched, _ = match_object_to_field(obj, analyze_field(field))
    layers = contact_occlusion_model(field=field, obj=matched, layout=layout, field_stats=analyze_field(field))
    mapping["09-material-integration-test.png"] = material_test_board(field, obj, matched, fused)
    mapping["10-contact-occlusion-test.png"] = contact_test_board(field, fused, layers["overlay"], layers["ambient"])
    full, report, thumbs = render_hierarchy_proof()
    mapping["12-hierarchy-100.png"] = thumbs["100"]
    mapping["13-hierarchy-50.png"] = thumbs["50"]
    mapping["14-hierarchy-25.png"] = thumbs["25"]
    mapping["15-hierarchy-15.png"] = thumbs["15"]
    mapping["hierarchy-scale-board.png"] = hierarchy_scale_board(thumbs)
    if provider_call_count() != 0:
        raise RuntimeError("V2 capability render must not generate images")
    for name, image in mapping.items():
        (OUT / name).write_bytes(_png(image))
    print("hier", report.get("pass"), "size", full.size, "calls", provider_call_count(), "obj", meta.get("object_size"))


if __name__ == "__main__":
    main()
