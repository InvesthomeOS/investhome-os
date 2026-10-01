"""Phase 10.2 live. VISUAL_REPLACE_ONLY child. Do not overwrite parent or prior children."""

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
from investhome_api.services.creative_director.phase10_2_master import WORKFLOW_ID_10_2, generate_phase10_2_photo_replacement

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase10-2-natural-language-photo-replacement")


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
    critic_path = Path("/tmp/phase10-2-critic.json")
    critic = json.loads(critic_path.read_text(encoding="utf-8-sig")) if critic_path.is_file() else None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase10_2_photo_replacement(db, user, row, language="tr", critic=critic)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-locked-master-03.png": images.get("parent"),
        "02-current-exterior-day002.png": images.get("current_exterior"),
        "03-real-temple-exterior-shortlist.png": images.get("shortlist"),
        "04-selected-replacement.png": images.get("selected"),
        "05-replacement-crop-plan.png": images.get("crop_plan"),
        "06-photo-replacement-child.png": images.get("child"),
        "07-parent-vs-child.png": images.get("pair"),
        "08-pixel-diff.png": images.get("diff"),
        "09-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    validation = result.get("validation") or {}
    compose = result.get("compose") or {}
    _dump("natural-language-parse.json", result.get("parse"))
    _dump("asset-selection.json", result.get("selection"))
    _dump("visual-replacement-contract.json", result.get("contract"))
    _dump("crop-plan.json", compose.get("crop"))
    _dump("pixel-diff.json", compose.get("pixel_delta"))
    _dump("revision-validation.json", validation)
    report = {
        "PHASE": "10.2 NATURAL-LANGUAGE PROJECT PHOTO REPLACEMENT",
        "STATUS": result.get("status"),
        "USER COMMAND": result.get("user_command"),
        "PARENT MASTER": result.get("parent_master_name"),
        "PARENT MASTER ID": result.get("parent_master_id"),
        "PARENT ASSET ID": result.get("parent_asset_id"),
        "CHILD REVISION ID": result.get("child_revision_id"),
        "CHILD ASSET ID": result.get("child_asset_id"),
        "REVISION TYPE": result.get("revision_type"),
        "TARGET": result.get("target_object"),
        "OLD EXTERIOR": result.get("old_exterior"),
        "OLD ASSET ID": result.get("old_asset_id"),
        "NEW EXTERIOR": result.get("new_exterior"),
        "NEW ASSET ID": result.get("new_asset_id"),
        "SELECTION REASON": result.get("selection_reason"),
        "NATURAL LANGUAGE PARSE": validation.get("NATURAL_LANGUAGE_PARSE"),
        "REAL TEMPLE REPLACEMENT": validation.get("REAL_TEMPLE_REPLACEMENT"),
        "EXTERIOR ACTUALLY CHANGED": validation.get("EXTERIOR_ACTUALLY_CHANGED"),
        "INTERIOR PRESERVED": validation.get("INTERIOR_PRESERVED"),
        "DESIGN GEOMETRY PRESERVED": validation.get("DESIGN_GEOMETRY_PRESERVED"),
        "TYPOGRAPHY PRESERVED": validation.get("TYPOGRAPHY_PRESERVED"),
        "LOGO PRESERVED": validation.get("LOGO_PRESERVED"),
        "LOOKING CHAMBER PRESERVED": validation.get("LOOKING_CHAMBER_PRESERVED"),
        "NEW EXTERIOR CROP": validation.get("NEW_EXTERIOR_CROP"),
        "ARCHITECTURE READABILITY": validation.get("ARCHITECTURE_READABILITY"),
        "PHOTO CARD FEELING": validation.get("PHOTO_CARD_FEELING"),
        "VISIBLE COMPOSITING DAMAGE": validation.get("VISIBLE_COMPOSITING_DAMAGE"),
        "PIXEL DELTA OUTSIDE EXTERIOR TERRITORY": validation.get("PIXEL_DELTA_OUTSIDE_EXTERIOR_TERRITORY"),
        "ARCHITECTURE FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": validation.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "GPT IMAGE CALLS": validation.get("GPT_IMAGE_CALLS"),
        "PARENT MASTER CHANGED": "NO",
        "CHILD APPROVAL": "DRAFT",
        "ROUTER ELIGIBLE": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_10_2,
        "CRITIC": result.get("critic"),
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase10-2-report.json", report)
    print(json.dumps(
        {k: report[k] for k in ("PHASE", "STATUS", "CHILD REVISION ID", "CHILD ASSET ID", "NEW EXTERIOR", "PIXEL DELTA OUTSIDE EXTERIOR TERRITORY")},
        indent=2,
        default=str,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
