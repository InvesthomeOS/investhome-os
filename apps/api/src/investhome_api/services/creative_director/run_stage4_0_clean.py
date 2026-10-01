"""Stage 4.0 clean live. Exclusive semantic layers. R2 composition unchanged."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.stage4_0_clean import (
    STATUS_BUG,
    STATUS_CLEAN,
    generate_stage4_0_clean,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    try:
        result = generate_stage4_0_clean(db, user, row, language="tr")
        db.commit()
        boards = result["boards"]
        boards["story"].save(OUT / "story-final-clean.png")
        boards["mobile"].save(OUT / "mobile-preview-clean.png")
        validation = result.get("validation") or {}
        print(
            json.dumps(
                {
                    "STATUS": result.get("status") or STATUS_CLEAN,
                    "PHOTO_OBJECT_COUNT": validation.get("PHOTO_OBJECT_COUNT"),
                    "SEMANTIC_LAYER_DUPLICATION_COUNT": validation.get("SEMANTIC_LAYER_DUPLICATION_COUNT"),
                    "ORPHAN_TEXT_FRAGMENT_COUNT": validation.get("ORPHAN_TEXT_FRAGMENT_COUNT"),
                },
                indent=2,
            )
        )
    except Exception as exc:
        db.rollback()
        print(json.dumps({"STATUS": STATUS_BUG, "ERROR": str(exc)}, indent=2))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
