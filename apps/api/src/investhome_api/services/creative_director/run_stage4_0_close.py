"""Stage 4.0 close live. Archive Story proof. Lock recomposer doctrine. No Story. No R4."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.premium_format_recomposer_v1 import (
    NEXT_STAGE,
    RECOMPOSER_ID,
    STATUS,
    archived_story_proof,
    permanent_format_adaptation_rule,
    recomposer_contract,
)
from investhome_api.services.creative_director.stage4_0_close import (
    STAGE_LABEL,
    WORKFLOW_ID_40_CLOSE,
    generate_stage4_0_close,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


def _dump(name: str, payload: object) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_stage4_0_close(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    archive = result.get("archive") or archived_story_proof()
    doctrine = result.get("doctrine") or permanent_format_adaptation_rule()
    contract = result.get("contract") or recomposer_contract()
    _dump("14-story-test-archive.json", archive)
    _dump("15-permanent-format-adaptation-rule.json", doctrine)
    _dump("16-premium-format-recomposer-v1.json", contract)
    report = {
        "STAGE": STAGE_LABEL,
        "STATUS": STATUS,
        "TECHNICAL_FIDELITY": "PASS",
        "DESIGN_FIDELITY": "FAIL",
        "CURRENT_STORY": "REJECTED",
        "PREMIUM_FORMAT_ADAPTER": "REPOSITION MODEL DEPRECATED",
        "NEW_MODEL": RECOMPOSER_ID,
        "STORY_GENERATED": False,
        "R4_CREATED": False,
        "STAGE_4_1_EXECUTED": False,
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "WORKFLOW": WORKFLOW_ID_40_CLOSE,
        "IDENTITY": {"before": before, "after": after},
        "NEXT": NEXT_STAGE,
    }
    _dump("17-stage4-0-close-report.json", report)
    print(json.dumps({"STAGE": report["STAGE"], "STATUS": report["STATUS"], "NEXT": report["NEXT"]}, indent=2))


if __name__ == "__main__":
    main()
