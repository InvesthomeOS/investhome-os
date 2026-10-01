"""Archive the human-rejected Temple Premium Campaign 01. No regeneration."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    PRODUCTION_CAMPAIGN_ID,
    PRODUCTION_COVER_V2,
    _phase5,
    _production_guard,
)
from investhome_api.services.creative_director.phase8_1_first_premium_master import TEMPLE_PREMIUM_MASTER_01_ID
from investhome_api.services.creative_director.project_creative_master_library import (
    archive_human_rejected_master,
    count_approved_premium,
)

MASTER_ID = "1534b9db-8196-5b3e-b437-b7e7c7555ef7"
ASSET_ID = "92293f08-4909-4af0-98c7-033b79608728"
REASON = (
    "The design is technically valid but does not meet Investhome Premium Master visual quality. "
    "The project photograph, campaign typography, commercial information and brand still behave "
    "as separate placed elements rather than one authored advertising composition."
)


def main() -> None:
    assert MASTER_ID == TEMPLE_PREMIUM_MASTER_01_ID
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, UUID(PRODUCTION_CAMPAIGN_ID))
    assert row is not None
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    blob = _phase5(dict(original))
    library = blob.get("project_creative_master_library")
    assert isinstance(library, dict)
    archive_human_rejected_master(library, master_id=MASTER_ID, reason=REASON)
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    _production_guard(before, after)
    cover = str(after.get("current_cover_asset_id") or "")
    if cover and cover != PRODUCTION_COVER_V2:
        raise RuntimeError("Archive refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.commit()
    archived = next(item for item in library["masters"] if str(item.get("master_id")) == MASTER_ID)
    print(
        json.dumps(
            {
                "MASTER": archived.get("master_name"),
                "MASTER_ID": archived.get("master_id"),
                "ASSET": archived.get("visual_asset"),
                "approval_status": archived.get("approval_status"),
                "router_eligible": archived.get("router_eligible"),
                "human_review": archived.get("human_review"),
                "HUMAN_APPROVED_PREMIUM_MASTERS": count_approved_premium(library),
                "PRODUCTION_COVER_CHANGED": "NO",
                "NEXT_STEP": "HUMAN_SELECTED_PREMIUM_MASTER_SOURCE",
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
