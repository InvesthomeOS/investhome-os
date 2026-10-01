"""Dry-run Phase 10.0 compositor against locked Master 03. No persist."""

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
from investhome_api.services.creative_director.phase10_0_parse import NEW_PRICE, OLD_PRICE, USER_COMMAND, parse_price_only_command
from investhome_api.services.creative_director.phase10_0_price_revise import apply_price_only, render_pixel_diff, render_territory

OUT = Path("/tmp/phase10-0-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parsed = parse_price_only_command(USER_COMMAND)
    db = SessionLocal()
    parent = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    child, meta = apply_price_only(parent, old_value=OLD_PRICE, new_value=NEW_PRICE)
    (OUT / "parent.png").write_bytes(_png(parent))
    (OUT / "child.png").write_bytes(_png(child))
    (OUT / "territory.png").write_bytes(_png(render_territory(parent, tuple(meta["territory"]))))
    (OUT / "diff.png").write_bytes(_png(render_pixel_diff(parent, child)))
    crop = tuple(meta["territory"])
    cw, ch = max(1, crop[2] - crop[0]), max(1, crop[3] - crop[1])
    (OUT / "parent-crop.png").write_bytes(_png(parent.crop(crop).resize((cw * 4, ch * 4))))
    (OUT / "child-crop.png").write_bytes(_png(child.crop(crop).resize((cw * 4, ch * 4))))
    (OUT / "meta.json").write_text(json.dumps({"parse": parsed, "compose": meta}, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"parse": parsed["pass"], "delta": meta["pixel_delta"], "territory": meta["territory"]}, indent=2))


if __name__ == "__main__":
    main()
