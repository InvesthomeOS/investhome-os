"""Phase 9.0 live. One Temple Premium Campaign 02 from ORNEK_00012. DRAFT. No promotion."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_compose import ORNEK_FILENAME, SUNSET_ASSET_ID, SUNSET_FILENAME
from investhome_api.services.creative_director.phase9_0_master import (
    MASTER_NAME_02,
    TEMPLE_PREMIUM_MASTER_02_ID,
    WORKFLOW_ID_90,
    generate_phase9_0_premium_master_02,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-0-premium-master-02-creative-first")


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
    result = generate_phase9_0_premium_master_02(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-human-selected-reference.png",
        "shortlist": "02-temple-photo-shortlist.png",
        "assets": "03-selected-project-assets.png",
        "direction": "04-creative-direction.png",
        "master": "05-premium-master-02.png",
        "pair": "06-reference-vs-master.png",
        "creative": "07-creative-quality-review.png",
        "reality": "08-project-reality-validation.png",
        "review": "09-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    review = result.get("creative_quality_review") or {}
    reality = result.get("project_reality_validation") or {}
    _dump("photo-selection.json", result.get("photo_selection") or {})
    _dump("creative-direction.json", result.get("creative_direction") or {})
    _dump(
        "premium-master-02.json",
        {
            "master_name": result.get("master_name"),
            "master_id": result.get("master_id"),
            "asset_id": result.get("asset_id"),
            "approval_status": result.get("approval_status"),
            "router_eligible": result.get("router_eligible"),
            "human_selected_source": result.get("human_selected_source"),
            "selected_assets": result.get("selected_assets"),
            "logo_asset_id": result.get("logo_asset_id"),
        },
    )
    _dump("creative-quality-review.json", review)
    _dump("project-reality-validation.json", reality)
    report = {
        "PHASE": "9.0 THE TEMPLE PREMIUM MASTER 02",
        "STATUS": result.get("status"),
        "HUMAN_SELECTED_SOURCE": ORNEK_FILENAME,
        "SELECTED_REAL_TEMPLE_ASSETS": result.get("selected_assets"),
        "MASTER": MASTER_NAME_02,
        "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "asset_id": result.get("asset_id"),
        "approval_status": "DRAFT",
        "CREATIVE_QUALITY": {
            "AGENCY_FINISHED_CAMPAIGN": review.get("AGENCY_FINISHED_CAMPAIGN"),
            "ACTUAL_CREATIVE_IDEA": review.get("ACTUAL_CREATIVE_IDEA"),
            "ONE_AUTHORED_COMPOSITION": review.get("ONE_AUTHORED_COMPOSITION"),
            "MEMORABLE_VISUAL_RELATIONSHIP": review.get("MEMORABLE_VISUAL_RELATIONSHIP"),
        },
        "REAL_PROJECT_PHOTOS": reality.get("REAL_PROJECT_PHOTOS"),
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": reality.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "REAL_TEMPLE_LOGO": reality.get("REAL_TEMPLE_LOGO"),
        "DUPLICATE_TEMPLE_WORDMARK": reality.get("DUPLICATE_TEMPLE_WORDMARK"),
        "FINANCIAL_CONTENT": reality.get("FINANCIAL_CONTENT"),
        "ROUTER_ELIGIBLE": "NO",
        "MASTER_01_CHANGED": "NO",
        "FORMAT_WORK_EXECUTED": "NO",
        "PRODUCTION_COVER_CHANGED": "NO",
        "NEXT_STEP": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "MASTER_01_ID": APPROVED_MASTER_ID,
        "MASTER_01_ASSET": APPROVED_ASSET_ID,
        "PHOTO": {"filename": SUNSET_FILENAME, "asset_id": SUNSET_ASSET_ID},
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "WORKFLOW": WORKFLOW_ID_90,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase9-0-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("PHASE", "STATUS", "master_id", "asset_id", "CREATIVE_QUALITY")
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
