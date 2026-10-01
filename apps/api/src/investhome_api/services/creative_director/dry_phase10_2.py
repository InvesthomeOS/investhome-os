"""Dry-run Phase 10.2 VISUAL_REPLACE_ONLY compositor. No persist."""

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
from investhome_api.services.creative_director.phase10_0_price_revise import render_pixel_diff
from investhome_api.services.creative_director.phase10_2_parse import USER_COMMAND, parse_visual_replace_command
from investhome_api.services.creative_director.phase10_2_replace import (
    SELECTED_ASSET_ID,
    apply_exterior_replacement,
    load_asset,
    render_parent_vs_child,
)

OUT = Path("/tmp/phase10-2-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parsed = parse_visual_replace_command(USER_COMMAND)
    (OUT / "parse.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    db = SessionLocal()
    parent = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    source = load_asset(db, SELECTED_ASSET_ID)
    child, meta = apply_exterior_replacement(parent, source)
    extras = meta.pop("extras")
    (OUT / "parent.png").write_bytes(_png(parent))
    (OUT / "child.png").write_bytes(_png(child))
    (OUT / "graded.png").write_bytes(_png(extras["graded"]))
    (OUT / "pair.png").write_bytes(_png(render_parent_vs_child(parent, child)))
    (OUT / "diff.png").write_bytes(_png(render_pixel_diff(parent, child)))
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(
        {
            "parse": parsed.get("pass"),
            "delta": meta.get("pixel_delta"),
            "crop": meta.get("crop"),
            "new": meta.get("new_filename"),
        },
        indent=2,
        ensure_ascii=False,
        default=str,
    ))


if __name__ == "__main__":
    main()
