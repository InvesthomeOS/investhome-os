"""Dry Phase 11.4 — crop grid + compose. No persist. No master write."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, _read_bytes
from investhome_api.services.creative_director.phase11_4_compose import (
    compose_proof,
    crop_threshold_photo,
    designed_threshold,
    html_copy_ok,
    render_art_direction_board,
    render_commercial_system_board,
    render_crop_grid,
    render_opportunity_board,
    render_thumbnail_board,
    thumbnail_image,
)
from investhome_api.services.creative_director.phase11_4_strategy import DAY009_ASSET_ID, OPPORTUNITY_ASSETS

OUT = Path("/tmp/phase11-4-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY009_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    crop, _tf = crop_threshold_photo(source)
    scene, meta = designed_threshold(source=source)
    image, scene2, html, meta2 = compose_proof(source=source, logo_bytes=logo_bytes)
    items = []
    for filename, asset_id, note in OPPORTUNITY_ASSETS:
        try:
            src = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
        items.append((filename.replace("IH_DC_TMP_001_Render_", "")[:28], src, note))
    (OUT / "crop-grid.png").write_bytes(_png(render_crop_grid(source)))
    (OUT / "06-visual-idea-proof.png").write_bytes(_png(scene))
    (OUT / "09-stage3-creative-proof-03.png").write_bytes(_png(image))
    (OUT / "01-project-asset-opportunity-board.png").write_bytes(_png(render_opportunity_board(items)))
    (OUT / "07-commercial-system-proof.png").write_bytes(_png(render_commercial_system_board(scene, image)))
    (OUT / "08-art-direction-board.png").write_bytes(_png(render_art_direction_board(source, crop, scene)))
    (OUT / "10-thumbnail-proof.png").write_bytes(_png(render_thumbnail_board(image)))
    (OUT / "10-thumbnail-15.png").write_bytes(_png(thumbnail_image(image, scale=0.15)))
    print("copy_ok", html_copy_ok(html))
    print("generated_pixels", meta2.get("internal_generated_pixels"))
    print("headline", meta2.get("headline"))
    print("size", image.size, scene.size)


if __name__ == "__main__":
    main()
