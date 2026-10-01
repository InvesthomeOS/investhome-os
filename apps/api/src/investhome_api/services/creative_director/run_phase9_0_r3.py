"""Phase 9.0-R3 live. Approve and lock Master 02. Do not re-render. Do not change cover."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import (
    APPROVED_ASSET_02,
    CREATIVE_CONCEPT,
    WORKFLOW_ID_90_R3,
    generate_phase9_0_r3_approve_lock_premium_master_02,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-0-r3-premium-master-02")


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
    result = generate_phase9_0_r3_approve_lock_premium_master_02(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    _dump("approved-master.json", result.get("approved_master") or {})
    _dump("master-library-state.json", result.get("library_state") or {})
    report = {
        "PHASE": "9.0-R3 MASTER 02 HUMAN APPROVAL FINALIZATION",
        "STATUS": result.get("status"),
        "MASTER": result.get("master_name"),
        "MASTER ID": result.get("master_id"),
        "FINAL ASSET ID": result.get("asset_id"),
        "APPROVAL STATUS": result.get("approval_status"),
        "STATE": result.get("master_state"),
        "ROUTER ELIGIBLE": "YES" if result.get("router_eligible") else "NO",
        "CREATIVE CONCEPT": CREATIVE_CONCEPT,
        "MASTER 01": "HUMAN_APPROVED / LOCKED",
        "MASTER 02": "HUMAN_APPROVED / LOCKED",
        "MASTER 03": "NOT CREATED",
        "REJECTED MASTER 02 HISTORY PRESERVED": "YES" if result.get("rejected_master_02_history_preserved") else "NO",
        "R1 HISTORY PRESERVED": "YES" if result.get("r1_history_preserved") else "NO",
        "VISUAL REGENERATED": "NO",
        "FORMAT WORK EXECUTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT": result.get("next_phase"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_90_R3,
        "LOCKED_R2_ASSET": APPROVED_ASSET_02,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase9-0-r3-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "MASTER ID", "FINAL ASSET ID", "ROUTER ELIGIBLE")}, indent=2, default=str))


if __name__ == "__main__":
    main()
