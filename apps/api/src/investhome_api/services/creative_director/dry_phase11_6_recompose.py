"""Recompose Phase 11.6 from the locked generated field. Does not call image generation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_CAMPAIGN_ID, _read_bytes
from investhome_api.services.creative_director.phase11_6_boards import (
    render_comparison_board,
    render_composition_development,
    render_human_review_board,
)
from investhome_api.services.creative_director.phase11_6_compose import compose_development_plate, compose_hybrid_proof
from investhome_api.services.creative_director.phase11_6_master import HISTORIC_PROOFS, _load_historic
from investhome_api.services.creative_director.phase11_6_photo_object import isolate_project_object, object_on_checker
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

OUT = Path("/tmp/phase11-6-hybrid-premium-engine")


def main() -> None:
    reset_provider_call_count()
    field = Image.open(OUT / "06-generated-field.png").convert("RGB")
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, UUID(PRODUCTION_CAMPAIGN_ID))
    assert row is not None
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    obj, _window, _meta = isolate_project_object(source)
    obj_plate = object_on_checker(obj)
    proof, markup, meta = compose_hybrid_proof(field=field, obj=obj, logo_bytes=logo_bytes)
    development = compose_development_plate(field=field, obj=obj)
    if provider_call_count() != 0:
        raise RuntimeError("Recompose must not call image generation")
    p1 = _load_historic(HISTORIC_PROOFS[0])
    p2 = _load_historic(HISTORIC_PROOFS[1])
    p3 = _load_historic(HISTORIC_PROOFS[2])
    mapping = {
        "07-real-project-object.png": obj_plate,
        "08-composition-development.png": render_composition_development(field, obj_plate, development),
        "09-hybrid-premium-proof.png": proof,
        "10-proof-comparison-board.png": render_comparison_board(p1, p2, p3, proof),
        "13-human-review-board.png": render_human_review_board(field, obj_plate, proof),
    }
    for name, image in mapping.items():
        (OUT / name).write_bytes(_png(image))
    (OUT / "compose-meta.json").write_text(str(meta), encoding="utf-8")
    print("recomposed", proof.size, "old_compiler", meta.get("old_compiler_used"), "copy_ok", "TAŞ TEMİNAT" in markup)


if __name__ == "__main__":
    main()
