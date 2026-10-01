"""Dry-run Phase 10.1 HEADLINE_ONLY compositor. No persist."""

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
from investhome_api.services.creative_director.phase10_1_headline_revise import (
    apply_clean_headline_revision,
    render_25_preview,
    render_labeled_crop,
    render_parent_vs_child,
)
from investhome_api.services.creative_director.phase10_1_parse import NEW_COPY, OLD_COPY, parse_headline_only_command, USER_COMMAND

OUT = Path("/tmp/phase10-1-dry")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parsed = parse_headline_only_command(USER_COMMAND)
    (OUT / "parse.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    db = SessionLocal()
    parent = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    child, meta = apply_clean_headline_revision(parent, old_copy=OLD_COPY, new_copy=NEW_COPY)
    extras = meta.pop("extras")
    (OUT / "parent.png").write_bytes(_png(parent))
    (OUT / "clean-full.png").write_bytes(_png(extras["clean_full"]))
    (OUT / "clean-crop.png").write_bytes(_png(extras["clean_crop"]))
    (OUT / "original-crop.png").write_bytes(_png(extras["original_crop"]))
    (OUT / "new-plate.png").write_bytes(_png(extras["new_plate"]))
    (OUT / "child.png").write_bytes(_png(child))
    (OUT / "pair.png").write_bytes(_png(render_parent_vs_child(parent, child)))
    (OUT / "diff.png").write_bytes(_png(render_pixel_diff(parent, child)))
    (OUT / "preview25.png").write_bytes(_png(render_25_preview(child)))
    orig = extras["original_crop"]
    (OUT / "original-zoom.png").write_bytes(
        _png(render_labeled_crop(orig.resize((orig.size[0] * 2, orig.size[1] * 2), Image.Resampling.NEAREST), "ORIGINAL HEADLINE"))
    )
    plate = extras["new_plate"]
    (OUT / "plate-zoom.png").write_bytes(
        _png(render_labeled_crop(plate.resize((plate.size[0] * 2, plate.size[1] * 2), Image.Resampling.NEAREST), "NEW HEADLINE PLATE"))
    )
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(
        {
            "parse": parsed.get("pass"),
            "residue": meta.get("residue"),
            "delta": meta.get("pixel_delta"),
            "territory": meta.get("territory"),
            "layout": {k: meta.get("layout", {}).get(k) for k in ("lines", "size", "lh", "tracking", "structure", "bbox", "fits")},
            "turkish": meta.get("turkish_glyphs"),
        },
        indent=2,
        ensure_ascii=False,
        default=str,
    ))


if __name__ == "__main__":
    main()
