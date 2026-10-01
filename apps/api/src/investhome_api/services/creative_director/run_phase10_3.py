"""Phase 10.3 live. Lock Stage 2. Do not regenerate. Do not start Stage 3."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase10_3_finalize import (
    WORKFLOW_ID_10_3,
    generate_phase10_3_stage_2_finalization,
)
from investhome_api.services.creative_director.phase10_3_revision_doctrine import NEXT_PHASE

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase10-3-stage-2-finalization")


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
    result = generate_phase10_3_stage_2_finalization(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    _dump("revision-doctrine.json", result.get("doctrine") or {})
    _dump("approved-revisions.json", result.get("approved_revisions") or [])
    _dump("approved-photo-child.json", result.get("approved_photo_child") or {})
    _dump("master-library-state.json", result.get("library_state") or {})
    report = {
        "PHASE": "10.3 STAGE 2 FINALIZATION",
        "STATUS": result.get("status"),
        "PRICE REVISION": result.get("price_revision"),
        "COPY REVISION": result.get("copy_revision"),
        "PROJECT PHOTO REPLACEMENT": result.get("project_photo_replacement"),
        "CORE REVISION CAPABILITIES": result.get("core_revision_capabilities"),
        "NATURAL LANGUAGE ROUTING": result.get("natural_language_routing"),
        "TARGETED TERRITORY RECONSTRUCTION": result.get("targeted_territory_reconstruction"),
        "LOCAL RESPONSIVE COPY RECOMPOSITION": result.get("local_responsive_copy_recomposition"),
        "REAL PROJECT PHOTO REPLACEMENT": result.get("real_project_photo_replacement"),
        "APPROVED MASTER IMMUTABILITY": result.get("approved_master_immutability"),
        "PROJECT REALITY POLICY": result.get("project_reality_policy"),
        "MASTER 01": "UNCHANGED",
        "MASTER 02": "UNCHANGED",
        "MASTER 03": "UNCHANGED",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER": "UNCHANGED",
        "STAGE 1": result.get("stage_1"),
        "STAGE 2": result.get("stage_2"),
        "NEXT": result.get("next_phase") or NEXT_PHASE,
        "STAGE 3 EXECUTED": "NO",
        "VISUAL REGENERATED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_10_3,
        "IDENTITY": {"before": before, "after": after},
        "LIBRARY": result.get("library_state"),
        "APPROVED REVISIONS": result.get("approved_revisions"),
        "PHOTO CHILD REVISION ID": result.get("photo_child_revision_id"),
        "PHOTO CHILD ASSET ID": result.get("photo_child_asset_id"),
    }
    _dump("phase10-3-report.json", report)
    print(json.dumps(
        {k: report[k] for k in ("PHASE", "STATUS", "STAGE 2", "NEXT", "STAGE 3 EXECUTED")},
        indent=2,
        default=str,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
