"""Stage 4.0-R1 live. Vertical polish of the existing brand Story."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.stage4_0_r1 import STATUS, generate_stage4_0_r1

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    result = generate_stage4_0_r1(db, user, row, language="tr")
    db.commit()
    boards = result["boards"]
    boards["story"].save(OUT / "story-final-r1.png")
    boards["pair"].save(OUT / "source-vs-r1.png")
    boards["mobile"].save(OUT / "mobile-preview-r1.png")
    report = {
        "STAGE": "4.0-R1 STORY VISUAL POLISH",
        "STATUS": result.get("status") or STATUS,
        "PARENT STORY": result.get("parent_story_asset_id"),
        "STORY ASSET ID": result.get("story_asset_id"),
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "APPROVAL": "PENDING HUMAN REVIEW",
        "PLACEMENTS": result.get("placements"),
    }
    (OUT / "stage4-0-r1-report.json").write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"STAGE": report["STAGE"], "STATUS": report["STATUS"]}, indent=2))


if __name__ == "__main__":
    main()
