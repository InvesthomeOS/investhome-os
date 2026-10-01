"""Render Phase 11.7 R1 from the retained 11.6 field. No image generation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_CAMPAIGN_ID, _read_bytes
from investhome_api.services.creative_director.phase11_6_photo_object import object_on_checker
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID
from investhome_api.services.creative_director.phase11_7_boards import (
    render_hierarchy_study,
    render_human_board,
    render_material_study,
    render_side_by_side,
    render_type_study,
    thumbnail,
)
from investhome_api.services.creative_director.phase11_7_compose import compose_hybrid_r1
from investhome_api.services.creative_director.phase11_7_object import isolate_project_object_r1
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

FIELD = Path("/tmp/phase11-6-hybrid-premium-engine/06-generated-field.png")
ORIGINAL = Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png")
OUT = Path("/tmp/phase11-7-hybrid-finish")


def main() -> None:
    reset_provider_call_count()
    OUT.mkdir(parents=True, exist_ok=True)
    field = Image.open(FIELD).convert("RGB")
    original = Image.open(ORIGINAL).convert("RGB")
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, UUID(PRODUCTION_CAMPAIGN_ID))
    assert row is not None
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    logo = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    obj, meta = isolate_project_object_r1(source)
    r1, markup, compose_meta, fused = compose_hybrid_r1(field=field, obj=obj, logo_bytes=logo)
    if provider_call_count() != 0:
        raise RuntimeError("R1 render must not call image generation")
    thumb = thumbnail(r1, 0.15)
    obj_plate = object_on_checker(obj)
    mapping = {
        "01-original-proof.png": original,
        "04-material-integration-study.png": render_material_study(field, obj_plate, fused),
        "05-typography-finish-study.png": render_type_study(r1),
        "06-commercial-hierarchy-study.png": render_hierarchy_study(r1),
        "07-hybrid-premium-proof-r1.png": r1,
        "08-thumbnail-r1.png": thumb,
        "09-side-by-side-review.png": render_side_by_side(original, r1),
        "13-human-review-board.png": render_human_board(original, r1, thumb),
        "qa-object-r1.png": obj_plate,
        "qa-fused.png": fused,
    }
    for name, image in mapping.items():
        (OUT / name).write_bytes(_png(image))
    print("r1", r1.size, "calls", provider_call_count(), "paper", compose_meta.get("fuse"))


if __name__ == "__main__":
    main()
