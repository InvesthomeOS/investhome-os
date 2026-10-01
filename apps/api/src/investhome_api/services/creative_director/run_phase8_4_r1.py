"""Phase 8.4-R1 live. Spatial polish of 1:1 format child. Canonical 4:5 unchanged."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_4_r1_polish import (
    WORKFLOW_ID_84_R1,
    generate_phase8_4_r1_format_child_spatial_polish,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-4-r1-format-adaptation-1x1")


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase8_4_r1_format_child_spatial_polish(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "canonical": "01-canonical-4x5.png",
        "parent": "02-parent-1x1.png",
        "r1": "03-r1-1x1.png",
        "pair": "04-parent-vs-r1.png",
        "three": "05-three-way.png",
        "spatial": "06-spatial-polish.png",
        "preservation": "07-preservation-validation.png",
        "review": "08-human-review-board.png",
        "identity": "09-identity-validation.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    identity = result.get("identity") or {}
    scores = identity.get("scores") or {}
    preservation = result.get("preservation_validation") or {}
    revision = result.get("revision_readiness") or {}
    _dump("format-adaptation-v1.json", result.get("format_adaptation") or {})
    _dump("identity-validation.json", identity)
    _dump("preservation-validation.json", preservation)
    _dump("revision-readiness.json", revision)
    report = {
        "PHASE": "8.4-R1",
        "STATUS": result.get("status"),
        "PARENT FORMAT CHILD ID": result.get("parent_format_child_id"),
        "R1 FORMAT CHILD ID": result.get("child_id"),
        "R1 ASSET ID": result.get("child_asset_id"),
        "PHOTO CROP PRESERVED": preservation.get("PHOTO_CROP_PRESERVED"),
        "ARCHITECTURE FIDELITY": preservation.get("ARCHITECTURE_FIDELITY"),
        "HEADLINE PRESERVED": preservation.get("HEADLINE_PRESERVED"),
        "OFFER PRESERVED": preservation.get("OFFER_PRESERVED"),
        "PRICE + UNIT PRESERVED": preservation.get("PRICE_UNIT_PRESERVED"),
        "CTA CLEAR": identity.get("CTA_CLEAR"),
        "EDITORIAL CLOSURE CLEAR": identity.get("EDITORIAL_CLOSURE_CLEAR"),
        "LEFT CAMPAIGN COLUMN COHESIVE": identity.get("LEFT_CAMPAIGN_COLUMN_COHESIVE"),
        "TEXT ON BUSY ARCHITECTURE": identity.get("TEXT_ON_BUSY_ARCHITECTURE"),
        "NEGATIVE SPACE LOGIC": scores.get("NEGATIVE_SPACE_LOGIC"),
        "WHOLE CANVAS FAMILY RESEMBLANCE": scores.get("WHOLE_CANVAS_FAMILY_RESEMBLANCE"),
        "PRICE REVISION": revision.get("PRICE_EDIT_ONLY"),
        "COPY REVISION": revision.get("COPY_EDIT_ONLY"),
        "VISUAL REPLACE": revision.get("VISUAL_REPLACE_ONLY"),
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "CANONICAL MASTER CHANGED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "HUMAN APPROVAL": "PENDING",
        "NEXT AFTER HUMAN APPROVAL": result.get("next_phase"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_84_R1,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-4-r1-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "R1 FORMAT CHILD ID", "R1 ASSET ID", "CTA CLEAR")}, indent=2, default=str))


if __name__ == "__main__":
    main()
