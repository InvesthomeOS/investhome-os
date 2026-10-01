"""Stage 4.0-R2 live. One continuous photograph. No fragments."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.stage4_0_r2 import STATUS, generate_stage4_0_r2

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    result = generate_stage4_0_r2(db, user, row, language="tr")
    db.commit()
    boards = result["boards"]
    boards["story"].save(OUT / "story-final-r2.png")
    boards["pair"].save(OUT / "source-vs-r2.png")
    boards["mobile"].save(OUT / "mobile-preview-r2.png")
    print(json.dumps({"STATUS": result.get("status") or STATUS, "PHOTO PASTES": result.get("photo_pastes")}, indent=2))


if __name__ == "__main__":
    main()
