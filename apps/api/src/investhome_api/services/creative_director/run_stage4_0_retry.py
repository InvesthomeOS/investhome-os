"""Stage 4.0 RETRY live. Render Investhome brand master → 9:16 Story. No GPT Image."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_FILENAME
from investhome_api.services.creative_director.stage4_0_retry import (
    NEXT_PHASE,
    STATUS_PENDING,
    generate_stage4_0_retry,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


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
    result = generate_stage4_0_retry(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    boards = result["boards"]
    boards["source"].save(OUT / "01-source-master.png")
    boards["story"].save(OUT / "02-story-final.png")
    boards["pair"].save(OUT / "03-source-vs-story.png")
    boards["mobile"].save(OUT / "04-story-mobile-preview.png")
    boards["review"].save(OUT / "05-human-review-board.png")
    review = result.get("visual_review") or {}
    report = {
        "STAGE": "4.0 PREMIUM FORMAT ADAPTATION",
        "STATUS": result.get("status") or STATUS_PENDING,
        "SOURCE MASTER": PRODUCTION_MASTER_ID,
        "SOURCE": SELECTED_FILENAME,
        "TARGET": "9:16 STORY — 1080×1920",
        "STORY GENERATED": "YES" if result.get("story_generated") else "NO",
        "SAME CAMPAIGN": review.get("SAME CAMPAIGN"),
        "SIMPLE RESIZE": review.get("SIMPLE RESIZE"),
        "VISUAL IDENTITY PRESERVED": review.get("VISUAL IDENTITY PRESERVED"),
        "TYPOGRAPHIC CHARACTER PRESERVED": review.get("TYPOGRAPHIC CHARACTER PRESERVED"),
        "PHOTO ROLE PRESERVED": review.get("PHOTO ROLE PRESERVED"),
        "BRAND CHARACTER PRESERVED": review.get("BRAND CHARACTER PRESERVED"),
        "STORY COMPOSITION FEELS NATIVE": review.get("STORY COMPOSITION FEELS NATIVE"),
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "APPROVAL": "PENDING HUMAN REVIEW",
        "STORY ASSET ID": result.get("story_asset_id"),
        "NEXT": NEXT_PHASE,
        "IDENTITY": {"before": before, "after": after},
        "PLACEMENTS": result.get("placements"),
    }
    _dump("06-stage4-0-retry-report.json", report)
    print(json.dumps({"STAGE": report["STAGE"], "STATUS": report["STATUS"], "STORY GENERATED": report["STORY GENERATED"]}, indent=2))


if __name__ == "__main__":
    main()
