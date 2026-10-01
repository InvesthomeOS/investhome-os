"""Stage 4.1 live. One-shot 9:16 recomposition. Pending human review."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.stage4_1_recompose import (
    STATUS_PENDING,
    generate_stage4_1_recomposition,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-1-premium-recomposition")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    result = generate_stage4_1_recomposition(db, user, row, language="tr")
    db.commit()
    boards = result["boards"]
    boards["source"].save(OUT / "01-source-master.png")
    boards["story"].save(OUT / "02-story-recomposed-final.png")
    boards["pair"].save(OUT / "03-source-vs-story.png")
    boards["mobile"].save(OUT / "04-mobile-preview.png")
    validation = result.get("validation") or {}
    print(
        json.dumps(
            {
                "STAGE": result.get("STAGE"),
                "STATUS": result.get("status") or STATUS_PENDING,
                "STORY_GENERATED": result.get("story_generated"),
                "SOURCE_MASTER": result.get("source_master_id"),
                "PHOTO_OBJECT_COUNT": validation.get("PHOTO_OBJECT_COUNT"),
                "SEMANTIC_LAYER_DUPLICATION_COUNT": validation.get("SEMANTIC_LAYER_DUPLICATION_COUNT"),
                "ORPHAN_TEXT_FRAGMENT_COUNT": validation.get("ORPHAN_TEXT_FRAGMENT_COUNT"),
                "SOURCE_TYPE_LEAKAGE": validation.get("SOURCE_TYPE_LEAKAGE"),
                "GENERATED_ARCHITECTURE_PIXELS": result.get("generated_architecture_pixels"),
                "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
