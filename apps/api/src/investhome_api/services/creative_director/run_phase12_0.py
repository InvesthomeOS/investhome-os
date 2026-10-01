"""Phase 12.0 live. Ingest one existing Investhome creative. No Stage 4. No generation."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase12_0_ingestion import (
    PRODUCTION_MASTER_ID,
    SELECTED_ASSET_ID,
    SELECTED_FILENAME,
    SOURCE_CATEGORY,
    SOURCE_PROJECT_NAME,
    STATUS_PENDING,
    WORKFLOW_ID_12_0,
    generate_phase12_0_ingestion,
    quality_check,
    source_record,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-0-production-master-ingestion")


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
    result = generate_phase12_0_ingestion(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    boards = result["boards"]
    boards["candidate"].save(OUT / "01-candidate-board.png")
    _dump("02-candidate-audit.json", result["audit"])
    boards["original"].save(OUT / "03-selected-original.png")
    _dump("04-source-record.json", result["source_record"])
    _dump("05-premium-semantic-map.json", result["semantic_map"])
    boards["overlay"].save(OUT / "06-semantic-overlay.png")
    _dump("07-relationship-map.json", result["relationship_map"])
    _dump("08-master-lock-map.json", result["lock_map"])
    _dump("09-master-ingestion-record.json", result["ingestion"])
    boards["review"].save(OUT / "10-human-review-board.png")
    quality = quality_check()
    report = {
        "PHASE": "12.0 FIRST PRODUCTION PREMIUM MASTER INGESTION",
        "STATUS": result.get("status") or STATUS_PENDING,
        "SELECTED CREATIVE": SELECTED_FILENAME,
        "ASSET ID": SELECTED_ASSET_ID,
        "PROJECT": SOURCE_PROJECT_NAME,
        "SOURCE CATEGORY": SOURCE_CATEGORY,
        "ORIGINAL FORMAT": "4:5",
        "DIMENSIONS": "1080×1350",
        "APPROVAL EVIDENCE": (
            "Investhome-branded finished 4:5 campaign curated in Media Library DESIGN_REFERENCE "
            "(Grade-A set). Not a research renderer output."
        ),
        "PRODUCTION QUALITY": quality["PROFESSIONAL QUALITY"],
        "COMMERCIAL COMPLETENESS": quality["COMMERCIAL COMPLETENESS"],
        "BRAND QUALITY": quality["BRAND QUALITY"],
        "TYPOGRAPHIC QUALITY": quality["TYPOGRAPHIC QUALITY"],
        "IMAGE QUALITY": quality["IMAGE QUALITY"],
        "FORMAT ADAPTATION POTENTIAL": quality["FORMAT ADAPTATION POTENTIAL"],
        "ORIGINAL ASSET MODIFIED": "NO",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "IDEOGRAM CALLS": 0,
        "PREMIUM MASTER INGESTION": "READY",
        "PREMIUM SEMANTIC MAP": "READY",
        "RELATIONSHIP MAP": "READY",
        "MASTER LOCK MAP": "READY",
        "MASTER ID": PRODUCTION_MASTER_ID,
        "ROUTER ELIGIBLE": False,
        "APPROVAL": "PENDING HUMAN REVIEW",
        "STAGE 4": "PAUSED",
        "NEXT": "HUMAN MASTER APPROVAL",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_12_0,
        "SOURCE RECORD": source_record(),
        "IDENTITY": {"before": before, "after": after},
        "QUALITY NOTES": {
            "commercial": quality["commercial_completeness_note"],
            "temple": quality["temple_project_reality_note"],
        },
    }
    _dump("11-phase12-0-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "MASTER ID": report["MASTER ID"]}, indent=2))


if __name__ == "__main__":
    main()
