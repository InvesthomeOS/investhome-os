"""Dry Phase 11.1 — compose only. No persist. No master write."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, _read_bytes
from investhome_api.services.creative_director.phase11_1_compose import (
    compose_proof,
    crop_letter_photo,
    designed_letter,
    html_copy_ok,
    render_art_direction_board,
    render_labeled,
    render_opportunity_board,
)
from investhome_api.services.creative_director.phase11_1_strategy import DAY008_ASSET_ID, OPPORTUNITY_ASSETS

OUT = Path("/tmp/phase11-1-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY008_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    scene, column_rgba, meta = designed_letter(source=source)
    image, scene2, html, meta2 = compose_proof(source=source, logo_bytes=logo_bytes)
    column, _tf = crop_letter_photo(source)
    items = []
    for filename, asset_id, note in OPPORTUNITY_ASSETS:
        try:
            src = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
        items.append((filename.replace("IH_DC_TMP_001_Render_", "")[:28], src, note))
    (OUT / "05-no-copy-proof.png").write_bytes(_png(scene))
    (OUT / "08-stage3-creative-proof.png").write_bytes(_png(image))
    (OUT / "01-project-asset-opportunity-board.png").write_bytes(_png(render_opportunity_board(items)))
    (OUT / "07-art-direction-board.png").write_bytes(_png(render_art_direction_board(source, column, scene)))
    (OUT / "05-labeled.png").write_bytes(_png(render_labeled(scene, "NO-COPY", "spire as printed letter")))
    (OUT / "08-labeled.png").write_bytes(_png(render_labeled(image, "PROOF", "with campaign copy")))
    print("copy_ok", html_copy_ok(html))
    print("meta", meta2.get("paste"), meta2.get("internal_generated_pixels"))
    print("html_has_tarih_parts", "TAR" in html, ">H</p>" in html)


if __name__ == "__main__":
    main()
