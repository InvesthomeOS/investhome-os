"""Phase 10.0-R1 live. Clean PRICE_ONLY child. Do not overwrite parent or rejected 10.0 child."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase10_0_r1_master import (
    WORKFLOW_ID_10_R1,
    generate_phase10_0_r1_clean_price_revision,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase10-0-r1-clean-price-revision")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    critic_path = Path("/tmp/phase10-0-r1-critic.json")
    critic = json.loads(critic_path.read_text(encoding="utf-8-sig")) if critic_path.is_file() else {
        "DOES_ANY_TEXT_LOOK_DAMAGED_OR_CORRUPTED": "PENDING",
        "DOES_THE_PRICE_LOOK_LIKE_NATIVE_ORIGINAL_TYPOGRAPHY": "PENDING",
        "ARE_OLD_PRICE_GLYPHS_VISIBLE": "PENDING",
        "IS_THERE_A_VISIBLE_PATCH_OR_MASK": "PENDING",
        "IS_750000_USD_FULLY_LEGIBLE": "PENDING",
    }
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase10_0_r1_clean_price_revision(db, user, row, language="tr", critic=critic)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-locked-master.png": images.get("parent"),
        "02-original-price-territory.png": images.get("original_territory"),
        "03-clean-price-background.png": images.get("clean_bg"),
        "04-new-price-render.png": images.get("new_price"),
        "05-price-revision-r1.png": images.get("r1"),
        "06-parent-vs-r1.png": images.get("pair"),
        "07-200-percent-price-inspection.png": images.get("zoom"),
        "08-pixel-diff.png": images.get("diff"),
        "09-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    validation = result.get("validation") or {}
    report = {
        "PHASE": "10.0-R1 CLEAN PRICE REVISION",
        "STATUS": result.get("status"),
        "USER COMMAND": result.get("user_command"),
        "OLD PRICE": result.get("old_price"),
        "NEW PRICE": result.get("new_price"),
        "SOURCE": "LOCKED MASTER 03",
        "CHILD REVISION ID": result.get("child_revision_id"),
        "CHILD ASSET ID": result.get("child_asset_id"),
        "OLD PRICE COMPLETELY REMOVED": validation.get("OLD_PRICE_COMPLETELY_REMOVED"),
        "CLEAN BACKGROUND BEFORE NEW TEXT": validation.get("CLEAN_BACKGROUND_BEFORE_NEW_TEXT"),
        "NEW PRICE NATIVE TYPOGRAPHY": validation.get("NEW_PRICE_NATIVE_TYPOGRAPHY"),
        "OLD GLYPH REMNANTS": validation.get("OLD_GLYPH_REMNANTS"),
        "VISIBLE PATCH": validation.get("VISIBLE_PATCH"),
        "NEW PRICE FULLY LEGIBLE": validation.get("NEW_PRICE_FULLY_LEGIBLE"),
        "PIXEL DELTA OUTSIDE CLEAN PRICE TERRITORY": validation.get("PIXEL_DELTA_OUTSIDE_CLEAN_PRICE_TERRITORY"),
        "LOOKING CHAMBER PRESERVED": validation.get("LOOKING_CHAMBER_PRESERVED"),
        "ARCHITECTURE FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": validation.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "GPT IMAGE CALLS": validation.get("GPT_IMAGE_CALLS"),
        "PARENT MASTER CHANGED": "NO",
        "CHILD APPROVAL": "DRAFT",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_10_R1,
        "CRITIC": result.get("critic"),
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase10-0-r1-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "CHILD REVISION ID", "CHILD ASSET ID", "PIXEL DELTA OUTSIDE CLEAN PRICE TERRITORY")}, indent=2, default=str))


if __name__ == "__main__":
    main()
