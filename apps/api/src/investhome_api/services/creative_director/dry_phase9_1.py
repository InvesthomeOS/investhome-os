"""Dry-run Master 03. No persist. No library write."""

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, _read_bytes
from investhome_api.services.creative_director.phase9_1_compose import (
    ARCHITECTURE_ASSET_ID,
    INTERIOR_ASSET_ID,
    compose_master_03,
    crop_architecture,
    crop_interior,
    designed_chamber,
    html_copy_ok,
)

OUT = Path("/tmp/phase9-1-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    interior_src = Image.open(BytesIO(_read_bytes(db, UUID(INTERIOR_ASSET_ID)))).convert("RGB")
    architecture_src = Image.open(BytesIO(_read_bytes(db, UUID(ARCHITECTURE_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    interior, _ = crop_interior(interior_src)
    architecture, _ = crop_architecture(architecture_src)
    chamber, _ = designed_chamber(interior=interior, architecture=architecture)
    chamber.save(OUT / "chamber.png")
    image, _, html, _ = compose_master_03(interior=interior, architecture=architecture, logo_bytes=logo_bytes)
    image.save(OUT / "master.png")
    print("copy_ok", html_copy_ok(html))
    print("sizes", image.size, chamber.size)


if __name__ == "__main__":
    main()
