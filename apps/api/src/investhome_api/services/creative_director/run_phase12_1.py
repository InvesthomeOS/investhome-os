"""Phase 12.1 live. Approve brand master + lock scope. No Stage 4. No artwork."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID, SELECTED_FILENAME
from investhome_api.services.creative_director.phase12_1_approve_lock import (
    MASTER_TYPE_LABEL,
    NEXT_PHASE,
    STATUS,
    WORKFLOW_ID_12_1,
    brand_master_scope,
    generate_phase12_1_approve_lock,
)
from investhome_api.services.creative_director.premium_format_adapter_v1 import STAGE4_PROOF_SCOPE

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-1-production-master-approval")


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
    result = generate_phase12_1_approve_lock(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    scope = brand_master_scope()
    _dump("01-master-scope.json", scope)
    _dump(
        "02-routing-rules.json",
        {
            "schema": "PremiumMasterRoutingRulesV1",
            "brand_master_id": PRODUCTION_MASTER_ID,
            "the_temple_production_premium_master": "NOT AVAILABLE",
            "do_not_use": ["Master 01", "Master 02", "Master 03", "research proofs", "ORNEK_00013 as a Temple master"],
            "stage_4_proof_scope": STAGE4_PROOF_SCOPE,
            "stage_4_executed": False,
            "next": NEXT_PHASE,
        },
    )
    report = {
        "PHASE": "12.1 PRODUCTION MASTER APPROVAL + PROJECT SCOPE LOCK",
        "STATUS": STATUS,
        "MASTER ID": PRODUCTION_MASTER_ID,
        "MASTER": SELECTED_FILENAME,
        "ASSET ID": SELECTED_ASSET_ID,
        "MASTER TYPE": MASTER_TYPE_LABEL,
        "HUMAN APPROVED": "YES",
        "ROUTER ELIGIBLE": "YES",
        "MASTER SCOPE": scope["MASTER_SCOPE"],
        "PROJECT_ID": scope["PROJECT_ID"],
        "BRAND_ID": scope["BRAND_ID"],
        "CROSS PROJECT REUSE": "FALSE",
        "FORMAT DERIVATIVES": "ALLOWED",
        "SEMANTIC REVISIONS": "ALLOWED",
        "PROJECT ASSET SUBSTITUTION": "NOT ALLOWED",
        "THE TEMPLE MASTER AVAILABLE": "NO",
        "STAGE 4 SOURCE AVAILABLE": "YES — INVESTHOME BRAND MASTER",
        "STAGE 4 EXECUTED": "NO",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_12_1,
        "NEXT": NEXT_PHASE,
        "IDENTITY": {"before": before, "after": after},
        "SCOPE": scope,
    }
    _dump("03-phase12-1-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "MASTER ID": report["MASTER ID"]}, indent=2))


if __name__ == "__main__":
    main()
