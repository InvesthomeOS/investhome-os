"""Dry-run Phase 10.0-R1 clean price compositor. No persist."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import _read_bytes
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_parse import NEW_PRICE, OLD_PRICE
from investhome_api.services.creative_director.phase10_0_r1_price_revise import apply_clean_price_revision, render_200_inspection

OUT = Path("/tmp/phase10-0-r1-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    parent = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    child, meta = apply_clean_price_revision(parent, old_value=OLD_PRICE, new_value=NEW_PRICE)
    extras = meta.pop("extras")
    box = tuple(meta["territory"])
    (OUT / "parent.png").write_bytes(_png(parent))
    (OUT / "clean-full.png").write_bytes(_png(extras["clean_full"]))
    (OUT / "clean-crop.png").write_bytes(_png(extras["clean_crop"].resize((extras["clean_crop"].size[0] * 4, extras["clean_crop"].size[1] * 4), Image.Resampling.NEAREST)))
    (OUT / "original-crop.png").write_bytes(_png(extras["original_crop"].resize((extras["original_crop"].size[0] * 4, extras["original_crop"].size[1] * 4), Image.Resampling.NEAREST)))
    (OUT / "new-plate.png").write_bytes(_png(extras["new_plate"].resize((extras["new_plate"].size[0] * 4, extras["new_plate"].size[1] * 4), Image.Resampling.NEAREST)))
    (OUT / "child.png").write_bytes(_png(child))
    (OUT / "zoom.png").write_bytes(_png(render_200_inspection(parent, child, box)))
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"residue": meta.get("residue"), "delta": meta.get("pixel_delta"), "territory": meta.get("territory")}, indent=2))


if __name__ == "__main__":
    main()
